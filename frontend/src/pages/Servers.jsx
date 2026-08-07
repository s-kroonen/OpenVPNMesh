import React, { useEffect, useState } from 'react'
import { useAuth } from '../App.jsx'
import HealthBadge from '../components/HealthBadge.jsx'
import { apiFetch } from '../api.js'

export default function Servers() {
  const { token } = useAuth()
  const [nodes, setNodes] = useState([])
  const [tokenInfo, setTokenInfo] = useState(null)
  const [showJoin, setShowJoin] = useState(false)
  const [rotating, setRotating] = useState(false)
  const [error, setError] = useState('')

  const headers = { Authorization: `Bearer ${token}` }

  async function load() {
    try {
      const r = await apiFetch('/api/nodes', { headers })
      if (r.ok) setNodes(await r.json())
    } catch { setError('Failed to load nodes') }
  }

  async function loadToken() {
    try {
      const r = await apiFetch('/api/nodes/join-token', { headers })
      if (r.ok) setTokenInfo(await r.json())
      else setTokenInfo(null)
    } catch {}
  }

  useEffect(() => { load(); loadToken() }, [])

  async function rotateToken() {
    setRotating(true)
    try {
      const r = await apiFetch('/api/nodes/join-token/rotate', { method: 'POST', headers })
      if (r.ok) {
        setTokenInfo(await r.json())
        setShowJoin(true)
      }
    } finally { setRotating(false) }
  }

  async function removeNode(node) {
    if (!confirm(`Remove node "${node.name}" from the mesh?`)) return
    const r = await apiFetch(`/api/nodes/${node.id}`, { method: 'DELETE', headers })
    if (r.ok) await load()
    else setError('Failed to remove node')
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ margin: 0 }}>Servers</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          {tokenInfo && (
            <>
              <button className="btn-primary btn-sm" onClick={() => setShowJoin(v => !v)}>
                {showJoin ? 'Hide join info' : 'Add server'}
              </button>
              <button className="btn-sm" style={{ background: '#2d3748', color: '#94a3b8' }}
                onClick={rotateToken} disabled={rotating}>
                {rotating ? 'Rotating…' : 'Rotate token'}
              </button>
            </>
          )}
        </div>
      </div>

      {showJoin && tokenInfo && (
        <div className="card" style={{ marginBottom: 20, fontSize: 13, lineHeight: 1.7 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>Join instructions for Node B</h3>
          <p style={{ margin: '0 0 10px', color: '#94a3b8' }}>
            Copy <code>mesh.yaml.example</code> to <code>mesh.yaml</code> on the new server, then set:
          </p>
          <pre style={{
            background: '#0f1117', border: '1px solid #2d3748', borderRadius: 6,
            padding: 14, margin: 0, overflowX: 'auto', fontSize: 12,
          }}>{`node:
  name: "node-b"          # unique name for this server
  public_ip: "YOUR_IP"    # this server's public IP

mesh:
  mode: "join"
  join_addr: "${tokenInfo.join_addr}"
  join_token: "${tokenInfo.join_token}"`}</pre>
          <p style={{ margin: '10px 0 0', color: '#94a3b8' }}>Then run: <code>docker compose up -d core frontend</code></p>
        </div>
      )}

      {error && <p className="error">{error}</p>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {nodes.map(n => (
          <div key={n.id} className="card"
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600 }}>{n.name}</div>
              <div style={{ color: '#94a3b8', fontSize: 13 }}>
                {n.public_ip} · WG: {n.wg_ip || '—'} · priority {n.priority}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <HealthBadge status={n.status} />
              {n.status !== 'leader' && (
                <button className="btn-danger btn-sm" onClick={() => removeNode(n)}>Remove</button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
