# 文件转换平台前端

> Vue 3 + Vite + TypeScript + Element Plus 企业级文件转换前端

[![Vue](https://img.shields.io/badge/Vue-3.4%2B-42b883)](https://vuejs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4%2B-3178c6)](https://www.typescriptlang.org)
[![Element Plus](https://img.shields.io/badge/Element_Plus-2.7%2B-409eff)](https://element-plus.org)

## ✨ 特性

- 🎨 **现代化技术栈**：Vue 3 Composition API + `<script setup>` + TypeScript
- 🚀 **极速开发**：Vite 5 + HMR + 自动按需引入（Element Plus）
- 📦 **企业级架构**：清晰的目录分层 + Pinia setup 风格 + 模块化路由
- 🌓 **暗色模式**：内置主题切换，CSS 变量驱动
- 🔄 **进度轮询**：基于 setTimeout 递归，避免请求堆积
- 🛡️ **类型安全**：完整 TypeScript 类型注解，编译期错误检测
- 📱 **响应式**：Element Plus Container 布局自适应桌面/平板

## 📁 项目结构

```
frontend/
├── public/
│   └── favicon.svg
├── src/
│   ├── api/                       # API 层
│   │   ├── index.ts               # axios 实例 + 拦截器 + 统一响应处理
│   │   ├── auth.ts                # 登录 / 登出 / 当前用户
│   │   ├── upload.ts              # 文件上传（支持进度回调）
│   │   └── convert.ts             # 转换 / 任务 / 下载 URL 构造
│   ├── stores/                    # Pinia 状态管理（setup 风格）
│   │   ├── auth.ts                # 认证（token、user、login/logout）
│   │   ├── app.ts                 # 全局（主题、侧边栏、loading、pageTitle）
│   │   └── task.ts                # 任务（文件列表、任务列表、轮询）
│   ├── router/                    # Vue Router
│   │   └── index.ts               # 路由表 + 全局守卫
│   ├── components/                # 公共组件
│   │   └── Layout/
│   │       ├── index.vue          # 主布局（侧边栏 + 顶栏 + 内容）
│   │       ├── Sidebar.vue        # 侧边栏菜单
│   │       ├── Header.vue         # 顶栏（主题切换、用户菜单）
│   │       └── constants.ts       # 布局尺寸常量
│   ├── views/                     # 页面
│   │   ├── login/Index.vue        # 登录页（占位）
│   │   ├── convert/Index.vue      # 转换主页（拖拽上传 + 配置 + 进度）
│   │   ├── tasks/Index.vue        # 任务列表 + 详情对话框
│   │   └── settings/Index.vue     # 系统设置（主题 + 账户 + 关于）
│   ├── types/                     # TypeScript 类型
│   │   └── index.ts               # 枚举 + API 模型 + 文件模型
│   ├── utils/                     # 工具函数
│   │   ├── constants.ts           # 常量（localStorage 键、大小限制、状态码）
│   │   └── format.ts              # 格式化（字节、时间、UUID）
│   ├── styles/                    # 全局样式
│   │   ├── index.scss             # 入口
│   │   ├── variables.scss         # 变量
│   │   ├── reset.scss             # 基础重置
│   │   └── dark.scss              # 暗色模式
│   ├── App.vue                    # 根组件
│   ├── main.ts                    # 应用入口
│   └── env.d.ts                   # 环境变量类型
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── .env.development               # 开发环境变量
├── .env.production                # 生产环境变量
├── .gitignore
└── README.md
```

## 🚀 快速开始

### 环境要求
- Node.js ≥ 18
- npm ≥ 9（或 pnpm / yarn）

### 安装依赖
```bash
cd frontend
npm install
```

### 启动开发服务器
```bash
npm run dev
```

默认启动在 `http://localhost:5173`（端口被占用时自动顺延）。

**开发服务器特性**：
- HMR 热更新
- `/api` 自动代理到后端（默认 `http://localhost:8000`）
- 自动打开浏览器

### 生产构建
```bash
npm run build
```

构建产物在 `dist/` 目录，输出体积参考：
- `vue-vendor`: ~110 KB（gzip 43 KB）
- `element-plus`: ~1 MB（gzip 341 KB）
- `utils` (axios + nprogress): ~50 KB（gzip 19 KB）
- **总计 gzip 约 430 KB**

### 类型检查
```bash
npm run type-check
```

## ⚙️ 配置

通过环境变量配置（`.env.development` / `.env.production`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_APP_TITLE` | `文件转换平台` | 应用标题 |
| `VITE_API_BASE` | `http://localhost:8000`（dev） / 空（prod） | 后端地址 |
| `VITE_API_PREFIX` | `/api` | API 路径前缀 |

后端实际路径 = `VITE_API_BASE + VITE_API_PREFIX`，例如：
- 开发：`http://localhost:8000/api/...`
- 生产：`/api/...`（Nginx 反代）

## 🏗 架构说明

### 数据流
```
View (Vue Component)
  └─→ Composable / Action
       └─→ Pinia Store (auth/app/task)
            └─→ API Module (auth/upload/convert)
                 └─→ Axios (with interceptors)
                      └─→ Backend
```

### 关键技术决策

1. **Pinia setup 风格**：所有 store 用 `defineStore('name', () => { ... })` 组合式风格，比 options 风格更灵活、类型推断更好。

2. **持久化用 localStorage**：避免引入 `pinia-plugin-persistedstate` 依赖。Store 内部手动读写 `STORAGE_KEYS` 常量。

3. **API 拦截器自动剥离外壳**：响应拦截器检测 `{code, message, data}` 结构后自动 `resolve(data)`，业务代码无需 `.data.data`。

4. **上传进度复用 axios 实例**：从 `api/index.ts` 导入 `service` 实例复用拦截器，单独 `onUploadProgress` 不走通用 `post()` 包装。

5. **轮询用 setTimeout 链**：每次请求独立 schedule，避免 setInterval 堆积。终态（SUCCESS / FAILED / PARTIAL_SUCCESS）自动停止。

6. **路由守卫 + localStorage**：刷新页面后从 localStorage 恢复 token，守卫判断 `authStore.isLoggedIn`。

7. **暗色模式用 CSS 变量**：在 `html.dark` 上一组 CSS 变量覆盖 Element Plus 的设计 token，无需重新挂载组件。

8. **NProgress 进度条**：在 `router.beforeEach` 启动 / `afterEach` 结束，配合路由切换淡入淡出动画。

## 📡 后端 API 约定

前端调用的端点（与后端 FastAPI 对应）：

| 方法 | 路径 | 用途 |
|------|------|------|
| `POST` | `/api/auth/login` | 用户登录 |
| `POST` | `/api/auth/logout` | 用户登出 |
| `GET`  | `/api/auth/me` | 获取当前用户 |
| `POST` | `/api/upload` | 上传单个文件 |
| `POST` | `/api/upload/batch` | 批量上传 |
| `POST` | `/api/convert` | 单文件转换（multipart） |
| `POST` | `/api/convert/batch` | 批量转换（multipart） |
| `GET`  | `/api/task/{task_id}` | 任务详情 |
| `GET`  | `/api/tasks?limit=50` | 任务列表 |
| `DELETE` | `/api/tasks/{task_id}` | 删除任务 |
| `GET`  | `/api/download/{task_id}` | 下载（批量 zip） |
| `GET`  | `/api/download/{task_id}/{filename}` | 下载（单文件） |

## 🎨 功能清单

| 功能 | 实现位置 | 状态 |
|------|----------|------|
| 文件上传（点击） | `views/convert/Index.vue` + `el-upload` | ✅ |
| 拖拽上传 | `views/convert/Index.vue` + `el-upload drag` | ✅ |
| 文件列表 | `views/convert/Index.vue` + `el-table` | ✅ |
| 转换类型选择 | `views/convert/Index.vue` + `el-select` | ✅ |
| 进度显示（上传 / 转换） | `el-progress` + Pinia 状态 | ✅ |
| 下载结果 | `getDownloadUrl()` + `<a download>` | ✅ |
| 错误提示 | axios 拦截器 + `ElMessage` | ✅ |
| 登录（占位） | `views/login/Index.vue` | ✅ |
| 暗色模式 | `appStore.toggleTheme()` + CSS 变量 | ✅ |
| 路由守卫 | `router/index.ts` | ✅ |
| 进度轮询 | `taskStore.startPolling()` | ✅ |
| 任务列表过滤 | `views/tasks/Index.vue` | ✅ |

## 🔌 与后端集成

### 当前状态
- 前端默认指向 `http://localhost:8000/api`
- vite dev server 代理 `/api` 到后端
- 后端实现位于仓库根目录 `api/`（FastAPI）

### 路径对齐
如果后端使用不同前缀（如 `/api/v1/`），修改 `.env.development`：
```env
VITE_API_PREFIX=/api/v1
```

### 启动完整栈
```bash
# 终端 1：启动后端
cd api
./start.sh          # 或 start.bat

# 终端 2：启动前端
cd frontend
npm run dev
```

## 🛠 常见问题

### Q: 启动后页面空白
检查浏览器控制台：
1. 后端是否启动（`curl http://localhost:8000/api/v1/health`）
2. Vite 代理是否生效（控制台 Network 看 `/api/...` 请求）
3. `localStorage` 中是否有旧 token（清空重试）

### Q: TypeScript 编译报错
```bash
npm run type-check
```
最常见原因：修改了 `types/index.ts` 后未同步更新 API 签名。

### Q: 暗色模式不生效
1. 检查 `localStorage.doc_converter_theme`
2. 检查 `<html>` 元素是否有 `class="dark"`
3. Element Plus 组件由 CSS 变量驱动，需保证样式表被加载

### Q: 轮询没有停止
在 `views/tasks/Index.vue` 的 `onUnmounted` 已调用 `taskStore.stopPolling()`。如果页面异常关闭，store 会在下次 `startPolling` 时检测 `polling` 标志并避免重复启动。

## 📦 打包优化

Vite 配置中已启用：
- **手动分包**：`vue-vendor` / `element-plus` / `utils` 三个 chunk 长期缓存
- **按需引入**：`unplugin-auto-import` + `unplugin-vue-components` 自动按需注册
- **Sourcemap 关闭**：生产构建不带 sourcemap，体积更小
- **目标 ES2015**：兼容主流浏览器

进一步优化方向：
- 路由懒加载（已实现）
- Element Plus 图标按需引入（已通过自动按需插件实现）
- CDN 加速（修改 `vite.config.ts` 的 `build.rollupOptions.external`）

## 📄 许可

MIT License
