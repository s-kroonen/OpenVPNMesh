"""
Route manager: polls core API and manages ip route entries for mesh peers.
Runs with host networking and NET_ADMIN capability.
"""
import os
import sys
import time
import logging
import subprocess

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [router] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

if os.environ.get("ENABLE_ROUTER", "false").lower() != "true":
    logger.info("ENABLE_ROUTER is not set to true — router is disabled. Exiting.")
    sys.exit(0)

CORE_API = os.environ.get("CORE_API", "http://127.0.0.1:8080")
POLL_INTERVAL = 3


def _ip_route_add(dest: str, via_iface: str = "wg0"):
    try:
        subprocess.run(
            ["ip", "route", "add", dest, "dev", via_iface],
            capture_output=True, timeout=5,
        )
    except FileNotFoundError:
        logger.debug("ip command not found — skipping (dev mode)")
    except Exception as e:
        logger.debug(f"ip route add error: {e}")


def _ip_route_del(dest: str):
    try:
        subprocess.run(
            ["ip", "route", "del", dest],
            capture_output=True, timeout=5,
        )
    except Exception:
        pass


def main():
    logger.info(f"Router started. Core API: {CORE_API}")
    known_routes: set = set()

    while True:
        try:
            with httpx.Client(timeout=5) as client:
                nodes_resp = client.get(f"{CORE_API}/api/nodes", timeout=5)
                health_resp = client.get(f"{CORE_API}/api/health/mesh", timeout=5)

                if nodes_resp.status_code == 200 and health_resp.status_code == 200:
                    nodes = {n["name"]: n for n in nodes_resp.json()}
                    health = {h["name"]: h for h in health_resp.json()}

                    desired_routes = set()
                    for name, node in nodes.items():
                        h = health.get(name, {})
                        if h.get("status") not in ("dead", "isolated") and node.get("wg_ip"):
                            desired_routes.add(node["wg_ip"] + "/32")

                    for route in desired_routes - known_routes:
                        logger.info(f"Adding route {route}")
                        _ip_route_add(route)

                    for route in known_routes - desired_routes:
                        logger.info(f"Removing route {route}")
                        _ip_route_del(route)

                    known_routes = desired_routes

        except httpx.ConnectError:
            logger.debug("Core API not reachable — will retry")
        except Exception as e:
            logger.warning(f"Router loop error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
