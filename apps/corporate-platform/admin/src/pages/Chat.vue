<template>
  <div class="chat-layout">
    <!-- 左侧对话列表 -->
    <div class="chat-sidebar">
      <el-button type="primary" @click="newConversation" style="width: 100%; margin-bottom: 12px">
        ＋ 新对话
      </el-button>

      <!-- 联网搜索和深度思考开关 -->
      <div class="search-toggle">
        <div style="display: flex; align-items: center; gap: 8px">
          <el-switch v-model="enableSearch" size="small" />
          <span style="font-size: 12px; color: #666">搜索</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px">
          <el-switch v-model="thinking" size="small" active-color="#9b59b6" />
          <span style="font-size: 12px; color: #666">深度思考</span>
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
            <span class="conv-model">{{ modelLabel(conv.model) }}</span>
            <span class="conv-time">{{ formatTime(conv.updated_at) }}</span>
          </div>
          <div class="conv-actions">
            <el-button text size="small" @click.stop="renameConv(conv)">✏️</el-button>
            <el-button text size="small" @click.stop="deleteConv(conv.id)">🗑️</el-button>
          </div>
        </div>
        <el-empty v-if="!conversations.length" description="暂无对话" :image-size="60" />
      </div>
    </div>

    <!-- 右侧聊天区 -->
    <div class="chat-main">
      <!-- 模型选择 -->
      <div class="chat-header">
        <el-select v-model="currentModel" style="width: 220px" size="small">
          <el-option v-for="m in models" :key="m.model_id" :label="m.display_name" :value="m.model_id">
            <span>{{ m.display_name }}</span>
            <el-tag size="small" style="margin-left: 6px">{{ m.provider }}</el-tag>
          </el-option>
        </el-select>
        <span v-if="enableSearch" style="color: #409EFF; font-size: 12px; margin-left: 8px">🔍 联网中</span>
      </div>

      <!-- 消息区域 -->
      <div class="chat-messages" ref="msgContainer">
        <div v-if="!activeId && !messages.length" class="chat-empty">
          <p style="font-size: 48px; margin-bottom: 16px">💬</p>
          <p>选择或创建一个对话开始聊天</p>
        </div>

        <div v-for="(msg, idx) in messages" :key="idx" :class="['msg-row', msg.role === 'user' ? 'msg-user' : 'msg-assistant']">
          <div class="msg-bubble">
            <!-- 图片附件 -->
            <div v-if="msg.images?.length" class="msg-images">
              <img v-for="(img, i) in msg.images" :key="i" :src="img" class="msg-img" @click="previewImage = img" />
            </div>
            <!-- 文件附件 -->
            <div v-if="msg.files?.length" class="msg-files">
              <div v-for="(f, i) in msg.files" :key="i" class="msg-file-tag">
                <span>{{ f.isImage ? '🖼️' : '📄' }} {{ f.name }}</span>
              </div>
            </div>
            <!-- 推理过程 -->
            <div v-if="msg.reasoning_content" class="msg-reasoning">
              <div class="reasoning-header" @click="toggleReasoning(msg)">💭 深度思考 {{ msg.reasoningCollapsed !== false ? '▸' : '▾' }}</div>
              <div v-if="msg.reasoningCollapsed === false" class="reasoning-body">{{ msg.reasoning_content }}</div>
            </div>
            <div class="msg-text" v-if="msg.content">{{ msg.content }}</div>
            <div v-if="msg.streaming" class="msg-loading"><span class="dot-flashing"></span></div>
            <div v-if="msg.role === 'assistant' && !msg.streaming && msg.content" class="msg-copy">
              <el-button text size="small" @click="copyText(msg.content)">📋</el-button>
              <el-button text size="small" @click="openDocEditor(msg.content)">📄 生成文档</el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="chat-input-area">
        <!-- 待发送文件列表 -->
        <div v-if="pendingFiles.length" class="pending-files">
          <div v-for="(f, i) in pendingFiles" :key="i" class="pending-file-item">
            <span class="file-icon">{{ f.isImage ? '🖼️' : fileIcon(f.name) }}</span>
            <span class="file-name">{{ f.name }}</span>
            <span class="file-size">{{ formatSize(f.size) }}</span>
            <el-button circle size="small" type="danger" class="remove-file-btn" @click="removeFile(i)">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>

        <div class="input-row">
          <el-input
            v-model="input"
            type="textarea"
            :rows="2"
            placeholder="Enter 发送，Shift+Enter 换行；支持上传 txt/pdf/docx/图片等文件"
            @keydown.enter.exact="handleSend"
            :disabled="sending"
            resize="none"
            class="input-textarea"
          />
        </div>
        <div class="input-actions">
          <div>
            <el-button @click="triggerUpload" :disabled="sending" size="small">📎 上传文件</el-button>
            <input ref="fileInput" type="file" accept="*" multiple style="display: none" @change="handleFiles" />
          </div>
          <el-button type="primary" @click="handleSend" :loading="sending" :disabled="!input.trim() && !pendingFiles.length">
            发送
          </el-button>
        </div>
      </div>
    </div>

    <!-- 图片预览弹窗 -->
    <el-dialog v-model="showPreview" title="图片预览" width="auto">
      <img :src="previewImage" style="max-width: 80vw; max-height: 70vh; border-radius: 8px" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getModels } from '../api'
import api from '../api'

// ---- 模型列表 ----
const router = useRouter()
const models = ref([])
const currentModel = ref('deepseek-v4-pro')

// ---- 对话管理 ----
const conversations = ref([])
const activeId = ref(null)
const messages = ref([])

// ---- 输入 ----
const input = ref('')
const sending = ref(false)
const pendingFiles = ref([])  // { name, size, content, isImage } — content 是文本或 base64 data URL
const fileInput = ref(null)
const enableSearch = ref(false)
const thinking = ref(false)

// ---- 预览 ----
const previewImage = ref('')
const showPreview = ref(false)

// ---- DOM ----
const msgContainer = ref(null)

// ---- 工具函数 ----
const TEXT_EXTS = ['txt','py','js','ts','jsx','tsx','json','csv','xml','yaml','yml','toml',
  'ini','cfg','conf','md','rst','sh','bash','html','css','scss','less','sql','log',
  'env','java','c','cpp','h','hpp','rs','go','rb','php','swift','kt','r','m','lua']
const IMAGE_EXTS = ['jpg','jpeg','png','gif','bmp','webp','svg','ico']
const UPLOAD_EXTS = ['pdf','docx']

function fileExt(name) { return (name || '').split('.').pop()?.toLowerCase() || '' }
function fileIcon(name) {
  const ext = fileExt(name)
  if (IMAGE_EXTS.includes(ext)) return '🖼️'
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

// ---- 模型名称映射 ----
const modelLabels = {
  'deepseek-v4-pro': 'DeepSeek',
  'kimi-k2.7-code': 'Kimi',
  'qwen3.7-max': 'Qwen',
  'glm-4.7': 'GLM',
  'doubao-seed-2-0-pro-260215': '豆包',
}
function modelLabel(id) {
  return modelLabels[id] || id
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

// ---- 滚动到底部 ----
async function scrollBottom() {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

// ---- 对话列表 ----
async function fetchConversations() {
  try {
    const { data } = await api.get('/conversations')
    conversations.value = data || []
  } catch {}
}

// ---- 切换对话 ----
async function switchConversation(conv) {
  if (activeId.value === conv.id) return
  activeId.value = conv.id
  currentModel.value = conv.model
  messages.value = []
  pendingFiles.value = []

  try {
    const { data } = await api.get(`/conversations/${conv.id}`)
    messages.value = (data.messages || []).map(m => ({
      role: m.role,
      content: m.content || '',
      images: m.images || null,
      files: m.files || null,
      reasoning_content: m.reasoning_content || '',
      reasoningCollapsed: true,
      streaming: false,
    }))
    await scrollBottom()
  } catch {
    ElMessage.error('加载对话失败')
  }
}

function toggleReasoning(msg) {
  msg.reasoningCollapsed = msg.reasoningCollapsed !== false
}

// ---- 新建对话 ----
async function newConversation() {
  activeId.value = null
  messages.value = []
  pendingFiles.value = []
  input.value = ''
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
    await ElMessageBox.confirm('确定删除这个对话？消息将一并删除。', '确认删除', {
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

// ---- 文件上传 ----
function triggerUpload() {
  fileInput.value?.click()
}

async function handleFiles(e) {
  const files = e.target.files
  if (!files?.length) return

  for (const file of files) {
    const ext = fileExt(file.name)
    const isImage = file.type.startsWith('image/') || IMAGE_EXTS.includes(ext)

    if (isImage) {
      // 图片 → base64 data URL
      const dataUrl = await readFileAsDataURL(file)
      pendingFiles.value.push({
        name: file.name,
        size: file.size,
        content: dataUrl,
        isImage: true,
      })
    } else if (TEXT_EXTS.includes(ext)) {
      // 文本文件 → 直接读内容
      const text = await readFileAsText(file)
      pendingFiles.value.push({
        name: file.name,
        size: file.size,
        content: text,
        isImage: false,
      })
    } else if (UPLOAD_EXTS.includes(ext)) {
      // PDF/DOCX → 上传到后端解析
      try {
        ElMessage.info(`正在解析 ${file.name} ...`)
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
        pendingFiles.value.push({
          name: file.name,
          size: file.size,
          content: data.content,
          isImage: false,
        })
        ElMessage.success(`${file.name} 解析完成`)
      } catch (err) {
        ElMessage.error(`${file.name}: ${err.message}`)
      }
    } else {
      // 其他文件 → 尝试当文本读
      try {
        const text = await readFileAsText(file)
        pendingFiles.value.push({
          name: file.name,
          size: file.size,
          content: text,
          isImage: false,
        })
      } catch {
        ElMessage.warning(`${file.name}: 不支持的文件类型 (.${ext})`)
      }
    }
  }
  e.target.value = ''
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

function removeFile(i) {
  pendingFiles.value.splice(i, 1)
}

// ---- 发送消息 ----
async function handleSend(e) {
  if (e?.shiftKey) return
  e?.preventDefault()

  const text = input.value.trim()
  if (!text && !pendingFiles.value.length) return
  if (sending.value) return

  // 分离图片和文档
  const images = pendingFiles.value.filter(f => f.isImage).map(f => f.content)
  const docs = pendingFiles.value.filter(f => !f.isImage)

  // 构建消息文本（文档内容追加到消息后面）
  let fullText = text
  if (docs.length) {
    const docTexts = docs.map(f => `\n\n--- 📄 ${f.name} ---\n${f.content}`)
    fullText = text + docTexts.join('')
  }

  // 构建 API content
  let apiContent = fullText
  if (images.length) {
    const parts = []
    if (fullText) parts.push({ type: 'text', text: fullText })
    for (const img of images) {
      parts.push({ type: 'image_url', image_url: { url: img } })
    }
    apiContent = parts
  }

  // 显示在消息中
  messages.value.push({
    role: 'user',
    content: text,
    images,
    files: [...pendingFiles.value],
    streaming: false,
  })
  const aiIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '', streaming: true })

  input.value = ''
  pendingFiles.value = []
  sending.value = true
  await scrollBottom()

  // 发送请求
  const token = localStorage.getItem('token')
  try {
    const resp = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        model: currentModel.value,
        messages: [
          ...messages.value
            .filter(m => m.role === 'user' || (m.role === 'assistant' && !m.streaming))
            .map(m => {
              // 重建该消息的 API content
              const msgImages = m.images || []
              let msgText = m.content || ''
              // 如果有文件附件，把文件内容加回去
              if (m.files?.length) {
                const docTexts = m.files.filter(f => !f.isImage).map(f => `\n\n--- 📄 ${f.name} ---\n${f.content}`)
                if (docTexts.length) msgText = msgText + docTexts.join('')
              }
              if (msgImages.length) {
                const parts = []
                if (msgText) parts.push({ type: 'text', text: msgText })
                for (const img of msgImages) parts.push({ type: 'image_url', image_url: { url: img } })
                return { role: m.role, content: parts }
              }
              return { role: m.role, content: msgText || '' }
            }),
        ],
        conversation_id: activeId.value || undefined,
        enable_search: enableSearch.value,
        thinking: thinking.value,
        max_tokens: 8192,
      }),
    })

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }

    // SSE 流读取
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
        if (!dataStr || dataStr === '[DONE]') continue

        try {
          const chunk = JSON.parse(dataStr)
          if (chunk.error) throw new Error(chunk.error.message || '流式错误')
          const choiceDelta = chunk.choices?.[0]?.delta || {}
          const deltaContent = choiceDelta.content
          const deltaReasoning = choiceDelta.reasoning_content
          if (deltaContent) {
            messages.value[aiIdx].content += deltaContent
          }
          if (deltaReasoning) {
            messages.value[aiIdx].reasoning_content = (messages.value[aiIdx].reasoning_content || '') + deltaReasoning
          }
          if (deltaContent || deltaReasoning) {
            await scrollBottom()
          }
        } catch (err) {
          if (err.message && !err.message.includes('JSON')) throw err
        }
      }
    }
    messages.value[aiIdx].streaming = false
  } catch (err) {
    messages.value[aiIdx].content = `❌ ${err.message}`
    messages.value[aiIdx].streaming = false
  } finally {
    sending.value = false
  }

  // 刷新对话列表（包含新创建的对话）
  await fetchConversations()
  // 如果服务端创建了新对话，更新 activeId
  if (!activeId.value) {
    // 新对话创建在服务端，取列表最新一条
    const latest = conversations.value[0]
    if (latest) {
      activeId.value = latest.id
    }
  }
}

// ---- 复制文本 ----
function copyText(text) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制')
  }).catch(() => {
    ElMessage.warning('复制失败')
  })
}

function openDocEditor(content) {
  sessionStorage.setItem('doc_prefill', content)
  sessionStorage.setItem('doc_prefill_title', '对话导出')
  router.push('/admin/documents')
}

// ---- 初始化 ----
onMounted(async () => {
  try {
    const { data } = await getModels()
    models.value = data.models || []
  } catch {}
  await fetchConversations()
})
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: calc(100vh - 140px);
  gap: 0;
}

/* 左侧栏 */
.chat-sidebar {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid #e4e7ed;
  padding: 12px;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}

.search-toggle {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  padding: 4px 0;
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

/* 右侧聊天 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  padding: 8px 16px;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f5f5f5;
}

.chat-empty {
  text-align: center;
  color: #999;
  margin-top: 80px;
}

.msg-row {
  display: flex;
  margin-bottom: 16px;
}
.msg-user {
  justify-content: flex-end;
}
.msg-assistant {
  justify-content: flex-start;
}

.msg-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 10px;
  line-height: 1.6;
  word-break: break-word;
  position: relative;
}

.msg-user .msg-bubble {
  background: #409EFF;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.msg-assistant .msg-bubble {
  background: #fff;
  color: #333;
  border: 1px solid #e4e7ed;
  border-bottom-left-radius: 4px;
  white-space: pre-wrap;
}

.msg-images {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}
.msg-img {
  max-width: 160px;
  max-height: 160px;
  border-radius: 6px;
  cursor: pointer;
  object-fit: cover;
}

.msg-copy {
  text-align: right;
  margin-top: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}
.msg-bubble:hover .msg-copy {
  opacity: 1;
}

.msg-loading {
  display: flex;
  align-items: center;
  padding: 6px;
}
.dot-flashing {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #409EFF;
  animation: dot-flash 1s infinite alternate;
}
@keyframes dot-flash {
  0% { opacity: 0.2; transform: scale(0.8); }
  100% { opacity: 1; transform: scale(1.2); }
}

/* 输入区 */
.chat-input-area {
  flex-shrink: 0;
  border-top: 1px solid #e4e7ed;
  padding: 12px 16px;
  background: #fff;
}

.pending-files {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}
.pending-file-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: #f0f5ff;
  border: 1px solid #d0e4ff;
  border-radius: 6px;
  font-size: 12px;
  position: relative;
}
.file-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-size {
  color: #999;
}
.remove-file-btn {
  width: 16px;
  height: 16px;
  min-width: 16px;
}

.msg-files {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
}
.msg-file-tag {
  font-size: 11px;
  padding: 2px 6px;
  background: rgba(255,255,255,0.3);
  border-radius: 4px;
}

.input-row {
  margin-bottom: 8px;
}
.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 推理过程 */
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
</style>
