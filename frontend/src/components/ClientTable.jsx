import React from 'react'

export default function ClientTable({ clients, onDownload, onDelete }) {
  if (!clients.length) {
    return <p style={{ color: '#94a3b8' }}>No VPN clients yet.</p>
  }
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
      <thead>
        <tr style={{ borderBottom: '1px solid #2d3748', color: '#94a3b8', textAlign: 'left' }}>
          <th style={{ padding: '8px 0' }}>Name</th>
          <th>IP</th>
          <th>Created</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {clients.map(c => (
          <tr key={c.id} style={{ borderBottom: '1px solid #1a1f2e' }}>
            <td style={{ padding: '10px 0', fontWeight: 500 }}>{c.name}</td>
            <td style={{ color: '#94a3b8' }}>{c.ovpn_ip || '—'}</td>
            <td style={{ color: '#94a3b8' }}>
              {c.created_at ? new Date(c.created_at * 1000).toLocaleDateString() : '—'}
            </td>
            <td style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', padding: '6px 0' }}>
              <button className="btn-primary btn-sm" onClick={() => onDownload(c)}>
                Download .ovpn
              </button>
              <button className="btn-danger btn-sm" onClick={() => onDelete(c)}>
                Revoke
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
