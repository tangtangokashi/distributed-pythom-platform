<script setup>
import { computed, ref } from 'vue'
import { platformApi, setToken } from '../api'

const emit = defineEmits(['authenticated'])
const mode = ref('login')
const name = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')
const canSubmit = computed(() => email.value.trim() && password.value.length >= (mode.value === 'register' ? 8 : 1) && (mode.value === 'login' || (name.value.trim().length >= 2 && password.value === confirmPassword.value)))

function switchMode(next) {
  mode.value = next; error.value = ''; password.value = ''; confirmPassword.value = ''
}

async function submit() {
  if (!canSubmit.value || loading.value) return
  if (mode.value === 'register' && password.value !== confirmPassword.value) { error.value = '两次输入的密码不一致'; return }
  loading.value = true; error.value = ''
  try {
    const payload = mode.value === 'register'
      ? { name: name.value.trim(), email: email.value.trim(), password: password.value }
      : { email: email.value.trim(), password: password.value }
    const result = mode.value === 'register' ? await platformApi.register(payload) : await platformApi.login(payload)
    setToken(result.access_token)
    emit('authenticated', result.user)
  } catch (err) { error.value = err.message }
  finally { loading.value = false }
}
</script>

<template><main class="auth-page"><section class="auth-visual"><div class="auth-brand"><div class="brand-mark"><i></i><i></i><i></i></div><div><strong>DataPulse</strong><small>智能决策平台</small></div></div><div class="auth-copy"><span>REAL-TIME INTELLIGENCE</span><h1>让每一条数据<br>成为清晰的决策。</h1><p>融合实时数据流、机器学习与数字孪生技术，统一洞察金融风险与电商运营表现。</p><div class="auth-features"><div><i>01</i><strong>实时数据流</strong><small>持续追踪业务变化</small></div><div><i>02</i><strong>智能风险识别</strong><small>模型自动捕捉异常</small></div><div><i>03</i><strong>3D 数字孪生</strong><small>直观呈现系统状态</small></div></div></div><div class="auth-orbit"><i></i><i></i><i></i><span></span></div><footer>© 2026 DataPulse · Distributed Intelligence Platform</footer></section><section class="auth-form-wrap"><div class="auth-form"><div class="auth-mobile-brand"><div class="brand-mark"><i></i><i></i><i></i></div><strong>DataPulse</strong></div><span class="auth-kicker">{{ mode === 'login' ? 'WELCOME BACK' : 'CREATE ACCOUNT' }}</span><h2>{{ mode === 'login' ? '登录你的工作台' : '创建平台账户' }}</h2><p>{{ mode === 'login' ? '输入账户信息，继续访问实时智能决策平台。' : '注册后即可访问全部业务数据和数字孪生场景。' }}</p><div class="auth-tabs"><button :class="{ active: mode === 'login' }" @click="switchMode('login')">登录</button><button :class="{ active: mode === 'register' }" @click="switchMode('register')">注册</button></div><form @submit.prevent="submit"><label v-if="mode === 'register'"><span>姓名</span><input v-model="name" autocomplete="name" maxlength="60" placeholder="请输入你的姓名"></label><label><span>邮箱地址</span><input v-model="email" type="email" autocomplete="email" maxlength="255" placeholder="name@example.com"></label><label><span>密码</span><div class="password-field"><input v-model="password" :type="showPassword ? 'text' : 'password'" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" maxlength="128" :placeholder="mode === 'register' ? '至少 8 个字符' : '请输入密码'"><button type="button" @click="showPassword = !showPassword">{{ showPassword ? '隐藏' : '显示' }}</button></div></label><label v-if="mode === 'register'"><span>确认密码</span><input v-model="confirmPassword" type="password" autocomplete="new-password" maxlength="128" placeholder="再次输入密码"></label><div v-if="error" class="auth-error"><b>!</b>{{ error }}</div><button class="auth-submit" :disabled="!canSubmit || loading" type="submit">{{ loading ? '请稍候…' : mode === 'login' ? '登录工作台' : '创建账户' }}<span>→</span></button></form><small class="auth-security">密码经过安全哈希处理，平台不会保存明文密码。</small></div></section></main></template>
