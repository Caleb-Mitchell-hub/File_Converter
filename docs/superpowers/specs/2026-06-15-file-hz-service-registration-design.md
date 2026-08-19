# File_HZ 服务注册接入 Serviced-MP —— 设计文档

> 日期：2026-06-15
> 状态：已批准，待实现

## 一、目标

让现有 `File_HZ` 文档转换服务（FastAPI 后端 :8000 + Vite 前端 :5213）能被 `Serviced-MP` 管理平台自动发现、监控、拉取运行时状态。

参考规范：`E:\WorkSpace\Project\Serviced_MP\API文档-服务注册规范.md`（"服务注册与监控接口文档"）。

## 二、范围

**做**：
1. 在 FastAPI 后端新增 `GET /info` 端点，返回规范第四节规定的 JSON
2. 在项目根目录创建 `serviced.yaml`，描述服务元数据供管理平台扫描

**不做**：
- 不实现"启动时主动向管理平台 POST 注册"（方式 B 主动注册）—— 当前是单实例、规范推荐方式 A（文件扫描）
- 不做周期性心跳上报（管理平台主动拉 `/info` 已足够）
- 不修改任何业务逻辑（转换器、任务管理器、API 路由、UI）

## 三、选型

| 决策 | 选择 | 原因 |
|---|---|---|
| 注册方式 | 方式 A（`serviced.yaml` 扫描） | 规范 ⭐⭐⭐ 推荐；解耦；服务不需要知道管理平台地址/Token |
| `/info` 状态语义 | 进程存活即可 | 简化；错误情况由日志/请求透出 |
| 暴露的 URL | 完整：后端根、Swagger、API、前端 | 运维一眼看到所有入口 |
| `serviced.yaml` 位置 | 项目根 `E:\WorkSpace\Project\File_HZ\serviced.yaml` | 管理平台扫描根目录即项目根，前后端都在里面 |
| 服务 `id` / `name` | `file-hz` / `File_HZ 文档转换服务` | 与项目目录名一致 |
| 路由挂载 | `/info` 挂在 FastAPI 根路径（不带 `/api/v1` 前缀） | 符合规范第四节的字面要求 |

## 四、架构

### 4.1 文件改动

```
File_HZ\
├── serviced.yaml                ← 新增：服务元数据
└── api\
    └── app\
        ├── main.py              ← 改：create_app() 注册 info_router
        └── api\routes\
            └── info.py          ← 新增：InfoRoute 路由
```

不动的部分：`doc_converter/`、`frontend/`、`api/app/api/routes/convert.py`、`api/app/api/routes/tasks.py`、`api/app/api/routes/health.py`、`api/app/service/*`、`api/app/models/*`、`api/app/config.py`。

### 4.2 数据流

```
[管理平台] -- 扫描根目录 --> 找到 serviced.yaml
[管理平台] -- 解析 yaml  --> 读取 name/ports/urls/health_url
[管理平台] -- GET <health_url> --> [File_HZ FastAPI /info]
[FastAPI /info] -- 查 psutil/os.getpid --> 返回 {status, pid, urls}
```

调用频率由管理平台决定（文档第六节"完整接入检查清单"说"默认 30s 一个扫描周期"，本服务不实现轮询）。

### 4.3 组件职责

| 组件 | 职责 | 依赖 |
|---|---|---|
| `InfoRoute` | 实现 `GET /info`，返回规范 JSON | `os` (pid) |
| `serviced.yaml` | 静态元数据 | 无 |
| `api/app/main.py` 改动 | 在 `create_app()` 内 `app.include_router(info_router)` | `InfoRoute` |

## 五、详细设计

### 5.1 `GET /info` 响应

```json
{
  "status": "running",
  "pid": 12345,
  "urls": [
    { "name": "后端根地址",   "url": "http://localhost:8000" },
    { "name": "Swagger 文档", "url": "http://localhost:8000/docs" },
    { "name": "REST API",     "url": "http://localhost:8000/api/v1" },
    { "name": "前端 Web 界面", "url": "http://localhost:5213" }
  ]
}
```

字段对应规范 4.2 节：
- `status`：固定 `"running"`（不探测依赖）
- `pid`：`os.getpid()` 当前进程
- `urls`：4 项，写死（端口由 `config.py` 的 settings 控制；为简单起见，URL 列表直接常量，不动态从 settings 拼）

### 5.2 `InfoRoute` 实现要点

```python
# api/app/api/routes/info.py
import os
from fastapi import APIRouter

router = APIRouter()

@router.get("/info", include_in_schema=False)
def get_info() -> dict:
    return {
        "status": "running",
        "pid": os.getpid(),
        "urls": [
            {"name": "后端根地址",   "url": "http://localhost:8000"},
            {"name": "Swagger 文档", "url": "http://localhost:8000/docs"},
            {"name": "REST API",     "url": "http://localhost:8000/api/v1"},
            {"name": "前端 Web 界面", "url": "http://localhost:5213"},
        ],
    }
```

- `include_in_schema=False` 不让 `/info` 出现在 `/docs` 干扰 OpenAPI 文档
- **永远返回 HTTP 200**（即使内部异常也 `return {"status": "error", ...}`），让管理平台区分"端点不可达"和"端点可达但服务异常"

### 5.3 挂载位置

```python
# api/app/main.py create_app() 内
from app.api.routes.info import router as info_router
app.include_router(info_router)  # 不带 prefix，路径 = /info
```

挂在 `create_app()` 末尾、`api_router` 注册之前或之后均可（无路径冲突）。

### 5.4 `serviced.yaml` 完整内容

```yaml
# 服务注册元数据（Serviced-MP 管理平台读取）
# 规范：E:\WorkSpace\Project\Serviced_MP\API文档-服务注册规范.md

name: "File_HZ 文档转换服务"
type: exe

description: |
  企业级文档转换平台。
  支持 Excel / Word / PDF / 图片 互转、OCR 识别。
  后端: FastAPI + uvicorn (port 8000)
  前端: Vue 3 + Vite (port 5213)

# 启动入口（按需），相对项目根
entry: api/scripts/run_dev.bat
workdir: .

# 不需要：args、env（启动脚本里已含）

ports:
  - number: 8000
    protocol: tcp
    listen_addr: 0.0.0.0
    note: FastAPI 后端 (uvicorn)
  - number: 5213
    protocol: tcp
    listen_addr: 0.0.0.0
    note: Vite 前端开发服务器

# 供运维人员直接打开
urls:
  - name: 前端 Web 界面
    url: http://localhost:5213
  - name: 后端根地址
    url: http://localhost:8000
  - name: Swagger 文档
    url: http://localhost:8000/docs

# 供程序调用的 API 入口
api_urls:
  - name: REST API v1
    url: http://localhost:8000/api/v1

# 健康检查端点：管理平台周期性 GET 此地址
health_url: http://localhost:8000/info
```

字段映射规范 2.2 节：
- `name` / `type` / `description`：必填 + 描述
- `entry` / `workdir`：用于管理平台"启动服务"功能
- `ports`：运维看到端口可一键 telnet/curl 测活
- `urls` / `api_urls`：UI 入口
- `health_url`：关键 —— 指向 `/info`

**不填的字段**（按规范是可选）：
- `args`、`env`：项目内已有启动脚本，无需重复声明
- `configs`：管理平台会自动发现
- `credentials`：无默认账户（用户体系在登录模块内）
- `system`：`type=exe` 时不适用

## 六、错误处理

| 场景 | 行为 |
|---|---|
| `/info` 内部异常（如 `os.getpid()` 不存在） | `try/except` 包裹，返回 `{"status": "error", "pid": null, "urls": []}` + HTTP 200 |
| `serviced.yaml` 不合法 | **不处理** —— YAML 错误在管理平台一侧校验，我们只负责文件存在且格式正确 |
| 端口被占用 | **不处理** —— 这是部署问题，不在服务注册范围 |
| 管理平台不可达 | **不处理** —— 服务是单向声明的（方式 A） |

## 七、测试

### 7.1 单元测试

- `tests/test_info_route.py`（新建）：
  - `GET /info` → 200
  - body 是 JSON，字段齐全：`status`（字符串）、`pid`（整数 > 0）、`urls`（数组，len ≥ 4）
  - 每个 url 元素包含 `name` 和 `url` 字段

### 7.2 集成 / 手工验证

1. 启动后端 `uvicorn app.main:app --port 8000`
2. `curl http://127.0.0.1:8000/info` → 期望返回规范 4.2 节 JSON
3. `curl http://127.0.0.1:8000/docs` → 期望 Swagger 可见且不包含 `/info`
4. 检查 `E:\WorkSpace\Project\File_HZ\serviced.yaml` 存在，YAML 合法（`python -c "import yaml; yaml.safe_load(open(r'E:\WorkSpace\Project\File_HZ\serviced.yaml'))"`）
5. 启动前端 `npm run dev`，`curl http://127.0.0.1:5213` → 期望 200，确认 ports 都活了

## 八、风险与注意

| 风险 | 缓解 |
|---|---|
| `pid` 在 uvicorn `--workers>1` 时返回 worker 进程 ID，不是 master | 文档说明：本服务是单 worker / 单进程（`--workers` 默认 1）。若未来要扩多 worker，再切换为 `parent_pid` |
| 端口写死在 `info.py` 里 | 当前 settings 没暴露 frontend port；写死简化代码。后续要支持"生产环境域名"再扩 |
| `serviced.yaml` 与 `vite.config.ts` 端口不一致（如 5213 改了） | 文档说明：改端口时同步两处。后续可考虑让 `info.py` 从 settings 读 backend port |
| 规范 `/info` 与现有 `/api/v1` 前缀冲突 | 我们**只在根路径挂 `/info`**，不重复挂 `/api/v1/info` |
| `/info` 不进 OpenAPI 文档 | 用 `include_in_schema=False` 避免污染 `/docs` |

## 九、不在本次范围（未来可能）

1. 方式 B（HTTP API 主动注册）—— 适用于多实例动态场景
2. `/info` 增加 LibreOffice / Office 健康探测
3. 周期性心跳上报
4. `info.py` 从 `settings` 读端口（而不是写死）
5. 支持多 worker 时返回 master pid
