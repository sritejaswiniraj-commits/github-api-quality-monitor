
import json
from pathlib import Path
from statistics import mean


HISTORY_FILE = Path("results/history.jsonl")


def analyze_history(history_file=None):
    # Resolve the path at call time so tests can patch HISTORY_FILE.
    if history_file is None:
        history_file = HISTORY_FILE

    if not history_file.exists():
        print("No history file found")
        return

    records = []

    with history_file.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON on line {line_number}")
                continue

            if isinstance(record, dict):
                records.append(record)

    if not records:
        print("No valid monitoring records found")
        return

    total_checks = len(records)
    successful_checks = sum(
        record.get("success") is True for record in records
    )
    failed_checks = total_checks - successful_checks

    success_rate = successful_checks / total_checks * 100

    print("API History Analysis")
    print("--------------------")
    print(f"Total checks: {total_checks}")
    print(f"Successful checks: {successful_checks}")
    print(f"Failed checks: {failed_checks}")
    print(f"Success rate: {success_rate:.2f}%")

    response_times = [
        record["response_time_ms"]
        for record in records
        if isinstance(record.get("response_time_ms"), (int, float))
        and not isinstance(record.get("response_time_ms"), bool)
    ]

    if response_times:
        print(f"Average response time: {mean(response_times):.2f} ms")
        print(f"Fastest response time: {min(response_times):.2f} ms")
        print(f"Slowest response time: {max(response_times):.2f} ms")
    else:
        print("No response-time data available")

    performance_results = [
        record["performance_passed"]
        for record in records
        if isinstance(record.get("performance_passed"), bool)
    ]

    if performance_results:
        performance_passes = sum(performance_results)
        performance_failures = (
            len(performance_results) - performance_passes
        )
        performance_pass_rate = (
            performance_passes / len(performance_results) * 100
        )

        print(f"Performance checks: {len(performance_results)}")
        print(f"Performance passes: {performance_passes}")
        print(f"Performance failures: {performance_failures}")
        print(f"Performance pass rate: {performance_pass_rate:.2f}%")
    else:
        print("Performance data unavailable.")


if __name__ == "__main__":
    analyze_history()
