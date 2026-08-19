<template>
  <div class="header-container">
    <!-- 左侧：折叠 + 面包屑 -->
    <div class="left">
      <el-button
        :icon="appStore.sidebarCollapsed ? Expand : Fold"
        text
        circle
        @click="appStore.toggleSidebar"
      />
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item>{{ route.meta?.title || '页面' }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 右侧：主题 + 刷新 + 用户 -->
    <div class="right">
      <!-- 主题切换 -->
      <el-tooltip
        :content="appStore.theme === 'dark' ? '切换到亮色' : '切换到暗色'"
      >
        <el-button
          :icon="appStore.theme === 'dark' ? Sunny : Moon"
          text
          circle
          @click="appStore.toggleTheme"
        />
      </el-tooltip>

      <!-- 刷新 -->
      <el-tooltip content="刷新">
        <el-button :icon="Refresh" text circle @click="reload" />
      </el-tooltip>

      <!-- 用户下拉 -->
      <el-dropdown @command="handleUserCmd">
        <span class="user-info">
          <el-avatar :size="28" :src="authStore.user?.avatar">
            {{ avatarText }}
          </el-avatar>
          <span class="username">{{ authStore.username }}</span>
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  Fold,
  Expand,
  Sunny,
  Moon,
  Refresh,
  ArrowDown,
  Setting,
  SwitchButton
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()

/** 头像显示文字：nickname 第一个字符，否则 username 首字母，否则 U */
const avatarText = computed<string>(() => {
  const u = authStore.user
  if (u?.nickname) return u.nickname[0]
  if (u?.username) return u.username[0].toUpperCase()
  return 'U'
})

function reload(): void {
  window.location.reload()
}

async function handleUserCmd(cmd: string): Promise<void> {
  if (cmd === 'logout') {
    try {
      await ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' })
      await authStore.logout()
      ElMessage.success('已退出登录')
      router.push('/login')
    } catch {
      // 用户取消确认时静默
    }
  } else if (cmd === 'settings') {
    router.push('/settings')
  }
}
</script>

<style scoped>
.header-container {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.left,
.right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 0 4px;
  outline: none;
}
.username {
  font-size: 14px;
  color: var(--el-text-color-primary);
}
</style>
