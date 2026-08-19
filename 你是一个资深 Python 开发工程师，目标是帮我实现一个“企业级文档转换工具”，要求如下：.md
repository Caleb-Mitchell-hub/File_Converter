5. - 你是资深 Python 架构师，目标是帮我将一个企业级文档转换工具封装为 REST API 服务。
   
     前提：
     - 文档转换引擎已经完成，功能包括：
       1. Excel → PDF
       2. PDF → Excel
       3. PDF → Image
       4. Image → PDF
       5. Word → PDF
       6. PDF → Word
     - 引擎提供统一调用接口：converter.convert(source_path, target_path)
   
     任务要求：
     1. 使用 **FastAPI** 封装所有功能为 REST API。
     2. 使用 **Pydantic** 定义请求和响应模型。
     3. API 支持：
        - 文件上传（单文件 / 多文件）
        - 转换类型选择
        - 批量转换
        - 转换任务 ID
        - 转换进度查询
        - 文件下载
     4. 返回统一 JSON 响应，包含：
        - task_id
        - status（pending/running/success/failed）
        - download_url
        - 错误信息
     5. 支持 Swagger 文档（自动生成）。
     6. 支持日志记录转换过程（包含异常捕获）。
     7. 支持异步接口（async / await）。
     8. 支持企业级目录结构：
        - app/
          - api/ （路由）
          - service/ （业务逻辑）
          - models/ （Pydantic模型）
          - utils/ （日志、配置、工具函数）
          - main.py （FastAPI入口）
        - uploads/ （上传临时文件）
        - outputs/ （生成文件）
        - logs/ （日志）
     9. 提供 Dockerfile 和 docker-compose.yml，可直接部署。
     10. 提供示例调用代码（Python requests）。
     11. 每个模块都必须有文档注释，说明功能和参数。
     12. 可扩展性强，方便后续增加更多文档格式转换。
   
     输出要求：
     - 完整的项目目录结构
     - requirements.txt
     - FastAPI 完整实现代码（路由、服务、模型、工具函数）
     - Dockerfile 和 docker-compose.yml
     - 示例调用 Python 代码
     - 日志配置示例
     - Swagger 自动文档可用
   
     请生成完整可运行的企业级文档转换 REST API 服务项目。