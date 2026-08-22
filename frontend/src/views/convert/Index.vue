<!--
  文件转换主页
  - 左侧：拖拽上传 + 文件列表
  - 右侧：转换配置 + 当前任务进度
-->
<template>
  <div class="convert-page">
    <div class="page-header">
      <h2>文件转换</h2>
      <p>支持 Excel / PDF / Word / 图片 互转，批量处理，保留格式</p>
    </div>

    <el-row :gutter="16">
      <!-- 左：上传 + 文件列表 -->
      <el-col :xs="24" :md="16">
        <div class="page-card">
          <h3 class="card-title">
            <el-icon><Upload /></el-icon>
            <span>选择文件</span>
            <span class="card-extra">
              已选 {{ taskStore.fileList.length }} 个，共 {{ taskStore.totalSizeHuman }}
            </span>
          </h3>

          <el-upload
            drag
            multiple
            :auto-upload="false"
            :show-file-list="false"
            :accept="acceptExts"
            :on-change="handleFileChange"
            :before-upload="beforeUpload"
            class="upload-area"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">
              将文件拖拽至此，或<em>点击选择</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 {{ acceptExts }}，单个文件不超过 100MB
              </div>
            </template>
          </el-upload>

          <el-table
            v-if="taskStore.fileList.length"
            :data="taskStore.fileList"
            class="file-table"
            size="default"
          >
            <el-table-column label="文件名" min-width="200">
              <template #default="{ row }">
                <el-icon><Document /></el-icon>
                <span class="filename" :title="row.name">{{ truncate(row.name, 30) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="大小" width="100">
              <template #default="{ row }">{{ row.sizeHuman }}</template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'pending'" type="info">等待</el-tag>
                <el-tag v-else-if="row.status === 'uploading'" type="warning">上传中</el-tag>
                <el-tag v-else-if="row.status === 'uploaded'" type="success">已上传</el-tag>
                <el-tag v-else type="danger" :title="row.error">失败</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" width="160">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.progress"
                  :status="row.status === 'failed' ? 'exception' : row.status === 'uploaded' ? 'success' : undefined"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button type="danger" link @click="taskStore.removeFile(row.id)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="taskStore.fileList.length" class="list-actions">
            <el-button text @click="taskStore.clearFiles()">清空列表</el-button>
          </div>
        </div>
      </el-col>

      <!-- 右：转换配置 -->
      <el-col :xs="24" :md="8">
        <div class="page-card">
          <h3 class="card-title">
            <el-icon><Setting /></el-icon>
            <span>转换配置</span>
          </h3>

          <el-form label-position="top" size="default">
            <el-form-item label="转换类型">
              <el-select
                v-model="conversionType"
                placeholder="请选择"
                class="full-w"
              >
                <el-option
                  v-for="t in CONVERSION_TYPES"
                  :key="t.value"
                  :label="t.label"
                  :value="t.value"
                >
                  <span style="float: left">{{ t.label }}</span>
                  <span style="float: right; color: var(--el-text-color-secondary); font-size: 12px;">
                    {{ categoryLabel(t.category) }}
                  </span>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item v-if="isImageConversion" label="DPI（清晰度）">
              <el-slider
                v-model="dpi"
                :min="72"
                :max="2400"
                :step="72"
                show-input
              />
            </el-form-item>

            <el-form-item v-if="isJpgConversion" label="JPG 质量">
              <el-slider
                v-model="jpgQuality"
                :min="1"
                :max="100"
                :step="1"
                show-input
              />
            </el-form-item>

            <el-form-item label="高级选项">
              <el-checkbox v-model="overwrite">覆盖已存在的目标文件</el-checkbox>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="submitting"
                :disabled="!taskStore.fileList.length || taskStore.pendingCount === 0"
                class="full-w"
                @click="onSubmit"
              >
                <el-icon><Refresh /></el-icon>
                开始转换（{{ taskStore.pendingCount }} 个待处理）
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 当前任务进度卡片 -->
        <div v-if="currentTask" class="page-card mt-16">
          <h3 class="card-title">
            <el-icon><Loading /></el-icon>
            <span>当前任务</span>
          </h3>
          <div class="task-info">
            <p>
              任务 ID：<el-text type="info" size="small">{{ currentTask.task_id }}</el-text>
            </p>
            <p>类型：{{ conversionLabel }}</p>
            <p>
              状态：<el-tag :type="statusTagType">{{ TaskStatusLabel[currentTask.status] }}</el-tag>
            </p>
            <el-progress
              :percentage="currentTask.progress"
              :status="currentTask.status === 'failed' ? 'exception' : currentTask.status === 'success' ? 'success' : undefined"
            />
            <p v-if="currentTask.total_files > 1" class="text-secondary text-center">
              已处理 {{ currentTask.processed_files }} / {{ currentTask.total_files }}
            </p>
            <!-- 二级进度：PDF 等大文档解析时显示「已解析到第 X / Y 页」 -->
            <p
              v-if="currentTask.extra && currentTask.extra.current_page !== undefined && currentTask.extra.total_pages"
              class="text-secondary text-center"
              style="font-size: 12px;"
            >
              <el-icon><Document /></el-icon>
              <span v-if="currentTask.extra.current_file">
                正在解析：{{ truncate(currentTask.extra.current_file, 22) }} ·
              </span>
              第 {{ currentTask.extra.current_page }} / {{ currentTask.extra.total_pages }} 页
              ({{ pagePercent(currentTask.extra.current_page, currentTask.extra.total_pages) }}%)
            </p>
            <p v-if="currentTask.error_message" class="text-danger error-block">
              <el-icon><WarningFilled /></el-icon>
              <span class="error-text">{{ currentTask.error_message }}</span>
            </p>
            <!-- 批量任务：每个文件的处理结果 -->
            <div
              v-if="currentTask.file_results && currentTask.file_results.length > 1"
              class="file-results"
            >
              <p class="text-secondary" style="margin: 12px 0 4px;">各文件结果：</p>
              <el-table
                :data="currentTask.file_results"
                size="small"
                :show-header="false"
                :max-height="220"
              >
                <el-table-column min-width="220">
                  <template #default="{ row }">
                    <el-icon v-if="row.success" style="color: var(--el-color-success);">
                      <CircleCheckFilled />
                    </el-icon>
                    <el-icon v-else style="color: var(--el-color-danger);">
                      <CircleCloseFilled />
                    </el-icon>
                    <span class="filename" :title="row.source_filename">
                      {{ truncate(row.source_filename, 28) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column width="120">
                  <template #default="{ row }">
                    <el-tag
                      v-if="!row.success"
                      type="danger"
                      size="small"
                      :title="row.message || '失败'"
                    >
                      {{ truncate(row.message || '失败', 14) }}
                    </el-tag>
                    <el-tag v-else type="success" size="small">成功</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div
              v-if="currentTask.status === 'success' || currentTask.status === 'partial_success'"
              class="task-actions"
            >
              <el-button
                v-for="file in currentTask.output_files"
                :key="file"
                type="primary"
                size="small"
                @click="onDownload(file)"
              >
                <el-icon><Download /></el-icon>
                下载 {{ truncate(file, 20) }}
              </el-button>
              <el-button
                v-if="currentTask.output_files.length && canPreview(currentTask.output_files[0])"
                type="success"
                plain
                size="small"
                @click="onPreview(currentTask.output_files[0])"
              >
                <el-icon><View /></el-icon>
                预览
              </el-button>
            </div>
            <el-button
              v-else-if="currentTask.status === 'failed'"
              type="primary"
              size="small"
              class="task-actions-btn"
              @click="onViewTaskDetail"
            >
              <el-icon><Document /></el-icon>
              查看任务详情
            </el-button>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 产物预览对话框 -->
    <FilePreviewDialog
      v-model:visible="previewVisible"
      :task-id="currentTask?.task_id || ''"
      :filename="previewFilename"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 文件转换主页
 *
 * 职责：
 * - 提供拖拽上传界面
 * - 维护本地待转换文件列表
 * - 提交单文件 / 批量任务到后端
 * - 展示当前任务的进度与下载入口
 */
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  ElMessage,
  type UploadFile,
  type UploadRawFile
} from 'element-plus'
import {
  CircleCheckFilled,
  CircleCloseFilled,
  WarningFilled,
  View
} from '@element-plus/icons-vue'
import { useTaskStore } from '@/stores/task'
import { useAppStore } from '@/stores/app'
import {
  CONVERSION_TYPES,
  TaskStatus,
  TaskStatusLabel,
  type ConversionType
} from '@/types'
import { ALLOWED_EXTENSIONS } from '@/utils/constants'
import { truncate } from '@/utils/format'
import { getDownloadUrl } from '@/api/convert'
import FilePreviewDialog from '@/components/FilePreviewDialog.vue'

const router = useRouter()
const taskStore = useTaskStore()
const appStore = useAppStore()

// 同步页面标题
appStore.setPageTitle('文件转换')

/** 上传组件 accept 字符串 */
const acceptExts = ALLOWED_EXTENSIONS.join(',')

/** 当前选择的转换类型 */
const conversionType = ref<ConversionType>(taskStore.conversionType)
/** DPI（图片类转换） */
const dpi = ref<number>(300)
/** JPG 输出质量 */
const jpgQuality = ref<number>(95)
/** 是否覆盖已存在文件 */
const overwrite = ref<boolean>(false)
/** 提交中（按钮 loading） */
const submitting = ref<boolean>(false)
/** 预览对话框可见性 */
const previewVisible = ref<boolean>(false)
/** 待预览的文件名 */
const previewFilename = ref<string>('')

// 转换类型变化时同步到 store
watch(conversionType, (v) => taskStore.setConversionType(v))

/** 是否为图片相关转换（需 DPI 控件） */
const isImageConversion = computed<boolean>(() =>
  conversionType.value.includes('_to_png') ||
  conversionType.value.includes('_to_jpg')
)

/** 是否为 JPG 输出（需质量控件） */
const isJpgConversion = computed<boolean>(() =>
  conversionType.value.endsWith('_to_jpg')
)

/** 转换类型显示名 */
const conversionLabel = computed<string>(() => {
  const t = CONVERSION_TYPES.find((c) => c.value === conversionType.value)
  return t?.label || conversionType.value
})

/** 类别显示名（用于 el-option 右侧辅助文字） */
const CATEGORY_LABEL: Record<string, string> = {
  excel: 'Excel',
  pdf: 'PDF',
  word: 'Word',
  image: '图片',
  ocr: 'OCR'
}
function categoryLabel(c: string): string {
  return CATEGORY_LABEL[c] || c
}

/** 当前任务 */
const currentTask = computed(() => taskStore.currentTask)

/** 状态对应的 tag 类型 */
const statusTagType = computed<'success' | 'warning' | 'danger' | 'info'>(() => {
  const s = currentTask.value?.status
  if (s === TaskStatus.SUCCESS) return 'success'
  if (s === TaskStatus.FAILED) return 'danger'
  if (s === TaskStatus.PARTIAL_SUCCESS) return 'warning'
  return 'info'
})

/**
 * el-upload change 回调
 * 关闭 auto-upload 后，这里仅把 file.raw 推入 store
 */
function handleFileChange(file: UploadFile): void {
  if (file.raw) {
    // 去重：相同 File 对象只加入一次
    const exists = taskStore.fileList.some((f) => f.file === file.raw)
    if (!exists) {
      taskStore.addFiles([file.raw])
    }
  }
}

/**
 * 阻止 el-upload 默认的上传行为
 * - true / undefined = 允许上传
 * - false = 阻止
 */
function beforeUpload(_file: UploadRawFile): boolean {
  return false
}

/**
 * 提交转换任务
 * - 单文件：走 submitSingle
 * - 多文件：走 submitBatch 并跳转到 /tasks
 */
async function onSubmit(): Promise<void> {
  if (taskStore.pendingCount === 0) {
    ElMessage.warning('请先选择文件')
    return
  }
  submitting.value = true
  try {
    if (taskStore.fileList.length === 1) {
      const task = await taskStore.submitSingle()
      if (task) {
        ElMessage.success('转换完成')
        taskStore.setCurrentTask(task)
      }
    } else {
      const task = await taskStore.submitBatch()
      if (task) {
        ElMessage.success(`任务已提交，处理 ${task.total_files} 个文件`)
        router.push({ path: '/tasks', query: { taskId: task.task_id } })
      }
    }
  } catch {
    // 错误已由 store / axios 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

/**
 * 触发浏览器下载
 * @param filename 输出文件名
 */
function onDownload(filename: string): void {
  const task = currentTask.value
  if (!task) return
  const url = getDownloadUrl(task.task_id, filename)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
}

/**
 * 打开产物预览（zip 不支持预览）
 */
function onPreview(filename: string): void {
  previewFilename.value = filename
  previewVisible.value = true
}

/** 是否可预览（zip 排除） */
function canPreview(filename: string): boolean {
  return !filename.toLowerCase().endsWith('.zip')
}

/**
 * 跳转到任务详情页（用于失败时查看完整原因）
 */
function onViewTaskDetail(): void {
  const task = currentTask.value
  if (!task) return
  router.push({ path: '/tasks', query: { taskId: task.task_id } })
}

/**
 * 计算页级百分比（保留整数）
 */
function pagePercent(current: number, total: number): number {
  if (!total || total <= 0) return 0
  return Math.min(100, Math.round((current / total) * 100))
}
</script>

<style scoped>
/* 页面容器 */
.convert-page {
  padding: 0;
}

/* 卡片标题 */
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
}
.card-extra {
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: normal;
}

/* 上传区 */
.upload-area {
  width: 100%;
}
.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  margin-bottom: 16px;
}
.upload-icon {
  font-size: 48px;
  color: var(--el-color-primary);
  margin-bottom: 12px;
}
.upload-text {
  font-size: 14px;
}
.upload-text em {
  color: var(--el-color-primary);
  font-style: normal;
  font-weight: 600;
}

/* 文件列表 */
.file-table {
  margin-top: 16px;
}
.filename {
  margin-left: 8px;
}
.list-actions {
  margin-top: 12px;
  text-align: right;
}

/* 当前任务卡片 */
.task-info p {
  margin: 8px 0;
  font-size: 13px;
}
.task-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.task-actions-btn {
  margin-top: 12px;
}

/* 错误块：图标 + 文本 */
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
  max-height: 180px;
  overflow-y: auto;
}
.error-block .error-text {
  flex: 1;
}

.file-results {
  margin-top: 8px;
}
.file-results .filename {
  margin-left: 6px;
}
</style>
