/**
 * 全局应用 store
 *
 * 职责：
 * - 主题（深色 / 浅色）切换 + 持久化 + 应用到 <html> 节点
 * - 侧边栏折叠状态 + 持久化
 * - 全局加载态
 * - 页面标题（同步到 document.title）
 *
 * 设计：
 * - 使用 Pinia setup 风格
 * - 主题初始化时即同步到 DOM，避免首屏闪烁
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ThemeMode } from '@/types'
import { STORAGE_KEYS } from '@/utils/constants'

/** 应用标题后缀（来源环境变量 VITE_APP_TITLE） */
const APP_TITLE: string =
  (import.meta.env.VITE_APP_TITLE as string) || '文件转换平台'

/** 把主题模式应用到 <html> 元素（用于 Tailwind dark 变体） */
function applyThemeToDOM(mode: ThemeMode): void {
  if (typeof document === 'undefined') return
  if (mode === ThemeMode.DARK) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

export const useAppStore = defineStore('app', () => {
  // ============================ state ============================
  /** 当前主题 */
  const theme = ref<ThemeMode>(
    (localStorage.getItem(STORAGE_KEYS.THEME) as ThemeMode) || ThemeMode.LIGHT
  )
  /** 侧边栏是否折叠 */
  const sidebarCollapsed = ref<boolean>(
    localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) === 'true'
  )
  /** 全局加载态 */
  const isLoading = ref<boolean>(false)
  /** 当前页面标题 */
  const pageTitle = ref<string>('首页')

  // ============================ actions ============================
  /**
   * 设置主题并持久化
   * @param mode 主题模式
   */
  function setTheme(mode: ThemeMode): void {
    theme.value = mode
    localStorage.setItem(STORAGE_KEYS.THEME, mode)
    applyThemeToDOM(mode)
  }

  /** 在 LIGHT / DARK 之间切换 */
  function toggleTheme(): void {
    setTheme(theme.value === ThemeMode.LIGHT ? ThemeMode.DARK : ThemeMode.LIGHT)
  }

  /** 切换侧边栏折叠状态 */
  function toggleSidebar(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem(
      STORAGE_KEYS.SIDEBAR_COLLAPSED,
      String(sidebarCollapsed.value)
    )
  }

  /**
   * 设置全局加载态
   * @param loading 是否加载中
   */
  function setLoading(loading: boolean): void {
    isLoading.value = loading
  }

  /**
   * 设置页面标题（同时更新 document.title）
   * @param title 页面名
   */
  function setPageTitle(title: string): void {
    pageTitle.value = title
    if (typeof document !== 'undefined') {
      document.title = `${title} - ${APP_TITLE}`
    }
  }

  // 启动时把持久化主题应用到 DOM，避免首屏闪烁
  applyThemeToDOM(theme.value)

  return {
    // state
    theme,
    sidebarCollapsed,
    isLoading,
    pageTitle,
    // actions
    setTheme,
    toggleTheme,
    toggleSidebar,
    setLoading,
    setPageTitle
  }
})
