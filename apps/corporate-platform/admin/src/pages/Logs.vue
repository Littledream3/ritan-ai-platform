<template>
  <el-card>
    <!-- 筛选 -->
    <el-form :inline="true" style="margin-bottom: 16px">
      <el-form-item label="模型">
        <el-select v-model="filters.model" placeholder="全部" clearable style="width: 180px" @change="fetchData">
          <el-option v-for="m in models" :key="m.model_id" :label="m.display_name" :value="m.model_id" />
        </el-select>
      </el-form-item>
      <el-form-item label="天数">
        <el-input-number v-model="filters.days" :min="1" :max="90" @change="fetchData" style="width: 120px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchData">查询</el-button>
      </el-form-item>
    </el-form>

    <!-- 表格 -->
    <el-table :data="logs" stripe v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column prop="model" label="模型" width="180">
        <template #default="{ row }">{{ modelLabel(row.model) }}</template>
      </el-table-column>
      <el-table-column prop="prompt_tokens" label="输入 Token" width="100" />
      <el-table-column prop="completion_tokens" label="输出 Token" width="100" />
      <el-table-column prop="latency_ms" label="耗时 (ms)" width="100" />
      <el-table-column prop="created_at" label="时间" min-width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="fetchData"
        @size-change="fetchData"
      />
    </div>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getAdminLogs, getModels } from '../api'

const loading = ref(false)
const logs = ref([])
const models = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const filters = reactive({ model: '', days: 7 })

const modelLabels = {
  'deepseek-v4-pro': 'DeepSeek V4 Pro',
  'kimi-k2.7-code': 'Kimi K2.7 Code',
  'qwen3.7-max': 'Qwen 3.7 Max',
  'glm-4.7': 'GLM 4.7',
  'doubao-seed-2-0-pro-260215': '豆包 Seed 2.0',
}
function modelLabel(id) { return modelLabels[id] || id }
function formatTime(t) { return t ? new Date(t).toLocaleString() : '-' }

async function fetchData() {
  loading.value = true
  try {
    const { data } = await getAdminLogs({
      model: filters.model || undefined,
      days: filters.days,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
    })
    logs.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await getModels()
    models.value = data.models || []
  } catch {}
  fetchData()
})
</script>
