function DashboardPage() {
  const { user, logout } = useAuth();
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [selectedWatchlist, setSelectedWatchlist] = useState<number | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [wlData, statsData] = await Promise.all([
        api.getWatchlists(),
        api.getArticleStats()
      ]);
      setWatchlists(wlData.watchlists);
      setStats(statsData);
      if (wlData.watchlists.length > 0 && !selectedWatchlist) {
        setSelectedWatchlist(wlData.watchlists[0].id);
      }
    } catch (error) {
      console.error('Failed to load data', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedWatchlist) {
      loadArticles();
    }
  }, [selectedWatchlist]);

  const loadArticles = async () => {
    try {
      const data = await api.getArticles({ page: 1, page_size: 50 });
      setArticles(data.articles);
    } catch (error) {
      console.error('Failed to load articles', error);
    }
  };

  const handleScan = async () => {
    if (!selectedWatchlist) return;
    setScanning(true);
    try {
      await api.triggerScan(selectedWatchlist);
      alert('Scan started! Refresh in a few moments to see results.');
    } catch (error: any) {
      alert(error.message);
    } finally {
      setScanning(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-blue-600">YourStockNews</h1>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">{user?.email}</span>
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                {user?.plan.toUpperCase()}
              </span>
              <button
                onClick={logout}
                className="text-gray-600 hover:text-gray-800 text-sm font-medium"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <div className="text-3xl font-bold text-gray-900">{stats.total}</div>
              <div className="text-sm text-gray-500 mt-1">Total Alerts</div>
            </div>
            <div className="bg-red-50 rounded-xl shadow-sm p-6 border border-red-200">
              <div className="text-3xl font-bold text-red-600">{stats.high}</div>
              <div className="text-sm text-red-700 mt-1">High Severity</div>
            </div>
            <div className="bg-yellow-50 rounded-xl shadow-sm p-6 border border-yellow-200">
              <div className="text-3xl font-bold text-yellow-600">{stats.med}</div>
              <div className="text-sm text-yellow-700 mt-1">Medium Severity</div>
            </div>
            <div className="bg-blue-50 rounded-xl shadow-sm p-6 border border-blue-200">
              <div className="text-3xl font-bold text-blue-600">{stats.unread}</div>
              <div className="text-sm text-blue-700 mt-1">Unread</div>
            </div>
          </div>
        )}

        {/* Watchlist Selector & Scan Button */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">Watchlist:</label>
              <select
                value={selectedWatchlist || ''}
                onChange={(e) => setSelectedWatchlist(Number(e.target.value))}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                {watchlists.map(wl => (
                  <option key={wl.id} value={wl.id}>
                    {wl.name} ({wl.tickers.length} tickers)
                  </option>
                ))}
              </select>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition"
              >
                + New Watchlist
              </button>
            </div>
            <button
              onClick={handleScan}
              disabled={scanning || !selectedWatchlist}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50"
            >
              {scanning ? 'Scanning...' : '🔍 Scan Now'}
            </button>
          </div>
        </div>

        {/* Articles Table */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Recent Alerts</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Severity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tickers
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {articles.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                      No alerts yet. Click "Scan Now" to fetch news.
                    </td>
                  </tr>
                ) : (
                  articles.map(article => (
                    <tr key={article.id} className="hover:bg-gray-50 cursor-pointer">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                          article.severity === 'HIGH' ? 'bg-red-100 text-red-800' :
                          article.severity === 'MED' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {article.severity}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline font-medium"
                        >
                          {article.title}
                        </a>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-1 flex-wrap">
                          {article.tickers.slice(0, 3).map(ticker => (
                            <span key={ticker} className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
                              {ticker}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {article.score.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {new Date(article.detected_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Create Watchlist Modal */}
      {showCreateModal && (
        <CreateWatchlistModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            loadData();
          }}
        />
      )}
    </div>
  );
}