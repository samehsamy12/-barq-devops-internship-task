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
