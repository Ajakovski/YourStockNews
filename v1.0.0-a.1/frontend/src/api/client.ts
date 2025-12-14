import { User, Watchlist, Article, ArticleStats, ScanJob, AuthTokens } from '../types';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

class ApiClient {
  private getHeaders(): HeadersInit {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` })
    };
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: this.getHeaders()
    });

    if (response.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Request failed');
    }
    return data;
  }

  // Authentication
  async login(email: string, password: string): Promise<AuthTokens> {
    const data = await this.request<AuthTokens>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data;
  }

  async register(email: string, password: string): Promise<AuthTokens> {
    const data = await this.request<AuthTokens>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data;
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/users/me');
  }

  // Watchlists
  async getWatchlists(): Promise<{ watchlists: Watchlist[]; total: number }> {
    return this.request<{ watchlists: Watchlist[]; total: number }>('/watchlists');
  }

  async createWatchlist(name: string, tickers: string[]): Promise<Watchlist> {
    return this.request<Watchlist>('/watchlists', {
      method: 'POST',
      body: JSON.stringify({ name, tickers })
    });
  }

  async deleteWatchlist(id: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/watchlists/${id}`, { 
      method: 'DELETE' 
    });
  }

  async addTicker(watchlistId: number, ticker: string): Promise<Watchlist> {
    return this.request<Watchlist>(`/watchlists/${watchlistId}/tickers`, {
      method: 'POST',
      body: JSON.stringify({ ticker })
    });
  }

  async removeTicker(watchlistId: number, ticker: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/watchlists/${watchlistId}/tickers/${ticker}`,
      { method: 'DELETE' }
    );
  }

  // Articles
  async getArticles(params: Record<string, any> = {}): Promise<{
    articles: Article[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    const query = new URLSearchParams(params).toString();
    return this.request(`/articles?${query}`);
  }

  async getArticleStats(): Promise<ArticleStats> {
    return this.request<ArticleStats>('/articles/stats');
  }

  async markArticleRead(id: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/articles/${id}/read`, { 
      method: 'PATCH' 
    });
  }

  // Scans
  async triggerScan(watchlistId: number): Promise<ScanJob> {
    return this.request<ScanJob>('/scans', {
      method: 'POST',
      body: JSON.stringify({ watchlist_id: watchlistId })
    });
  }

  async getScanHistory(): Promise<{ scan_jobs: ScanJob[]; total: number }> {
    return this.request<{ scan_jobs: ScanJob[]; total: number }>('/scans');
  }

  async getScanStatus(id: number): Promise<ScanJob> {
    return this.request<ScanJob>(`/scans/${id}`);
  }

  // Subscriptions
  async getSubscription(): Promise<{
    plan: string;
    status: string;
    current_period_end: string | null;
  }> {
    return this.request('/subscriptions/me');
  }
}

export const api = new ApiClient();