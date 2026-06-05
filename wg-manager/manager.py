"""
WireGuard manager: polls core API, regenerates wg0.conf, and calls wg syncconf.
Runs with host networking and NET_ADMIN capability.
"""
import os
import sys
import time
import logging
import subprocess
import hashlib

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [wg-manager] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

if os.environ.get("ENABLE_WG", "false").lower() != "true":
    logger.info("ENABLE_WG is not set to true — wg-manager is disabled. Exiting.")
    sys.exit(0)

CORE_API = os.environ.get("CORE_API", "http://127.0.0.1:8080")
WG_CONF = "/data/wg/wg0.conf"
WG_IFACE = "wg0"
POLL_INTERVAL = 3


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _wg_syncconf(conf_path: str):
    try:
        result = subprocess.run(
            ["wg", "syncconf", WG_IFACE, conf_path],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            logger.warning(f"wg syncconf failed: {result.stderr.strip()}")
        else:
            logger.info(f"wg syncconf applied {conf_path}")
    except FileNotFoundError:
        logger.debug("wg not found — skipping syncconf (dev mode)")
    except Exception as e:
        logger.warning(f"wg syncconf error: {e}")


def _read_handshakes() -> dict:
    try:
        result = subprocess.run(
            ["wg", "show", WG_IFACE, "latest-handshakes"],
            capture_output=True, text=True, timeout=5,
        )
        handshakes = {}
        for line in result.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) == 2:
                handshakes[parts[0]] = int(parts[1])
        return handshakes
    except Exception:
        return {}


def _post_handshakes(client: httpx.Client, handshakes: dict):
    if not handshakes:
        return
    try:
        client.post(f"{CORE_API}/api/health/handshakes", json=handshakes, timeout=3)
    except Exception:
        pass


def main():
    logger.info(f"WireGuard manager started. Core API: {CORE_API}")
    last_hash = ""

    while True:
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{CORE_API}/api/nodes", timeout=5)
                if resp.status_code != 200:
                    logger.debug(f"Core API returned {resp.status_code}")
                    time.sleep(POLL_INTERVAL)
                    continue

                # If core wrote a new wg0.conf, sync it
                if os.path.exists(WG_CONF):
                    conf_text = open(WG_CONF).read()
                    new_hash = _hash(conf_text)
                    if new_hash != last_hash:
                        logger.info("WireGuard config changed — syncing…")
                        _wg_syncconf(WG_CONF)
                        last_hash = new_hash

                handshakes = _read_handshakes()
                _post_handshakes(client, handshakes)

        except httpx.ConnectError:
            logger.debug("Core API not reachable yet — will retry")
        except Exception as e:
            logger.warning(f"Manager loop error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
