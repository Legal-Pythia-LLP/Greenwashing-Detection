# ESG Greenwashing Analysis API

本项目基于 FastAPI、LangChain、OpenAI/ClimateBERT 等，提供 ESG 漂绿分析自动化 API，现已实现彻底模块化，结构清晰，易于维护和扩展。

## 技术栈
- 后端: FastAPI, Uvicorn
- AI: OpenAI, ClimateBERT, LangChain, LangGraph
- 数据库: SQLite (内置), FAISS (向量存储)
- 前端: React (v2目录下)
- 工具: Pydantic, BeautifulSoup (爬虫)

## 主要功能
- ESG 报告上传与自动分析（支持 PDF）
- LangGraph 工作流与 Agent 智能推理  
- 新闻验证与漂绿指标量化
- 多模型与自定义工具扩展
- 完全分层架构设计

## 快速开始

### 环境配置
建议使用 Python 3.10+

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 数据库初始化
```bash
python -m app.init_db
```

### 启动服务
```bash
# 开发模式
uvicorn app.main:app --reload

# 生产模式
python -m app.main
```

## 项目结构

```
summer-pro/
├── app/                  # 后端核心代码
│   ├── api/              # API路由
│   ├── core/             # 业务逻辑与工具
│   ├── models/           # 数据模型
│   ├── config.py         # 配置管理
│   └── main.py           # 应用入口
├── v2/                   # 前端React应用
├── data/                 # 数据库文件
├── pdfs/                 # 示例ESG报告
├── uploads/              # 上传文件存储
├── tests/                # 单元测试
└── webscraper/           # 新闻爬虫
```

## API文档
访问本地运行的API文档:
- Swagger UI: http://localhost:8000/docs  
- Redoc: http://localhost:8000/redoc

## 环境变量配置
复制`.env.example`为`.env`并填写您的API密钥:
```ini
OPENAI_API_KEY=your_key
CLIMATEBERT_API_KEY=your_key
AZURE_ENDPOINT=your_endpoint
```

## 贡献指南
欢迎通过issue或PR贡献代码:
1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -m 'Add some feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建Pull Request

## 维护者
- [qouli-q](https://github.com/qouli-q)
