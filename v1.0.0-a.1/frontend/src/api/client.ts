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
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Request failed');
    }
    return data;
  }

  // Auth
  async login(email: string, password: string) {
    const data = await this.request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    localStorage.setItem('access_token', data.access_token);
    return data;
  }

  async register(email: string, password: string) {
    const data = await this.request<{ access_token: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    localStorage.setItem('access_token', data.access_token);
    return data;
  }

  async getCurrentUser() {
    return this.request<any>('/users/me');
  }

  // Watchlists
  async getWatchlists() {
    return this.request<{ watchlists: any[]; total: number }>('/watchlists');
  }

  async createWatchlist(name: string, tickers: string[]) {
    return this.request<any>('/watchlists', {
      method: 'POST',
      body: JSON.stringify({ name, tickers })
    });
  }

  async deleteWatchlist(id: number) {
    return this.request<any>(`/watchlists/${id}`, { method: 'DELETE' });
  }

  // Articles
  async getArticles(params: Record<string, any> = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request<any>(`/articles?${query}`);
  }

  async getArticleStats() {
    return this.request<any>('/articles/stats');
  }

  // Scans
  async triggerScan(watchlistId: number) {
    return this.request<any>('/scans', {
      method: 'POST',
      body: JSON.stringify({ watchlist_id: watchlistId })
    });
  }

  async getScanHistory() {
    return this.request<any>('/scans');
  }
}

export const api = new ApiClient();

