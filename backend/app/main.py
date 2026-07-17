from fastapi import FastAPI

from app.api.routes import router
from app.api.ai_routes import router as ai_router

app = FastAPI(
    title="PulseCRM AI",
    version="1.0.0",
    description="Agentic AI-powered Healthcare Relationship Intelligence Platform"
)

app.include_router(router)
app.include_router(ai_router)


@app.get("/")
def home():
    return {"message": "PulseCRM AI Backend Running"}


@app.get("/health")
def health():
    return {"status": "healthy"}