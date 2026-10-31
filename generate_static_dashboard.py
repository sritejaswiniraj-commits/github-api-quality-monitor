"""
Build a self-contained static dashboard (dashboard/index.html) from
results/history.jsonl. No server, no framework — one portable HTML file that
hosts free on GitHub Pages and gives a shareable link.

Usage: python generate_static_dashboard.py
"""
import json
import statistics as stats
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HISTORY = Path("results/history.jsonl")
OUT = Path("dashboard/index.html")
THRESHOLD = 500

BG, CARD, BORDER = "#0d1117", "#161b22", "#30363d"
FG, MUTED, ACCENT = "#e6edf3", "#8b949e", "#58a6ff"
GOOD, WARN, BAD = "#3fb950", "#d29922", "#f85149"


def load():
    rows = []
    with open(HISTORY) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def rt(r):
    v = r.get("response_time_ms")
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def pct(vals, p):
    if not vals:
        return 0
    s = sorted(vals)
    k = (len(s) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def main():
    rows = load()
    if not rows:
        print("No data in", HISTORY)
        return
    for r in rows:
        try:
            r["_t"] = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
        except Exception:
            r["_t"] = None
    rows = [r for r in rows if r["_t"]]
    rows.sort(key=lambda r: r["_t"])

    total = len(rows)
    ok = sum(1 for r in rows if r.get("success") is True)
    success_rate = 100 * ok / total
    lats = [rt(r) for r in rows if rt(r) is not None]
    p50, p95, p99 = pct(lats, 50), pct(lats, 95), pct(lats, 99)
    avg = stats.mean(lats) if lats else 0
    over = sum(v > THRESHOLD for v in lats)
    perf = [r["performance_passed"] for r in rows if isinstance(r.get("performance_passed"), bool)]
    perf_rate = 100 * sum(perf) / len(perf) if perf else 0

    # hourly latency series
    hourly = defaultdict(list)
    for r in rows:
        v = rt(r)
        if v is not None:
            hourly[r["_t"].strftime("%Y-%m-%d %H:00")].append(v)
    series = [(h, stats.mean(v)) for h, v in sorted(hourly.items())]

    # failures by reason
    fails = defaultdict(int)
    for r in rows:
        if r.get("success") is not True:
            reason = (r.get("error") or "unknown").split(":")[0][:40]
            fails[reason] += 1

    span = f'{rows[0]["_t"].strftime("%b %d")} – {rows[-1]["_t"].strftime("%b %d, %Y")}'
    state_c = GOOD if success_rate >= 99 else WARN if success_rate >= 95 else BAD
    state_t = "HEALTHY" if success_rate >= 99 else "DEGRADED" if success_rate >= 95 else "UNHEALTHY"

    labels = json.dumps([h[-8:-3] if i % max(1, len(series) // 12) == 0 else ""
                         for i, (h, _) in enumerate(series)])
    data = json.dumps([round(v, 1) for _, v in series])
    hist_vals = json.dumps([round(v, 1) for v in lats])
    fail_rows = "".join(
        f'<tr><td>{k}</td><td style="text-align:right">{v}</td></tr>'
        for k, v in sorted(fails.items(), key=lambda x: -x[1])
    ) or '<tr><td colspan="2" style="color:var(--muted)">No failures recorded</td></tr>'

    recent = "".join(
        f'<tr><td>{r["_t"].strftime("%m-%d %H:%M")}</td>'
        f'<td>{r.get("status_code","—")}</td>'
        f'<td style="color:{GOOD if r.get("success") else BAD}">{"✓" if r.get("success") else "✗"}</td>'
        f'<td style="text-align:right">{rt(r):.0f}</td></tr>'
        for r in rows[-12:][::-1] if rt(r) is not None
    )

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitHub API Quality Monitor</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{{--bg:{BG};--card:{CARD};--border:{BORDER};--fg:{FG};--muted:{MUTED};
  --accent:{ACCENT};--good:{GOOD};--warn:{WARN};--bad:{BAD}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  padding:28px 20px;max-width:1040px;margin:0 auto}}
h1{{font-size:28px;margin:0;letter-spacing:-.01em}}
.pill{{display:inline-block;padding:4px 12px;border-radius:999px;font-size:12px;
  font-weight:700;margin-left:10px;vertical-align:middle;
  background:{state_c}22;color:{state_c};border:1px solid {state_c}55}}
.sub{{color:var(--muted);font-size:14px;margin:6px 0 26px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:26px}}
.kpi{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px}}
.kpi .l{{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em}}
.kpi .v{{font-size:30px;font-weight:700;margin-top:8px;line-height:1}}
.kpi .f{{color:var(--muted);font-size:12px;margin-top:8px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px}}
.card h2{{font-size:15px;margin:0 0 16px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:720px){{.grid2{{grid-template-columns:1fr}}}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
td,th{{padding:7px 8px;border-bottom:1px solid var(--border);text-align:left}}
th{{color:var(--muted);font-weight:500}}
.foot{{color:var(--muted);font-size:11px;margin-top:8px}}
</style></head><body>
<h1>GitHub API Quality Monitor <span class="pill">● {state_t}</span></h1>
<div class="sub">Availability, latency and performance of the GitHub REST API, observed from scheduled CI runs · {span} · {total:,} checks</div>

<div class="kpis">
  <div class="kpi"><div class="l">Success rate</div><div class="v" style="color:{state_c}">{success_rate:.1f}%</div><div class="f">{ok:,} ok · {total-ok} failed</div></div>
  <div class="kpi"><div class="l">Median latency</div><div class="v">{p50:.0f} ms</div><div class="f">avg {avg:.0f} ms</div></div>
  <div class="kpi"><div class="l">p95 / p99</div><div class="v">{p95:.0f}<span style="font-size:16px;color:var(--muted)"> / {p99:.0f} ms</span></div><div class="f">{over} over {THRESHOLD} ms</div></div>
  <div class="kpi"><div class="l">Perf pass rate</div><div class="v" style="color:{GOOD if perf_rate>=95 else WARN}">{perf_rate:.1f}%</div><div class="f">≤ {THRESHOLD} ms threshold</div></div>
</div>

<div class="card"><h2>Average latency over time</h2>
  <canvas id="line" height="90"></canvas>
  <div class="foot">Each point = mean latency per hour.</div>
</div>

<div class="grid2">
  <div class="card"><h2>Latency distribution</h2><canvas id="hist" height="150"></canvas></div>
  <div class="card"><h2>Failures by type</h2>
    <table><tr><th>Reason</th><th style="text-align:right">Count</th></tr>{fail_rows}</table>
  </div>
</div>

<div class="card"><h2>Recent runs</h2>
  <table><tr><th>Time (UTC)</th><th>Status</th><th>Result</th><th style="text-align:right">Latency</th></tr>{recent}</table>
</div>

<div class="foot">Note: measurements reflect what scheduled GitHub Actions runs observed from one environment — not a guarantee of how every user or region experiences the API.</div>

<script>
const g=(id)=>document.getElementById(id).getContext('2d');
new Chart(g('line'),{{type:'line',data:{{labels:{labels},
  datasets:[{{data:{data},borderColor:'{ACCENT}',backgroundColor:'rgba(88,166,255,.08)',
    fill:true,tension:.3,pointRadius:0,borderWidth:2}}]}},
  options:{{plugins:{{legend:{{display:false}}}},scales:{{
    x:{{grid:{{color:'{BORDER}'}},ticks:{{color:'{MUTED}',maxRotation:0,autoSkip:true}}}},
    y:{{grid:{{color:'{BORDER}'}},ticks:{{color:'{MUTED}'}},title:{{display:true,text:'ms',color:'{MUTED}'}}}}}}}}}});
// simple histogram
const vals={hist_vals};const bins=24;const mn=Math.min(...vals),mx=Math.max(...vals);
const w=(mx-mn)/bins||1;const counts=new Array(bins).fill(0);
vals.forEach(v=>{{let i=Math.min(bins-1,Math.floor((v-mn)/w));counts[i]++;}});
const blabels=counts.map((_,i)=>Math.round(mn+i*w));
new Chart(g('hist'),{{type:'bar',data:{{labels:blabels,
  datasets:[{{data:counts,backgroundColor:'{ACCENT}'}}]}},
  options:{{plugins:{{legend:{{display:false}}}},scales:{{
    x:{{grid:{{display:false}},ticks:{{color:'{MUTED}',maxTicksLimit:8}},title:{{display:true,text:'ms',color:'{MUTED}'}}}},
    y:{{grid:{{color:'{BORDER}'}},ticks:{{color:'{MUTED}'}}}}}}}}}});
</script>
</body></html>"""

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html)
    print(f"Wrote {OUT}  ({total} records, {success_rate:.1f}% success, p95={p95:.0f}ms)")


if __name__ == "__main__":
    main()
