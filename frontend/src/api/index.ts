/**
 * Axios 实例 + 拦截器
 *
 * 基础路径通过环境变量注入：
 * - dev:   /api  (经 vite proxy 转发)
 * - prod:  /api  (Nginx 反代)
 *
 * 拦截器职责：
 * - 请求：自动注入 token
 * - 响应：剥离统一外壳 {code, message, data}，把 data 字段作为 resolve 值
 *         非 0 code 抛 APIError
 * - 401：清登录态并跳登录页
 */

import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig
} from 'axios'
import { ElMessage } from 'element-plus'
import { BUSINESS_CODE, HTTP_STATUS, STORAGE_KEYS } from '@/utils/constants'
import type { APIResponse } from '@/types'

export class APIError extends Error {
  code: number
  detail?: string
  task_id?: string
  status: number

  constructor(message: string, code: number, status: number, detail?: string, task_id?: string) {
    super(message)
    this.name = 'APIError'
    this.code = code
    this.status = status
    this.detail = detail
    this.task_id = task_id
  }
}

const baseURL = (import.meta.env.VITE_API_BASE || '') + (import.meta.env.VITE_API_PREFIX || '/api')

const service: AxiosInstance = axios.create({
  baseURL,
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' }
})

// -------------------- 请求拦截器 --------------------
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem(STORAGE_KEYS.TOKEN)
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// -------------------- 响应拦截器 --------------------
service.interceptors.response.use(
  (response: AxiosResponse<APIResponse | any>) => {
    // 文件下载等二进制响应直接返回
    if (response.config.responseType === 'blob' || response.config.responseType === 'arraybuffer') {
      return response.data
    }

    const payload = response.data
    // 后端标准外壳 {code, message, data}
    if (payload && typeof payload === 'object' && 'code' in payload) {
      if (payload.code === BUSINESS_CODE.SUCCESS) {
        return payload.data
      }
      // 401 / token 过期
      if (payload.code === BUSINESS_CODE.UNAUTHORIZED || payload.code === BUSINESS_CODE.TOKEN_EXPIRED) {
        handleUnauthorized()
        return Promise.reject(
          new APIError(payload.message || '未登录', payload.code, response.status, payload.detail, payload.task_id)
        )
      }
      // 业务错误
      ElMessage.error(payload.message || '请求失败')
      return Promise.reject(
        new APIError(payload.message || '请求失败', payload.code, response.status, payload.detail, payload.task_id)
      )
    }
    // 非标准响应：原样返回
    return payload
  },
  (error) => {
    const status: number = error?.response?.status ?? 0
    // 优先用后端给的真实失败原因（errorResponse.message / detail），
    // 不要被前端硬编码的"服务器内部错误"覆盖。
    const backendPayload: APIErrorPayload | undefined = error?.response?.data
    let msg = backendPayload?.message || backendPayload?.detail || error.message || '网络错误'

    if (status === HTTP_STATUS.UNAUTHORIZED) {
      handleUnauthorized()
      // 401 用后端 message 才有意义（"未登录" / "token 过期"）
    } else if (status === HTTP_STATUS.NOT_FOUND) {
      // 资源不存在：保留后端 detail（"文件不存在: xxx"）
      if (!backendPayload?.message && !backendPayload?.detail) {
        msg = '资源不存在'
      }
    } else if (error.code === 'ECONNABORTED') {
      msg = '请求超时'
    } else if (error.message?.includes('Network Error')) {
      msg = '网络连接失败'
    }
    // 其它状态（含 4xx/5xx）：一律透传后端给的中文原因，不做覆写

    if (status !== HTTP_STATUS.UNAUTHORIZED) {
      // 截断到 200 字符以内，避免 ElMessage 弹窗被超长堆栈刷屏
      const display = msg.length > 200 ? msg.slice(0, 200) + '…' : msg
      ElMessage.error(display)
    }

    const apiErr = new APIError(
      msg,
      backendPayload?.code ?? 0,
      status,
      backendPayload?.detail,
      backendPayload?.task_id
    )
    return Promise.reject(apiErr)
  }
)

function handleUnauthorized() {
  localStorage.removeItem(STORAGE_KEYS.TOKEN)
  localStorage.removeItem(STORAGE_KEYS.USER)
  // 避免循环引用，直接用 location
  if (location.pathname !== '/login') {
    location.href = '/login'
  }
}

// -------------------- 通用请求方法 --------------------
export function request<T = any>(config: AxiosRequestConfig): Promise<T> {
  return service.request<any, T>(config)
}

export function get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ method: 'GET', url, params, ...config })
}

export function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ method: 'POST', url, data, ...config })
}

export function del<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ method: 'DELETE', url, ...config })
}

export function put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ method: 'PUT', url, data, ...config })
}

export default service
