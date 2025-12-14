export interface User {
  id: number;
  email: string;
  plan: string;
  subscription_status: string;
  is_active: boolean;
  created_at: string;
}

export interface Watchlist {
  id: number;
  user_id: number;
  name: string;
  tickers: string[];
  created_at: string;
  updated_at: string;
}

export interface Article {
  id: number;
  title: string;
  description: string | null;
  url: string;
  severity: 'HIGH' | 'MED' | 'LOW';
  score: number;
  tickers: string[];
  published_at: string;
  detected_at: string;
  posted: number;
}

export interface ScanJob {
  id: number;
  user_id: number;
  watchlist_id: number;
  status: 'pending' | 'running' | 'success' | 'failed';
  started_at: string | null;
  finished_at: string | null;
  articles_found: number;
  error_message: string | null;
}

export interface ArticleStats {
  total: number;
  high: number;
  med: number;
  low: number;
  unread: number;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}