#!/bin/sh
# Pull the latest image; if the git commit SHA baked into the OCI label changed,
# deploy it and verify /api/health reports that exact SHA. Roll back to the
# previous SHA on failure. Idempotent: a no-op when the SHA is unchanged.
set -eu
cd /opt/musical-color

. ./.env

IMAGE=ghcr.io/wsitra/musical-color
SHA_FILE=.current-sha
PREV_FILE=.previous-sha
HEALTH_URL=http://localhost:3100/api/health
COMPOSE_FILE=compose.prod.yml

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"; }

printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin >/dev/null

docker pull "$IMAGE:latest" >/dev/null
sha="$(docker inspect --format='{{index .Config.Labels "org.opencontainers.image.revision"}}' "$IMAGE:latest")"
[ -n "$sha" ] || sha="$(docker inspect --format='{{range .Config.Env}}{{if eq (split . "=" 0) "APP_VERSION"}}{{split . "=" 1}}{{end}}{{end}}' "$IMAGE:latest")"

if [ -z "$sha" ]; then
  log "error: could not determine commit SHA from $IMAGE:latest"
  exit 1
fi

current="$(cat "$SHA_FILE" 2>/dev/null || true)"

if [ "$sha" = "$current" ]; then
  log "up to date ($sha)"
  exit 0
fi

rollback() {
  prev="$(cat "$PREV_FILE" 2>/dev/null || true)"
  if [ -n "$prev" ]; then
    log "rolling back to $prev"
    docker pull "$IMAGE:$prev"
    docker tag "$IMAGE:$prev" "$IMAGE:latest"
    docker compose -f "$COMPOSE_FILE" up -d
  else
    log "no previous release to roll back to"
  fi
}

prune_old_images() {
  # $1 = previously deployed image (kept as the rollback target)
  # $2 = newly deployed image (the new current)
  keep_rollback="$1"
  keep_current="$2"
  for t in $(docker images --format '{{.Tag}}' "$IMAGE" 2>/dev/null); do
    case "$t" in
      ""|latest|"$keep_current"|"$keep_rollback") ;;
      *) docker rmi "${IMAGE}:${t}" >/dev/null 2>&1 || true ;;
    esac
  done
  docker image prune -f >/dev/null 2>&1 || true
}

log "deploying $sha (was ${current:-none})"
if ! docker tag "$IMAGE:latest" "$IMAGE:$sha" || ! docker compose -f "$COMPOSE_FILE" up -d; then
  log "deploy failed"
  rollback
  exit 1
fi

ok=""
body=""
i=0
while [ "$i" -lt 30 ]; do
  body="$(curl -fsS "$HEALTH_URL" 2>/dev/null || true)"
  if [ -n "$body" ]; then ok=1; break; fi
  i=$((i + 1))
  sleep 2
done

version="$(printf '%s' "$body" | sed -n 's/.*"version":"\([^"]*\)".*/\1/p')"
if [ "$ok" = "1" ] && [ "$version" = "$sha" ]; then
  [ -n "$current" ] && cp "$SHA_FILE" "$PREV_FILE"
  echo "$sha" > "$SHA_FILE"
  prune_old_images "$current" "$sha"
  log "deployed $sha (health ok)"
else
  log "health check failed (version='${version:-<none>}', expected $sha)"
  rollback
  exit 1
fi
