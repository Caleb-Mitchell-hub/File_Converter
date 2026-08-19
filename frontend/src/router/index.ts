/**
 * 路由配置
 *
 * 设计：
 * - 公开路由：/login
 * - 受保护路由：所有其他路由（通过 Layout 包裹）
 * - 全局守卫：检查登录态，未登录跳转 /login 并保留 redirect
 * - 404：兜底跳登录页（演示项目简单处理）
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/Index.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/components/Layout/index.vue'),
    redirect: '/convert',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'convert',
        name: 'Convert',
        component: () => import('@/views/convert/Index.vue'),
        meta: { title: '文件转换', icon: 'Refresh' }
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/tasks/Index.vue'),
        meta: { title: '任务列表', icon: 'List' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/Index.vue'),
        meta: { title: '设置', icon: 'Setting' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/login/Index.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

/**
 * 全局前置守卫
 * - 遍历 matched 链判断是否需要登录
 * - 未登录访问受保护路由时跳转 /login，并通过 query 记录来源
 */
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some((r) => r.meta?.requiresAuth !== false)

  if (requiresAuth && !authStore.isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router
