from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai_routes import router as ai_router
from app.api.routes import router

app = FastAPI(
    title="PulseCRM AI",
    version="1.0.0",
    description="Agentic AI-powered Healthcare Relationship Intelligence Platform",
)

import os

# Configure CORS origins:
# - Always allow local dev origins
# - Optionally append production frontend origin(s) from the environment variable FRONTEND_ORIGINS
#   (comma-separated list). Do NOT use '*' in production.
allow_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_frontend_env = os.getenv("FRONTEND_ORIGINS", "") or os.getenv("FRONTEND_PROD_ORIGIN", "")
if _frontend_env:
    for o in [p.strip() for p in _frontend_env.split(",") if p.strip()]:
        if o not in allow_origins:
            allow_origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
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