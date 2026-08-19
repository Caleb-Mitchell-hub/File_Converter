/**
 * 工具常量
 */

/** LocalStorage 键名 */
export const STORAGE_KEYS = {
  TOKEN: 'doc_converter_token',
  USER: 'doc_converter_user',
  THEME: 'doc_converter_theme',
  SIDEBAR_COLLAPSED: 'doc_converter_sidebar_collapsed'
} as const

/** 文件大小限制（字节） */
export const FILE_SIZE_LIMITS = {
  MAX_UPLOAD_MB: 100,
  MAX_BATCH_FILES: 50
} as const

/** 支持的文件扩展名 */
export const ALLOWED_EXTENSIONS = [
  '.xlsx', '.xls',
  '.pdf',
  '.docx', '.doc',
  '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'
] as const

/** HTTP 状态码 */
export const HTTP_STATUS = {
  OK: 200,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  SERVER_ERROR: 500
} as const

/** 业务错误码 */
export const BUSINESS_CODE = {
  SUCCESS: 0,
  UNAUTHORIZED: 401,
  TOKEN_EXPIRED: 4001
} as const
