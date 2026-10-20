
import json
from pathlib import Path

HISTORY_FILE = Path("results/history.jsonl")


def analyze_history():
    """Summarize historical API monitoring results."""
    if not HISTORY_FILE.exists():
        print("No history file found. Run python monitor.py first.")
        return

    records = []

    with HISTORY_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
                if isinstance(record, dict):
                    records.append(record)
                else:
                    print(f"Skipping invalid record on line {line_number}.")
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON on line {line_number}.")

    if not records:
        print("No valid monitoring records found.")
        return

    total = len(records)
    successful = sum(record.get("success") is True for record in records)
    failed = total - successful
    success_rate = successful / total * 100

    response_times = [
        record["response_time_ms"]
        for record in records
        if isinstance(record.get("response_time_ms"), (int, float))
        and not isinstance(record.get("response_time_ms"), bool)
    ]

    print("=== GitHub API Quality Report ===")
    print(f"Total checks: {total}")
    print(f"Successful checks: {successful}")
    print(f"Failed checks: {failed}")
    print(f"Success rate: {success_rate:.2f}%")

    if response_times:
        print(
            f"Average response time: "
            f"{sum(response_times) / len(response_times):.2f} ms"
        )
        print(f"Fastest response time: {min(response_times):.2f} ms")
        print(f"Slowest response time: {max(response_times):.2f} ms")
    else:
        print("No response-time data available.")

    performance_records = [
        record
        for record in records
        if isinstance(record.get("performance_passed"), bool)
    ]

    if performance_records:
        performance_checks = len(performance_records)
        performance_passes = sum(
            record["performance_passed"] is True
            for record in performance_records
        )
        performance_failures = performance_checks - performance_passes
        performance_pass_rate = performance_passes / performance_checks * 100

        print(f"Performance checks: {performance_checks}")
        print(f"Performance passes: {performance_passes}")
        print(f"Performance failures: {performance_failures}")
        print(f"Performance pass rate: {performance_pass_rate:.2f}%")
    else:
        print("Performance data unavailable.")


if __name__ == "__main__":
    analyze_history()
