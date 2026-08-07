FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    openvpn \
    iproute2 \
    iptables \
    iputils-ping \
    curl \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

COPY openvpn/start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
