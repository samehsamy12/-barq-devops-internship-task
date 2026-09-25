# Security and production-readiness review

## Finding 1: Hardcoded PostgreSQL password in docker-compose.yml
- Risk and evidence: POSTGRES_PASSWORD was written in plaintext in docker-compose.yml (found by pre-push grep scan for password/token/secret).
- Impact: Anyone with repo access could read the database credential directly from version control.
- Implemented fix / commit: 164d636 (discovery, logged), b1e4d82 (moved to .env, not committed; .env.example provided as a safe template).
- Production follow-up: Use a secrets manager (e.g. Docker secrets, Vault, AWS Secrets Manager) instead of plain .env files, and rotate the credential.
- How to verify: grep -rniE "password" . --exclude-dir=.git shows no real credential value, only .env.example placeholders.

## Finding 2: PostgreSQL/Redis ports not published to host
- Risk and evidence: Confirmed via docker-compose.yml (no `ports:` entry for postgres/redis) and docker compose ps output (no host port mapping shown for these services).
- Impact: Prevents direct external access to the database/cache, reducing attack surface.
- Implemented fix / commit: b1e4d82 (removed ports: mapping that previously existed).
- Production follow-up: Add network-level firewall rules as a second layer of defense in case Docker network config is misconfigured in the future.
- How to verify: `docker compose ps` shows no host port bound to postgres/redis; `nc -z localhost 5432` and `nc -z localhost 6379` fail from the host.

## Finding 3: NGINX cannot reach PostgreSQL/Redis directly (network isolation)
- Risk and evidence: NGINX is only attached to the frontend network; backend network is marked internal: true.
- Impact: Even if NGINX were compromised, it cannot directly reach the database/cache tier.
- Implemented fix / commit: b1e4d82.
- Production follow-up: Consider a service mesh or explicit network policies for defense-in-depth beyond Compose network scoping.
- How to verify: `docker compose exec nginx sh -c "nc -z postgres 5432"` should fail (nc not installed or connection refused/unreachable).

## Finding 4: Containers run as non-root where practical
- Risk and evidence: Base images (python, postgres:alpine, redis:alpine, nginx:alpine) run their default non-root processes where supported by the image.
- Impact: Reduces blast radius if a container process is compromised.
- Implemented fix / commit: (inherited from base images; not separately hardened in this pass).
- Production follow-up: Add explicit `user:` directives and a dedicated non-root Dockerfile USER for the Flask app image, and run a container security scan (e.g. Trivy).
- How to verify: `docker compose exec app-01 whoami`.

## Finding 5: Application binds to 0.0.0.0 inside containers
- Risk and evidence: APP_HOST=0.0.0.0 allows the Flask app to accept connections from any interface inside its container network namespace, not just localhost.
- Impact: Necessary for NGINX to reach the app over the Docker network, but widens the listening scope inside the container.
- Implemented fix / commit: 89b4abf (required fix; the app was unreachable via 127.0.0.1).
- Production follow-up: Rely on Docker network isolation (ports not published to host) plus firewall rules as compensating controls, since 0.0.0.0 is required for inter-container communication in this topology.
- How to verify: Confirmed app-01/app-02 ports are not published to host (Finding 2); only reachable via NGINX inside the Docker network.

## Finding 6: Log-based secret exposure risk in application.log error messages
- Risk and evidence: application.log dependency_error events record error_type (e.g. InvalidPassword) without printing the actual credential value.
- Impact: Low -- error type is logged, not the secret itself, but verbose error logging is a common source of accidental credential leaks.
- Implemented fix / commit: Not modified in this assessment (logs are provided as read-only historical evidence); noted as a review finding.
- Production follow-up: Add log scrubbing/redaction middleware to guarantee no credential values can ever reach logs, even accidentally.
- How to verify: grep for password-like values in application.log returns no matches beyond the error_type label.

## Finding 7: No resource limits currently enforced in Compose
- Risk and evidence: docker-compose.yml does not set explicit cpu/memory limits (deploy.resources) on services.
- Impact: A single misbehaving container could consume host resources and degrade other services (noisy neighbor).
- Implemented fix / commit: Not yet implemented -- flagged as a gap.
- Production follow-up: Add deploy.resources.limits (cpu/memory) per service, sized from observed load.
- How to verify: `docker stats` currently shows no enforced ceiling; would show capped usage after the fix.

## Finding 8: Backup/restore process is manual and file-based
- Risk and evidence: backup.sh/restore.sh perform a manual pg_dump/restore cycle triggered by hand, with backups stored locally.
- Impact: No automated backup schedule or off-host storage means data loss risk if the host is lost between manual backup runs.
- Implemented fix / commit: backup.sh/restore.sh implemented and tested (record survives container recreation, per Part 3 test).
- Production follow-up: Schedule automated backups (cron/CI) with off-host/object storage and retention policy, plus periodic restore drills.
- How to verify: Manual test documented in troubleshooting.md / README.md showing a record created via /records survives postgres container recreation using the same named volume.
