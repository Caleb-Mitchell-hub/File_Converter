/**
 * 文件上传 API 模块
 *
 * 设计说明：
 * - 后端实现把"上传"与"转换"合并为一步：直接调 `POST /convert` 即可。
 *   因此本文件实际上是 convertApi 的语义别名，对外保留"上传"概念便于扩展。
 * - 如果未来后端拆出独立的 /upload 端点，只需修改本文件内部实现，
 *   调用方代码（任务存储等）无需改动。
 *
 * 特点：
 * - 必须使用 FormData，不能用 JSON
 * - 必须使用 axios 原生 service 实例，保留拦截器（token 注入、统一错误处理）
 * - 通过 onUploadProgress 回调实时上报上传进度
 */

import service from './index'
import type { ConvertResult, UploadResult } from '@/types'
import { ConversionType } from '@/types'

/**
 * 上传单个文件
 *
 * 当前实现：实际上传后立即转换，返回 ConvertResult。
 *
 * @param file 浏览器 File 对象
 * @param onProgress 上传进度回调（0-100）
 * @returns 上传 + 转换结果
 */
export function uploadFile(
  file: File,
  onProgress?: (percent: number) => void
): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('conversion_type', ConversionType.PNG_TO_PDF) // 默认转 PDF

  return service
    .post<ConvertResult>('/convert', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onProgress) {
          onProgress(Math.round((e.loaded * 100) / e.total))
        }
      }
    })
    .then((res) => {
      // 把 ConvertResult 适配为 UploadResult（最小集）
      const r = res as unknown as ConvertResult
      return {
        file_id: r.task_id,
        filename: r.output_filename,
        size: r.file_size,
        url: r.download_url
      } as UploadResult
    })
}

/**
 * 批量上传多个文件
 *
 * 并行上传（互不阻塞），单个文件进度通过 fileIndex 区分。
 *
 * @param files 文件列表
 * @param onProgress 单个文件进度回调 (fileIndex, percent)
 * @returns 各文件的上传结果（顺序与入参一致）
 */
export function uploadFiles(
  files: File[],
  onProgress?: (fileIndex: number, percent: number) => void
): Promise<UploadResult[]> {
  if (!files || files.length === 0) {
    return Promise.resolve([])
  }

  const tasks = files.map((file, index) =>
    uploadFile(file, (percent) => onProgress?.(index, percent))
  )

  return Promise.all(tasks)
}
