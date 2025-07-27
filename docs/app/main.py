from app.api.upload import router as upload_router
from app.api.chat import router as chat_router
from app.api.vision import router as vision_router
from app.api.ocr_router import ocr_router 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
app.include_router(vision_router)
app.include_router(ocr_router, prefix="/ocr")

@app.get("/ping")
def ping():
    return {"msg": "pong"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
