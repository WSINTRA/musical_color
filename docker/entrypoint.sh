#!/bin/sh
set -eu

PORT="${PORT:-3001}"
HEALTH_URL="http://127.0.0.1:${PORT}/api/health"

echo "starting backend on 0.0.0.0:${PORT} (version=${APP_VERSION:-dev})"
/app/backend &
BACKEND_PID=$!

i=0
until curl -fsS "$HEALTH_URL" >/dev/null 2>&1; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "backend exited before becoming healthy" >&2
    exit 1
  fi
  i=$((i + 1))
  if [ "$i" -ge 60 ]; then
    echo "backend did not become healthy within 30s" >&2
    exit 1
  fi
  sleep 0.5
done

echo "backend healthy; starting nginx on :3000"
# nginx is the foreground process; the backend keeps running as its child.
exec nginx -c /etc/nginx/nginx.conf
