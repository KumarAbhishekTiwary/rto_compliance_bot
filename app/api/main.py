# CRITICAL: configure OpenAI SSL/proxy before anything else
from app.agents import openai_client  # noqa: F401

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import compliance, chatbot, webhooks, chat
from app.api.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="RTO Compliance Bot",
    description="Automated Return-to-Office compliance tracking with AI agents",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compliance.router, prefix="/api/v1", tags=["compliance"])
app.include_router(chatbot.router,    prefix="/api/v1", tags=["chatbot"])
app.include_router(webhooks.router,   prefix="/api/v1", tags=["webhooks"])
app.include_router(chat.router,       prefix="/api/v1", tags=["chat"])


@app.get("/")
def root():
    return {
        "service": "RTO Compliance Bot",
        "docs": "/docs",
        "chat_ui": "/api/v1/chat",
    }
