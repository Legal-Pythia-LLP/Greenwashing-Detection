from app.api.upload import router as upload_router
from app.api.chat import router as chat_router
from app.api.ocr_router import router as ocr_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload_router, chat_router, wikirate_router
from app.api.inspector import router as inspector_router
from app.api.analysis_router import router as analysis_router

app = FastAPI(title="ESG Greenwashing Analysis API", root_path="/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(wikirate_router)
app.include_router(ocr_router)
app.include_router(inspector_router)
app.include_router(analysis_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 


