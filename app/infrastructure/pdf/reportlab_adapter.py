"""ReportLab pdf generation adapter."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.domain.clinical_notes.models import PrescriptionArtifact
from app.domain.pdf.models import ConsultationMetadata, PdfGenerator
from app.domain.prescriptions.models import Prescription
from app.core.config import get_settings

# ── Palette ────────────────────────────────────────────────────────────────
_BLUE = colors.HexColor("#2563eb")
_BLUE_LIGHT = colors.HexColor("#eff6ff")
_BLUE_DIM = colors.HexColor("#bfdbfe")
_ACCENT = colors.HexColor("#1d4ed8")
_DARK = colors.HexColor("#0f172a")
_MUTED = colors.HexColor("#64748b")
_BORDER = colors.HexColor("#e2e8f0")
_WHITE = colors.white


def _build_styles() -> dict:
    defs = [
        ParagraphStyle(
            "BannerTitle",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=_WHITE,
            leading=28,
        ),
        ParagraphStyle(
            "BannerSub",
            fontName="Helvetica",
            fontSize=9,
            textColor=_BLUE_DIM,
            leading=13,
        ),
        ParagraphStyle(
            "BannerRight",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=_WHITE,
            leading=13,
            alignment=TA_RIGHT,
        ),
        ParagraphStyle(
            "BannerRightSub",
            fontName="Helvetica",
            fontSize=9,
            textColor=_BLUE_DIM,
            leading=13,
            alignment=TA_RIGHT,
        ),
        ParagraphStyle(
            "InfoLabel",
            fontName="Helvetica-Bold",
            fontSize=7,
            textColor=_MUTED,
            leading=10,
            spaceAfter=1,
        ),
        ParagraphStyle(
            "InfoValue", fontName="Helvetica", fontSize=10, textColor=_DARK, leading=14
        ),
        ParagraphStyle(
            "SectionHead",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=_ACCENT,
            leading=15,
            spaceBefore=10,
            spaceAfter=4,
        ),
        ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=10,
            textColor=_DARK,
            leading=15,
            spaceAfter=3,
        ),
        ParagraphStyle(
            "Bullet",
            fontName="Helvetica",
            fontSize=10,
            textColor=_DARK,
            leading=15,
            leftIndent=14,
            spaceAfter=2,
        ),
        ParagraphStyle(
            "FooterStyle", fontName="Helvetica", fontSize=8, textColor=_MUTED
        ),
    ]
    out = {}
    for s in defs:
        out[s.name] = s
    return out


_STYLES = _build_styles()


def _md(text: str) -> str:
    """Convert **bold** and *italic* markdown to ReportLab XML."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
    return text


def _build_banner(metadata: ConsultationMetadata, usable_w: float) -> Table:
    date_str = (
        metadata.consultation_date.strftime("%d %B %Y")
        if metadata.consultation_date
        else "—"
    )
    left = [
        Paragraph("MedFlow", _STYLES["BannerTitle"]),
        Paragraph("Clinical Management System", _STYLES["BannerSub"]),
    ]
    right = [
        Paragraph("CLINICAL REPORT", _STYLES["BannerRight"]),
        Paragraph(
            f"Consultation #{metadata.consultation_id} &nbsp;·&nbsp; {date_str}",
            _STYLES["BannerRightSub"],
        ),
    ]
    t = Table([[left, right]], colWidths=[usable_w * 0.55, usable_w * 0.45])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _BLUE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 18),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
                ("LEFTPADDING", (0, 0), (0, 0), 20),
                ("RIGHTPADDING", (1, 0), (1, 0), 20),
                ("LEFTPADDING", (1, 0), (1, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 8),
            ]
        )
    )
    return t


def _build_info_card(metadata: ConsultationMetadata, usable_w: float) -> Table:
    date_label = (
        metadata.consultation_date.strftime("%d %b %Y, %H:%M")
        if metadata.consultation_date
        else "—"
    )
    L, V = _STYLES["InfoLabel"], _STYLES["InfoValue"]
    col = usable_w / 4

    data = [
        [
            Paragraph("PATIENT", L),
            Paragraph(metadata.patient_name or "—", V),
            Paragraph("DATE", L),
            Paragraph(date_label, V),
        ],
        [
            Paragraph("CLINICIAN", L),
            Paragraph(metadata.clinician_name or "—", V),
            Paragraph("VISIT TYPE", L),
            Paragraph(metadata.visit_type or "General", V),
        ],
    ]
    t = Table(data, colWidths=[col * 0.55, col * 1.45, col * 0.55, col * 1.45])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _BLUE_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1, _BORDER),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, _BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return t


def _parse_content(markdown: str) -> list:
    """Convert markdown text to a list of ReportLab flowables."""
    flowables = []
    for line in markdown.split("\n"):
        stripped = line.strip()

        # Skip pure separator lines (---, ===, -----)
        if re.match(r"^[-=]{3,}$", stripped):
            continue

        if stripped.startswith("## ") or stripped.startswith("### "):
            heading = re.sub(r"^#{2,3}\s*", "", stripped)
            flowables.append(
                HRFlowable(width="100%", thickness=0.5, color=_BORDER, spaceAfter=2)
            )
            flowables.append(Paragraph(_md(heading), _STYLES["SectionHead"]))

        elif stripped.startswith("- "):
            flowables.append(
                Paragraph(f"&bull;&nbsp; {_md(stripped[2:])}", _STYLES["Bullet"])
            )

        elif stripped:
            flowables.append(Paragraph(_md(stripped), _STYLES["Body"]))

        else:
            flowables.append(Spacer(1, 0.07 * inch))

    return flowables


def _footer_cb(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(_BORDER)
    canvas.setLineWidth(0.5)
    y_line = 0.65 * inch
    canvas.line(0.75 * inch, y_line, A4[0] - 0.75 * inch, y_line)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_MUTED)
    canvas.drawString(0.75 * inch, 0.45 * inch, "MedFlow — Confidential Medical Record")
    canvas.drawRightString(A4[0] - 0.75 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


class ReportLabPdfGenerator(PdfGenerator):
    def __init__(self):
        self.settings = get_settings()
        self.pdf_output_dir = Path(self.settings.pdf_output_dir)
        self.pdf_output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report_pdf(
        self, report_markdown: str, consultation_metadata: ConsultationMetadata
    ) -> str:
        if not report_markdown or not report_markdown.strip():
            raise ValueError("Report markdown cannot be empty")

        # ── Descriptive filename ────────────────────────────────────
        last = (consultation_metadata.patient_name or "unknown").strip().split()[-1]
        safe_last = re.sub(r"[^a-z0-9]", "", last.lower()) or "unknown"
        date_str = (
            consultation_metadata.consultation_date.strftime("%Y%m%d")
            if consultation_metadata.consultation_date
            else datetime.now().strftime("%Y%m%d")
        )
        filename = (
            f"report_{safe_last}_{date_str}_{consultation_metadata.consultation_id}.pdf"
        )
        file_path = self.pdf_output_dir / filename

        usable_w = A4[0] - 1.5 * inch

        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.85 * inch,
            bottomMargin=0.85 * inch,
        )

        flowables = [
            _build_banner(consultation_metadata, usable_w),
            Spacer(1, 0.2 * inch),
            _build_info_card(consultation_metadata, usable_w),
            Spacer(1, 0.25 * inch),
            *_parse_content(report_markdown),
        ]

        doc.build(flowables, onFirstPage=_footer_cb, onLaterPages=_footer_cb)

        if not file_path.exists():
            raise IOError(f"Failed to create PDF at {file_path}")

        return str(file_path)

    def generate_prescription_pdf(
        self, prescription: Prescription
    ) -> PrescriptionArtifact:
        return PrescriptionArtifact(
            prescription_id=prescription.id or 0,
            consultation_id=prescription.consultation_id,
            doctor_id=prescription.doctor_id,
            patient_id=prescription.patient_id,
            version=prescription.version,
            storage_backend="mongo_metadata",
            file_name=f"prescription_{prescription.id or 'draft'}.pdf",
            byte_size=0,
        )
