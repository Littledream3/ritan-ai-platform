<template>
  <div>
    <!-- 管理端统计卡片 -->
    <el-row v-if="isAdmin" :gutter="20" style="margin-bottom: 20px">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="总调用量" :value="stats.total_calls">
            <template #prefix><el-icon color="#409EFF"><TrendCharts /></el-icon></template>
          </el-statistic>
          <p class="stat-desc">最近 {{ days }} 天</p>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="总 Token 消耗" :value="stats.total_prompt_tokens + stats.total_completion_tokens">
            <template #prefix><el-icon color="#67C23A"><Coin /></el-icon></template>
          </el-statistic>
          <p class="stat-desc">输入 {{ stats.total_prompt_tokens }} / 输出 {{ stats.total_completion_tokens }}</p>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="活跃用户" :value="stats.active_users">
            <template #prefix><el-icon color="#E6A23C"><UserFilled /></el-icon></template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="可用模型" :value="stats.available_models ?? 5">
            <template #prefix><el-icon color="#F56C6C"><Monitor /></el-icon></template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 模型用量占比 + 今日用量汇总 -->
    <el-row :gutter="20">
      <el-col v-if="isAdmin" :xs="24" :md="12">
        <el-card header="模型调用占比" shadow="hover">
          <div v-if="stats.by_model && stats.by_model.length" style="height: 280px">
            <div
              v-for="m in stats.by_model"
              :key="m.model"
              style="margin-bottom: 16px"
            >
              <div style="display: flex; justify-content: space-between; margin-bottom: 4px">
                <span>{{ modelLabel(m.model) }}</span>
                <span style="color: #999">{{ m.calls }} 次</span>
              </div>
              <el-progress
                :percentage="Math.round((m.calls / totalCalls) * 100)"
                :color="progressColor(m.model)"
              />
            </div>
          </div>
          <el-empty v-else description="暂无数据" />
        </el-card>
      </el-col>

      <el-col :xs="24" :md="isAdmin ? 12 : 24">
        <el-card header="今日我的用量" shadow="hover">
          <div v-if="today.summary?.calls > 0">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="今日调用">{{ today.summary.calls }} 次</el-descriptions-item>
              <el-descriptions-item label="输入 Token">{{ today.summary.prompt_tokens.toLocaleString() }}</el-descriptions-item>
              <el-descriptions-item label="输出 Token">{{ today.summary.completion_tokens.toLocaleString() }}</el-descriptions-item>
            </el-descriptions>
            <div v-if="today.by_model?.length" style="margin-top: 16px">
              <el-tag v-for="m in today.by_model" :key="m.model" style="margin-right: 8px; margin-bottom: 8px">
                {{ modelLabel(m.model) }}：{{ m.calls }} 次
              </el-tag>
            </div>
          </div>
          <el-empty v-else description="今日暂无调用" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 天数选择 -->
    <div v-if="isAdmin" style="margin-top: 16px; text-align: right">
      统计范围：
      <el-radio-group v-model="days" @change="fetchStats" size="small">
        <el-radio-button :value="1">今天</el-radio-button>
        <el-radio-button :value="7">7 天</el-radio-button>
        <el-radio-button :value="30">30 天</el-radio-button>
      </el-radio-group>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getAdminStats, getTodayStats } from '../api'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const isAdmin = user.role === 'admin'

const days = ref(7)
const stats = ref({})
const today = ref({ summary: {}, by_model: [] })

const totalCalls = computed(() =>
  (stats.value.by_model || []).reduce((s, m) => s + m.calls, 0) || 1
)

const modelLabels = {
  'deepseek-v4-pro': 'DeepSeek V4 Pro',
  'kimi-k2.7-code': 'Kimi K2.7 Code',
  'qwen3.7-max': 'Qwen 3.7 Max',
  'glm-4.7': 'GLM 4.7',
  'doubao-seed-2-0-pro-260215': '豆包 Seed 2.0',
}
const modelColors = {
  'deepseek-v4-pro': '#409EFF',
  'kimi-k2.7-code': '#67C23A',
  'qwen3.7-max': '#E6A23C',
  'glm-4.7': '#F56C6C',
  'doubao-seed-2-0-pro-260215': '#909399',
}

function modelLabel(id) {
  return modelLabels[id] || id
}
function progressColor(id) {
  return modelColors[id] || '#409EFF'
}

async function fetchStats() {
  if (isAdmin) {
    try {
      const { data } = await getAdminStats(days.value)
      stats.value = data
      stats.value.available_models = 5
    } catch {}
  }
  try {
    const { data } = await getTodayStats()
    today.value = data
  } catch {}
}

onMounted(fetchStats)
</script>

<style scoped>
.stat-card {
  margin-bottom: 16px;
}
.stat-desc {
  color: #999;
  font-size: 12px;
  margin: 0;
}
</style>
