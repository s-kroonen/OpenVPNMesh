#!/bin/sh
set -e

if [ "$(echo "${ENABLE_OPENVPN:-false}" | tr '[:upper:]' '[:lower:]')" != "true" ]; then
    echo "[openvpn] ENABLE_OPENVPN is not set to true — openvpn is disabled. Exiting."
    exit 0
fi

CONFIG=/data/openvpn/server.conf

echo "[openvpn] Waiting for config at $CONFIG ..."
until [ -f "$CONFIG" ]; do
    sleep 3
done

echo "[openvpn] Config found. Starting OpenVPN..."
exec openvpn --config "$CONFIG"
