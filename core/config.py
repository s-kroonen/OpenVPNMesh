"""
Configuration loader — env vars take priority, mesh.yaml is the fallback.

ENV-VAR mode (Portainer / no file mount):
  Set MESH_NODE_NAME + MESH_PUBLIC_IP and every other MESH_* var you need.
  The YAML file is not read at all.

FILE mode (local dev):
  Leave MESH_NODE_NAME unset. Mount mesh.yaml at /etc/meshvpn/mesh.yaml
  (or point MESH_CONFIG env var at a different path).
  CF_API_TOKEN and ADMIN_PASSWORD env vars still override the file values.
"""
import os
import sys
from typing import Optional
from pydantic import BaseModel, Field


class NodeConfig(BaseModel):
    name: str
    public_ip: str
    wg_port: int = Field(default=51820, ge=1, le=65535)
    vpn_port: int = Field(default=443, ge=1, le=65535)
    api_port: int = Field(default=8080, ge=1, le=65535)
    ui_port: int = Field(default=3000, ge=1, le=65535)
    priority: int = 100


class MeshConfig(BaseModel):
    mode: str = "leader"
    join_addr: Optional[str] = ""
    join_token: Optional[str] = ""


class NetworkConfig(BaseModel):
    client_subnet: str = "10.8.0.0/24"
    mesh_subnet: str = "10.99.0.0/24"
    allowed_lan: str = "192.168.100.0/24"


class RoutingConfig(BaseModel):
    mode: str = "weighted"
    weight: int = 100
    health_interval: int = 3
    failover_threshold: int = 3


class CloudflareConfig(BaseModel):
    enabled: bool = False
    api_token: Optional[str] = ""
    zone_id: Optional[str] = ""
    domain: str = "vpn.yourdomain.com"
    ttl: int = 60


class AuthConfig(BaseModel):
    admin_password: Optional[str] = "admin"


class MeshSettings(BaseModel):
    node: NodeConfig
    mesh: MeshConfig = MeshConfig()
    network: NetworkConfig = NetworkConfig()
    routing: RoutingConfig = RoutingConfig()
    cloudflare: CloudflareConfig = CloudflareConfig()
    auth: AuthConfig = AuthConfig()


def _from_env() -> dict:
    """Build the full config dict from MESH_* environment variables."""
    e = os.environ.get
    return {
        "node": {
            "name":       os.environ["MESH_NODE_NAME"],
            "public_ip":  os.environ["MESH_PUBLIC_IP"],
            "wg_port":    int(e("MESH_WG_PORT",  "51820")),
            "vpn_port":   int(e("MESH_VPN_PORT", "443")),
            "api_port":   int(e("MESH_API_PORT", "8080")),
            "ui_port":    int(e("MESH_UI_PORT",  "3000")),
            "priority":   int(e("MESH_PRIORITY", "100")),
        },
        "mesh": {
            "mode":       e("MESH_MODE",       "leader"),
            "join_addr":  e("MESH_JOIN_ADDR",  ""),
            "join_token": e("MESH_JOIN_TOKEN", ""),
        },
        "network": {
            "client_subnet": e("MESH_CLIENT_SUBNET", "10.8.0.0/24"),
            "mesh_subnet":   e("MESH_SUBNET",         "10.99.0.0/24"),
            "allowed_lan":   e("MESH_ALLOWED_LAN",    "192.168.100.0/24"),
        },
        "routing": {
            "mode":                e("MESH_ROUTING_MODE",        "weighted"),
            "weight":         int(e("MESH_ROUTING_WEIGHT",       "100")),
            "health_interval": int(e("MESH_HEALTH_INTERVAL",     "3")),
            "failover_threshold": int(e("MESH_FAILOVER_THRESHOLD","3")),
        },
        "cloudflare": {
            "enabled":   e("CF_ENABLED", "false").lower() == "true",
            "api_token": e("CF_API_TOKEN", ""),
            "zone_id":   e("CF_ZONE_ID",   ""),
            "domain":    e("CF_DOMAIN",    "vpn.yourdomain.com"),
            "ttl":   int(e("CF_TTL",       "60")),
        },
        "auth": {
            "admin_password": e("ADMIN_PASSWORD", "admin"),
        },
    }


def _from_yaml(path: str) -> dict:
    import yaml  # lazy import — not needed in env-var mode
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}
    # Allow env var overrides on top of file values
    if os.environ.get("CF_API_TOKEN"):
        raw.setdefault("cloudflare", {})["api_token"] = os.environ["CF_API_TOKEN"]
    if os.environ.get("ADMIN_PASSWORD"):
        raw.setdefault("auth", {})["admin_password"] = os.environ["ADMIN_PASSWORD"]
    return raw


YAML_PATH = os.environ.get("MESH_CONFIG", "/etc/meshvpn/mesh.yaml")

try:
    # Env-var mode: both required keys present → no file needed
    if "MESH_NODE_NAME" in os.environ and "MESH_PUBLIC_IP" in os.environ:
        _raw = _from_env()
        print("[config] Using environment-variable configuration.")
    else:
        # File mode
        if not os.path.exists(YAML_PATH):
            print(
                f"ERROR: Config file not found at {YAML_PATH} and "
                "MESH_NODE_NAME / MESH_PUBLIC_IP are not set.\n"
                "Either mount a mesh.yaml file or supply MESH_NODE_NAME + MESH_PUBLIC_IP env vars.",
                file=sys.stderr,
            )
            sys.exit(1)
        _raw = _from_yaml(YAML_PATH)
        print(f"[config] Using file configuration: {YAML_PATH}")

    settings = MeshSettings(**_raw)

except KeyError as e:
    print(f"ERROR: Required environment variable missing: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Failed to load configuration: {e}", file=sys.stderr)
    sys.exit(1)
