
import time

import requests

API_URL = "https://api.github.com/repos/octocat/Hello-World"
TIMEOUT_SECONDS = 10


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
            result["error"] = "Response JSON did not match the expected schema"
            return result

        result["success"] = True
        return result

    except requests.RequestException as exc:
        result["response_time_ms"] = round(
            (time.perf_counter() - start_time) * 1000, 2
        )
        result["error"] = str(exc)
        return result


if __name__ == "__main__":
    result = check_github_api()

    for key, value in result.items():
        print(f"{key}: {value}")
