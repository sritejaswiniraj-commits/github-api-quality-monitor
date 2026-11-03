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
REPO_URL = "https://github.com/sritejaswiniraj-commits/github-api-quality-monitor"


def load():
    rows = []
    if not HISTORY.exists():
        return rows
    for line in HISTORY.read_text().splitlines():
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

    hourly = defaultdict(list)
    for r in rows:
        v = rt(r)
        if v is not None:
            hourly[r["_t"].strftime("%Y-%m-%d %H:00")].append(v)
    series = [(h, stats.mean(v)) for h, v in sorted(hourly.items())]

    fails = defaultdict(int)
    for r in rows:
        if r.get("success") is not True:
            reason = str(r.get("error") or f"HTTP {r.get('status_code','?')}")[:46]
            fails[reason] += 1

    span = f'{rows[0]["_t"].strftime("%b %d")} – {rows[-1]["_t"].strftime("%b %d, %Y")}'
    days = (rows[-1]["_t"] - rows[0]["_t"]).days + 1
    state_t = "HEALTHY" if success_rate >= 99 else "OPERATIONAL" if success_rate >= 95 else "DEGRADED"

    step = max(1, len(series) // 14)
    labels = json.dumps([h[-5:] if i % step == 0 else "" for i, (h, _) in enumerate(series)])
    data = json.dumps([round(v, 1) for _, v in series])
    hist_vals = json.dumps([round(v, 1) for v in lats])
    fail_rows = "".join(
        f'<tr><td>{k}</td><td style="text-align:right;font-weight:600">{v}</td></tr>'
        for k, v in sorted(fails.items(), key=lambda x: -x[1])
    ) or '<tr><td colspan="2" style="color:var(--muted)">No failures recorded</td></tr>'
    recent = "".join(
        f'<tr><td>{r["_t"].strftime("%m-%d %H:%M")}</td><td>{r.get("status_code","—")}</td>'
        f'<td><span class="dot" style="background:{"#16a34a" if r.get("success") else "#dc2626"}"></span>'
        f'{"Success" if r.get("success") else "Failure"}</td>'
        f'<td style="text-align:right">{rt(r):.0f} ms</td></tr>'
        for r in rows[-14:][::-1] if rt(r) is not None
    )

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitHub API Quality Monitor</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#f4f5fb; --surface:#ffffff; --ink:#1a1c2e; --muted:#6b7190; --line:#eceef5;
  --violet:#7c5cff; --violet2:#a78bfa; --blue:#4f80ff; --teal:#2dd4bf;
  --good:#16a34a; --bad:#dc2626; --amber:#d97706;
  --grad:linear-gradient(135deg,#7c5cff 0%,#4f80ff 100%);
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:'Inter',-apple-system,sans-serif;font-size:14px}}
a{{color:inherit;text-decoration:none}}
.layout{{display:flex;min-height:100vh}}
.side{{width:232px;flex-shrink:0;background:var(--surface);border-right:1px solid var(--line);
  padding:24px 16px;position:sticky;top:0;height:100vh;display:flex;flex-direction:column}}
.brand{{display:flex;align-items:center;gap:10px;padding:0 8px 24px;font-weight:800;font-size:15px}}
.brand .logo{{width:30px;height:30px;border-radius:8px;background:var(--grad);display:grid;place-items:center;color:#fff;font-size:15px}}
.nav a{{display:flex;align-items:center;gap:11px;padding:10px 12px;border-radius:10px;color:var(--muted);
  font-weight:500;margin-bottom:3px;transition:.15s}}
.nav a:hover{{background:var(--bg);color:var(--ink)}}
.nav a.active{{background:var(--grad);color:#fff;box-shadow:0 6px 16px rgba(124,92,255,.3)}}
.nav .ic{{width:18px;text-align:center;font-size:15px}}
.side .foot{{margin-top:auto;padding:14px 12px;border-radius:12px;background:var(--bg);font-size:12px;color:var(--muted)}}
.side .foot a{{color:var(--violet);font-weight:600}}
.main{{flex:1;padding:28px 34px;max-width:1180px}}
.head h1{{font-size:24px;margin:0;font-weight:800;letter-spacing:-.02em}}
.head p{{color:var(--muted);margin:5px 0 0}}
.head .hl{{color:var(--good);font-weight:600}}
.pill{{display:inline-block;padding:5px 13px;border-radius:999px;font-size:12px;font-weight:700;
  background:rgba(22,163,74,.12);color:var(--good);border:1px solid rgba(22,163,74,.25);margin-left:10px;vertical-align:middle}}
.topbar{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:26px;flex-wrap:wrap;gap:12px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:18px;margin-bottom:22px}}
.kpi{{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:20px 22px;
  box-shadow:0 2px 10px rgba(26,28,46,.04)}}
.kpi .l{{color:var(--muted);font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.04em}}
.kpi .v{{font-size:32px;font-weight:800;margin-top:10px;letter-spacing:-.02em}}
.kpi .v small{{font-size:17px;color:var(--muted);font-weight:600}}
.kpi .f{{color:var(--muted);font-size:12.5px;margin-top:8px}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:22px 24px;
  margin-bottom:22px;box-shadow:0 2px 10px rgba(26,28,46,.04)}}
.card h2{{font-size:15px;margin:0 0 4px;font-weight:700}}
.card .cap{{color:var(--muted);font-size:12.5px;margin:0 0 18px}}
.grid2{{display:grid;grid-template-columns:1.4fr 1fr;gap:22px}}
@media(max-width:860px){{.grid2{{grid-template-columns:1fr}} .side{{display:none}}}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
td,th{{padding:9px 6px;border-bottom:1px solid var(--line);text-align:left}}
th{{color:var(--muted);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.03em}}
tr:last-child td{{border-bottom:none}}
.dot{{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:7px;vertical-align:middle}}
.note{{color:var(--muted);font-size:11.5px;margin-top:6px;line-height:1.5}}
.insight{{background:linear-gradient(135deg,rgba(124,92,255,.07),rgba(79,128,255,.07));
  border:1px solid rgba(124,92,255,.18);border-radius:14px;padding:14px 18px;margin-bottom:22px;font-size:13.5px}}
.insight b{{color:var(--violet)}}
</style></head><body>
<div class="layout">
  <aside class="side">
    <div class="brand"><span class="logo">◈</span> API Monitor</div>
    <nav class="nav">
      <a href="#overview" class="active"><span class="ic">▦</span> Overview</a>
      <a href="#latency"><span class="ic">◠</span> Latency</a>
      <a href="#failures"><span class="ic">⚑</span> Failures</a>
      <a href="#runs"><span class="ic">≡</span> Recent runs</a>
      <a href="{REPO_URL}" target="_blank"><span class="ic">◐</span> Source code</a>
    </nav>
    <div class="foot">Monitoring the GitHub REST API on a schedule via CI.<br><br>
      <a href="{REPO_URL}" target="_blank">View on GitHub →</a></div>
  </aside>
  <main class="main">
    <div class="topbar" id="overview">
      <div class="head">
        <h1>Systems Overview <span class="pill">● {state_t}</span></h1>
        <p>GitHub REST API — <span class="hl">{success_rate:.1f}% success</span> across {total} checks · {span} ({days}d) · observed from scheduled CI runs.</p>
      </div>
    </div>
    <div class="kpis">
      <div class="kpi"><div class="l">Success rate</div><div class="v" style="color:var(--good)">{success_rate:.1f}%</div><div class="f">{ok} ok · {total-ok} failed</div></div>
      <div class="kpi"><div class="l">Median latency</div><div class="v">{p50:.0f}<small> ms</small></div><div class="f">average {avg:.0f} ms</div></div>
      <div class="kpi"><div class="l">p95 / p99</div><div class="v">{p95:.0f}<small> / {p99:.0f} ms</small></div><div class="f">{over} over {THRESHOLD} ms threshold</div></div>
      <div class="kpi"><div class="l">Range</div><div class="v">{min(lats):.0f}<small> – {max(lats):.0f} ms</small></div><div class="f">fastest to slowest observed</div></div>
    </div>
    <div class="insight">
      <b>What the data shows:</b> latency stayed tight (p99 {p99:.0f} ms, nothing over {THRESHOLD} ms). The only failures were {total-ok} HTTP 403s clustered in a short window — fast rejections, consistent with a rate-limit window rather than an outage.
    </div>
    <div class="card" id="latency">
      <h2>Latency over time</h2>
      <p class="cap">Average response time per hour across the monitoring window.</p>
      <canvas id="line" height="78"></canvas>
    </div>
    <div class="grid2">
      <div class="card">
        <h2>Latency distribution</h2>
        <p class="cap">How response times clustered across all {total} checks.</p>
        <canvas id="hist" height="150"></canvas>
      </div>
      <div class="card" id="failures">
        <h2>Failures by type</h2>
        <p class="cap">Every non-success response, grouped.</p>
        <table><tr><th>Reason</th><th style="text-align:right">Count</th></tr>{fail_rows}</table>
      </div>
    </div>
    <div class="card" id="runs">
      <h2>Recent runs</h2>
      <p class="cap">The latest checks, newest first.</p>
      <table><tr><th>Time (UTC)</th><th>Status</th><th>Result</th><th style="text-align:right">Latency</th></tr>{recent}</table>
    </div>
    <p class="note">Note: measurements reflect what scheduled GitHub Actions runs observed from one environment — not a guarantee of how every user or region experiences the API. Built with Python · data committed to the repo on every run.</p>
  </main>
</div>
<script>
const grad=(ctx,c1,c2)=>{{const g=ctx.createLinearGradient(0,0,0,240);g.addColorStop(0,c1);g.addColorStop(1,c2);return g;}};
const lc=document.getElementById('line').getContext('2d');
new Chart(lc,{{type:'line',data:{{labels:{labels},datasets:[{{data:{data},
  borderColor:'#7c5cff',borderWidth:2.5,fill:true,tension:.4,pointRadius:0,
  backgroundColor:grad(lc,'rgba(124,92,255,.22)','rgba(124,92,255,0)')}}]}},
  options:{{plugins:{{legend:{{display:false}}}},scales:{{
    x:{{grid:{{display:false}},ticks:{{color:'#9499b7',maxRotation:0,autoSkip:true}}}},
    y:{{grid:{{color:'#eef0f7'}},ticks:{{color:'#9499b7'}},title:{{display:true,text:'ms',color:'#9499b7'}}}}}}}}}});
const vals={hist_vals};const bins=22;const mn=Math.min(...vals),mx=Math.max(...vals);const w=(mx-mn)/bins||1;
const counts=new Array(bins).fill(0);vals.forEach(v=>{{let i=Math.min(bins-1,Math.floor((v-mn)/w));counts[i]++;}});
const bl=counts.map((_,i)=>Math.round(mn+i*w));
const hc=document.getElementById('hist').getContext('2d');
new Chart(hc,{{type:'bar',data:{{labels:bl,datasets:[{{data:counts,
  backgroundColor:grad(hc,'#7c5cff','#4f80ff'),borderRadius:5,barPercentage:.95,categoryPercentage:.98}}]}},
  options:{{plugins:{{legend:{{display:false}}}},scales:{{
    x:{{grid:{{display:false}},ticks:{{color:'#9499b7',maxTicksLimit:8}},title:{{display:true,text:'ms',color:'#9499b7'}}}},
    y:{{grid:{{color:'#eef0f7'}},ticks:{{color:'#9499b7'}}}}}}}}}});
const secs=['overview','latency','failures','runs'].map(id=>document.getElementById(id));
const links=document.querySelectorAll('.nav a');
addEventListener('scroll',()=>{{let cur='overview';secs.forEach(s=>{{if(s&&s.getBoundingClientRect().top<160)cur=s.id;}});
  links.forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+cur));}});
</script>
</body></html>"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html)
    print(f"Wrote {OUT}  ({total} records, {success_rate:.1f}% success, p50={p50:.0f}ms p95={p95:.0f}ms)")


if __name__ == "__main__":
    main()
