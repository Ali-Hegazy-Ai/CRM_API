import argparse
import csv
import json
import os
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://ali-hegazy-ai8576-26vewggo.leapcell.dev"
DEFAULT_OUT_DIR = os.path.join(os.path.dirname(__file__), "exports")


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch real customer data from internet CRM API and store it.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for CRM API")
    parser.add_argument("--version", default="v3", help="Data version to request")
    parser.add_argument("--limit", type=int, default=100, help="Records per page")
    parser.add_argument("--max-pages", type=int, default=0, help="0 means fetch all pages")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Directory for output files")
    return parser.parse_args()


def safe_base_url(url):
    value = str(url).strip()
    if value.endswith("/"):
        value = value[:-1]
    return value


def build_customers_url(base_url, version, page, limit):
    query = urlencode({"version": version, "page": page, "limit": limit})
    return f"{base_url}/customers?{query}"


def fetch_page(url, timeout):
    request = Request(url, headers={"Accept": "application/json"})
    context = ssl.create_default_context()

    try:
        response = urlopen(request, timeout=timeout, context=context)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        print(f"Request failed: {exc}")
        return None

    try:
        payload_text = response.read().decode("utf-8", errors="replace")
    finally:
        try:
            response.close()
        except Exception:
            pass

    try:
        return json.loads(payload_text)
    except json.JSONDecodeError:
        print("Failed to decode JSON response")
        return None


def write_json(path, data):
    file_handle = open(path, "w", encoding="utf-8")
    try:
        json.dump(data, file_handle, ensure_ascii=True, indent=2)
    finally:
        file_handle.close()


def write_csv(path, rows):
    if len(rows) == 0:
        file_handle = open(path, "w", newline="", encoding="utf-8")
        file_handle.close()
        return

    all_keys = []
    key_set = set()

    for row in rows:
        if isinstance(row, dict):
            for key in row.keys():
                if key not in key_set:
                    key_set.add(key)
                    all_keys.append(key)

    file_handle = open(path, "w", newline="", encoding="utf-8")
    try:
        writer = csv.DictWriter(file_handle, fieldnames=all_keys)
        writer.writeheader()
        for row in rows:
            if isinstance(row, dict):
                writer.writerow(row)
    finally:
        file_handle.close()


def main():
    args = parse_args()
    base_url = safe_base_url(args.base_url)

    if args.limit < 1:
        print("limit must be >= 1")
        return 1

    out_dir = args.out_dir
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    page = 1
    all_customers = []
    total_api_value = None
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    while True:
        if args.max_pages > 0 and page > args.max_pages:
            break

        url = build_customers_url(base_url, args.version, page, args.limit)
        print(f"Fetching page {page}: {url}")
        payload = fetch_page(url, args.timeout)

        if payload is None:
            return 1

        if not isinstance(payload, dict):
            print("Unexpected response shape. Expected a JSON object.")
            return 1

        data_rows = payload.get("data", [])
        if not isinstance(data_rows, list):
            print("Unexpected response shape. Field 'data' is not a list.")
            return 1

        total_api_value = payload.get("total", total_api_value)
        has_more = bool(payload.get("has_more", False))

        for row in data_rows:
            if isinstance(row, dict):
                all_customers.append(row)

        print(f"Page {page} rows: {len(data_rows)} | cumulative: {len(all_customers)} | has_more: {has_more}")

        if len(data_rows) == 0:
            break

        if not has_more:
            break

        page = page + 1

    json_path = os.path.join(out_dir, f"customers_{args.version}.json")
    csv_path = os.path.join(out_dir, f"customers_{args.version}.csv")

    output_payload = {
        "source": base_url,
        "endpoint": "/customers",
        "version": args.version,
        "started_at": started_at,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fetched_count": len(all_customers),
        "api_total_last_seen": total_api_value,
        "records": all_customers,
    }

    write_json(json_path, output_payload)
    write_csv(csv_path, all_customers)

    print(f"Saved JSON: {json_path}")
    print(f"Saved CSV: {csv_path}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())