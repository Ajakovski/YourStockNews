#!/usr/bin/env python3
"""
YourStockNews.py
v1.0.0 - SaaS-compatible single-run scanner

Stateless, multi-user, web-app safe.
"""

import re
import hashlib
import sqlite3
import requests
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone

# ============================================================================
# Configuration
# ============================================================================

# Severity thresholds (can later be per-user / per-plan)
HIGH_THRESHOLD = 2.75
MED_THRESHOLD = 1.25
BATCH_SIZE = 10

# ============================================================================
# Keyword scoring (UNCHANGED)
# ============================================================================

keyword_weights = {
    "acquir": 1.5, "acquisition": 1.5, "acquired": 1.5, "merger": 1.5,
    "lawsuit": 2.0, "settlement": 1.8, "investigation": 1.8,
    "bankrupt": 3.0, "bankruptcy": 3.0,
    "earnings": 2.0, "beats": 1.8, "misses": 1.8,
    "resign": 1.8, "ceo": 1.0, "cfo": 1.0,
    "recall": 2.5, "fraud": 3.0,
}
keyword_weights = {k.lower(): v for k, v in keyword_weights.items()}

# ============================================================================
# Utility helpers
# ============================================================================

def now_utc() -> str:
    """Return current UTC timestamp in ISO 8601 format"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def normalize_text(s: str) -> str:
    """Normalize text for comparison"""
    return re.sub(r"\s+", " ", (s or "").strip()).lower()

def canonical_article_hash(title: str, url: str, published_at: str) -> str:
    """Generate unique hash for deduplication"""
    base = "|".join([
        normalize_text(title),
        normalize_text(url),
        normalize_text(published_at)
    ])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

# ============================================================================
# Database operations
# ============================================================================

def connect_db(db_path: str):
    """Connect to SQLite database"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def save_article(
    *,
    user_id: int,
    watchlist_id: int,
    title: str,
    description: str,
    url: str,
    severity: str,
    score: float,
    published_at: str,
    tickers: List[str],
    mark_posted: bool,
    db_path: str
) -> int:
    """Save article to database with transaction safety"""
    art_hash = canonical_article_hash(title, url, published_at)
    
    conn = connect_db(db_path)
    conn.execute("BEGIN TRANSACTION")
    
    try:
        cur = conn.cursor()
        
        # Insert article
        cur.execute("""
            INSERT OR IGNORE INTO articles
            (user_id, watchlist_id, title, description, url,
             severity, score, hash, published_at, detected_at, posted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
        """, (
            user_id, watchlist_id, title, description, url,
            severity, score, art_hash, published_at, 1 if mark_posted else 0
        ))
        
        # Get article ID
        cur.execute("""
            SELECT id FROM articles 
            WHERE hash=? AND user_id=? AND watchlist_id=?
        """, (art_hash, user_id, watchlist_id))
        
        row = cur.fetchone()
        if not row:
            conn.rollback()
            conn.close()
            raise ValueError("Failed to retrieve article ID after insert")
        
        art_id = row["id"]
        
        # Insert tickers
        for t in tickers:
            cur.execute("""
                INSERT OR IGNORE INTO article_tickers
                (article_id, ticker, user_id, watchlist_id)
                VALUES (?, ?, ?, ?)
            """, (art_id, t.upper(), user_id, watchlist_id))
        
        conn.commit()
        return art_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ============================================================================
# Scoring logic (UNCHANGED)
# ============================================================================

def score_text(text: str) -> float:
    """Calculate keyword score for text"""
    if not text:
        return 0.0
    s = 0.0
    text_l = text.lower()
    for kw, w in keyword_weights.items():
        s += text_l.count(kw) * w
    return s

def weighted_severity(article: Dict[str, Any]) -> Tuple[str, float]:
    """Calculate severity and score for article"""
    blob = " ".join([
        article.get("title", ""),
        article.get("description", ""),
        article.get("content", "")
    ])
    score = score_text(blob)
    
    if score >= HIGH_THRESHOLD:
        return "HIGH", score
    elif score >= MED_THRESHOLD:
        return "MED", score
    return "LOW", score

# ============================================================================
# MarketAux API client
# ============================================================================

def marketaux_fetch(
    symbols: List[str],
    api_key: str,
    published_after: Optional[str]
) -> List[dict]:
    """Fetch news from MarketAux API"""
    url = "https://api.marketaux.com/v1/news/all"
    params = {
        "symbols": ",".join(symbols),
        "language": "en",
        "api_token": api_key,
        "filter_entities": "true"  # Recommended by docs
    }
    
    # Convert ISO timestamp to YYYY-MM-DD format if provided
    if published_after:
        # Extract date part only (MarketAux expects YYYY-MM-DD, not full ISO)
        if "T" in published_after:
            params["published_after"] = published_after.split("T")[0]
        else:
            params["published_after"] = published_after
    
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("data") or []

# ============================================================================
# MAIN ENTRY POINT - SaaS-safe single scan
# ============================================================================

def run_single_scan(
    user_id: int,
    watchlist_id: int,
    tickers: List[str],
    api_key: str,
    last_timestamp: str = None,
    db_path: str = 'med_alerts.db'
) -> Dict[str, Any]:
    """
    Run a single news scan for given tickers.
    
    Args:
        user_id: Database user ID
        watchlist_id: Database watchlist ID
        tickers: List of ticker symbols (e.g., ['AAPL', 'GOOGL'])
        api_key: MarketAux API key (provided by backend)
        last_timestamp: ISO timestamp of last scan (e.g., '2024-01-15T10:30:00Z')
        db_path: Path to SQLite database file
    
    Returns:
        {
            "status": "success" | "error",
            "articles_found": int,
            "articles": [
                {
                    "title": str,
                    "description": str,
                    "url": str,
                    "severity": "HIGH" | "MED" | "LOW",
                    "score": float,
                    "tickers": [str],
                    "published_at": str,
                    "hash": str
                }
            ],
            "last_timestamp": str,
            "severity_counts": {"HIGH": int, "MED": int, "LOW": int},
            "error": str  # Only if status == "error"
        }
    """
    
    try:
        # Validate inputs
        if not tickers:
            return {
                "status": "error",
                "error": "No tickers provided",
                "articles_found": 0,
                "articles": [],
                "severity_counts": {"HIGH": 0, "MED": 0, "LOW": 0},
                "last_timestamp": last_timestamp or "1970-01-01T00:00:00Z"
            }
        
        if not api_key:
            return {
                "status": "error",
                "error": "No API key provided",
                "articles_found": 0,
                "articles": [],
                "severity_counts": {"HIGH": 0, "MED": 0, "LOW": 0},
                "last_timestamp": last_timestamp or "1970-01-01T00:00:00Z"
            }
        
        # Initialize counters
        fetched_total = 0
        articles_out = []
        severity_counts = {"HIGH": 0, "MED": 0, "LOW": 0}
        max_published_at = last_timestamp or "1970-01-01T00:00:00Z"
        
        # Process in batches
        for i in range(0, len(tickers), BATCH_SIZE):
            batch = tickers[i:i + BATCH_SIZE]
            articles = marketaux_fetch(batch, api_key, last_timestamp)
            fetched_total += len(articles)
            
            for art in articles:
                severity, score = weighted_severity(art)
                
                # Skip LOW severity articles
                if severity == "LOW":
                    continue
                
                # Extract article data
                title = art.get("title", "")
                desc = art.get("description", "")
                url = art.get("url") or art.get("link") or ""
                published_at = art.get("published_at") or ""
                matched = art.get("tickers") or batch
                
                # Track newest timestamp
                if published_at > max_published_at:
                    max_published_at = published_at
                
                # Save to database
                try:
                    save_article(
                        user_id=user_id,
                        watchlist_id=watchlist_id,
                        title=title,
                        description=desc,
                        url=url,
                        severity=severity,
                        score=score,
                        published_at=published_at,
                        tickers=matched,
                        mark_posted=(severity == "HIGH"),
                        db_path=db_path
                    )
                    
                    # Add to output
                    severity_counts[severity] += 1
                    articles_out.append({
                        "title": title,
                        "description": desc,
                        "url": url,
                        "severity": severity,
                        "score": round(score, 2),
                        "tickers": matched,
                        "published_at": published_at,
                        "hash": canonical_article_hash(title, url, published_at)
                    })
                    
                except Exception as save_error:
                    # Log but continue processing other articles
                    continue
        
        # Return success response
        return {
            "status": "success",
            "articles_found": len(articles_out),
            "articles": articles_out,
            "last_timestamp": max_published_at,
            "severity_counts": severity_counts
        }
    
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error": f"MarketAux API error: {str(e)}",
            "articles_found": 0,
            "articles": [],
            "severity_counts": {"HIGH": 0, "MED": 0, "LOW": 0},
            "last_timestamp": last_timestamp or "1970-01-01T00:00:00Z"
        }
    
    except sqlite3.Error as e:
        return {
            "status": "error",
            "error": f"Database error: {str(e)}",
            "articles_found": 0,
            "articles": [],
            "severity_counts": {"HIGH": 0, "MED": 0, "LOW": 0},
            "last_timestamp": last_timestamp or "1970-01-01T00:00:00Z"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "articles_found": 0,
            "articles": [],
            "severity_counts": {"HIGH": 0, "MED": 0, "LOW": 0},
            "last_timestamp": last_timestamp or "1970-01-01T00:00:00Z"
        }


# ============================================================================
# Test runner (optional, for local testing)
# ============================================================================

if __name__ == "__main__":
    import os
    
    # Test with sample data
    result = run_single_scan(
        user_id=1,
        watchlist_id=1,
        tickers=["AAPL", "GOOGL"],
        api_key=os.getenv("MARKETAUX_API_KEY", "9Ydp4VNIm9zZ6WHmVcys40L9gUlUWOKW6ZYFxX2T"),
        last_timestamp="2024-12-01T00:00:00Z",
        db_path="test_alerts.db"
    )
    
    print(f"Status: {result['status']}")
    print(f"Articles found: {result['articles_found']}")
    print(f"Severity counts: {result['severity_counts']}")
    if result['status'] == 'error':
        print(f"Error: {result['error']}")