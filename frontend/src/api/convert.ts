/**
 * 转换 API 模块
 *
 * 包含：
 * - 单文件同步转换（POST /convert）
 * - 批量异步转换（POST /convert/batch，返回 task_id）
 * - 任务查询 / 列表 / 删除
 * - 下载 URL 构造
 *
 * 特点：
 * - 单文件/批量转换需要上传文件并报告进度，因此直接走 axios service 实例
 * - 其他轻量请求（GET/DELETE）走通用 get/del
 */

import service from './index'
import { del, get } from './index'
import type {
  BatchConvertSubmitResult,
  ConversionType,
  ConvertResult,
  TaskInfo,
  TaskListResponse
} from '@/types'

/** 基础 URL（与 index.ts 中的 service.baseURL 保持一致） */
const baseURL =
  (import.meta.env.VITE_API_BASE || '') + (import.meta.env.VITE_API_PREFIX || '/api')

/** 单文件转换可选参数 */
export interface ConvertSingleOptions {
  /** 目标 DPI（用于图片类转换） */
  dpi?: number
  /** JPG 输出质量 0-100 */
  jpg_quality?: number
  /** 是否覆盖已存在的目标文件 */
  overwrite?: boolean
  /** 自定义输出文件名（不含扩展名） */
  target_filename?: string
}

/** 批量转换可选参数 */
export interface ConvertBatchOptions {
  /** 目标 DPI */
  dpi?: number
  /** JPG 输出质量 0-100 */
  jpg_quality?: number
  /** 是否覆盖已存在文件 */
  overwrite?: boolean
  /** 是否打包为 zip 输出 */
  zip_output?: boolean
  /** 任务子目录（便于在结果页分组） */
  target_subdir?: string
}

/**
 * 单文件转换（同步）
 *
 * ⚠️ 已废弃：保留只是为了不破坏历史调用方。新逻辑请使用 :func:`convertSingleAsync`。
 *
 * 流程：上传 + 转换 + 返回结果（包含 task_id 与 download_url）。
 * 注意：此接口在转换期间**不会**对外暴露中间进度（PDF 解析耗时较长时不可见）。
 *
 * @param file 浏览器 File 对象
 * @param conversionType 转换类型
 * @param options 可选：dpi、jpg_quality、overwrite、target_filename
 * @param onUploadProgress 上传进度回调（0-100）
 * @returns 转换结果
 * @deprecated 请改用 convertSingleAsync + 轮询
 */
export function convertSingle(
  file: File,
  conversionType: ConversionType,
  options?: ConvertSingleOptions,
  onUploadProgress?: (percent: number) => void
): Promise<ConvertResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('conversion_type', conversionType)
  if (options?.dpi) form.append('dpi', String(options.dpi))
  if (options?.jpg_quality) form.append('jpg_quality', String(options.jpg_quality))
  form.append('overwrite', String(!!options?.overwrite))
  if (options?.target_filename) {
    form.append('target_filename', options.target_filename)
  }

  return service
    .post<ConvertResult>('/convert', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onUploadProgress) {
          onUploadProgress(Math.round((e.loaded * 100) / e.total))
        }
      }
    })
    .then((res) => res as unknown as ConvertResult)
}

/**
 * 单文件转换（异步）
 *
 * 流程：上传 + 立即返回 task_id，调用方需轮询 getTask 获取进度（含 PDF 页级）。
 * 后端路径：`POST /api/v1/convert/async`（202 Accepted）。
 *
 * @param file 浏览器 File 对象
 * @param conversionType 转换类型
 * @param options 同 convertSingle
 * @param onUploadProgress 上传进度回调（0-100）
 * @returns task 提交结果（含 task_id）
 */
export function convertSingleAsync(
  file: File,
  conversionType: ConversionType,
  options?: ConvertSingleOptions,
  onUploadProgress?: (percent: number) => void
): Promise<BatchConvertSubmitResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('conversion_type', conversionType)
  if (options?.dpi) form.append('dpi', String(options.dpi))
  if (options?.jpg_quality) form.append('jpg_quality', String(options.jpg_quality))
  form.append('overwrite', String(!!options?.overwrite))
  if (options?.target_filename) {
    form.append('target_filename', options.target_filename)
  }

  return service
    .post<BatchConvertSubmitResult>('/convert/async', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onUploadProgress) {
          onUploadProgress(Math.round((e.loaded * 100) / e.total))
        }
      }
    })
    .then((res) => res as unknown as BatchConvertSubmitResult)
}

/**
 * 批量转换（异步）
 *
 * 流程：上传 + 创建任务 + 返回 task_id，调用方需轮询 getTask 获取结果
 *
 * @param files 多个文件
 * @param conversionType 转换类型
 * @param options 可选：dpi、jpg_quality、overwrite、zip_output、target_subdir
 * @param onUploadProgress 上传进度回调（0-100）
 * @returns 任务提交结果
 */
export function convertBatch(
  files: File[],
  conversionType: ConversionType,
  options?: ConvertBatchOptions,
  onUploadProgress?: (percent: number) => void
): Promise<BatchConvertSubmitResult> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  form.append('conversion_type', conversionType)
  if (options?.dpi) form.append('dpi', String(options.dpi))
  if (options?.jpg_quality) form.append('jpg_quality', String(options.jpg_quality))
  form.append('overwrite', String(!!options?.overwrite))
  if (options?.zip_output) form.append('zip_output', String(!!options.zip_output))
  if (options?.target_subdir) form.append('target_subdir', options.target_subdir)

  return service
    .post<BatchConvertSubmitResult>('/convert/batch', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onUploadProgress) {
          onUploadProgress(Math.round((e.loaded * 100) / e.total))
        }
      }
    })
    .then((res) => res as unknown as BatchConvertSubmitResult)
}

/**
 * 查询任务详情
 *
 * 后端路径：`GET /api/v1/tasks/{task_id}`
 *
 * @param taskId 任务 ID
 * @returns 任务详细信息
 */
export function getTask(taskId: string): Promise<TaskInfo> {
  return get<TaskInfo>(`/tasks/${encodeURIComponent(taskId)}`)
}

/**
 * 列出最近任务
 *
 * @param limit 最多返回多少条（默认 50）
 * @returns 任务列表与总数
 */
export function listTasks(limit = 50): Promise<TaskListResponse> {
  return get<TaskListResponse>('/tasks', { limit })
}

/**
 * 删除任务
 *
 * @param taskId 任务 ID
 */
export function deleteTask(taskId: string): Promise<void> {
  return del<void>(`/tasks/${encodeURIComponent(taskId)}`)
}

/**
 * 获取任务结果文件下载 URL
 *
 * 后端路径：
 *   单文件：`GET /api/v1/tasks/{task_id}/download/{filename}`
 *   批量（zip）：`GET /api/v1/tasks/{task_id}/download`
 *
 * 返回的是相对路径，调用方通常通过 axios 触发 blob 下载
 * （或在 `<a :href="...">` 上点击，浏览器自动带 token 由 service 注入）
 *
 * @param taskId 任务 ID
 * @param filename 可选，批量任务时必须（用于多文件结果）
 * @returns 完整下载 URL
 */
export function getDownloadUrl(taskId: string, filename?: string): string {
  return filename
    ? `${baseURL}/tasks/${encodeURIComponent(taskId)}/download/${encodeURIComponent(filename)}`
    : `${baseURL}/tasks/${encodeURIComponent(taskId)}/download`
}
