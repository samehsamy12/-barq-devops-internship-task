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
