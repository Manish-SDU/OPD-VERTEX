# Connecting This Exact PDF Project to Overleaf with GitHub

Use this guide after the local files are ready.

The main document is `main.tex`. It embeds `assets/pdfs/source.pdf` exactly, so Overleaf produces the same visual result as the original PDF.

## Option A: Standalone GitHub repository

This is recommended because Overleaf expects a LaTeX project with `main.tex` at the project root.

1. In GitHub, create a new repository such as `opd-vertex-overleaf-report`.
2. In VS Code terminal, run:

```powershell
cd overleaf-report
git init
git add .
git commit -m "Create OPD-Vertex Overleaf report"
git remote add origin https://github.com/Manish-SDU/opd-vertex-overleaf-report.git
git branch -M main
git push -u origin main
```

3. In Overleaf, open `https://www.overleaf.com/project`.
4. Choose `New Project`.
5. Choose `Import from GitHub`.
6. Select the new repository.
7. Set `main.tex` as the main document if Overleaf asks.
8. In `Menu`, set the compiler to `pdfLaTeX`.

## Option B: Keep this inside the existing application repository

This works if you want the report versioned with the source code, but Overleaf may be less convenient because the LaTeX file is inside a subfolder.

1. Push the current application repository to GitHub.
2. In Overleaf, import the GitHub repository.
3. Open `overleaf-report/main.tex`.
4. Set it as the main document.

## If GitHub import is unavailable

Some Overleaf accounts restrict GitHub sync. If the GitHub option is not visible, create a ZIP file of this folder and upload it as a new Overleaf project. The report will still compile normally.

## After editing in Overleaf

If GitHub sync is enabled, use Overleaf's GitHub sync panel to push Overleaf changes back to GitHub. Pull those changes in VS Code before making more local edits.