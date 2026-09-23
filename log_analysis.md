# Log analysis

Use all three supplied logs. Answer every question with commands/scripts and actual output.

1. What UTC interval is covered? How many valid, malformed and duplicate lines are in each file?
2. How many distinct client requests occurred? How did you deduplicate and avoid counting retries twice?
3. What are the final client status counts and error rate? State your denominator.
4. Which paths, time windows and backends account for the failures?
5. What are the median and p95 client latencies? State the percentile method and units.
6. Which requests retried upstream? How many succeeded after retrying?
7. Build an incident timeline using evidence from access, error AND application logs.
8. Show one correlated failed request and one successful request. Include IDs and timestamps.
9. Which errors appear to be proxy/connectivity issues versus dependency/application issues? What proves it?
10. What do the logs not prove? What would you check next in a running environment?

## Commands / scripts
## Results
### Q1: Time range & line counts
- Time range: 2026-08-20T11:00:00.015Z to 2026-08-20T11:29:57.578Z (UTC, ~30 minutes)
- access.log: 725 valid, 1 malformed, 5 exact duplicates -> 720 distinct
- application.log: 729 valid, 1 malformed, 2 exact duplicates -> 727 distinct
- error.log: 68 non-empty lines (plain text, no JSON validity concept)
- Commands: `python3 scripts/analyze_logs.py`, cross-verified with `wc -l`

### Q2: Distinct client requests & dedup method
- 720 distinct client requests (from access.log)
- Dedup method: exact match across ALL fields (json.dumps with sort_keys), not just request_id
- Rationale: request_id alone caused false positives in application.log (47 false "duplicates"
  were actually paired http_request + dependency_error events for the same request, not true dupes)
- 5 true duplicates found in access.log: lab-000121/241/361/481/601, all path "/",
  exactly 5 minutes apart, byte-for-byte identical -> likely a logging artifact, not a retried request

### Q3: Final status counts & error rate
- Status counts (deduplicated, n=720): {200: 615, 404: 10, 502: 40, 503: 47, 504: 8}
- Denominator: 720 distinct client requests
- Errors (status >= 400): 105
- Error rate: 14.58%
- Command: python3 scripts/analyze_logs.py (status_summary function)

### Q4: Failures by path, time window, and backend
- Failures by path (status >= 400, n=105): {/records: 26, /counter: 26, /ready: 23,
  /missing: 10, /health: 10, /: 10}
- Note: /missing is expected to fail (nonexistent route, likely all 404s) — not a real issue.
  /records, /counter, /ready are real required endpoints with disproportionately high failure counts.
- Failures by backend: app-01 (172.23.0.11:8080) = 32 failures, app-02 (172.23.0.12:8080) = 73 failures
- app-02 accounts for more than double the failures of app-01 -> strong quantitative evidence
  supporting the error.log finding that app-02 experienced a connectivity outage during the incident.
- Command: python3 scripts/analyze_logs.py (failures_breakdown function)

### Q5: Median and p95 client latency
- Method: request_time field (seconds) from access.log, deduplicated records only, nearest-rank
  percentile method (index = 0.95 * (n-1) after sorting)
- Median latency: 54.0ms
- P95 latency: 2001.0ms
- Units: milliseconds (converted from request_time, which is in seconds per logs/README.md)
- Observation: ~37x gap between median and p95 suggests a small subset of very slow requests
  pulling the tail up, likely correlated with the app-02 outage window (to be confirmed against
  error.log timestamps in Q7/Q9)
- Command: python3 scripts/analyze_logs.py (latency_percentiles function)

### Q6: Retried requests and retry success rate
- 19 requests retried upstream (upstream field contains comma-separated addresses)
- All 19 (100%) succeeded after retry (final status < 400)
- Pattern: every retry sample tried 172.23.0.12:8080 (app-02) FIRST, then fell back to
  172.23.0.11:8080 (app-01) — consistent with app-02 being unavailable during the incident window
- Open question for Stage 2 investigation: why did only 19 requests get an upstream retry while
  95 other failed requests (Q3/Q4) received a direct 502/503/504 with no retry? Needs review of
  NGINX upstream/retry configuration.
- Command: python3 scripts/analyze_logs.py (retry_analysis function)

### Q7: Incident timeline (correlated across access, error, application logs)
- 11:05:02Z: First 502 errors begin appearing for app-02 (172.23.0.12), cycling through
  /health, /records, /counter, / every ~5-10 seconds
- 11:05-~11:20: Repeated "connect() failed (111: Connection refused)" in error.log for app-02
  -> app-02 process appears to be down/unreachable (TCP connection actively refused)
- ~11:20:07 onward: application.log shows dependency_error events (InvalidPassword) against
  postgres, overlapping with the app-02 outage window
- 11:25:14 onward: error.log pattern shifts to "upstream timed out (110)" instead of
  "connection refused" -> suggests app-02 came back up but was slow/unresponsive rather than
  fully down, consistent with the P95 latency spike (~2001ms) found in Q5
- 11:30:00: "log collector rotated stream" notice marks end of captured log window (not
  necessarily end of incident, just end of this log file's time range)
- Command: python3 scripts/analyze_logs.py (build_timeline function, cross-referencing all 3 logs)

### Q8: One correlated failed request and one successful request
**Failed request: lab-000122**
- access.log: 11:05:02.503Z, GET /health, status=502, upstream=172.23.0.12:8080, request_time=0.003s
- error.log: 11:05:02, "connect() failed (111: Connection refused)" targeting
  http://172.23.0.12:8080/health, request_id=lab-000122
- application.log: NO RECORD FOUND — the request never reached the application layer;
  it failed at the NGINX/proxy level before hitting app-02.

**Successful request: lab-000002**
- access.log: 11:00:02.532Z, GET /health, status=200, upstream=172.23.0.12:8080, request_time=0.032s
- error.log: no record (expected, request succeeded)
- application.log: 11:00:02.532Z, event=http_request, instance_id=app-02, status=200, duration_ms=32.0
- Note: this successful request hit the SAME backend (app-02) five minutes before it went down,
  confirming app-02 was healthy at 11:00 and failed sometime before 11:05.

### Q9: Proxy/connectivity errors vs dependency/application errors
**Proxy/connectivity issues (NGINX <-> backend):**
- Evidence: error.log shows "connect() failed (111: Connection refused)" (11:05-~11:20) and
  "upstream timed out (110)" (11:25 onward), both targeting app-02 (172.23.0.12:8080)
- Evidence: access.log shows 502 (Bad Gateway) and 504 (Gateway Timeout) responses directly
  correlated with those error.log timestamps and the same upstream
- Evidence: the failed example (lab-000122, Q8) has NO corresponding application.log entry —
  proof the request never reached the app, confirming it's a proxy-layer failure, not an
  application bug
- Total: 40 (502) + 8 (504) = 48 requests attributable to proxy/connectivity issues (Q3 data)

**Dependency/application issues:**
- Evidence: application.log contains 47 "dependency_error" events with error_type=InvalidPassword,
  dependency=postgres, occurring ~11:20:07 to ~11:21:45 — DIFFERENT time window than the
  connection-refused phase (11:05-11:20)
- These represent the application successfully receiving a request but failing to complete it
  due to a downstream dependency (database credential) problem — a distinct failure mode from
  NGINX being unable to reach the app at all
- 503 (Service Unavailable, 47 occurrences, Q3 data) is the client-facing status most likely
  correlated with this application-level dependency failure, based on matching counts (47 vs 47)

**What proves the distinction:** presence/absence of an application.log entry for the same
request_id, plus which log (error.log vs application.log) contains the failure detail, plus
whether the timestamp falls in the "connection refused" window vs the "dependency_error" window.

### Q10: What the logs do not prove / what to check next in a running environment
**What the logs do NOT prove:**
- WHY app-02 became unreachable (process crash, OOM kill, container restart, network partition,
  resource exhaustion) — error.log only shows the symptom (connection refused / timeout), not
  the root cause on the app-02 side
- Whether the postgres InvalidPassword errors (11:20-11:21) were caused by the SAME incident as
  the app-02 outage, or a separate, coincidentally overlapping issue — the logs show correlation
  in time but not a confirmed causal link
- Whether app-02 fully recovered after 11:30 (the log window ends there) — we only know the
  timeout pattern continued through the end of the captured window
- The actual NGINX upstream/retry configuration (max_fails, fail_timeout, proxy_next_upstream
  settings) that explains why only 19 of many failed requests received an automatic retry
- Current state of the running environment — these are historical/synthetic logs, not live data

**What to check next in a running environment:**
- `docker ps` / `docker logs app-02` (or equivalent container name) to see actual crash/restart
  evidence and exit codes around 11:05 and 11:25
- NGINX config (nginx.conf) for upstream block settings: retry policy, timeouts, health checks
- PostgreSQL logs/config around 11:20 to confirm whether a credential rotation, restart, or
  config change caused the InvalidPassword errors
- Container resource usage/limits (docker stats) to rule out OOM as a root cause
- Whether a health check or restart policy exists that would have auto-recovered app-02, and
  whether it worked as intended
## Timeline and correlated examples
## Conclusions and limits
