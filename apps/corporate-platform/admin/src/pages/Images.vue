<template>
  <div class="images-container">
    <!-- 左侧：参数面板 -->
    <div class="panel-left">
      <el-card>
        <template #header>
          <h3 style="margin: 0">文生图</h3>
        </template>
        <el-form :model="form" label-position="top">
          <!-- 模型选择 -->
          <el-form-item label="模型">
            <el-select v-model="form.model" style="width: 100%" @change="onModelChange">
              <el-option
                v-for="m in models"
                :key="m.model_id"
                :label="`${m.display_name} (${m.provider})`"
                :value="m.model_id"
                :disabled="!m.available"
              >
                <span>{{ m.display_name }}</span>
                <span style="float: right; color: #999; font-size: 12px">{{ m.provider }}</span>
              </el-option>
            </el-select>
            <div v-if="currentModel && !currentModel.available" style="color: #e6a23c; font-size: 12px; margin-top: 4px">
              ⚠️ API Key 未配置
            </div>
          </el-form-item>

          <!-- 提示词 -->
          <el-form-item label="提示词">
            <el-input
              v-model="form.prompt"
              type="textarea"
              :rows="4"
              placeholder="描述你想生成的图片..."
              maxlength="5000"
              show-word-limit
            />
          </el-form-item>

          <!-- 尺寸 -->
          <el-form-item v-if="currentModel" label="尺寸">
            <el-select v-model="form.size" style="width: 100%">
              <el-option
                v-for="s in currentModel.sizes"
                :key="s"
                :label="s"
                :value="s"
              />
            </el-select>
          </el-form-item>

          <!-- 质量（仅 GLM） -->
          <el-form-item v-if="currentModel && currentModel.qualities" label="质量">
            <el-radio-group v-model="form.quality">
              <el-radio
                v-for="q in currentModel.qualities"
                :key="q"
                :value="q"
              >{{ q === 'hd' ? 'HD 高清 (~20s)' : 'Standard 标准 (~5-10s)' }}</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 生成数量 -->
          <el-form-item label="生成数量">
            <el-input-number v-model="form.n" :min="1" :max="4" />
          </el-form-item>

          <!-- 生成按钮 -->
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              style="width: 100%"
              :loading="generating"
              :disabled="!form.prompt || !currentModel?.available"
              @click="handleGenerate"
            >
              {{ generating ? '生成中...' : '生成图片' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 右侧：结果展示 -->
    <div class="panel-right">
      <!-- 加载状态 -->
      <div v-if="generating" class="loading-state">
        <el-icon class="is-loading" :size="48"><Loading /></el-icon>
        <p style="margin-top: 16px; color: #999">
          {{ loadingHint }}
        </p>
      </div>

      <!-- 空状态 -->
      <div v-else-if="results.length === 0" class="empty-state">
        <el-icon :size="64" color="#c0c4cc"><PictureFilled /></el-icon>
        <p style="margin-top: 16px; color: #999">输入提示词，开始生成图片</p>
      </div>

      <!-- 结果网格 -->
      <div v-else class="results-grid">
        <div
          v-for="(img, idx) in results"
          :key="idx"
          class="result-card"
        >
          <el-card>
            <el-image
              :src="img.url"
              fit="cover"
              style="width: 100%; aspect-ratio: 1; cursor: pointer"
              :preview-src-list="results.map(r => r.url)"
              :initial-index="idx"
            />
            <div class="result-actions">
              <span class="result-label">#{{ idx + 1 }}</span>
              <el-button
                size="small"
                text
                @click="downloadFile(img.url, `image_${idx + 1}.png`)"
              >下载</el-button>
              <el-button
                size="small"
                text
                @click="copyUrl(img.url)"
              >复制 URL</el-button>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { PictureFilled, Loading } from '@element-plus/icons-vue'
import { getImageModels, generateImage } from '../api'

// ---- 状态 ----
const models = ref([])
const results = ref([])
const generating = ref(false)

const form = reactive({
  model: '',
  prompt: '',
  size: '',
  n: 1,
  quality: '',
})

const currentModel = computed(() => {
  return models.value.find(m => m.model_id === form.model)
})

const loadingHint = computed(() => {
  if (!currentModel.value) return '正在生成...'
  const p = currentModel.value.provider
  if (p === 'qwen') return '通义万相异步生成中，请耐心等待（最长约 60 秒）...'
  return '正在生成中...'
})

// ---- 初始化 ----
onMounted(async () => {
  try {
    const { data } = await getImageModels()
    models.value = data.models || []
    // 默认选中第一个可用的模型
    const firstAvailable = models.value.find(m => m.available)
    if (firstAvailable) {
      form.model = firstAvailable.model_id
      form.size = firstAvailable.default_size
      if (firstAvailable.qualities) {
        form.quality = firstAvailable.qualities[0]
      }
    } else if (models.value.length > 0) {
      form.model = models.value[0].model_id
    }
  } catch {
    ElMessage.error('加载图片模型列表失败')
  }
})

// ---- 方法 ----
function onModelChange() {
  const m = currentModel.value
  if (!m) return
  form.size = m.default_size
  form.quality = m.qualities ? m.qualities[0] : ''
  form.n = 1
}

async function handleGenerate() {
  if (!form.prompt.trim()) {
    ElMessage.warning('请输入提示词')
    return
  }
  if (!currentModel.value?.available) {
    ElMessage.warning('当前模型不可用')
    return
  }

  generating.value = true
  results.value = []
  try {
    const { data } = await generateImage({
      model: form.model,
      prompt: form.prompt.trim(),
      size: form.size || undefined,
      n: form.n,
      quality: form.quality || undefined,
    })
    if (data.data && data.data.length > 0) {
      results.value = data.data
      ElMessage.success(`成功生成 ${data.data.length} 张图片`)
    } else {
      ElMessage.warning('生成完成但未返回图片')
    }
  } catch (err) {
    // 错误由拦截器统一提示
  } finally {
    generating.value = false
  }
}

function copyUrl(url) {
  navigator.clipboard.writeText(url).then(() => {
    ElMessage.success('URL 已复制')
  }).catch(() => {
    // fallback
    const input = document.createElement('input')
    input.value = url
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    ElMessage.success('URL 已复制')
  })
}

function openUrl(url) {
  window.open(url, '_blank')
}

function downloadFile(url, filename) {
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  ElMessage.success('开始下载')
}
</script>

<style scoped>
.images-container {
  display: flex;
  height: calc(100vh - 140px);
  gap: 16px;
}

.panel-left {
  width: 340px;
  flex-shrink: 0;
  overflow-y: auto;
}

.panel-right {
  flex: 1;
  overflow-y: auto;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  flex-wrap: wrap;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding-top: 120px;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  width: 100%;
  align-items: start;
}

.result-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
}

.result-label {
  color: #999;
  font-size: 12px;
  margin-right: auto;
}
</style>
