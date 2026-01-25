import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

// Custom smaller marker icon (25% smaller than default)
const smallIcon = L.icon({
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [19, 31],       // default is [25, 41]
  iconAnchor: [9, 31],      // default is [12, 41]
  popupAnchor: [1, -26],    // default is [1, -34]
  shadowSize: [31, 31],     // default is [41, 41]
})

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

function Landing() {
  const [orgs, setOrgs] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    fetchData()
  }, [])
  
  const fetchData = async () => {
    try {
      // Fetch geocoded orgs with EINs
      const orgsResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/organizations?select=id,name,slug,latitude,longitude,city,ein&latitude=not.is.null&longitude=not.is.null`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const geocodedOrgs = await orgsResponse.json()
      setOrgs(geocodedOrgs)
      
      // Fetch quick stats
      const allOrgsResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/organizations?select=id,ein`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const allOrgs = await allOrgsResponse.json()
      
      const finResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/financials?select=organization_id,revenue,year&order=year.desc.nullslast&limit=1000`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const financials = await finResponse.json()
      
      // Get unique orgs with data
      const orgsWithData = [...new Set(financials.map(f => f.organization_id))].length
      
      // Calculate total from latest year
      const latestYear = Math.max(...financials.map(f => f.year))
      const latestRevenue = financials
        .filter(f => f.year === latestYear)
        .reduce((sum, f) => sum + (f.revenue || 0), 0)
      
      setStats({
        totalOrgs: allOrgs.length,
        geocoded: geocodedOrgs.length,
        withFinancials: orgsWithData,
        totalRevenue: latestRevenue
      })
      
      setLoading(false)
    } catch (error) {
      console.error('Error fetching data:', error)
      setLoading(false)
    }
  }
  
  return (
    <div className="landing">
      <div className="hero">
        <h1>Michigan Environmental Organizations</h1>
        <p className="hero-subtitle">
          Mapping the movement • Tracking economic impact • Connecting communities
        </p>
        
        {stats && (
          <div className="hero-stats">
            <div className="hero-stat">
              <div className="hero-stat-value">{stats.totalOrgs}</div>
              <div className="hero-stat-label">Organizations</div>
            </div>
            <div className="hero-stat">
              <div className="hero-stat-value">{stats.geocoded}</div>
              <div className="hero-stat-label">On the Map</div>
            </div>
            <div className="hero-stat">
              <div className="hero-stat-value">{stats.withFinancials}</div>
              <div className="hero-stat-label">With Financial Data</div>
            </div>
            <div className="hero-stat">
              <div className="hero-stat-value">${(stats.totalRevenue / 1000000).toFixed(0)}M</div>
              <div className="hero-stat-label">Annual Revenue</div>
            </div>
          </div>
        )}
      </div>
      
      <div className="landing-nav">
        <Link to="/organizations" className="landing-nav-card">
          <div className="landing-nav-icon">🔍</div>
          <h2>Search Organizations</h2>
          <p>Browse and filter {stats?.totalOrgs || 'hundreds of'} environmental groups across Michigan</p>
        </Link>
        
        <Link to="/dashboard" className="landing-nav-card">
          <div className="landing-nav-icon">📊</div>
          <h2>Movement Dashboard</h2>
          <p>Explore economic impact, financial health, and sector trends</p>
        </Link>
      </div>
      
      <div className="map-section">
        <h2>Organizations Across Michigan</h2>
        <p className="map-subtitle">{stats?.geocoded || 517} organizations mapped by location</p>
        
        {loading ? (
          <div className="map-loading">Loading map...</div>
        ) : (
          <div className="map-container-wrapper">
            <MapContainer
              center={[44.3148, -85.6024]}
              zoom={7}
              style={{ height: 'calc(100vh - 220px)', minHeight: '400px', width: '100%' }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {orgs.map(org => (
                <Marker key={org.id} position={[org.latitude, org.longitude]} icon={smallIcon}>
                  <Popup className="custom-popup">
                    <div className="popup-content">
                      <h3>{org.name}</h3>
                      <p className="popup-location">{org.city}</p>
                      <div className="popup-links">
                        <Link to={`/org/${org.slug}`} className="popup-link primary">
                          View Profile →
                        </Link>
                        {org.ein && (
                          <a 
                            href={`https://projects.propublica.org/nonprofits/organizations/${org.ein}`}
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="popup-link secondary"
                          >
                            990 Forms →
                          </a>
                        )}
                      </div>
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>
        )}
      </div>
      
      <div className="landing-footer">
        <h3>About the ECOcensus Project</h3>
        <p>
          This database tracks Michigan's environmental nonprofit sector, combining IRS 990 financial data 
          with geographic and organizational information. Built by <a href="https://planetdetroit.org" target="_blank" rel="noopener noreferrer">Planet Detroit</a> and <a href="https://www.environmentalcouncil.org" target="_blank" rel="noopener noreferrer">Michigan Environmental Council</a>.
        </p>
      </div>
    </div>
  )
}

export default Landing
