# Summer-Project
本项目为多语言 ESG 绿洗分析系统后端，基于 FastAPI、LangChain、Azure OpenAI Embedding 等。

---

## 1. 环境准备

### 1.1 创建 Python 虚拟环境

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

### 1.2 安装依赖

```powershell
pip install -r requirements.txt
```

---

## 2. 启动后端服务

```powershell
uvicorn app.main:app --reload
```

- 启动后访问 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) 查看 API 文档。

---

## 3. 目录结构说明

```
docs/
  ├── app/
  │   ├── api/             # 路由层（如 chat.py, upload.py, validate.py）
  │   ├── config.py        # 配置文件
  │   ├── main.py          # FastAPI 启动入口
  │   ├── models/          # 数据模型（如 pydantic_models.py, state.py）
  │   ├── services/        # 业务逻辑层（如 agent.py, esg_analysis.py, memory.py）
  │   └── utils/           # 工具函数（如 hashing.py, language.py, pdf_processing.py, translation.py）
  ├── data_files/          # 数据文件（如 companies.csv）
  ├── pdfs/                # PDF 文件
  ├── uploads/             # 上传文件存放目录
  ├── requirements.txt     # 依赖
  └── README.md            # 项目说明

# 根目录还有：
original version/                        # 原始版本相关文件夹
```

---

## 4. 常见问题

- **环境变量未生效**：请确保 `.env` 文件在根目录，且重启终端后再运行。
- **缺少依赖**：如遇 `ModuleNotFoundError`，请重新执行 `pip install -r requirements.txt`。
- **API Key 报错**：请检查 `.env` 文件内容和格式。

---