import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

function Home() {
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all') // 'all', 'with-data', 'without-data'
  
  useEffect(() => {
    fetchOrgs()
  }, [])
  
  const fetchOrgs = async () => {
    try {
      // Fetch orgs
      const orgsResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/organizations?select=*&order=name`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const orgsData = await orgsResponse.json()
      
      // Fetch financial data counts
      const finResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/financials?select=organization_id`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const finData = await finResponse.json()
      
      // Count financials per org
      const finCounts = {}
      finData.forEach(f => {
        finCounts[f.organization_id] = (finCounts[f.organization_id] || 0) + 1
      })
      
      // Add hasFinancials flag
      const orgsWithFlags = orgsData.map(org => ({
        ...org,
        hasFinancials: (finCounts[org.id] || 0) > 0
      }))
      
      setOrgs(orgsWithFlags)
      setLoading(false)
    } catch (error) {
      console.error('Error:', error)
      setLoading(false)
    }
  }
  
  const filteredOrgs = orgs.filter(org => {
    // Search filter
    const matchesSearch = org.name.toLowerCase().includes(search.toLowerCase())
    
    // Financial data filter
    if (filter === 'with-data') return matchesSearch && org.hasFinancials
    if (filter === 'without-data') return matchesSearch && !org.hasFinancials
    return matchesSearch // 'all'
  })
  
  const withDataCount = orgs.filter(o => o.hasFinancials).length
  const withoutDataCount = orgs.length - withDataCount
  
  return (
    <div className="home">
      <header className="home-header">
        <h1>Michigan Environmental Organizations</h1>
        <p className="subtitle">
          {orgs.length} organizations · {withDataCount} with financial data · {withoutDataCount} contact info only
        </p>
      </header>
      
      <div className="search-box">
        <input 
          type="text" 
          placeholder="Search organizations..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      
      <div className="filter-buttons">
        <button 
          className={filter === 'all' ? 'active' : ''} 
          onClick={() => setFilter('all')}
        >
          All ({orgs.length})
        </button>
        <button 
          className={filter === 'with-data' ? 'active' : ''} 
          onClick={() => setFilter('with-data')}
        >
          With Financial Data ({withDataCount})
        </button>
        <button 
          className={filter === 'without-data' ? 'active' : ''} 
          onClick={() => setFilter('without-data')}
        >
          Contact Info Only ({withoutDataCount})
        </button>
      </div>
      
      {loading ? (
        <div className="loading">Loading organizations...</div>
      ) : (
        <section className="org-list">
          <h2>
            {filteredOrgs.length} {filter === 'all' ? 'Organizations' : 
             filter === 'with-data' ? 'Organizations with Financial Data' : 
             'Organizations (Contact Info Only)'}
          </h2>
          <div className="org-grid">
            {filteredOrgs.map(org => (
              <Link key={org.slug} to={`/org/${org.slug}`} className="org-card">
                <h3>{org.name}</h3>
                {org.hasFinancials ? (
                  <span className="badge">Financial data available</span>
                ) : (
                  <span className="badge small-org">Contact info only</span>
                )}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export default Home