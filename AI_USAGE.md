# AI Usage Disclosure

## Tools Used
- Claude (Anthropic) and Gemini (Google) were used as AI assistants during this assessment.

## Purpose and Affected Files
- Guidance on Docker/Compose/NGINX configuration fixes: docker-compose.yml, nginx/nginx.conf, config/app.env
- Writing the log analysis Python script and interpreting results: scripts/analyze_logs.py, log_analysis.md
- Drafting documentation structure and content: troubleshooting.md, decisions.md, security_review.md, README.md
- Writing and debugging the GitHub Actions CI workflow: .github/workflows/ci.yml
- Writing validate.sh, backup.sh, restore.sh, failure_test.py

## Verification
- Every command and script was run manually in the actual Linux/Docker environment before
  being committed; results shown in this repo's commit history and troubleshooting.md are
  real command output, not generated text.
- All log_analysis.md figures (counts, percentiles, timelines) were independently
  cross-checked with separate commands (e.g. `wc -l` against script output) before being recorded.
- The CI workflow's green run (commit 05f14a4) is independent proof the described setup
  actually builds and passes validation in a clean environment, not just on the author's machine.
- All AI-suggested fixes were reviewed and tested against the actual symptom before being
  accepted; two AI-introduced YAML indentation errors (in the CI workflow) were caught via
  failed CI runs and manually corrected, as documented in the commit history.
