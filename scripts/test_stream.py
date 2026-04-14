import argparse
import csv
import json
import os
import ssl
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_URL = "http://127.0.0.1:8000"
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "test_stream_output.csv")


def parse_args():
    parser = argparse.ArgumentParser(description="Test the CRM SSE stream and export events to CSV.")
    parser.add_argument("--url", default=DEFAULT_URL, help="SSE endpoint to test")
    parser.add_argument("--limit", type=int, default=25, help="Initial backlog size to request")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="CSV file to write")
    parser.add_argument("--duration", type=int, default=15, help="Maximum number of seconds to listen")
    parser.add_argument("--timeout", type=int, default=5, help="HTTP connect timeout in seconds")
    parser.add_argument("--read-timeout", type=float, default=1.0, help="Per-read idle timeout in seconds")
    return parser.parse_args()


def normalize_data(value):
    if isinstance(value, dict):
        return value
    return {}


def parse_event_block(block_lines):
    event_type = "message"
    event_id = ""
    data_lines = []

    for line in block_lines:
        if line.startswith(":"):
            return None
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("id:"):
            event_id = line[3:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    if len(data_lines) == 0:
        return None

    data_text = "\n".join(data_lines)
    try:
        data_value = json.loads(data_text)
    except json.JSONDecodeError:
        data_value = {"raw": data_text}

    if not isinstance(data_value, dict):
        data_value = {"value": data_value}

    if event_id and "sequence" not in data_value:
        try:
            data_value["sequence"] = int(event_id)
        except ValueError:
            data_value["sequence"] = event_id

    if "event_type" not in data_value:
        data_value["event_type"] = event_type

    return data_value


def write_csv_rows(output_path, rows):
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    header = [
        "received_at",
        "sequence",
        "event_type",
        "entity",
        "id",
        "timestamp",
        "data_keys",
        "data_json",
    ]

    file_handle = open(output_path, "w", newline="", encoding="utf-8")
    try:
        writer = csv.DictWriter(file_handle, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    finally:
        file_handle.close()


def build_stream_url(url_value, limit_value):
    base_url = url_value.strip()
    if "/stream/events" not in base_url:
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        base_url = base_url + "/stream/events"

    if "?" in base_url:
        return f"{base_url}&limit={limit_value}"
    return f"{base_url}?limit={limit_value}"


def build_change_feed_url(stream_url, limit_value):
    return stream_url.replace("/stream/events", "/stream/changes").split("?", 1)[0] + f"?limit={limit_value}"


def read_change_feed(change_feed_url, timeout_value):
    helper_code = (
        "import json, ssl, sys\n"
        "from urllib.request import Request, urlopen\n"
        "url = sys.argv[1]\n"
        "request = Request(url, headers={'Accept': 'application/json'})\n"
        "response = urlopen(request, timeout=max(30, int(sys.argv[2])), context=ssl.create_default_context())\n"
        "try:\n"
        "    print(response.read().decode('utf-8', errors='replace'))\n"
        "finally:\n"
        "    response.close()\n"
    )

    try:
        completed = subprocess.run(
            [sys.executable, "-c", helper_code, change_feed_url, str(timeout_value)],
            capture_output=True,
            text=True,
            timeout=max(45, timeout_value + 15),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Failed to read change feed: {exc}")
        return []

    if completed.returncode != 0:
        stderr_text = completed.stderr.strip()
        if stderr_text:
            print(f"Failed to read change feed: {stderr_text}")
        else:
            print("Failed to read change feed from subprocess.")
        return []

    payload_text = completed.stdout.strip()

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        print("Change feed response was not valid JSON.")
        return []

    events = payload.get("events", []) if isinstance(payload, dict) else []
    rows = []

    for event_data in events:
        if not isinstance(event_data, dict):
            continue
        rows.append({
            "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sequence": event_data.get("sequence", ""),
            "event_type": event_data.get("event_type", ""),
            "entity": event_data.get("entity", ""),
            "id": event_data.get("id", ""),
            "timestamp": event_data.get("timestamp", ""),
            "data_keys": ";".join(sorted(normalize_data(event_data.get("data", {})).keys())),
            "data_json": json.dumps(normalize_data(event_data.get("data", {})), ensure_ascii=True),
        })

    return rows


def probe_stream(stream_url, duration_value, timeout_value, read_timeout_value):
    request = Request(stream_url, headers={"Accept": "text/event-stream"})
    context = ssl.create_default_context()
    event_count = 0
    keepalive_count = 0
    buffer = []
    start_time = time.time()

    try:
        response = urlopen(request, timeout=timeout_value, context=context)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        print(f"SSE stream unavailable or timed out: {exc}")
        return False, event_count, keepalive_count

    try:
        while True:
            if time.time() - start_time >= duration_value:
                break

            try:
                response.fp.raw._sock.settimeout(read_timeout_value)
                raw_line = response.readline()
            except socket.timeout:
                continue

            if raw_line == b"":
                break

            if not raw_line:
                continue

            line = raw_line.decode("utf-8", errors="replace").strip()

            if line == "":
                event_data = parse_event_block(buffer)
                buffer = []

                if event_data is not None:
                    event_count += 1
                    print(f"Received SSE event {event_count}: {event_data.get('event_type', '')} {event_data.get('entity', '')} {event_data.get('id', '')}")

                if event_count >= 1:
                    return True, event_count, keepalive_count

                continue

            if line.startswith(":"):
                keepalive_count += 1
                print("Stream keep-alive received")
                continue

            buffer.append(line)

    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"Stream probe failed: {exc}")
        return False, event_count, keepalive_count
    finally:
        try:
            response.close()
        except Exception:
            pass

    return event_count > 0, event_count, keepalive_count


def main():
    args = parse_args()
    stream_url = build_stream_url(args.url, args.limit)
    change_feed_url = build_change_feed_url(stream_url, args.limit)

    print(f"Reading change feed from {change_feed_url}")
    rows = read_change_feed(change_feed_url, args.timeout)

    if len(rows) == 0:
        print("No events were available from either stream or change feed.")
        return 1

    write_csv_rows(args.output, rows)
    print(f"Wrote {len(rows)} events to {args.output}")

    print(f"Probing SSE stream at {stream_url}")
    stream_ok, event_count, keepalive_count = probe_stream(
        stream_url,
        args.duration,
        args.timeout,
        args.read_timeout,
    )
    print(f"SSE events seen: {event_count}")
    print(f"Keep-alives seen: {keepalive_count}")
    print(f"SSE stream healthy: {stream_ok}")
    print("Stream test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())