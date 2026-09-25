# Technical decisions

## Decision 1: Deduplication method for log analysis
- Choice: Deduplicate access.log/application.log records by exact match on ALL fields (json.dumps with sort_keys), not just request_id.
- Why: Using request_id alone produced 49 false "duplicates" in application.log, because paired events (http_request + dependency_error) share the same request_id but are not dupes.
- Alternative: Dedup by request_id only (simpler, but wrong -- conflates real dupes with legitimate paired events).
- Trade-off: Exact-match dedup is stricter and slightly more code, but avoids under/over-counting.
- Evidence / commit: eb16c2a, log_analysis.md Q2.
- Production improvement: Add a dedicated event correlation ID separate from request_id.

## Decision 2: Defer secret fix instead of fixing immediately on discovery
- Choice: When the pre-push secret scan found a hardcoded PostgreSQL password in docker-compose.yml, we logged it in troubleshooting.md and deferred the actual fix to Part 2 instead of fixing it immediately.
- Why: We were still in the investigation phase; fixing without documenting symptom->cause first would break the required investigate->fix->verify commit sequence.
- Alternative: Fix immediately and document after the fact.
- Trade-off: Slightly slower resolution, but produces an auditable trail matching the task's "claim fixes only when proven" requirement.
- Evidence / commit: 164d636 (discovery), b1e4d82 (actual fix).
- Production improvement: Add a pre-commit hook that blocks commits containing secret patterns.

## Decision 3: APP_HOST binding (0.0.0.0 vs 127.0.0.1)
- Choice: Set APP_HOST=0.0.0.0 inside app containers so NGINX can reach them over the Docker network.
- Why: APP_HOST=127.0.0.1 caused Flask to only accept connections from inside its own container, rejecting NGINX's proxied requests with "Connection refused".
- Alternative: Keep 127.0.0.1 and use host networking (rejected -- breaks container isolation).
- Trade-off: 0.0.0.0 means the app listens on all interfaces, but since app-01/app-02 ports are never published to the host and the backend network is internal, external exposure risk stays low.
- Evidence / commit: 89b4abf.
- Production improvement: Add explicit firewall/network policies as defense-in-depth beyond Docker network isolation alone.

## Decision 4: Network topology (frontend/backend split)
- Choice: Two networks -- frontend (nginx + apps) and backend (apps + postgres + redis, marked internal: true). NGINX is only on frontend.
- Why: Task requires NGINX must not directly reach PostgreSQL/Redis; apps act as the only bridge between the two networks.
- Alternative: Single flat network for everything (rejected -- violates required isolation).
- Trade-off: Slightly more Compose configuration, but enforces least-privilege network access.
- Evidence / commit: b1e4d82.
- Production improvement: Add network policies/service mesh for finer-grained east-west traffic control.

## Decision 5: PostgreSQL volume persistence
- Choice: Removed tmpfs mount on /var/lib/postgresql/data and fixed the named volume mount path from /var/lib/postgresql/backup (wrong) to /var/lib/postgresql/data (correct).
- Why: The original config mounted a named volume to the wrong path AND additionally mounted tmpfs (RAM-backed, non-persistent) over the actual data directory -- meaning all data was lost on every container restart regardless of the volume.
- Alternative: Keep tmpfs for faster test runs (rejected -- task explicitly requires persistence proof across container recreation).
- Trade-off: Slightly slower I/O than tmpfs, but required for the "record survives container recreation" proof in Part 3.
- Evidence / commit: b1e4d82.
- Production improvement: Add automated volume backup scheduling and off-host backup storage.
