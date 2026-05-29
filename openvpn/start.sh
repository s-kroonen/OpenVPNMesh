#!/bin/sh
set -e

CONFIG=/data/openvpn/server.conf

echo "[openvpn] Waiting for config at $CONFIG ..."
until [ -f "$CONFIG" ]; do
    sleep 3
done

echo "[openvpn] Config found. Starting OpenVPN..."
exec openvpn --config "$CONFIG"
