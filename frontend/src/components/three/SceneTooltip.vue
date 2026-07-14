<script setup>
defineProps({ visible: Boolean, x: Number, y: Number, title: String, rows: { type: Array, default: () => [] } })
</script>
<template><div v-if="visible" class="scene-tooltip" :style="{ left: x + 'px', top: y + 'px' }"><strong>{{ title }}</strong><div v-for="row in rows" :key="row[0]"><span>{{ row[0] }}</span><b>{{ row[1] }}</b></div></div></template>
