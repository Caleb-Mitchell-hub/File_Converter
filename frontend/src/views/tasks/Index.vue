<!--
  任务列表页
  - 表格：所有历史任务
  - 过滤：按状态
  - 操作：查看详情 / 下载结果 / 删除
-->
<template>
  <div class="tasks-page">
    <div class="page-header flex-between">
      <div>
        <h2>任务列表</h2>
        <p>查看所有转换任务的状态、进度和结果</p>
      </div>
      <div class="flex" style="gap: 8px;">
        <el-button :icon="Refresh" @click="reload">刷新</el-button>
        <el-select
          v-model="filterStatus"
          placeholder="全部状态"
          clearable
          size="default"
          style="width: 140px;"
        >
          <el-option label="等待中" :value="TaskStatus.PENDING" />
          <el-option label="处理中" :value="TaskStatus.RUNNING" />
          <el-option label="已完成" :value="TaskStatus.SUCCESS" />
          <el-option label="部分成功" :value="TaskStatus.PARTIAL_SUCCESS" />
          <el-option label="失败" :value="TaskStatus.FAILED" />
        </el-select>
      </div>
    </div>

    <div class="page-card">
      <el-table
        :data="filteredTasks"
        v-loading="loading"
        empty-text="暂无任务"
        stripe
      >
        <el-table-column label="任务 ID" prop="task_id" width="160">
          <template #default="{ row }">
            <el-text size="small" type="info">{{ row.task_id }}</el-text>
          </template>
        </el-table-column>
        <el-table-column label="转换类型" width="160">
          <template #default="{ row }">
            {{ getConversionLabel(row.conversion_type) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status as TaskStatusType)">
              {{ TaskStatusLabel[row.status as TaskStatusType] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="240">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress"
              :status="getProgressStatus(row.status as TaskStatusType)"
            />
            <span
              v-if="row.total_files > 1"
              class="text-secondary"
              style="font-size: 12px;"
            >
              {{ row.processed_files }} / {{ row.total_files }}
            </span>
            <!-- 二级进度：PDF → DOCX 页级 -->
            <span
              v-if="row.extra && row.extra.current_page !== undefined && row.extra.total_pages"
              class="text-secondary"
              style="font-size: 12px; display: block;"
            >
              第 {{ row.extra.current_page }} / {{ row.extra.total_pages }} 页
              ({{ pagePercent(row.extra.current_page, row.extra.total_pages) }}%)
            </span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="耗时" width="100">
          <template #default="{ row }">
            <span v-if="row.finished_at">{{ getDuration(row.created_at, row.finished_at) }}</span>
            <span v-else class="text-secondary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'running' || row.status === 'pending'"
              size="small"
              type="primary"
              @click="onView(row as TaskInfo)"
            >查看进度</el-button>
            <el-button
              v-if="row.status === 'success' || row.status === 'partial_success'"
              size="small"
              type="success"
              @click="onDownload(row as TaskInfo)"
            >下载结果</el-button>
            <el-button size="small" @click="onView(row as TaskInfo)">详情</el-button>
            <el-button size="small" type="danger" @click="onDelete(row as TaskInfo)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 任务详情对话框 -->
    <el-dialog v-model="detailVisible" title="任务详情" width="600px">
      <div v-if="detailTask" class="task-detail">
        <p><strong>任务 ID：</strong>{{ detailTask.task_id }}</p>
        <p><strong>转换类型：</strong>{{ getConversionLabel(detailTask.conversion_type) }}</p>
        <p>
          <strong>状态：</strong>
          <el-tag :type="getStatusType(detailTask.status)">
            {{ TaskStatusLabel[detailTask.status] }}
          </el-tag>
        </p>
        <p><strong>创建时间：</strong>{{ formatDate(detailTask.created_at) }}</p>
        <p v-if="detailTask.finished_at">
          <strong>完成时间：</strong>{{ formatDate(detailTask.finished_at) }}
        </p>
        <p><strong>进度：</strong></p>
        <el-progress
          :percentage="detailTask.progress"
          :status="getProgressStatus(detailTask.status)"
        />
        <p
          v-if="detailTask.extra && detailTask.extra.current_page !== undefined && detailTask.extra.total_pages"
          class="text-secondary"
          style="font-size: 12px; margin-top: 6px;"
        >
          <span v-if="detailTask.extra.current_file">
            正在解析：{{ truncate(detailTask.extra.current_file, 30) }} ·
          </span>
          第 {{ detailTask.extra.current_page }} / {{ detailTask.extra.total_pages }} 页
          ({{ pagePercent(detailTask.extra.current_page, detailTask.extra.total_pages) }}%)
        </p>
        <p v-if="detailTask.error_message" class="text-danger error-block">
          <strong>错误：</strong>
          <span class="error-text">{{ detailTask.error_message }}</span>
        </p>
        <div
          v-if="detailTask.file_results && detailTask.file_results.length"
          class="file-results"
        >
          <p style="margin: 12px 0 4px;"><strong>各文件结果：</strong></p>
          <el-table :data="detailTask.file_results" size="small" :max-height="240">
            <el-table-column label="状态" width="70">
              <template #default="{ row }">
                <el-tag v-if="row.success" type="success" size="small">成功</el-tag>
                <el-tag v-else type="danger" size="small">失败</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="文件名" min-width="180">
              <template #default="{ row }">
                <span :title="row.source_filename">
                  {{ truncate(row.source_filename, 30) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="输出" min-width="120">
              <template #default="{ row }">
                <span v-if="row.output_filename" :title="row.output_filename">
                  {{ truncate(row.output_filename, 18) }}
                </span>
                <span v-else class="text-secondary">-</span>
              </template>
            </el-table-column>
            <el-table-column label="原因" min-width="200">
              <template #default="{ row }">
                <span v-if="!row.success" :title="row.message" class="text-danger">
                  {{ truncate(row.message, 60) }}
                </span>
                <span v-else class="text-secondary">{{ row.message || 'ok' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <p v-if="detailTask.output_files.length"><strong>输出文件：</strong></p>
        <ul v-if="detailTask.output_files.length">
          <li v-for="f in detailTask.output_files" :key="f">
            <el-link type="primary" @click="downloadFile(detailTask.task_id, f)">
              {{ f }}
            </el-link>
          </li>
        </ul>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * 任务列表页
 *
 * 职责：
 * - 拉取并展示历史任务
 * - 提供按状态过滤
 * - 任务详情弹窗 + 正在运行任务的轮询
 * - 下载 / 删除任务
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useTaskStore } from '@/stores/task'
import { useAppStore } from '@/stores/app'
import {
  TaskStatus,
  TaskStatusLabel,
  CONVERSION_TYPES,
  type TaskInfo,
  type TaskStatus as TaskStatusType
} from '@/types'
import { formatDate, truncate } from '@/utils/format'
import { getDownloadUrl } from '@/api/convert'
import * as convertApi from '@/api/convert'

const route = useRoute()
const taskStore = useTaskStore()
const appStore = useAppStore()

appStore.setPageTitle('任务列表')

/** 表格加载态 */
const loading = ref<boolean>(false)
/** 状态过滤器 */
const filterStatus = ref<TaskStatusType | ''>('')
/** 详情弹窗可见性 */
const detailVisible = ref<boolean>(false)
/** 当前查看的任务 */
const detailTask = ref<TaskInfo | null>(null)

/** 按状态过滤后的任务列表 */
const filteredTasks = computed<TaskInfo[]>(() => {
  if (!filterStatus.value) return taskStore.tasks
  return taskStore.tasks.filter((t) => t.status === filterStatus.value)
})

/**
 * 获取转换类型显示名
 */
function getConversionLabel(t: string): string {
  return CONVERSION_TYPES.find((c) => c.value === t)?.label || t
}

/**
 * 状态 → Element tag 类型
 */
function getStatusType(s: TaskStatusType): 'success' | 'warning' | 'danger' | 'info' {
  if (s === TaskStatus.SUCCESS) return 'success'
  if (s === TaskStatus.FAILED) return 'danger'
  if (s === TaskStatus.PARTIAL_SUCCESS) return 'warning'
  return 'info'
}

/**
 * 状态 → el-progress 状态
 */
function getProgressStatus(s: TaskStatusType): 'success' | 'exception' | undefined {
  if (s === TaskStatus.SUCCESS || s === TaskStatus.PARTIAL_SUCCESS) return 'success'
  if (s === TaskStatus.FAILED) return 'exception'
  return undefined
}

/**
 * 计算两个时间戳之间的耗时
 */
function getDuration(start: string, end: string): string {
  const ms = new Date(end).getTime() - new Date(start).getTime()
  if (isNaN(ms) || ms < 0) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60_000).toFixed(1)}min`
}

/**
 * 打开任务详情
 * - 正在运行的任务开启轮询
 */
function onView(task: TaskInfo): void {
  detailTask.value = task
  detailVisible.value = true
  if (task.status === TaskStatus.PENDING || task.status === TaskStatus.RUNNING) {
    taskStore.startPolling(task.task_id)
  }
}

/**
 * 详情弹窗内的轮询：把 store 刷新的 task 同步到 detailTask，
 * 保证弹窗里二级进度也跟着变。
 */
let detailTimer: number | null = null
function startDetailPolling(taskId: string): void {
  stopDetailPolling()
  const tick = async () => {
    try {
      const fresh = await convertApi.getTask(taskId)
      detailTask.value = fresh
      if (fresh.status === 'success' || fresh.status === 'failed' || fresh.status === 'partial_success') {
        return
      }
    } catch {
      // 拉失败也无所谓，让外层 store 轮询继续
    }
    detailTimer = window.setTimeout(tick, 1500)
  }
  // 立刻拉一次，立即显示当前状态
  tick()
}
function stopDetailPolling(): void {
  if (detailTimer !== null) {
    window.clearTimeout(detailTimer)
    detailTimer = null
  }
}

/**
 * 下载任务结果
 * - 单文件：直接下载
 * - 多文件：下载 zip 包
 */
function onDownload(task: TaskInfo): void {
  if (task.output_files.length === 1) {
    downloadFile(task.task_id, task.output_files[0])
  } else {
    const url = getDownloadUrl(task.task_id)
    const a = document.createElement('a')
    a.href = url
    a.download = `batch_${task.task_id}.zip`
    a.click()
  }
}

/**
 * 浏览器触发下载单个文件
 */
function downloadFile(taskId: string, filename: string): void {
  const url = getDownloadUrl(taskId, filename)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
}

/**
 * 删除任务（带二次确认）
 */
async function onDelete(task: TaskInfo): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认删除任务 ${task.task_id}？`,
      '提示',
      { type: 'warning' }
    )
    await taskStore.removeTask(task.task_id)
    ElMessage.success('已删除')
  } catch {
    // 用户取消
  }
}

/** 重新拉取任务列表 */
async function reload(): Promise<void> {
  loading.value = true
  try {
    await taskStore.loadTasks(50)
  } finally {
    loading.value = false
  }
}

/** 计算页级百分比 */
function pagePercent(current: number, total: number): number {
  if (!total || total <= 0) return 0
  return Math.min(100, Math.round((current / total) * 100))
}

onMounted(async () => {
  await reload()
  // 如果 URL 带 taskId，自动打开详情
  const taskId = route.query.taskId as string | undefined
  if (taskId) {
    try {
      const t = await taskStore.fetchTask(taskId)
      onView(t)
    } catch {
      // 任务可能已被删除，忽略
    }
  }
})

onUnmounted(() => {
  // 离开页面停止轮询
  taskStore.stopPolling()
  stopDetailPolling()
})

/** 当前查看的任务变化时，自动开/停详情弹窗的二级轮询 */
watch(
  () => detailTask.value?.task_id,
  (id, prev) => {
    if (prev && prev !== id) stopDetailPolling()
    if (
      id
      && (detailTask.value?.status === TaskStatus.PENDING
        || detailTask.value?.status === TaskStatus.RUNNING)
    ) {
      startDetailPolling(id)
    }
  }
)
</script>

<style scoped>
.task-detail p {
  margin: 8px 0;
}
.task-detail ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}
.error-block {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  background: #fef0f0;
  border: 1px solid #fbc4c4;
  color: #c45656;
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 220px;
  overflow-y: auto;
}
.error-block .error-text {
  flex: 1;
}
.file-results {
  margin-top: 4px;
}
</style>
