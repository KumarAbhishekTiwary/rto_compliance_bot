"""FastAPI entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.routers import compliance, chatbot, webhooks, chat
from app.api.scheduler import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()

app = FastAPI(
    title="RTO Compliance Bot API",
    description="Multi-agent RTO compliance monitoring system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compliance.router, prefix="/api/v1", tags=["compliance"])
app.include_router(chatbot.router, prefix="/api/v1", tags=["chatbot"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["webhooks"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])


@app.get("/")
def root():
    return {"service": "RTO Compliance Bot", "status": "running", "version": "1.0.0"}

@app.get("/api/v1/health")
def health():
    return {"status": "healthy"}
