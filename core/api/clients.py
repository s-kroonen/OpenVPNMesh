import os
import datetime
import ipaddress
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional

from config import settings
from db import get_db, get_all_clients, get_client_by_id, get_all_nodes
from api.auth import require_auth
from pki import sign_client_cert
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)
router = APIRouter()

PKI_DIR = "/data/pki"
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
_jinja = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


class ClientOut(BaseModel):
    id: int
    name: str
    wg_pubkey: Optional[str] = None
    wg_ip: Optional[str] = None
    ovpn_ip: Optional[str] = None
    created_at: int


class CreateClientRequest(BaseModel):
    name: str


class CreateClientResponse(BaseModel):
    id: int
    name: str


def _get_next_client_ip() -> str:
    net = ipaddress.ip_network(settings.network.client_subnet)
    hosts = list(net.hosts())
    with get_db() as conn:
        used = {r["ovpn_ip"] for r in conn.execute("SELECT ovpn_ip FROM clients").fetchall() if r["ovpn_ip"]}
    for host in hosts:
        if str(host) not in used:
            return str(host)
    raise RuntimeError("No free IPs in client subnet")


@router.get("", response_model=List[ClientOut])
async def get_clients(_user: str = Depends(require_auth)):
    return [
        ClientOut(id=c["id"], name=c["name"], wg_pubkey=c["wg_pubkey"],
                  wg_ip=c["wg_ip"], ovpn_ip=c["ovpn_ip"], created_at=c["created_at"])
        for c in get_all_clients()
    ]


@router.post("", response_model=CreateClientResponse, status_code=201)
async def create_client(req: CreateClientRequest, _user: str = Depends(require_auth)):
    try:
        ca_key_pem = open(os.path.join(PKI_DIR, "ca.key")).read()
        ca_cert_pem = open(os.path.join(PKI_DIR, "ca.crt")).read()
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="PKI not ready")

    key_pem, cert_pem = sign_client_cert(ca_key_pem, ca_cert_pem, req.name)
    ovpn_ip = _get_next_client_ip()
    now = int(datetime.datetime.utcnow().timestamp())

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO clients (name, ovpn_ip, created_at, cert_pem, key_pem)
               VALUES (?, ?, ?, ?, ?)""",
            (req.name, ovpn_ip, now, cert_pem, key_pem),
        )
        client_id = cur.lastrowid

    return CreateClientResponse(id=client_id, name=req.name)


@router.get("/{client_id}/ovpn", response_class=PlainTextResponse)
async def get_client_ovpn(client_id: int, _user: str = Depends(require_auth)):
    client = get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    try:
        ca_cert = open(os.path.join(PKI_DIR, "ca.crt")).read()
        ta_key = open(os.path.join(PKI_DIR, "ta.key")).read()
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="PKI not ready")

    nodes = get_all_nodes()
    tmpl = _jinja.get_template("client.ovpn.j2")
    content = tmpl.render(
        nodes=[dict(n) for n in nodes],
        ca_cert=ca_cert,
        client_cert=client["cert_pem"],
        client_key=client["key_pem"],
        ta_key=ta_key,
    )
    return PlainTextResponse(
        content=content,
        headers={"Content-Disposition": f'attachment; filename="{client["name"]}.ovpn"'},
    )


@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: int, _user: str = Depends(require_auth)):
    client = get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    with get_db() as conn:
        conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
