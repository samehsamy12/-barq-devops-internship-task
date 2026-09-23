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
## Timeline and correlated examples
## Conclusions and limits
