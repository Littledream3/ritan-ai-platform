<template>
  <div class="doc-container">
    <!-- 左侧：输入面板 -->
    <div class="doc-left">
      <el-card>
        <template #header>
          <span style="font-weight: 600">AI 文档生成</span>
        </template>
        <el-form label-position="top">
          <el-form-item label="描述你想要的文档">
            <el-input
              v-model="prompt"
              type="textarea"
              :rows="4"
              placeholder="例如：生成一份关于人工智能技术发展趋势的分析报告，包含市场规模、主要技术方向、以及未来展望..."
              maxlength="5000"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="选择模型">
            <el-select v-model="currentModel" style="width: 100%">
              <el-option
                v-for="m in availableModels"
                :key="m.model_id"
                :label="`${m.display_name} (${m.provider})`"
                :value="m.model_id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="输出格式">
            <el-radio-group v-model="exportFormat">
              <el-radio value="docx">Word (.docx)</el-radio>
              <el-radio value="pdf">PDF (.pdf)</el-radio>
              <el-radio value="xlsx">Excel (.xlsx)</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              style="width: 100%"
              :loading="generating"
              :disabled="!prompt.trim()"
              @click="generateDocument"
            >
              {{ generating ? 'AI 正在生成...' : '生成内容' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 右侧：编辑 & 下载 -->
    <div class="doc-right">
      <el-card>
        <template #header>
          <div class="editor-header">
            <span style="font-weight: 600">内容编辑</span>
            <div style="display: flex; gap: 8px">
              <el-input
                v-model="fileName"
                placeholder="文件名"
                size="small"
                style="width: 180px"
              />
              <el-button
                type="success"
                size="small"
                :disabled="!editorContent.trim()"
                :loading="downloading"
                @click="downloadDocument"
              >
                下载文件
              </el-button>
            </div>
          </div>
        </template>
        <el-input
          v-model="editorContent"
          type="textarea"
          :rows="18"
          placeholder="AI 生成的内容将显示在这里，你可以直接编辑..."
          class="editor-textarea"
        />
        <div v-if="!editorContent && !generating" class="editor-placeholder">
          <el-icon :size="48" color="#c0c4cc"><Document /></el-icon>
          <p style="margin-top: 12px; color: #999">输入文档描述，点击"生成内容"</p>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { getModels, exportDocumentApi, downloadBlob } from '../api'

// ---- 状态 ----
const availableModels = ref([])
const currentModel = ref('')
const prompt = ref('')
const exportFormat = ref('docx')
const editorContent = ref('')
const fileName = ref('文档')
const generating = ref(false)
const downloading = ref(false)

// ---- 初始化 ----
onMounted(async () => {
  try {
    const { data } = await getModels()
    availableModels.value = (data.models || []).filter(m => m.available)
    if (availableModels.value.length) {
      currentModel.value = availableModels.value[0].model_id
    }
  } catch {
    ElMessage.error('加载模型列表失败')
  }

  // 如果从其他页面跳转过来带了预填内容
  const prefill = sessionStorage.getItem('doc_prefill')
  if (prefill) {
    editorContent.value = prefill
    fileName.value = sessionStorage.getItem('doc_prefill_title') || '文档'
    sessionStorage.removeItem('doc_prefill')
    sessionStorage.removeItem('doc_prefill_title')
  }
})

// 自动更新文件名（格式变化时）
watch(exportFormat, (val) => {
  const base = fileName.value.replace(/\.(docx|pdf|xlsx)$/i, '')
  fileName.value = base + '.' + val
})

// ---- 方法 ----
async function generateDocument() {
  if (!prompt.value.trim()) return

  generating.value = true
  editorContent.value = ''

  const token = localStorage.getItem('token')
  const modelPrompt = exportFormat.value === 'xlsx'
    ? `${prompt.value}\n\n请以 Markdown 表格格式输出数据。要求：\n1. 第一行是表头\n2. 每行数据用 | 分隔\n3. 数据要完整、准确`
    : `${prompt.value}\n\n请直接输出文档正文内容，不要包含额外的解释说明。使用清晰的段落结构和标题。`

  try {
    const resp = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        model: currentModel.value,
        messages: [{ role: 'user', content: modelPrompt }],
        max_tokens: 4096,
      }),
    })

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }

    const data = await resp.json()
    const text = data.choices?.[0]?.message?.content || ''
    editorContent.value = text

    // 自动设置文件名
    const baseName = prompt.value.trim().slice(0, 30).replace(/[\/\\]/g, '_')
    fileName.value = (baseName || '文档') + '.' + exportFormat.value
    ElMessage.success('内容生成完成，可编辑后下载')
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    generating.value = false
  }
}

async function downloadDocument() {
  if (!editorContent.value.trim()) return

  downloading.value = true
  try {
    const body = {
      content: editorContent.value,
      format: exportFormat.value,
      title: fileName.value.replace(/\.(docx|pdf|xlsx)$/i, ''),
      type: 'document',
    }

    // Excel 特殊处理：尝试解析 markdown 表格
    if (exportFormat.value === 'xlsx') {
      const rows = parseMarkdownTable(editorContent.value)
      if (rows.length) {
        body.rows = rows
      }
    }

    const resp = await exportDocumentApi(body)
    downloadBlob(resp.data, fileName.value)
  } catch {} finally {
    downloading.value = false
  }
}

function parseMarkdownTable(text) {
  // 解析 Markdown 表格为 list[dict]
  const lines = text.split('\n').filter(l => l.trim().startsWith('|'))
  if (lines.length < 2) return []

  const parseRow = (line) =>
    line.trim().replace(/^\||\|$/g, '').split('|').map(s => s.trim())

  const headers = parseRow(lines[0])
  // 跳过分隔行（如果存在）
  const dataStart = lines[1] && lines[1].includes('---') ? 2 : 1
  const rows = []
  for (let i = dataStart; i < lines.length; i++) {
    const cells = parseRow(lines[i])
    const row = {}
    headers.forEach((h, idx) => {
      row[h || `列${idx + 1}`] = cells[idx] || ''
    })
    if (Object.values(row).some(v => v)) rows.push(row)
  }
  return rows
}
</script>

<style scoped>
.doc-container {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.doc-left {
  flex-shrink: 0;
}

.doc-right {
  flex: 1;
  min-width: 0;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.editor-textarea :deep(.el-textarea__inner) {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.8;
  min-height: 500px;
}

.editor-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 0;
}

@media (max-width: 900px) {
  .doc-container {
    grid-template-columns: 1fr;
  }
}
</style>
