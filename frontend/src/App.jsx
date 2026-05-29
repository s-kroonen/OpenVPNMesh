import React, { createContext, useContext, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'

import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Clients from './pages/Clients.jsx'
import Servers from './pages/Servers.jsx'
import Routing from './pages/Routing.jsx'

const AuthCtx = createContext(null)

export function useAuth() {
  return useContext(AuthCtx)
}

function Nav() {
  const { logout } = useAuth()
  const loc = useLocation()
  const links = [
    { to: '/', label: 'Dashboard' },
    { to: '/clients', label: 'Clients' },
    { to: '/servers', label: 'Servers' },
    { to: '/routing', label: 'Routing' },
  ]
  return (
    <nav style={{
      background: '#111827',
      borderBottom: '1px solid #1f2937',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      gap: 24,
      height: 52,
    }}>
      <span style={{ fontWeight: 700, color: '#63b3ed', marginRight: 16 }}>MeshVPN</span>
      {links.map(l => (
        <Link
          key={l.to}
          to={l.to}
          style={{
            color: loc.pathname === l.to ? '#fff' : '#94a3b8',
            fontWeight: loc.pathname === l.to ? 600 : 400,
            fontSize: 14,
          }}
        >{l.label}</Link>
      ))}
      <button
        onClick={logout}
        style={{ marginLeft: 'auto', background: 'transparent', color: '#94a3b8', fontSize: 13 }}
      >Logout</button>
    </nav>
  )
}

function Protected({ children }) {
  const { token } = useAuth()
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('token') || '')

  const login = (t) => {
    sessionStorage.setItem('token', t)
    setToken(t)
  }
  const logout = () => {
    sessionStorage.removeItem('token')
    setToken('')
  }

  return (
    <AuthCtx.Provider value={{ token, login, logout }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={
            <Protected>
              <Nav />
              <div style={{ padding: 24 }}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/clients" element={<Clients />} />
                  <Route path="/servers" element={<Servers />} />
                  <Route path="/routing" element={<Routing />} />
                </Routes>
              </div>
            </Protected>
          } />
        </Routes>
      </BrowserRouter>
    </AuthCtx.Provider>
  )
}
