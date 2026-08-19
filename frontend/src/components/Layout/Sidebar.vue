<template>
  <div class="sidebar-container">
    <!-- Logo -->
    <div class="logo" :class="{ collapsed: appStore.sidebarCollapsed }">
      <el-icon :size="24" color="#409eff">
        <Document />
      </el-icon>
      <span v-show="!appStore.sidebarCollapsed" class="title">文件转换</span>
    </div>

    <!-- 菜单 -->
    <el-menu
      :default-active="activeMenu"
      :collapse="appStore.sidebarCollapsed"
      :collapse-transition="false"
      background-color="transparent"
      router
      class="sidebar-menu"
    >
      <el-menu-item index="/convert">
        <el-icon><Refresh /></el-icon>
        <template #title>文件转换</template>
      </el-menu-item>
      <el-menu-item index="/tasks">
        <el-icon><List /></el-icon>
        <template #title>任务列表</template>
      </el-menu-item>
      <el-menu-item index="/settings">
        <el-icon><Setting /></el-icon>
        <template #title>系统设置</template>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const appStore = useAppStore()
const activeMenu = computed<string>(() => route.path)
</script>

<style scoped>
.sidebar-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.logo {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  border-bottom: 1px solid var(--el-border-color-lighter);
  white-space: nowrap;
  overflow: hidden;
}
.logo.collapsed {
  padding: 0;
  justify-content: center;
}
.title {
  transition: opacity 0.15s;
}
.sidebar-menu {
  flex: 1;
  border-right: none;
}
</style>
