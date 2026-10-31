from datetime import datetime
from pathlib import Path

from dashboard_utils import calculate_metrics, load_history, valid_response_time
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

HISTORY_FILE = Path("results/history.jsonl")
PERFORMANCE_THRESHOLD_MS = 500

# ---- palette (kept in one place so charts and CSS stay consistent) ----
BG = "#0d1117"
CARD = "#161b22"
BORDER = "#30363d"
FG = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#58a6ff"
GOOD = "#3fb950"
WARN = "#d29922"
BAD = "#f85149"

st.set_page_config(
    page_title="GitHub API Quality Monitor",
    page_icon="📊",
    layout="wide",
)

# ---- global CSS: turns default Streamlit into a deliberate monitoring UI ----
st.markdown(
    f"""
    <style>
      .stApp {{ background:{BG}; }}
      #MainMenu, footer, header {{ visibility:hidden; }}
      .block-container {{ padding-top:2.2rem; max-width:1200px; }}
      h1, h2, h3 {{ color:{FG}; letter-spacing:-0.01em; }}
      .hero-title {{ font-size:30px; font-weight:700; margin:0; }}
      .hero-sub {{ color:{MUTED}; font-size:14px; margin-top:4px; }}
      .status-pill {{
        display:inline-block; padding:4px 12px; border-radius:999px;
        font-size:12px; font-weight:600; margin-left:12px; vertical-align:middle;
      }}
      /* KPI cards */
      .kpi {{
        background:{CARD}; border:1px solid {BORDER}; border-radius:12px;
        padding:18px 20px; height:100%;
      }}
      .kpi .label {{ color:{MUTED}; font-size:12px; text-transform:uppercase;
        letter-spacing:.05em; margin-bottom:8px; }}
      .kpi .value {{ font-size:30px; font-weight:700; line-height:1; }}
      .kpi .foot {{ color:{MUTED}; font-size:12px; margin-top:8px; }}
      hr {{ border-color:{BORDER}; }}
      section[data-testid="stSidebar"] {{ background:{CARD}; border-right:1px solid {BORDER}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

if not HISTORY_FILE.exists():
    st.warning("No monitoring history found. Run `python monitor.py` to create results/history.jsonl.")
    st.stop()

records, warnings = load_history(HISTORY_FILE)

for record in records:
    ts = record.get("timestamp")
    try:
        record["_parsed_timestamp"] = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        record["_parsed_timestamp"] = None

if not records:
    st.info("No valid monitoring records are available yet.")
    st.stop()

records.sort(key=lambda r: (r.get("_parsed_timestamp") is not None,
                            r.get("_parsed_timestamp") or datetime.min))

# ---- sidebar filters (unchanged logic) ----
st.sidebar.header("Filters")
valid_dates = [r["_parsed_timestamp"].date() for r in records if r.get("_parsed_timestamp")]
filtered = records[:]
if valid_dates:
    earliest, latest = min(valid_dates), max(valid_dates)
    sel = st.sidebar.date_input("Date range", value=(earliest, latest),
                                min_value=earliest, max_value=latest)
    if isinstance(sel, tuple) and len(sel) == 2:
        s, e = sel
        filtered = [r for r in filtered if r.get("_parsed_timestamp")
                    and s <= r["_parsed_timestamp"].date() <= e]
run_limit = st.sidebar.selectbox("Records to display", ["All", "Last 10", "Last 25", "Last 50"], 0)
if run_limit != "All":
    filtered = filtered[-int(run_limit.split()[-1]):]
if not filtered:
    st.info("No monitoring records match the selected filters.")
    st.stop()

m = calculate_metrics(filtered)
response_times = [v for r in filtered if (v := valid_response_time(r)) is not None]
perf_results = [r["performance_passed"] for r in filtered
                if isinstance(r.get("performance_passed"), bool)]
success_rate = m["success_rate"]

# ---- header with live status pill ----
if success_rate is None:
    pill_c, pill_t = MUTED, "NO DATA"
elif success_rate >= 99:
    pill_c, pill_t = GOOD, "HEALTHY"
elif success_rate >= 95:
    pill_c, pill_t = WARN, "DEGRADED"
else:
    pill_c, pill_t = BAD, "UNHEALTHY"

st.markdown(
    f"""
    <div class="hero-title">GitHub API Quality Monitor
      <span class="status-pill" style="background:{pill_c}22;color:{pill_c};border:1px solid {pill_c}55">
      ● {pill_t}</span></div>
    <div class="hero-sub">Availability, latency, performance and rate-limit monitoring of the GitHub REST API,
      observed from scheduled CI runs.</div>
    """,
    unsafe_allow_html=True,
)
st.write("")


def kpi(col, label, value, foot="", color=FG):
    col.markdown(
        f'<div class="kpi"><div class="label">{label}</div>'
        f'<div class="value" style="color:{color}">{value}</div>'
        f'<div class="foot">{foot}</div></div>',
        unsafe_allow_html=True,
    )


# ---- KPI row ----
c1, c2, c3, c4 = st.columns(4)
kpi(c1, "Success rate",
    f"{success_rate:.1f}%" if success_rate is not None else "N/A",
    f"{m['successful_checks']} ok · {m['failed_checks']} failed",
    GOOD if (success_rate or 0) >= 99 else WARN if (success_rate or 0) >= 95 else BAD)
kpi(c2, "Avg latency",
    f"{m['average_response_time']:.0f} ms" if m["average_response_time"] else "N/A",
    f"fastest {m['fastest_response_time']:.0f} · slowest {m['slowest_response_time']:.0f} ms"
    if response_times else "")
over = sum(v > PERFORMANCE_THRESHOLD_MS for v in response_times)
kpi(c3, "Perf pass rate",
    f"{m['performance_pass_rate']:.1f}%" if m["performance_pass_rate"] is not None else "N/A",
    f"{over} over {PERFORMANCE_THRESHOLD_MS} ms",
    GOOD if (m["performance_pass_rate"] or 0) >= 95 else WARN)
kpi(c4, "Monitoring runs", f"{m['total_checks']:,}",
    "one check per scheduled run")

st.write("")
st.markdown("---")

# ---- shared Plotly styling ----
def style_fig(fig, height=330):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=FG, size=12), margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(gridcolor=BORDER, zeroline=False),
        yaxis=dict(gridcolor=BORDER, zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


# ---- latency over time (the main chart) ----
st.subheader("Latency over time")
timed = [r for r in filtered if valid_response_time(r) is not None]
if timed:
    xs = [r["_parsed_timestamp"] for r in timed]
    ys = [valid_response_time(r) for r in timed]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=ACCENT, width=2),
                             fill="tozeroy", fillcolor=f"rgba(88,166,255,0.08)", name="Latency"))
    fig.add_hline(y=PERFORMANCE_THRESHOLD_MS, line_dash="dash", line_color=WARN,
                  annotation_text=f"{PERFORMANCE_THRESHOLD_MS} ms threshold",
                  annotation_font_color=WARN)
    style_fig(fig, 360)
    fig.update_layout(xaxis_title=None, yaxis_title="ms")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No valid latency measurements in this selection.")

# ---- two columns: availability donut + latency distribution ----
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Availability")
    ok, fail = m["successful_checks"], m["failed_checks"]
    donut = go.Figure(go.Pie(
        values=[ok, fail], labels=["Successful", "Failed"], hole=0.68,
        marker=dict(colors=[GOOD, BAD]), textinfo="none", sort=False))
    donut.update_layout(
        annotations=[dict(text=f"{success_rate:.1f}%" if success_rate is not None else "N/A",
                          x=0.5, y=0.5, font=dict(size=26, color=FG), showarrow=False)],
        showlegend=True)
    style_fig(donut, 300)
    st.plotly_chart(donut, use_container_width=True)

with col_r:
    st.subheader("Latency distribution")
    if response_times:
        hist = px.histogram(x=response_times, nbins=30)
        hist.update_traces(marker_color=ACCENT, marker_line_width=0)
        hist.add_vline(x=PERFORMANCE_THRESHOLD_MS, line_dash="dash", line_color=WARN)
        style_fig(hist, 300)
        hist.update_layout(xaxis_title="ms", yaxis_title="count")
        st.plotly_chart(hist, use_container_width=True)
    else:
        st.info("No latency data.")

st.markdown("---")

# ---- history table ----
st.subheader("Recent monitoring runs")
table = []
for r in reversed(filtered[-50:]):
    rt = valid_response_time(r)
    table.append({
        "Timestamp": r["_parsed_timestamp"].strftime("%Y-%m-%d %H:%M") if r.get("_parsed_timestamp") else "Unknown",
        "Status": r.get("status_code", "N/A"),
        "Result": "✓ Success" if r.get("success") is True else "✗ Failure",
        "Latency (ms)": f"{rt:.0f}" if rt is not None else "—",
        "Perf": "Pass" if r.get("performance_passed") is True else "Fail" if r.get("performance_passed") is False else "—",
        "Rate limit left": r.get("rate_limit_remaining", "N/A"),
        "Error": r.get("error") or "",
    })
st.dataframe(table, use_container_width=True, hide_index=True)

st.caption("Data source: results/history.jsonl · metrics computed from the filtered records.")
