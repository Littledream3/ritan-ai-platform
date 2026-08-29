<template>
  <div class="videos-container">
    <!-- 左侧：参数面板 -->
    <div class="panel-left">
      <el-card>
        <template #header>
          <h3 style="margin: 0">文生视频</h3>
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
              placeholder="描述你想生成的视频内容..."
              maxlength="3000"
              show-word-limit
            />
          </el-form-item>

          <!-- 分辨率 -->
          <el-form-item v-if="currentModel" label="分辨率">
            <el-select v-model="form.resolution" style="width: 100%">
              <el-option
                v-for="r in currentModel.resolutions"
                :key="r"
                :label="r"
                :value="r"
              />
            </el-select>
          </el-form-item>

          <!-- 比例 -->
          <el-form-item v-if="currentModel" label="画面比例">
            <el-select v-model="form.ratio" style="width: 100%">
              <el-option
                v-for="r in currentModel.ratios"
                :key="r"
                :label="r"
                :value="r"
              />
            </el-select>
          </el-form-item>

          <!-- 时长 -->
          <el-form-item v-if="currentModel" label="时长（秒）">
            <el-slider
              v-model="form.duration"
              :min="currentModel.durations[0]"
              :max="currentModel.max_duration"
              :marks="durationMarks"
              show-input
            />
          </el-form-item>

          <!-- 质量（仅 GLM） -->
          <el-form-item v-if="currentModel && currentModel.qualities" label="质量">
            <el-radio-group v-model="form.quality">
              <el-radio
                v-for="q in currentModel.qualities"
                :key="q"
                :value="q"
              >{{ q === 'quality' ? 'Quality 质量优先' : 'Speed 速度优先' }}</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- FPS（仅 GLM） -->
          <el-form-item v-if="currentModel && currentModel.fps_options" label="帧率 (FPS)">
            <el-radio-group v-model="form.fps">
              <el-radio
                v-for="f in currentModel.fps_options"
                :key="f"
                :value="f"
              >{{ f }}</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 音频 -->
          <el-form-item label="生成音频">
            <el-switch v-model="form.with_audio" />
            <span style="margin-left: 8px; color: #999; font-size: 12px">{{ form.with_audio ? 'AI 自动配音' : '静音视频' }}</span>
          </el-form-item>

          <!-- 水印 -->
          <el-form-item label="AI 水印">
            <el-switch v-model="form.watermark" />
            <span style="margin-left: 8px; color: #999; font-size: 12px">{{ form.watermark ? '包含' : '不包含' }}</span>
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
              {{ generating ? `生成中 (${elapsed}s)...` : '生成视频' }}
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
          视频生成中，请耐心等待（最长约 5 分钟）...
        </p>
        <p style="margin-top: 8px; color: #bbb; font-size: 13px">
          已等待 {{ elapsed }} 秒
        </p>
      </div>

      <!-- 空状态 -->
      <div v-else-if="results.length === 0" class="empty-state">
        <el-icon :size="64" color="#c0c4cc"><VideoCamera /></el-icon>
        <p style="margin-top: 16px; color: #999">输入提示词，开始生成视频</p>
      </div>

      <!-- 结果 -->
      <div v-else class="results-area">
        <div
          v-for="(vid, idx) in results"
          :key="idx"
          class="result-card"
        >
          <el-card>
            <video
              :src="vid.url"
              controls
              style="width: 100%; max-height: 480px; border-radius: 4px"
              preload="metadata"
            >
              您的浏览器不支持视频播放
            </video>
            <div class="result-actions">
              <span class="result-label">#{{ idx + 1 }}</span>
              <el-button size="small" text @click="downloadFile(vid.url, `video_${idx + 1}.mp4`)">下载</el-button>
              <el-button size="small" text @click="copyUrl(vid.url)">复制 URL</el-button>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCamera, Loading } from '@element-plus/icons-vue'
import { getVideoModels, generateVideo } from '../api'

// ---- 状态 ----
const models = ref([])
const results = ref([])
const generating = ref(false)
const elapsed = ref(0)
let elapsedTimer = null

const form = reactive({
  model: '',
  prompt: '',
  resolution: '',
  ratio: '16:9',
  duration: 5,
  quality: '',
  fps: 30,
  with_audio: true,
  watermark: false,
})

const currentModel = computed(() => {
  return models.value.find(m => m.model_id === form.model)
})

const durationMarks = computed(() => {
  if (!currentModel.value) return {}
  const marks = {}
  for (const d of currentModel.value.durations) {
    marks[d] = `${d}s`
  }
  return marks
})

// ---- 初始化 ----
onMounted(async () => {
  try {
    const { data } = await getVideoModels()
    models.value = data.models || []
    const firstAvailable = models.value.find(m => m.available)
    if (firstAvailable) {
      form.model = firstAvailable.model_id
      form.resolution = firstAvailable.default_resolution
      form.ratio = firstAvailable.ratios[0]
      form.duration = firstAvailable.durations[0]
      if (firstAvailable.qualities) {
        form.quality = firstAvailable.qualities[0]
      }
      if (firstAvailable.fps_options) {
        form.fps = firstAvailable.fps_options[0]
      }
    } else if (models.value.length > 0) {
      form.model = models.value[0].model_id
    }
  } catch {
    ElMessage.error('加载视频模型列表失败')
  }
})

onUnmounted(() => {
  if (elapsedTimer) clearInterval(elapsedTimer)
})

// ---- 方法 ----
function onModelChange() {
  const m = currentModel.value
  if (!m) return
  form.resolution = m.default_resolution
  form.ratio = m.ratios[0]
  form.duration = m.durations[0]
  form.quality = m.qualities ? m.qualities[0] : ''
  form.fps = m.fps_options ? m.fps_options[0] : 30
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
  elapsed.value = 0
  elapsedTimer = setInterval(() => { elapsed.value++ }, 1000)

  try {
    const { data } = await generateVideo({
      model: form.model,
      prompt: form.prompt.trim(),
      resolution: form.resolution || undefined,
      ratio: form.ratio || undefined,
      duration: form.duration,
      quality: form.quality || undefined,
      fps: currentModel.value.fps_options ? form.fps : undefined,
      with_audio: form.with_audio,
      watermark: form.watermark,
    })
    if (data.data && data.data.length > 0) {
      results.value = data.data
      ElMessage.success('视频生成完成')
    } else {
      ElMessage.warning('生成完成但未返回视频')
    }
  } catch (err) {
    // 错误由拦截器统一提示
  } finally {
    generating.value = false
    if (elapsedTimer) {
      clearInterval(elapsedTimer)
      elapsedTimer = null
    }
  }
}

function copyUrl(url) {
  navigator.clipboard.writeText(url).then(() => {
    ElMessage.success('URL 已复制')
  }).catch(() => {
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
.videos-container {
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

.results-area {
  width: 100%;
  max-width: 800px;
}

.result-card {
  margin-bottom: 16px;
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
