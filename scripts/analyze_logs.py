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
