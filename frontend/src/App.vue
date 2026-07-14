<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue'
import { platformApi } from './api'
import { useDeviceCapability } from './composables/useDeviceCapability'

const ClusterTwin = defineAsyncComponent(() => import('./components/three/ClusterTwin.vue'))
const FinanceTerrain = defineAsyncComponent(() => import('./components/three/FinanceTerrain.vue'))
const CommerceWorld = defineAsyncComponent(() => import('./components/three/CommerceWorld.vue'))

const navItems = [
  ['overview', '运营总览', '▦'], ['finance', '金融风险', '⌁'],
  ['ecommerce', '电商运营', '◇'], ['models', '模型中心', '⬡'],
  ['assistant', '智能助手', '✦'],
]
const pageMeta = {
  overview: ['运营总览', '掌握业务脉搏，快速识别值得关注的变化'],
  finance: ['金融风险中心', '跟踪核心标的走势、短期预测与异常波动'],
  ecommerce: ['电商运营中心', '聚焦订单表现、异常交易与高价值用户'],
  models: ['模型中心', '统一查看模型能力、运行方式与服务状态'],
  assistant: ['智能分析助手', '将实时指标转化为清晰、可执行的业务判断'],
}
const active = ref('overview')
const mobileOpen = ref(false)
const loading = ref(true)
const connected = ref(false)
const error = ref('')
const dashboard = ref(null)
const models = ref([])
const question = ref('')
const answer = ref('你好，我可以根据当前聚合指标解释风险信号，并给出运营建议。')
const asking = ref(false)
const showThree = ref(true)
const { desktop, reducedMotion, webgl } = useDeviceCapability()
const canRenderThree = computed(() => desktop.value && webgl.value && showThree.value)
let timer

const meta = computed(() => pageMeta[active.value])
const kpis = computed(() => dashboard.value?.kpis || {})
const ticks = computed(() => dashboard.value?.ticks || [])
const alerts = computed(() => dashboard.value?.alerts || [])
const orders = computed(() => dashboard.value?.orders_feed || [])
const nodes = computed(() => dashboard.value?.nodes || [])
const stream = computed(() => dashboard.value?.stream || {})
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
async function control(action) {
  try { await platformApi.simulation(action); await refresh() }
  catch (err) { error.value = err.message }
}
async function ask(text = question.value) {
  if (!text.trim() || asking.value) return
  question.value = text; asking.value = true; answer.value = '正在分析当前实时指标…'
  try { answer.value = (await platformApi.explain(text)).answer }
  catch (err) { answer.value = '分析暂时不可用：' + err.message }
  finally { asking.value = false }
}
function switchPage(id) { active.value = id; mobileOpen.value = false; window.scrollTo({ top: 0, behavior: 'smooth' }) }
onMounted(async () => { await Promise.all([refresh(), loadModels()]); timer = setInterval(refresh, 2500) })
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="app-shell">
    <aside :class="['sidebar', { open: mobileOpen }]">
      <div class="brand"><div class="brand-mark"><i></i><i></i><i></i></div><div><strong>DataPulse</strong><small>智能决策平台</small></div></div>
      <nav><p class="nav-caption">工作台</p><button v-for="item in navItems" :key="item[0]" :class="['nav-link', { active: active === item[0] }]" @click="switchPage(item[0])"><b>{{ item[2] }}</b><span>{{ item[1] }}</span><i v-if="item[0] === 'overview' && alerts.length">{{ alerts.length }}</i></button></nav>
      <div class="sidebar-foot"><div class="environment"><div><i></i><strong>演示环境</strong></div><p>当前为本地模拟数据，集群指标仅用于界面展示。</p></div><div class="profile"><span>DA</span><div><strong>数据分析员</strong><small>平台管理员</small></div><b>•••</b></div></div>
    </aside>
    <div v-if="mobileOpen" class="scrim" @click="mobileOpen = false"></div>

    <main>
      <header class="topbar"><button class="menu" @click="mobileOpen = true">☰</button><div class="breadcrumb"><span>智能决策平台</span><b>/</b><strong>{{ meta[0] }}</strong></div><div class="top-actions"><span :class="['connection', { offline: !connected }]"><i></i>{{ connected ? '数据已连接' : '等待连接' }}</span><button class="bell">◌<i v-if="alerts.length"></i></button><span class="avatar">DA</span></div></header>
      <div class="content">
        <section class="page-heading"><div><span>今日实时数据</span><h1>{{ meta[0] }}</h1><p>{{ meta[1] }}</p></div><div><button v-if="['overview','finance','ecommerce'].includes(active) && desktop && webgl" class="view-toggle" @click="showThree = !showThree">{{ showThree ? '切换二维视图' : '开启三维视图' }}</button><span class="live"><i></i>实时更新</span><time>{{ new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' }) }}</time></div></section>
        <div v-if="error" class="banner"><b>!</b>{{ error }}<button @click="refresh">重新连接</button></div>
        <div v-if="loading" class="loading"><i></i><p>正在加载业务数据…</p></div>

        <template v-else-if="active === 'overview'">
          <section class="metrics">
            <article><div><span class="metric-icon blue">订</span><em>实时</em></div><p>累计订单</p><h2>{{ (kpis.orders || 0).toLocaleString() }}</h2><small>本次演示周期</small></article>
            <article><div><span class="metric-icon purple">¥</span><em>聚合</em></div><p>总交易额</p><h2>¥{{ Number(kpis.gmv || 0).toLocaleString(undefined, { maximumFractionDigits: 0 }) }}</h2><small>订单金额累计</small></article>
            <article><div><span class="metric-icon green">人</span><em>活跃</em></div><p>活跃用户</p><h2>{{ kpis.active_users || 0 }}</h2><small>近实时估算</small></article>
            <article class="risk"><div><span class="metric-icon red">!</span><em>需关注</em></div><p>风险告警</p><h2>{{ kpis.alerts || 0 }}</h2><small>最近检测结果</small></article>
          </section>
          <ClusterTwin v-if="canRenderThree" :nodes="nodes" :stream="stream" :connected="connected" :reduced-motion="reducedMotion" />
          <section class="grid main-grid">
            <article class="panel chart-panel"><div class="panel-head"><div><h3>市场走势</h3><p>核心标的实时价格变化</p></div><div class="legend"><span>AAPL</span><span>TSLA</span><span>NVDA</span></div></div><div class="chart"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><g><line x1="0" y1="20" x2="100" y2="20"/><line x1="0" y1="52" x2="100" y2="52"/><line x1="0" y1="84" x2="100" y2="84"/></g><polyline v-for="line in chartLines" :key="line.symbol" :class="line.symbol.toLowerCase()" :points="line.points" fill="none" vector-effect="non-scaling-stroke"/></svg></div><div class="chart-foot"><span>较早</span><span>实时价格流</span><span>现在</span></div></article>
            <article class="panel"><div class="panel-head"><div><h3>计算资源</h3><p>三节点演示集群</p></div><span class="badge">模拟状态</span></div><div class="node-list"><div v-for="node in nodes" :key="node.name" class="node"><span>{{ node.name.includes('1') ? '主' : '算' }}</span><div><strong>{{ node.name }}</strong><small>{{ node.role }}</small></div><em><i></i>正常</em></div></div><div class="stream"><div><small>模拟消息</small><strong>{{ (stream.kafka_messages || 0).toLocaleString() }}</strong></div><div><small>处理延迟</small><strong>{{ stream.spark_latency || 0 }} ms</strong></div></div></article>
          </section>
          <section class="grid bottom-grid">
            <article class="panel"><div class="panel-head"><div><h3>最新风险告警</h3><p>模型检测到的业务异常</p></div><button>查看全部</button></div><div v-if="alerts.length" class="alert-list"><div v-for="alert in alerts.slice(0, 4)" :key="alert.id" class="alert"><span :class="alert.severity === '高' ? 'high' : ''">{{ alert.severity }}</span><div><strong>{{ alert.title }}</strong><small>{{ alert.detail }}</small></div><time>{{ alert.time }}</time></div></div><div v-else class="empty"><span>✓</span><strong>当前运行平稳</strong><p>暂未检测到需要关注的异常</p></div></article>
            <article class="panel control"><div class="panel-head"><div><h3>数据回放</h3><p>控制本地演示数据生成</p></div><span :class="['run-status', { paused: !dashboard?.running }]">{{ dashboard?.running ? '运行中' : '已暂停' }}</span></div><div class="control-state"><span :class="{ paused: !dashboard?.running }">{{ dashboard?.running ? '▶' : 'Ⅱ' }}</span><div><strong>{{ dashboard?.running ? '实时数据正在生成' : '数据回放已暂停' }}</strong><p>每次生成一条行情与一笔订单</p></div></div><div class="buttons"><button class="primary" @click="control('start')">开始回放</button><button @click="control('stop')">暂停</button><button @click="control('step')">单步生成</button></div></article>
          </section>
        </template>

        <template v-else-if="active === 'finance'">
          <section class="stock-grid"><article v-for="stock in latestStocks" :key="stock.symbol"><div class="stock-title"><span>{{ stock.symbol[0] }}</span><div><strong>{{ stock.symbol }}</strong><small>NASDAQ · 实时</small></div></div><h2>${{ stock.price.toFixed(2) }}</h2><em :class="stock.change_pct >= 0 ? 'positive' : 'negative'">{{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct.toFixed(2) }}%</em><div class="bars"><i v-for="n in 13" :key="n" :style="{ height: (25 + ((n * 17 + stock.price) % 65)) + '%' }"></i></div></article></section>
          <FinanceTerrain v-if="canRenderThree" :ticks="ticks" :connected="connected" :reduced-motion="reducedMotion" />
          <section class="grid main-grid"><article class="panel chart-panel"><div class="panel-head"><div><h3>多标的行情对比</h3><p>AAPL、TSLA 与 NVDA 实时价格趋势</p></div><span class="badge">Isolation Forest</span></div><div class="chart large"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><g><line x1="0" y1="20" x2="100" y2="20"/><line x1="0" y1="52" x2="100" y2="52"/><line x1="0" y1="84" x2="100" y2="84"/></g><polyline v-for="line in chartLines" :key="line.symbol" :class="line.symbol.toLowerCase()" :points="line.points" fill="none" vector-effect="non-scaling-stroke"/></svg></div></article><article class="panel"><div class="panel-head"><div><h3>金融风险信号</h3><p>最新异常波动记录</p></div></div><div class="alert-list"><div v-for="a in alerts.filter(x => x.domain === 'finance')" :key="a.id" class="alert"><span class="high">{{ a.severity }}</span><div><strong>{{ a.title }}</strong><small>{{ a.detail }}</small></div><time>{{ a.time }}</time></div><div v-if="!alerts.some(x => x.domain === 'finance')" class="empty"><span>✓</span><strong>市场风险平稳</strong><p>当前没有异常波动</p></div></div></article></section>
        </template>

        <template v-else-if="active === 'ecommerce'">
          <section class="metrics three"><article><p>累计订单</p><h2>{{ (kpis.orders || 0).toLocaleString() }}</h2><small>演示周期累计</small></article><article><p>总交易额</p><h2>¥{{ Number(kpis.gmv || 0).toLocaleString(undefined, { maximumFractionDigits: 0 }) }}</h2><small>GMV 实时聚合</small></article><article><p>平均客单价</p><h2>¥{{ kpis.orders ? Math.round(kpis.gmv / kpis.orders).toLocaleString() : 0 }}</h2><small>交易额 / 订单数</small></article></section>
          <CommerceWorld v-if="canRenderThree" :orders="orders" :connected="connected" :reduced-motion="reducedMotion" />
          <section class="grid commerce-grid"><article class="panel orders"><div class="panel-head"><div><h3>实时订单</h3><p>最新交易与异常检测结果</p></div><span class="badge">{{ orders.length }} 条动态</span></div><div class="table"><div class="table-head"><span>时间 / 订单号</span><span>商品</span><span>区域</span><span>金额</span><span>状态</span></div><div v-for="o in orders.slice(0, 10)" :key="o.order_code" :class="['table-row', { anomaly: o.is_anomaly }]"><span><small>{{ o.time }}</small><strong>{{ o.order_code }}</strong></span><span>{{ o.product }}</span><span>{{ o.region }}</span><span>¥{{ o.amount.toLocaleString() }}</span><em :class="{ danger: o.is_anomaly }">{{ o.is_anomaly ? '异常' : '正常' }}</em></div></div></article><article class="panel"><div class="panel-head"><div><h3>用户价值分层</h3><p>K-Means 聚类结果示例</p></div></div><div class="segments"><div v-for="user in [['U1090','高价值用户','¥2,890 · 13 笔订单',88],['U1012','活跃用户','¥1,680 · 8 笔订单',66],['U1048','潜力用户','¥590 · 4 笔订单',38]]" :key="user[0]"><span>{{ user[0] }}</span><strong>{{ user[1] }}</strong><p>{{ user[2] }}</p><div><i :style="{ width: user[3] + '%' }"></i></div><small>推荐：智能手表、无线耳机</small></div></div></article></section>
        </template>

        <template v-else-if="active === 'models'">
          <section class="metrics three"><article><span class="metric-icon green">✓</span><p>在线模型</p><h2>{{ modelCounts.online }}</h2><small>提供实时推理</small></article><article><span class="metric-icon blue">↻</span><p>批处理模型</p><h2>{{ modelCounts.batch }}</h2><small>按任务调度运行</small></article><article><span class="metric-icon purple">…</span><p>待训练模型</p><h2>{{ modelCounts.pending }}</h2><small>等待训练资源</small></article></section>
          <section class="models"><article v-for="model in models" :key="model.name"><div><span class="model-glyph">M</span><em :class="model.status === '在线' ? 'online' : model.status === '批处理' ? 'batch' : 'pending'"><i></i>{{ model.status }}</em></div><h3>{{ model.name }}</h3><p>{{ model.purpose }}</p><section><small>模型指标</small><strong>{{ model.metric }}</strong></section><footer><span>最近更新：今天</span><button>查看详情 →</button></footer></article></section><div class="info"><span>i</span><div><strong>关于模型运行环境</strong><p>在线模型在 Web 服务内执行演示推理；Spark ALS 与 LSTM 当前为架构预留能力。</p></div></div>
        </template>

        <template v-else>
          <section class="assistant"><article><div class="assistant-intro"><span>✦</span><div><small>AI 分析助手</small><h2>今天想了解哪些业务变化？</h2><p>我会使用当前订单、交易额和风险告警等聚合指标进行分析。</p></div></div><div class="answer"><span>AI</span><p>{{ answer }}</p></div><div class="question"><textarea v-model="question" rows="3" placeholder="输入你的问题，例如：当前有哪些需要关注的风险？" @keydown.ctrl.enter="ask()"></textarea><div><span>Ctrl + Enter 发送</span><button :disabled="asking || !question.trim()" @click="ask()">{{ asking ? '分析中…' : '发送问题' }} ↑</button></div></div></article><aside><article class="panel"><div class="panel-head"><div><h3>快捷问题</h3><p>从常用分析开始</p></div></div><button v-for="prompt in ['当前系统健康状态如何？','最近的异常订单是什么原因？','是否有需要关注的风险信号？','给出当前运营建议']" :key="prompt" class="prompt" @click="ask(prompt)"><span>↗</span>{{ prompt }}</button></article><div class="privacy"><span>盾</span><div><strong>数据隐私保护</strong><p>仅提交订单数、GMV 和告警摘要，不传输原始订单或个人信息。</p></div></div></aside></section>
        </template>
      </div>
    </main>
  </div>
</template>
