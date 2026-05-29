import React from 'react'
import HealthBadge from './HealthBadge.jsx'

function ago(ts) {
  if (!ts) return '—'
  const s = Math.floor(Date.now() / 1000) - ts
  if (s < 5)  return 'just now'
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  return `${Math.floor(s / 3600)}h ago`
}

function Dot({ ok }) {
  return (
    <span style={{
      display: 'inline-block',
      width: 8, height: 8,
      borderRadius: '50%',
      background: ok ? '#48bb78' : '#fc8181',
      marginRight: 5,
    }} />
  )
}

export default function NodeCard({ node, health }) {
  return (
    <div className="card" style={{ minWidth: 270 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>{node.name}</div>
          <div style={{ color: '#94a3b8', fontSize: 13, marginTop: 2 }}>{node.public_ip}</div>
        </div>
        <HealthBadge status={health?.status || node.status} />
      </div>

      <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 7 }}>
        <Row label="WG IP"    value={node.wg_ip || '—'} />
        <Row label="API port" value={node.api_port} />
        <Row label="Priority" value={node.priority} />

        <div style={{ borderTop: '1px solid #2d3748', margin: '4px 0' }} />

        <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
          <span><Dot ok={health?.api_ok !== false} />API</span>
          <span><Dot ok={health?.wg_ok} />WireGuard</span>
        </div>

        {health?.latency_ms != null && (
          <Row label="Latency" value={`${health.latency_ms} ms`} />
        )}
        {health?.last_seen && (
          <Row label="Last seen" value={ago(health.last_seen)} />
        )}
      </div>
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
      <span style={{ color: '#94a3b8' }}>{label}</span>
      <span>{value}</span>
    </div>
  )
}
