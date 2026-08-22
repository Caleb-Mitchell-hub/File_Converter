
<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <el-icon :size="48" color="#409eff">
          <Document />
        </el-icon>
        <h1>文件转换平台</h1>
        <p>企业级文档格式转换服务</p>
      </div>

      <el-tabs v-model="mode" stretch class="login-tabs">
        <!-- 登录 -->
        <el-tab-pane label="登 录" name="login">
          <el-form
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

            <el-form-item>
              <el-checkbox v-model="loginForm.remember">记住我</el-checkbox>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="loading"
                class="login-btn"
                @click="onLogin"
              >
                登 录
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 注册 -->
        <el-tab-pane label="注 册" name="register">
          <el-form
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
              >
                注 册
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <div class="login-footer">
        <el-text type="info" size="small">
          默认管理员 admin / admin123，首次登录后请修改密码
        </el-text>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Avatar, Document, Lock, User } from '@element-plus/icons-vue'
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
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-box {
  width: 420px;
  padding: 40px;
  background: var(--el-bg-color);
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
}
.login-header {
  text-align: center;
  margin-bottom: 24px;
}
.login-header h1 {
  margin: 16px 0 8px;
  font-size: 24px;
  color: var(--el-text-color-primary);
}
.login-header p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
.login-tabs {
  margin-bottom: 8px;
}
.login-btn {
  width: 100%;
}
.login-footer {
  margin-top: 12px;
  text-align: center;
}
</style>
