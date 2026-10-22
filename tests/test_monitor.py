
from unittest.mock import Mock, patch

import requests

from monitor import check_github_api


def make_response(status_code=200, data=None, headers=None):
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}

    if data is None:
        data = {
            "id": 123,
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": {"login": "octocat"},
        }

    response.json.return_value = data
    return response


@patch("monitor.requests.get")
def test_successful_api_response(mock_get):
    mock_get.return_value = make_response(
        headers={"X-RateLimit-Remaining": "59"}
    )

    result = check_github_api()

    assert result["success"] is True
    assert result["status_code"] == 200
    assert result["has_required_fields"] is True
    assert result["rate_limit_remaining"] == "59"


@patch("monitor.requests.get")
def test_http_error_is_recorded(mock_get):
    mock_get.return_value = make_response(status_code=403)

    result = check_github_api()

    assert result["success"] is False
    assert result["status_code"] == 403
    assert "Unexpected HTTP status" in result["error"]


@patch("monitor.requests.get")
def test_missing_required_field_is_detected(mock_get):
    mock_get.return_value = make_response(
        data={"id": 123, "name": "Hello-World"}
    )

    result = check_github_api()

    assert result["success"] is False
    assert result["has_required_fields"] is False


@patch("monitor.requests.get")
def test_invalid_json_is_recorded(mock_get):
    response = make_response()
    response.json.side_effect = ValueError("Invalid JSON")
    mock_get.return_value = response

    result = check_github_api()

    assert result["success"] is False
    assert result["error"] == "Response was not valid JSON"


@patch("monitor.requests.get")
def test_timeout_is_recorded(mock_get):
    mock_get.side_effect = requests.Timeout("Request timed out")

    result = check_github_api()

    assert result["success"] is False
    assert result["status_code"] is None
    assert "timed out" in result["error"].lower()


@patch("monitor.requests.get")
def test_wrong_field_type_is_detected(mock_get):
    mock_get.return_value = make_response(
        data={
            "id": "123",
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": {"login": "octocat"},
        }
    )

    result = check_github_api()

    assert result["success"] is False
    assert result["has_required_fields"] is False
    assert result["error"] == (
        "Response JSON did not match the expected schema"
    )


@patch("monitor.requests.get")
def test_invalid_owner_structure_is_detected(mock_get):
    mock_get.return_value = make_response(
        data={
            "id": 123,
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": "octocat",
        }
    )

    result = check_github_api()

    assert result["success"] is False
    assert result["has_required_fields"] is False


def test_fast_response_passes_performance_threshold():
    mock_response = make_response()
    with patch("monitor.requests.get", return_value=mock_response):
        with patch("monitor.time.perf_counter", side_effect=[0, 0.3]):
            result = check_github_api()

    assert result["success"] is True
    assert result["performance_passed"] is True
    assert result["performance_message"] == "Response time is within the limit"


def test_slow_response_fails_performance_threshold():
    mock_response = make_response()
    with patch("monitor.requests.get", return_value=mock_response):
        with patch("monitor.time.perf_counter", side_effect=[0, 0.7]):
            result = check_github_api()

    assert result["success"] is True
    assert result["performance_passed"] is False
    assert "exceeded" in result["performance_message"]


@patch("monitor.requests.get")
def test_missing_rate_limit_header_does_not_fail_valid_response(mock_get):
    mock_get.return_value = make_response(headers={})

    result = check_github_api()

    assert result["success"] is True
    assert result["rate_limit_remaining"] is None


@patch("monitor.requests.get")
def test_connection_error_is_recorded(mock_get):
    mock_get.side_effect = requests.ConnectionError("Connection failed")

    result = check_github_api()

    assert result["success"] is False
    assert result["status_code"] is None
    assert "Connection failed" in result["error"]


def test_response_at_exact_threshold_passes():
    mock_response = make_response()

    with patch("monitor.requests.get", return_value=mock_response):
        with patch("monitor.time.perf_counter", side_effect=[0, 0.5]):
            result = check_github_api()

    assert result["response_time_ms"] == 500.0
    assert result["performance_passed"] is True


@patch("monitor.requests.get")
def test_non_dictionary_json_is_rejected(mock_get):
    mock_get.return_value = make_response(data=["not", "an", "object"])

    result = check_github_api()

    assert result["success"] is False
    assert result["has_required_fields"] is False
    assert result["error"] == (
        "Response JSON did not match the expected schema"
    )


def test_schema_rejects_invalid_top_level_types():
    from monitor import validate_response_schema

    assert validate_response_schema(None) is False
    assert validate_response_schema([]) is False
    assert validate_response_schema("not an object") is False
    assert validate_response_schema(123) is False

