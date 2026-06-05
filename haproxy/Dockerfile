FROM haproxy:2.9

COPY haproxy/haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg
COPY haproxy/start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
