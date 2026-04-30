# backend/main.py
# Orchaid — FastAPI Backend
# NVIDIA NIM + Gemini 2.5 Pro + Google Cloud + FDA OpenData
#
# Deployment: Google Cloud Run
# Frontend: Next.js on Vercel → points NEXT_PUBLIC_API_URL to this service
#
# Run locally:
#   uvicorn main:app --reload --port 8000

from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from api.actions import router as actions_router
from api.gchat import router as gchat_router
from api.fda import router as fda_router
from api.telemetry import router as telemetry_router


app = FastAPI(
    title="Orchaid API",
    description="Physical AI backend for grocery supply chain intelligence. "
                "Built on NVIDIA NIM, Gemini 2.5 Pro via Vertex AI, and Google Cloud.",
    version="1.0.0",
)

# CORS — allow requests from Vercel frontend and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
        # Add your specific Vercel domain once deployed
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(chat_router,      prefix="/chat",      tags=["Agent Chat"])
app.include_router(actions_router,   prefix="/actions",   tags=["Physical AI Actions"])
app.include_router(gchat_router,     prefix="/gchat",     tags=["Google Chat"])
app.include_router(fda_router,       prefix="/fda",       tags=["FDA OpenData"])
app.include_router(telemetry_router, prefix="/telemetry", tags=["Warehouse Telemetry"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Orchaid API",
        "version": "1.0.0",
        "stack": {
            "agents": "NVIDIA NIM (Nemotron 70B + Llama 8B)",
            "orchestrator": "Gemini 2.5 Pro via Vertex AI",
            "data": "Google Cloud BigQuery",
            "documents": "Google Cloud Document AI",
            "notifications": "Google Chat Webhook",
            "compliance": "FDA OpenFDA API",
        },
        "physical_ai_loops": [
            "Loop 1: Equipment Agent → Google Chat Dispatch",
            "Loop 2: Safety Agent → WMS Quarantine",
            "Loop 3: Forecasting Agent → POS Markdown",
        ],
        "status": "online",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
