import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API_URL = "https://api.github.com/repos/octocat/Hello-World"
TIMEOUT_SECONDS = 10
MAX_RESPONSE_TIME_MS = 500


def validate_response_schema(data):
    """Check that required fields exist and have the expected types."""
    if not isinstance(data, dict):
        return False

    if not isinstance(data.get("id"), int):
        return False

    if not isinstance(data.get("name"), str):
        return False

    if not isinstance(data.get("full_name"), str):
        return False

    owner = data.get("owner")
    if not isinstance(owner, dict):
        return False

    if not isinstance(owner.get("login"), str):
        return False

    return True


def check_github_api():
    """Check API status, response time, schema and rate-limit headers."""
    start_time = time.perf_counter()

    result = {
        "url": API_URL,
        "status_code": None,
        "response_time_ms": None,
        "success": False,
        "performance_passed": None,
        "performance_message": None,
        "rate_limit_remaining": None,
        "has_required_fields": False,
        "error": None,
    }

    try:
        response = requests.get(API_URL, timeout=TIMEOUT_SECONDS)

        result["response_time_ms"] = round(
            (time.perf_counter() - start_time) * 1000, 2
        )
        result["status_code"] = response.status_code
        result["rate_limit_remaining"] = response.headers.get(
            "X-RateLimit-Remaining"
        )

        if response.status_code != 200:
            result["error"] = (
                f"Unexpected HTTP status: {response.status_code}"
            )
            return result

        try:
            data = response.json()
        except ValueError:
            result["error"] = "Response was not valid JSON"
            return result

        result["has_required_fields"] = validate_response_schema(data)

        if not result["has_required_fields"]:
            result["error"] = (
                "Response JSON did not match the expected schema"
            )
            return result

        result["success"] = True

        response_time = result["response_time_ms"]

        result["performance_passed"] = (
        response_time <= MAX_RESPONSE_TIME_MS
        )
        if result["performance_passed"]:
            result["performance_message"] = "Response time is within the limit"
        else:
            result["performance_message"] = (
                f"Response time exceeded the {MAX_RESPONSE_TIME_MS} ms limit"
           )

        return result

    except requests.RequestException as exc:
        result["response_time_ms"] = round(
            (time.perf_counter() - start_time) * 1000, 2
        )
        result["error"] = str(exc)
        return result


def save_result(result):
    """Append one timestamped monitoring result to the history file."""
    history_file = Path("results/history.jsonl")
    history_file.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **result,
    }

    with history_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def run_once():
    """Run a single check, save it, and return the result."""
    result = check_github_api()
    save_result(result)
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GitHub API quality monitor")
    parser.add_argument(
        "--batch",
        type=int,
        default=1,
        help="Number of samples to collect in this run (default: 1).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        help="Seconds to wait between samples in batch mode (default: 120).",
    )
    args = parser.parse_args()

    samples = max(1, args.batch)
    last_result = None

    for i in range(samples):
        last_result = run_once()
        state = "OK" if last_result["success"] else "FAIL"
        print(
            f"[{i + 1}/{samples}] {state} "
            f"status={last_result['status_code']} "
            f"{last_result['response_time_ms']}ms "
            f"{last_result['error'] or ''}"
        )
        # Space samples apart so they are genuinely time-distributed,
        # but don't sleep after the final one.
        if i < samples - 1:
            time.sleep(max(0, args.interval))

    print("result_saved_to: results/history.jsonl")

    # In batch mode we never fail the workflow on a single bad sample —
    # a real API blip is data, not a build failure. Single-run keeps the
    # original strict behaviour for CI/testing.
    if samples == 1 and last_result is not None:
        if not last_result["success"] or last_result["performance_passed"] is False:
            raise SystemExit(1)
