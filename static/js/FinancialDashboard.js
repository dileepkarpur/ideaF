const { useState } = React;

const formatPrice = (value) => {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
};

const formatCurrency = (value) => {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
    notation: 'compact'
  }).format(value);
};

const formatPercent = (value) => {
  if (value === null || value === undefined) return 'N/A';
  return `${value.toFixed(2)}%`;
};

const FinancialDashboard = () => {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);
  const [analysisType, setAnalysisType] = useState(null);
  const [analysisContent, setAnalysisContent] = useState('');
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!ticker) return;

    setLoading(true);
    setError('');
    setData(null);
    setAnalysisContent('');
    
    try {
      const response = await fetch(`/api/stock/${ticker.toUpperCase()}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to fetch data');
      }
      
      const result = await response.json();
      console.log("Fetched data:", result); // Debug log
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalysisClick = async (type) => {
    if (!data) return;

    setLoadingAnalysis(true);
    setAnalysisType(type);
    setAnalysisContent('');
    
    try {
      const endpoint = `/api/${type}`;
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate analysis');
      }

      const result = await response.json();
      setAnalysisContent(
        result[type === 'analyze' ? 'analysis' :
              type === 'predict' ? 'prediction' :
              'risk_assessment']
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const renderMetricCard = ({ title, value, previousValue = null, date = null, formatFn = formatCurrency }) => {
    const change = previousValue ? ((value - previousValue) / previousValue) * 100 : null;
    
    return (
      <div className="bg-white rounded-lg p-4 shadow-md">
        <h3 className="text-sm text-gray-600 font-medium">{title}</h3>
        <p className="text-2xl font-bold text-gray-900">
          {formatFn(value)}
        </p>
        {date && (
          <p className="text-xs text-gray-500 mt-1">
            As of {new Date(date).toLocaleDateString()}
          </p>
        )}
        {change !== null && !isNaN(change) && (
          <p className={`text-sm mt-1 ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {change >= 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <form onSubmit={handleSearch} className="mb-8">
        <div className="flex gap-4">
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="Enter stock ticker (e.g., AAPL)"
            className="flex-1 p-2 border rounded shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={loading || !ticker}
            className="bg-blue-600 text-white px-6 py-2 rounded shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-8">
          {error}
        </div>
      )}

      {data && (
        <div className="space-y-8">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-start">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {data.company_info.name} ({data.company_info.ticker})
                </h1>
                <p className="text-gray-600 mt-1">
                  {data.company_info.sector} | {data.company_info.industry}
                </p>
                <div className="flex gap-4 mt-2 text-sm text-gray-500">
                  <span>Market Cap: {formatCurrency(data.company_info.marketCap)}</span>
                  <span>EPS: {formatCurrency(data.company_info.eps)}</span>
                  <span>Employees: {data.company_info.employees.toLocaleString()}</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-gray-900">
                  {formatPrice(data.company_info.currentPrice)}
                </div>
                {data.company_info.priceChange && (
                  <div className={`text-lg ${data.company_info.priceChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {data.company_info.priceChange >= 0 ? '↑' : '↓'} 
                    {Math.abs(data.company_info.priceChange).toFixed(2)}%
                  </div>
                )}
                <div className="text-sm text-gray-500 mt-1">
                  Last Updated: {data.company_info.lastUpdated}
                </div>
              </div>
            </div>
          </div>

          {/* Quarterly Data Period */}
          <div className="bg-white rounded-lg shadow-md p-4">
            <h2 className="text-lg font-semibold mb-2">Financial Data Period</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Latest Quarter: </span>
                <span className="font-medium">{new Date(data.quarterly_data[0].date).toLocaleDateString()}</span>
              </div>
              <div>
                <span className="text-gray-600">Previous Quarter: </span>
                <span className="font-medium">{new Date(data.quarterly_data[1].date).toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {data.quarterly_data[0] && (
              <>
                {renderMetricCard({
                  title: 'Revenue',
                  value: data.quarterly_data[0].metrics.Revenue,
                  previousValue: data.quarterly_data[1]?.metrics.Revenue,
                  date: data.quarterly_data[0].date
                })}
                {renderMetricCard({
                  title: 'Net Income',
                  value: data.quarterly_data[0].metrics.NetIncome,
                  previousValue: data.quarterly_data[1]?.metrics.NetIncome
                })}
                {renderMetricCard({
                  title: 'Profit Margin',
                  value: data.quarterly_data[0].metrics.ProfitMargin,
                  previousValue: data.quarterly_data[1]?.metrics.ProfitMargin,
                  formatFn: formatPercent
                })}
                {renderMetricCard({
                  title: 'Total Assets',
                  value: data.quarterly_data[0].metrics.Assets,
                  previousValue: data.quarterly_data[1]?.metrics.Assets
                })}
              </>
            )}
          </div>

          {window.Recharts && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">Quarterly Performance</h2>
              <div style={{ width: '100%', height: 400 }}>
                <window.Recharts.ResponsiveContainer>
                  <window.Recharts.LineChart
                    data={data.quarterly_data.map(q => ({
                      date: q.date,
                      revenue: q.metrics.Revenue,
                      netIncome: q.metrics.NetIncome,
                      profitMargin: q.metrics.ProfitMargin
                    }))}
                    margin={{ top: 10, right: 30, left: 30, bottom: 10 }}
                  >
                    <window.Recharts.CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                    <window.Recharts.XAxis dataKey="date" />
                    <window.Recharts.YAxis yAxisId="left" />
                    <window.Recharts.YAxis yAxisId="right" orientation="right" />
                    <window.Recharts.Tooltip />
                    <window.Recharts.Legend />
                    <window.Recharts.Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="revenue"
                      name="Revenue"
                      stroke="#2563eb"
                      strokeWidth={2}
                    />
                    <window.Recharts.Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="netIncome"
                      name="Net Income"
                      stroke="#16a34a"
                      strokeWidth={2}
                    />
                  </window.Recharts.LineChart>
                </window.Recharts.ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-4 justify-center">
            {['analyze', 'predict', 'risk'].map((type) => (
              <button
                key={type}
                onClick={() => handleAnalysisClick(type)}
                disabled={loadingAnalysis}
                className={`px-8 py-3 rounded-lg shadow-md text-white disabled:opacity-50 ${
                  type === 'analyze' ? 'bg-blue-600 hover:bg-blue-700' :
                  type === 'predict' ? 'bg-green-600 hover:bg-green-700' :
                  'bg-yellow-600 hover:bg-yellow-700'
                }`}
              >
                {type === 'analyze' ? 'Analyze Financials' :
                 type === 'predict' ? 'Predict Next Quarter' :
                 'Risk Assessment'}
              </button>
            ))}
          </div>

          {loadingAnalysis && (
            <div className="flex justify-center">
              <div className="loading"></div>
            </div>
          )}

          {analysisContent && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">
                {analysisType === 'analyze' ? 'Financial Analysis' :
                 analysisType === 'predict' ? 'Next Quarter Prediction' :
                 'Risk Assessment'}
              </h2>
              <div className="prose max-w-none">
                {analysisContent.split('\n\n').map((paragraph, index) => (
                  <p key={index} className="mb-4 text-gray-700">
                    {paragraph}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Export for mounting
window.FinancialDashboard = FinancialDashboard;
