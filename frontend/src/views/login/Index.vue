
<template>
  <div class="login-page">
    <!-- 背景光晕 -->
    <div class="glow glow-1"></div>
    <div class="glow glow-2"></div>
    <div class="glow glow-3"></div>

    <!-- 左：品牌区 -->
    <div class="brand">
      <div class="brand-logo">
        <div class="brand-logo-icon">
          <el-icon :size="30"><Document /></el-icon>
        </div>
        <div>
          <h1>文件转换平台</h1>
          <div class="brand-sub">企业级文档格式转换服务</div>
        </div>
      </div>

      <div class="features">
        <div class="feature">
          <div class="feature-icon"><el-icon :size="20"><Refresh /></el-icon></div>
          <div>
            <strong>多格式互转</strong>
            <span>Excel / Word / PDF / 图片 13 种转换方向</span>
          </div>
        </div>
        <div class="feature">
          <div class="feature-icon"><el-icon :size="20"><Cpu /></el-icon></div>
          <div>
            <strong>三引擎 OCR</strong>
            <span>Tesseract · Qwen-VL · OpenCV 混合识别</span>
          </div>
        </div>
        <div class="feature">
          <div class="feature-icon"><el-icon :size="20"><Files /></el-icon></div>
          <div>
            <strong>批量转换</strong>
            <span>多文件后台任务，进度实时追踪</span>
          </div>
        </div>
        <div class="feature">
          <div class="feature-icon"><el-icon :size="20"><Lock /></el-icon></div>
          <div>
            <strong>安全隔离</strong>
            <span>用户数据隔离，任务持久化不丢失</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右：表单区 -->
    <div class="form-side">
      <div class="card">
        <div class="tabs">
          <button
            type="button"
            class="tab"
            :class="{ active: mode === 'login' }"
            @click="mode = 'login'"
          >登 录</button>
          <button
            type="button"
            class="tab"
            :class="{ active: mode === 'register' }"
            @click="mode = 'register'"
          >注 册</button>
        </div>

        <!-- 登录表单 -->
        <el-form
          v-show="mode === 'login'"
          ref="loginRef"
          :model="loginForm"
          :rules="loginRules"
          size="large"
          @keyup.enter="onLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="用户名"
              :prefix-icon="User"
              clearable
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="密码"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <div class="row-between">
            <el-checkbox v-model="loginForm.remember">记住我</el-checkbox>
          </div>

          <el-form-item>
            <el-button
              type="primary"
              :loading="loading"
              class="login-btn"
              @click="onLogin"
            >登 录</el-button>
          </el-form-item>
        </el-form>

        <!-- 注册表单 -->
        <el-form
          v-show="mode === 'register'"
          ref="registerRef"
          :model="registerForm"
          :rules="registerRules"
          size="large"
          @keyup.enter="onRegister"
        >
          <el-form-item prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="用户名（3-32 位）"
              :prefix-icon="User"
              clearable
            />
          </el-form-item>

          <el-form-item prop="nickname">
            <el-input
              v-model="registerForm.nickname"
              placeholder="昵称（可选）"
              :prefix-icon="Avatar"
              clearable
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="密码（至少 6 位）"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-form-item prop="confirm">
            <el-input
              v-model="registerForm.confirm"
              type="password"
              placeholder="确认密码"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="registering"
              class="login-btn"
              @click="onRegister"
            >注 册</el-button>
          </el-form-item>
        </el-form>
      </div>

      <div class="copyright">© 2026 File Converter · v1.0.0</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  Avatar,
  Cpu,
  Document,
  Files,
  Lock,
  Refresh,
  User
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import * as authApi from '@/api/auth'
import type { RegisterRequest } from '@/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const registering = ref(false)

const loginRef = ref<FormInstance>()
const registerRef = ref<FormInstance>()

const loginForm = reactive({
  username: 'admin',
  password: 'admin123',
  remember: true
})

const registerForm = reactive({
  username: '',
  nickname: '',
  password: '',
  confirm: ''
})

const loginRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 32, message: '用户名长度 3-32 位', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

/** 登录：调用真实后端，成功后跳转 */
async function onLogin(): Promise<void> {
  if (!loginRef.value) return
  try {
    await loginRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    await authStore.login({
      username: loginForm.username,
      password: loginForm.password
    })
    ElMessage.success('登录成功')
    const redirect =
      (route.query.redirect as string | undefined) || '/convert'
    router.push(redirect)
  } catch {
    // 错误提示由 axios 拦截器统一处理
  } finally {
    loading.value = false
  }
}

/** 注册：成功后切回登录并预填用户名 */
async function onRegister(): Promise<void> {
  if (!registerRef.value) return
  try {
    await registerRef.value.validate()
  } catch {
    return
  }

  registering.value = true
  try {
    const payload: RegisterRequest = {
      username: registerForm.username,
      password: registerForm.password
    }
    if (registerForm.nickname) {
      payload.nickname = registerForm.nickname
    }
    await authApi.register(payload)
    ElMessage.success('注册成功，请登录')
    mode.value = 'login'
    loginForm.username = registerForm.username
    loginForm.password = ''
  } catch {
    // 错误提示由 axios 拦截器统一处理
  } finally {
    registering.value = false
  }
}
</script>

<style scoped>
/* ---------- 全屏渐变背景 ---------- */
.login-page {
  height: 100vh;
  display: flex;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 45%, #06b6d4 100%);
}
.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.45;
  pointer-events: none;
}
.glow-1 { width: 420px; height: 420px; background: #a78bfa; top: -120px; left: 8%; }
.glow-2 { width: 380px; height: 380px; background: #22d3ee; bottom: -100px; right: 30%; }
.glow-3 { width: 300px; height: 300px; background: #f472b6; bottom: 12%; left: 40%; }

/* ---------- 左：品牌区 ---------- */
.brand {
  flex: 1.1;
  color: #fff;
  padding: 80px 72px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;
  z-index: 1;
}
.brand-logo {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.brand-logo-icon {
  width: 56px;
  height: 56px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(8px);
  color: #fff;
}
.brand h1 {
  font-size: 40px;
  font-weight: 700;
  letter-spacing: 1px;
  margin: 0;
}
.brand-sub {
  font-size: 16px;
  opacity: 0.85;
  margin-top: 4px;
}
.features {
  display: flex;
  flex-direction: column;
  gap: 22px;
  margin-top: 40px;
}
.feature {
  display: flex;
  align-items: center;
  gap: 16px;
}
.feature-icon {
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(6px);
  color: #fff;
  flex-shrink: 0;
}
.feature strong {
  display: block;
  font-size: 16px;
  font-weight: 600;
}
.feature span {
  font-size: 13px;
  opacity: 0.78;
}

/* ---------- 右：表单区 ---------- */
.form-side {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 32px;
  position: relative;
  z-index: 1;
}
.card {
  width: 420px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(18px) saturate(140%);
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 20px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.25);
  padding: 32px 32px 20px;
}
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 10px;
  padding: 4px;
}
.tab {
  flex: 1;
  padding: 9px 0;
  text-align: center;
  border-radius: 8px;
  font-size: 15px;
  color: #64748b;
  cursor: pointer;
  border: none;
  background: transparent;
  transition: all 0.18s;
}
.tab.active {
  background: #fff;
  color: #4f46e5;
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.18);
}
.row-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -6px 0 14px;
}
.login-btn {
  width: 100%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35);
  transition: transform 0.12s, box-shadow 0.2s;
}
.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(99, 102, 241, 0.42);
}
.copyright {
  margin-top: 20px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
  text-align: center;
}

/* ---------- 暗色模式适配 ---------- */
html.dark .card {
  background: rgba(30, 32, 40, 0.72);
  border-color: rgba(255, 255, 255, 0.12);
}
html.dark .tabs {
  background: rgba(255, 255, 255, 0.06);
}
html.dark .tab {
  color: #a3a6ad;
}
html.dark .tab.active {
  background: rgba(255, 255, 255, 0.1);
  color: #a5b4fc;
  box-shadow: none;
}

/* 小屏适配：隐藏品牌区，表单全宽居中 */
@media (max-width: 900px) {
  .brand { display: none; }
  .form-side { flex: 1; }
  .card { width: 100%; max-width: 420px; }
}
</style>
