import os
import logging
from fastapi import FastAPI
from .config import settings
from .db import init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="MeshVPN Core Daemon")

# Initialize database
init_db()

# Import and include API routes
from .api import auth, nodes, clients, routing, health

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(nodes.router, prefix="/api/nodes", tags=["nodes"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(routing.router, prefix="/api/routing", tags=["routing"])
app.include_router(health.router, prefix="/api/health", tags=["health"])

@app.get("/")
async def root():
    return {"message": "MeshVPN Core Daemon"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}