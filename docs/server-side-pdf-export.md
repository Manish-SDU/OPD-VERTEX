# Server-Side PDF Export Guide

This document describes how to implement a proper server-side PDF export flow for OPD-Vertex so clinical reports can be downloaded as polished PDF files without relying on the browser print dialog.

## Goal

Replace the current browser-driven `Save as PDF` experience with a backend-generated PDF that:

- uses a stable A4 layout
- excludes browser headers and footers
- preserves the report structure already produced by `report_markdown`
- can be downloaded directly from the application
- remains compatible with both mock mode and real mode

## Recommended Approach

Implement a dedicated report PDF generation path for clinical reports, separate from the existing placeholder prescription PDF adapter.

Suggested stack:

- `reportlab` for deterministic server-side PDF rendering
- optional lightweight text-to-layout parser for the existing `report_markdown`
- file output to `PDF_OUTPUT_DIR` during the first iteration

Why this approach:

- no browser dependency
- predictable formatting
- easy to run in Docker
- works offline
- fits the current Python/FastAPI architecture

## Proposed Architecture

Add a new vertical slice for report PDF export:

1. Route layer
   Add an endpoint such as `GET /review/report/{consultation_id}/pdf`

2. Application layer
   Add a service responsible for:
   - loading the generated clinical report
   - validating that `report_markdown` exists
   - calling a PDF renderer
   - returning a downloadable file response

3. Infrastructure layer
   Add a real PDF renderer implementation using ReportLab

4. Storage
   First iteration:
   - write the PDF to `PDF_OUTPUT_DIR`
   - return it via `FileResponse`

   Later iteration:
   - persist PDF metadata in Mongo/GridFS or another artifact store

## Suggested Files

Possible additions:

- `app/application/pdf/services.py`
- `app/api/routes/review.py`
  add a new report PDF endpoint
- `app/infrastructure/pdf/reportlab_adapter.py`
  extend or split the current adapter
- `app/domain/pdf/models.py`
  add a report PDF contract if you want to keep prescription and report exports separate

Optional:

- `app/infrastructure/pdf/report_markdown_parser.py`
- `app/tests/integration/test_report_pdf.py`
- `app/tests/unit/test_pdf_rendering.py`

## Data Source

Use:

- `generated_document.generated_output.report_markdown`

This is the best source for the first version because:

- it already contains the final report text
- it matches the visual structure the user sees
- it avoids rebuilding the document from many nested fields

## Rendering Strategy

Parse `report_markdown` into three zones:

1. Header block
   Example:
   - Facility Name
   - Department
   - Encounter ID
   - Date of Visit
   - Time of Visit
   - Clinician
   - Report Status
   - Source

2. Numbered sections
   Example:
   - `1. PATIENT INFORMATION`
   - `2. ENCOUNTER DETAILS`
   - `3. CHIEF COMPLAINT`

3. Section body content
   Example:
   - key/value rows
   - plain paragraphs
   - bullet lists
   - subsection labels such as `A. Medications Prescribed`

Recommended PDF layout:

- top title band with report name
- metadata grid or stacked header rows
- each numbered section in a bordered block
- consistent typography:
  - title: bold, larger
  - section headings: bold, blue or dark slate
  - labels: semibold
  - body text: regular serif or clean sans-serif
- page numbers in footer

## Minimal Implementation Plan

### Step 1: Add a real report PDF service

Create an application service that:

- accepts `consultation_id`
- loads review context
- raises a `404` or `400` if the report is missing
- calls the PDF renderer
- returns the generated file path

### Step 2: Build a ReportLab renderer

Implement a renderer that:

- creates an A4 document
- uses paragraph styles
- renders the report title and metadata
- splits sections using the existing separator lines
- wraps long text correctly
- creates multi-page documents safely

### Step 3: Expose a download endpoint

In `review.py`, add:

- `GET /review/report/{consultation_id}/pdf`

Response:

- `FileResponse`
- `media_type="application/pdf"`
- `filename=f"clinical_report_{consultation_id}.pdf"`

### Step 4: Update the UI

Replace the current export link so it points to the new endpoint instead of the print-only page.

Possible UX:

- keep both actions:
  - `Export PDF`
  - `Print View`

## ReportLab Notes

Recommended primitives:

- `SimpleDocTemplate`
- `Paragraph`
- `Spacer`
- `Table`
- `TableStyle`
- `PageBreak`

Recommended styles:

- title style
- metadata label/value styles
- section heading style
- normal body style
- bullet/list style

Useful implementation detail:

- create a helper that converts one parsed section into a list of Flowables

## Parsing Rules

The current `report_markdown` is structured enough for rule-based parsing.

Suggested parsing logic:

1. Read all lines
2. Capture metadata lines before the first separator block
3. Detect sections with a regex like:
   - separator line
   - numbered heading
   - separator line
4. Inside each section:
   - lines starting with `- ` become bullets
   - lines containing `:` become label/value rows
   - lines matching `^[A-Z]\.` become subsection headings
   - other lines become normal paragraphs

This is sufficient for version 1.

## Suggested Endpoint Behavior

If report exists:

- generate PDF
- return file download

If report does not exist:

- return `404` or `400` with a clear message like:
  - `Clinical report has not been generated yet.`

If generation fails:

- log the exception
- return `500` with a safe error message

## Storage Options

### Option A: Ephemeral local files

Good for first implementation.

Pros:

- simple
- easy to debug
- no schema changes

Cons:

- artifacts may be lost between container rebuilds

### Option B: Persisted artifact metadata

Store:

- file name
- consultation id
- generated timestamp
- byte size
- checksum
- storage backend

This aligns well with the existing artifact concepts in the codebase.

### Option C: GridFS / object storage

Best for production-like persistence, but not necessary for the first version.

## Testing Plan

### Unit tests

Test:

- parser splits metadata and sections correctly
- renderer handles long content
- renderer handles bullet lists
- renderer handles missing optional sections

### Integration tests

Test:

- endpoint returns `200`
- response content type is `application/pdf`
- filename is correct
- missing report returns controlled error

### Manual checks

Verify:

- PDF opens correctly
- no browser headers/footers
- page breaks are clean
- long reports do not overflow
- typography is readable

## Nice Future Improvements

- include hospital/clinic logo
- watermark drafts vs approved reports
- approved signature block
- QR code with consultation/report id
- saved PDF version history
- direct email attachment support

## Recommended First Deliverable

The best first production step is:

1. keep the current print view for quick fallback
2. add a new true server-side endpoint
3. generate PDFs from `report_markdown` using ReportLab
4. return them as downloadable files from FastAPI

That gives a clean, professional export path with minimal architectural risk.
