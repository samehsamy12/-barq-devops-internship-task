# BARQ Assessment Environment Investigation & Fixes

## Issue 1: App Container Healthcheck Failure (404 Not Found)

- **Symptoms:** `app-01` and `app-02` containers were in `(unhealthy)` state continuously. Application logs showed repeating `GET /healthz` returning HTTP status `404`.
- **Hypothesis:** The healthcheck path specified in `docker-compose.yml` did not exist in the Flask application routes.
- **Commands & Results:**
  - `docker compose ps` -> Showed `app-01` and `app-02` as `(unhealthy)`.
  - `docker compose logs app-01 --tail=30` -> Showed `GET /healthz HTTP/1.1 404`.
  - `grep -A 5 "healthcheck" docker-compose.yml` -> Found `http://127.0.0.1:8080/healthz`.
  - `cat app/server.py` -> Identified valid endpoint is `@app.get("/health")`.
- **Root Cause:** Mismatch between the probe path in `docker-compose.yml` (`/healthz`) and the implemented Flask route (`/health`).
- **Fix:** Updated `docker-compose.yml` healthcheck test command to send requests to `/health`.
- **Verification:** Ran `docker compose up -d` and confirmed via `docker compose ps` that both `app-01` and `app-02` status changed to `(healthy)`.

## Issue #2: NGINX Port Binding and Upstream Connection Failures

### Root Cause
1. **Port Mismatch in Docker Compose**: `docker-compose.yml` forwarded host port `8080` to port `81` inside the NGINX container, whereas NGINX was configured to listen on port `80` in `nginx/nginx.conf`.
2. **Incorrect Upstream Port**: In `nginx/nginx.conf`, the `upstream` pool configured `app-01` to use port `8081` instead of `8080`.
3. **Loopback Binding Restriction**: In `docker-compose.yml`, `APP_HOST` was set to `127.0.0.1`, which caused Flask application containers (`app-01` and `app-02`) to accept connections only from `localhost` inside their own containers, rejecting requests proxied by NGINX with `Connection refused`.

### Solution Applied
1. Updated `docker-compose.yml` NGINX port mapping from `"127.0.0.1:${PUBLIC_PORT:-8080}:81"` to `"127.0.0.1:${PUBLIC_PORT:-8080}:80"`.
2. Fixed `nginx/nginx.conf` upstream block by updating `app-01:8081` to `app-01:8080`.
3. Modified `APP_HOST` in `docker-compose.yml` from `127.0.0.1` to `0.0.0.0` to allow inter-container connectivity over the Docker network.

## Issue #3: Network Isolation, Volume Persistence, and Environment Hardening

### Root Cause
1. **Unnecessary Port Exposure**: Database (15432) and Cache (16379) ports were directly exposed to the host machine.
2. **Improper Network Segmentation**: NGINX was attached to the `backend` network, violating isolation boundaries.
3. **Volatile Database Storage**: PostgreSQL utilized `tmpfs` for data directory instead of persistent volume mapping.
4. **Redis Persistence Disabled**: Redis configuration explicitly set `--appendonly no`.
5. **Configuration Typo**: `app-02` container inherited `INSTANCE_ID: "app-01"`.

### Solution Applied
1. Removed direct port publishing for `postgres` and `redis`, keeping only NGINX exposed on port 8080[cite: 1].
2. Restricted NGINX to the `frontend` network and enabled `internal: true` on the `backend` network[cite: 1].
3. Updated PostgreSQL volume mapping to `/var/lib/postgresql/data` and removed `tmpfs`.
4. Enabled Redis AOF persistence via `--appendonly yes`[cite: 1].
5. Corrected `INSTANCE_ID` for `app-02` and created a clean `.env.example` file[cite: 1].
