import datetime
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional

from config import settings
from db import get_all_nodes, get_node_by_name
from state import get_state
from api.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


class NodeHealthOut(BaseModel):
    node_id: int
    name: str
    status: str
    last_seen: Optional[int] = None
    wg_ok: bool = False
    api_ok: bool = True
    ping_ok: bool = False
    latency_ms: Optional[int] = None


@router.get("", response_model=NodeHealthOut)
async def get_health():
    node = get_node_by_name(settings.node.name)
    if not node:
        return NodeHealthOut(
            node_id=0, name=settings.node.name,
            status=get_state().value, api_ok=True,
        )
    return NodeHealthOut(
        node_id=node["id"],
        name=node["name"],
        status=get_state().value,
        last_seen=node["last_seen"],
        api_ok=True,
    )


@router.get("/mesh", response_model=List[NodeHealthOut])
async def get_mesh_health(_user: str = Depends(require_auth)):
    nodes = get_all_nodes()
    now = int(datetime.datetime.utcnow().timestamp())
    result = []
    for n in nodes:
        last_seen = n["last_seen"]
        stale = last_seen and (now - last_seen) > 30
        result.append(NodeHealthOut(
            node_id=n["id"],
            name=n["name"],
            status=n["status"] if not stale else "dead",
            last_seen=last_seen,
            api_ok=not stale,
        ))
    return result
