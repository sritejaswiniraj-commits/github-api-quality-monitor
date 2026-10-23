
import json
from pathlib import Path
from statistics import mean


def valid_response_time(record):
    value = record.get("response_time_ms")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def load_history(history_file):
    """Load valid JSON object records and report malformed JSON lines."""
    path = Path(history_file)
    records = []
    warnings = []

    if not path.exists():
        return records, warnings

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"Invalid JSON on line {line_number}")
                continue

            if isinstance(record, dict):
                records.append(record)

    return records, warnings


def calculate_metrics(records):
    """Calculate dashboard metrics from monitoring records."""
    total_checks = len(records)
    successful_checks = sum(
        record.get("success") is True for record in records
    )

    response_times = [
        value
        for record in records
        if (value := valid_response_time(record)) is not None
    ]

    performance_results = [
        record["performance_passed"]
        for record in records
        if isinstance(record.get("performance_passed"), bool)
    ]

    return {
        "total_checks": total_checks,
        "successful_checks": successful_checks,
        "failed_checks": total_checks - successful_checks,
        "success_rate": (
            successful_checks / total_checks * 100
            if total_checks else None
        ),
        "average_response_time": (
            mean(response_times) if response_times else None
        ),
        "fastest_response_time": (
            min(response_times) if response_times else None
        ),
        "slowest_response_time": (
            max(response_times) if response_times else None
        ),
        "performance_checks": len(performance_results),
        "performance_passes": sum(performance_results),
        "performance_failures": (
            len(performance_results) - sum(performance_results)
        ),
        "performance_pass_rate": (
            sum(performance_results) / len(performance_results) * 100
            if performance_results else None
        ),
    }
