import datetime
import json
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from db import get_db, get_routing
from api.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


class RoutingConfig(BaseModel):
    mode: str = "weighted"
    weight: int = 100
    health_interval: int = 3
    failover_threshold: int = 3


@router.get("", response_model=RoutingConfig)
async def get_routing_config(_user: str = Depends(require_auth)):
    row = get_routing()
    weights = json.loads(row.get("weights_json") or "{}")
    return RoutingConfig(
        mode=row.get("mode", "weighted"),
        weight=weights.get("default", 100),
    )


@router.put("", response_model=RoutingConfig)
async def update_routing(config: RoutingConfig, _user: str = Depends(require_auth)):
    now = int(datetime.datetime.utcnow().timestamp())
    weights_json = json.dumps({"default": config.weight})
    with get_db() as conn:
        conn.execute("DELETE FROM routing_rules")
        conn.execute(
            "INSERT INTO routing_rules (mode, weights_json, updated_at) VALUES (?, ?, ?)",
            (config.mode, weights_json, now),
        )
    return config
