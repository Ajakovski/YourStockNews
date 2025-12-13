-- ============================================================================
-- YourStockNews - Multi-Tenant SaaS Schema Migration
-- Version: 002
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Modify existing tables for multi-tenancy
-- ----------------------------------------------------------------------------

-- Add user/watchlist tracking to articles
ALTER TABLE articles ADD COLUMN user_id INTEGER;
ALTER TABLE articles ADD COLUMN watchlist_id INTEGER;

-- Add user/watchlist tracking to article_tickers
ALTER TABLE article_tickers ADD COLUMN user_id INTEGER;
ALTER TABLE article_tickers ADD COLUMN watchlist_id INTEGER;

-- ----------------------------------------------------------------------------
-- 2. Create core user tables
-- ----------------------------------------------------------------------------

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Watchlists table
CREATE TABLE IF NOT EXISTS watchlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Watchlist tickers (many-to-many relationship)
CREATE TABLE IF NOT EXISTS watchlist_tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (watchlist_id, ticker),
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 3. Scan job tracking
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS scan_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    watchlist_id INTEGER NOT NULL,
    status TEXT CHECK(status IN ('pending', 'running', 'success', 'failed')) NOT NULL,
    started_at DATETIME,
    finished_at DATETIME,
    articles_found INTEGER DEFAULT 0,
    last_timestamp TEXT,
    error_message TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 4. Subscription & billing tables
-- ----------------------------------------------------------------------------

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    plan TEXT NOT NULL DEFAULT 'free',
    status TEXT CHECK(status IN ('active', 'canceled', 'expired', 'past_due')) NOT NULL DEFAULT 'active',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    current_period_end DATETIME,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Usage limits by plan
CREATE TABLE IF NOT EXISTS usage_limits (
    plan TEXT PRIMARY KEY,
    max_watchlists INTEGER NOT NULL,
    max_tickers_per_watchlist INTEGER NOT NULL,
    max_scans_per_day INTEGER NOT NULL,
    article_history_days INTEGER NOT NULL,
    webhooks_enabled INTEGER DEFAULT 0,
    api_access_enabled INTEGER DEFAULT 0
);

-- ----------------------------------------------------------------------------
-- 5. Indexes for performance
-- ----------------------------------------------------------------------------

-- Articles indexes
CREATE INDEX IF NOT EXISTS idx_articles_user ON articles(user_id);
CREATE INDEX IF NOT EXISTS idx_articles_watchlist ON articles(watchlist_id);
CREATE INDEX IF NOT EXISTS idx_articles_user_watchlist ON articles(user_id, watchlist_id);
CREATE INDEX IF NOT EXISTS idx_articles_hash_user ON articles(hash, user_id, watchlist_id);
CREATE INDEX IF NOT EXISTS idx_articles_severity ON articles(severity);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_articles_posted ON articles(posted);

-- Article tickers indexes
CREATE INDEX IF NOT EXISTS idx_article_tickers_article ON article_tickers(article_id);
CREATE INDEX IF NOT EXISTS idx_article_tickers_ticker ON article_tickers(ticker);
CREATE INDEX IF NOT EXISTS idx_article_tickers_user ON article_tickers(user_id, watchlist_id);

-- Watchlists indexes
CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists(user_id);

-- Watchlist tickers indexes
CREATE INDEX IF NOT EXISTS idx_watchlist_tickers_watchlist ON watchlist_tickers(watchlist_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_tickers_ticker ON watchlist_tickers(ticker);

-- Scan jobs indexes
CREATE INDEX IF NOT EXISTS idx_scan_jobs_user ON scan_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_watchlist ON scan_jobs(watchlist_id);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_status ON scan_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_started ON scan_jobs(started_at);

-- Subscriptions indexes
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_plan ON subscriptions(plan);

-- ----------------------------------------------------------------------------
-- 6. Seed data for usage limits
-- ----------------------------------------------------------------------------

INSERT OR REPLACE INTO usage_limits 
(plan, max_watchlists, max_tickers_per_watchlist, max_scans_per_day, article_history_days, webhooks_enabled, api_access_enabled)
VALUES
    ('free',       1,   10,   5,   7,   0, 0),
    ('pro',       10,   50, 100,  90,   1, 0),
    ('enterprise', 999, 500, 1000, 365,  1, 1);

-- ----------------------------------------------------------------------------
-- 7. Create default admin user (password: change_me_123)
-- ----------------------------------------------------------------------------

-- Password hash for 'change_me_123' using bcrypt
-- This should be changed immediately after first login
INSERT OR IGNORE INTO users (id, email, password_hash, is_active)
VALUES (
    1,
    'admin@yourstocknews.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND.LQ.JqKq5u',
    1
);

-- Create default watchlist for admin
INSERT OR IGNORE INTO watchlists (id, user_id, name)
VALUES (1, 1, 'Default Watchlist');

-- Create default subscription for admin
INSERT OR IGNORE INTO subscriptions (user_id, plan, status)
VALUES (1, 'enterprise', 'active');

-- ----------------------------------------------------------------------------
-- END OF MIGRATION
-- ============================================================================