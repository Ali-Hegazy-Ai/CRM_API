import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"


def get_json(path, params=None):
	if params is None:
		params = {}

	url = BASE + path
	if len(params) > 0:
		query = urllib.parse.urlencode(params)
		url = url + "?" + query

	with urllib.request.urlopen(url, timeout=10) as response:
		status_code = response.getcode()
		body = response.read().decode("utf-8")
		return status_code, json.loads(body)


def check_health():
	status_code, _ = get_json("/health")
	assert status_code == 200
	print("Health OK")


def check_metrics():
	status_code, data = get_json("/metrics")
	assert status_code == 200
	print("Metrics:", data)
	assert "current_state_count" in data


def check_entities():
	status_code, data = get_json("/customers", {"version": "v3", "limit": 5})
	assert status_code == 200
	assert "data" in data
	print("Entities OK, count:", len(data["data"]))


def check_incremental():
	now = int(time.time())
	time.sleep(2)

	status_code, data = get_json("/customers", {"version": "v3", "updated_after": now})
	assert status_code == 200
	print("Incremental OK, returned:", len(data["data"]))


def check_cdc():
	status1, data1 = get_json("/changes", {"since": 0, "limit": 3})
	assert status1 == 200

	assert len(data1["events"]) > 0
	next_cursor = data1["next_cursor"]

	status2, data2 = get_json("/changes", {"since": next_cursor, "limit": 3})
	assert status2 == 200

	print("CDC OK")
	print("Page1:", [e["event_id"] for e in data1["events"]])
	print("Page2:", [e["event_id"] for e in data2["events"]])


def main():
	print("Running smoke test...\n")

	try:
		check_health()
		check_metrics()
		check_entities()
		check_incremental()
		check_cdc()
	except urllib.error.URLError:
		print("Smoke test failed: could not connect to API at", BASE)
		print("Start the API server first, then run this script again.")
		sys.exit(1)
	except AssertionError:
		print("Smoke test failed: one of the API checks did not pass.")
		sys.exit(1)

	print("\nALL TESTS PASSED")


if __name__ == "__main__":
	main()
