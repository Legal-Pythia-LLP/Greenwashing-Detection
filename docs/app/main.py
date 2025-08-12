from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload_router, chat_router, wikirate_router

app = FastAPI(title="ESG Greenwashing Analysis API", root_path="/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(wikirate_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 