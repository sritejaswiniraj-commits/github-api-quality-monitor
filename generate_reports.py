
import json
from pathlib import Path

import matplotlib

# Use a non-interactive backend so charts can be generated in CI.
matplotlib.use("Agg")

import matplotlib.pyplot as plt


HISTORY_FILE = Path("results/history.jsonl")
REPORTS_DIR = Path("reports")
PERFORMANCE_THRESHOLD_MS = 500


def load_history(history_file=HISTORY_FILE):
    """Load valid JSON object records from a JSONL history file."""
    records = []

    if not history_file.exists():
        print("No history file found")
        return records

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

    return records


def valid_response_time(record):
    """Return a numeric response time, excluding booleans."""
    value = record.get("response_time_ms")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def generate_reports(history_file=None, output_dir=None):
    """Generate response-time, API-result, and performance charts."""
    if history_file is None:
        history_file = HISTORY_FILE
    if output_dir is None:
        output_dir = REPORTS_DIR

    records = load_history(history_file)

    if not records:
        print("No valid monitoring records found; no charts generated.")
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    # Chart 1: response time per record that contains valid timing data.
    timed_records = [
        (index, value)
        for index, record in enumerate(records, start=1)
        if (value := valid_response_time(record)) is not None
    ]

    if timed_records:
        run_numbers, response_times = zip(*timed_records)

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(run_numbers, response_times, marker="o", label="Response time")
        ax.axhline(
            PERFORMANCE_THRESHOLD_MS,
            linestyle="--",
            label=f"Threshold ({PERFORMANCE_THRESHOLD_MS} ms)",
        )
        ax.set_title("API Response Times")
        ax.set_xlabel("Monitoring record")
        ax.set_ylabel("Response time (ms)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()

        path = output_dir / "response_times.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        generated_files.append(path)
    else:
        print("No valid response-time data; response-time chart skipped.")

    # Chart 2: successful versus failed API checks.
    successful = sum(record.get("success") is True for record in records)
    failed = len(records) - successful

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(["Successful", "Failed"], [successful, failed])
    ax.set_title("API Check Results")
    ax.set_ylabel("Number of checks")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    path = output_dir / "api_success_failures.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    generated_files.append(path)

    # Chart 3: performance results only for records with a boolean value.
    performance_results = [
        record["performance_passed"]
        for record in records
        if isinstance(record.get("performance_passed"), bool)
    ]

    if performance_results:
        passes = sum(performance_results)
        failures = len(performance_results) - passes

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.bar(["Passed", "Failed"], [passes, failures])
        ax.set_title("Performance Threshold Results")
        ax.set_ylabel("Number of checks")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()

        path = output_dir / "performance_pass_rate.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        generated_files.append(path)
    else:
        print("No performance data; performance chart skipped.")

    print(f"Generated {len(generated_files)} chart(s):")
    for path in generated_files:
        print(path)

    return generated_files


if __name__ == "__main__":
    generate_reports()
