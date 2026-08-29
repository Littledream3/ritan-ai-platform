<template>
  <el-container style="height: 100vh; overflow: hidden">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" style="transition: width 0.3s">
      <div class="logo">
        <span v-if="!isCollapse">🤖 模型网关</span>
        <span v-else>🤖</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        :collapse="isCollapse"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/admin">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/admin/logs">
          <el-icon><Document /></el-icon>
          <span>用量明细</span>
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/models">
          <el-icon><Monitor /></el-icon>
          <span>模型状态</span>
        </el-menu-item>
        <el-menu-item index="/admin/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>对话</span>
        </el-menu-item>
        <el-menu-item index="/admin/images">
          <el-icon><Picture /></el-icon>
          <span>图片生成</span>
        </el-menu-item>
        <el-menu-item index="/admin/videos">
          <el-icon><VideoCamera /></el-icon>
          <span>视频生成</span>
        </el-menu-item>
        <el-menu-item index="/admin/discuss">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 辩论</span>
        </el-menu-item>
        <el-menu-item index="/admin/documents">
          <el-icon><Document /></el-icon>
          <span>文档生成</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主体 -->
    <el-container style="height: 100%">
      <el-header style="height: 60px; flex-shrink: 0">
        <div class="header-left">
          <el-button @click="isCollapse = !isCollapse" :icon="isCollapse ? 'Expand' : 'Fold'" text />
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/admin' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="pageTitle">{{ pageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag v-if="user.role === 'admin'" type="danger" size="small">管理员</el-tag>
          <span style="margin-left: 8px">{{ user.name }}</span>
          <el-button text @click="handleLogout" style="margin-left: 16px">退出</el-button>
        </div>
      </el-header>

      <el-main style="overflow-y: auto; flex: 1">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)

const user = JSON.parse(localStorage.getItem('user') || '{}')

const activeMenu = computed(() => {
  if (route.path.startsWith('/admin/logs')) return '/admin/logs'
  if (route.path.startsWith('/admin/users')) return '/admin/users'
  if (route.path.startsWith('/admin/models')) return '/admin/models'
  if (route.path.startsWith('/admin/chat')) return '/admin/chat'
  if (route.path.startsWith('/admin/images')) return '/admin/images'
  if (route.path.startsWith('/admin/videos')) return '/admin/videos'
  if (route.path.startsWith('/admin/discuss')) return '/admin/discuss'
  if (route.path.startsWith('/admin/documents')) return '/admin/documents'
  return '/admin'
})

const pageTitle = computed(() => {
  if (route.path.startsWith('/admin/logs')) return '用量明细'
  if (route.path.startsWith('/admin/users')) return '用户管理'
  if (route.path.startsWith('/admin/models')) return '模型状态'
  if (route.path.startsWith('/admin/chat')) return '对话'
  if (route.path.startsWith('/admin/images')) return '图片生成'
  if (route.path.startsWith('/admin/videos')) return '视频生成'
  if (route.path.startsWith('/admin/discuss')) return 'AI 辩论'
  if (route.path.startsWith('/admin/documents')) return '文档生成'
  return ''
})

function handleLogout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/admin/login')
}
</script>

<style scoped>
.el-aside {
  background-color: #304156;
  height: 100vh;
  overflow-y: auto;
}
.el-aside .el-menu {
  border-right: none;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}
.el-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e6e6e6;
  background: #fff;
  flex-shrink: 0;
}
.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.el-main {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>
