# ESG Greenwashing Analysis API

本项目基于 FastAPI、LangChain、OpenAI/ClimateBERT 等，提供 ESG 漂绿分析自动化 API，现已实现彻底模块化，结构清晰，易于维护和扩展。

## 主要功能
- ESG 报告上传与自动分析（支持 PDF）
- LangGraph 工作流与 Agent 智能推理
- 新闻验证与漂绿指标量化
- 多模型与自定义工具扩展
- 完全分层：API 路由、核心业务、工具、数据模型、配置、爬虫等全部独立

## 创建 Python 虚拟环境

建议使用 Python 3.10+。
>进入项目目录
```powershell
cd docs
```
>创建虚拟环境
```powershell
python -m venv venv
```
>激活虚拟环境
```powershell
venv\Scripts\activate
```


## 安装依赖
```bash
pip install -r requirements.txt
```

## 启动服务
```bash
python -m app.main
```
或
```bash
uvicorn app.main:app --reload
```

## 目录结构
```
sp_s/
  app/
    main.py                # FastAPI 启动入口
    api/                   # 路由与接口（upload.py, chat.py）
    core/                  # 核心功能/工具（esg_analysis.py, tools.py, ...）
    models/                # Pydantic/TypedDict 数据模型
    config.py              # 配置与环境变量加载
    dependencies.py        # 依赖注入（可选）
  data_files/              # 数据文件（如 companies.csv）
  uploads/                 # 上传文件临时目录
  webscraper/              # 新闻爬虫相关
  requirements.txt
  README.md
  tests/                   # 单元测试
```

## 环境变量
请参考 `.env.example` 配置 Azure OpenAI、ClimateBERT 等密钥。

## 代码分层说明
- **app/api/**：所有 API 路由，负责参数校验和请求分发
- **app/core/**：核心业务逻辑、LangGraph/Agent、工具、向量库等
- **app/models/**：所有数据结构定义
- **app/config.py**：全局配置、环境变量、路径
- **webscraper/**：新闻爬虫，支持 BBC/CNN
- **tests/**：单元测试

## 贡献与维护
欢迎 issue、PR 和建议！