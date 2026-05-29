"""
Cloudflare DNS updater: keeps A records for healthy nodes.
Only the leader runs the full update; followers manage their own record only.
"""
import os
import time
import logging

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [cloudflare] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

CORE_API = os.environ.get("CORE_API", "http://core:8080")
CF_API_TOKEN = os.environ.get("CF_API_TOKEN", "")
CF_ZONE_ID = os.environ.get("CF_ZONE_ID", "")
CF_DOMAIN = os.environ.get("CF_DOMAIN", "vpn.yourdomain.com")
POLL_INTERVAL = 10


def _get_cf_records(zone_id: str, token: str) -> dict:
    try:
        resp = httpx.get(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            return {r["name"]: r for r in resp.json().get("result", [])}
    except Exception as e:
        logger.warning(f"CF API error: {e}")
    return {}


def _upsert_record(zone_id: str, token: str, name: str, ip: str, ttl: int = 60):
    try:
        existing = _get_cf_records(zone_id, token).get(name)
        if existing:
            if existing["content"] == ip:
                return
            httpx.put(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{existing['id']}",
                headers={"Authorization": f"Bearer {token}"},
                json={"type": "A", "name": name, "content": ip, "ttl": ttl},
                timeout=10,
            )
        else:
            httpx.post(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
                headers={"Authorization": f"Bearer {token}"},
                json={"type": "A", "name": name, "content": ip, "ttl": ttl},
                timeout=10,
            )
    except Exception as e:
        logger.warning(f"CF upsert error: {e}")


def _delete_record(zone_id: str, token: str, name: str):
    try:
        existing = _get_cf_records(zone_id, token).get(name)
        if existing:
            httpx.delete(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{existing['id']}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
    except Exception as e:
        logger.warning(f"CF delete error: {e}")


def main():
    logger.info("Cloudflare updater started.")

    if not CF_API_TOKEN or not CF_ZONE_ID:
        logger.info("CF_API_TOKEN or CF_ZONE_ID not set — Cloudflare updates disabled.")
        while True:
            time.sleep(60)

    while True:
        try:
            with httpx.Client(timeout=5) as client:
                mesh_resp = client.get(f"{CORE_API}/api/health/mesh", timeout=5)
                if mesh_resp.status_code == 200:
                    nodes_health = mesh_resp.json()
                    nodes_resp = client.get(f"{CORE_API}/api/nodes", timeout=5)
                    nodes = {n["name"]: n for n in (nodes_resp.json() if nodes_resp.status_code == 200 else [])}

                    for h in nodes_health:
                        name = h["name"]
                        node = nodes.get(name, {})
                        dns_name = f"{name}.{CF_DOMAIN}"
                        if h["status"] in ("leader", "follower") and node.get("public_ip"):
                            _upsert_record(CF_ZONE_ID, CF_API_TOKEN, dns_name, node["public_ip"])
                        else:
                            _delete_record(CF_ZONE_ID, CF_API_TOKEN, dns_name)

        except Exception as e:
            logger.warning(f"Updater loop error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
