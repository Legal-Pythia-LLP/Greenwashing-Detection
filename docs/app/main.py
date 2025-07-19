from fastapi import FastAPI
from app.api.upload import router as upload_router
from app.api.chat import router as chat_router
from app.api.validate import router as validate_router

# FastAPI 应用主入口，注册所有API路由
app = FastAPI(title="Multilingual ESG Greenwashing Analysis API", root_path="/v1")

# 注册上传、聊天、验证等API路由
app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(validate_router) 