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

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        size="large"
        @keyup.enter="onLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="form.remember">记住我</el-checkbox>
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

      <div class="login-footer">
        <el-text type="info" size="small">
          提示：演示版本可任意输入用户名密码
        </el-text>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Document, User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { STORAGE_KEYS } from '@/utils/constants'
import type { UserInfo } from '@/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({
  username: 'admin',
  password: 'admin',
  remember: true
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

/**
 * 演示版登录：
 * - 不调用真实后端，本地构造 token + user 写入 store 和 localStorage
 * - 生产环境应替换为 authStore.login(form) 调用
 */
async function onLogin(): Promise<void> {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    const fakeToken = 'demo-token-' + Date.now()
    const fakeUser: UserInfo = {
      id: '1',
      username: form.username,
      nickname: form.username === 'admin' ? '管理员' : form.username,
      role: 'admin'
    }

    localStorage.setItem(STORAGE_KEYS.TOKEN, fakeToken)
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(fakeUser))

    // 同步到 store（直接修改 ref 因为 store 暴露了 state）
    authStore.token = fakeToken
    authStore.user = fakeUser

    ElMessage.success('登录成功')
    const redirect =
      (route.query.redirect as string | undefined) || '/convert'
    router.push(redirect)
  } catch (e) {
    const msg = e instanceof Error ? e.message : '登录失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
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
  width: 400px;
  padding: 40px;
  background: var(--el-bg-color);
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
}
.login-header {
  text-align: center;
  margin-bottom: 32px;
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
.login-btn {
  width: 100%;
}
.login-footer {
  margin-top: 16px;
  text-align: center;
}
</style>
