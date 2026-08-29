import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/admin/login',
    name: 'Login',
    component: () => import('../pages/Login.vue'),
  },
  {
    path: '/admin',
    component: () => import('../pages/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('../pages/Dashboard.vue'),
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('../pages/Logs.vue'),
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../pages/Users.vue'),
      },
      {
        path: 'models',
        name: 'Models',
        component: () => import('../pages/Models.vue'),
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('../pages/Chat.vue'),
      },
      {
        path: 'images',
        name: 'Images',
        component: () => import('../pages/Images.vue'),
      },
      {
        path: 'videos',
        name: 'Videos',
        component: () => import('../pages/Videos.vue'),
      },
      {
        path: 'discuss',
        name: 'Discuss',
        component: () => import('../pages/Discuss.vue'),
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('../pages/Documents.vue'),
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/admin',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫 — 未登录重定向
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/admin/login')
  } else if (to.path === '/admin/login' && token) {
    next('/admin')
  } else {
    next()
  }
})

export default router
