<!--
  系统设置页
  - 外观：主题、侧边栏
  - 账户：当前用户信息、退出
  - 关于：应用信息
-->
<template>
  <div class="settings-page">
    <div class="page-header">
      <h2>系统设置</h2>
      <p>个性化配置你的使用偏好</p>
    </div>

    <el-row :gutter="16">
      <!-- 外观 -->
      <el-col :xs="24" :md="12">
        <div class="page-card">
          <h3 class="card-title">
            <el-icon><Sunny /></el-icon>
            <span>外观</span>
          </h3>
          <el-form label-position="left" label-width="100px">
            <el-form-item label="主题模式">
              <el-radio-group
                :model-value="appStore.theme"
                @change="onThemeChange"
              >
                <el-radio-button :value="ThemeMode.LIGHT">亮色</el-radio-button>
                <el-radio-button :value="ThemeMode.DARK">暗色</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="侧边栏">
              <el-switch
                :model-value="!appStore.sidebarCollapsed"
                @change="onSidebarChange"
                active-text="展开"
                inactive-text="收起"
              />
            </el-form-item>
          </el-form>
        </div>
      </el-col>

      <!-- 账户 -->
      <el-col :xs="24" :md="12">
        <div class="page-card">
          <h3 class="card-title">
            <el-icon><User /></el-icon>
            <span>账户</span>
          </h3>
          <el-form label-position="left" label-width="100px">
            <el-form-item label="用户名">
              <el-text>{{ authStore.user?.username || '-' }}</el-text>
            </el-form-item>
            <el-form-item label="昵称">
              <el-text>{{ authStore.user?.nickname || '-' }}</el-text>
            </el-form-item>
            <el-form-item label="角色">
              <el-tag>{{ authStore.role === 'admin' ? '管理员' : '普通用户' }}</el-tag>
            </el-form-item>
            <el-form-item>
              <el-button type="danger" @click="onLogout">退出登录</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-col>

      <!-- OCR 引擎 -->
      <el-col :span="24" class="mt-16">
        <div class="page-card">
          <h3 class="card-title">
            <el-icon><Cpu /></el-icon>
            <span>OCR 引擎</span>
          </h3>
          <el-form label-position="left" label-width="120px">
            <el-form-item label="引擎选择">
              <el-select
                v-model="ocrEngine"
                placeholder="选择 OCR 引擎"
                style="width: 100%"
              >
                <el-option
                  v-for="(label, value) in OcrEngineLabel"
                  :key="value"
                  :label="label"
                  :value="value"
                />
              </el-select>
              <div class="form-help">{{ OcrEngineDesc[ocrEngine] }}</div>
            </el-form-item>

            <template v-if="ocrEngine === OcrEngine.QWEN_VL">
              <el-form-item label="API Key">
                <el-input
                  v-model="qwenApiKey"
                  type="password"
                  show-password
                  placeholder="输入 Qwen API Key"
                />
              </el-form-item>
              <el-form-item label="Base URL">
                <el-input v-model="qwenBaseUrl" placeholder="API 地址" />
              </el-form-item>
              <el-form-item label="模型">
                <el-input v-model="qwenModel" placeholder="模型名称" />
              </el-form-item>
              <el-form-item label="超时(秒)">
                <el-input-number
                  v-model="qwenTimeout"
                  :min="10"
                  :max="300"
                  :step="10"
                />
              </el-form-item>
            </template>

            <el-form-item>
              <el-button type="primary" :loading="ocrSaving" @click="onSaveOcr">
                保存配置
              </el-button>
              <el-button @click="onLoadOcr" :loading="ocrLoading">
                重新加载
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-col>

      <!-- 关于 -->
      <el-col :span="24" class="mt-16">
        <div class="page-card">
          <h3 class="card-title">
            <el-icon><InfoFilled /></el-icon>
            <span>关于</span>
          </h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="应用名称">{{ appTitle }}</el-descriptions-item>
            <el-descriptions-item label="版本">1.0.0</el-descriptions-item>
            <el-descriptions-item label="后端 API">{{ apiBase }}</el-descriptions-item>
            <el-descriptions-item label="技术栈">Vue 3 + Vite + TypeScript + Element Plus</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
/**
 * 系统设置页
 *
 * 职责：
 * - 主题切换（写入 store + 持久化）
 * - 侧边栏折叠切换
 * - 展示当前账户信息 + 退出
 * - 展示应用元信息
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Cpu } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { ThemeMode, OcrEngine, OcrEngineLabel, OcrEngineDesc } from '@/types'
import type { OcrSettingsUpdate } from '@/types'
import { getOcrSettings, updateOcrSettings } from '@/api/settings'

const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()

// OCR state
const ocrEngine = ref<OcrEngine>(OcrEngine.OPENCV_HYBRID)
const qwenApiKey = ref('')
const qwenBaseUrl = ref('')
const qwenModel = ref('')
const qwenTimeout = ref(60)
const ocrSaving = ref(false)
const ocrLoading = ref(false)

/** 应用标题（来自环境变量 VITE_APP_TITLE） */
const appTitle: string =
  (import.meta.env.VITE_APP_TITLE as string) || '文件转换平台'

/** 后端 API base */
const apiBase: string =
  (import.meta.env.VITE_API_BASE as string) ||
  (import.meta.env.VITE_API_PREFIX as string) ||
  '/api'

/**
 * 主题切换回调
 */
function onThemeChange(val: ThemeMode | string | number | boolean | undefined): void {
  if (val === ThemeMode.LIGHT || val === ThemeMode.DARK) {
    appStore.setTheme(val)
    ElMessage.success(`已切换到${val === 'dark' ? '暗色' : '亮色'}模式`)
  }
}

/**
 * 侧边栏开关切换
 * - el-switch 状态变化时调用，期望与 store 当前值取反
 */
function onSidebarChange(val: boolean | string | number): void {
  if (typeof val === 'boolean') {
    // val=true 表示"展开"，与 store 的"折叠"标志相反
    const expectedCollapsed = !val
    if (expectedCollapsed !== appStore.sidebarCollapsed) {
      appStore.toggleSidebar()
    }
  }
}

/**
 * 退出登录
 */
async function onLogout(): Promise<void> {
  try {
    await ElMessageBox.confirm('确认退出？', '提示', { type: 'warning' })
    await authStore.logout()
    ElMessage.success('已退出')
    router.push('/login')
  } catch {
    // 用户取消
  }
}

async function onLoadOcr(): Promise<void> {
  ocrLoading.value = true
  try {
    const data = await getOcrSettings()
    ocrEngine.value = data.engine as OcrEngine
    qwenApiKey.value = data.qwen_api_key
    qwenBaseUrl.value = data.qwen_base_url
    qwenModel.value = data.qwen_model
    qwenTimeout.value = data.qwen_timeout
  } catch {
    // error handled by interceptor
  } finally {
    ocrLoading.value = false
  }
}

async function onSaveOcr(): Promise<void> {
  ocrSaving.value = true
  try {
    const payload: OcrSettingsUpdate = {
      engine: ocrEngine.value,
      qwen_api_key: qwenApiKey.value || undefined,
      qwen_base_url: qwenBaseUrl.value,
      qwen_model: qwenModel.value,
      qwen_timeout: qwenTimeout.value
    }
    await updateOcrSettings(payload)
    ElMessage.success('OCR 配置已保存')
  } catch {
    // error handled by interceptor
  } finally {
    ocrSaving.value = false
  }
}

onMounted(() => {
  onLoadOcr()
})
</script>

<style scoped>
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
}

.form-help {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.5;
}
</style>
