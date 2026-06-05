FROM haproxy:2.9

COPY haproxy/haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg
COPY --chmod=755 haproxy/start.sh /start.sh

CMD ["/start.sh"]
