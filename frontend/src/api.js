// Runtime-configurable API base URL.
//
// window.__API_URL__ is written by /config.js at container startup from the
// API_URL env var. When unset (empty string) fetches stay relative — nginx
// inside the frontend container proxies /api/ → http://core:8080/api/.
//
// Set API_URL when the frontend and API live at different origins, e.g.:
//   API_URL=http://localhost:8080         (local dev, hitting core directly)
//   API_URL=https://vpn.example.com       (behind a reverse proxy on same host)

export const API_BASE = ((window.__API_URL__ || '').trim()).replace(/\/$/, '')

export function apiUrl(path) {
  return API_BASE + path
}

export function apiFetch(path, opts) {
  return fetch(apiUrl(path), opts)
}
