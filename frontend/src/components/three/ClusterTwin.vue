<script setup>
import { computed, ref, watch } from 'vue'
import { useThreeScene } from '../../composables/useThreeScene'
import SceneTooltip from './SceneTooltip.vue'

const props = defineProps({ nodes: { type: Array, default: () => [] }, stream: { type: Object, default: () => ({}) }, connected: Boolean, reducedMotion: Boolean })
const filters = ['全部', 'Web', 'Kafka', 'Spark', '存储']
const activeFilter = ref('全部')
const selected = ref(null)
const tip = ref({ visible: false, x: 0, y: 0, title: '', rows: [] })
const selectedRows = computed(() => selected.value ? [['角色', selected.value.role], ['状态', selected.value.status === 'healthy' ? '健康' : selected.value.status], ['消息', Number(props.stream.kafka_messages || 0).toLocaleString()], ['延迟', (props.stream.spark_latency || 0) + ' ms']] : [])

const nodePositions = [[0, 1.1, 0], [-5, .8, 2.8], [5, .8, 2.8]]
const { host, ready, error, paused, context, resetCamera } = useThreeScene({
  cameraPosition: [10, 8, 13], target: [0, .5, 1],
  setup({ THREE, scene, camera, renderer, controls }) {
    const grid = new THREE.GridHelper(30, 30, 0x214264, 0x132b43)
    grid.material.transparent = true; grid.material.opacity = .42; scene.add(grid)
    const nodeMeshes = []
    const interactives = []
    const connections = []
    const particles = []
    props.nodes.forEach((node, index) => {
      const group = new THREE.Group(); group.position.set(...(nodePositions[index] || [index * 3, 1, 0])); group.userData = { node, index }
      const base = new THREE.Mesh(new THREE.CylinderGeometry(index ? .85 : 1.15, index ? 1 : 1.35, .28, 32), new THREE.MeshStandardMaterial({ color: 0x18334d, metalness: .65, roughness: .35 }))
      const core = new THREE.Mesh(new THREE.IcosahedronGeometry(index ? .62 : .88, 2), new THREE.MeshStandardMaterial({ color: node.status === 'healthy' ? 0x34d399 : 0xfb7185, emissive: node.status === 'healthy' ? 0x0b5f54 : 0x7b2230, emissiveIntensity: 1.2, metalness: .25, roughness: .25 }))
      core.position.y = index ? .72 : .95; core.userData = { node, index }; interactives.push(core)
      const ring = new THREE.Mesh(new THREE.TorusGeometry(index ? .9 : 1.25, .025, 8, 64), new THREE.MeshBasicMaterial({ color: index ? 0x7367f0 : 0x50c8e8, transparent: true, opacity: .75 }))
      ring.rotation.x = Math.PI / 2; ring.position.y = .08
      group.add(base, core, ring); scene.add(group); nodeMeshes.push({ group, core, ring })
    })
    const services = [['Web', 0x50c8e8], ['Kafka', 0x7367f0], ['Spark', 0xf0a84b], ['存储', 0x34d399]]
    ;[[0, 1], [0, 2], [1, 2], [2, 0]].forEach(([a, b], index) => {
      const start = new THREE.Vector3(...nodePositions[a]).add(new THREE.Vector3(0, 1.1, 0)); const end = new THREE.Vector3(...nodePositions[b]).add(new THREE.Vector3(0, 1.1, 0)); const mid = start.clone().add(end).multiplyScalar(.5); mid.y += 2.2
      if (index === 3) { mid.y += .65; mid.z -= 1.1 }
      const curve = new THREE.QuadraticBezierCurve3(start, mid, end)
      const service = services[index]
      const color = props.stream.spark_latency > 60 ? 0xf0a84b : service[1]
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(48)), new THREE.LineBasicMaterial({ color, transparent: true, opacity: .55 }))
      line.userData.service = service[0]; scene.add(line); connections.push(line)
      const count = Math.min(18, Math.max(6, Math.ceil(Number(props.stream.throughput || 2) * 3)))
      const geometry = new THREE.BufferGeometry(); const positions = new Float32Array(count * 3); geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
      const points = new THREE.Points(geometry, new THREE.PointsMaterial({ color, size: .11, transparent: true, opacity: .95, depthWrite: false }))
      points.userData = { curve, count, offset: index / 3, service: service[0] }; scene.add(points); particles.push(points)
    })
    const raycaster = new THREE.Raycaster(); const pointer = new THREE.Vector2(); let lastMove = 0
    const pick = (event, click = false) => {
      if (!click && performance.now() - lastMove < 50) return; lastMove = performance.now()
      const rect = renderer.domElement.getBoundingClientRect(); pointer.x = (event.clientX - rect.left) / rect.width * 2 - 1; pointer.y = -(event.clientY - rect.top) / rect.height * 2 + 1
      raycaster.setFromCamera(pointer, camera); const hit = raycaster.intersectObjects(interactives, false)[0]
      renderer.domElement.style.cursor = hit ? 'pointer' : 'grab'
      if (hit) { const node = hit.object.userData.node; tip.value = { visible: !click, x: event.clientX - rect.left + 14, y: event.clientY - rect.top + 14, title: node.name, rows: [['角色', node.role], ['状态', node.status === 'healthy' ? '健康' : node.status]] }; if (click) { selected.value = node; controls.target.copy(hit.object.getWorldPosition(new THREE.Vector3())); controls.update() } }
      else { tip.value.visible = false; if (click) selected.value = null }
    }
    const move = (e) => pick(e); const click = (e) => pick(e, true); renderer.domElement.addEventListener('pointermove', move); renderer.domElement.addEventListener('click', click)
    return { nodeMeshes, connections, particles, animate(delta, elapsed) { nodeMeshes.forEach((item, i) => { item.core.rotation.y += delta * .35; item.ring.rotation.z += delta * (i ? .18 : -.22); if (!props.reducedMotion) item.core.position.y = (i ? .72 : .95) + Math.sin(elapsed * 1.4 + i) * .06 }); particles.forEach((points) => { const attr = points.geometry.attributes.position; for (let i = 0; i < points.userData.count; i++) { const t = (elapsed * .11 + i / points.userData.count + points.userData.offset) % 1; const p = points.userData.curve.getPoint(t); attr.setXYZ(i, p.x, p.y, p.z) } attr.needsUpdate = true }) }, dispose() { renderer.domElement.removeEventListener('pointermove', move); renderer.domElement.removeEventListener('click', click) } }
  }
})

watch(activeFilter, (value) => { const ctx = context.value; if (!ctx) return; [...ctx.connections, ...ctx.particles].forEach((object) => { object.visible = value === '全部' || object.userData.service === value }) })
watch(() => props.nodes, (nodes) => { context.value?.nodeMeshes.forEach((item, i) => { const healthy = nodes[i]?.status === 'healthy'; item.core.material.color.setHex(healthy ? 0x34d399 : 0xfb7185) }) }, { deep: true })
</script>

<template><article class="twin-card"><div class="twin-head"><div><span class="scene-kicker">DISTRIBUTED SYSTEM TWIN</span><h3>分布式集群数字孪生</h3><p>球体＝节点，彩色弧线＝服务链路，流动光点＝回放事件；用于解释系统关系，并非地理地图。</p></div><div class="scene-actions"><button @click="paused = !paused">{{ paused ? '继续动画' : '暂停动画' }}</button><button @click="resetCamera">重置视角</button></div></div><div class="scene-filters"><button v-for="filter in filters" :key="filter" :class="{ active: activeFilter === filter }" @click="activeFilter = filter">{{ filter }}</button></div><div class="scene-stage"><div ref="host" class="three-host"></div><div v-if="!ready && !error" class="scene-loading"><i></i>正在建立数字孪生场景…</div><div v-if="error" class="scene-error">WebGL 初始化失败：{{ error }}</div><div v-if="!connected" class="scene-disconnected">数据连接中断 · 保留最后有效状态</div><SceneTooltip v-bind="tip"/><div v-if="selected" class="scene-detail"><button @click="selected = null">×</button><span>NODE INSPECTOR</span><h4>{{ selected.name }}</h4><div v-for="row in selectedRows" :key="row[0]"><small>{{ row[0] }}</small><strong>{{ row[1] }}</strong></div></div><div class="scene-help">左键旋转 · 右键平移 · 滚轮缩放</div></div></article></template>
