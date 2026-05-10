"""
main.py
-------
CyberNova Sales Intelligence Dashboard — FastAPI entry point.

Run with:
    cd dashboard
    python -m uvicorn main:app --reload --port 8000
"""

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, salesperson, sales_manager, systems_manager

app = FastAPI(
    title="CyberNova Sales Intelligence API",
    description="Secure analytics API for IIS sales log data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(salesperson.router)
app.include_router(sales_manager.router)
app.include_router(systems_manager.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "CyberNova Sales Intelligence API"}