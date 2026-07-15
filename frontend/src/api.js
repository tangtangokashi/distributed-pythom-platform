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
  updateProfile: (payload) => request('/api/auth/me', { method: 'PATCH', body: JSON.stringify(payload) }),
  sendPasswordChangeCode: () => request('/api/auth/password-change-code', { method: 'POST' }),
  dashboard: () => request('/api/dashboard'),
  models: () => request('/api/models'),
  alerts: () => request('/api/alerts?limit=100'),
  sentiment: () => request('/api/sentiment'),
  translateReview: async (text) => (await request('/api/reviews/translate', { method: 'POST', body: JSON.stringify({ text }) })).translation,
  orderReview: (orderCode) => request('/api/orders/' + encodeURIComponent(orderCode) + '/review'),
  recommendations: (userId) => request('/api/recommendations/' + encodeURIComponent(userId)),
  aiStatus: () => request('/api/ai/status'),
  simulation: (action) => request('/api/simulation/' + action, { method: 'POST' }),
  injectScenario: (scenario) => request('/api/simulation/inject', { method: 'POST', body: JSON.stringify({ scenario }) }),
  generateReport: () => request('/api/reports/generate', { method: 'POST' }),
  explain: (question) => request('/api/ai/explain', {
    method: 'POST',
    body: JSON.stringify({ question }),
  }),
}
