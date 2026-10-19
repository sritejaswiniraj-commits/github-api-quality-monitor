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
                records.append(json.loads(line))
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
    ]

    print("=== GitHub API Quality Report ===")
    print(f"Total checks: {total}")
    print(f"Successful checks: {successful}")
    print(f"Failed checks: {failed}")
    print(f"Success rate: {success_rate:.2f}%")

    if response_times:
        print(f"Average response time: {sum(response_times) / len(response_times):.2f} ms")
        print(f"Fastest response time: {min(response_times):.2f} ms")
        print(f"Slowest response time: {max(response_times):.2f} ms")
    else:
        print("No response-time data available.")


if __name__ == "__main__":
    analyze_history()
