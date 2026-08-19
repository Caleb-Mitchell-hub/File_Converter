/**
 * 任务 store
 *
 * 职责：
 * - 待上传 / 上传中的文件列表（带状态、进度）
 * - 任务列表 + 当前查看的任务
 * - 进度轮询（基于 setTimeout 自递归，不重叠）
 *
 * 设计：
 * - 使用 Pinia setup 风格
 * - 轮询采用 setTimeout 链而非 setInterval，避免请求堆积
 * - 终态（SUCCESS / FAILED / PARTIAL_SUCCESS）自动停止轮询
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as convertApi from '@/api/convert'
import {
  ConversionType,
  TaskStatus,
  type TaskInfo,
  type UploadFileItem
} from '@/types'
import { genId, humanReadableSize } from '@/utils/format'
import { FILE_SIZE_LIMITS } from '@/utils/constants'

/** 终态集合：到达后停止轮询 */
const TERMINAL_STATUSES: TaskStatus[] = [
  TaskStatus.SUCCESS,
  TaskStatus.FAILED,
  TaskStatus.PARTIAL_SUCCESS
]

/** 单个文件大小上限（字节） */
const MAX_FILE_SIZE_BYTES: number =
  FILE_SIZE_LIMITS.MAX_UPLOAD_MB * 1024 * 1024

export const useTaskStore = defineStore('task', () => {
  // ============================ state ============================
  /** 待上传 / 上传中 / 已上传 / 失败 的文件列表 */
  const fileList = ref<UploadFileItem[]>([])
  /** 任务列表（最新在前） */
  const tasks = ref<TaskInfo[]>([])
  /** 当前正在查看的任务 */
  const currentTask = ref<TaskInfo | null>(null)
  /** 当前选择的转换类型 */
  const conversionType = ref<ConversionType>(ConversionType.PNG_TO_PDF)
  /** 是否正在轮询 */
  const polling = ref<boolean>(false)
  /** 轮询定时器句柄 */
  let pollTimer: number | null = null

  // ============================ getters ============================
  /** 文件总大小（字节） */
  const totalSize = computed(() =>
    fileList.value.reduce((sum, f) => sum + f.size, 0)
  )
  /** 文件总大小（人类可读） */
  const totalSizeHuman = computed(() => humanReadableSize(totalSize.value))
  /** 待处理文件数（pending + uploading） */
  const pendingCount = computed(
    () =>
      fileList.value.filter(
        (f) => f.status === 'pending' || f.status === 'uploading'
      ).length
  )
  /** 运行中任务（pending + running） */
  const runningTasks = computed(() =>
    tasks.value.filter(
      (t) => t.status === TaskStatus.RUNNING || t.status === TaskStatus.PENDING
    )
  )

  // ============================ 文件操作 ============================
  /**
   * 添加文件到待上传列表
   * @param files 浏览器 File 列表
   */
  function addFiles(files: File[]): void {
    for (const f of files) {
      if (f.size > MAX_FILE_SIZE_BYTES) {
        // 超大文件：直接标记失败，仍留在列表中由用户手动移除
        fileList.value.push({
          id: genId(),
          file: f,
          name: f.name,
          size: f.size,
          sizeHuman: humanReadableSize(f.size),
          status: 'failed',
          progress: 0,
          error: `超过最大大小 ${FILE_SIZE_LIMITS.MAX_UPLOAD_MB}MB`
        })
        continue
      }
      fileList.value.push({
        id: genId(),
        file: f,
        name: f.name,
        size: f.size,
        sizeHuman: humanReadableSize(f.size),
        status: 'pending',
        progress: 0
      })
    }
  }

  /**
   * 从列表中移除文件
   * @param id 文件项 id
   */
  function removeFile(id: string): void {
    fileList.value = fileList.value.filter((f) => f.id !== id)
  }

  /** 清空文件列表 */
  function clearFiles(): void {
    fileList.value = []
  }

  /** 切换当前转换类型 */
  function setConversionType(type: ConversionType): void {
    conversionType.value = type
  }

  // ============================ 提交任务 ============================
  /**
   * 提交单个文件转换（**异步路径**，可看到页级进度）
   * - 取列表中第一个 pending 文件
   * - POST /api/v1/convert/async 立刻拿到 task_id
   * - 启动轮询：currentTask 实时刷新 progress / extra.current_page / extra.total_pages
   * - 终态后停止轮询，调用方从返回值获取最终 TaskInfo
   */
  async function submitSingle(): Promise<TaskInfo | null> {
    const first = fileList.value.find((f) => f.status === 'pending')
    if (!first) return null
    first.status = 'uploading'
    first.error = undefined
    try {
      const res = await convertApi.convertSingleAsync(
        first.file,
        conversionType.value,
        {},
        (percent) => {
          first.progress = percent
        }
      )
      const taskId = res.task_id
      first.status = 'uploaded'
      first.progress = 100

      // 立刻拉一次 → 设 currentTask → 启动轮询
      const task = await convertApi.getTask(taskId)
      tasks.value.unshift(task)
      currentTask.value = task
      startPolling(taskId)
      return task
    } catch (e) {
      first.status = 'failed'
      const reason = e instanceof Error ? e.message : String(e)
      first.error = reason
      throw e
    }
  }

  /**
   * 提交批量转换
   * - 所有 pending 文件一起提交（zip_output 默认为 true）
   * - 上传进度只回写到第一个文件（API 只回传总进度）
   */
  async function submitBatch(): Promise<TaskInfo | null> {
    const pendings = fileList.value.filter((f) => f.status === 'pending')
    if (pendings.length === 0) return null
    pendings.forEach((f) => {
      f.status = 'uploading'
      f.progress = 0
      f.error = undefined
    })
    try {
      const files = pendings.map((f) => f.file)
      const res = await convertApi.convertBatch(
        files,
        conversionType.value,
        { zip_output: true },
        (percent) => {
          // 进度回写到第一个文件，其余置为同比例
          pendings[0].progress = percent
        }
      )
      pendings.forEach((f) => {
        f.status = 'uploaded'
        f.progress = 100
      })

      // 立即查询任务并放入列表
      const task = await convertApi.getTask(res.task_id)
      tasks.value.unshift(task)
      // 标记为当前任务并开始轮询
      currentTask.value = task
      startPolling(task.task_id)
      return task
    } catch (e) {
      pendings.forEach((f) => {
        f.status = 'failed'
        f.error = e instanceof Error ? e.message : String(e)
      })
      throw e
    }
  }

  // ============================ 任务 CRUD ============================
  /**
   * 加载任务列表
   * @param limit 最多返回多少条，默认 50
   */
  async function loadTasks(limit = 50): Promise<void> {
    const res = await convertApi.listTasks(limit)
    tasks.value = res.tasks
  }

  /**
   * 查询并更新单个任务
   * @param taskId 任务 id
   */
  async function fetchTask(taskId: string): Promise<TaskInfo> {
    const task = await convertApi.getTask(taskId)
    const idx = tasks.value.findIndex((t) => t.task_id === taskId)
    if (idx >= 0) tasks.value[idx] = task
    if (currentTask.value?.task_id === taskId) currentTask.value = task
    return task
  }

  /**
   * 删除任务
   * @param taskId 任务 id
   */
  async function removeTask(taskId: string): Promise<void> {
    await convertApi.deleteTask(taskId)
    tasks.value = tasks.value.filter((t) => t.task_id !== taskId)
    if (currentTask.value?.task_id === taskId) {
      currentTask.value = null
      stopPolling()
    }
  }

  /** 设置当前查看的任务（不自动开始轮询） */
  function setCurrentTask(task: TaskInfo | null): void {
    currentTask.value = task
  }

  // ============================ 轮询 ============================
  /**
   * 开始轮询任务进度（setTimeout 链，不重叠）
   * @param taskId 任务 id
   * @param interval 轮询间隔毫秒，默认 1500
   */
  function startPolling(taskId: string, interval = 1500): void {
    if (polling.value) return
    polling.value = true

    const tick = async () => {
      // 关键检查：期间可能已 stop
      if (!polling.value) return
      try {
        const task = await convertApi.getTask(taskId)
        const idx = tasks.value.findIndex((t) => t.task_id === taskId)
        if (idx >= 0) tasks.value[idx] = task
        if (currentTask.value?.task_id === taskId) currentTask.value = task

        if (TERMINAL_STATUSES.includes(task.status)) {
          stopPolling()
        } else {
          pollTimer = window.setTimeout(tick, interval)
        }
      } catch {
        // 查询失败：停止轮询，避免无效请求风暴
        stopPolling()
      }
    }
    tick()
  }

  /** 停止轮询 */
  function stopPolling(): void {
    polling.value = false
    if (pollTimer !== null) {
      window.clearTimeout(pollTimer)
      pollTimer = null
    }
  }

  return {
    // state
    fileList,
    tasks,
    currentTask,
    conversionType,
    polling,
    // getters
    totalSize,
    totalSizeHuman,
    pendingCount,
    runningTasks,
    // 文件操作
    addFiles,
    removeFile,
    clearFiles,
    setConversionType,
    // 提交
    submitSingle,
    submitBatch,
    // 任务 CRUD
    loadTasks,
    fetchTask,
    removeTask,
    setCurrentTask,
    // 轮询
    startPolling,
    stopPolling
  }
})
