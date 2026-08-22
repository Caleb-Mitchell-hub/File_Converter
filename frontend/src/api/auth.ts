
/**
 * 认证 API 模块
 *
 * 已接入真实后端（/api/v1/auth/*）：
 * - POST /auth/register  注册
 * - POST /auth/login     登录，签发 JWT
 * - GET  /auth/me        当前用户信息（请求自动携带 Bearer token）
 *
 * 登出为无状态 JWT 模型：前端清空 localStorage 即可，无需后端端点。
 */

import { get, post } from './index'
import type { LoginRequest, LoginResponse, RegisterRequest, UserInfo } from '@/types'

/**
 * 用户登录
 *
 * @param data 登录表单（用户名 + 密码）
 * @returns 登录响应（access_token + 用户信息）
 */
export function login(data: LoginRequest): Promise<LoginResponse> {
  return post<LoginResponse>('/auth/login', data)
}

/**
 * 用户注册（普通用户）
 *
 * @param data 注册表单
 * @returns 新用户信息
 */
export function register(data: RegisterRequest): Promise<{ user: UserInfo }> {
  return post<{ user: UserInfo }>('/auth/register', data)
}

/**
 * 用户登出
 *
 * 后端为无状态 JWT：token 由前端 localStorage 持有，
 * 清空本地状态即可完成登出（由调用方 authStore.logout 处理）。
 */
export function logout(): Promise<void> {
  return Promise.resolve()
}

/**
 * 获取当前登录用户信息
 *
 * 请求自动携带 Bearer token（由 index.ts 请求拦截器注入），
 * 401 时由统一拦截器跳转到登录页。
 *
 * @returns 当前登录用户信息
 */
export function getCurrentUser(): Promise<UserInfo> {
  return get<UserInfo>('/auth/me')
}
