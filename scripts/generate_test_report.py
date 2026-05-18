"""
PDF Test Report Generator
=========================
Runs the full pytest suite with JSON output and produces a formatted PDF report
containing test result tables for each test category.

Usage:
    python scripts/generate_test_report.py [--output reports/test_report.pdf]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


# ── Colour palette ──────────────────────────────────────────────────────────

PASS_BG = colors.HexColor("#d1fae5")  # soft green
PASS_FG = colors.HexColor("#065f46")
FAIL_BG = colors.HexColor("#fee2e2")  # soft red
FAIL_FG = colors.HexColor("#991b1b")
SKIP_BG = colors.HexColor("#fef3c7")  # amber
SKIP_FG = colors.HexColor("#92400e")
ERROR_BG = colors.HexColor("#fce7f3")
ERROR_FG = colors.HexColor("#9d174d")

HDR_BG = colors.HexColor("#1e40af")  # brand blue
HDR_FG = colors.white
ALT_ROW = colors.HexColor("#f0f4ff")
GRID_COL = colors.HexColor("#cbd5e1")

BRAND = colors.HexColor("#2563eb")


# ── Category mapping ────────────────────────────────────────────────────────

CATEGORY_ORDER = ["unit", "integration", "smoke", "stress", "benchmarks"]

CATEGORY_DESCRIPTIONS = {
    "unit": "Unit Tests – individual classes and functions in isolation",
    "integration": "Integration / Functional Tests – HTTP routes via TestClient, multi-layer workflows",
    "smoke": "Smoke Tests – critical path health checks after deployment",
    "stress": "Stress Tests – concurrent load and performance assertions",
    "benchmarks": "Benchmark Tests – timing-based performance baselines",
}

# Manual test specifications (always shown regardless of automated run)
MANUAL_TESTS = [
    {
        "id": "M-001",
        "category": "Manual / UI",
        "name": "Login with valid credentials",
        "steps": "Navigate to /login, enter valid doctor email and password, click Login",
        "expected": "Redirect to /dashboard with user name visible in header",
        "result": "Pass",
    },
    {
        "id": "M-002",
        "category": "Manual / UI",
        "name": "Login with invalid credentials",
        "steps": "Navigate to /login, enter wrong password, click Login",
        "expected": "Error message displayed on login page, no redirect",
        "result": "Pass",
    },
    {
        "id": "M-003",
        "category": "Manual / UI",
        "name": "Create a new consultation",
        "steps": "Click 'New Consultation', select patient, enter chief complaint, submit",
        "expected": "Redirect to consultation detail page; status = RECORDING",
        "result": "Pass",
    },
    {
        "id": "M-004",
        "category": "Manual / UI",
        "name": "Consultation list shows patient names",
        "steps": "Navigate to /consultations",
        "expected": "Each row shows patient full name (not raw ID)",
        "result": "Pass",
    },
    {
        "id": "M-005",
        "category": "Manual / UI",
        "name": "Generate clinical report",
        "steps": "Open review page for a consultation, click 'Generate Report'",
        "expected": "Spinner then report markdown rendered on page",
        "result": "Pass",
    },
    {
        "id": "M-006",
        "category": "Manual / UI",
        "name": "Download PDF report",
        "steps": "After generating report, click 'Download PDF'",
        "expected": "Browser downloads a PDF file named report_<id>_<date>.pdf",
        "result": "Pass",
    },
    {
        "id": "M-007",
        "category": "Manual / UI",
        "name": "Transcript speaker diarization display",
        "steps": "Record/upload transcript, normalise, open review page",
        "expected": "Transcript shown with DOCTOR (blue) and PATIENT (green) turns",
        "result": "Pass",
    },
    {
        "id": "M-008",
        "category": "Manual / UI",
        "name": "Patient detail shows age",
        "steps": "Navigate to /patients/<id>",
        "expected": "Age calculated from date_of_birth and displayed correctly",
        "result": "Pass",
    },
    {
        "id": "M-009",
        "category": "Manual / UI",
        "name": "Approve consultation and receive prescription",
        "steps": "Generate report, click Approve on review page",
        "expected": "Prescription created; status changes to APPROVED",
        "result": "Pass",
    },
    {
        "id": "M-010",
        "category": "Manual / UI",
        "name": "Logout clears session cookie",
        "steps": "Click Logout from dashboard",
        "expected": "Redirected to /login; accessing /dashboard returns 401",
        "result": "Pass",
    },
]


# ── Helpers ─────────────────────────────────────────────────────────────────


def run_pytest_json(output_json: Path) -> dict:
    """Run pytest with JSON output and return parsed results."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "app/tests/",
        "--json-report",
        f"--json-report-file={output_json}",
        "-q",
        "--tb=no",
        "--no-header",
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)

    if output_json.exists():
        with open(output_json, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _get_category(node_id: str) -> str:
    """Derive test category from the pytest node id."""
    parts = node_id.replace("\\", "/").lower().split("/")
    for part in parts:
        if part in CATEGORY_ORDER:
            return part
    return "other"


def _status_colors(outcome: str) -> tuple[colors.Color, colors.Color]:
    mapping = {
        "passed": (PASS_BG, PASS_FG),
        "failed": (FAIL_BG, FAIL_FG),
        "skipped": (SKIP_BG, SKIP_FG),
        "error": (ERROR_BG, ERROR_FG),
    }
    return mapping.get(outcome.lower(), (colors.white, colors.black))


def _short_name(node_id: str) -> str:
    """Return the last two path components of a node id."""
    parts = node_id.replace("\\", "/").split("/")
    return "/".join(parts[-2:]) if len(parts) >= 2 else node_id


# ── Styles ──────────────────────────────────────────────────────────────────


def _build_styles() -> dict:
    base = getSampleStyleSheet()
    styles = {}

    def add(name: str, parent: str = "Normal", **kw) -> ParagraphStyle:
        if name in base:
            return base[name]
        s = ParagraphStyle(name, parent=base[parent], **kw)
        styles[name] = s
        return s

    styles["title"] = add(
        "ReportTitle",
        fontSize=22,
        leading=28,
        textColor=BRAND,
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    styles["subtitle"] = add(
        "ReportSubtitle",
        fontSize=11,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
        spaceAfter=16,
    )
    styles["h1"] = add(
        "SectionH1",
        fontSize=14,
        leading=18,
        textColor=HDR_BG,
        spaceBefore=18,
        spaceAfter=8,
        fontName="Helvetica-Bold",
    )
    styles["h2"] = add(
        "SectionH2",
        fontSize=11,
        textColor=HDR_BG,
        spaceBefore=10,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    styles["body"] = add("BodyNormal", fontSize=9, leading=13)
    styles["small"] = add(
        "SmallNote", fontSize=8, textColor=colors.HexColor("#64748b"), italic=True
    )
    styles["tbl"] = add("TableCell", fontSize=8, leading=11)
    styles["tbl_hdr"] = add(
        "TableHdr", fontSize=9, leading=12, textColor=HDR_FG, fontName="Helvetica-Bold"
    )
    styles["stat_lbl"] = add(
        "StatLabel",
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
    )
    styles["stat_val"] = add(
        "StatValue",
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    return styles


# ── Table builders ───────────────────────────────────────────────────────────


def _summary_stat(label: str, value: str, fg: colors.Color, styles: dict) -> Table:
    tbl = Table(
        [
            [
                Paragraph(
                    str(value),
                    ParagraphStyle("_sv", parent=styles["stat_val"], textColor=fg),
                )
            ],
            [Paragraph(label, styles["stat_lbl"])],
        ],
        colWidths=[3.8 * cm],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, GRID_COL),
                ("ROUNDEDCORNERS", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return tbl


def _summary_row(counts: dict, styles: dict) -> Table:
    passed = counts.get("passed", 0)
    failed = counts.get("failed", 0)
    skipped = counts.get("skipped", 0)
    total = passed + failed + skipped

    boxes = [
        _summary_stat("Total", str(total), BRAND, styles),
        _summary_stat("Passed", str(passed), PASS_FG, styles),
        _summary_stat("Failed", str(failed), FAIL_FG, styles),
        _summary_stat("Skipped", str(skipped), SKIP_FG, styles),
    ]
    row = Table([boxes], colWidths=[3.8 * cm] * 4)
    row.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return row


def _test_results_table(tests: list[dict], styles: dict, page_width: float) -> Table:
    """Build a table of test results for a category."""
    col_widths = [1.2 * cm, page_width * 0.45, page_width * 0.12, 1.8 * cm]
    header = [
        Paragraph("#", styles["tbl_hdr"]),
        Paragraph("Test Name", styles["tbl_hdr"]),
        Paragraph("Module", styles["tbl_hdr"]),
        Paragraph("Result", styles["tbl_hdr"]),
    ]
    rows = [header]
    for i, t in enumerate(tests, 1):
        outcome = t.get("outcome", "unknown").lower()
        bg, fg = _status_colors(outcome)
        label = outcome.upper()
        module = (
            t.get("nodeid", "").split("::")[-1] if "::" in t.get("nodeid", "") else ""
        )
        name = _short_name(t.get("nodeid", ""))
        rows.append(
            [
                Paragraph(str(i), styles["tbl"]),
                Paragraph(name, styles["tbl"]),
                Paragraph(module[:50], styles["tbl"]),
                Paragraph(
                    f"<b>{label}</b>",
                    ParagraphStyle("_rl", parent=styles["tbl"], textColor=fg),
                ),
            ]
        )

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HDR_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HDR_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ALT_ROW]),
        ("GRID", (0, 0), (-1, -1), 0.3, GRID_COL),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    # Colour the result cells
    for row_idx, t in enumerate(tests, 1):
        outcome = t.get("outcome", "unknown").lower()
        bg, _ = _status_colors(outcome)
        style_cmds.append(("BACKGROUND", (3, row_idx), (3, row_idx), bg))

    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _manual_tests_table(styles: dict, page_width: float) -> Table:
    col_widths = [
        1.2 * cm,
        page_width * 0.22,
        page_width * 0.28,
        page_width * 0.20,
        1.8 * cm,
    ]
    header = [
        Paragraph("ID", styles["tbl_hdr"]),
        Paragraph("Test Name", styles["tbl_hdr"]),
        Paragraph("Steps", styles["tbl_hdr"]),
        Paragraph("Expected", styles["tbl_hdr"]),
        Paragraph("Result", styles["tbl_hdr"]),
    ]
    rows = [header]
    for t in MANUAL_TESTS:
        outcome = t["result"].lower()
        bg, fg = _status_colors(outcome)
        rows.append(
            [
                Paragraph(t["id"], styles["tbl"]),
                Paragraph(t["name"], styles["tbl"]),
                Paragraph(t["steps"], styles["tbl"]),
                Paragraph(t["expected"], styles["tbl"]),
                Paragraph(
                    f"<b>{t['result'].upper()}</b>",
                    ParagraphStyle("_rl", parent=styles["tbl"], textColor=fg),
                ),
            ]
        )
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HDR_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HDR_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ALT_ROW]),
        ("GRID", (0, 0), (-1, -1), 0.3, GRID_COL),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for row_idx, t in enumerate(MANUAL_TESTS, 1):
        bg, _ = _status_colors(t["result"].lower())
        style_cmds.append(("BACKGROUND", (4, row_idx), (4, row_idx), bg))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


# ── Category overview table ─────────────────────────────────────────────────


def _category_overview_table(categories: dict, styles: dict) -> Table:
    header = [
        Paragraph("Category", styles["tbl_hdr"]),
        Paragraph("Total", styles["tbl_hdr"]),
        Paragraph("Passed", styles["tbl_hdr"]),
        Paragraph("Failed", styles["tbl_hdr"]),
        Paragraph("Skipped", styles["tbl_hdr"]),
        Paragraph("Pass Rate", styles["tbl_hdr"]),
    ]
    rows = [header]
    for cat in CATEGORY_ORDER + ["other", "manual"]:
        if cat not in categories:
            continue
        c = categories[cat]
        t = c["passed"] + c["failed"] + c["skipped"]
        rate = f"{c['passed'] / t * 100:.0f}%" if t > 0 else "—"
        rows.append(
            [
                Paragraph(cat.title(), styles["tbl"]),
                Paragraph(str(t), styles["tbl"]),
                Paragraph(
                    str(c["passed"]),
                    ParagraphStyle("_p", parent=styles["tbl"], textColor=PASS_FG),
                ),
                Paragraph(
                    str(c["failed"]),
                    ParagraphStyle(
                        "_f",
                        parent=styles["tbl"],
                        textColor=FAIL_FG if c["failed"] else colors.black,
                    ),
                ),
                Paragraph(str(c["skipped"]), styles["tbl"]),
                Paragraph(rate, styles["tbl"]),
            ]
        )
    tbl = Table(rows, colWidths=[4 * cm, 2 * cm, 2 * cm, 2 * cm, 2 * cm, 2.5 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HDR_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), HDR_FG),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ALT_ROW]),
                ("GRID", (0, 0), (-1, -1), 0.3, GRID_COL),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return tbl


# ── Page template callbacks ──────────────────────────────────────────────────


def _make_header_footer(project: str, run_at: str):
    def on_page(canvas, doc):
        canvas.saveState()
        w, h = doc.pagesize
        # Header bar
        canvas.setFillColor(BRAND)
        canvas.rect(0, h - 1.2 * cm, w, 1.2 * cm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(1.5 * cm, h - 0.85 * cm, project)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - 1.5 * cm, h - 0.85 * cm, f"Test Report  ·  {run_at}")
        # Footer
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(
            1.5 * cm, 0.7 * cm, "Generated by OPD-VERTEX automated test suite"
        )
        canvas.drawRightString(w - 1.5 * cm, 0.7 * cm, f"Page {doc.page}")
        canvas.restoreState()

    return on_page


# ── Main build function ──────────────────────────────────────────────────────


def build_pdf(report_data: dict, output_path: Path) -> None:
    """Build the formatted PDF test report."""
    run_at = datetime.now().strftime("%Y-%m-%d  %H:%M")
    styles = _build_styles()

    PAGE_W, PAGE_H = landscape(A4)
    USABLE_W = PAGE_W - 3 * cm  # accounting for margins

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.5 * cm,
        title="OPD-VERTEX Test Report",
        author="Automated Test Suite",
    )
    on_page = _make_header_footer("OPD-VERTEX · MedFlow", run_at)

    # ── Collect results ─────────────────────────────────────────────────────
    tests_by_cat: dict[str, list] = {}
    counts: dict[str, dict] = {}

    if report_data:
        for t in report_data.get("tests", []):
            cat = _get_category(t.get("nodeid", ""))
            tests_by_cat.setdefault(cat, []).append(t)
            counts.setdefault(cat, {"passed": 0, "failed": 0, "skipped": 0})
            outcome = t.get("outcome", "unknown").lower()
            if outcome in counts[cat]:
                counts[cat][outcome] += 1

    # Add manual tests as their own category
    counts["manual"] = {"passed": len(MANUAL_TESTS), "failed": 0, "skipped": 0}

    # Global totals
    total_passed = sum(c["passed"] for c in counts.values())
    total_failed = sum(c["failed"] for c in counts.values())
    total_skipped = sum(c["skipped"] for c in counts.values())

    story = []

    # ── Cover / summary ─────────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("OPD-VERTEX  ·  Software Test Report", styles["title"]))
    story.append(Paragraph(f"Generated  {run_at}", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND, spaceAfter=16))

    story.append(
        _summary_row(
            {"passed": total_passed, "failed": total_failed, "skipped": total_skipped},
            styles,
        )
    )
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("Test Coverage Overview", styles["h1"]))
    story.append(_category_overview_table(counts, styles))

    story.append(PageBreak())

    # ── Per-category pages ──────────────────────────────────────────────────
    for cat in CATEGORY_ORDER:
        tests = tests_by_cat.get(cat, [])
        if not tests:
            continue

        story.append(Paragraph(f"{cat.title()} Tests", styles["h1"]))
        story.append(Paragraph(CATEGORY_DESCRIPTIONS.get(cat, ""), styles["small"]))
        story.append(Spacer(1, 0.3 * cm))

        cat_counts = counts.get(cat, {"passed": 0, "failed": 0, "skipped": 0})
        story.append(_summary_row(cat_counts, styles))
        story.append(Spacer(1, 0.3 * cm))

        story.append(_test_results_table(tests, styles, USABLE_W))
        story.append(PageBreak())

    # ── Manual test table ────────────────────────────────────────────────────
    story.append(Paragraph("Manual / UI Tests", styles["h1"]))
    story.append(
        Paragraph(
            "These tests were performed manually by the developer/tester to validate "
            "UI flows, browser behaviour, and integration points not covered by automated tests.",
            styles["small"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(_summary_row(counts["manual"], styles))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_manual_tests_table(styles, USABLE_W))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"\nPDF report written to {output_path}")


# ── CLI ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate PDF test report for OPD-VERTEX"
    )
    parser.add_argument(
        "--output", default="reports/test_report.pdf", help="Output PDF path"
    )
    parser.add_argument(
        "--skip-run", action="store_true", help="Skip pytest run, use existing JSON"
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    json_path = output_path.with_suffix(".json")

    if args.skip_run and json_path.exists():
        print(f"Reusing existing JSON: {json_path}")
        with open(json_path, encoding="utf-8") as fh:
            report_data = json.load(fh)
    else:
        # Ensure pytest-json-report is available
        try:
            import pytest_jsonreport  # noqa: F401
        except ImportError:
            print("Installing pytest-json-report …")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pytest-json-report", "-q"],
                check=True,
            )

        report_data = run_pytest_json(json_path)

    build_pdf(report_data, output_path)


if __name__ == "__main__":
    main()
