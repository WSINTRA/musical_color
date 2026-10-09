# VPS Runbook — Musical Color

Model: GitHub Actions builds the image and pushes it to GHCR
(`ghcr.io/wsitra/musical-color`). A systemd timer on the server checks every
15 minutes for a new `latest`, and only when the baked git commit SHA changes,
pulls it, re-tags it `latest`, restarts the compose stack, and verifies
`/api/health` reports that exact SHA (baked in as the OCI
`org.opencontainers.image.revision` label). On verification failure it rolls
back to the previous SHA.

The image is code-only. The **dataset** (clips, manifest, `music_color.lbdb`)
lives on the server at `/opt/musical-color/data` and is bind-mounted into the
container at `/app/data`. It is **not** in the image and is **not** in git.

Nothing here commits secrets to the repo. The only secret on the server is the
read-only GHCR token in `/opt/musical-color/.env` (chmod 600).

## Health check

- Endpoint: `GET /api/health` → `{"status":"ok","version":"<git sha>"}`
- From the server: `curl http://localhost:3100/api/health`
- The `version` must match the deployed commit SHA
  (`cat /opt/musical-color/.current-sha`).

## 1. One-time GitHub setup (do in your browser)

Create a fine-grained PAT scoped to the `WSINTRA/musical_color` repo with
**Contents: Read-only** and **Packages: Read and write**. Store it as a
repository secret named `GHCR_TOKEN` (used by the `image` job to push).

Create a second fine-grained PAT with the same scope but **Packages: Read-only**
— that one goes on the server (step 2) and is used to pull.

## 2. Server prep

```sh
ssh ws@<host>
sudo mkdir -p /opt/musical-color/data
sudo chown -R ws:ws /opt/musical-color
cd /opt/musical-color
```

Create `/opt/musical-color/.env`:

```sh
cat > /opt/musical-color/.env <<EOF
GHCR_USER=wsitra
GHCR_TOKEN=PASTE_READ_ONLY_PAT_HERE
EOF
chmod 600 /opt/musical-color/.env
```

## 3. Ship the dataset

Copy the dataset into `/opt/musical-color/data` (from a machine that has the
processed `data/` directory). The container needs at minimum:

```
data/
├── clips/                        # trimmed .wav + demucs .mp3 + _lyrics.txt
└── manifest/tracks.jsonl          # seeded into LadybugDB on container start
```

`music_color.lbdb` is created/updated by the backend at start and persists in
this bind mount. To keep the server in sync with local pipeline runs:

```sh
rsync -a --delete data/clips data/manifest ws@<host>:/opt/musical-color/data/
```

After adding/removing tracks, restart the stack once so the manifest re-seeds:

```sh
docker compose -f /opt/musical-color/compose.prod.yml up -d
```

## 4. Compose file

`/opt/musical-color/compose.prod.yml`:

```yaml
services:
  app:
    image: ghcr.io/wsitra/musical-color:latest
    ports:
      - '3100:3000'
    environment:
      PORT: '3001'
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

## 5. Deploy script

The canonical script is in the repo at `docker/deploy/pull-and-run.sh`.
Install/refresh it on the server:

```sh
scp ws@<dev-machine>:<repo>/docker/deploy/pull-and-run.sh /opt/musical-color/pull-and-run.sh
chmod +x /opt/musical-color/pull-and-run.sh
```

It pulls `:latest`, reads the SHA from the OCI label (fallback: `APP_VERSION`
env), and if it changed, re-tags it `latest`, restarts compose, and polls
`/api/health` for up to 60s. The reported `version` must equal the SHA,
otherwise it rolls back to the previous SHA.

## 6. systemd timer

`/etc/systemd/system/musical-color-deploy.service`:

```ini
[Unit]
Description=Musical Color: pull and deploy new image if available
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/opt/musical-color/pull-and-run.sh
```

`/etc/systemd/system/musical-color-deploy.timer`:

```ini
[Unit]
Description=Run Musical Color deploy check every 15 minutes

[Timer]
OnBootSec=30s
OnUnitActiveSec=15min
AccuracySec=10s

[Install]
WantedBy=timers.target
```

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now musical-color-deploy.timer
systemctl list-timers | grep musical-color
```

Logs: `journalctl -u musical-color-deploy.service -f`

## 7. Firewall

Open TCP 3100 in the firewall so the app is reachable, then tighten to 80/443
once nginx + TLS are added in front.

## 8. First deploy + verification

With `GHCR_TOKEN` set on GitHub and the pipeline green, the timer picks up the
first image within ~15 min of a push. Or trigger immediately:

```sh
sudo /opt/musical-color/pull-and-run.sh
```

Verify:

```sh
curl -s http://localhost:3100/api/health
# {"status":"ok","version":"<git sha>"}
cat /opt/musical-color/.current-sha
```

`<git sha>` must match the pushed commit.

## 9. Rollback (manual)

```sh
cd /opt/musical-color
. ./.env
sha="<old-sha>"
docker pull ghcr.io/wsitra/musical-color:$sha
docker tag ghcr.io/wsitra/musical-color:$sha ghcr.io/wsitra/musical-color:latest
docker compose -f compose.prod.yml up -d
echo "$sha" | sudo tee /opt/musical-color/.current-sha
```

## 10. Backups

Nightly: tar the dataset (which contains `music_color.lbdb`) to local + offsite.

```sh
tar -czf /opt/musical-color/data-$(date +%F).tgz -C /opt/musical-color data
```
