from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from ..db import get_db

router = APIRouter()

class Node(BaseModel):
    id: int
    name: str
    public_ip: str
    wg_pubkey: Optional[str] = None
    wg_ip: Optional[str] = None
    api_port: int
    wg_port: int
    vpn_port: int
    priority: int
    status: str
    last_seen: Optional[int] = None
    joined_at: int

class JoinRequest(BaseModel):
    name: str
    public_ip: str
    wg_pubkey: str
    wg_port: int
    vpn_port: int
    api_port: int
    priority: int

class JoinResponse(BaseModel):
    wg_ip: str
    nodes: List[Node]
    ca_cert: str
    ta_key: str
    dh_param: str
    server_cert: str
    server_key: str
    routing_config: dict

@router.get("/nodes", response_model=List[Node])
async def get_nodes():
    # This is a placeholder - actual implementation will be added in later phases
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Nodes API not implemented yet"
    )

@router.get("/nodes/self")
async def get_self_node():
    # This is a placeholder - actual implementation will be added in later phases
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Nodes API not implemented yet"
    )

@router.post("/nodes/join", response_model=JoinResponse)
async def join_node(request: JoinRequest):
    # This is a placeholder - actual implementation will be added in later phases
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Join API not implemented yet"
    )

@router.delete("/nodes/{node_id}")
async def delete_node(node_id: int):
    # This is a placeholder - actual implementation will be added in later phases
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Nodes API not implemented yet"
    )

@router.get("/nodes/join-token")
async def get_join_token():
    # This is a placeholder - actual implementation will be added in later phases
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Join token API not implemented yet"
    )