<template>
  <el-container class="app-layout">
    <!-- 侧边栏 -->
    <el-aside
      :width="appStore.sidebarCollapsed ? `${SIDEBAR_COLLAPSED_WIDTH}px` : `${SIDEBAR_WIDTH}px`"
      class="sidebar"
    >
      <Sidebar />
    </el-aside>

    <el-container>
      <!-- 顶部 -->
      <el-header class="header" :height="`${HEADER_HEIGHT}px`">
        <Header />
      </el-header>

      <!-- 内容 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component, route }">
          <transition name="fade" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { HEADER_HEIGHT, SIDEBAR_WIDTH, SIDEBAR_COLLAPSED_WIDTH } from './constants'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const appStore = useAppStore()
</script>

<style scoped>
.app-layout {
  height: 100vh;
}
.sidebar {
  background: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color-lighter);
  transition: width 0.2s;
  overflow: hidden;
}
.header {
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-lighter);
  padding: 0 16px;
}
.main-content {
  background: var(--el-bg-color-page);
  padding: 16px;
  overflow: auto;
}

/* 路由切换淡入淡出 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
