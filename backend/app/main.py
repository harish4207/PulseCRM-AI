from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai_routes import router as ai_router
from app.api.routes import router

app = FastAPI(
    title="PulseCRM AI",
    version="1.0.0",
    description="Agentic AI-powered Healthcare Relationship Intelligence Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ai_router)


@app.get("/")
def home():
    return {"message": "PulseCRM AI Backend Running"}


@app.get("/health")
def health():
    return {"status": "healthy"}