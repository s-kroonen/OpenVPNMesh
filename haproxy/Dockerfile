FROM haproxy:2.9

COPY haproxy/haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg

CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg", "-W", "-p", "/var/run/haproxy.pid"]
