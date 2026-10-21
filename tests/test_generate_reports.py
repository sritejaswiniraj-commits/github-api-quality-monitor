
import json

from generate_reports import generate_reports


def write_history(path, records):
    path.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )


def test_generates_all_three_charts(tmp_path):
    history_file = tmp_path / "history.jsonl"
    output_dir = tmp_path / "reports"

    write_history(
        history_file,
        [
            {
                "success": True,
                "response_time_ms": 200,
                "performance_passed": True,
            },
            {
                "success": False,
                "response_time_ms": 600,
                "performance_passed": False,
            },
        ],
    )

    generated = generate_reports(history_file, output_dir)

    assert len(generated) == 3
    assert (output_dir / "response_times.png").is_file()
    assert (output_dir / "api_success_failures.png").is_file()
    assert (output_dir / "performance_pass_rate.png").is_file()


def test_missing_history_generates_no_charts(tmp_path):
    history_file = tmp_path / "missing.jsonl"
    output_dir = tmp_path / "reports"

    generated = generate_reports(history_file, output_dir)

    assert generated == []
    assert not output_dir.exists()


def test_legacy_records_generate_two_charts(tmp_path):
    history_file = tmp_path / "history.jsonl"
    output_dir = tmp_path / "reports"

    write_history(
        history_file,
        [
            {"success": True, "response_time_ms": 250},
            {"success": True, "response_time_ms": 300},
        ],
    )

    generated = generate_reports(history_file, output_dir)

    assert len(generated) == 2
    assert (output_dir / "response_times.png").is_file()
    assert (output_dir / "api_success_failures.png").is_file()
    assert not (output_dir / "performance_pass_rate.png").exists()


def test_invalid_json_lines_are_skipped(tmp_path, capsys):
    history_file = tmp_path / "history.jsonl"
    output_dir = tmp_path / "reports"

    history_file.write_text(
        '{"success": true, "response_time_ms": 200}\n'
        'not valid json\n',
        encoding="utf-8",
    )

    generated = generate_reports(history_file, output_dir)

    output = capsys.readouterr().out

    assert "Skipping invalid JSON on line 2" in output
    assert len(generated) == 2
