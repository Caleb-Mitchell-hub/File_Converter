/**
 * 通用格式化函数
 */

/** 字节数 → 人类可读字符串 */
export function humanReadableSize(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`
}

/** 时间戳 / 字符串 → 格式化的本地时间 */
export function formatDate(input: string | number | Date, withTime = true): string {
  const d = new Date(input)
  if (isNaN(d.getTime())) return '-'
  const pad = (n: number) => n.toString().padStart(2, '0')
  const datePart = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  if (!withTime) return datePart
  return `${datePart} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/** 计算进度百分比（保留 1 位小数） */
export function formatProgress(processed: number, total: number): string {
  if (total <= 0) return '0.0%'
  return `${((processed / total) * 100).toFixed(1)}%`
}

/** 截断长字符串 */
export function truncate(str: string, maxLen = 30): string {
  if (!str) return ''
  return str.length > maxLen ? str.slice(0, maxLen) + '…' : str
}

/** 获取文件扩展名（不含点，小写） */
export function getExt(filename: string): string {
  const idx = filename.lastIndexOf('.')
  return idx >= 0 ? filename.slice(idx + 1).toLowerCase() : ''
}

/** 生成简短 UUID */
export function genId(length = 16): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID().replace(/-/g, '').slice(0, length)
  }
  return Math.random().toString(36).slice(2, 2 + length)
}
