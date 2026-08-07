#!/bin/sh
set -e

if [ "$(echo "${ENABLE_OPENVPN:-false}" | tr '[:upper:]' '[:lower:]')" != "true" ]; then
    echo "[openvpn] ENABLE_OPENVPN is not set to true — openvpn is disabled. Exiting."
    exit 0
fi

CONFIG=/data/openvpn/server.conf
CLIENT_SUBNET="${MESH_CLIENT_SUBNET:-10.8.0.0/24}"

echo "[openvpn] Waiting for config at $CONFIG ..."
until [ -f "$CONFIG" ]; do
    sleep 3
done

# Enable IP forwarding and NAT client traffic out through the container's
# egress interface (eth0 on the docker bridge). Without this, VPN clients get
# an address in ${CLIENT_SUBNET} but their traffic has no return path.
echo "[openvpn] Enabling IPv4 forwarding..."
if [ -w /proc/sys/net/ipv4/ip_forward ]; then
    echo 1 > /proc/sys/net/ipv4/ip_forward
else
    echo "[openvpn] WARN: cannot enable ip_forward — client traffic may not route"
fi

echo "[openvpn] Adding MASQUERADE for ${CLIENT_SUBNET} out eth0..."
iptables -t nat -C POSTROUTING -s "${CLIENT_SUBNET}" -o eth0 -j MASQUERADE 2>/dev/null \
    || iptables -t nat -A POSTROUTING -s "${CLIENT_SUBNET}" -o eth0 -j MASQUERADE

echo "[openvpn] Config found. Starting OpenVPN..."
exec openvpn --config "$CONFIG"
