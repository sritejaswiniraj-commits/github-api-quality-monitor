
import json

from datetime import date, datetime
from pathlib import Path
from statistics import mean
from dashboard_utils import calculate_metrics, load_history, valid_response_time
import plotly.express as px
import streamlit as st


HISTORY_FILE = Path("results/history.jsonl")
PERFORMANCE_THRESHOLD_MS = 500


st.set_page_config(
    page_title="GitHub API Quality Monitor",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def load_history(history_file: str, modified_time: float):
    """Load valid JSON object records from JSONL history."""
    records = []

    path = Path(history_file)
    if not path.exists():
        return records, []

    warnings = []
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
                timestamp = record.get("timestamp")
                try:
                    parsed_timestamp = datetime.fromisoformat(
                        timestamp.replace("Z", "+00:00")
                    )
                except (AttributeError, ValueError):
                    parsed_timestamp = None

                record["_parsed_timestamp"] = parsed_timestamp
                records.append(record)

    return records, warnings


def valid_number(value):
    """Accept numeric values but exclude booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def response_time(record):
    value = record.get("response_time_ms")
    return value if valid_number(value) else None


def format_timestamp(value):
    if not isinstance(value, datetime):
        return "Unknown"
    return value.strftime("%Y-%m-%d %H:%M:%S")


st.title("📊 GitHub API Quality Monitor")
st.caption(
    "Interactive monitoring dashboard for API availability, "
    "response times, performance, and rate limits."
)

if not HISTORY_FILE.exists():
    st.warning(
        "No monitoring history found. Run `python monitor.py` "
        "to create results/history.jsonl."
    )
    st.stop()

records, warnings = load_history(HISTORY_FILE)

if warnings:
    with st.expander(f"Data warnings ({len(warnings)})"):
        for warning in warnings:
            st.write(warning)

if not records:
    st.info("No valid monitoring records are available yet.")
    st.stop()

# Sort by parsed timestamp; records with unknown timestamps appear first.
records.sort(
    key=lambda record: (
        record.get("_parsed_timestamp") is not None,
        record.get("_parsed_timestamp") or datetime.min,
    )
)

st.sidebar.header("Dashboard filters")

valid_dates = [
    record["_parsed_timestamp"].date()
    for record in records
    if record.get("_parsed_timestamp") is not None
]

filtered_records = records[:]

if valid_dates:
    earliest = min(valid_dates)
    latest = max(valid_dates)
    selected_dates = st.sidebar.date_input(
        "Date range",
        value=(earliest, latest),
        min_value=earliest,
        max_value=latest,
    )

    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        filtered_records = [
            record
            for record in filtered_records
            if (
                record.get("_parsed_timestamp") is not None
                and start_date
                <= record["_parsed_timestamp"].date()
                <= end_date
            )
        ]

run_limit = st.sidebar.selectbox(
    "Records to display",
    options=["All", "Last 10", "Last 25", "Last 50"],
    index=0,
)

if run_limit != "All":
    limit = int(run_limit.split()[-1])
    filtered_records = filtered_records[-limit:]

if not filtered_records:
    st.info("No monitoring records match the selected filters.")
    st.stop()

metrics = calculate_metrics(filtered_records)

total_checks = metrics["total_checks"]
successful_checks = metrics["successful_checks"]
failed_checks = metrics["failed_checks"]
success_rate = metrics["success_rate"]

response_times = [
    valid_response_time(record)
    for record in filtered_records
    if valid_response_time(record) is not None
]

performance_results = [
    record["performance_passed"]
    for record in filtered_records
    if isinstance(record.get("performance_passed"), bool)
]

average_response = metrics["average_response_time"]
fastest_response = metrics["fastest_response_time"]
slowest_response = metrics["slowest_response_time"]
performance_pass_rate = metrics["performance_pass_rate"]

# KPI cards
st.subheader("Monitoring overview")
col1, col2, col3, col4 = st.columns(4)

col1.metric("API success rate", f"{success_rate:.1f}%")
col2.metric(
    "Average response time",
    f"{average_response:.1f} ms" if average_response is not None else "N/A",
)
col3.metric(
    "Performance pass rate",
    (
        f"{performance_pass_rate:.1f}%"
        if performance_pass_rate is not None
        else "N/A"
    ),
)
col4.metric("Monitoring runs", total_checks)

st.caption(
    f"{successful_checks} successful · {failed_checks} unsuccessful · "
    f"{len(performance_results)} records with performance results"
)

# Response-time chart
st.subheader("Response time over time")

timed_records = [
    record
    for record in filtered_records
    if response_time(record) is not None
]

if timed_records:
    chart_records = [
        {
            "Run": index,
            "Timestamp": format_timestamp(record.get("_parsed_timestamp")),
            "Response time (ms)": response_time(record),
            "Threshold (ms)": PERFORMANCE_THRESHOLD_MS,
        }
        for index, record in enumerate(timed_records, start=1)
    ]

    fig = px.line(
        chart_records,
        x="Run",
        y="Response time (ms)",
        markers=True,
        hover_data=["Timestamp"],
        title="API response time by monitoring run",
    )
    fig.add_scatter(
        x=[item["Run"] for item in chart_records],
        y=[PERFORMANCE_THRESHOLD_MS] * len(chart_records),
        mode="lines",
        name=f"Threshold ({PERFORMANCE_THRESHOLD_MS} ms)",
        line={"dash": "dash"},
    )
    fig.update_layout(
        xaxis_title="Monitoring run",
        yaxis_title="Response time (ms)",
        legend_title="Metric",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No valid response-time measurements in this selection.")

if response_times:
    a, b, c = st.columns(3)
    a.metric("Fastest response", f"{fastest_response:.1f} ms")
    b.metric("Slowest response", f"{slowest_response:.1f} ms")
    c.metric(
        "Over 500 ms",
        sum(value > PERFORMANCE_THRESHOLD_MS for value in response_times),
    )

# API availability chart
st.subheader("API check results")

result_counts = [
    {"Result": "Successful", "Checks": successful_checks},
    {"Result": "Unsuccessful", "Checks": failed_checks},
]

fig_results = px.bar(
    result_counts,
    x="Result",
    y="Checks",
    color="Result",
    text="Checks",
    title="Successful versus unsuccessful API checks",
)
fig_results.update_layout(showlegend=False)
st.plotly_chart(fig_results, use_container_width=True)

# Performance chart
st.subheader("Performance threshold results")

if performance_results:
    passed = sum(performance_results)
    failed = len(performance_results) - passed

    performance_counts = [
        {"Result": "Passed", "Checks": passed},
        {"Result": "Failed", "Checks": failed},
    ]

    fig_performance = px.bar(
        performance_counts,
        x="Result",
        y="Checks",
        color="Result",
        text="Checks",
        title="Checks against the performance threshold",
    )
    fig_performance.update_layout(showlegend=False)
    st.plotly_chart(fig_performance, use_container_width=True)
else:
    st.info(
        "Performance results are unavailable for these records. "
        "Older records may not contain performance measurements."
    )

# Recent history table
st.subheader("Monitoring history")

table_records = []
for record in reversed(filtered_records):
    table_records.append(
        {
            "Timestamp": format_timestamp(record.get("_parsed_timestamp")),
            "Status code": record.get("status_code", "N/A"),
            "API result": (
                "Success"
                if record.get("success") is True
                else "Failure"
            ),
            "Response time (ms)": response_time(record),
            "Performance": (
                "Pass"
                if record.get("performance_passed") is True
                else "Fail"
                if record.get("performance_passed") is False
                else "N/A"
            ),
            "Rate limit remaining": record.get("rate_limit_remaining", "N/A"),
            "Error": record.get("error") or "",
        }
    )

st.dataframe(
    table_records,
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "Data source: results/history.jsonl · "
    "Dashboard metrics are calculated from the filtered records."
)
