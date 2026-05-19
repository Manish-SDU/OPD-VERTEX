# Connecting This Editable Report Project to Overleaf with GitHub

Use this guide after the local files are ready.

The main document is `main.tex`. It compiles editable LaTeX files from `sections/`, so the report can be edited normally in Overleaf.

The current workspace branch for this report is `SP4-Report`.

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

Use GitHub's normal credential flow. Do not paste a Git token into chat; if Git prompts for a token, type it directly into the terminal prompt.

3. In Overleaf, open `https://www.overleaf.com/project`.
4. Choose `New Project`.
5. Choose `Import from GitHub`.
6. Select the new repository.
7. Set `main.tex` as the main document if Overleaf asks.
8. In `Menu`, set the compiler to `pdfLaTeX`.

## Option B: Keep this inside the existing application repository

This works if you want the report versioned with the source code, but Overleaf may be less convenient because the LaTeX file is inside a subfolder.

1. Commit the report changes on `SP4-Report`.
2. Push the branch: `git push -u origin SP4-Report`.
3. In Overleaf, import the GitHub repository and select the `SP4-Report` branch if Overleaf asks.
4. Open `overleaf-report/main.tex`.
5. Set it as the main document.

## Option C: Push only the Overleaf folder to the Overleaf remote

The repository already has an `overleaf` Git remote. To publish only the LaTeX project folder so `main.tex` is at the Overleaf project root, run from the repository root:

```powershell
git subtree push --prefix overleaf-report overleaf SP4-Report:master
```

If Git asks for credentials, type your token directly into the terminal prompt. Do not paste it into chat.

## If GitHub import is unavailable

Some Overleaf accounts restrict GitHub sync. If the GitHub option is not visible, create a ZIP file of this folder and upload it as a new Overleaf project. The report will still compile normally.

The SDU class loads `minted`; keep the included `latexmkrc` file because it enables shell escape for Overleaf builds.

## After editing in Overleaf

If GitHub sync is enabled, use Overleaf's GitHub sync panel to push Overleaf changes back to GitHub. Pull those changes in VS Code before making more local edits.