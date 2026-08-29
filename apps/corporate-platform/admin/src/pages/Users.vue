<template>
  <el-card>
    <!-- 表格 -->
    <el-table :data="users" stripe v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="name" label="昵称" width="140" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">{{ row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_active"
            @change="(val) => toggleActive(row, val)"
            active-text="启用"
            inactive-text="禁用"
          />
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="160">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchData"
        @size-change="fetchData"
      />
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" title="编辑用户" width="450px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="昵称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="editForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAdminUsers, editUser } from '../api'

const loading = ref(false)
const saving = ref(false)
const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const editForm = reactive({ id: 0, name: '', role: 'user', is_active: true })

function formatTime(t) { return t ? new Date(t).toLocaleString() : '-' }

async function fetchData() {
  loading.value = true
  try {
    const { data } = await getAdminUsers({
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
    })
    users.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function openEdit(row) {
  editForm.id = row.id
  editForm.name = row.name
  editForm.role = row.role
  editForm.is_active = row.is_active
  dialogVisible.value = true
}

async function toggleActive(row, val) {
  try {
    await editUser(row.id, { is_active: val })
    row.is_active = val
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch {}
}

async function handleSave() {
  saving.value = true
  try {
    await editUser(editForm.id, {
      name: editForm.name,
      role: editForm.role,
      is_active: editForm.is_active,
    })
    dialogVisible.value = false
    ElMessage.success('保存成功')
    fetchData()
  } finally {
    saving.value = false
  }
}

onMounted(fetchData)
</script>
