/**
 * 认证 store
 *
 * 职责：
 * - 保存登录态（token、用户信息）
 * - 提供登录 / 登出 / 拉取用户信息的能力
 * - 把关键状态持久化到 localStorage（无 pinia-plugin-persistedstate 依赖）
 *
 * 设计：
 * - 使用 Pinia setup 风格（Composition API）
 * - 401 场景由请求拦截器统一处理，这里只在 catch 中清理本地状态
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'
import type { LoginRequest, UserInfo } from '@/types'
import { STORAGE_KEYS } from '@/utils/constants'

/** 从 localStorage 读取用户信息（容错 JSON 解析失败） */
function readUser(): UserInfo | null {
  const raw = localStorage.getItem(STORAGE_KEYS.USER)
  if (!raw) return null
  try {
    return JSON.parse(raw) as UserInfo
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  // ============================ state ============================
  /** JWT token，从 localStorage 初始化 */
  const token = ref<string>(localStorage.getItem(STORAGE_KEYS.TOKEN) || '')
  /** 当前登录用户信息 */
  const user = ref<UserInfo | null>(readUser())

  // ============================ getters ============================
  /** 是否已登录 */
  const isLoggedIn = computed(() => !!token.value)
  /** 显示用用户名（优先 nickname） */
  const username = computed(
    () => user.value?.nickname || user.value?.username || '未登录'
  )
  /** 当前用户角色，默认 user */
  const role = computed(() => user.value?.role || 'user')

  // ============================ actions ============================
  /**
   * 用户登录
   * @param credentials 登录表单
   */
  async function login(credentials: LoginRequest): Promise<void> {
    const res = await authApi.login(credentials)
    token.value = res.access_token
    user.value = res.user
    // 持久化
    localStorage.setItem(STORAGE_KEYS.TOKEN, res.access_token)
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(res.user))
  }

  /**
   * 拉取当前用户信息
   * - 无 token 时直接 return
   * - 拉取失败（token 失效）时清理本地登录态
   */
  async function fetchUserInfo(): Promise<void> {
    if (!token.value) return
    try {
      const info = await authApi.getCurrentUser()
      user.value = info
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(info))
    } catch (e) {
      // token 失效：拦截器通常会清 localStorage 并跳转，这里做兜底
      clearAuth()
      throw e
    }
  }

  /** 清理本地登录态（不调用后端） */
  function clearAuth(): void {
    token.value = ''
    user.value = null
    localStorage.removeItem(STORAGE_KEYS.TOKEN)
    localStorage.removeItem(STORAGE_KEYS.USER)
  }

  /**
   * 登出
   * - 后端目前为无状态 JWT，前端清状态即可
   * - 即便后端调用失败也要清掉本地状态
   */
  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } catch {
      // 忽略：登出必须清本地态
    }
    clearAuth()
  }

  return {
    // state
    token,
    user,
    // getters
    isLoggedIn,
    username,
    role,
    // actions
    login,
    logout,
    fetchUserInfo,
    clearAuth
  }
})
