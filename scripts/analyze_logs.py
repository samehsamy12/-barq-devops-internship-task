import json

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
