
import json
from pathlib import Path
from statistics import mean


HISTORY_FILE = Path("results/history.jsonl")


def valid_response_time(record):
    value = record.get("response_time_ms")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def calculate_success_rate(records):
    if not records:
        return None
    successful = sum(record.get("success") is True for record in records)
    return successful / len(records) * 100


def describe_trend(earlier, later, higher_is_better=True):
    if later == earlier:
        return "unchanged"

    improved = later > earlier if higher_is_better else later < earlier
    return "improving" if improved else "worsening"


def report_trends(records):
    print("\nMonitoring Trends")
    print("-----------------")

    if len(records) < 2:
        print("Not enough history to compare trends (need at least 2 records).")
        return

    # Compare the earlier and later halves in file order.
    midpoint = len(records) // 2
    earlier_records = records[:midpoint]
    later_records = records[midpoint:]

    earlier_rate = calculate_success_rate(earlier_records)
    later_rate = calculate_success_rate(later_records)

    print(f"Earlier success rate: {earlier_rate:.2f}%")
    print(f"Later success rate: {later_rate:.2f}%")
    print(
        "Success-rate trend: "
        f"{describe_trend(earlier_rate, later_rate)}"
    )

    earlier_times = [
        value
        for record in earlier_records
        if (value := valid_response_time(record)) is not None
    ]
    later_times = [
        value
        for record in later_records
        if (value := valid_response_time(record)) is not None
    ]

    if earlier_times and later_times:
        earlier_average = mean(earlier_times)
        later_average = mean(later_times)

        print(f"Earlier average response time: {earlier_average:.2f} ms")
        print(f"Later average response time: {later_average:.2f} ms")
        print(
            "Response-time trend: "
            f"{describe_trend(earlier_average, later_average, False)}"
        )
    else:
        print("Response-time trend unavailable: insufficient response-time data.")

    earlier_performance = [
        record["performance_passed"]
        for record in earlier_records
        if isinstance(record.get("performance_passed"), bool)
    ]
    later_performance = [
        record["performance_passed"]
        for record in later_records
        if isinstance(record.get("performance_passed"), bool)
    ]

    if earlier_performance and later_performance:
        earlier_pass_rate = (
            sum(earlier_performance) / len(earlier_performance) * 100
        )
        later_pass_rate = (
            sum(later_performance) / len(later_performance) * 100
        )

        print(f"Earlier performance pass rate: {earlier_pass_rate:.2f}%")
        print(f"Later performance pass rate: {later_pass_rate:.2f}%")
        print(
            "Performance trend: "
            f"{describe_trend(earlier_pass_rate, later_pass_rate)}"
        )
    else:
        print(
            "Performance trend unavailable: "
            "both periods need performance data."
        )


def analyze_history(history_file=None):
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
        value
        for record in records
        if (value := valid_response_time(record)) is not None
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
        performance_failures = len(performance_results) - performance_passes
        performance_pass_rate = (
            performance_passes / len(performance_results) * 100
        )

        print(f"Performance checks: {len(performance_results)}")
        print(f"Performance passes: {performance_passes}")
        print(f"Performance failures: {performance_failures}")
        print(f"Performance pass rate: {performance_pass_rate:.2f}%")
    else:
        print("Performance data unavailable.")

    report_trends(records)


if __name__ == "__main__":
    analyze_history()

