# OPD-Vertex Exact PDF Overleaf Project

This folder is a standalone Overleaf project that reproduces the original PDF exactly by embedding it with LaTeX's `pdfpages` package.

The main file is intentionally simple: it does not redesign the report. It includes `assets/pdfs/source.pdf` page-for-page so the Overleaf output matches the PDF layout.

## Files

- `main.tex` is the Overleaf main file and exact-PDF wrapper.
- `assets/pdfs/source.pdf` is the PDF that Overleaf will reproduce exactly.
- `editable-report.tex` is the earlier editable LaTeX draft, kept only as a backup/reference.
- `config/metadata.tex` stores title, author, date, and repository metadata.
- `config/preamble.tex` stores layout, colors, tables, figures, and PDF settings.
- `sections/` stores the editable report chapters.
- `assets/charts/` stores chart images used in the validation section.
- `assets/pdfs/` stores generated PDF appendices.

## Compile on Overleaf

1. Open Overleaf.
2. Create or import a project using this folder.
3. Set the main document to `main.tex`.
4. Set the compiler to `pdfLaTeX`.
5. Recompile.

If you want a different PDF to be reproduced, replace `assets/pdfs/source.pdf` with that PDF and keep the same file name.

## Important note

This method preserves the PDF appearance exactly. It does not make the PDF text editable as normal LaTeX paragraphs. An exact visual match and fully editable LaTeX source are different goals; exact matching is done by embedding the original PDF.

## Recommended GitHub flow

For the cleanest Overleaf import, push this folder as its own repository instead of importing the full application repository.

```powershell
cd overleaf-report
git init
git add .
git commit -m "Create OPD-Vertex Overleaf report"
```

Then create a GitHub repository, add it as `origin`, and push:

```powershell
git remote add origin https://github.com/Manish-SDU/opd-vertex-overleaf-report.git
git branch -M main
git push -u origin main
```

After that, use Overleaf's GitHub import/sync feature and select the new repository.