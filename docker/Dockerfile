# syntax=docker/dockerfile:1

# --- Frontend build ---------------------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /src
COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci
COPY app/frontend/ ./
RUN npm run build

# --- Rust backend build -----------------------------------------------------
FROM debian:trixie-slim AS rust
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl xz-utils build-essential cmake pkg-config git \
    && rm -rf /var/lib/apt/lists/*
ENV RUSTUP_HOME=/root/.rustup \
    CARGO_HOME=/root/.cargo \
    PATH=/root/.cargo/bin:$PATH
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --profile minimal --default-toolchain stable --component rustfmt
WORKDIR /app
COPY app/backend/Cargo.toml app/backend/Cargo.lock ./
# Compile dependencies against a throwaway binary so that src-only changes
# only recompile the (small) backend crate, not the whole lbug tree.
RUN mkdir -p src && echo 'fn main() {}' > src/main.rs && cargo build --release && rm src/main.rs
COPY app/backend/src ./src
RUN cargo build --release

# --- Runtime ----------------------------------------------------------------
FROM debian:trixie-slim AS runtime
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      nginx libstdc++6 libgcc-s1 curl \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd -r app && useradd -r -g app -M -d /app -s /usr/sbin/nologin app
WORKDIR /app

ARG COMMIT_SHA=""
ENV APP_VERSION=${COMMIT_SHA}
LABEL org.opencontainers.image.revision=${COMMIT_SHA}

COPY --from=rust /app/target/release/backend /app/backend
COPY --from=frontend /src/dist /app/dist
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh \
    && chown -R app:app /app \
    && chown -R app:app /var/log/nginx /var/lib/nginx
# Dataset (clips, manifest, .lbdb) is bind-mounted at /app/data at deploy time.
RUN mkdir -p /app/data && chown -R app:app /app/data

ENV PORT=3001 \
    APP_VERSION="" \
    LBDB_PATH=/app/data/music_color.lbdb \
    MANIFEST_PATH=/app/data/manifest/tracks.jsonl \
    CLIPS_DIR=/app/data/clips

EXPOSE 3000
USER app
ENTRYPOINT ["/app/entrypoint.sh"]
