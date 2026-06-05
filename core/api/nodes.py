import hmac
import datetime
import logging
import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

from config import settings
from db import (
    get_db, get_all_nodes, get_node_by_name, get_node_by_id,
    get_config, set_config, insert_node, get_next_mesh_ip,
)
from api.auth import require_auth
from pki import sign_server_cert
from mesh_config import write_wg_config

logger = logging.getLogger(__name__)
router = APIRouter()

PKI_DIR = "/data/pki"


class NodeOut(BaseModel):
    id: int
    name: str
    public_ip: str
    api_url: Optional[str] = None
    wg_pubkey: Optional[str] = None
    wg_ip: Optional[str] = None
    api_port: int
    wg_port: int
    vpn_port: int
    priority: int
    status: str
    last_seen: Optional[int] = None
    joined_at: Optional[int] = None


class JoinRequest(BaseModel):
    name: str
    public_ip: str
    api_url: Optional[str] = None   # full public URL if behind a reverse proxy
    wg_pubkey: str
    wg_port: int
    vpn_port: int
    api_port: int
    priority: int


class JoinResponse(BaseModel):
    wg_ip: str
    nodes: List[NodeOut]
    ca_cert: str
    ta_key: str
    dh_param: str
    server_cert: str
    server_key: str
    routing_config: dict
    mesh_secret: str


def _node_to_out(row) -> NodeOut:
    return NodeOut(**{k: row[k] for k in row.keys()})


@router.get("", response_model=List[NodeOut])
async def get_nodes(_user: str = Depends(require_auth)):
    return [_node_to_out(n) for n in get_all_nodes()]


@router.get("/self", response_model=NodeOut)
async def get_self(_user: str = Depends(require_auth)):
    node = get_node_by_name(settings.node.name)
    if not node:
        raise HTTPException(status_code=404, detail="Self not found in DB")
    return _node_to_out(node)


@router.get("/join-token")
async def get_join_token(_user: str = Depends(require_auth)):
    token = get_config("join_token")
    if not token:
        raise HTTPException(status_code=404, detail="No join token — is this node the leader?")
    return {"join_token": token, "join_addr": settings.node.effective_api_url}


@router.post("/join", response_model=JoinResponse)
async def join_node(
    req: JoinRequest,
    x_join_token: Optional[str] = Header(None),
):
    stored_token = get_config("join_token")
    if not stored_token:
        raise HTTPException(status_code=403, detail="This node is not a leader")

    if not x_join_token or not hmac.compare_digest(x_join_token, stored_token):
        raise HTTPException(status_code=403, detail="Invalid join token")

    existing = get_node_by_name(req.name)
    if existing:
        wg_ip = existing["wg_ip"]
        logger.info(f"Node {req.name} re-joining with existing IP {wg_ip}")
    else:
        wg_ip = get_next_mesh_ip(settings.network.mesh_subnet)
        insert_node(
            name=req.name,
            public_ip=req.public_ip,
            api_url=req.api_url,
            wg_pubkey=req.wg_pubkey,
            wg_ip=wg_ip,
            api_port=req.api_port,
            wg_port=req.wg_port,
            vpn_port=req.vpn_port,
            priority=req.priority,
            status="follower",
        )
        logger.info(f"Node {req.name} joined with IP {wg_ip}")

    try:
        ca_key_pem = open(os.path.join(PKI_DIR, "ca.key")).read()
        ca_cert_pem = open(os.path.join(PKI_DIR, "ca.crt")).read()
        ta_key = open(os.path.join(PKI_DIR, "ta.key")).read()
        dh_param = open(os.path.join(PKI_DIR, "dh.pem")).read()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"PKI not ready: {e}")

    srv_key_pem, srv_cert_pem = sign_server_cert(ca_key_pem, ca_cert_pem, req.name)

    from db import get_routing
    routing = get_routing()

    all_nodes = [_node_to_out(n) for n in get_all_nodes()]

    # Regenerate WG config so the new peer is included
    try:
        write_wg_config()
    except Exception as e:
        logger.warning(f"Could not update WG config after join: {e}")

    return JoinResponse(
        wg_ip=wg_ip,
        nodes=all_nodes,
        ca_cert=ca_cert_pem,
        ta_key=ta_key,
        dh_param=dh_param,
        server_cert=srv_cert_pem,
        server_key=srv_key_pem,
        routing_config={"mode": routing["mode"], "weights_json": routing["weights_json"]},
        mesh_secret=get_config("mesh_secret") or "",
    )


@router.post("/join-token/rotate")
async def rotate_join_token(_user: str = Depends(require_auth)):
    new_token = secrets.token_hex(32)
    set_config("join_token", new_token)
    return {
        "join_token": new_token,
        "join_addr": settings.node.effective_api_url,
    }


@router.delete("/{node_id}", status_code=204)
async def delete_node(node_id: int, _user: str = Depends(require_auth)):
    node = get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node["name"] == settings.node.name:
        raise HTTPException(status_code=400, detail="Cannot remove self")
    with get_db() as conn:
        conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
