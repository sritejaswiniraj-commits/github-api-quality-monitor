
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

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(
            run_numbers,
            response_times,
            marker="o",
            linewidth=2,
            markersize=6,
            label="Response time",
        )
        ax.axhline(
            PERFORMANCE_THRESHOLD_MS,
            linestyle="--",
            linewidth=1.5,
            label=f"Performance threshold ({PERFORMANCE_THRESHOLD_MS} ms)",
        )

        # Highlight measurements that exceed the threshold.
        for run_number, response_time in timed_records:
            if response_time > PERFORMANCE_THRESHOLD_MS:
                ax.annotate(
                    f"{response_time:g} ms",
                    (run_number, response_time),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha="center",
                    fontsize=8,
                )

        ax.set_title("API Response Time by Monitoring Run")
        ax.set_xlabel("Monitoring run")
        ax.set_ylabel("Response time (ms)")
        ax.set_xticks(run_numbers)
        ax.grid(axis="y", alpha=0.3)
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
    total_checks = len(records)
    success_rate = (successful / total_checks) * 100 if total_checks else 0

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(["Successful", "Failed"], [successful, failed])

    ax.set_title(f"API Check Results — {success_rate:.1f}% Success Rate")
    ax.set_ylabel("Number of checks")
    ax.grid(axis="y", alpha=0.3)

    for bar, count in zip(bars, [successful, failed]):
        ax.annotate(
            str(count),
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )

    ax.set_ylim(0, max(successful, failed, 1) * 1.15)
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
        total_performance_checks = len(performance_results)
        pass_rate = (passes / total_performance_checks) * 100

        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(["Passed", "Failed"], [passes, failures])

        ax.set_title(f"Performance Threshold Results — {pass_rate:.1f}% Pass Rate")
        ax.set_ylabel("Number of checks")
        ax.grid(axis="y", alpha=0.3)

        for bar, count in zip(bars, [passes, failures]):
            ax.annotate(
                str(count),
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
            )

        ax.set_ylim(0, max(passes, failures, 1) * 1.15)
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
