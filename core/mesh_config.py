"""Shared helpers for rendering and writing WireGuard / OpenVPN configs.
Imported by main.py and API handlers — must NOT import from api/ or main.py."""
import os
import ipaddress
import logging

from jinja2 import Environment, FileSystemLoader

from config import settings
from db import get_config, get_node_by_name, get_all_nodes

logger = logging.getLogger(__name__)

DATA_DIR = "/data"
PKI_DIR = os.path.join(DATA_DIR, "pki")
WG_DIR = os.path.join(DATA_DIR, "wg")
OPENVPN_DIR = os.path.join(DATA_DIR, "openvpn")
HAPROXY_DIR = os.path.join(DATA_DIR, "haproxy")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
_jinja = Environment(loader=FileSystemLoader(TEMPLATES_DIR), trim_blocks=True, lstrip_blocks=True)


def _write_file(path: str, content: str, mode: int = 0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, mode)


def render_wg_config() -> str:
    self_node = get_node_by_name(settings.node.name)
    if not self_node:
        logger.warning("Cannot render WG config: self not in DB")
        return ""
    privkey = get_config("wg_privkey") or ""
    all_nodes = get_all_nodes()
    peers = [dict(n) for n in all_nodes if n["name"] != self_node["name"]]
    tmpl = _jinja.get_template("wg0.conf.j2")
    return tmpl.render(
        node={
            "wg_ip": self_node["wg_ip"],
            "wg_privkey": privkey,
            "wg_port": self_node["wg_port"],
        },
        peers=peers,
    )


def render_ovpn_server_config() -> str:
    self_node = get_node_by_name(settings.node.name)
    if not self_node:
        return ""
    net = ipaddress.ip_network(settings.network.client_subnet)
    lan = ipaddress.ip_network(settings.network.allowed_lan)
    tmpl = _jinja.get_template("server.ovpn.j2")
    return tmpl.render(
        node={"vpn_port": self_node["vpn_port"]},
        client_subnet_base=str(net.network_address),
        client_subnet_mask=str(net.netmask),
        allowed_lan_base=str(lan.network_address),
        allowed_lan_mask=str(lan.netmask),
    )


def write_wg_config():
    content = render_wg_config()
    if content:
        _write_file(os.path.join(WG_DIR, "wg0.conf"), content, 0o600)
        logger.info("WireGuard config updated.")


def write_ovpn_config():
    content = render_ovpn_server_config()
    if content:
        _write_file(os.path.join(OPENVPN_DIR, "server.conf"), content)
        logger.info("OpenVPN server config updated.")
