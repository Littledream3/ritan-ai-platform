<template>
  <el-card>
    <el-row :gutter="20">
      <el-col v-for="m in models" :key="m.model_id" :xs="24" :sm="12" :md="8" :lg="6" style="margin-bottom: 20px">
        <el-card shadow="hover" :body-style="{ padding: '20px' }">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px">
            <h3 style="margin: 0">{{ m.display_name }}</h3>
            <el-tag :type="m.available ? 'success' : 'danger'" size="small">
              {{ m.available ? '可用' : '不可用' }}
            </el-tag>
          </div>
          <p style="color: #999; font-size: 12px; margin: 0 0 8px">{{ m.provider }}</p>
          <p style="color: #666; font-size: 13px; margin: 0 0 8px">{{ m.description }}</p>
          <el-text type="info" size="small" tag="code">{{ m.model_id }}</el-text>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快速测试 -->
    <el-card header="快速测试对话" shadow="hover" style="margin-top: 20px">
      <el-form :inline="true">
        <el-form-item label="模型">
          <el-select v-model="testModel" style="width: 220px">
            <el-option v-for="m in models" :key="m.model_id" :label="m.display_name" :value="m.model_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="问题">
          <el-input v-model="testPrompt" placeholder="输入测试问题" style="width: 300px" @keyup.enter="testChat" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="testChat" :loading="testing">发送</el-button>
        </el-form-item>
      </el-form>
      <div v-if="testResult" style="margin-top: 12px">
        <el-alert type="success" :closable="false">
          <template #title>
            {{ testResult }}
          </template>
        </el-alert>
      </div>
    </el-card>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getModels, chatApi } from '../api'

const models = ref([])
const testModel = ref('deepseek-v4-pro')
const testPrompt = ref('用一句话介绍北京')
const testResult = ref('')
const testing = ref(false)

async function fetchModels() {
  try {
    const { data } = await getModels()
    models.value = data.models || []
  } catch {}
}

async function testChat() {
  testing.value = true
  testResult.value = ''
  try {
    const { data } = await chatApi({
      model: testModel.value,
      messages: [{ role: 'user', content: testPrompt.value }],
      max_tokens: 128,
    })
    testResult.value = data.choices?.[0]?.message?.content || '(空)'
  } catch {
    testResult.value = '调用失败，请检查模型状态'
  } finally {
    testing.value = false
  }
}

onMounted(fetchModels)
</script>
