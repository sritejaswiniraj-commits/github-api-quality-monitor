


from dashboard_utils import (
    calculate_metrics,
    load_history,
    valid_response_time,
)


def test_load_history_reads_valid_records(tmp_path):
    history = tmp_path / "history.jsonl"
    history.write_text(
        '{"success": true}\n{"success": false}\n',
        encoding="utf-8",
    )

    records, warnings = load_history(history)

    assert len(records) == 2
    assert records[0]["success"] is True
    assert records[1]["success"] is False
    assert warnings == []


def test_load_history_skips_invalid_json(tmp_path):
    history = tmp_path / "history.jsonl"
    history.write_text(
        '{"success": true}\nnot-json\n',
        encoding="utf-8",
    )

    records, warnings = load_history(history)

    assert len(records) == 1
    assert warnings == ["Invalid JSON on line 2"]


def test_load_history_handles_missing_file(tmp_path):
    records, warnings = load_history(tmp_path / "missing.jsonl")

    assert records == []
    assert warnings == []


def test_valid_response_time_excludes_invalid_values():
    assert valid_response_time({"response_time_ms": 120.5}) == 120.5
    assert valid_response_time({"response_time_ms": True}) is None
    assert valid_response_time({"response_time_ms": "120"}) is None
    assert valid_response_time({}) is None


def test_calculate_metrics():
    records = [
        {
            "success": True,
            "response_time_ms": 100,
            "performance_passed": True,
        },
        {
            "success": False,
            "response_time_ms": 300,
            "performance_passed": False,
        },
        {
            "success": True,
            "response_time_ms": 200,
        },
    ]

    metrics = calculate_metrics(records)

    assert metrics["total_checks"] == 3
    assert metrics["successful_checks"] == 2
    assert metrics["failed_checks"] == 1
    assert metrics["success_rate"] == (2 / 3) * 100
    assert metrics["average_response_time"] == 200
    assert metrics["fastest_response_time"] == 100
    assert metrics["slowest_response_time"] == 300
    assert metrics["performance_checks"] == 2
    assert metrics["performance_passes"] == 1
    assert metrics["performance_failures"] == 1
    assert metrics["performance_pass_rate"] == 50


def test_calculate_metrics_handles_empty_history():
    metrics = calculate_metrics([])

    assert metrics["total_checks"] == 0
    assert metrics["success_rate"] is None
    assert metrics["average_response_time"] is None
    assert metrics["performance_pass_rate"] is None


def test_legacy_records_are_excluded_from_performance_rate():
    records = [
        {"success": True, "performance_passed": True},
        {"success": True},
        {"success": False, "performance_passed": False},
    ]

    metrics = calculate_metrics(records)

    assert metrics["performance_checks"] == 2
    assert metrics["performance_pass_rate"] == 50
