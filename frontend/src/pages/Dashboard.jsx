import React, { useEffect, useState } from 'react'
import { useAuth } from '../App.jsx'
import NodeCard from '../components/NodeCard.jsx'
import { apiFetch } from '../api.js'

export default function Dashboard() {
  const { token } = useAuth()
  const [nodes, setNodes] = useState([])
  const [health, setHealth] = useState({})
  const [routing, setRouting] = useState(null)
  const [error, setError] = useState('')

  const hdrs = { Authorization: `Bearer ${token}` }

  async function load() {
    try {
      const [nr, hr, rr] = await Promise.all([
        apiFetch('/api/nodes',        { headers: hdrs }),
        apiFetch('/api/health/mesh',  { headers: hdrs }),
        apiFetch('/api/routing',      { headers: hdrs }),
      ])
      if (nr.ok) setNodes(await nr.json())
      if (hr.ok) {
        const list = await hr.json()
        setHealth(Object.fromEntries(list.map(h => [h.name, h])))
      }
      if (rr.ok) setRouting(await rr.json())
    } catch {
      setError('Failed to load data')
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ margin: 0 }}>Mesh Dashboard</h2>
        {routing && (
          <span style={{ color: '#94a3b8', fontSize: 13 }}>
            Routing: <strong style={{ color: '#e2e8f0' }}>{routing.mode}</strong>
          </span>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
        {nodes.length === 0 && !error && (
          <p style={{ color: '#94a3b8' }}>Loading nodes…</p>
        )}
        {nodes.map(n => (
          <NodeCard key={n.id} node={n} health={health[n.name]} />
        ))}
      </div>
    </div>
  )
}
