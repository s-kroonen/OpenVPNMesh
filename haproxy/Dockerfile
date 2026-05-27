FROM haproxy:2.9

COPY haproxy.cfg.j2 /usr/local/etc/haproxy/haproxy.cfg.j2

CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg", "-p", "/var/run/haproxy.pid"]