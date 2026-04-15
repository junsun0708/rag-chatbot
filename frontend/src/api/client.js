const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const chatAPI = {
  ask: (question) => request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  }),
}

export const docAPI = {
  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/documents/upload', { method: 'POST', body: form })
  },
  sources: () => request('/documents/sources'),
}

export const integrationAPI = {
  syncConfluence: (config) => request('/integrations/confluence/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  }),
  syncNotion: (config) => request('/integrations/notion/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  }),
}
