#!/bin/sh
# Runs automatically before nginx starts (nginx:alpine executes every script
# in /docker-entrypoint.d/ in order, then starts the container's CMD).
set -eu

API_PORT="${API_PORT:-8001}"

cat > /usr/share/nginx/html/config.js <<EOF
window.DOJO_CONFIG = { apiBaseUrl: "http://localhost:${API_PORT}" };
EOF
