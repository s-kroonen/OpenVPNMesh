import React, { useEffect, useState } from 'react'
import { useAuth } from '../App.jsx'
import ClientTable from '../components/ClientTable.jsx'
import { apiFetch } from '../api.js'

export default function Clients() {
  const { token } = useAuth()
  const [clients, setClients] = useState([])
  const [newName, setNewName] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  async function load() {
    try {
      const r = await apiFetch('/api/clients', { headers })
      if (r.ok) setClients(await r.json())
    } catch { setError('Failed to load clients') }
  }

  useEffect(() => { load() }, [])

  async function addClient(e) {
    e.preventDefault()
    if (!newName.trim()) return
    setAdding(true)
    setError('')
    try {
      const r = await apiFetch('/api/clients', {
        method: 'POST',
        headers,
        body: JSON.stringify({ name: newName.trim() }),
      })
      if (r.ok) {
        setNewName('')
        await load()
      } else {
        const d = await r.json()
        setError(d.detail || 'Failed to add client')
      }
    } finally { setAdding(false) }
  }

  async function downloadOvpn(client) {
    const r = await apiFetch(`/api/clients/${client.id}/ovpn`, { headers })
    if (!r.ok) { setError('Download failed'); return }
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${client.name}.ovpn`; a.click()
    URL.revokeObjectURL(url)
  }

  async function deleteClient(client) {
    if (!confirm(`Revoke client "${client.name}"?`)) return
    await apiFetch(`/api/clients/${client.id}`, { method: 'DELETE', headers })
    await load()
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ margin: 0 }}>VPN Clients</h2>
      </div>

      <form onSubmit={addClient} style={{ display: 'flex', gap: 10, marginBottom: 24, maxWidth: 400 }}>
        <input
          placeholder="Client name (e.g. my-laptop)"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          required
        />
        <button type="submit" className="btn-primary" disabled={adding} style={{ whiteSpace: 'nowrap' }}>
          {adding ? 'Adding…' : 'Add client'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      <div className="card">
        <ClientTable clients={clients} onDownload={downloadOvpn} onDelete={deleteClient} />
      </div>
    </div>
  )
}
