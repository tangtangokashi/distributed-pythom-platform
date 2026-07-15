<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue'
import { clearToken, getToken, platformApi } from './api'
import { useDeviceCapability } from './composables/useDeviceCapability'
import AuthGate from './components/AuthGate.vue'
import TwoDTopology from './components/TwoDTopology.vue'

const ClusterTwin = defineAsyncComponent(() => import('./components/three/ClusterTwin.vue'))
const FinanceTerrain = defineAsyncComponent(() => import('./components/three/FinanceTerrain.vue'))
const CommerceWorld = defineAsyncComponent(() => import('./components/three/CommerceWorld.vue'))

const navGroups = [
  { label: '业务监控', items: [['overview', '运营总览', '▦'], ['finance', '金融风险', '⌁'], ['ecommerce', '电商运营', '◇'], ['sentiment', '评论分析', '☷']] },
  { label: '智能决策', items: [['recommendations', '推荐中心', '★'], ['models', '模型中心', '⬡'], ['reports', '报告中心', '▤'], ['assistant', '智能助手', '✦']] },
]
const pageMeta = {
  overview: ['运营总览', '掌握业务脉搏，快速识别值得关注的变化'],
  finance: ['金融风险中心', '跟踪核心标的走势、短期预测与异常波动'],
  ecommerce: ['电商运营中心', '聚焦订单表现、异常交易与高价值用户'],
  recommendations: ['个性化推荐中心', '基于真实 Olist 历史订单的用户-品类协同过滤推荐'],
  orderReview: ['订单评论分析', '查看所选 Olist 真实订单及其对应的商品评价'],
  sentiment: ['评价分析中心', '订单评价与独立中文商品评价分析库分开管理'],
  models: ['模型中心', '统一查看模型能力、运行方式与服务状态'],
  reports: ['运营与风控报告', '汇总真实回放、模型告警和中文评论洞察，生成可下载报告'],
  assistant: ['智能分析助手', '将实时指标转化为清晰、可执行的业务判断'],
}
const active = ref('overview')
const mobileOpen = ref(false)
const loading = ref(true)
const connected = ref(false)
const error = ref('')
const dashboard = ref(null)
const models = ref([])
const sentiment = ref({ chinese: { counts: {}, samples: [], keywords: [], total: 0 }, olist: { counts: {}, samples: [], keywords: [], total: 0 } })
const reviewSource = ref('olist')
const reviewTranslations = ref({})
const translatingReview = ref('')
const aiStatus = ref({ provider: '正在检测', model: '…', connected: false })
const allAlerts = ref([])
const alertPanelOpen = ref(false)
const modelDetail = ref(null)
const orderReview = ref(null)
const orderReviewLoading = ref(false)
const profileOpen = ref(false)
const profileSaving = ref(false)
const profileCodeSending = ref(false)
const profileCodeMessage = ref('')
const profileError = ref('')
const profileForm = ref({ name: '', current_password: '', new_password: '', confirm_password: '', verification_code: '' })
const report = ref(null)
const reportGenerating = ref(false)
const recommendation = ref(null)
const recommendationLoading = ref(false)
const selectedRecommendationUser = ref('')
const question = ref('')
const answer = ref('你好，我可以根据当前聚合指标解释风险信号，并给出运营建议。')
const asking = ref(false)
const authChecked = ref(false)
const currentUser = ref(null)
const { desktop, reducedMotion, webgl } = useDeviceCapability()
const canRenderThree = computed(() => desktop.value && webgl.value)
const userInitials = computed(() => currentUser.value?.name?.slice(0, 2).toUpperCase() || '用户')
let timer

const meta = computed(() => pageMeta[active.value])
const kpis = computed(() => dashboard.value?.kpis || {})
const ticks = computed(() => dashboard.value?.ticks || [])
const alerts = computed(() => dashboard.value?.alerts || [])
const orders = computed(() => dashboard.value?.orders_feed || [])
const recommendationUsers = computed(() => [...new Set(orders.value.map((order) => order.user_id).filter(Boolean))].slice(0, 12))
const nodes = computed(() => dashboard.value?.nodes || [])
const stream = computed(() => dashboard.value?.stream || {})
const exerciseEvents = computed(() => dashboard.value?.exercise_events || [])
const activeSentiment = computed(() => sentiment.value?.[reviewSource.value] || { counts: {}, samples: [], keywords: [], total: 0 })
const latestStocks = computed(() => {
  const latest = new Map()
  ticks.value.forEach((tick) => latest.set(tick.symbol, tick))
  return ['AAPL', 'TSLA', 'NVDA'].map((symbol) => latest.get(symbol)).filter(Boolean)
})
const chartLines = computed(() => ['AAPL', 'TSLA', 'NVDA'].map((symbol) => {
  const values = ticks.value.filter((tick) => tick.symbol === symbol).map((tick) => tick.price)
  if (!values.length) return { symbol, points: '' }
  const min = Math.min(...values), max = Math.max(...values), span = max - min || 1
  return { symbol, points: values.map((value, index) => {
    const x = values.length === 1 ? 50 : 4 + index / (values.length - 1) * 92
    return x + ',' + (86 - (value - min) / span * 68)
  }).join(' ') }
}))
const modelCounts = computed(() => ({
  online: models.value.filter((m) => m.status === '在线').length,
  batch: models.value.filter((m) => m.status === '批处理').length,
  pending: models.value.filter((m) => m.status === '待训练').length,
}))

async function refresh() {
  try {
    dashboard.value = await platformApi.dashboard()
    connected.value = true; error.value = ''
  } catch {
    connected.value = false; error.value = '后端暂未连接，正在等待 FastAPI 服务…'
  } finally { loading.value = false }
}
async function loadModels() { try { models.value = await platformApi.models() } catch { models.value = [] } }
async function loadExtras() {
  const [sentimentResult, aiResult] = await Promise.allSettled([platformApi.sentiment(), platformApi.aiStatus()])
  if (sentimentResult.status === 'fulfilled') sentiment.value = sentimentResult.value
  if (aiResult.status === 'fulfilled') aiStatus.value = aiResult.value
}
async function openAlerts() {
  alertPanelOpen.value = true
  try { allAlerts.value = await platformApi.alerts() }
  catch (err) { error.value = err.message }
}
function openModel(model) { modelDetail.value = model }
async function inspectOrder(order) {
  active.value = 'orderReview'; orderReview.value = { order, reviews: [], analysis: {} }; orderReviewLoading.value = true
  window.scrollTo({ top: 0, behavior: 'smooth' })
  try { orderReview.value = await platformApi.orderReview(order.order_code) }
  catch (err) { error.value = err.message }
  finally { orderReviewLoading.value = false }
}
function openProfile() {
  profileError.value = ''
  profileCodeMessage.value = ''
  profileForm.value = { name: currentUser.value?.name || '', current_password: '', new_password: '', confirm_password: '', verification_code: '' }
  profileOpen.value = true
}
async function saveProfile() {
  profileError.value = ''
  if (profileForm.value.new_password && profileForm.value.new_password !== profileForm.value.confirm_password) { profileError.value = '两次输入的新密码不一致'; return }
  if (profileForm.value.new_password && !profileForm.value.verification_code) { profileError.value = '修改密码前请先获取并填写邮箱验证码'; return }
  profileSaving.value = true
  try {
    currentUser.value = await platformApi.updateProfile({ name: profileForm.value.name, current_password: profileForm.value.current_password || null, new_password: profileForm.value.new_password || null, verification_code: profileForm.value.verification_code || null })
    profileOpen.value = false
  } catch (err) { profileError.value = err.message }
  finally { profileSaving.value = false }
}
async function sendPasswordCode() {
  profileError.value = ''; profileCodeMessage.value = ''; profileCodeSending.value = true
  try { profileCodeMessage.value = (await platformApi.sendPasswordChangeCode()).message }
  catch (err) { profileError.value = err.message }
  finally { profileCodeSending.value = false }
}
async function control(action) {
  try { await platformApi.simulation(action); await refresh() }
  catch (err) { error.value = err.message }
}
async function injectScenario(scenario) {
  try { await platformApi.injectScenario(scenario); await refresh() }
  catch (err) { error.value = err.message }
}
async function loadRecommendations(userId = selectedRecommendationUser.value) {
  if (!userId) return
  selectedRecommendationUser.value = userId; recommendationLoading.value = true
  try { recommendation.value = await platformApi.recommendations(userId) }
  catch (err) { error.value = err.message }
  finally { recommendationLoading.value = false }
}
async function generateReport() {
  reportGenerating.value = true
  try { report.value = await platformApi.generateReport() }
  catch (err) { error.value = err.message }
  finally { reportGenerating.value = false }
}
async function translateReview(text) {
  if (!text || translatingReview.value) return
  if (reviewTranslations.value[text]) return
  translatingReview.value = text
  try { reviewTranslations.value = { ...reviewTranslations.value, [text]: await platformApi.translateReview(text) } }
  catch (err) { error.value = err.message }
  finally { translatingReview.value = '' }
}
function downloadReport() {
  if (!report.value?.answer) return
  downloadBlob(report.value.answer, 'text/markdown;charset=utf-8', `DataPulse运营风控报告-${new Date().toISOString().slice(0, 10)}.md`)
}
function downloadBlob(content, type, filename) {
  const blob = new Blob([content], { type })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}
function reportHtml() {
  const title = 'DataPulse 运营与风控报告'
  const body = (report.value?.answer || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
  return `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title><style>body{font-family:"Microsoft YaHei",Arial,sans-serif;max-width:860px;margin:42px auto;color:#172033;line-height:1.8}h1{font-size:25px;border-bottom:2px solid #3f8fe2;padding-bottom:12px}.meta{color:#718096;font-size:12px;margin-bottom:24px}.content{white-space:normal;font-size:14px}</style></head><body><h1>${title}</h1><p class="meta">${report.value?.source || ''} · ${new Date(report.value?.generated_at || Date.now()).toLocaleString('zh-CN')}</p><div class="content">${body}</div></body></html>`
}
function downloadWordReport() {
  if (!report.value?.answer) return
  downloadBlob(reportHtml(), 'application/msword;charset=utf-8', `DataPulse运营风控报告-${new Date().toISOString().slice(0, 10)}.doc`)
}
function exportPdfReport() {
  if (!report.value?.answer) return
  const printWindow = window.open('', '_blank')
  if (!printWindow) { error.value = '浏览器阻止了 PDF 导出窗口，请允许弹出窗口后重试'; return }
  printWindow.document.write(reportHtml())
  printWindow.document.close()
  printWindow.focus()
  printWindow.onafterprint = () => printWindow.close()
  setTimeout(() => printWindow.print(), 200)
}
async function ask(text = question.value) {
  if (!text.trim() || asking.value) return
  question.value = text; asking.value = true; answer.value = '正在分析当前实时指标…'
  try { answer.value = (await platformApi.explain(text)).answer }
  catch (err) { answer.value = '分析暂时不可用：' + err.message }
  finally { asking.value = false }
}
function switchPage(id) {
  active.value = id; mobileOpen.value = false; window.scrollTo({ top: 0, behavior: 'smooth' })
  if (id === 'recommendations' && !selectedRecommendationUser.value && recommendationUsers.value[0]) loadRecommendations(recommendationUsers.value[0])
}
async function startSession(user) {
  currentUser.value = user
  loading.value = true
  await Promise.all([refresh(), loadModels(), loadExtras()])
  clearInterval(timer)
  timer = setInterval(refresh, 2500)
}
async function restoreSession() {
  if (!getToken()) { authChecked.value = true; return }
  try { await startSession(await platformApi.me()) }
  catch { clearToken(); currentUser.value = null }
  finally { authChecked.value = true }
}
function logout() { clearToken(); currentUser.value = null; dashboard.value = null; models.value = []; clearInterval(timer) }
function expireSession() { currentUser.value = null; dashboard.value = null; clearInterval(timer) }
onMounted(() => { window.addEventListener('auth-expired', expireSession); restoreSession() })
onBeforeUnmount(() => { clearInterval(timer); window.removeEventListener('auth-expired', expireSession) })
</script>

<template>
  <div v-if="!authChecked" class="auth-boot"><div class="brand-mark"><i></i><i></i><i></i></div><p>正在恢复登录状态…</p></div>
  <AuthGate v-else-if="!currentUser" @authenticated="startSession" />
  <div v-else class="app-shell">
    <aside :class="['sidebar', { open: mobileOpen }]">
      <div class="brand"><div class="brand-mark"><i></i><i></i><i></i></div><div><strong>DataPulse</strong><small>智能决策平台</small></div></div>
      <nav><section v-for="group in navGroups" :key="group.label" class="nav-group"><p class="nav-caption">{{ group.label }}</p><button v-for="item in group.items" :key="item[0]" :class="['nav-link', { active: active === item[0] }]" @click="switchPage(item[0])"><b>{{ item[2] }}</b><span>{{ item[1] }}</span><i v-if="item[0] === 'overview' && alerts.length">{{ alerts.length }}</i></button></section></nav>
      <div class="sidebar-foot"><div class="environment"><div><i></i><strong>数据服务状态</strong></div><p>金融 OHLCV、Olist 订单与商品评价均按历史时间顺序加载。</p></div><div class="profile"><span>{{ userInitials }}</span><div><strong>{{ currentUser.name }}</strong><small>{{ currentUser.email }}</small></div><button class="logout-button" title="退出登录" @click="logout">退出</button></div></div>
    </aside>
    <div v-if="mobileOpen" class="scrim" @click="mobileOpen = false"></div>

    <main>
      <header class="topbar"><button class="menu" @click="mobileOpen = true">☰</button><div class="breadcrumb"><span>智能决策平台</span><b>/</b><strong>{{ meta[0] }}</strong></div><div class="top-actions"><span :class="['connection', { offline: !connected }]"><i></i>{{ connected ? '数据已连接' : '等待连接' }}</span><button class="bell" title="风险告警中心" @click="openAlerts">◌<i v-if="alerts.length"></i></button><button class="avatar avatar-button" :title="'编辑 ' + currentUser.email + ' 的个人资料'" @click="openProfile">{{ userInitials }}</button></div></header>
      <div class="content">
        <section class="page-heading"><div><span>真实历史数据回放</span><h1>{{ meta[0] }}</h1><p>{{ meta[1] }}</p></div><div><span class="live"><i></i>实时更新</span><time>{{ new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' }) }}</time></div></section>
        <div v-if="error" class="banner"><b>!</b>{{ error }}<button @click="refresh">重新连接</button></div>
        <div v-if="loading" class="loading"><i></i><p>正在加载业务数据…</p></div>

        <template v-else-if="active === 'overview'">
          <section class="metrics">
            <article><div><span class="metric-icon blue">订</span><em>实时</em></div><p>累计订单</p><h2>{{ (kpis.orders || 0).toLocaleString() }}</h2><small>当前回放窗口</small></article>
            <article><div><span class="metric-icon purple">R$</span><em>聚合</em></div><p>总交易额</p><h2>R${{ Number(kpis.gmv || 0).toLocaleString(undefined, { maximumFractionDigits: 0 }) }}</h2><small>Olist 订单金额累计</small></article>
            <article><div><span class="metric-icon green">人</span><em>活跃</em></div><p>活跃用户</p><h2>{{ kpis.active_users || 0 }}</h2><small>近实时估算</small></article>
            <article class="risk"><div><span class="metric-icon red">!</span><em>需关注</em></div><p>风险告警</p><h2>{{ kpis.alerts || 0 }}</h2><small>最近检测结果</small></article>
          </section>
          <ClusterTwin v-if="canRenderThree" :nodes="nodes" :stream="stream" :connected="connected" :reduced-motion="reducedMotion" />
          <TwoDTopology type="cluster" :nodes="nodes" :stream="stream" :ticks="ticks" :orders="orders" :alerts="alerts" @navigate="switchPage" />
          <section class="grid main-grid">
            <article class="panel chart-panel"><div class="panel-head"><div><h3>市场走势</h3><p>核心标的实时价格变化</p></div><div class="legend"><span>AAPL</span><span>TSLA</span><span>NVDA</span></div></div><div class="chart"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><g><line x1="0" y1="20" x2="100" y2="20"/><line x1="0" y1="52" x2="100" y2="52"/><line x1="0" y1="84" x2="100" y2="84"/></g><polyline v-for="line in chartLines" :key="line.symbol" :class="line.symbol.toLowerCase()" :points="line.points" fill="none" vector-effect="non-scaling-stroke"/></svg></div><div class="chart-foot"><span>较早</span><span>实时价格流</span><span>现在</span></div></article>
            <article class="panel"><div class="panel-head"><div><h3>计算资源</h3><p>服务节点与处理指标</p></div><span class="badge">服务状态</span></div><div class="node-list"><div v-for="node in nodes" :key="node.name" class="node"><span>{{ node.name.includes('1') ? '主' : '算' }}</span><div><strong>{{ node.name }}</strong><small>{{ node.role }}</small></div><em><i></i>正常</em></div></div><div class="stream"><div><small>处理事件</small><strong>{{ (stream.kafka_messages || 0).toLocaleString() }}</strong></div><div><small>处理延迟</small><strong>{{ stream.spark_latency || 0 }} ms</strong></div></div></article>
          </section>
          <section class="grid bottom-grid">
            <article class="panel"><div class="panel-head"><div><h3>最新风险告警</h3><p>模型检测到的业务异常</p></div><button @click="openAlerts">查看全部</button></div><div v-if="alerts.length" class="alert-list"><div v-for="alert in alerts.slice(0, 4)" :key="alert.id" class="alert"><span :class="alert.severity === '高' ? 'high' : ''">{{ alert.severity }}</span><div><strong>{{ alert.title }}</strong><small>{{ alert.detail }}</small></div><time>{{ alert.time }}</time></div></div><div v-else class="empty"><span>✓</span><strong>当前运行平稳</strong><p>暂未检测到需要关注的异常</p></div></article>
            <article class="panel control"><div class="panel-head"><div><h3>真实数据回放</h3><p>按历史顺序回放金融 OHLCV 与 Olist 真实订单</p></div><span :class="['run-status', { paused: !dashboard?.running }]">{{ dashboard?.running ? '运行中' : '已暂停' }}</span></div><div class="control-state"><span :class="{ paused: !dashboard?.running }">{{ dashboard?.running ? '▶' : 'Ⅱ' }}</span><div><strong>{{ dashboard?.running ? '真实历史事件正在连续回放' : '数据回放已暂停' }}</strong><p>开始回放：每秒推进一组事件；单步生成：只推进一组，便于讲解。</p></div></div><div class="buttons"><button class="primary" @click="control('start')">开始回放</button><button @click="control('stop')">暂停</button><button @click="control('step')">单步生成</button></div></article>
          </section>
          <section class="panel exercise-panel"><div class="panel-head"><div><h3>风险测试</h3><p>在历史数据回放上叠加独立标识的控制事件，检查异常检测和处置链路是否正常工作。</p></div><span class="badge">控制事件</span></div><div class="exercise-actions"><button @click="injectScenario('market_shock')"><b>金融</b><strong>加入市场剧烈波动</strong><small>价格 ±6.8% 与成交量放大</small></button><button @click="injectScenario('large_order')"><b>订单</b><strong>加入大额异常订单</strong><small>触发 Isolation Forest 检测</small></button><button @click="injectScenario('negative_reviews')"><b>评论</b><strong>加入负面评论激增</strong><small>触发舆情风险联动</small></button></div><div v-if="exerciseEvents.length" class="exercise-timeline"><div v-for="event in exerciseEvents" :key="event.time + event.title"><time>{{ event.time }}</time><span>{{ event.type }}</span><strong>{{ event.title }}</strong><p>{{ event.detail }}</p></div></div><div v-else class="exercise-empty">尚无控制事件。</div></section>
        </template>

        <template v-else-if="active === 'finance'">
          <section class="stock-grid"><article v-for="stock in latestStocks" :key="stock.symbol"><div class="stock-title"><span>{{ stock.symbol[0] }}</span><div><strong>{{ stock.symbol }}</strong><small>NASDAQ · 实时</small></div></div><h2>${{ stock.price.toFixed(2) }}</h2><em :class="stock.change_pct >= 0 ? 'positive' : 'negative'">{{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct.toFixed(2) }}%</em><div class="bars"><i v-for="n in 13" :key="n" :style="{ height: (25 + ((n * 17 + stock.price) % 65)) + '%' }"></i></div></article></section>
          <FinanceTerrain v-if="canRenderThree" :ticks="ticks" :connected="connected" :reduced-motion="reducedMotion" />
          <TwoDTopology type="finance" :ticks="ticks" />
          <section class="grid main-grid"><article class="panel chart-panel"><div class="panel-head"><div><h3>多标的行情对比</h3><p>AAPL、TSLA 与 NVDA 实时价格趋势</p></div><span class="badge">Isolation Forest</span></div><div class="chart large"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><g><line x1="0" y1="20" x2="100" y2="20"/><line x1="0" y1="52" x2="100" y2="52"/><line x1="0" y1="84" x2="100" y2="84"/></g><polyline v-for="line in chartLines" :key="line.symbol" :class="line.symbol.toLowerCase()" :points="line.points" fill="none" vector-effect="non-scaling-stroke"/></svg></div></article><article class="panel"><div class="panel-head"><div><h3>金融风险信号</h3><p>最新异常波动记录</p></div></div><div class="alert-list"><div v-for="a in alerts.filter(x => x.domain === 'finance')" :key="a.id" class="alert"><span class="high">{{ a.severity }}</span><div><strong>{{ a.title }}</strong><small>{{ a.detail }}</small></div><time>{{ a.time }}</time></div><div v-if="!alerts.some(x => x.domain === 'finance')" class="empty"><span>✓</span><strong>市场风险平稳</strong><p>当前没有异常波动</p></div></div></article></section>
        </template>

        <template v-else-if="active === 'ecommerce'">
          <section class="metrics three"><article><p>累计订单</p><h2>{{ (kpis.orders || 0).toLocaleString() }}</h2><small>Olist 巴西历史订单回放</small></article><article><p>总交易额</p><h2>R${{ Number(kpis.gmv || 0).toLocaleString(undefined, { maximumFractionDigits: 0 }) }}</h2><small>巴西雷亚尔 GMV 聚合</small></article><article><p>平均客单价</p><h2>R${{ kpis.orders ? Math.round(kpis.gmv / kpis.orders).toLocaleString() : 0 }}</h2><small>真实巴西订单金额 / 订单数</small></article></section>
          <CommerceWorld v-if="canRenderThree" :orders="orders" :connected="connected" :reduced-motion="reducedMotion" />
          <TwoDTopology type="commerce" :orders="orders" />
          <section class="grid commerce-grid"><article class="panel orders"><div class="panel-head"><div><h3>实时订单</h3><p>Olist 巴西历史交易与异常检测结果 · 点击订单查看对应评论</p></div><span class="badge">{{ orders.length }} 条动态</span></div><div class="table"><div class="table-head"><span>时间 / 订单号</span><span>商品</span><span>区域</span><span>金额</span><span>状态</span></div><button v-for="o in orders.slice(0, 10)" :key="o.order_code" :class="['table-row order-row', { anomaly: o.is_anomaly }]" @click="inspectOrder(o)"><span><small>{{ o.time }}</small><strong>{{ o.order_code }}</strong></span><span>{{ o.product }}</span><span>{{ o.region }}</span><span>R${{ o.amount.toLocaleString() }}</span><em :class="{ danger: o.is_anomaly }">{{ o.is_anomaly ? '异常' : '正常' }}</em></button></div></article><article class="panel"><div class="panel-head"><div><h3>用户价值分层</h3><p>K-Means 聚类结果示例</p></div></div><div class="segments"><div v-for="user in [['U1090','高价值用户','R$2,890 · 13 笔订单',88],['U1012','活跃用户','R$1,680 · 8 笔订单',66],['U1048','潜力用户','R$590 · 4 笔订单',38]]" :key="user[0]"><span>{{ user[0] }}</span><strong>{{ user[1] }}</strong><p>{{ user[2] }}</p><div><i :style="{ width: user[3] + '%' }"></i></div><small>推荐：智能手表、无线耳机</small></div></div></article></section>
        </template>

        <template v-else-if="active === 'orderReview'">
          <button class="back-button" @click="switchPage('ecommerce')">← 返回电商运营</button>
          <section v-if="orderReview" class="order-review-page"><article class="panel order-summary"><div class="panel-head"><div><h3>订单信息</h3><p>来自 Olist Brazilian E-Commerce Dataset 的真实历史订单</p></div><span class="badge">{{ orderReviewLoading ? '读取评价中' : '真实订单' }}</span></div><dl><div><dt>回放订单号</dt><dd>{{ orderReview.order.order_code }}</dd></div><div><dt>真实源订单 ID</dt><dd>{{ orderReview.order.source_order_id }}</dd></div><div><dt>商品品类</dt><dd>{{ orderReview.order.category }}</dd></div><div><dt>巴西地区</dt><dd>{{ orderReview.order.region }}</dd></div><div><dt>订单金额</dt><dd>R${{ Number(orderReview.order.amount).toLocaleString() }}</dd></div><div><dt>历史下单时间</dt><dd>{{ orderReview.order.source_time }}</dd></div></dl></article><article class="panel review-analysis"><div class="panel-head"><div><h3>该订单的评论分析</h3><p>{{ orderReview.analysis?.source }}</p></div></div><div v-if="orderReviewLoading" class="empty"><span>…</span><strong>正在读取该订单的真实评价</strong></div><div v-else-if="orderReview.reviews?.length" class="order-review-list"><article v-for="(review, index) in orderReview.reviews" :key="index"><header><span :class="review.sentiment === '正面' ? 'positive' : review.sentiment === '负面' ? 'negative' : 'neutral'">{{ review.sentiment }}</span><strong>{{ review.score }} / 5 ★</strong><time>{{ review.date }}</time></header><div v-if="review.translation" class="review-translation"><strong>中文译文（DeepSeek）</strong><p>{{ review.translation }}</p></div><p class="review-original"><b>原文：</b>{{ review.text }}</p></article><div class="review-method"><strong>分析方法</strong><p>{{ orderReview.analysis?.summary }}</p></div></div><div v-else class="empty"><span>○</span><strong>该订单没有可用评价记录</strong><p>Olist 数据集中并非每笔订单都包含评论；订单信息仍为真实数据。</p></div></article></section>
          <div v-else class="panel empty"><span>!</span><strong>未选择订单</strong><p>请返回电商运营页，从实时订单列表选择一笔订单。</p></div>
        </template>

        <template v-else-if="active === 'recommendations'">
          <section class="recommend-hero"><div><span>COLLABORATIVE FILTERING</span><h2>真实订单驱动的个性化推荐</h2><p>从 Olist 全量已完成订单中提取用户—品类隐式交互，通过相似用户的共同购买行为推荐尚未购买的品类。</p></div><span class="badge">协同过滤推荐</span></section>
          <section class="panel user-selector"><div class="panel-head"><div><h3>选择回放用户</h3><p>用户来自当前实时订单流；选择后计算其历史偏好和相似用户推荐。</p></div></div><div class="user-chips"><button v-for="userId in recommendationUsers" :key="userId" :class="{ active: selectedRecommendationUser === userId }" @click="loadRecommendations(userId)">{{ userId.slice(0, 8) }}…</button><span v-if="!recommendationUsers.length">等待真实订单回放数据…</span></div></section>
          <section v-if="recommendationLoading" class="panel empty"><span>…</span><strong>正在计算协同过滤推荐</strong><p>正在从真实历史订单中检索相似用户。</p></section>
          <section v-else-if="recommendation" class="grid recommendation-grid"><article class="panel recommendation-profile"><div class="panel-head"><div><h3>用户购买偏好</h3><p>{{ recommendation.is_cold_start ? '冷启动用户：使用真实订单热门品类' : '由历史购买品类构成的隐式反馈画像' }}</p></div><span class="badge">{{ recommendation.user_id.slice(0, 10) }}…</span></div><div v-if="recommendation.history.length" class="history-tags"><span v-for="item in recommendation.history" :key="item.category">{{ item.category }} <b>{{ item.count }}</b></span></div><div v-else class="empty"><span>○</span><strong>历史交互不足</strong><p>已自动转为热门品类冷启动推荐。</p></div><div class="recommend-method"><strong>推荐算法</strong><p>{{ recommendation.method }}</p></div></article><article class="panel recommendation-results"><div class="panel-head"><div><h3>推荐商品品类</h3><p>基于 Olist 真实订单中用户的共同购买关系</p></div></div><div class="recommend-list"><article v-for="(item, index) in recommendation.items" :key="item.category"><span>{{ index + 1 }}</span><div><strong>{{ item.display_name }}</strong><small>代表商品 ID：{{ item.product_hint }}…</small><p>{{ item.reason }}</p></div><em>推荐分 {{ item.score }}</em></article><div v-if="!recommendation.items.length" class="empty"><span>○</span><strong>暂未得到推荐</strong><p>请尝试选择另一位回放用户。</p></div></div></article></section>
          <section v-else class="panel empty"><span>★</span><strong>请选择一位回放用户</strong><p>系统将使用用户-品类协同过滤生成推荐结果。</p></section>
        </template>

        <template v-else-if="active === 'sentiment'">
          <section class="review-source-switch" aria-label="评价数据源"><button :class="{ active: reviewSource === 'olist' }" @click="reviewSource = 'olist'"><strong>Olist 订单评价</strong><span>与巴西订单关联 · 葡萄牙语原文</span></button><button :class="{ active: reviewSource === 'chinese' }" @click="reviewSource = 'chinese'"><strong>中文商品评价分析库</strong><span>SE-ABSA16 · 独立公开数据集</span></button></section>
          <section class="metrics three sentiment-metrics"><article><span class="metric-icon green">+</span><p>正面评价</p><h2>{{ activeSentiment.counts?.['正面'] || 0 }}</h2><small>{{ reviewSource === 'chinese' ? '独立中文商品评价正向样本' : 'Olist 订单关联的正向评价' }}</small></article><article><span class="metric-icon purple">○</span><p>中性评价</p><h2>{{ activeSentiment.counts?.['中性'] || 0 }}</h2><small>{{ reviewSource === 'chinese' ? '该数据集未提供中性标签' : 'Olist 三星评价样本' }}</small></article><article class="risk"><span class="metric-icon red">!</span><p>负面评价</p><h2>{{ activeSentiment.counts?.['负面'] || 0 }}</h2><small>{{ reviewSource === 'chinese' ? '独立中文商品评价负向样本' : 'Olist 订单关联的负向评价' }}</small></article></section>
          <section class="grid sentiment-grid"><article class="panel"><div class="panel-head"><div><h3>{{ reviewSource === 'chinese' ? '中文商品评价情感分布' : 'Olist 订单评价情感分布' }}</h3><p>{{ activeSentiment.source || '正在加载评价数据' }}</p></div><span class="badge">{{ activeSentiment.total || 0 }} 条样本</span></div><div class="sentiment-bars"><div v-for="item in [['正面','positive'],['中性','neutral'],['负面','negative']]" :key="item[0]"><span>{{ item[0] }}</span><div><i :class="item[1]" :style="{ width: (activeSentiment.total ? ((activeSentiment.counts?.[item[0]] || 0) / activeSentiment.total * 100) : 0) + '%' }"></i></div><b>{{ activeSentiment.counts?.[item[0]] || 0 }}</b></div></div><h4 class="keyword-title">{{ reviewSource === 'chinese' ? '商品关注方面' : '葡萄牙语高频词' }}</h4><div class="keywords"><span v-for="word in activeSentiment.keywords" :key="word.word">{{ word.word }} <b>{{ word.count }}</b></span></div></article><article class="panel"><div class="panel-head"><div><h3>{{ reviewSource === 'chinese' ? '独立中文评价样本' : 'Olist 订单评价原文' }}</h3><p v-if="reviewSource === 'chinese'">SE-ABSA16 公开数据集，不与 Olist 订单关联。</p></div></div><div class="review-list"><div v-for="review in activeSentiment.samples?.slice(0, 6)" :key="review.text"><span :class="review.sentiment === '正面' ? 'positive' : review.sentiment === '负面' ? 'negative' : 'neutral'">{{ review.sentiment }} · {{ review.score }}</span><p>{{ review.text }}</p><div v-if="reviewSource === 'olist'" class="review-translate"><button :disabled="translatingReview === review.text" @click="translateReview(review.text)">{{ translatingReview === review.text ? '翻译中…' : '翻译为中文' }}</button><p v-if="reviewTranslations[review.text]">{{ reviewTranslations[review.text] }}</p></div><small>{{ reviewSource === 'chinese' ? review.aspect + ' · ' : '' }}{{ review.date }}</small></div><div v-if="!activeSentiment.samples?.length" class="empty"><span>…</span><strong>暂无可用评价</strong></div></div></article></section>
        </template>

        <template v-else-if="active === 'models'">
          <section class="metrics three"><article><span class="metric-icon green">✓</span><p>在线模型</p><h2>{{ modelCounts.online }}</h2><small>提供实时推理</small></article><article><span class="metric-icon blue">↻</span><p>批处理模型</p><h2>{{ modelCounts.batch }}</h2><small>按任务调度运行</small></article><article><span class="metric-icon purple">…</span><p>待训练模型</p><h2>{{ modelCounts.pending }}</h2><small>等待训练资源</small></article></section>
          <section class="models"><article v-for="model in models" :key="model.name"><div><span class="model-glyph">M</span><em :class="model.status === '在线' ? 'online' : model.status === '批处理' ? 'batch' : 'pending'"><i></i>{{ model.status }}</em></div><h3>{{ model.name }}</h3><p>{{ model.purpose }}</p><section><small>模型指标</small><strong>{{ model.metric }}</strong></section><footer><span>最近更新：今天</span><button @click="openModel(model)">查看详情 →</button></footer></article></section><div class="info"><span>i</span><div><strong>模型运行环境</strong><p>在线模型由 Web 服务提供推理；Spark ALS 与 LSTM 可在部署后作为独立计算任务运行。</p></div></div>
        </template>

        <template v-else-if="active === 'reports'">
          <section class="report-hero"><div><span>AI REPORTING CENTER</span><h2>运营与风控报告</h2><p>基于当前聚合指标、风险告警、控制事件和评论情感统计生成；不传输原始订单或用户信息。</p></div><button class="primary" :disabled="reportGenerating" @click="generateReport">{{ reportGenerating ? 'DeepSeek 正在生成…' : '生成报告' }}</button></section>
          <section class="grid report-source-grid"><article class="panel"><h3>数据范围</h3><ul><li>金融：AAPL、TSLA、NVDA 历史 OHLCV</li><li>电商：Olist 订单与异常检测结果</li><li>评论：Olist 订单关联的巴西评价</li><li>风险：模型告警与已记录的控制事件</li></ul></article><article class="panel"><h3>报告内容</h3><ul><li>关键经营指标与趋势</li><li>风险事件和订单评价洞察</li><li>可执行的运营与风控建议</li><li>生成时间与模型来源</li></ul></article></section>
          <section v-if="report" class="panel generated-report"><div class="panel-head"><div><h3>已生成报告</h3><p>{{ report.source }} · {{ new Date(report.generated_at).toLocaleString('zh-CN') }}</p></div><div class="report-downloads"><button @click="downloadReport">Markdown</button><button @click="downloadWordReport">导出 Word</button><button @click="exportPdfReport">导出 PDF</button></div></div><pre>{{ report.answer }}</pre></section>
          <section v-else class="panel empty report-empty"><span>▤</span><strong>暂无报告</strong></section>
        </template>

        <template v-else>
          <section class="assistant"><article><div class="assistant-intro"><span>✦</span><div><small>AI 分析助手</small><h2>今天想了解哪些业务变化？</h2><p>我会使用当前订单、交易额和风险告警等聚合指标进行分析。</p><span :class="['ai-provider', { fallback: !aiStatus.connected }]">{{ aiStatus.connected ? `已接入 DeepSeek · ${aiStatus.model}` : '未配置 DeepSeek 服务' }}</span></div></div><div class="answer"><span>AI</span><p>{{ answer }}</p></div><div class="question"><textarea v-model="question" rows="3" placeholder="输入你的问题，例如：当前有哪些需要关注的风险？" @keydown.ctrl.enter="ask()"></textarea><div><span>Ctrl + Enter 发送</span><button :disabled="asking || !question.trim()" @click="ask()">{{ asking ? '分析中…' : '发送问题' }} ↑</button></div></div></article><aside><article class="panel"><div class="panel-head"><div><h3>快捷问题</h3><p>从常用分析开始</p></div></div><button v-for="prompt in ['当前系统健康状态如何？','最近的异常订单是什么原因？','是否有需要关注的风险信号？','给出当前运营建议']" :key="prompt" class="prompt" @click="ask(prompt)"><span>↗</span>{{ prompt }}</button></article><div class="privacy"><span>盾</span><div><strong>数据隐私保护</strong><p>仅提交订单数、GMV 和告警摘要，不传输原始订单或个人信息。</p></div></div></aside></section>
        </template>
      </div>
    </main>
    <div v-if="alertPanelOpen" class="modal-backdrop" @click.self="alertPanelOpen = false"><article class="detail-modal alert-modal"><button class="modal-close" @click="alertPanelOpen = false">×</button><span class="modal-kicker">ALERT CENTER</span><h2>全部风险告警</h2><p>展示本次真实数据回放期间由异常检测模型生成的告警记录。</p><div class="alert-list modal-list"><div v-for="alert in allAlerts" :key="alert.id" class="alert"><span :class="alert.severity === '高' ? 'high' : ''">{{ alert.severity }}</span><div><strong>{{ alert.title }}</strong><small>{{ alert.detail }}</small></div><time>{{ alert.time }}</time></div><div v-if="!allAlerts.length" class="empty"><span>✓</span><strong>没有告警</strong><p>当前回放窗口未发现异常。</p></div></div></article></div>
    <div v-if="modelDetail" class="modal-backdrop" @click.self="modelDetail = null"><article class="detail-modal"><button class="modal-close" @click="modelDetail = null">×</button><span class="modal-kicker">MODEL DETAIL</span><h2>{{ modelDetail.name }}</h2><p>{{ modelDetail.purpose }} · {{ modelDetail.status }} · {{ modelDetail.metric }}</p><dl><div><dt>输入特征</dt><dd>{{ modelDetail.details?.input }}</dd></div><div><dt>输出结果</dt><dd>{{ modelDetail.details?.output }}</dd></div><div><dt>数据来源</dt><dd>{{ modelDetail.details?.data }}</dd></div><div><dt>运行说明</dt><dd>{{ modelDetail.details?.note }}</dd></div></dl></article></div>
    <div v-if="profileOpen" class="modal-backdrop" @click.self="profileOpen = false"><article class="detail-modal profile-modal"><button class="modal-close" @click="profileOpen = false">×</button><span class="modal-kicker">ACCOUNT SETTINGS</span><h2>个人信息与安全</h2><p>邮箱作为登录账号暂不可直接修改；修改密码时必须验证当前密码并接收邮箱验证码。</p><form @submit.prevent="saveProfile"><label><span>显示名称</span><input v-model.trim="profileForm.name" required minlength="2" maxlength="60" /></label><label><span>登录邮箱</span><input :value="currentUser.email" disabled /></label><div class="profile-divider"><span>可选：修改密码</span></div><label><span>当前密码</span><input v-model="profileForm.current_password" type="password" autocomplete="current-password" placeholder="修改密码时填写" /></label><label><span>新密码</span><input v-model="profileForm.new_password" type="password" autocomplete="new-password" minlength="8" placeholder="至少 8 位" /></label><label><span>确认新密码</span><input v-model="profileForm.confirm_password" type="password" autocomplete="new-password" minlength="8" placeholder="再次输入新密码" /></label><label><span>邮箱验证码</span><div class="code-input"><input v-model.trim="profileForm.verification_code" inputmode="numeric" maxlength="6" placeholder="6 位验证码" /><button type="button" :disabled="profileCodeSending" @click="sendPasswordCode">{{ profileCodeSending ? '发送中…' : '获取验证码' }}</button></div></label><p v-if="profileCodeMessage" class="profile-code-message">{{ profileCodeMessage }}</p><p v-if="profileError" class="profile-error">{{ profileError }}</p><footer><button type="button" @click="profileOpen = false">取消</button><button class="primary" :disabled="profileSaving" type="submit">{{ profileSaving ? '保存中…' : '保存修改' }}</button></footer></form></article></div>
  </div>
</template>
