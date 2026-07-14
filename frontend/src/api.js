const TOKEN_KEY = 'datapulse_access_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

const request = async (path, options = {}) => {
  const token = getToken()
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: 'Bearer ' + token } : {}),
      ...options.headers,
    },
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}))
    if (response.status === 401 && !path.includes('/auth/login')) {
      clearToken()
      window.dispatchEvent(new CustomEvent('auth-expired'))
    }
    const message = Array.isArray(detail.detail)
      ? detail.detail.map((item) => item.msg?.replace(/^Value error, /, '')).join('；')
      : detail.detail
    throw new Error(message || '请求失败 (' + response.status + ')')
  }
  return response.json()
}

export const platformApi = {
  sendEmailCode: (email) => request('/api/auth/email-code', { method: 'POST', body: JSON.stringify({ email }) }),
  register: (payload) => request('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload) => request('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  me: () => request('/api/auth/me'),
  dashboard: () => request('/api/dashboard'),
  models: () => request('/api/models'),
  simulation: (action) => request('/api/simulation/' + action, { method: 'POST' }),
  explain: (question) => request('/api/ai/explain', {
    method: 'POST',
    body: JSON.stringify({ question }),
  }),
}
