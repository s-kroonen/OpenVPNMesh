import os
import logging
import datetime
import secrets
import subprocess
import ipaddress
from fastapi import FastAPI
from .config import settings
from .db import init_db, get_db

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

# Data directory paths
DATA_DIR = "/data"
PKI_DIR = os.path.join(DATA_DIR, "pki")
WG_DIR = os.path.join(DATA_DIR, "wg")
OPENVPN_DIR = os.path.join(DATA_DIR, "openvpn")

# Ensure data directories exist
os.makedirs(PKI_DIR, exist_ok=True)
os.makedirs(WG_DIR, exist_ok=True)
os.makedirs(OPENVPN_DIR, exist_ok=True)

def get_first_ip_in_subnet(subnet):
    """Get the first IP address in a subnet."""
    network = ipaddress.ip_network(subnet)
    return str(network.network_address + 1)

def initialize_leader():
    """Initialize the leader node."""
    logger.info("Initializing leader node...")

    try:
        with get_db() as conn:
            # Check if this node is already in the database (restart case)
            cursor = conn.execute("SELECT * FROM nodes WHERE name = ?", (settings.node.name,))
            existing_node = cursor.fetchone()

            if existing_node:
                logger.info("Node already exists in database (restart case)")
                # For now, we'll just log that it exists
                wg_ip = existing_node['wg_ip']
            else:
                logger.info("Creating new leader node")
                # For now, we'll just generate a mock keypair
                # In a real implementation, we'd call generate_wireguard_keypair()
                wg_pubkey = "mock_public_key_for_now"
                wg_ip = get_first_ip_in_subnet(settings.network.mesh_subnet)

                # Insert self into nodes table
                conn.execute("""
                    INSERT INTO nodes (name, public_ip, wg_pubkey, wg_ip, api_port, wg_port, vpn_port, priority, status, joined_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    settings.node.name,
                    settings.node.public_ip,
                    wg_pubkey,
                    wg_ip,
                    settings.node.api_port,
                    settings.node.wg_port,
                    settings.node.vpn_port,
                    settings.node.priority,
                    "leader",
                    int(datetime.datetime.utcnow().timestamp())
                ))

            # Generate join token
            join_token = secrets.token_hex(32)
            conn.execute("""
                INSERT OR REPLACE INTO mesh_config (key, value, updated_at)
                VALUES ('join_token', ?, ?)
            """, (join_token, int(datetime.datetime.utcnow().timestamp())))

            logger.info("Leader node initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing leader node: {e}")
        raise

# Check if we're in leader mode and initialize accordingly
if settings.mesh.mode == "leader":
    initialize_leader()

@app.get("/")
async def root():
    return {"message": "MeshVPN Core Daemon"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}