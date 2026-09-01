"""
FastAPI Server Entrypoint: Mounts all Routers, CORS Middleware,
Static Files Handler, DB Initializer, and Root Endpoints.
"""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.database import init_db, seed_demo_data
from app.routers import farmer, guard, clerk, admin, voice

# Initialize Database Schema & Seed Data
init_db()

app = FastAPI(
    title="Smart Storage-Aware Farmer Procurement & Offline-Resilient Supply Chain Platform",
    description="SIH PS 26032: End-to-End Procurement Platform with Real-time Capacity Admission, Social Equity Engine, AI Crop Quality Inspection, and True Offline Resilient Sync.",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(farmer.router)
app.include_router(guard.router)
app.include_router(clerk.router)
app.include_router(admin.router)
app.include_router(voice.router)

# Mount Static Assets Directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    """Serves the main Single Page Application index.html."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({
        "message": "Farmer Procurement Platform API is active. Static files will be served once built.",
        "api_docs": "/docs"
    })

@app.get("/api/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "Farmer Procurement Supply Chain Platform",
        "version": "1.0.0",
        "database": "SQLite (Supabase Compatible)",
        "offline_sync_support": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
