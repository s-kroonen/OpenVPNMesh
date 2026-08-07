import React, { useEffect, useState } from 'react'
import { useAuth } from '../App.jsx'
import { apiFetch } from '../api.js'

const MODES = ['weighted', 'random', 'fastest', 'failover']

export default function Routing() {
  const { token } = useAuth()
  const [config, setConfig] = useState({ mode: 'weighted', weight: 100, health_interval: 3, failover_threshold: 3 })
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  useEffect(() => {
    apiFetch('/api/routing', { headers })
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setConfig(d))
      .catch(() => {})
  }, [])

  async function save(e) {
    e.preventDefault()
    setError('')
    setSaved(false)
    try {
      const r = await apiFetch('/api/routing', {
        method: 'PUT',
        headers,
        body: JSON.stringify(config),
      })
      if (r.ok) {
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
      } else {
        const d = await r.json()
        setError(d.detail || 'Save failed')
      }
    } catch { setError('Save failed') }
  }

  return (
    <div style={{ maxWidth: 500 }}>
      <h2 style={{ marginTop: 0 }}>Routing Settings</h2>

      <form onSubmit={save} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div>
          <label style={{ display: 'block', marginBottom: 6, fontSize: 13, color: '#94a3b8' }}>Routing mode</label>
          <select
            value={config.mode}
            onChange={e => setConfig(c => ({ ...c, mode: e.target.value }))}
            style={{
              width: '100%', padding: '8px 12px', background: '#1e2332',
              border: '1px solid #2d3748', borderRadius: 6, color: '#e2e8f0', fontSize: 14,
            }}
          >
            {MODES.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>

        {config.mode === 'weighted' && (
          <div>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 13, color: '#94a3b8' }}>
              Default weight: {config.weight}
            </label>
            <input
              type="range" min="1" max="200" value={config.weight}
              onChange={e => setConfig(c => ({ ...c, weight: Number(e.target.value) }))}
              style={{ width: '100%' }}
            />
          </div>
        )}

        <div>
          <label style={{ display: 'block', marginBottom: 6, fontSize: 13, color: '#94a3b8' }}>
            Health check interval (seconds)
          </label>
          <input
            type="number" min="1" max="60" value={config.health_interval}
            onChange={e => setConfig(c => ({ ...c, health_interval: Number(e.target.value) }))}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: 6, fontSize: 13, color: '#94a3b8' }}>
            Failover threshold (missed heartbeats)
          </label>
          <input
            type="number" min="1" max="20" value={config.failover_threshold}
            onChange={e => setConfig(c => ({ ...c, failover_threshold: Number(e.target.value) }))}
          />
        </div>

        {error && <p className="error">{error}</p>}

        <button type="submit" className="btn-primary">
          {saved ? '✓ Saved' : 'Save settings'}
        </button>
      </form>
    </div>
  )
}
