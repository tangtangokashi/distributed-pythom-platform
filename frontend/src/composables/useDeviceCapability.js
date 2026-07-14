import { onBeforeUnmount, onMounted, ref } from 'vue'

export function useDeviceCapability() {
  const desktop = ref(false)
  const reducedMotion = ref(false)
  const webgl = ref(true)

  const detect = () => {
    desktop.value = window.innerWidth >= 1024
    reducedMotion.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    try {
      const canvas = document.createElement('canvas')
      webgl.value = Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'))
    } catch { webgl.value = false }
  }

  onMounted(() => { detect(); window.addEventListener('resize', detect, { passive: true }) })
  onBeforeUnmount(() => window.removeEventListener('resize', detect))
  return { desktop, reducedMotion, webgl }
}
