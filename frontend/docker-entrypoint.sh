#!/bin/sh
set -e

# Write runtime config that the SPA reads via window.__API_URL__.
# API_URL empty (default) → SPA uses relative /api/* paths (nginx proxies to core).
# API_URL set            → SPA hits that absolute origin directly.
cat > /usr/share/nginx/html/config.js <<EOF
window.__API_URL__ = "${API_URL:-}";
EOF

exec nginx -g 'daemon off;'
