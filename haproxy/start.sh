#!/bin/sh
set -e

if [ "$(echo "${ENABLE_HAPROXY:-false}" | tr '[:upper:]' '[:lower:]')" != "true" ]; then
    echo "[haproxy] ENABLE_HAPROXY is not set to true — haproxy is disabled. Exiting."
    exit 0
fi

echo "[haproxy] Starting HAProxy..."
exec haproxy -f /usr/local/etc/haproxy/haproxy.cfg -W
