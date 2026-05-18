#!/usr/bin/env python
"""Generate benchmark charts from test results.

Run *after* the benchmark tests to turn ``reports/benchmark_results.json``
into:
  - ``reports/benchmark_chart.svg``  — bar chart of p95 latencies per operation
  - ``reports/benchmark_report.html`` — self-contained HTML with all charts
  - Terminal output via plotext (optional, only if plotext is installed)

Usage
-----
    python scripts/generate_test_graphs.py

The script first re-runs the benchmark tests (if the JSON file is absent
or stale) and then generates the charts.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
RESULTS_FILE = REPORTS / "benchmark_results.json"

# ── Colour palette ─────────────────────────────────────────────────────
COLOURS = [
    "#2563EB",  # blue
    "#16A34A",  # green
    "#DC2626",  # red
    "#D97706",  # amber
    "#7C3AED",  # violet
    "#0891B2",  # cyan
    "#DB2777",  # pink
    "#65A30D",  # lime
]


# ── Run benchmarks if results are missing ──────────────────────────────


def _run_benchmarks() -> None:
    print("[graphs] Running benchmark tests to collect results …")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "app/tests/benchmarks/",
            "-v",
            "--tb=short",
            "-q",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("[graphs] WARNING: some benchmark tests failed; charts may be partial.")


# ── Load results ───────────────────────────────────────────────────────


def _load_results() -> dict:
    if not RESULTS_FILE.exists():
        print("[graphs] No results file found — re-running benchmarks …")
        _run_benchmarks()
    if not RESULTS_FILE.exists():
        print("[graphs] ERROR: results file still missing after run. Exiting.")
        sys.exit(1)
    return json.loads(RESULTS_FILE.read_text())


# ── Terminal chart (plotext) ───────────────────────────────────────────


def _print_terminal_chart(results: dict) -> None:
    try:
        import plotext as plt  # type: ignore[import]
    except ImportError:
        print("[graphs] plotext not installed — skipping terminal chart.")
        return

    labels = list(results.keys())
    p50 = [results[k]["p50_ms"] for k in labels]
    p95 = [results[k]["p95_ms"] for k in labels]
    p99 = [results[k]["p99_ms"] for k in labels]

    plt.clf()
    plt.title("OPD-Vertex Benchmark: p50 / p95 / p99 latencies (ms)")
    plt.bar(labels, p50, label="p50", color="blue")
    plt.bar(labels, p95, label="p95", color="green")
    plt.bar(labels, p99, label="p99", color="red")
    plt.xlabel("Operation")
    plt.ylabel("Latency (ms)")
    plt.show()


# ── SVG bar chart ──────────────────────────────────────────────────────


def _make_svg_bar_chart(
    results: dict,
    metric: str = "p95_ms",
    title: str = "p95 Latency per Operation (ms)",
) -> str:
    labels = list(results.keys())
    values = [results[k][metric] for k in labels]

    width, height = 900, 450
    margin = {"top": 60, "right": 40, "bottom": 130, "left": 70}
    chart_w = width - margin["left"] - margin["right"]
    chart_h = height - margin["top"] - margin["bottom"]

    max_val = max(values) if values else 1
    y_max = max_val * 1.2 or 1

    bar_count = len(labels)
    bar_gap = 12
    bar_w = (chart_w - bar_gap * (bar_count + 1)) / bar_count

    def _x(i: int) -> float:
        return margin["left"] + bar_gap * (i + 1) + bar_w * i

    def _y_top(v: float) -> float:
        return margin["top"] + chart_h * (1 - v / y_max)

    def _bar_h(v: float) -> float:
        return chart_h * (v / y_max)

    bars = []
    for i, (label, val) in enumerate(zip(labels, values)):
        colour = COLOURS[i % len(COLOURS)]
        x = _x(i)
        yt = _y_top(val)
        bh = _bar_h(val)
        lx = x + bar_w / 2
        ly = height - margin["bottom"] + 18
        bars.append(
            f'<rect x="{x:.1f}" y="{yt:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" '
            f'fill="{colour}" rx="4"/>'
        )
        bars.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{yt - 5:.1f}" text-anchor="middle" '
            f'font-size="11" fill="#111">{val:.2f}</text>'
        )
        # Angled label
        bars.append(
            f'<text transform="rotate(-35, {lx:.1f}, {ly:.1f})" '
            f'x="{lx:.1f}" y="{ly:.1f}" text-anchor="end" '
            f'font-size="11" fill="#444">{label}</text>'
        )

    # Y-axis ticks
    y_ticks = []
    tick_count = 5
    for ti in range(tick_count + 1):
        val = y_max * ti / tick_count
        y = _y_top(val)
        y_ticks.append(
            f'<line x1="{margin["left"] - 5:.1f}" y1="{y:.1f}" '
            f'x2="{margin["left"]:.1f}" y2="{y:.1f}" stroke="#999" stroke-width="1"/>'
        )
        y_ticks.append(
            f'<text x="{margin["left"] - 8:.1f}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-size="10" fill="#666">{val:.1f}</text>'
        )

    svg = textwrap.dedent(f"""\
        <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"
             style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    background:#fff; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,.12)">
          <!-- title -->
          <text x="{width / 2:.1f}" y="38" text-anchor="middle"
                font-size="15" font-weight="600" fill="#111">{title}</text>
          <!-- chart area border -->
          <rect x="{margin["left"]:.1f}" y="{margin["top"]:.1f}"
                width="{chart_w:.1f}" height="{chart_h:.1f}"
                fill="#F8FAFC" stroke="#E2E8F0"/>
          <!-- y-axis label -->
          <text transform="rotate(-90, {margin["left"] - 50:.1f}, {margin["top"] + chart_h / 2:.1f})"
                x="{margin["left"] - 50:.1f}" y="{margin["top"] + chart_h / 2:.1f}"
                text-anchor="middle" font-size="12" fill="#555">Latency (ms)</text>
          <!-- y ticks -->
          {"".join(y_ticks)}
          <!-- bars + labels -->
          {"".join(bars)}
          <!-- x-axis -->
          <line x1="{margin["left"]:.1f}" y1="{margin["top"] + chart_h:.1f}"
                x2="{margin["left"] + chart_w:.1f}" y2="{margin["top"] + chart_h:.1f}"
                stroke="#999" stroke-width="1.5"/>
        </svg>
    """)
    return svg


# ── HTML report ────────────────────────────────────────────────────────


def _make_html_report(results: dict, svg_p95: str, svg_p50: str, svg_p99: str) -> str:
    rows = []
    for op, stats in results.items():
        rows.append(
            f"<tr><td>{op}</td>"
            f"<td>{stats['iterations']}</td>"
            f"<td>{stats['mean_ms']:.3f}</td>"
            f"<td>{stats['p50_ms']:.3f}</td>"
            f"<td class='p95'>{stats['p95_ms']:.3f}</td>"
            f"<td class='p99'>{stats['p99_ms']:.3f}</td>"
            f"<td>{stats['min_ms']:.3f}</td>"
            f"<td>{stats['max_ms']:.3f}</td></tr>"
        )

    return textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <title>OPD-Vertex Benchmark Report</title>
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 1100px; margin: 40px auto; padding: 0 20px; color:#111 }}
            h1   {{ font-size:1.8rem; border-bottom:2px solid #2563EB; padding-bottom:8px }}
            h2   {{ font-size:1.2rem; margin-top:32px; color:#334155 }}
            svg  {{ display:block; margin: 24px auto }}
            table {{ border-collapse:collapse; width:100%; margin-top:24px; font-size:.9rem }}
            th,td{{ padding:8px 12px; border:1px solid #E2E8F0; text-align:right }}
            th   {{ background:#F1F5F9; text-align:center }}
            td:first-child{{ text-align:left; font-weight:500 }}
            .p95 {{ color:#D97706; font-weight:600 }}
            .p99 {{ color:#DC2626; font-weight:600 }}
          </style>
        </head>
        <body>
          <h1>OPD-Vertex · Benchmark Report</h1>
          <p>Generated by <code>scripts/generate_test_graphs.py</code> &mdash; all values in <strong>ms</strong>.</p>

          <h2>p95 Latency per Operation</h2>
          {svg_p95}

          <h2>p50 (Median) Latency per Operation</h2>
          {svg_p50}

          <h2>p99 Latency per Operation</h2>
          {svg_p99}

          <h2>Raw Numbers</h2>
          <table>
            <thead><tr>
              <th>Operation</th><th>N</th><th>Mean</th>
              <th>p50</th><th>p95</th><th>p99</th>
              <th>Min</th><th>Max</th>
            </tr></thead>
            <tbody>{"".join(rows)}</tbody>
          </table>
        </body>
        </html>
    """)


# ── Entry point ────────────────────────────────────────────────────────


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)

    results = _load_results()
    if not results:
        print("[graphs] No benchmark data available. Exiting.")
        sys.exit(1)

    print(f"[graphs] Loaded {len(results)} benchmark entries.")

    # Terminal output
    _print_terminal_chart(results)

    # SVG charts
    svg_p95 = _make_svg_bar_chart(results, "p95_ms", "p95 Latency per Operation (ms)")
    svg_p50 = _make_svg_bar_chart(
        results, "p50_ms", "Median (p50) Latency per Operation (ms)"
    )
    svg_p99 = _make_svg_bar_chart(results, "p99_ms", "p99 Latency per Operation (ms)")

    (REPORTS / "benchmark_chart_p95.svg").write_text(svg_p95, encoding="utf-8")
    (REPORTS / "benchmark_chart_p50.svg").write_text(svg_p50, encoding="utf-8")
    (REPORTS / "benchmark_chart_p99.svg").write_text(svg_p99, encoding="utf-8")
    print("[graphs] Saved SVG charts →", REPORTS)

    # HTML report
    html = _make_html_report(results, svg_p95, svg_p50, svg_p99)
    (REPORTS / "benchmark_report.html").write_text(html, encoding="utf-8")
    print("[graphs] Saved HTML report →", REPORTS / "benchmark_report.html")


if __name__ == "__main__":
    main()
