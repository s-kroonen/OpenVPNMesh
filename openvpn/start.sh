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
# egress interface. Without this, VPN clients get an address in ${CLIENT_SUBNET}
# but their traffic has no return path.
echo "[openvpn] Enabling IPv4 forwarding..."
if [ -w /proc/sys/net/ipv4/ip_forward ]; then
    echo 1 > /proc/sys/net/ipv4/ip_forward
    echo "[openvpn]   ip_forward=$(cat /proc/sys/net/ipv4/ip_forward)"
else
    echo "[openvpn] WARN: cannot enable ip_forward — client traffic will not route"
fi

# Auto-detect egress interface from the default route rather than hardcoding
# eth0 — Docker sometimes names interfaces differently (eth0, ens3, etc.).
EGRESS_IFACE=$(ip route show default 2>/dev/null | awk '/default/ {print $5; exit}')
EGRESS_IFACE=${EGRESS_IFACE:-eth0}
echo "[openvpn] Egress interface: ${EGRESS_IFACE}"

echo "[openvpn] Installing NAT + FORWARD rules for ${CLIENT_SUBNET}..."
iptables -t nat -C POSTROUTING -s "${CLIENT_SUBNET}" -o "${EGRESS_IFACE}" -j MASQUERADE 2>/dev/null \
    || iptables -t nat -A POSTROUTING -s "${CLIENT_SUBNET}" -o "${EGRESS_IFACE}" -j MASQUERADE

# Some images/kernels start the FORWARD policy at DROP. Explicitly allow the
# tun0 ↔ egress path (idempotent — -C first, only append if missing).
iptables -C FORWARD -i tun0 -o "${EGRESS_IFACE}" -j ACCEPT 2>/dev/null \
    || iptables -A FORWARD -i tun0 -o "${EGRESS_IFACE}" -j ACCEPT
iptables -C FORWARD -i "${EGRESS_IFACE}" -o tun0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null \
    || iptables -A FORWARD -i "${EGRESS_IFACE}" -o tun0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

echo "[openvpn] iptables NAT table:"
iptables -t nat -L POSTROUTING -n -v --line-numbers | sed 's/^/[openvpn]   /'

echo "[openvpn] Config found. Starting OpenVPN..."
exec openvpn --config "$CONFIG"
