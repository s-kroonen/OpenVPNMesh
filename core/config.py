import os
from typing import Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

class NodeConfig(BaseModel):
    name: str
    public_ip: str
    wg_port: int = Field(..., ge=1, le=65535)
    vpn_port: int = Field(..., ge=1, le=65535)
    api_port: int = Field(..., ge=1, le=65535)
    ui_port: int = Field(..., ge=1, le=65535)
    priority: int = 100

class MeshConfig(BaseModel):
    mode: str = "leader"  # "leader" or "join"
    join_addr: Optional[str] = ""
    join_token: Optional[str] = ""

class NetworkConfig(BaseModel):
    client_subnet: str
    mesh_subnet: str
    allowed_lan: str

class RoutingConfig(BaseModel):
    mode: str = "weighted"  # weighted | random | fastest | failover
    weight: int = 100
    health_interval: int = 3
    failover_threshold: int = 3

class CloudflareConfig(BaseModel):
    enabled: bool = True
    api_token: Optional[str] = ""
    zone_id: Optional[str] = ""
    domain: str = "vpn.yourdomain.com"
    ttl: int = 60

class AuthConfig(BaseModel):
    admin_password: Optional[str] = ""

class MeshSettings(BaseSettings):
    node: NodeConfig
    mesh: MeshConfig
    network: NetworkConfig
    routing: RoutingConfig
    cloudflare: CloudflareConfig
    auth: AuthConfig

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Load settings from environment and config file
try:
    settings = MeshSettings()
    print("Configuration loaded successfully")
except Exception as e:
    print(f"Error loading configuration: {e}")
    raise SystemExit(1)