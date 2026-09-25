# Troubleshooting journal

Keep chronological entries. Copy this block for each meaningful investigation.

## Entry / date / time
- Symptom:
- Hypothesis:
- Command or test:
- Actual output:
- Failed attempt and what changed your thinking:
- Root cause:
- Fix:
- Retest evidence:
- Related commit:
- Remaining uncertainty:

Do not fabricate a failed attempt just to fill the template. Record actual attempts.
## Entry 1 / 2026-09-24 / (initial secret scan)
- Symptom: Pre-push secret scan (`grep` for token/password/secret) flagged a hardcoded value in docker-compose.yml.
- Hypothesis: A real credential may have been committed in plaintext.
- Command or test: `grep -rniE "token|password|secret|glpat|ghp_" . --exclude-dir=.git`
- Actual output: `./docker-compose.yml:25: POSTGRES_PASSWORD: BarqLabOnly_7qN2vK8c`
- Failed attempt and what changed your thinking: N/A yet — investigation only, no fix attempted.
- Root cause: Not yet confirmed. Likely intentional starter issue: PostgreSQL password hardcoded directly in Compose file instead of sourced from .env.
- Fix: Deferred to Part 2 (Docker/Compose hardening) — move to .env, reference via variable, add to .gitignore.
- Retest evidence: Pending.
- Related commit: (to be added)
- Remaining uncertainty: Whether this password is actually the one the app currently uses, or a red herring, will confirm once containers are running.
## Entry 2 / 2026-09-24 / (log duplication pattern)
- Symptom: Initial duplicate-detection script flagged 5 duplicates in access.log and 49 in application.log.
- Hypothesis: The 49 in application.log might be a false positive caused by conflating different event types under the same request_id.
- Command or test: `grep -o '"event": "[a-z_]*"' ../logs/application.log | sort | uniq -c`, then re-ran duplicate detection keyed on (request_id, event) instead of request_id alone.
- Actual output: application.log duplicates dropped from 49 to 2 real duplicates after fixing the key. access.log confirmed 5 real duplicates: lab-000121, lab-000241, lab-000361, lab-000481, lab-000601 — all on path "/", exactly 5 minutes apart, each pair byte-for-byte identical (same timestamp, same upstream).
- Failed attempt and what changed your thinking: First duplicate count (49 in application.log) was wrong — it conflated "http_request" and "dependency_error" events sharing the same request_id, which are legitimate paired events, not duplicates. Fixed by keying on (request_id, event).
- Root cause: access.log duplicates appear to be a periodic exact-duplicate log entry (every 5 minutes, path "/", identical content) — likely a logging/monitoring artifact, not a real retried request.
- Fix: N/A — this is a log analysis finding, not an environment bug to fix. Will apply dedup rule (exact match on all fields) when computing distinct client request counts.
- Retest evidence: Verified via independent `grep` + manual inspection of all 5 flagged pairs — all confirmed identical.
- Related commit: (to be added)
- Remaining uncertainty: Root cause of the periodic duplication (NGINX log flush behavior vs external healthcheck) not confirmed — would need live environment access to verify.

## Entry 3 / 2026-09-24 / (app.env credentials/ports mismatch)
- Symptom: /ready endpoint returned {"postgres":"unavailable","redis":"unavailable"}, status 503.
  app-01 logs showed OperationalError (postgres) and ConnectionError (redis).
- Hypothesis: config/app.env credentials/ports did not match docker-compose.yml / actual service ports.
- Command or test: `cat config/app.env` compared against docker-compose.yml POSTGRES_PASSWORD and
  default Postgres/Redis ports.
- Actual output: app.env had DATABASE_URL password ending "...vK8d" (docker-compose.yml has "...vK8c"),
  postgres port 5433 (actual: 5432), REDIS_URL port 6380 (actual: 6379). Three mismatches in two lines.
- Failed attempt and what changed your thinking: First tried `docker compose restart app-01 app-02`
  after fixing app.env — still failed with same error. Learned that `restart` does not reload env_file
  contents; the container must be recreated with `--force-recreate` (or `up -d`) to pick up new env vars.
- Root cause: config/app.env had an incorrect Postgres password (typo) and incorrect hardcoded ports
  for both Postgres (5433 vs actual 5432) and Redis (6380 vs actual 6379).
- Fix: Corrected config/app.env to use the matching password (BarqLabOnly_7qN2vK8c) and correct
  default ports (postgres:5432, redis:6379). Recreated containers with `docker compose up -d --force-recreate`.
- Retest evidence: curl localhost:8080/ready now returns {"postgres":"ready","redis":"ready","status":"ready"}.
- Related commit: (to be added)
- Remaining uncertainty: Whether this was the ONLY cause of the historical incident in the log files
  (Q1-Q10 analysis), or a separate/additional misconfiguration — the log incident's root cause on the
  app-02 container side is still not fully confirmed (see log_analysis.md Q10).

## Entry 4 / 2026-09-24 / (endpoint verification)
- Symptom: N/A — proactive verification after fixing app.env.
- Command or test: Tested all required endpoints: /, /health, /ready, /instance, /records (GET+POST), /counter
- Actual output: All endpoints return 200 with expected data. /records POST required field "title"
  (not "name") - confirmed via error message, then successful insert (id:3) persisted and visible
  in subsequent GET. /counter returns incrementing Redis-backed value. Looped 6x on /instance:
  confirmed alternating app-02/app-01/app-02/app-01/app-02/app-01 - NGINX load balancing confirmed working.
- Root cause: N/A (verification, not a bug)
- Fix: N/A
- Retest evidence: All curl commands and outputs documented above.
- Related commit: (to be added)
- Remaining uncertainty: None for this verification step.
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
