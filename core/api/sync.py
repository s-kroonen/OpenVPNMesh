"""Internal sync endpoints — authenticated by mesh_secret, not JWT."""
import hmac
import logging

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

from db import get_config, set_config, get_all_nodes, get_node_by_name, update_node_status
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _check_mesh_auth(x_mesh_secret: Optional[str]):
    stored = get_config("mesh_secret")
    if not stored or not x_mesh_secret:
        raise HTTPException(status_code=403, detail="Mesh secret required")
    if not hmac.compare_digest(x_mesh_secret, stored):
        raise HTTPException(status_code=403, detail="Invalid mesh secret")


@router.get("/snapshot")
async def snapshot(x_mesh_secret: Optional[str] = Header(None)):
    _check_mesh_auth(x_mesh_secret)
    nodes = [dict(n) for n in get_all_nodes()]
    return {"nodes": nodes}


class HeartbeatIn(BaseModel):
    from_node: str
    state: str


@router.post("/heartbeat")
async def heartbeat(body: HeartbeatIn, x_mesh_secret: Optional[str] = Header(None)):
    _check_mesh_auth(x_mesh_secret)
    try:
        update_node_status(body.from_node, body.state)
    except Exception as e:
        logger.warning(f"Heartbeat update failed: {e}")
    return {"ok": True}


@router.post("/delta")
async def delta(x_mesh_secret: Optional[str] = Header(None)):
    _check_mesh_auth(x_mesh_secret)
    return {"ok": True}
