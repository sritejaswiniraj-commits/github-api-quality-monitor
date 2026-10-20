
import json
from unittest.mock import patch

import analyze_history


def test_missing_history_file(tmp_path, capsys):
    history_file = tmp_path / "history.jsonl"

    with patch.object(analyze_history, "HISTORY_FILE", history_file):
        analyze_history.analyze_history()

    output = capsys.readouterr().out
    assert "No history file found" in output


def test_empty_history_file(tmp_path, capsys):
    history_file = tmp_path / "history.jsonl"
    history_file.write_text("", encoding="utf-8")

    with patch.object(analyze_history, "HISTORY_FILE", history_file):
        analyze_history.analyze_history()

    output = capsys.readouterr().out
    assert "No valid monitoring records found" in output


def test_invalid_json_line_is_skipped(tmp_path, capsys):
    history_file = tmp_path / "history.jsonl"
    history_file.write_text(
        '{"success": true, "response_time_ms": 100}\n'
        'this is not valid JSON\n',
        encoding="utf-8",
    )

    with patch.object(analyze_history, "HISTORY_FILE", history_file):
        analyze_history.analyze_history()

    output = capsys.readouterr().out
    assert "Skipping invalid JSON on line 2" in output
    assert "Total checks: 1" in output


def test_report_calculates_success_rate_and_response_times(tmp_path, capsys):
    history_file = tmp_path / "history.jsonl"
    records = [
        {"success": True, "response_time_ms": 100},
        {"success": True, "response_time_ms": 200},
        {"success": False, "response_time_ms": 300},
    ]

    history_file.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )

    with patch.object(analyze_history, "HISTORY_FILE", history_file):
        analyze_history.analyze_history()

    output = capsys.readouterr().out
    assert "Total checks: 3" in output
    assert "Successful checks: 2" in output
    assert "Failed checks: 1" in output
    assert "Success rate: 66.67%" in output
    assert "Average response time: 200.00 ms" in output
    assert "Fastest response time: 100.00 ms" in output
    assert "Slowest response time: 300.00 ms" in output


def test_report_without_response_times(tmp_path, capsys):
    history_file = tmp_path / "history.jsonl"
    history_file.write_text(
        json.dumps({"success": True}) + "\n",
        encoding="utf-8",
    )

    with patch.object(analyze_history, "HISTORY_FILE", history_file):
        analyze_history.analyze_history()

    output = capsys.readouterr().out
    assert "Total checks: 1" in output
    assert "No response-time data available" in output
