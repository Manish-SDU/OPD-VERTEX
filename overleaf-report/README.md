# OPD-Vertex Overleaf Report

This folder is a standalone LaTeX project for Overleaf. It contains an editable technical report, validation charts, and generated PDF appendices for OPD-Vertex.

## Files

- `main.tex` is the Overleaf main file.
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