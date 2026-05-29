import os
import asyncio
import logging
import secrets
import datetime
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from config import settings
from db import (
    init_db, get_config, set_config, get_db,
    get_node_by_name, insert_node, get_all_nodes, get_next_mesh_ip,
)
from state import NodeState, set_state
from pki import (
    generate_wg_keypair, generate_ca, sign_server_cert,
    generate_ta_key, generate_dh_params,
)
from mesh_config import (
    write_wg_config, write_ovpn_config,
    PKI_DIR, WG_DIR, OPENVPN_DIR, HAPROXY_DIR,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [core] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _ensure_dirs():
    for d in (PKI_DIR, WG_DIR, OPENVPN_DIR, HAPROXY_DIR):
        os.makedirs(d, exist_ok=True)


def _write_file(path: str, content: str, mode: int = 0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, mode)


def _read_file(path: str) -> str | None:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


def _setup_pki():
    ca_key_path = os.path.join(PKI_DIR, "ca.key")
    ca_cert_path = os.path.join(PKI_DIR, "ca.crt")
    srv_key_path = os.path.join(PKI_DIR, "server.key")
    srv_cert_path = os.path.join(PKI_DIR, "server.crt")
    ta_path = os.path.join(PKI_DIR, "ta.key")
    dh_path = os.path.join(PKI_DIR, "dh.pem")

    if not os.path.exists(ca_key_path):
        logger.info("Generating CA keypair…")
        ca_key_pem, ca_cert_pem = generate_ca()
        _write_file(ca_key_path, ca_key_pem, 0o600)
        _write_file(ca_cert_path, ca_cert_pem)
        logger.info("CA generated.")
    else:
        ca_key_pem = _read_file(ca_key_path)
        ca_cert_pem = _read_file(ca_cert_path)

    if not os.path.exists(srv_cert_path):
        logger.info("Generating server certificate…")
        srv_key_pem, srv_cert_pem = sign_server_cert(
            ca_key_pem, ca_cert_pem, settings.node.name
        )
        _write_file(srv_key_path, srv_key_pem, 0o600)
        _write_file(srv_cert_path, srv_cert_pem)
        logger.info("Server certificate generated.")

    if not os.path.exists(ta_path):
        logger.info("Generating TLS auth key…")
        _write_file(ta_path, generate_ta_key(), 0o600)

    if not os.path.exists(dh_path):
        logger.info("Generating DH parameters (2048-bit) — may take up to a minute…")
        dh_pem = generate_dh_params()
        _write_file(dh_path, dh_pem)
        logger.info("DH parameters generated.")


def _setup_wg_keypair() -> tuple[str, str]:
    privkey = get_config("wg_privkey")
    pubkey = get_config("wg_pubkey")
    if not privkey:
        logger.info("Generating WireGuard keypair…")
        privkey, pubkey = generate_wg_keypair()
        set_config("wg_privkey", privkey)
        set_config("wg_pubkey", pubkey)
        logger.info("WireGuard keypair generated.")
    return privkey, pubkey


async def _leader_startup():
    logger.info("Starting in LEADER mode…")
    set_state(NodeState.LEADER)

    _privkey, pubkey = _setup_wg_keypair()

    existing = get_node_by_name(settings.node.name)
    if not existing:
        wg_ip = get_next_mesh_ip(settings.network.mesh_subnet)
        insert_node(
            name=settings.node.name,
            public_ip=settings.node.public_ip,
            wg_pubkey=pubkey,
            wg_ip=wg_ip,
            api_port=settings.node.api_port,
            wg_port=settings.node.wg_port,
            vpn_port=settings.node.vpn_port,
            priority=settings.node.priority,
            status="leader",
        )
        logger.info(f"Leader node registered with WG IP {wg_ip}")
    else:
        logger.info(f"Existing leader record found (wg_ip={existing['wg_ip']})")

    if not get_config("join_token"):
        set_config("join_token", secrets.token_hex(32))
        logger.info("Join token generated.")

    if not get_config("mesh_secret"):
        set_config("mesh_secret", secrets.token_hex(32))

    _setup_pki()
    write_wg_config()
    write_ovpn_config()

    haproxy_cfg = (
        "global\n    log stdout format raw local0\n\n"
        "defaults\n    mode tcp\n    timeout connect 5s\n"
        "    timeout client 60s\n    timeout server 60s\n    log global\n\n"
        "frontend vpn_in\n    bind *:443\n    default_backend openvpn_local\n\n"
        "backend openvpn_local\n    server ovpn 127.0.0.1:1194 check\n"
    )
    _write_file(os.path.join(HAPROXY_DIR, "haproxy.cfg"), haproxy_cfg)

    logger.info("Leader startup complete.")


def _join_base_url(join_addr: str) -> str:
    """Return a base URL for the leader API.

    join_addr can be:
      - a full URL:    https://vpn.example.com   →  used as-is
      - host only:     192.168.1.10:8080          →  http:// prepended
    """
    if join_addr.startswith(("http://", "https://")):
        return join_addr.rstrip("/")
    return f"http://{join_addr}"


async def _join_startup():
    join_addr = settings.mesh.join_addr
    join_token = settings.mesh.join_token
    if not join_addr or not join_token:
        logger.error("join mode requires mesh.join_addr and mesh.join_token in mesh.yaml")
        raise SystemExit(1)

    base_url = _join_base_url(join_addr)
    logger.info(f"Starting in FOLLOWER mode, joining {base_url}…")
    set_state(NodeState.FOLLOWER)

    _privkey, pubkey = _setup_wg_keypair()

    body = {
        "name": settings.node.name,
        "public_ip": settings.node.public_ip,
        "wg_pubkey": pubkey,
        "wg_port": settings.node.wg_port,
        "vpn_port": settings.node.vpn_port,
        "api_port": settings.node.api_port,
        "priority": settings.node.priority,
    }

    join_url = f"{base_url}/api/nodes/join"
    response_data = None

    # Allow opting out of SSL verification for self-signed certs (not recommended).
    ssl_verify = os.environ.get("MESH_JOIN_SSL_VERIFY", "true").lower() != "false"
    async with httpx.AsyncClient(timeout=10, verify=ssl_verify) as client:
        while True:
            try:
                resp = await client.post(
                    join_url,
                    json=body,
                    headers={"X-Join-Token": join_token},
                )
                if resp.status_code == 200:
                    response_data = resp.json()
                    break
                logger.warning(f"Join rejected ({resp.status_code}): {resp.text} — retrying in 10s")
            except Exception as e:
                logger.warning(f"Cannot reach leader at {base_url}: {e} — retrying in 10s")
            await asyncio.sleep(10)

    logger.info("Join accepted. Storing received configuration…")

    _write_file(os.path.join(PKI_DIR, "ca.crt"), response_data["ca_cert"])
    _write_file(os.path.join(PKI_DIR, "ta.key"), response_data["ta_key"], 0o600)
    _write_file(os.path.join(PKI_DIR, "dh.pem"), response_data["dh_param"])
    _write_file(os.path.join(PKI_DIR, "server.crt"), response_data["server_cert"])
    _write_file(os.path.join(PKI_DIR, "server.key"), response_data["server_key"], 0o600)

    if response_data.get("mesh_secret"):
        set_config("mesh_secret", response_data["mesh_secret"])

    wg_ip = response_data["wg_ip"]
    all_nodes_data = response_data["nodes"]

    if not get_node_by_name(settings.node.name):
        insert_node(
            name=settings.node.name,
            public_ip=settings.node.public_ip,
            wg_pubkey=pubkey,
            wg_ip=wg_ip,
            api_port=settings.node.api_port,
            wg_port=settings.node.wg_port,
            vpn_port=settings.node.vpn_port,
            priority=settings.node.priority,
            status="follower",
        )

    now = int(datetime.datetime.utcnow().timestamp())
    with get_db() as conn:
        for nd in all_nodes_data:
            if nd["name"] == settings.node.name:
                continue
            exists = conn.execute(
                "SELECT id FROM nodes WHERE name = ?", (nd["name"],)
            ).fetchone()
            if not exists:
                conn.execute(
                    """INSERT INTO nodes
                       (name, public_ip, wg_pubkey, wg_ip, api_port, wg_port, vpn_port,
                        priority, status, joined_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        nd["name"], nd["public_ip"], nd["wg_pubkey"], nd["wg_ip"],
                        nd["api_port"], nd["wg_port"], nd["vpn_port"],
                        nd["priority"], nd["status"], now,
                    ),
                )

    write_wg_config()
    write_ovpn_config()

    logger.info("Follower startup complete.")


async def _health_loop():
    from db import update_node_status
    interval = settings.routing.health_interval
    while True:
        await asyncio.sleep(interval)
        try:
            update_node_status(settings.node.name, get_state().value)
        except Exception as e:
            logger.debug(f"Health loop error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_dirs()
    init_db()

    if settings.mesh.mode == "leader":
        await _leader_startup()
    elif settings.mesh.mode == "join":
        await _join_startup()
    else:
        logger.error(f"Unknown mesh mode: {settings.mesh.mode}")
        raise SystemExit(1)

    asyncio.create_task(_health_loop())
    yield


app = FastAPI(title="MeshVPN Core Daemon", lifespan=lifespan)

from api import auth, nodes, clients, routing, health, sync

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(nodes.router, prefix="/api/nodes", tags=["nodes"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(routing.router, prefix="/api/routing", tags=["routing"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(sync.router, prefix="/api/sync", tags=["sync"])


@app.get("/")
async def root():
    return {"service": "MeshVPN Core Daemon", "node": settings.node.name}


@app.get("/health")
async def basic_health():
    return {"status": "ok", "node": settings.node.name, "mode": settings.mesh.mode}
