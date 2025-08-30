from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gw_api.api import (
    upload_router,
    chat_router,
    wikirate_router,
    report_router,
    dashboard_router,
    language,
)
from gw_api.db import init_db

app = FastAPI(title="ESG Greenwashing Analysis API")

# Initialize database tables
init_db()


@app.get("/")
async def root():
    return {"message": "ESG API is running", "status": "ok"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/v2")
app.include_router(chat_router, prefix="/v2")
app.include_router(wikirate_router, prefix="/v2")
app.include_router(report_router, prefix="/v2")
app.include_router(dashboard_router, prefix="/v2")
app.include_router(language.router, prefix="/v2")
