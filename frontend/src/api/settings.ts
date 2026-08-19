import { get, put } from './index'
import type { OcrSettingsResponse, OcrSettingsUpdate } from '@/types'

/** 获取 OCR 引擎配置 */
export function getOcrSettings(): Promise<OcrSettingsResponse> {
  return get<OcrSettingsResponse>('/settings/ocr')
}

/** 更新 OCR 引擎配置 */
export function updateOcrSettings(data: OcrSettingsUpdate): Promise<OcrSettingsResponse> {
  return put<OcrSettingsResponse>('/settings/ocr', data)
}
