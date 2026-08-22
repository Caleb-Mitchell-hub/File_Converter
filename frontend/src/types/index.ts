/**
 * 全局 TypeScript 类型定义
 * 包括：枚举、API 响应模型、Store 模型
 */

/* ============================ 枚举 ============================ */

/** 任务状态 */
export enum TaskStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  SUCCESS = 'success',
  FAILED = 'failed',
  PARTIAL_SUCCESS = 'partial_success'
}

/** 任务状态中文标签 */
export const TaskStatusLabel: Record<TaskStatus, string> = {
  [TaskStatus.PENDING]: '等待中',
  [TaskStatus.RUNNING]: '处理中',
  [TaskStatus.SUCCESS]: '已完成',
  [TaskStatus.FAILED]: '失败',
  [TaskStatus.PARTIAL_SUCCESS]: '部分成功'
}

/** 转换类型枚举（与后端 ConversionType 一一对应） */
export enum ConversionType {
  XLSX_TO_PDF = 'xlsx_to_pdf',
  XLSX_TO_PNG = 'xlsx_to_png',
  XLSX_TO_JPG = 'xlsx_to_jpg',
  PDF_TO_XLSX = 'pdf_to_xlsx',
  DOCX_TO_PDF = 'docx_to_pdf',
  PDF_TO_DOCX = 'pdf_to_docx',
  PDF_TO_PNG = 'pdf_to_png',
  PDF_TO_JPG = 'pdf_to_jpg',
  PNG_TO_PDF = 'png_to_pdf',
  JPG_TO_PDF = 'jpg_to_pdf',
  JPEG_TO_PDF = 'jpeg_to_pdf',
  PNG_TO_XLSX = 'png_to_xlsx',
  JPG_TO_XLSX = 'jpg_to_xlsx'
}

/** 转换类型描述 */
export interface ConversionTypeInfo {
  value: ConversionType
  label: string
  sourceExt: string
  targetExt: string
  category: 'excel' | 'pdf' | 'word' | 'image' | 'ocr'
}

/** 所有支持的转换类型清单 */
export const CONVERSION_TYPES: ConversionTypeInfo[] = [
  { value: ConversionType.XLSX_TO_PDF, label: 'Excel → PDF', sourceExt: '.xlsx', targetExt: '.pdf', category: 'excel' },
  { value: ConversionType.XLSX_TO_PNG, label: 'Excel → PNG', sourceExt: '.xlsx', targetExt: '.png', category: 'excel' },
  { value: ConversionType.XLSX_TO_JPG, label: 'Excel → JPG', sourceExt: '.xlsx', targetExt: '.jpg', category: 'excel' },
  { value: ConversionType.PDF_TO_XLSX, label: 'PDF → Excel', sourceExt: '.pdf', targetExt: '.xlsx', category: 'pdf' },
  { value: ConversionType.DOCX_TO_PDF, label: 'Word → PDF', sourceExt: '.docx', targetExt: '.pdf', category: 'word' },
  { value: ConversionType.PDF_TO_DOCX, label: 'PDF → Word', sourceExt: '.pdf', targetExt: '.docx', category: 'word' },
  { value: ConversionType.PDF_TO_PNG, label: 'PDF → PNG', sourceExt: '.pdf', targetExt: '.png', category: 'pdf' },
  { value: ConversionType.PDF_TO_JPG, label: 'PDF → JPG', sourceExt: '.pdf', targetExt: '.jpg', category: 'pdf' },
  // 图片相关：标注具体源格式（PNG / JPG / JPEG）
  { value: ConversionType.PNG_TO_PDF, label: 'PNG → PDF', sourceExt: '.png', targetExt: '.pdf', category: 'image' },
  { value: ConversionType.JPG_TO_PDF, label: 'JPG → PDF', sourceExt: '.jpg', targetExt: '.pdf', category: 'image' },
  { value: ConversionType.JPEG_TO_PDF, label: 'JPEG → PDF', sourceExt: '.jpeg', targetExt: '.pdf', category: 'image' },
  // OCR：标注源图格式，避免选择时歧义
  { value: ConversionType.PNG_TO_XLSX, label: 'OCR(PNG) → Excel', sourceExt: '.png', targetExt: '.xlsx', category: 'ocr' },
  { value: ConversionType.JPG_TO_XLSX, label: 'OCR(JPG) → Excel', sourceExt: '.jpg', targetExt: '.xlsx', category: 'ocr' }
]

/** 主题模式 */
export enum ThemeMode {
  LIGHT = 'light',
  DARK = 'dark'
}

/* ============================ API 响应模型 ============================ */

/** 统一响应外壳 */
export interface APIResponse<T = unknown> {
  code: number
  message: string
  data?: T
}

/** 错误响应（HTTP 错误外壳；类 APIError 在 api/index.ts 中定义） */
export interface APIErrorPayload {
  code: number
  message: string
  detail?: string
  task_id?: string
}

/** 单文件上传结果 */
export interface UploadResult {
  file_id: string
  filename: string
  size: number
  url: string
}

/** 转换提交结果（单文件同步） */
export interface ConvertResult {
  task_id: string
  status: TaskStatus
  source_filename: string
  output_filename: string
  download_url: string
  file_size: number
  file_size_human?: string
}

/** 批量转换提交结果（异步） */
export interface BatchConvertSubmitResult {
  task_id: string
  status: TaskStatus
  total_files: number
  message: string
}

/** 单文件处理结果（批量中） */
export interface FileResult {
  source_filename: string
  output_filename?: string
  success: boolean
  message: string
}

/** 任务信息 */
export interface TaskInfo {
  task_id: string
  status: TaskStatus
  conversion_type: ConversionType
  progress: number
  total_files: number
  processed_files: number
  created_at: string
  updated_at: string
  finished_at?: string | null
  error_message?: string | null
  output_files: string[]
  download_url?: string | null
  file_results?: FileResult[]
  extra: Record<string, any>
}

/** 任务列表响应 */
export interface TaskListResponse {
  total: number
  tasks: TaskInfo[]
}

/** 健康检查响应 */
export interface HealthResponse {
  status: string
  app: string
  version: string
  converters: number
  supported_pairs: number
  timestamp: string
}

/** 登录请求 */
export interface LoginRequest {
  username: string
  password: string
}

/** 登录响应 */
export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: UserInfo
}

/** 注册请求 */
export interface RegisterRequest {
  username: string
  password: string
  nickname?: string
}

/** 用户信息 */
export interface UserInfo {
  id: string
  username: string
  nickname: string
  avatar?: string
  role: 'admin' | 'user'
}

/* ============================ 上传文件模型 ============================ */

/** 前端文件项 */
export interface UploadFileItem {
  id: string
  file: File
  name: string
  size: number
  sizeHuman: string
  status: 'pending' | 'uploading' | 'uploaded' | 'failed'
  progress: number
  error?: string
  uploadedId?: string
}

/** OCR 引擎 */
export enum OcrEngine {
  OPENCV_HYBRID = 'opencv_hybrid',
  QWEN_VL = 'qwen_vl',
  TESSERACT = 'tesseract'
}

/** OCR 引擎中文标签 */
export const OcrEngineLabel: Record<OcrEngine, string> = {
  [OcrEngine.OPENCV_HYBRID]: 'OpenCV 混合（推荐）',
  [OcrEngine.QWEN_VL]: 'Qwen-VL 云端',
  [OcrEngine.TESSERACT]: 'Tesseract 本地'
}

/** OCR 引擎说明 */
export const OcrEngineDesc: Record<OcrEngine, string> = {
  [OcrEngine.OPENCV_HYBRID]: 'OpenCV 几何检测 + Qwen-VL 云端 OCR，适合有边框表格',
  [OcrEngine.QWEN_VL]: '纯 Qwen-VL 云端 OCR，适合无线表格，需配置 API Key',
  [OcrEngine.TESSERACT]: '纯本地 Tesseract OCR，无需网络，适合简单文字识别'
}

/** OCR 配置响应 */
export interface OcrSettingsResponse {
  engine: string
  qwen_api_key: string
  qwen_base_url: string
  qwen_model: string
  qwen_timeout: number
}

/** OCR 配置更新请求 */
export interface OcrSettingsUpdate {
  engine?: string
  qwen_api_key?: string
  qwen_base_url?: string
  qwen_model?: string
  qwen_timeout?: number
}
