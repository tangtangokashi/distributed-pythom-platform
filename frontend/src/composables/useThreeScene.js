import { onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

export function useThreeScene({ cameraPosition = [8, 7, 10], target = [0, 0, 0], setup }) {
  const host = ref(null)
  const ready = ref(false)
  const error = ref('')
  const paused = ref(false)
  const context = shallowRef(null)
  let frame = 0
  let observer
  let visible = true
  const handleVisibility = () => { visible = !document.hidden }

  const resetCamera = () => {
    const ctx = context.value
    if (!ctx) return
    ctx.camera.position.set(...cameraPosition)
    ctx.controls.target.set(...target)
    ctx.controls.update()
  }

  onMounted(() => {
    try {
      const scene = new THREE.Scene()
      scene.background = new THREE.Color(0x07111f)
      scene.fog = new THREE.FogExp2(0x07111f, 0.025)
      const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200)
      camera.position.set(...cameraPosition)
      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
      renderer.outputColorSpace = THREE.SRGBColorSpace
      renderer.toneMapping = THREE.ACESFilmicToneMapping
      renderer.toneMappingExposure = 1.1
      host.value.appendChild(renderer.domElement)
      const controls = new OrbitControls(camera, renderer.domElement)
      controls.enableDamping = true
      controls.dampingFactor = 0.06
      controls.minDistance = 5
      controls.maxDistance = 28
      controls.maxPolarAngle = Math.PI * 0.48
      controls.target.set(...target)
      controls.update()
      scene.add(new THREE.HemisphereLight(0x8bdcff, 0x07111f, 1.4))
      const key = new THREE.DirectionalLight(0x92a8ff, 2.2)
      key.position.set(6, 10, 4)
      scene.add(key)

      const clock = new THREE.Clock()
      const custom = setup({ THREE, scene, camera, renderer, controls }) || {}
      context.value = { THREE, scene, camera, renderer, controls, ...custom }
      const resize = () => {
        if (!host.value) return
        const { width, height } = host.value.getBoundingClientRect()
        if (!width || !height) return
        camera.aspect = width / height
        camera.updateProjectionMatrix()
        renderer.setSize(width, height, false)
      }
      observer = new ResizeObserver(resize)
      observer.observe(host.value)
      resize()

      const render = () => {
        frame = requestAnimationFrame(render)
        if (!visible) return
        const delta = Math.min(clock.getDelta(), 0.05)
        if (!paused.value) custom.animate?.(delta, clock.elapsedTime)
        controls.update()
        renderer.render(scene, camera)
      }
      document.addEventListener('visibilitychange', handleVisibility)
      render()
      ready.value = true
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'WebGL 初始化失败'
    }
  })

  onBeforeUnmount(() => {
    cancelAnimationFrame(frame)
    observer?.disconnect()
    document.removeEventListener('visibilitychange', handleVisibility)
    const ctx = context.value
    if (!ctx) return
    ctx.dispose?.()
    ctx.controls.dispose()
    ctx.scene.traverse((object) => {
      object.geometry?.dispose?.()
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      materials.filter(Boolean).forEach((material) => {
        Object.values(material).forEach((value) => value?.isTexture && value.dispose())
        material.dispose?.()
      })
    })
    ctx.renderer.dispose()
    ctx.renderer.forceContextLoss()
    ctx.renderer.domElement.remove()
    context.value = null
  })

  return { host, ready, error, paused, context, resetCamera }
}
