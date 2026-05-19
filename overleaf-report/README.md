# OPD-Vertex Editable Overleaf Project

This folder is a standalone Overleaf project for the OPD-Vertex fourth semester report. The report content has been extracted from `4th_Semester_OPDVertex_Report.pdf` and rewritten into editable LaTeX section files.

`main.tex` no longer embeds the source report PDF. It compiles normal LaTeX content so the text, tables, figures, and structure can be edited directly in Overleaf.

## Files

- `main.tex` is the Overleaf main file.
- `editable-report.tex` mirrors the same editable document structure and is kept as a compatibility entry point.
- `config/metadata.tex` stores title, author, date, and repository metadata.
- `config/preamble.tex` stores layout, colors, tables, figures, and PDF settings.
- `sections/` stores the editable report chapters.
- `assets/charts/` stores chart images used in the validation section.
- `assets/pdfs/` stores optional generated validation PDF appendices, not the source report body.
- `assets/extracted/4th_semester_report.txt` is the plain-text extraction used as conversion source.

## Compile on Overleaf

1. Open Overleaf.
2. Create or import a project using this folder.
3. Set the main document to `main.tex`.
4. Set the compiler to `pdfLaTeX`.
5. Recompile.

The original PDF is kept only as a reference. To edit the report, change the files in `sections/` instead of replacing a PDF.

## SDU template note

The chat attachment `SDU_Template.zip` was not visible as a workspace file during conversion. If you place that zip in this folder or extract it into the workspace, the editable report content can be moved into the exact SDU template structure.

## Recommended GitHub flow

For the cleanest Overleaf import, push this folder as its own repository instead of importing the full application repository.

```powershell
cd overleaf-report
git init
git add .
git commit -m "Create OPD-Vertex Overleaf report"
```

Then create a GitHub repository, add it as `origin`, and push. Do not paste personal access tokens into chat; use GitHub's normal browser login or type credentials directly into the terminal if Git asks for them.

```powershell
git remote add origin https://github.com/Manish-SDU/opd-vertex-overleaf-report.git
git branch -M main
git push -u origin main
```

After that, use Overleaf's GitHub import/sync feature and select the new repository.