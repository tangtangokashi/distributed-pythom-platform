<script setup>
import { ref, watch } from 'vue'
import { useThreeScene } from '../../composables/useThreeScene'
import SceneTooltip from './SceneTooltip.vue'

const props = defineProps({ ticks: { type: Array, default: () => [] }, connected: Boolean, reducedMotion: Boolean })
const symbols = ['AAPL', 'TSLA', 'NVDA']
const enabled = ref({ AAPL: true, TSLA: true, NVDA: true })
const tip = ref({ visible: false, x: 0, y: 0, title: '', rows: [] })
const colors = { AAPL: 0x50c8e8, TSLA: 0x7367f0, NVDA: 0xf0a84b }

const { host, ready, error, paused, context, resetCamera } = useThreeScene({
  cameraPosition: [11, 8, 13], target: [0, 1, 0],
  setup({ THREE, scene, camera, renderer, controls }) {
    const grid = new THREE.GridHelper(24, 24, 0x224461, 0x13283e); grid.material.transparent = true; grid.material.opacity = .45; scene.add(grid)
    const lines = {}; const glowLines = {}; const markers = new THREE.Group(); scene.add(markers)
    symbols.forEach((symbol, index) => {
      const material = new THREE.LineBasicMaterial({ color: colors[symbol], transparent: true, opacity: .95 })
      const line = new THREE.Line(new THREE.BufferGeometry(), material); line.position.z = (index - 1) * 3; line.userData.symbol = symbol; scene.add(line); lines[symbol] = line
      const glow = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: colors[symbol], transparent: true, opacity: .16 })); glow.position.copy(line.position); glow.scale.y = .15; scene.add(glow); glowLines[symbol] = glow
      const rail = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-7, .02, line.position.z), new THREE.Vector3(7, .02, line.position.z)]), new THREE.LineDashedMaterial({ color: colors[symbol], dashSize: .18, gapSize: .16, transparent: true, opacity: .25 })); rail.computeLineDistances(); scene.add(rail)
    })
    const update = (ticks) => {
      while (markers.children.length) { const item = markers.children.pop(); item.geometry.dispose(); item.material.dispose() }
      symbols.forEach((symbol, symbolIndex) => {
        const data = ticks.filter((tick) => tick.symbol === symbol)
        if (!data.length) { lines[symbol].geometry.setFromPoints([]); glowLines[symbol].geometry.setFromPoints([]); return }
        const values = data.map((tick) => tick.price), min = Math.min(...values), max = Math.max(...values), span = max - min || 1
        const points = data.map((tick, index) => new THREE.Vector3(-7 + index / Math.max(1, data.length - 1) * 14, .35 + (tick.price - min) / span * 3.8, 0))
        lines[symbol].geometry.dispose(); lines[symbol].geometry = new THREE.BufferGeometry().setFromPoints(points); lines[symbol].userData.data = data
        glowLines[symbol].geometry.dispose(); glowLines[symbol].geometry = new THREE.BufferGeometry().setFromPoints(points)
        data.forEach((tick, index) => { if (Math.abs(tick.change_pct) < 2.5) return; const group = new THREE.Group(); const ball = new THREE.Mesh(new THREE.SphereGeometry(.14, 12, 12), new THREE.MeshBasicMaterial({ color: 0xfb7185 })); const beam = new THREE.Mesh(new THREE.CylinderGeometry(.018, .05, 1.4, 8), new THREE.MeshBasicMaterial({ color: 0xfb7185, transparent: true, opacity: .4 })); beam.position.y = .7; group.position.copy(points[index]); group.position.z = (symbolIndex - 1) * 3; group.userData = { tick, symbol }; group.add(ball, beam); markers.add(group) })
      })
    }
    update(props.ticks)
    const raycaster = new THREE.Raycaster(); raycaster.params.Line.threshold = .3; const pointer = new THREE.Vector2(); let last = 0
    const move = (event) => { if (performance.now() - last < 50) return; last = performance.now(); const rect = renderer.domElement.getBoundingClientRect(); pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1); raycaster.setFromCamera(pointer, camera); const hit = raycaster.intersectObjects([...Object.values(lines), ...markers.children], true)[0]; if (!hit) { tip.value.visible = false; renderer.domElement.style.cursor = 'grab'; return } let object = hit.object; while (object.parent && !object.userData.tick && !object.userData.symbol) object = object.parent; const symbol = object.userData.symbol; const data = object.userData.data || []; const tick = object.userData.tick || data[Math.min(data.length - 1, Math.max(0, Math.round((hit.point.x + 7) / 14 * (data.length - 1))))]; if (!tick) return; renderer.domElement.style.cursor = 'crosshair'; tip.value = { visible: true, x: event.clientX - rect.left + 12, y: event.clientY - rect.top + 12, title: symbol + ' · ' + tick.time, rows: [['价格', '$' + tick.price.toFixed(2)], ['涨跌', (tick.change_pct >= 0 ? '+' : '') + tick.change_pct.toFixed(2) + '%'], ['成交量', Number(tick.volume).toLocaleString()]] } }
    renderer.domElement.addEventListener('pointermove', move)
    return { lines, glowLines, markers, update, animate(delta, elapsed) { if (!props.reducedMotion) markers.children.forEach((group, i) => { const scale = 1 + Math.sin(elapsed * 3 + i) * .2; group.children[0].scale.setScalar(scale) }) }, dispose() { renderer.domElement.removeEventListener('pointermove', move) } }
  }
})

watch(() => props.ticks, (ticks) => context.value?.update(ticks), { deep: true })
watch(enabled, (value) => { if (!context.value) return; symbols.forEach((symbol) => { context.value.lines[symbol].visible = value[symbol]; context.value.glowLines[symbol].visible = value[symbol]; context.value.markers.children.forEach((m) => { if (m.userData.symbol === symbol) m.visible = value[symbol] }) }) }, { deep: true })
function view(type) { const ctx = context.value; if (!ctx) return; const positions = { top: [0, 17, .01], side: [17, 4, 0] }; ctx.camera.position.set(...positions[type]); ctx.controls.target.set(0, 1, 0); ctx.controls.update() }
</script>

<template><article class="twin-card finance-twin"><div class="twin-head"><div><span class="scene-kicker">MARKET TERRAIN</span><h3>三维金融时间序列</h3><p>各标的独立归一化，仅用于比较趋势形态</p></div><div class="scene-actions"><button @click="view('top')">俯视</button><button @click="view('side')">侧视</button><button @click="resetCamera">重置</button><button @click="paused = !paused">{{ paused ? '继续' : '暂停' }}</button></div></div><div class="scene-filters symbol-filters"><button v-for="symbol in symbols" :key="symbol" :class="[symbol.toLowerCase(), { active: enabled[symbol] }]" @click="enabled[symbol] = !enabled[symbol]"><i></i>{{ symbol }}</button></div><div class="scene-stage"><div ref="host" class="three-host"></div><div v-if="!ready && !error" class="scene-loading"><i></i>正在构建金融地形…</div><div v-if="error" class="scene-error">WebGL 初始化失败：{{ error }}</div><div v-if="!connected" class="scene-disconnected">数据连接中断 · 保留最后有效状态</div><SceneTooltip v-bind="tip"/><div class="axis-labels"><span>AAPL</span><span>TSLA</span><span>NVDA</span></div><div class="scene-help">悬浮曲线查看真实价格 · 红色光柱表示异常点</div></div></article></template>
