
<template>
  <el-dialog
    :model-value="visible"
    :title="dialogTitle"
    width="80%"
    top="6vh"
    destroy-on-close
    :close-on-click-modal="false"
    @update:model-value="onClose"
    @open="loadPreview"
  >
    <div v-loading="loading" class="preview-body">
      <iframe
        v-if="type === 'pdf' && objectUrl"
        :src="objectUrl"
        class="preview-frame"
        title="PDF 预览"
      />
      <div v-else-if="type === 'image' && objectUrl" class="preview-image-wrap">
        <img :src="objectUrl" alt="预览" class="preview-image" />
      </div>
      <iframe
        v-else-if="type === 'html' && htmlContent !== null"
        :srcdoc="htmlContent"
        class="preview-frame"
        title="文档预览"
      />
      <el-empty v-else-if="error" :description="error" />
      <el-empty v-else description="暂无预览内容" />
    </div>

    <template #footer>
      <el-button type="primary" @click="onDownload">
        <el-icon><Download /></el-icon>
        下载
      </el-button>
      <el-button @click="onClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 任务产物在线预览对话框
 *
 * - PDF / 图片：后端返回文件流，前端 blob + objectURL 展示
 * - XLSX / DOCX：后端渲染 HTML，前端 iframe srcdoc 展示
 * - 其它（zip 等）：提示下载
 *
 * 所有请求走 axios（自动携带 Bearer token）。
 */
import { computed, onUnmounted, ref } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { downloadTaskFile, previewFile } from '@/api/convert'

const props = defineProps<{
  visible: boolean
  taskId: string
  filename: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
}>()

const loading = ref(false)
const error = ref('')
const type = ref<'pdf' | 'image' | 'html' | 'none'>('none')
const objectUrl = ref('')
const htmlContent = ref<string | null>(null)

const dialogTitle = computed(() => '预览 - ' + props.filename)

/** 可预览的图片扩展名 */
const IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp']

function extOf(name: string): string {
  const idx = name.lastIndexOf('.')
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : ''
}

function cleanup(): void {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value)
    objectUrl.value = ''
  }
  htmlContent.value = null
  type.value = 'none'
  error.value = ''
}

async function loadPreview(): Promise<void> {
  if (!props.visible || !props.filename) return
  cleanup()
  loading.value = true
  try {
    const blob = await previewFile(props.taskId, props.filename)
    const ext = extOf(props.filename)
    if (ext === 'pdf') {
      type.value = 'pdf'
      objectUrl.value = URL.createObjectURL(blob)
    } else if (IMAGE_EXTS.includes(ext)) {
      type.value = 'image'
      objectUrl.value = URL.createObjectURL(blob)
    } else if (ext === 'xlsx' || ext === 'docx') {
      type.value = 'html'
      htmlContent.value = await blob.text()
    } else {
      type.value = 'none'
      error.value = '该格式暂不支持在线预览，请下载后查看'
    }
  } catch (e) {
    type.value = 'none'
    error.value = e instanceof Error ? e.message : '预览加载失败'
  } finally {
    loading.value = false
  }
}

function onDownload(): void {
  downloadTaskFile(props.taskId, props.filename).catch((e) => {
    error.value = e instanceof Error ? e.message : '下载失败'
  })
}

function onClose(): void {
  cleanup()
  emit('update:visible', false)
}

onUnmounted(cleanup)
</script>

<style scoped>
.preview-body {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.preview-frame {
  width: 100%;
  height: 70vh;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  background: #fff;
}
.preview-image-wrap {
  max-width: 100%;
  overflow: auto;
  text-align: center;
}
.preview-image {
  max-width: 100%;
  max-height: 70vh;
}
</style>
