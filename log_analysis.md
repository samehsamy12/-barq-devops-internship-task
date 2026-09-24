# Log Analysis & Correlation Report

## 1. Overview & Objectives
- Analyzed sample logs (`access.log`, `error.log`, `application.log`) using automated scripts and Linux command-line tools.
- Correlated events across tiers to identify request lifecycles, error patterns, and anomaly timings.

## 2. Key Findings & Patterns
- **Access Logs**: Tracked incoming requests directed through Nginx, noting status codes (200 OK, 503 Service Unavailable, etc.) and timestamps.
- **Application Logs**: Correlated `request_id` values to trace backend processing steps, database queries, and cache operations.
- **Error Logs**: Isolated dependency connection failures (PostgreSQL and Redis timeouts) during container startup mismatches.

## 3. Answers to Template Questions
- **What failed first?** Connection initialization failed due to password and port discrepancies in application environment variables (`app.env`).
- **What proved the cause?** Direct comparison between `docker-compose.yml` configuration values and error traces in `app-01`/`app-02` container logs.
- **Duplicate Handling:** Handled duplicate access log entries by filtering based on unique request identifiers and exact timestamp matching to avoid double-counting.
