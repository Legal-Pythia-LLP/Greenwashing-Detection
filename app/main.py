from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload_router, chat_router, wikirate_router, report_router, dashboard_router,language
from app.db import init_db

app = FastAPI(title="ESG Greenwashing Analysis API")

# Initialize database tables
init_db()

@app.get("/")
async def root():
    return {"message": "ESG API is running", "status": "ok"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/v2")
app.include_router(chat_router, prefix="/v2")
app.include_router(wikirate_router)
app.include_router(report_router, prefix="/v2")
app.include_router(dashboard_router)
app.include_router(language.router, prefix="/v2")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
