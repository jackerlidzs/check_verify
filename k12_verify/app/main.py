"""
FastAPI Main Application
"""
import sys
import asyncio

# Fix Windows event loop for Playwright subprocess support
# MUST be set BEFORE any other imports
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from .api.routes import router as api_router
from .db.database import init_db

# Create FastAPI app
app = FastAPI(
    title="K12 Verify",
    description="SheerID Teacher Verification Tool",
    version="1.0.0"
)

# Paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include API routes
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve main Web UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    print("[*] K12 Verify starting up...")
    init_db()
    print("[OK] Ready at http://localhost:8000")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}
