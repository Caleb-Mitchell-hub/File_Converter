/**
 * 应用入口
 * - 创建 Pinia 状态管理
 * - 注册 Vue Router
 * - 全局挂载 Element Plus 图标
 * - 配置 NProgress 进度条
 * - 加载全局样式
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

import 'element-plus/dist/index.css'
import '@/styles/index.scss'

import App from './App.vue'
import router from './router'

// NProgress 配置
NProgress.configure({ showSpinner: false, trickleSpeed: 200 })

const app = createApp(App)

// 注册所有 Element Plus 图标为全局组件
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component as any)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 路由守卫：开始 / 结束进度条
router.beforeEach((_to, _from, next) => {
  NProgress.start()
  next()
})
router.afterEach(() => {
  NProgress.done()
})

app.mount('#app')
