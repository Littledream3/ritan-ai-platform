<template>
  <div class="discuss-layout"
       @dragover.prevent="onDragOver"
       @dragleave.prevent="onDragLeave"
       @drop.prevent="onDrop"
  >
    <!-- 拖拽遮罩 -->
    <div v-if="dragging" class="drop-overlay">
      <div class="drop-hint">
        <el-icon :size="48"><UploadFilled /></el-icon>
        <p>释放以上传文件/文件夹</p>
      </div>
    </div>

    <!-- ============ 左侧对话列表 ============ -->
    <div class="discuss-sidebar">
      <el-button type="primary" @click="newConversation" style="width: 100%; margin-bottom: 12px">
        ＋ 新辩论
      </el-button>

      <!-- 深度思考 / 搜索 / 记忆开关 -->
      <div class="toggle-group">
        <div class="toggle-item">
          <el-switch v-model="enableSearch" size="small" />
          <span>搜索</span>
        </div>
        <div class="toggle-item">
          <el-switch v-model="thinking" size="small" active-color="#9b59b6" />
          <span>深度思考</span>
        </div>
        <div class="toggle-item">
          <el-switch v-model="memory" size="small" active-color="#e6a23c" />
          <span>记忆</span>
        </div>
      </div>

      <div class="conv-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          :class="['conv-item', { active: conv.id === activeId }]"
          @click="switchConversation(conv)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-meta">
            <span class="conv-model">{{ conv.model?.split(',')[0] || '-' }}</span>
            <span class="conv-time">{{ formatTime(conv.updated_at) }}</span>
          </div>
          <div class="conv-actions">
            <el-button text size="small" @click.stop="renameConv(conv)">✏️</el-button>
            <el-button text size="small" @click.stop="deleteConv(conv.id)">🗑️</el-button>
          </div>
        </div>
        <el-empty v-if="!conversations.length" description="暂无辩论" :image-size="60" />
      </div>
    </div>

    <!-- ============ 右侧辩论区 ============ -->
    <div class="discuss-main">
      <!-- 历史消息（无活跃辩论时显示已加载的历史） -->
      <div class="discuss-messages" ref="msgContainer" v-if="!discussing && !rounds.length && historyMessages.length">
        <div class="history-notice">
          <el-alert title="此对话包含历史辩论记录" type="info" :closable="false" show-icon style="margin-bottom: 16px" />
        </div>
        <div v-for="(msg, idx) in historyMessages" :key="idx" :class="['hist-msg', msg.role === 'user' ? 'hist-user' : 'hist-assistant']">
          <div class="hist-bubble">
            <div class="hist-content">{{ msg.content }}</div>
            <!-- 推理过程 -->
            <div v-if="msg.reasoning_content" class="msg-reasoning">
              <div class="reasoning-header" @click="msg.reasoningCollapsed = !msg.reasoningCollapsed">
                💭 深度思考 {{ msg.reasoningCollapsed !== false ? '▸' : '▾' }}
              </div>
              <div v-if="msg.reasoningCollapsed === false" class="reasoning-body">{{ msg.reasoning_content }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 问题输入区 -->
      <div class="discuss-header">
        <el-card>
          <el-form :model="form" label-position="top">
            <el-form-item label="问题">
              <el-input
                v-model="form.question"
                type="textarea"
                :rows="3"
                placeholder="输入你想让 AI 们讨论的问题..."
                maxlength="10000"
                show-word-limit
              />
            </el-form-item>

            <!-- 上传区域 -->
            <div class="upload-area">
              <div class="upload-buttons">
                <el-button size="small" @click="triggerFileUpload" :disabled="discussing">📎 上传文件</el-button>
                <el-button size="small" @click="triggerFolderUpload" :disabled="discussing">📁 上传文件夹</el-button>
                <span class="upload-hint">或拖拽文件/文件夹到此处</span>
              </div>
              <input ref="fileInput" type="file" multiple style="display:none" @change="handleFiles" />
              <input ref="folderInput" type="file" webkitdirectory style="display:none" @change="handleFiles" />

              <!-- 待上传文件列表 -->
              <div v-if="pendingFiles.length" class="pending-files">
                <div v-for="(f, i) in pendingFiles" :key="i" class="pending-file-item" :class="{ 'file-error': f.error }">
                  <span class="file-icon">{{ fileIcon(f) }}</span>
                  <img v-if="f.isImage && f.thumbnail" :src="f.thumbnail" class="file-thumb" @click="previewImage = f.thumbnail; showPreview = true" />
                  <div v-else-if="f.isVideo && f.thumbnail" class="file-thumb video-thumb" @click="previewVideoUrl = f.thumbnail; showVideoPreview = true">
                    <img :src="f.thumbnail" />
                    <el-icon class="play-icon"><VideoPlay /></el-icon>
                  </div>
                  <span class="file-name">{{ f.name }}</span>
                  <span class="file-size">{{ formatSize(f.size) }}</span>
                  <span v-if="f.uploading" class="file-status uploading">
                    <el-icon class="is-loading"><Loading /></el-icon> 上传中...
                  </span>
                  <span v-else-if="f.error" class="file-status error">{{ f.error }}</span>
                  <el-button circle size="small" type="danger" @click="removeFile(i)" :disabled="f.uploading">
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>

            <div style="display: flex; gap: 24px; flex-wrap: wrap">
              <el-form-item label="参与模型" style="flex: 1; min-width: 300px">
                <el-checkbox-group v-model="form.models">
                  <el-checkbox
                    v-for="m in availableModels"
                    :key="m.model_id"
                    :value="m.model_id"
                    :label="m.model_id"
                  >{{ m.display_name }} <el-tag size="small" style="margin-left: 4px">{{ m.provider }}</el-tag></el-checkbox>
                </el-checkbox-group>
                <div v-if="form.models.length < 2" style="color: #e6a23c; font-size: 12px; margin-top: 4px">至少选择 2 个模型</div>
                <div v-if="hasVisualAttachments && textOnlyModelNames.length" style="color: #e6a23c; font-size: 12px; margin-top: 4px">
                  ⚠️ 以下模型不支持直接查看图片/视频，将基于文字描述讨论：{{ textOnlyModelNames.join('、') }}
                </div>
              </el-form-item>
              <el-form-item label="讨论轮数">
                <el-radio-group v-model="form.rounds">
                  <el-radio :value="2">2 轮</el-radio>
                  <el-radio :value="3">3 轮</el-radio>
                </el-radio-group>
              </el-form-item>
            </div>
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="discussing"
                :disabled="form.models.length < 2 || !form.question.trim() || pendingFiles.some(f => f.uploading)"
                @click="startDiscuss"
              >
                {{ discussing ? '讨论中...' : '开始讨论' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 讨论过程 -->
      <div class="discuss-body" v-if="rounds.length || discussing">
        <!-- 每个轮次 -->
        <div v-for="(round, ri) in rounds" :key="ri" class="round-section">
          <el-divider>
            <el-tag :type="round.type" size="large">
              第 {{ round.round }} 轮：{{ round.label }}
            </el-tag>
          </el-divider>
          <div class="round-cards">
            <el-card
              v-for="(resp, mi) in round.responses"
              :key="mi"
              class="response-card"
              :class="{ 'response-error': resp.error }"
              shadow="hover"
            >
              <template #header>
                <div class="card-header">
                  <span class="model-badge">{{ resp.model_name }}</span>
                  <el-tag v-if="resp.error" type="danger" size="small">失败</el-tag>
                </div>
              </template>
              <!-- 推理过程 -->
              <div v-if="resp.reasoning_content" class="msg-reasoning">
                <div class="reasoning-header" @click="resp.reasoningCollapsed = !resp.reasoningCollapsed">
                  💭 深度思考 {{ resp.reasoningCollapsed !== false ? '▸' : '▾' }}
                </div>
                <div v-if="resp.reasoningCollapsed === false" class="reasoning-body">{{ resp.reasoning_content }}</div>
              </div>
              <div class="card-content" v-if="resp.content">{{ resp.content }}</div>
              <div class="card-loading" v-else>
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>等待中...</span>
              </div>
            </el-card>
          </div>
        </div>

        <!-- 加载中（等待下一轮） -->
        <div v-if="waitingNext" class="waiting-next">
          <el-icon class="is-loading" :size="32"><Loading /></el-icon>
          <span>等待下一轮...</span>
        </div>
      </div>

      <!-- 最终结论 -->
      <div class="discuss-final" v-if="finalContent">
        <el-divider>
          <el-tag type="success" size="large">最终结论</el-tag>
        </el-divider>
        <el-card shadow="hover" class="final-card">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between">
              <span>由 {{ finalModel }} 综合总结</span>
              <el-button text size="small" @click="openDocEditor(finalContent)">📄 生成文档</el-button>
            </div>
          </template>
          <!-- 最终结论推理 -->
          <div v-if="finalReasoning" class="msg-reasoning" style="margin-bottom: 8px">
            <div class="reasoning-header" @click="finalReasoningCollapsed = !finalReasoningCollapsed">
              💭 深度思考 {{ finalReasoningCollapsed !== false ? '▸' : '▾' }}
            </div>
            <div v-if="finalReasoningCollapsed === false" class="reasoning-body">{{ finalReasoning }}</div>
          </div>
          <div class="final-content">{{ finalContent }}</div>
        </el-card>
      </div>

      <!-- 空状态 -->
      <div v-if="!discussing && !rounds.length && !historyMessages.length" class="empty-state">
        <el-icon :size="64" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p style="margin-top: 16px; color: #999">输入问题，选择至少 2 个模型，开始 AI 辩论</p>
      </div>
    </div>

    <!-- 图片预览弹窗 -->
    <el-dialog v-model="showPreview" title="图片预览" width="auto">
      <img :src="previewImage" style="max-width: 80vw; max-height: 70vh; border-radius: 8px" />
    </el-dialog>

    <!-- 视频预览弹窗 -->
    <el-dialog v-model="showVideoPreview" title="视频预览" width="auto">
      <video :src="previewVideoUrl" controls style="max-width: 80vw; max-height: 70vh; border-radius: 8px" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatDotRound, Loading, UploadFilled, Close, VideoPlay } from '@element-plus/icons-vue'
import { getModels } from '../api'
import api from '../api'

// ---- 工具函数 ----
const TEXT_EXTS = ['txt','py','js','ts','jsx','tsx','json','csv','xml','yaml','yml','toml',
  'ini','cfg','conf','md','rst','sh','bash','html','css','scss','less','sql','log',
  'env','java','c','cpp','h','hpp','rs','go','rb','php','swift','kt','r','m','lua']
const IMAGE_EXTS = ['jpg','jpeg','png','gif','bmp','webp','svg','ico']
const VIDEO_EXTS = ['mp4','mov','avi','webm','mkv']
const UPLOAD_EXTS = ['pdf','docx']

function fileExt(name) { return (name || '').split('.').pop()?.toLowerCase() || '' }
function fileIcon(f) {
  const ext = fileExt(f.name || f)
  if (f.isImage || IMAGE_EXTS.includes(ext)) return '🖼️'
  if (f.isVideo || VIDEO_EXTS.includes(ext)) return '🎬'
  if (ext === 'pdf') return '📕'
  if (ext === 'docx') return '📘'
  if (['txt','md','rst'].includes(ext)) return '📝'
  if (['py','js','ts','java','c','cpp','go','rs','rb','php'].includes(ext)) return '💻'
  if (['json','xml','yaml','yml','toml','csv'].includes(ext)) return '📊'
  return '📄'
}
function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error('读取失败'))
    reader.readAsText(file)
  })
}
function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error('读取失败'))
    reader.readAsDataURL(file)
  })
}
function generateVideoThumbnail(file) {
  return new Promise((resolve) => {
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.muted = true
    video.playsInline = true
    const url = URL.createObjectURL(file)
    video.src = url
    video.onloadeddata = () => { video.currentTime = 1 }
    video.onseeked = () => {
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth || 320
      canvas.height = video.videoHeight || 180
      const ctx = canvas.getContext('2d')
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      const dataUrl = canvas.toDataURL('image/jpeg', 0.7)
      URL.revokeObjectURL(url)
      resolve(dataUrl)
    }
    video.onerror = () => { URL.revokeObjectURL(url); resolve(null) }
    setTimeout(() => { URL.revokeObjectURL(url); resolve(null) }, 5000)
  })
}

// 图片压缩：限制最大尺寸和 JPEG 质量，减少 base64 请求体大小
const MAX_IMAGE_DIM = 1920  // 最大宽/高
const JPEG_QUALITY = 0.7    // JPEG 压缩质量（大量图片时减小体积）
function resizeImage(file) {
  return new Promise((resolve, reject) => {
    // 非图片文件或小文件跳过
    if (!file.type.startsWith('image/') || file.size < 100 * 1024) {
      readFileAsDataURL(file).then(resolve, reject)
      return
    }
    // SVG/GIF 保持原样
    if (file.type === 'image/svg+xml' || file.type === 'image/gif') {
      readFileAsDataURL(file).then(resolve, reject)
      return
    }
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      URL.revokeObjectURL(url)
      let { width, height } = img
      // 仅当超出最大尺寸时才缩放
      if (width <= MAX_IMAGE_DIM && height <= MAX_IMAGE_DIM) {
        readFileAsDataURL(file).then(resolve, reject)
        return
      }
      const ratio = Math.min(MAX_IMAGE_DIM / width, MAX_IMAGE_DIM / height)
      width = Math.round(width * ratio)
      height = Math.round(height * ratio)
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0, width, height)
      const dataUrl = canvas.toDataURL('image/jpeg', JPEG_QUALITY)
      resolve(dataUrl)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      readFileAsDataURL(file).then(resolve, reject)
    }
  })
}
function formatTime(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

// ---- 状态 ----
const router = useRouter()
const availableModels = ref([])
const conversations = ref([])
const activeId = ref(null)
const historyMessages = ref([])
const discussing = ref(false)
const waitingNext = ref(false)
const rounds = ref([])
const finalContent = ref('')
const finalModel = ref('')
const finalReasoning = ref('')
const finalReasoningCollapsed = ref(false)
const dragging = ref(false)
const pendingFiles = ref([])
const fileInput = ref(null)
const folderInput = ref(null)
const showPreview = ref(false)
const previewImage = ref('')
const showVideoPreview = ref(false)
const previewVideoUrl = ref('')
const thinking = ref(false)
const enableSearch = ref(false)
const memory = ref(false)
const msgContainer = ref(null)

const form = reactive({
  question: '',
  models: [],
  rounds: 3,
})

// ---- 计算属性 ----
const hasVisualAttachments = computed(() => pendingFiles.value.some(f => f.isImage || f.isVideo))
const textOnlyModelNames = computed(() => {
  return availableModels.value
    .filter(m => {
      const caps = m.capabilities || ['chat']
      return !caps.includes('vision') && form.models.includes(m.model_id)
    })
    .map(m => m.display_name)
})

// ---- 滚动 ----
async function scrollBottom() {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

// ---- 对话列表 ----
async function fetchConversations() {
  try {
    const { data } = await api.get('/conversations', { params: { conv_type: 'discuss' } })
    conversations.value = data || []
  } catch {}
}

// ---- 切换对话 ----
async function switchConversation(conv) {
  if (activeId.value === conv.id) return
  activeId.value = conv.id

  // 清空当前讨论
  rounds.value = []
  finalContent.value = ''
  finalModel.value = ''
  finalReasoning.value = ''
  pendingFiles.value = []
  form.question = ''
  historyMessages.value = []

  try {
    const { data } = await api.get(`/conversations/${conv.id}`)
    historyMessages.value = (data.messages || []).map(m => ({
      role: m.role,
      content: m.content || '',
      reasoning_content: m.reasoning_content || '',
      reasoningCollapsed: true,
    }))
    await scrollBottom()
  } catch {
    ElMessage.error('加载辩论记录失败')
  }
}

// ---- 新建辩论 ----
async function newConversation() {
  activeId.value = null
  rounds.value = []
  finalContent.value = ''
  finalModel.value = ''
  finalReasoning.value = ''
  historyMessages.value = []
  pendingFiles.value = []
  form.question = ''
  form.models = availableModels.value.length >= 3
    ? availableModels.value.slice(0, 3).map(m => m.model_id)
    : availableModels.value.length >= 2
      ? availableModels.value.slice(0, 2).map(m => m.model_id)
      : []
  form.rounds = 3
}

// ---- 重命名 ----
async function renameConv(conv) {
  try {
    const { value } = await ElMessageBox.prompt('新标题', '重命名', {
      inputValue: conv.title,
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    if (value && value.trim()) {
      await api.put(`/conversations/${conv.id}`, { title: value.trim() })
      conv.title = value.trim()
    }
  } catch {}
}

// ---- 删除对话 ----
async function deleteConv(id) {
  try {
    await ElMessageBox.confirm('确定删除这个辩论对话？消息将一并删除。', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await api.delete(`/conversations/${id}`)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (activeId.value === id) {
      newConversation()
    }
    ElMessage.success('已删除')
  } catch {}
}

// ---- 初始化 ----
onMounted(async () => {
  try {
    const { data } = await getModels()
    availableModels.value = (data.models || []).filter(m => m.available)
    if (availableModels.value.length >= 3) {
      form.models = availableModels.value.slice(0, 3).map(m => m.model_id)
    } else if (availableModels.value.length >= 2) {
      form.models = availableModels.value.slice(0, 2).map(m => m.model_id)
    }
  } catch {
    ElMessage.error('加载模型列表失败')
  }
  await fetchConversations()
})

// ---- 文件上传 ----
function triggerFileUpload() { fileInput.value?.click() }
function triggerFolderUpload() { folderInput.value?.click() }
function removeFile(i) { pendingFiles.value.splice(i, 1) }

async function handleFiles(e) {
  const files = [...(e.target.files || [])]
  if (!files.length) return

  for (const file of files) {
    const relPath = file.webkitRelativePath || file.name
    if (relPath.split('/').some(p => p.startsWith('.'))) continue

    const ext = fileExt(file.name)
    const isImage = file.type.startsWith('image/') || IMAGE_EXTS.includes(ext)
    const isVideo = file.type.startsWith('video/') || VIDEO_EXTS.includes(ext)

    if (isImage) {
      const dataUrl = await resizeImage(file)
      pendingFiles.value.push({
        name: file.name, size: file.size,
        content: dataUrl, isImage: true, isVideo: false,
        thumbnail: dataUrl, uploading: false, error: null,
      })
    } else if (isVideo) {
      const item = {
        name: file.name, size: file.size,
        content: null, isImage: false, isVideo: true,
        thumbnail: null, uploading: true, error: null,
      }
      pendingFiles.value.push(item)
      generateVideoThumbnail(file).then(thumb => { item.thumbnail = thumb })
      try {
        const formData = new FormData()
        formData.append('file', file)
        const token = localStorage.getItem('token')
        const resp = await fetch('/api/v1/upload/video', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        })
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}))
          throw new Error(err.detail || `上传失败 (${resp.status})`)
        }
        const data = await resp.json()
        item.content = data.url
        item.uploading = false
      } catch (err) {
        item.error = err.message
        item.uploading = false
      }
    } else if (TEXT_EXTS.includes(ext)) {
      const text = await readFileAsText(file)
      pendingFiles.value.push({
        name: file.name, size: file.size,
        content: text, isImage: false, isVideo: false,
        thumbnail: null, uploading: false, error: null,
      })
    } else if (UPLOAD_EXTS.includes(ext)) {
      const item = {
        name: file.name, size: file.size,
        content: null, isImage: false, isVideo: false,
        thumbnail: null, uploading: true, error: null,
      }
      pendingFiles.value.push(item)
      try {
        const formData = new FormData()
        formData.append('file', file)
        const token = localStorage.getItem('token')
        const resp = await fetch('/api/v1/upload', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        })
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}))
          throw new Error(err.detail || `上传失败 (${resp.status})`)
        }
        const data = await resp.json()
        item.content = data.content
        item.uploading = false
      } catch (err) {
        item.error = err.message
        item.uploading = false
      }
    } else {
      try {
        const text = await readFileAsText(file)
        pendingFiles.value.push({
          name: file.name, size: file.size,
          content: text, isImage: false, isVideo: false,
          thumbnail: null, uploading: false, error: null,
        })
      } catch {
        ElMessage.warning(`${file.name}: 不支持的文件类型 (.${ext})`)
      }
    }
  }
  if (e.target) e.target.value = ''
}

// ---- 拖拽上传 ----
function onDragOver(e) {
  e.dataTransfer.dropEffect = 'copy'
  dragging.value = true
}
function onDragLeave(e) {
  dragging.value = false
}
async function onDrop(e) {
  dragging.value = false
  const items = [...(e.dataTransfer.items || [])]
  const files = []

  for (const item of items) {
    if (item.kind !== 'file') continue
    const entry = item.webkitGetAsEntry?.()
    if (entry?.isDirectory) {
      files.push(...await traverseDirectory(entry))
    } else {
      const file = item.getAsFile()
      if (file) files.push(file)
    }
  }

  if (files.length) {
    await handleFiles({ target: { files } })
  }
}

async function traverseDirectory(entry) {
  const files = []
  const reader = entry.createReader()
  const readEntries = () => new Promise((resolve) => reader.readEntries((entries) => resolve(entries)))

  let entries
  do {
    entries = await readEntries()
    for (const e of entries) {
      if (e.isFile) {
        const file = await new Promise((resolve) => e.file(resolve))
        Object.defineProperty(file, 'webkitRelativePath', {
          value: e.fullPath.replace(/^\//, ''),
          writable: true,
        })
        files.push(file)
      } else if (e.isDirectory) {
        files.push(...await traverseDirectory(e))
      }
    }
  } while (entries.length > 0)

  return files
}

// ---- 讨论 ----
async function startDiscuss() {
  if (form.models.length < 2) {
    ElMessage.warning('至少选择 2 个模型')
    return
  }

  discussing.value = true
  waitingNext.value = false
  rounds.value = []
  finalContent.value = ''
  finalModel.value = ''
  finalReasoning.value = ''
  finalReasoningCollapsed.value = false
  historyMessages.value = []

  const token = localStorage.getItem('token')
  const modelNames = {}
  for (const m of availableModels.value) {
    modelNames[m.model_id] = m.display_name
  }

  // 分离附件
  const images = pendingFiles.value.filter(f => f.isImage && !f.error).map(f => f.content)
  const videos = pendingFiles.value.filter(f => f.isVideo && !f.error).map(f => f.content)
  const textFiles = pendingFiles.value.filter(f => !f.isImage && !f.isVideo && !f.error)

  // 构建增强后的问题（文本文件内容追加）
  let fullQuestion = form.question.trim()
  if (textFiles.length) {
    const fileTexts = textFiles.map(f => `\n\n--- 📄 ${f.name} ---\n${f.content}`)
    fullQuestion += fileTexts.join('')
  }
  if (fullQuestion.length > 10000) {
    fullQuestion = fullQuestion.substring(0, 9997) + '...'
  }

  // 构建请求体
  const body = {
    question: fullQuestion,
    models: form.models,
    rounds: form.rounds,
    thinking: thinking.value,
    enable_search: enableSearch.value,
    memory: memory.value,
    conversation_id: activeId.value || undefined,
  }
  if (images.length) body.images = images
  if (videos.length) body.videos = videos

  // 生成标题（第一次提问时）
  if (!activeId.value) {
    body.title = fullQuestion.length > 50 ? fullQuestion.substring(0, 50) + '...' : fullQuestion
  }

  // 预估请求体大小，过大时警告
  const bodySize = JSON.stringify(body).length
  if (bodySize > 20 * 1024 * 1024) {
    ElMessage.warning(`请求体较大 (${(bodySize / 1024 / 1024).toFixed(1)}MB)，图片较多时建议分批讨论`)
  }

  try {
    const resp = await fetch('/api/v1/discuss', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    })

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) continue
        const dataStr = trimmed.slice(5).trim()
        if (!dataStr) continue

        try {
          const event = JSON.parse(dataStr)
          handleEvent(event, modelNames)
        } catch {}
      }
    }
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    discussing.value = false
    waitingNext.value = false
  }

  // 刷新对话列表
  await fetchConversations()
  if (!activeId.value) {
    const latest = conversations.value[0]
    if (latest) {
      activeId.value = latest.id
    }
  }
}

function handleEvent(event, modelNames) {
  switch (event.type) {
    case 'start':
      for (let r = 1; r <= (event.rounds || 3); r++) {
        const label = r === 3 ? '最终回答' : r === 2 ? '交叉点评' : '独立回答'
        const type = r === 3 ? 'success' : r === 2 ? 'warning' : ''
        rounds.value.push({
          round: r,
          label,
          type,
          responses: event.models.map(mid => ({
            model_id: mid,
            model_name: modelNames[mid] || mid,
            content: '',
            reasoning_content: '',
            reasoningCollapsed: true,
            error: false,
          })),
        })
      }
      waitingNext.value = false
      break

    case 'round_start':
      waitingNext.value = false
      break

    case 'round_result':
      {
        const roundIdx = event.round - 1
        if (roundIdx < rounds.value.length) {
          const round = rounds.value[roundIdx]
          const resp = round.responses.find(
            r => r.model_id === event.model
          )
          if (resp) {
            resp.content = event.content
            resp.reasoning_content = event.reasoning_content || ''
            resp.error = !!event.error
          }
        }
      }
      break

    case 'final':
      finalContent.value = event.content
      finalModel.value = event.model_name || event.model
      finalReasoning.value = event.reasoning_content || ''
      finalReasoningCollapsed.value = false
      waitingNext.value = false
      break

    case 'error':
      ElMessage.error(`[${event.model || ''}] ${event.message}`)
      waitingNext.value = false
      break

    case 'done':
      waitingNext.value = false
      break
  }
}

function openDocEditor(content) {
  sessionStorage.setItem('doc_prefill', content)
  sessionStorage.setItem('doc_prefill_title', '讨论结论')
  router.push('/admin/documents')
}
</script>

<style scoped>
.discuss-layout {
  display: flex;
  height: calc(100vh - 140px);
  gap: 0;
  position: relative;
}

/* ======== 左侧栏 ======== */
.discuss-sidebar {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid #e4e7ed;
  padding: 12px;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}

.toggle-group {
  margin-bottom: 12px;
  padding: 8px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}
.toggle-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 12px;
  color: #666;
}
.toggle-item + .toggle-item {
  border-top: 1px solid #f0f0f0;
}

.conv-list {
  flex: 1;
  overflow-y: auto;
}

.conv-item {
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  position: relative;
}
.conv-item:hover {
  background: #e8f0fe;
}
.conv-item.active {
  background: #d0e4ff;
}

.conv-title {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 40px;
}

.conv-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.conv-actions {
  position: absolute;
  top: 8px;
  right: 4px;
  display: none;
}
.conv-item:hover .conv-actions {
  display: flex;
}

/* ======== 右侧辩论区 ======== */
.discuss-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow-y: auto;
}

.discuss-header {
  padding: 16px;
  flex-shrink: 0;
}

/* ======== 历史消息 ======== */
.discuss-messages {
  padding: 16px;
  overflow-y: auto;
  max-height: 300px;
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
}
.hist-msg {
  margin-bottom: 8px;
}
.hist-user .hist-bubble {
  background: #409EFF;
  color: #fff;
  border-radius: 10px 10px 4px 10px;
  padding: 8px 12px;
  margin-left: auto;
  max-width: 70%;
}
.hist-assistant .hist-bubble {
  background: #fff;
  color: #333;
  border: 1px solid #e4e7ed;
  border-radius: 10px 10px 10px 4px;
  padding: 8px 12px;
  max-width: 85%;
}
.hist-content {
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 13px;
}

/* ======== 推理过程 ======== */
.msg-reasoning {
  margin: 4px 0 8px;
  border-radius: 6px;
  background: rgba(155, 89, 182, 0.08);
  border-left: 3px solid #9b59b6;
  overflow: hidden;
}
.reasoning-header {
  padding: 6px 10px;
  font-size: 12px;
  color: #7d3c98;
  cursor: pointer;
  user-select: none;
  font-weight: 500;
}
.reasoning-header:hover {
  background: rgba(155, 89, 182, 0.12);
}
.reasoning-body {
  padding: 8px 10px;
  font-size: 12px;
  color: #555;
  line-height: 1.6;
  white-space: pre-wrap;
  border-top: 1px solid rgba(155, 89, 182, 0.15);
  max-height: 400px;
  overflow-y: auto;
}

/* ======== 上传区域 ======== */
.upload-area {
  margin-bottom: 16px;
  border: 1px dashed #dcdfe6;
  border-radius: 8px;
  padding: 12px 16px;
  background: #fafafa;
  transition: border-color 0.3s;
}
.upload-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.upload-hint {
  color: #999;
  font-size: 12px;
  margin-left: 4px;
}
.pending-files {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.pending-file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  max-width: 360px;
}
.pending-file-item.file-error {
  border-color: #f56c6c;
  background: #fef0f0;
}
.file-icon {
  flex-shrink: 0;
  font-size: 18px;
}
.file-thumb {
  width: 36px;
  height: 36px;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
  flex-shrink: 0;
}
.video-thumb {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.video-thumb img {
  width: 36px;
  height: 36px;
  object-fit: cover;
  border-radius: 4px;
}
.video-thumb .play-icon {
  position: absolute;
  color: #fff;
  font-size: 16px;
  background: rgba(0,0,0,.5);
  border-radius: 50%;
  padding: 2px;
}
.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 140px;
}
.file-size {
  color: #999;
  font-size: 11px;
  flex-shrink: 0;
}
.file-status {
  font-size: 11px;
  flex-shrink: 0;
}
.file-status.uploading {
  color: #409eff;
}
.file-status.error {
  color: #f56c6c;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ======== 拖拽遮罩 ======== */
.drop-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(64, 158, 255, 0.12);
  border: 3px dashed #409EFF;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.drop-hint {
  text-align: center;
  color: #409EFF;
  background: rgba(255,255,255,.95);
  padding: 32px 48px;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0,0,0,.1);
}
.drop-hint p {
  margin-top: 12px;
  font-size: 16px;
}

/* ======== 讨论区域 ======== */
.discuss-body {
  padding: 0 16px 20px;
}
.round-section {
  margin-bottom: 16px;
}
.round-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 16px;
}
.response-card {
  transition: all 0.3s;
}
.response-card.response-error {
  border-color: #f56c6c;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.model-badge {
  font-weight: 600;
  color: #409EFF;
}
.card-content {
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  line-height: 1.7;
  font-size: 14px;
}
.card-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #999;
  padding: 20px 0;
}
.waiting-next {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: #999;
}

/* ======== 最终结论 ======== */
.discuss-final {
  padding: 0 16px 20px;
}
.final-card {
  border-color: #67c23a;
}
.final-content {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 14px;
  max-height: 600px;
  overflow-y: auto;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 100px;
}
</style>
