/**
 * 认证 API 模块
 *
 * 当前状态：占位实现（后端尚未提供 /auth/* 端点）
 *
 * 设计说明：
 * - 登录页（views/login/Index.vue）当前使用本地 fakeUser 直接构造登录态，
 *   不依赖本模块。
 * - 保留本模块的函数签名是为后续接入真实后端鉴权时无缝对接。
 * - 所有函数都返回本地构造的占位数据，避免触发真实的网络请求导致 404。
 *
 * 接入真实后端时，只需把内部实现替换为 `post('/auth/login', data)` 即可。
 */

import type { LoginRequest, LoginResponse, UserInfo } from '@/types'

/**
 * 用户登录
 *
 * 当前为占位实现：本地直接构造一个 fake 登录响应。
 *
 * @param data 登录表单（用户名 + 密码）
 * @returns 登录响应（包含 access_token 和用户信息）
 */
export function login(data: LoginRequest): Promise<LoginResponse> {
  // 占位：真实实现应为 `return post<LoginResponse>('/auth/login', data)`
  const token = `demo-token-${Date.now()}`
  const user: UserInfo = {
    id: '1',
    username: data.username,
    nickname: data.username === 'admin' ? '管理员' : data.username,
    role: data.username === 'admin' ? 'admin' : 'user'
  }
  return Promise.resolve({
    access_token: token,
    token_type: 'bearer',
    expires_in: 86400,
    user
  })
}

/**
 * 用户登出
 *
 * 后端无状态，token 在前端 localStorage 中清空即可。
 * 当前为占位实现，调用方应自行清空 localStorage。
 */
export function logout(): Promise<void> {
  // 占位：真实实现应为 `return post<void>('/auth/logout')`
  return Promise.resolve()
}

/**
 * 获取当前登录用户信息
 *
 * 当前为占位实现：从 localStorage 读取。
 * 请求会自动携带 Bearer token（由 index.ts 请求拦截器注入），
 * 401 时由统一拦截器跳转到登录页。
 *
 * @returns 当前登录用户信息
 */
export function getCurrentUser(): Promise<UserInfo> {
  // 占位：真实实现应为 `return get<UserInfo>('/auth/me')`
  const userStr = localStorage.getItem('doc_converter_user')
  if (userStr) {
    try {
      return Promise.resolve(JSON.parse(userStr) as UserInfo)
    } catch {
      // 解析失败，返回默认
    }
  }
  return Promise.resolve({
    id: '1',
    username: 'admin',
    nickname: '管理员',
    role: 'admin'
  })
}
