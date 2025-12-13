#!/usr/bin/env python3
"""
==========================================================================================================================================================
|THE CODE IS FULLY COPIED FROM A PRIVATE AI-Stock-Automatization REPO NAMED StockAI-Bot2.4.py USED FOR TESTING BACKEND CODE BEFORE PRODUCTION DEPLOYMENT.|
==========================================================================================================================================================
mvp_alerts_2.4.py (Extended Matching v2.4)
Upgrades from 2.3:
 - Integrated DB migration from old med_articles to new canonical schema.
 - Canonical article hashing (SHA256 of normalized title+url+published_at) to deduplicate.
 - articles table + article_tickers link table (many-to-many).
 - 'posted' flag per article to avoid duplicate HIGH posts; HIGH posts include all matched tickers.
 - MED entries stored once and linked to tickers.
 - Improved logging with RotatingFileHandler, diagnostics on startup.
 - Better timestamp formatting and fallback handling.
 - Preserves original behavior where possible.
"""

import os
import sys
import time
import json
import math
import logging
import traceback
import requests
import re
import sqlite3
import hashlib
import platform
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dateutil import parser as dateutil_parser
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# ---------------------------
# Configuration
# ---------------------------
MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY", "9Ydp4VNIm9zZ6WHmVcys40L9gUlUWOKW6ZYFxX2T")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1435654882710519888/ZDx_dGG22dknR4hGrENapdaG1Cm-VyUCUvrXmI6kGxcw0KLILP5AJKmNB14L9TzD65J-")
WATCHLIST_PATH = "watchlist.txt"
COMPANY_MAP_PATH = "company_map.json"
LAST_TS_PATH = "last_timestamp.txt"
LOG_FILE = "bot.log"
DB_PATH = "med_alerts.db"

# User-tunable
BATCH_SIZE = 10
CYCLE_SECONDS = int(os.getenv("CYCLE_SECONDS", "3600"))
COLD_START_HOURS = 12
SMART_COOLDOWN_MINUTES = 30
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5
FILTER_MODE = int(os.getenv("FILTER_MODE", "2"))
LOG_LEVEL = logging.INFO

# Severity thresholds
HIGH_THRESHOLD = 2.75
MED_THRESHOLD = 1.25
if FILTER_MODE == 3:
    HIGH_THRESHOLD = 3.5
    MED_THRESHOLD = 2.0
elif FILTER_MODE == 2:
    HIGH_THRESHOLD = 2.75
    MED_THRESHOLD = 1.25
elif FILTER_MODE == 1:
    HIGH_THRESHOLD = 2.5
    MED_THRESHOLD = 1.0

# Extended Matching settings
EXT_MATCH_LOG_TIER = True        # log match tier
FUZZY_MAX_DISTANCE = 2
FUZZY_MIN_TOKEN_LEN = 4

# Keyword weights
keyword_weights: Dict[str, float] = {
    "acquir": 1.5, "acquisition": 1.5, "acquired": 1.5, "merger": 1.5, "takeover": 1.5,
    "lawsuit": 2.0, "settlement": 1.8, "investigation": 1.8, "charged": 2.5, "indict": 2.5,
    "bankrupt": 3.0, "bankruptcy": 3.0, "delist": 2.5, "insider": 1.2, "stake": 0.7,
    "earnings": 2.0, "beats": 1.8, "misses": 1.8, "guidance": 1.7, "revenue": 1.1,
    "q1": 0.4, "q2": 0.4, "q3": 0.4, "q4": 0.4,
    "resign": 1.8, "resignation": 1.8, "stepping down": 1.8, "appoint": 1.4, "ceo": 1.0, "cfo": 1.0,
    "recall": 2.5, "accredit": 1.0, "regulator": 1.5, "sanction": 2.5, "fine": 2.0,
    "offer": 0.8, "buyback": 1.5, "dividend": 1.2, "layoff": 2.0, "shutdown": 2.5,
    "bankrun": 3.0, "cyberattack": 2.5, "hack": 2.2, "data breach": 2.5,
    "token": 1.2, "suspend": 1.8,
    "tariff": 1.5, "embargo": 2.0, "war": 3.0,
    "downgrade": 1.6, "upgrade": 1.6, "price target": 0.9, "fraud": 3.0,
    "ipo": 1.2, "filing": 0.8,
    "announce": 0.5, "launch": 0.6, "contract": 1.0, "agreement": 0.8, "partnership": 0.9,
}
keyword_weights = {k.lower(): v for k, v in keyword_weights.items()}

# ---------------------------
# Logging: rotating + stream handler
# ---------------------------
logger = logging.getLogger("mvp_alerts")
logger.setLevel(LOG_LEVEL)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

# Rotating file handler: 5 files, 5MB each
try:
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
except Exception:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

# Avoid duplicate handlers on reload
if logger.handlers:
    logger.handlers = []
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# ---------------------------
# Utilities
# ---------------------------

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def format_timestamp_z(dt: datetime) -> str:
    return dt.replace(microsecond=0).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def try_multiple_ts_formats(dt: datetime) -> List[str]:
    candidates = []
    candidates.append(dt.replace(microsecond=0).isoformat().replace("+00:00", ""))
    candidates.append(dt.replace(microsecond=0).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"))
    candidates.append(dt.replace(microsecond=0).astimezone(timezone.utc).isoformat())
    return candidates

def read_last_timestamp(path: str = LAST_TS_PATH) -> Optional[str]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            ts = f.read().strip()
            if not ts:
                return None
            _ = dateutil_parser.parse(ts)
            return ts
    except Exception as e:
        logger.warning(f"Failed to read last timestamp: {e}")
        return None

def write_last_timestamp(ts: str, path: str = LAST_TS_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(ts)
    except Exception as e:
        logger.warning(f"Failed to write last timestamp: {e}")

def safe_request_get(url: str, params: dict, headers: dict = None, max_retries: int = MAX_RETRIES) -> Tuple[Optional[requests.Response], Optional[dict]]:
    attempt = 0
    backoff = 1.0
    headers = headers or {}
    while attempt < max_retries:
        attempt += 1
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            if resp.status_code == 200:
                try:
                    return resp, resp.json()
                except Exception:
                    return resp, None
            if resp.status_code in (429, 500, 502, 503, 504):
                logger.warning(f"MarketAux HTTP {resp.status_code}: {resp.text}")
                sleep_for = backoff * (RETRY_BACKOFF_BASE ** (attempt - 1))
                logger.info(f"Retrying after {sleep_for:.1f}s (attempt {attempt}/{max_retries})")
                time.sleep(sleep_for)
                continue
            return resp, None
        except requests.RequestException as e:
            logger.warning(f"Request error: {e}. attempt {attempt}/{max_retries}")
            time.sleep(backoff * (RETRY_BACKOFF_BASE ** (attempt - 1)))
            continue
    logger.error("Exceeded max retries on request.")
    return None, None

def post_to_discord(content: str) -> bool:
    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not set; skipping Discord post.")
        return False
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
        if resp.status_code in (200, 204):
            logger.info("Discord posted.")
            return True
        else:
            logger.warning(f"Discord post failed: {resp.status_code} {resp.text}")
            return False
    except requests.RequestException as e:
        logger.warning(f"Discord post exception: {e}")
        return False

def load_watchlist(path: str = WATCHLIST_PATH) -> List[str]:
    if not os.path.exists(path):
        logger.warning("watchlist.txt not found; creating empty watchlist.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip().upper() for line in f if line.strip()]
    logger.info(f"Loaded {len(lines)} personal tickers from {path}.")
    return lines

def load_company_map(path: str = COMPANY_MAP_PATH) -> Dict[str, str]:
    if not os.path.exists(path):
        logger.info("No company_map.json found; continuing with ticker-only names.")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = {k.upper(): v for k, v in data.items()}
        logger.info(f"Loaded company map from {path}.")
        return data
    except Exception as e:
        logger.warning(f"Failed to load company_map.json: {e}")
        return {}

def normalize_text_for_hash(s: str) -> str:
    # minimal normalization before hashing
    return re.sub(r"\s+", " ", (s or "").strip()).lower()

def canonical_article_hash(title: str, url: str, published_at: str) -> str:
    base = "|".join([normalize_text_for_hash(title), normalize_text_for_hash(url), normalize_text_for_hash(published_at)])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

# ---------------------------
# DB: new schema + migration
# ---------------------------

def connect_db():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn

def init_and_migrate_db():
    """
    Create new schema if missing and migrate old med_articles table if present.
    New schema:
      - articles(id, title, description, url, severity, score, hash, published_at, detected_at, posted)
      - article_tickers(id, article_id, ticker)
    """

    conn = connect_db()
    cur = conn.cursor()

    # Create new tables if they don't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            url TEXT,
            severity TEXT,
            score REAL,
            hash TEXT UNIQUE,
            published_at TEXT,
            detected_at TEXT DEFAULT (datetime('now')),
            posted INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS article_tickers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            ticker TEXT,
            UNIQUE(article_id, ticker),
            FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
        )
    """)
    conn.commit()

    # Detect old med_articles schema and migrate
    # Old table name guessed to be 'med_articles' (from v2.3)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='med_articles'")
    if cur.fetchone():
        logger.info("Legacy med_articles table detected — starting migration into new schema.")
        try:
            cur.execute("SELECT id, ticker, title, description, url, severity, published_at, detected_at FROM med_articles")
            rows = cur.fetchall()
            migrated = 0
            for r in rows:
                ticker = r["ticker"] or ""
                title = r["title"] or ""
                desc = r["description"] or ""
                url = r["url"] or ""
                severity_val = r["severity"] if r["severity"] is not None else ""
                published_at = r["published_at"] or ""
                # old severity may be numeric; store as MED/LOW/HIGH by thresholds
                if isinstance(severity_val, (int, float)):
                    score_val = float(severity_val)
                    if score_val >= HIGH_THRESHOLD:
                        sev_text = "HIGH"
                    elif score_val >= MED_THRESHOLD:
                        sev_text = "MED"
                    else:
                        sev_text = "LOW"
                else:
                    # if it's textual or empty, attempt to keep as-is; default MED for safety
                    sev_text = str(severity_val) if severity_val else "MED"

                art_hash = canonical_article_hash(title, url, published_at)
                # Insert article if not present
                try:
                    cur.execute("""
                        INSERT OR IGNORE INTO articles (title, description, url, severity, score, hash, published_at, detected_at, posted)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """, (title, desc, url, sev_text, None, art_hash, published_at or None, r["detected_at"] or None))
                    conn.commit()
                except Exception:
                    # ignore duplicate or insertion issues
                    pass

                # Get article_id
                cur.execute("SELECT id FROM articles WHERE hash=?", (art_hash,))
                art_row = cur.fetchone()
                if art_row:
                    art_id = art_row["id"]
                    try:
                        cur.execute("INSERT OR IGNORE INTO article_tickers (article_id, ticker) VALUES (?, ?)", (art_id, ticker.upper()))
                        conn.commit()
                    except Exception:
                        pass
                migrated += 1

            logger.info(f"Migration complete — migrated {migrated} legacy rows.")
            # Optional: keep legacy table, or comment out the next line to drop it.
            # cur.execute("DROP TABLE IF EXISTS med_articles")
            # conn.commit()
        except Exception:
            logger.exception("Failed while migrating legacy med_articles table.")
    conn.close()

# DB helper functions for new schema

def find_article_by_hash(art_hash: str) -> Optional[sqlite3.Row]:
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM articles WHERE hash=?", (art_hash,))
    row = cur.fetchone()
    conn.close()
    return row

def save_article_and_link(title: str, description: str, url: str, severity: str, score: float, published_at: str, tickers: List[str], mark_posted: bool=False) -> Tuple[int, bool]:
    """
    Save article if not exists (by hash). Link provided tickers in article_tickers.
    If mark_posted True, set posted=1 in articles.
    Returns (article_id, inserted_flag)
    """
    art_hash = canonical_article_hash(title, url, published_at or "")
    conn = connect_db()
    cur = conn.cursor()
    inserted = False
    try:
        cur.execute("""
            INSERT OR IGNORE INTO articles (title, description, url, severity, score, hash, published_at, detected_at, posted)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
        """, (title, description, url, severity, score, art_hash, published_at or None, 1 if mark_posted else 0))
        conn.commit()
        # fetch article id
        cur.execute("SELECT id, posted FROM articles WHERE hash=?", (art_hash,))
        art_row = cur.fetchone()
        if art_row is None:
            raise RuntimeError("Failed to fetch inserted article.")
        art_id = art_row["id"]
        # if inserted (we inserted new row), SQLite's INSERT OR IGNORE doesn't tell us. Check if posted flag set:
        # If this is a new insert, some fields will match values we passed; we treat inserted=True when first time linking tickers.
        # For robust detection, check if there was any ticker existing.
        cur.execute("SELECT COUNT(1) as cnt FROM article_tickers WHERE article_id=?", (art_id,))
        cnt_before = cur.fetchone()["cnt"]
        for t in tickers:
            try:
                cur.execute("INSERT OR IGNORE INTO article_tickers (article_id, ticker) VALUES (?, ?)", (art_id, t.upper()))
            except Exception:
                pass
        conn.commit()
        cur.execute("SELECT COUNT(1) as cnt_after FROM article_tickers WHERE article_id=?", (art_id,))
        cnt_after = cur.fetchone()["cnt_after"]
        inserted = (cnt_before == 0 and cnt_after > 0)
        # if mark_posted True and posted flag not yet set, update
        if mark_posted:
            cur.execute("UPDATE articles SET posted=1 WHERE id=?", (art_id,))
            conn.commit()
    except Exception:
        logger.exception("save_article_and_link failed.")
        conn.rollback()
        art_id = -1
    finally:
        conn.close()
    return art_id, inserted

def mark_article_posted_by_hash(art_hash: str):
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE articles SET posted=1 WHERE hash=?", (art_hash,))
        conn.commit()
    except Exception:
        logger.exception("mark_article_posted_by_hash failed.")
    finally:
        conn.close()

def get_tickers_for_article_by_hash(art_hash: str) -> List[str]:
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT at.ticker FROM article_tickers at
        JOIN articles a ON a.id = at.article_id
        WHERE a.hash = ?
    """, (art_hash,))
    rows = cur.fetchall()
    conn.close()
    return [r["ticker"] for r in rows] if rows else []

# ---------------------------
# Scoring
# ---------------------------
def score_text(text: str) -> float:
    if not text:
        return 0.0
    s = 0.0
    text_l = text.lower()
    for kw, w in keyword_weights.items():
        start = 0
        count = 0
        while True:
            idx = text_l.find(kw, start)
            if idx == -1:
                break
            count += 1
            start = idx + len(kw)
        if count:
            s += count * w
    return s

def weighted_severity(article: Dict[str, Any]) -> Tuple[str, float]:
    title = article.get("title", "") or ""
    desc = article.get("description", "") or ""
    content = article.get("content", "") or ""
    text_blob = " ".join([title, desc, content])
    score = score_text(text_blob)
    if score >= HIGH_THRESHOLD:
        return "HIGH", score
    elif score >= MED_THRESHOLD:
        return "MED", score
    else:
        return "LOW", score

# ---------------------------
# MarketAux fetch
# ---------------------------
def marketaux_fetch_batch(symbols: List[str], published_after: str, page: int = 1) -> Tuple[List[dict], Optional[dict]]:
    base_url = "https://api.marketaux.com/v1/news/all"
    params = {
        "symbols": ",".join(symbols),
        "published_after": published_after,
        "page": page,
        "language": "en",
    }
    headers = {"User-Agent": "mvp_alerts/2.4"}
    params["api_token"] = MARKETAUX_API_KEY
    resp, j = safe_request_get(base_url, params, headers=headers)
    if resp is None:
        logger.warning("marketaux_fetch_batch: No response (network error).")
        return [], None
    if resp.status_code != 200:
        try:
            parsed = resp.json()
        except Exception:
            parsed = {"error": {"code": str(resp.status_code), "message": resp.text}}
        logger.warning(f"MarketAux HTTP {resp.status_code}: {parsed}")
        return [], parsed
    try:
        if isinstance(j, dict) and "data" in j:
            articles = j["data"]
        elif isinstance(j, dict) and "news" in j:
            articles = j["news"]
        elif isinstance(j, list):
            articles = j
        else:
            articles = j.get("articles") if isinstance(j, dict) else []
            if articles is None:
                articles = []
        return articles, j
    except Exception:
        logger.exception("Failed to parse MarketAux JSON response.")
        return [], j

# ---------------------------
# Cooldown manager
# ---------------------------
class CooldownManager:
    def __init__(self, cooldown_minutes: int = SMART_COOLDOWN_MINUTES):
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self.last_posted: Dict[str, datetime] = {}

    def can_post(self, ticker: str) -> bool:
        t = self.last_posted.get(ticker)
        if t is None:
            return True
        if now_utc() - t >= self.cooldown:
            return True
        return False

    def mark_posted(self, ticker: str):
        self.last_posted[ticker] = now_utc()

# ---------------------------
# Extended Matching v2 (unchanged but included)
# ---------------------------
def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[lb]

def _normalize_text(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()

def _url_tokens(url: str) -> List[str]:
    tokens = re.split(r"[\-_/\.\?=&]+", url or "")
    return [t.lower() for t in tokens if t]

def detect_tickers_extended(article: Dict[str, Any], batch: List[str], company_map: Dict[str, str]) -> List[str]:
    title = (article.get("title") or "")
    desc = (article.get("description") or "")
    content = (article.get("content") or "")
    url = (article.get("url") or article.get("link") or "")
    text_full = " ".join([title, desc, content])

    # TIER 1: direct tickers from MarketAux
    tks = []
    if isinstance(article.get("tickers"), list) and article.get("tickers"):
        for t in article.get("tickers"):
            ut = t.upper()
            if ut in batch:
                tks.append(ut)
        if tks:
            if EXT_MATCH_LOG_TIER:
                logger.info(f"Detected tickers via MarketAux field: {tks} (tier 1)")
            return list(dict.fromkeys(tks))

    title_n = _normalize_text(title)
    desc_n = _normalize_text(desc)
    text_n = _normalize_text(text_full)
    url_n = (url or "").lower()
    url_tokens = _url_tokens(url_n)

    matched = set()

    def company_name_for(ticker: str) -> str:
        return (company_map.get(ticker.upper()) or "").strip()

    # TIER 2: exact company name in title or description
    for t in batch:
        name = company_name_for(t)
        if not name:
            continue
        name_n = _normalize_text(name)
        if name_n and (name_n in title_n or name_n in desc_n):
            matched.add(t.upper())
    if matched:
        if EXT_MATCH_LOG_TIER:
            logger.info(f"Matched by exact company name in title/desc: {sorted(matched)} (tier 2)")
        return sorted(matched)

    # TIER 3: run-together / partial name match (remove spaces)
    for t in batch:
        name = company_name_for(t)
        if not name:
            continue
        name_compact = re.sub(r"\s+", "", name.lower())
        if name_compact and (name_compact in title.lower().replace(" ", "") or name_compact in desc.lower().replace(" ", "")):
            matched.add(t.upper())
    if matched:
        if EXT_MATCH_LOG_TIER:
            logger.info(f"Matched by run-together company name: {sorted(matched)} (tier 3)")
        return sorted(matched)

    # TIER 4: token presence — all significant tokens from company name must appear somewhere
    for t in batch:
        name = company_name_for(t)
        if not name:
            continue
        tokens = [tok for tok in re.split(r"\s+", name.lower()) if tok]
        if not tokens:
            continue
        found_all = True
        for tok in tokens:
            if tok in title_n or tok in desc_n or tok in text_n or tok in " ".join(url_tokens):
                continue
            else:
                found_all = False
                break
        if found_all:
            matched.add(t.upper())
    if matched:
        if EXT_MATCH_LOG_TIER:
            logger.info(f"Matched by token presence of full company name: {sorted(matched)} (tier 4)")
        return sorted(matched)

    # TIER 5: fuzzy token matching (Levenshtein) on tokens >= FUZZY_MIN_TOKEN_LEN
    for t in batch:
        name = company_name_for(t)
        if not name:
            continue
        tokens = [tok for tok in re.split(r"\s+", name.lower()) if tok]
        good = False
        for tok in tokens:
            if len(tok) < FUZZY_MIN_TOKEN_LEN:
                continue
            title_tokens = [w for w in re.split(r"[^a-z0-9]+", title.lower()) if w]
            for wt in title_tokens:
                dist = levenshtein(tok, wt)
                if dist <= FUZZY_MAX_DISTANCE:
                    good = True
                    break
            if good:
                break
            for ut in url_tokens:
                dist = levenshtein(tok, ut)
                if dist <= FUZZY_MAX_DISTANCE:
                    good = True
                    break
            if good:
                break
        if good:
            matched.add(t.upper())
    if matched:
        if EXT_MATCH_LOG_TIER:
            logger.info(f"Matched by fuzzy token similarity: {sorted(matched)} (tier 5)")
        return sorted(matched)

    # TIER 6: ticker word-boundary match in text
    for t in batch:
        pat = r"\b" + re.escape(t.upper()) + r"\b"
        if re.search(pat, title.upper()) or re.search(pat, desc.upper()) or re.search(pat, content.upper()):
            matched.add(t.upper())
    if matched:
        if EXT_MATCH_LOG_TIER:
            logger.info(f"Matched by ticker word-boundary in text: {sorted(matched)} (tier 6)")
        return sorted(matched)

    # TIER 7: URL token direct match
    for t in batch:
        if t.lower() in url_tokens:
            matched.add(t.upper())
            continue
        name = company_name_for(t)
        if not name:
            continue
        name_tokens = [tok for tok in re.split(r"\s+", name.lower()) if tok]
        for nt in name_tokens:
            if nt in url_tokens or nt.replace(" ", "") in url_tokens:
                matched.add(t.upper())
                break
    if matched:
        if EXT_MATCH_LOG_TIER:
            logger.info(f"Matched by URL token matching: {sorted(matched)} (tier 7)")
        return sorted(matched)

    # FINAL fallback (tier 8)
    fallback = batch[0].upper() if batch else ""
    if fallback:
        if EXT_MATCH_LOG_TIER:
            logger.info(f"No tickers detected — assigning fallback {fallback} (tier 8)")
        return [fallback]
    return []

# ---------------------------
# Presentation helpers
# ---------------------------
def normalize_company_name(ticker: str, company_map: Dict[str, str]) -> str:
    name = company_map.get(ticker.upper())
    if not name:
        return ticker.upper()
    return name

def build_article_summary(tickers: List[str], company_map: Dict[str, str], severity: str, score: float, article: Dict[str, Any]) -> str:
    title = article.get("title") or ""
    url = article.get("url") or article.get("link") or ""
    tickers_str = ",".join(sorted(set([t.upper() for t in tickers])))
    companies = [normalize_company_name(t, company_map) for t in tickers]
    companies_str = ",".join(companies)
    return f"{tickers_str} | {severity} | {score:.2f} — {companies_str} — {title} {url}"

# ---------------------------
# System diagnostics
# ---------------------------
def system_diagnostics(watchlist: List[str], company_map: Dict[str, str]):
    try:
        logger.info("=== System Diagnostics ===")
        logger.info(f"Python: {platform.python_version()}")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"MARKETAUX_API_KEY: {'SET' if MARKETAUX_API_KEY else 'MISSING'}")
        logger.info(f"DISCORD_WEBHOOK_URL: {'SET' if DISCORD_WEBHOOK_URL else 'MISSING'}")
        logger.info(f"Watchlist Count: {len(watchlist)}")
        logger.info(f"Company Map Count: {len(company_map)}")
        # DB health
        try:
            conn = connect_db()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(1) as cnt FROM articles")
            cnt = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(1) as cnt2 FROM article_tickers")
            cnt2 = cur.fetchone()["cnt2"]
            conn.close()
            logger.info(f"DB articles: {cnt}, article_tickers: {cnt2}")
        except Exception as e:
            logger.warning(f"DB diagnostic failed: {e}")
        logger.info(f"Log file: {LOG_FILE}")
        logger.info("==========================")
    except Exception:
        logger.exception("Failed to run system diagnostics")

# ---------------------------
# Main flow
# ---------------------------
def chunk_list(lst: List[str], n: int) -> List[List[str]]:
    return [lst[i:i + n] for i in range(0, len(lst), n)]

def main_loop():
    if not MARKETAUX_API_KEY:
        logger.error("MARKETAUX_API_KEY not set. Export it to the environment and restart.")
        return
    watchlist = load_watchlist()
    if not watchlist:
        logger.error("Watchlist empty. Add tickers to watchlist.txt and restart.")
        return
    company_map = load_company_map()
    cooldown_mgr = CooldownManager()

    # Initialize / migrate DB
    init_and_migrate_db()

    # Diagnostics
    system_diagnostics(watchlist, company_map)

    last_ts = read_last_timestamp()
    if last_ts:
        try:
            last_dt = dateutil_parser.parse(last_ts)
            logger.info(f"Resuming from last_timestamp: {last_ts}")
        except Exception:
            last_dt = now_utc() - timedelta(hours=COLD_START_HOURS)
            logger.warning("Invalid last_timestamp; falling back to cold start window.")
    else:
        last_dt = now_utc() - timedelta(hours=COLD_START_HOURS)
        logger.info(f"No last_timestamp found. Cold start will use {COLD_START_HOURS} hours.")

    cycle_count = 0
    while True:
        cycle_count += 1
        logger.info(f"========== Bot 2.4 Startup ==========" if cycle_count == 1 else f"=== Cycle #{cycle_count} startup ===")
        logger.info("SQLite MED DB ready.")
        watchlist = load_watchlist()
        total_tickers = len(watchlist)
        logger.info(f"Cycle composition: {total_tickers} personal + 0 random = {total_tickers} total.")
        published_after_candidates = try_multiple_ts_formats(last_dt)
        batches = chunk_list(watchlist, BATCH_SIZE)
        fetched_total = 0
        kept_total = 0
        posted_total = 0
        cycle_end_ts = format_timestamp_z(now_utc())
        logger.info(f"Starting news scan cycle. published_after candidates: {published_after_candidates[0]}")

        for batch_idx, batch in enumerate(batches, start=1):
            batch_articles: List[Dict[str, Any]] = []
            raw_response = None
            success = False
            for pa in published_after_candidates:
                logger.info(f"Outbound URL: https://api.marketaux.com/v1/news/all?symbols={','.join(batch)}&published_after={pa}&page=1")
                articles, raw_response = marketaux_fetch_batch(batch, pa, page=1)
                if raw_response and isinstance(raw_response, dict) and raw_response.get("error"):
                    code = raw_response["error"].get("code")
                    msg = raw_response["error"].get("message", "")
                    if code in ("malformed_parameters", "malformed_parameter", "invalid_request") or ("published_after" in msg.lower()):
                        logger.warning(f"MarketAux HTTP 400-like: {raw_response} — trying next timestamp format.")
                        continue
                if articles is not None:
                    batch_articles = articles
                    success = True
                    break
            if not success:
                logger.warning("Batch fetch failed or returned no data; continuing to next batch.")
                continue

            fetched = len(batch_articles)
            fetched_total += fetched
            logger.info(f"Fetched {fetched} articles for batch ({','.join(batch)})")

            kept_in_batch = 0
            posted_in_batch = 0

            for art in batch_articles:
                title = art.get("title", "") or ""
                desc = art.get("description", "") or ""
                url = art.get("url", "") or art.get("link", "") or ""
                published_at = art.get("published_at") or art.get("published_at_local") or ""
                content = art.get("content", "") or ""

                article_tickers = detect_tickers_extended(art, batch, company_map)
                if not article_tickers:
                    article_tickers = [batch[0].upper()] if batch else []

                # Compute severity & score
                severity, score = weighted_severity(art)

                # Canonical hash
                art_hash = canonical_article_hash(title, url, published_at or "")

                # Check if article already exists
                existing = find_article_by_hash(art_hash)
                existing_posted = bool(existing["posted"]) if existing else False

                # Save / link article (for MED and HIGH we persist)
                if severity == "HIGH":
                    # For HIGH: if article already posted, skip posting; else we post once including all tickers
                    if existing and existing_posted:
                        logger.info(f"HIGH article already posted (hash): skipping post. {title[:80]}")
                        # Ensure tickers are linked
                        _, _ = save_article_and_link(title, desc, url, severity, score, published_at or "", article_tickers, mark_posted=False)
                        kept_in_batch += 1
                    else:
                        # Save, link, post
                        # If existing but not yet posted, gather previously-linked tickers to include them in post
                        linked_tickers = get_tickers_for_article_by_hash(art_hash) if existing else []
                        combined_tickers = sorted(set([t.upper() for t in (linked_tickers + article_tickers)]))
                        summary = build_article_summary(combined_tickers, company_map, "HIGH", score, art)
                        success_post = post_to_discord(summary)
                        if success_post:
                            # Save and mark posted
                            art_id, _ = save_article_and_link(title, desc, url, "HIGH", score, published_at or "", combined_tickers, mark_posted=True)
                            posted_in_batch += 1
                            logger.info(f"Posted HIGH: tickers={combined_tickers} title={title[:80]}")
                        else:
                            # Save but don't mark posted
                            art_id, _ = save_article_and_link(title, desc, url, "HIGH", score, published_at or "", combined_tickers, mark_posted=False)
                            logger.info(f"Saved HIGH (not posted): tickers={combined_tickers} title={title[:80]}")
                        kept_in_batch += 1

                elif severity == "MED":
                    # Save MED once (if duplicate, it will link tickers)
                    art_id, inserted_flag = save_article_and_link(title, desc, url, "MED", score, published_at or "", article_tickers, mark_posted=False)
                    logger.info(f"MED saved to DB: {','.join(article_tickers)} | {score:.2f} — {title[:120]}")
                    kept_in_batch += 1

                else:  # LOW
                    # For LOW we don't save unless you want to; keep previous behavior (skip)
                    logger.debug(f"LOW: {','.join(article_tickers)} - {title[:120]}")
                    # Optionally link low articles? Currently skip saving.
                    # If you want to persist LOW, call save_article_and_link similarly.
                    # kept_in_batch unchanged

            kept_total += kept_in_batch
            posted_total += posted_in_batch
            logger.info(f"Batch {batch_idx}/{len(batches)} result: fetched={fetched} kept={kept_in_batch} posted={posted_in_batch}")
            time.sleep(0.2)

        logger.info(f"Cycle summary: fetched={fetched_total} kept={kept_total} posted={posted_total}")
        write_last_timestamp(cycle_end_ts)
        logger.info(f"Cycle {cycle_count} completed ... (stored last_timestamp={cycle_end_ts})")
        logger.info(f"Sleeping {CYCLE_SECONDS}s until next cycle.")
        time.sleep(CYCLE_SECONDS)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received — shutting down.")
    except Exception:
        logger.exception("Unhandled exception — shutting down.")