import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState(null)
  
  useEffect(() => {
    fetchDashboardData()
  }, [])
  
  const fetchDashboardData = async () => {
    try {
      const finResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/financials?select=*&order=year.desc`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const financials = await finResponse.json()
      
      const uniqueOrgIds = [...new Set(financials.map(f => f.organization_id))]
      
      const orgsResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/organizations?select=id,name,slug,ein&id=in.(${uniqueOrgIds.join(',')})`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const orgs = await orgsResponse.json()
      
      const calculatedStats = calculateStats(orgs, financials)
      setStats(calculatedStats)
      setLoading(false)
      
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
      setLoading(false)
    }
  }
  
  const calculateStats = (orgs, financials) => {
    const years = [...new Set(financials.map(f => f.year))]
      .filter(year => year <= 2023)
      .sort()
    
    const byYear = {}
    years.forEach(year => {
      byYear[year] = { year, revenue: 0, expenses: 0, assets: 0, orgs: new Set() }
    })
    
    financials.forEach(f => {
      if (byYear[f.year]) {
        byYear[f.year].revenue += f.revenue || 0
        byYear[f.year].expenses += f.expenses || 0
        byYear[f.year].assets += f.assets || 0
        byYear[f.year].orgs.add(f.organization_id)
      }
    })
    
    const revenueByYear = Object.values(byYear).map(y => ({
      year: y.year,
      revenue: y.revenue,
      expenses: y.expenses
    }))
    
    const latestYear = Math.max(...years)
    const latestData = byYear[latestYear]
    
    const orgHealth = {}
    orgs.forEach(org => {
      const orgFinancials = financials
        .filter(f => f.organization_id === org.id)
        .sort((a, b) => b.year - a.year)

      if (orgFinancials.length > 0) {
        // Use up to 3 most recent years for rolling average
        const recentYears = orgFinancials.slice(0, 3)
        const yearsUsed = recentYears.map(f => f.year)

        // Calculate 3-year averages
        const avgRevenue = recentYears.reduce((sum, f) => sum + (f.revenue || 0), 0) / recentYears.length
        const avgExpenses = recentYears.reduce((sum, f) => sum + (f.expenses || 0), 0) / recentYears.length
        const avgMargin = avgRevenue - avgExpenses
        const avgMarginPercent = avgRevenue > 0 ? (avgMargin / avgRevenue) * 100 : 0

        // Use latest year for assets (point-in-time metric)
        const latestAssets = orgFinancials[0].assets || 0

        // Health thresholds (symmetric around break-even)
        // Healthy: margin > 5%
        // Stable: margin between -5% and +5%
        // At Risk: margin < -5%
        let health = 'healthy'
        if (avgMarginPercent < -5) health = 'at-risk'
        else if (avgMarginPercent < 5) health = 'stable'

        orgHealth[org.id] = {
          ...org,
          health,
          revenue: avgRevenue,
          expenses: avgExpenses,
          assets: latestAssets,
          margin: avgMarginPercent,
          ein: org.ein,
          yearsAnalyzed: yearsUsed,
          yearRange: yearsUsed.length > 1
            ? `${Math.min(...yearsUsed)}-${Math.max(...yearsUsed)}`
            : `${yearsUsed[0]}`
        }
      }
    })
    
    const healthCounts = {
      healthy: Object.values(orgHealth).filter(o => o.health === 'healthy').length,
      stable: Object.values(orgHealth).filter(o => o.health === 'stable').length,
      atRisk: Object.values(orgHealth).filter(o => o.health === 'at-risk').length
    }
    
    const sizeDistribution = { small: 0, medium: 0, large: 0 }
    
    Object.values(orgHealth).forEach(org => {
      if (org.revenue < 100000) sizeDistribution.small++
      else if (org.revenue < 1000000) sizeDistribution.medium++
      else sizeDistribution.large++
    })
    
    const top10Revenue = Object.values(orgHealth).sort((a, b) => b.revenue - a.revenue).slice(0, 10)
    const top10Assets = Object.values(orgHealth).filter(o => o.assets > 0).sort((a, b) => b.assets - a.assets).slice(0, 10)
    const strongest = Object.values(orgHealth).filter(o => o.revenue >= 50000).sort((a, b) => b.margin - a.margin).slice(0, 5)
    const weakest = Object.values(orgHealth).filter(o => o.revenue >= 50000).sort((a, b) => a.margin - b.margin).slice(0, 5)
    
    return {
      totalRevenue: latestData.revenue,
      totalExpenses: latestData.expenses,
      totalAssets: latestData.assets,
      orgCount: orgs.length,
      yearRange: `${Math.min(...years)}-${Math.max(...years)}`,
      revenueByYear,
      healthCounts,
      sizeDistribution,
      top10Revenue,
      top10Assets,
      strongest,
      weakest
    }
  }
  
  if (loading) return <div className="dashboard loading"><p>Loading dashboard data...</p></div>
  if (!stats) return <div className="dashboard error"><p>Error loading dashboard data</p></div>
  
  const healthData = [
    { name: 'Healthy', value: stats.healthCounts.healthy, color: '#4ade80' },
    { name: 'Stable', value: stats.healthCounts.stable, color: '#fbbf24' },
    { name: 'At Risk', value: stats.healthCounts.atRisk, color: '#ef4444' }
  ]
  
  const sizeData = [
    { name: 'Small', label: '<$100K', value: stats.sizeDistribution.small },
    { name: 'Medium', label: '$100K-$1M', value: stats.sizeDistribution.medium },
    { name: 'Large', label: '>$1M', value: stats.sizeDistribution.large }
  ]
  
  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Michigan Environmental Movement</h1>
        <p className="subtitle">Economic Impact & Financial Health Analysis</p>
      </header>
      
      <div className="stats-grid big-stats">
        <div className="stat-card big">
          <div className="stat-label">Total Annual Revenue</div>
          <div className="stat-value huge">${(stats.totalRevenue / 1000000).toFixed(1)}M</div>
          <div className="stat-note">Latest year reported</div>
        </div>
        <div className="stat-card big">
          <div className="stat-label">Organizations Tracked</div>
          <div className="stat-value huge">{stats.orgCount}</div>
          <div className="stat-note">With financial data</div>
        </div>
        <div className="stat-card big">
          <div className="stat-label">Total Assets</div>
          <div className="stat-value huge">${(stats.totalAssets / 1000000).toFixed(1)}M</div>
          <div className="stat-note">Combined movement resources</div>
        </div>
        <div className="stat-card big">
          <div className="stat-label">Years of Data</div>
          <div className="stat-value huge">{stats.yearRange}</div>
          <div className="stat-note">Historical tracking</div>
        </div>
      </div>
      
      <section className="dashboard-section">
        <h2>Economic Impact Over Time</h2>
        <div className="chart-container large">
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={stats.revenueByYear}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis tickFormatter={(value) => `$${(value / 1000000).toFixed(0)}M`} />
              <Tooltip formatter={(value) => `$${value.toLocaleString()}`} labelStyle={{ color: '#333' }} />
              <Legend />
              <Line type="monotone" dataKey="revenue" stroke="#2f80c3" strokeWidth={3} name="Total Revenue" dot={{ r: 5 }} />
              <Line type="monotone" dataKey="expenses" stroke="#ea5a39" strokeWidth={3} name="Total Expenses" dot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
      
      <div className="two-column">
        <section className="dashboard-section">
          <h2>Financial Health Distribution</h2>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={healthData} cx="50%" cy="50%" labelLine={false} label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`} outerRadius={100} dataKey="value">
                  {healthData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="health-legend">
            <p className="legend-note">Based on 3-year average operating margin</p>
            <div className="legend-item"><span className="dot" style={{ background: '#4ade80' }}></span><strong>Healthy:</strong> Margin above +5%</div>
            <div className="legend-item"><span className="dot" style={{ background: '#fbbf24' }}></span><strong>Stable:</strong> Margin between -5% and +5%</div>
            <div className="legend-item"><span className="dot" style={{ background: '#ef4444' }}></span><strong>At Risk:</strong> Margin below -5%</div>
          </div>
        </section>
        
        <section className="dashboard-section">
          <h2>Organization Size Distribution</h2>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={sizeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fontSize: 14 }} interval={0} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#2f80c3" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
      
      <div className="two-column">
        <section className="dashboard-section">
          <h2>💰 Top 10 by Annual Revenue</h2>
          <p className="section-note">3-year average revenue from IRS 990 filings</p>
          <div className="top-orgs-list">
            {stats.top10Revenue.map((org, index) => (
              <Link key={org.id} to={`/org/${org.slug}`} className="top-org-item">
                <div className="rank">#{index + 1}</div>
                <div className="org-info">
                  <h3>{org.name}</h3>
                  <div className="org-stats">
                    <span className="revenue">${(org.revenue / 1000000).toFixed(2)}M/yr</span>
                    <span className="health" data-health={org.health}>
                      {org.health === 'healthy' ? '✓ Healthy' : org.health === 'stable' ? '● Stable' : '⚠ At Risk'}
                    </span>
                    <span className="year-range">{org.yearRange}</span>
                  </div>
                </div>
                {org.ein && <span className="propublica-link" onClick={(e) => { e.preventDefault(); window.open(`https://projects.propublica.org/nonprofits/organizations/${org.ein}`, '_blank'); }}>990s →</span>}
              </Link>
            ))}
          </div>
        </section>

        <section className="dashboard-section">
          <h2>🏦 Top 10 by Total Assets</h2>
          <p className="section-note">Most recent reported assets from IRS 990 filings</p>
          <div className="top-orgs-list">
            {stats.top10Assets.map((org, index) => (
              <Link key={org.id} to={`/org/${org.slug}`} className="top-org-item">
                <div className="rank">#{index + 1}</div>
                <div className="org-info">
                  <h3>{org.name}</h3>
                  <div className="org-stats">
                    <span className="revenue">${(org.assets / 1000000).toFixed(2)}M assets</span>
                    <span className="health" data-health={org.health}>
                      {org.health === 'healthy' ? '✓ Healthy' : org.health === 'stable' ? '● Stable' : '⚠ At Risk'}
                    </span>
                    <span className="year-range">{org.yearRange}</span>
                  </div>
                </div>
                {org.ein && <span className="propublica-link" onClick={(e) => { e.preventDefault(); window.open(`https://projects.propublica.org/nonprofits/organizations/${org.ein}`, '_blank'); }}>990s →</span>}
              </Link>
            ))}
          </div>
        </section>
      </div>
      
      <div className="two-column">
        <section className="dashboard-section">
          <h2>💪 Strongest Financial Position</h2>
          <p className="section-note">Highest 3-year average operating margins (min. $50K revenue)</p>
          <div className="health-list">
            {stats.strongest.map((org, index) => (
              <Link key={org.id} to={`/org/${org.slug}`} className="health-list-item">
                <div className="health-org-name"><strong>#{index + 1}</strong> {org.name}</div>
                <div className="health-org-stats">
                  <span className="margin positive">+{org.margin.toFixed(1)}%</span>
                  <span className="revenue-small">${(org.revenue / 1000).toFixed(0)}K</span>
                  <span className="year-range">{org.yearRange}</span>
                </div>
                {org.ein && <span className="propublica-link-small" onClick={(e) => { e.preventDefault(); window.open(`https://projects.propublica.org/nonprofits/organizations/${org.ein}`, '_blank'); }}>990s</span>}
              </Link>
            ))}
          </div>
        </section>

        <section className="dashboard-section">
          <h2>⚠️ Most Financially Challenged</h2>
          <p className="section-note">Most negative 3-year average margins (min. $50K revenue)</p>
          <div className="health-list">
            {stats.weakest.map((org, index) => (
              <Link key={org.id} to={`/org/${org.slug}`} className="health-list-item">
                <div className="health-org-name"><strong>#{index + 1}</strong> {org.name}</div>
                <div className="health-org-stats">
                  <span className="margin negative">{org.margin.toFixed(1)}%</span>
                  <span className="revenue-small">${(org.revenue / 1000).toFixed(0)}K</span>
                  <span className="year-range">{org.yearRange}</span>
                </div>
                {org.ein && <span className="propublica-link-small" onClick={(e) => { e.preventDefault(); window.open(`https://projects.propublica.org/nonprofits/organizations/${org.ein}`, '_blank'); }}>990s</span>}
              </Link>
            ))}
          </div>
        </section>
      </div>
      
      <section className="dashboard-section insights">
        <h2>Key Insights</h2>
        <div className="insights-grid">
          <div className="insight-card">
            <h3>Movement Size</h3>
            <p>Michigan's environmental movement represents over <strong>${(stats.totalRevenue / 1000000).toFixed(0)} million</strong> in annual economic activity across {stats.orgCount} organizations with available financial data.</p>
          </div>
          <div className="insight-card">
            <h3>Financial Health</h3>
            <p><strong>{((stats.healthCounts.healthy / stats.orgCount) * 100).toFixed(0)}%</strong> of organizations are financially healthy, with revenue exceeding expenses. This indicates a relatively stable movement.</p>
          </div>
          <div className="insight-card">
            <h3>Organization Mix</h3>
            <p>The movement includes <strong>{stats.sizeDistribution.small} small</strong>, <strong>{stats.sizeDistribution.medium} medium</strong>, and <strong>{stats.sizeDistribution.large} large</strong> organizations, showing diversity in organizational capacity.</p>
          </div>
        </div>
      </section>
      
      <footer className="dashboard-footer">
        <p>Built by <a href="https://planetdetroit.org" target="_blank" rel="noopener noreferrer">Planet Detroit</a> and <a href="https://www.environmentalcouncil.org" target="_blank" rel="noopener noreferrer">Michigan Environmental Council</a></p>
        <p>Data from IRS 990 forms via ProPublica Nonprofit Explorer</p>
      </footer>
    </div>
  )
}

export default Dashboard
