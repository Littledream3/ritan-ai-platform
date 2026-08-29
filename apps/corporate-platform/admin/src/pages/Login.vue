<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <h2 style="text-align: center; margin: 0">多模型 API 网关</h2>
      </template>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="0">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" style="width: 100%" @click="handleLogin" :loading="loading">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <p style="text-align: center; color: #999; font-size: 13px">
        没有账号？<el-link type="primary" @click="showRegister = true">立即注册</el-link>
      </p>
      <p style="text-align: center; color: #999; font-size: 13px; margin-top: 8px">
        <el-link type="primary" @click="showForgot = true">忘记密码？</el-link>
      </p>
    </el-card>

    <!-- 注册对话框 -->
    <el-dialog v-model="showRegister" title="注册新账号" width="440px">
      <el-form :model="regForm" :rules="regRules" ref="regFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="regForm.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="regForm.password" type="password" />
        </el-form-item>
        <el-form-item label="昵称" prop="name">
          <el-input v-model="regForm.name" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="regForm.email" placeholder="contact@example.invalid" />
        </el-form-item>
        <el-form-item label="验证码" prop="code">
          <div style="display: flex; gap: 8px; width: 100%">
            <el-input v-model="regForm.code" placeholder="6位验证码" maxlength="6" style="flex: 1" />
            <el-button
              type="primary"
              :disabled="codeCooldown > 0"
              @click="sendCode"
              :loading="sendingCode"
              style="flex-shrink: 0"
            >{{ codeCooldown > 0 ? `${codeCooldown}s` : '发送验证码' }}</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeRegister">取消</el-button>
        <el-button type="primary" @click="handleRegister" :loading="regLoading">注册并登录</el-button>
      </template>
    </el-dialog>

    <!-- 忘记密码对话框 -->
    <el-dialog v-model="showForgot" title="重置密码" width="440px">
      <el-form :model="forgotForm" :rules="forgotRules" ref="forgotFormRef" label-width="80px">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="forgotForm.email" placeholder="contact@example.invalid" />
        </el-form-item>
        <el-form-item label="验证码" prop="code">
          <div style="display: flex; gap: 8px; width: 100%">
            <el-input v-model="forgotForm.code" placeholder="6位验证码" maxlength="6" style="flex: 1" />
            <el-button
              type="primary"
              :disabled="forgotCooldown > 0"
              @click="sendResetCode"
              :loading="sendingResetCode"
              style="flex-shrink: 0"
            >{{ forgotCooldown > 0 ? `${forgotCooldown}s` : '发送验证码' }}</el-button>
          </div>
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="forgotForm.newPassword" type="password" placeholder="至少 6 位" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeForgot">取消</el-button>
        <el-button type="primary" @click="handleResetPassword" :loading="resetLoading">重置密码</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { loginApi, registerApi, sendCodeApi, forgotPasswordApi, resetPasswordApi } from '../api'

const router = useRouter()
const formRef = ref()
const regFormRef = ref()
const loading = ref(false)
const regLoading = ref(false)
const showRegister = ref(false)

const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少 6 位', trigger: 'blur' }],
}

const regForm = reactive({ username: '', password: '', name: '', email: '', code: '' })
const regRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少 6 位', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9._%+-]+@ritanai\.com$/,
      message: '邮箱格式不正确，必须是 contact@example.invalid',
      trigger: 'blur',
    },
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为 6 位数字', trigger: 'blur' },
  ],
}

// 验证码发送状态
const sendingCode = ref(false)
const codeCooldown = ref(0)
let cooldownTimer = null

// 忘记密码
const showForgot = ref(false)
const forgotFormRef = ref()
const resetLoading = ref(false)
const sendingResetCode = ref(false)
const forgotCooldown = ref(0)
let forgotCooldownTimer = null

const forgotForm = reactive({ email: '', code: '', newPassword: '' })
const forgotRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9._%+-]+@ritanai\.com$/, message: '邮箱格式不正确，必须是 contact@example.invalid', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为 6 位数字', trigger: 'blur' },
  ],
  newPassword: [{ required: true, min: 6, message: '新密码至少 6 位', trigger: 'blur' }],
}

// 关闭注册窗时清除冷却
watch(showRegister, (val) => {
  if (!val) {
    if (cooldownTimer) clearInterval(cooldownTimer)
    codeCooldown.value = 0
    regForm.email = ''
    regForm.code = ''
  }
})

watch(showForgot, (val) => {
  if (!val) {
    if (forgotCooldownTimer) clearInterval(forgotCooldownTimer)
    forgotCooldown.value = 0
    forgotForm.email = ''
    forgotForm.code = ''
    forgotForm.newPassword = ''
  }
})

async function sendResetCode() {
  try {
    await forgotFormRef.value.validateField('email')
  } catch { return }

  sendingResetCode.value = true
  try {
    await forgotPasswordApi({ email: forgotForm.email.trim() })
    ElMessage.success('验证码已发送，请查收邮件')
    forgotCooldown.value = 60
    forgotCooldownTimer = setInterval(() => {
      forgotCooldown.value--
      if (forgotCooldown.value <= 0) {
        clearInterval(forgotCooldownTimer)
        forgotCooldownTimer = null
      }
    }, 1000)
  } catch {} finally {
    sendingResetCode.value = false
  }
}

function closeForgot() {
  showForgot.value = false
}

async function handleResetPassword() {
  const valid = await forgotFormRef.value.validate().catch(() => false)
  if (!valid) return
  resetLoading.value = true
  try {
    await resetPasswordApi({
      email: forgotForm.email.trim(),
      code: forgotForm.code,
      new_password: forgotForm.newPassword,
    })
    ElMessage.success('密码已重置，请使用新密码登录')
    showForgot.value = false
  } catch {} finally {
    resetLoading.value = false
  }
}

async function sendCode() {
  // 先校验邮箱字段
  try {
    await regFormRef.value.validateField('email')
  } catch {
    return
  }

  sendingCode.value = true
  try {
    await sendCodeApi({ email: regForm.email.trim() })
    ElMessage.success('验证码已发送，请查收邮件')

    // 60 秒冷却
    codeCooldown.value = 60
    cooldownTimer = setInterval(() => {
      codeCooldown.value--
      if (codeCooldown.value <= 0) {
        clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    }, 1000)
  } catch {
    // 错误由拦截器统一提示
  } finally {
    sendingCode.value = false
  }
}

function closeRegister() {
  showRegister.value = false
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const { data } = await loginApi({ username: form.username, password: form.password })
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    router.push('/admin')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  const valid = await regFormRef.value.validate().catch(() => false)
  if (!valid) return
  regLoading.value = true
  try {
    const { data } = await registerApi({
      username: regForm.username,
      password: regForm.password,
      name: regForm.name || regForm.username,
      email: regForm.email.trim(),
      code: regForm.code,
    })
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    showRegister.value = false
    router.push('/admin')
  } finally {
    regLoading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 400px;
}
</style>
