import json
import re

BASE = "../logs"

def load_access_log():
    path = f"{BASE}/access.log"
    valid = []
    malformed = 0
    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                valid.append(record)
            except json.JSONDecodeError:
                malformed += 1
                print(f"Malformed line {line_number}: {line[:80]}")
    return valid, malformed

def load_application_log():
    path = f"{BASE}/application.log"
    valid = []
    malformed = 0
    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                valid.append(record)
            except json.JSONDecodeError:
                malformed += 1
                print(f"Malformed line {line_number}: {line[:80]}")
    return valid, malformed

def load_error_log():
    path = f"{BASE}/error.log"
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            lines.append(line)
    return lines

def get_time_range(records):
    timestamps = [r["timestamp"] for r in records if "timestamp" in r]
    if not timestamps:
        return None, None
    return min(timestamps), max(timestamps)

def find_duplicates(records):
    seen = {}
    duplicates = 0
    for r in records:
        rid = r.get("request_id")
        event = r.get("event", "access")
        if rid is None:
            continue
        key = (rid, event)
        if key in seen:
            duplicates += 1
            print(f"  Duplicate found: request_id={rid}, event={event}")
        else:
            seen[key] = True
    return duplicates

def deduplicate(records):
    seen = set()
    unique = []
    for r in records:
        key = json.dumps(r, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique

def status_summary(records):
    counts = {}
    for r in records:
        status = r.get("status")
        if status is None:
            continue
        counts[status] = counts.get(status, 0) + 1
    total = sum(counts.values())
    errors = sum(v for k, v in counts.items() if k >= 400)
    error_rate = (errors / total * 100) if total else 0
    return counts, total, errors, error_rate

def failures_breakdown(records):
    by_path = {}
    by_backend = {}
    for r in records:
        status = r.get("status", 0)
        if status < 400:
            continue
        path = r.get("path", "unknown")
        backend = r.get("upstream", "unknown")
        by_path[path] = by_path.get(path, 0) + 1
        by_backend[backend] = by_backend.get(backend, 0) + 1
    return by_path, by_backend

def latency_percentiles(records):
    times = sorted(r["request_time"] for r in records if "request_time" in r)
    if not times:
        return None, None
    n = len(times)
    median = times[n // 2] if n % 2 == 1 else (times[n // 2 - 1] + times[n // 2]) / 2
    p95_index = int(0.95 * (n - 1))
    p95 = times[p95_index]
    return median, p95

def retry_analysis(records):
    retried = []
    for r in records:
        upstream = r.get("upstream", "")
        if "," in upstream:
            retried.append(r)
    succeeded_after_retry = sum(1 for r in retried if r.get("status", 0) < 400)
    return retried, succeeded_after_retry

def parse_error_log_timeline(error_lines):
    events = []
    pattern = re.compile(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")
    for line in error_lines:
        match = pattern.match(line)
        if match:
            events.append((match.group(1), line))
    return events

def build_timeline(access_unique, app_unique, error_lines):
    timeline = []
    for r in access_unique:
        if r.get("status", 0) >= 500:
            timeline.append((r["timestamp"], "access", f"status={r['status']} path={r.get('path')} upstream={r.get('upstream')}"))
    for r in app_unique:
        if r.get("event") == "dependency_error":
            timeline.append((r["timestamp"], "application", f"dependency_error dependency={r.get('dependency')} error_type={r.get('error_type')}"))
    for ts, line in parse_error_log_timeline(error_lines):
        timeline.append((ts, "error", line[:100]))
    timeline.sort(key=lambda x: x[0])
    return timeline

if __name__ == "__main__":
    access_records, access_malformed = load_access_log()
    print(f"[access.log] Valid: {len(access_records)}, Malformed: {access_malformed}")

    app_records, app_malformed = load_application_log()
    print(f"[application.log] Valid: {len(app_records)}, Malformed: {app_malformed}")

    error_lines = load_error_log()
    print(f"[error.log] Total non-empty lines: {len(error_lines)}")

    start, end = get_time_range(access_records)
    print(f"[access.log] Time range: {start} to {end}")

    app_start, app_end = get_time_range(app_records)
    print(f"[application.log] Time range: {app_start} to {app_end}")

    access_dupes = find_duplicates(access_records)
    print(f"[access.log] Duplicate request_ids: {access_dupes}")

    app_dupes = find_duplicates(app_records)
    print(f"[application.log] Duplicate request_ids: {app_dupes}")

    access_unique = deduplicate(access_records)
    print(f"[access.log] Distinct client requests: {len(access_unique)}")

    app_unique = deduplicate(app_records)
    print(f"[application.log] Distinct records (after exact dedup): {len(app_unique)}")

    counts, total, errors, rate = status_summary(access_unique)
    print(f"[access.log] Status counts (deduplicated): {counts}")
    print(f"[access.log] Total: {total}, Errors (>=400): {errors}, Error rate: {rate:.2f}%")

    by_path, by_backend = failures_breakdown(access_unique)
    print(f"[access.log] Failures by path: {by_path}")
    print(f"[access.log] Failures by backend: {by_backend}")

    median, p95 = latency_percentiles(access_unique)
    print(f"[access.log] Median latency: {median*1000:.1f}ms, P95: {p95*1000:.1f}ms")

    retried, succeeded = retry_analysis(access_unique)
    print(f"[access.log] Requests that retried upstream: {len(retried)}")
    print(f"[access.log] Succeeded after retry: {succeeded}")
    for r in retried[:5]:
        print(f"  Sample retry: request_id={r['request_id']}, upstream={r['upstream']}, status={r['status']}")

    timeline = build_timeline(access_unique, app_unique, error_lines)
    print(f"\n=== TIMELINE (last 15 events) ===")
    for ts, source, detail in timeline[-15:]:
        print(f"{ts} [{source}] {detail}")
