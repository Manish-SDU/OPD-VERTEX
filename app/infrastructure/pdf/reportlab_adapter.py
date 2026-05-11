"""ReportLab pdf generation adapter."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_CENTER


from app.domain.clinical_notes.models import PrescriptionArtifact
from app.domain.pdf.models import (
    PdfGenerator,
    ConsultationMetadata,
)
from app.domain.prescriptions.models import Prescription
from app.core.config import get_settings


class ReportLabPdfGenerator(PdfGenerator):
    def __init__(self):
        self.settings = get_settings()
        self.pdf_output_dir = Path(self.settings.pdf_output_dir)
        self.pdf_output_dir.mkdir(parents=True, exist_ok=True)
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _safe_add_style(self, style: ParagraphStyle) -> None:
        """Add a style to the stylesheet only if it does not already exist."""
        if style.name not in self.styles.byName:
            self.styles.add(style)

    def _create_custom_styles(self) -> None:
        """Create custom paragraph styles for clinical reports."""
        self._safe_add_style(
            ParagraphStyle(
                name="ReportTitle",
                parent=self.styles["Heading1"],
                fontSize=16,
                textColor=colors.HexColor("#1a1a1a"),
                spaceAfter=12,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )
        self._safe_add_style(
            ParagraphStyle(
                name="SectionHeading",
                parent=self.styles["Heading2"],
                fontSize=12,
                textColor=colors.HexColor("#2c3e50"),
                spaceAfter=8,
                spaceBefore=12,
                fontName="Helvetica-Bold",
            )
        )
        self._safe_add_style(
            ParagraphStyle(
                name="PatientInfo",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#34495e"),
                spaceAfter=4,
                fontName="Helvetica",
            )
        )
        self._safe_add_style(
            ParagraphStyle(
                name="BodyText",
                parent=self.styles["Normal"],
                fontSize=10,
                leading=14,
                spaceAfter=6,
                fontName="Helvetica",
            )
        )
        self._safe_add_style(
            ParagraphStyle(
                name="Footer",
                parent=self.styles["Normal"],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
            )
        )

    def generate_report_pdf(
        self, report_markdown: str, consultation_metadata: ConsultationMetadata
    ) -> str:
        """Generate a clinical report PDF from markdown."""
        if not report_markdown or report_markdown.strip() == "":
            raise ValueError("Report markdown cannot be empty")

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{consultation_metadata.consultation_id}_{timestamp}.pdf"
        file_path = self.pdf_output_dir / filename

        # Create PDF document
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        # Build flowables
        flowables = []

        # Title
        flowables.append(
            Paragraph(
                f"Clinical Report - Consultation #{consultation_metadata.consultation_id}",
                self.styles["ReportTitle"],
            )
        )
        flowables.append(Spacer(1, 0.2 * inch))

        # Patient and Clinician Info Header
        header_data = [
            [
                Paragraph(
                    f"<b>Patient:</b> {consultation_metadata.patient_name}",
                    self.styles["PatientInfo"],
                ),
                Paragraph(
                    f"<b>Date:</b> {consultation_metadata.consultation_date.strftime('%Y-%m-%d %H:%M')}",
                    self.styles["PatientInfo"],
                ),
            ],
            [
                Paragraph(
                    f"<b>Clinician:</b> {consultation_metadata.clinician_name}",
                    self.styles["PatientInfo"],
                ),
                Paragraph(
                    f"<b>Visit Type:</b> {consultation_metadata.visit_type or 'General'}",
                    self.styles["PatientInfo"],
                ),
            ],
        ]
        header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
        header_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecf0f1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        flowables.append(header_table)
        flowables.append(Spacer(1, 0.3 * inch))

        # Parse and render markdown sections
        self._parse_and_render_markdown(report_markdown, flowables)

        # Footer
        flowables.append(Spacer(1, 0.3 * inch))
        footer_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Page <pageNumber/>"
        flowables.append(Paragraph(footer_text, self.styles["Footer"]))

        # Build PDF
        doc.build(flowables)

        # Verify file was created and get size
        if not file_path.exists():
            raise IOError(f"Failed to create PDF at {file_path}")

        return str(file_path)

    def _parse_and_render_markdown(self, markdown: str, flowables: list) -> None:
        """Parse markdown and convert sections to ReportLab flowables."""
        lines = markdown.split("\n")
        current_section = None
        section_content = []

        for line in lines:
            # Section headers (## Section Name)
            if line.startswith("## "):
                # Flush previous section
                if current_section and section_content:
                    self._render_section(
                        current_section, "\n".join(section_content), flowables
                    )
                    section_content = []

                current_section = line.replace("## ", "").strip()
                flowables.append(
                    Paragraph(current_section, self.styles["SectionHeading"])
                )
            # Subsection headers (### Subsection)
            elif line.startswith("### "):
                subsection = line.replace("### ", "").strip()
                flowables.append(
                    Paragraph(f"<b>{subsection}</b>", self.styles["BodyText"])
                )

            # List items (- item)
            elif line.strip().startswith("- "):
                item = line.replace("- ", "").strip()
                # Convert markdown bold/italic to ReportLab HTML
                item = self._convert_markdown_formatting(item)
                flowables.append(Paragraph(f"• {item}", self.styles["BodyText"]))
            # Regular text (non-empty lines)
            elif line.strip():
                # Convert markdown formatting to ReportLab HTML
                formatted_line = self._convert_markdown_formatting(line.strip())
                flowables.append(Paragraph(formatted_line, self.styles["BodyText"]))

            # Empty lines create spacing
            elif not line.strip():
                flowables.append(Spacer(1, 0.1 * inch))

        # Flush final section
        if current_section and section_content:
            self._render_section(current_section, "\n".join(section_content), flowables)

    def _convert_markdown_formatting(self, text: str) -> str:
        """Convert markdown formatting (**bold**, *italic*) to ReportLab HTML."""
        # **bold** → <b>bold</b>
        text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
        # *italic* → <i>italic</i>
        text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
        # `code` → <font name="Courier">code</font>
        text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
        return text

    def _render_section(self, section_name: str, content: str, flowables: list) -> None:
        """Render a section with its content."""
        # This is a helper; content is rendered as we parse
        pass

    def generate_prescription_pdf(
        self, prescription: Prescription
    ) -> PrescriptionArtifact:
        """Generate prescription PDF metadata without leaking SQL storage details."""
        # TODO: render a real PDF and persist the artifact via Mongo-backed storage.
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
