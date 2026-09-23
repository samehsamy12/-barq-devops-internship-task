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
