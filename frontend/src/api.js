const request = async (path, options = {}) => {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}))
    throw new Error(detail.detail || '请求失败 (' + response.status + ')')
  }
  return response.json()
}

export const platformApi = {
  dashboard: () => request('/api/dashboard'),
  models: () => request('/api/models'),
  simulation: (action) => request('/api/simulation/' + action, { method: 'POST' }),
  explain: (question) => request('/api/ai/explain', {
    method: 'POST',
    body: JSON.stringify({ question }),
  }),
}
