import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

// Extract outlet name from URL domain
const getOutletNameFromUrl = (url) => {
  if (!url) return 'News Source'
  try {
    const hostname = new URL(url).hostname.replace('www.', '')
    // Map common domains to friendly names
    const domainMap = {
      'bridgemi.com': 'Bridge Michigan',
      'freep.com': 'Detroit Free Press',
      'detroitnews.com': 'The Detroit News',
      'mlive.com': 'MLive',
      'michiganradio.org': 'Michigan Radio',
      'secondwavemedia.com': 'Second Wave Media',
      'metrotimes.com': 'Metro Times',
      'crainsdetroit.com': "Crain's Detroit Business",
      'dailydetroit.com': 'Daily Detroit',
      'modelDmedia.com': 'Model D Media',
      'detroitisit.com': 'Detroit Is It',
      'hourdetroit.com': 'Hour Detroit',
      'interlochen.org': 'Interlochen Public Radio',
      'greatlakesnow.org': 'Great Lakes Now',
      'news.google.com': 'Google News',
      'npr.org': 'NPR',
      'nytimes.com': 'The New York Times',
      'washingtonpost.com': 'The Washington Post',
    }
    return domainMap[hostname] || hostname.split('.')[0].charAt(0).toUpperCase() + hostname.split('.')[0].slice(1)
  } catch {
    return 'News Source'
  }
}

function OrgProfile() {
  const { slug } = useParams()
  const [org, setOrg] = useState(null)
  const [financials, setFinancials] = useState([])
  const [mediaMentions, setMediaMentions] = useState([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    fetchOrgData()
  }, [slug])
  
  const fetchOrgData = async () => {
    setLoading(true)
    try {
      const orgResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/organizations?slug=eq.${slug}&select=*`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const orgData = await orgResponse.json()
      
      if (orgData.length === 0) {
        setOrg(null)
        setLoading(false)
        return
      }
      
      setOrg(orgData[0])
      
      const finResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/financials?organization_id=eq.${orgData[0].id}&order=year.desc`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const finData = await finResponse.json()
      setFinancials(finData)

      // Fetch media mentions with outlet info
      const mediaResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/media_mentions?organization_id=eq.${orgData[0].id}&select=*,outlets(name,url)&order=published_date.desc.nullslast`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const mediaData = await mediaResponse.json()
      setMediaMentions(mediaData)

      setLoading(false)
    } catch (error) {
      console.error('Error fetching data:', error)
      setLoading(false)
    }
  }
  
  if (loading) return <div className="loading">Loading...</div>
  if (!org) return <div className="error">Organization not found</div>
  
  const chartData = [...financials].reverse().map(f => ({
    year: f.year,
    revenue: f.revenue,
    expenses: f.expenses,
    assets: f.assets
  }))
  
  return (
    <div className="org-profile">
      <nav className="breadcrumb">
        <Link to="/">← Back to All Organizations</Link>
      </nav>
      
      <header className="org-header">
        <h1>{org.name}</h1>
        {org.mission_statement_text && (
          <p className="mission">{org.mission_statement_text}</p>
        )}
      </header>
      
      <div className="org-content">
        <section className="financial-section">
          <h2>Financial Overview</h2>
          
          {financials.length > 0 ? (
            <>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-label">Latest Revenue</div>
                  <div className="stat-value">
                    ${financials[0].revenue.toLocaleString()}
                  </div>
                  <div className="stat-year">{financials[0].year}</div>
                </div>
                
                <div className="stat-card">
                  <div className="stat-label">Total Assets</div>
                  <div className="stat-value">
                    ${financials[0].assets.toLocaleString()}
                  </div>
                  <div className="stat-year">{financials[0].year}</div>
                </div>
                
                <div className="stat-card">
                  <div className="stat-label">Years of Data</div>
                  <div className="stat-value">{financials.length}</div>
                  <div className="stat-year">
                    {financials[financials.length - 1].year} - {financials[0].year}
                  </div>
                </div>
              </div>
              
              <div className="chart-container">
                <h3>Revenue & Expenses Over Time</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="year" />
                    <YAxis />
                    <Tooltip formatter={(value) => `$${value.toLocaleString()}`} />
                    <Legend />
                    <Line type="monotone" dataKey="revenue" stroke="#2f80c3" strokeWidth={2} name="Revenue" />
                    <Line type="monotone" dataKey="expenses" stroke="#ea5a39" strokeWidth={2} name="Expenses" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              
              <div className="financial-table">
                <h3>Detailed Financials</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Year</th>
                      <th>Revenue</th>
                      <th>Expenses</th>
                      <th>Assets</th>
                      <th>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {financials.map(f => (
                      <tr key={f.id}>
                        <td>{f.year}</td>
                        <td>${f.revenue.toLocaleString()}</td>
                        <td>${f.expenses.toLocaleString()}</td>
                        <td>${f.assets.toLocaleString()}</td>
                        <td><a href={f.source_url} target="_blank">View 990</a></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="no-data">
              No financial data available. This organization likely files Form 990-N (revenue under $50,000).
            </p>
          )}
        </section>
        
        <section className="contact-section">
          <h2>Contact Information</h2>
          <div className="contact-info">
            {org.website && (
              <p><strong>Website:</strong> <a href={org.website} target="_blank" rel="noopener noreferrer">{org.website}</a></p>
            )}
            {org.email && <p><strong>Email:</strong> <a href={`mailto:${org.email}`}>{org.email}</a></p>}
            {org.phone && <p><strong>Phone:</strong> {org.phone}</p>}
            {org.address && (
              <p><strong>Address:</strong> {org.address}, {org.city}, MI {org.zip}</p>
            )}
          </div>
        </section>
        
        <section className="media-section">
          <h2>Media Coverage</h2>
          {mediaMentions.length > 0 ? (
            <div className="media-mentions-list">
              {mediaMentions.map(mention => (
                <article key={mention.id} className="media-mention-card">
                  <div className="mention-outlet">
                    {mention.outlets?.name || getOutletNameFromUrl(mention.article_url)}
                  </div>
                  <h3 className="mention-headline">
                    <a href={mention.article_url} target="_blank" rel="noopener noreferrer">
                      {mention.headline}
                    </a>
                  </h3>
                  {mention.published_date && (
                    <div className="mention-date">
                      {new Date(mention.published_date).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </div>
                  )}
                  {mention.excerpt && (
                    <p className="mention-excerpt">{mention.excerpt}</p>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <p className="no-data">No media mentions found for this organization.</p>
          )}
        </section>
      </div>
    </div>
  )
}

export default OrgProfile