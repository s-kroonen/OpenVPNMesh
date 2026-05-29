import React from 'react'

const COLORS = {
  leader:    '#48bb78',
  follower:  '#63b3ed',
  candidate: '#f6ad55',
  isolated:  '#fc8181',
  dead:      '#718096',
}

export default function HealthBadge({ status }) {
  const color = COLORS[status] || '#718096'
  return (
    <span style={{
      display: 'inline-block',
      background: color + '22',
      color,
      border: `1px solid ${color}55`,
      borderRadius: 4,
      padding: '2px 8px',
      fontSize: 12,
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
    }}>
      {status}
    </span>
  )
}
