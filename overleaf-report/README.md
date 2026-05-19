# OPD-Vertex Editable Overleaf Project

This folder is a standalone Overleaf project for the OPD-Vertex fourth semester report. The report content has been extracted from `4th_Semester_OPDVertex_Report.pdf` and rewritten into editable LaTeX section files.

`main.tex` uses the SDU `bachelorthesis.cls` template and compiles normal LaTeX content so the text, tables, figures, and structure can be edited directly in Overleaf.

## Files

- `main.tex` is the Overleaf main file.
- `editable-report.tex` mirrors the same editable document structure and is kept as a compatibility entry point.
- `bachelorthesis.cls` and `assets/sdu_logo.pdf` come from `SDU_Template.zip`.
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

The SDU class loads `minted`, so `latexmkrc` enables shell escape for Overleaf builds.

The original PDF is kept only as a reference. To edit the report, change the files in `sections/` instead of replacing a PDF.

## SDU template note

The SDU template class and logo have been copied into this project, so Overleaf can compile the report without needing the original `SDU_Template.zip` upload.

## Recommended branch flow

This workspace is currently on the `SP4-Report` branch. Commit the report changes there and push that branch to GitHub so Overleaf can import or sync the same branch.

```powershell
git add overleaf-report
git commit -m "Create editable SDU Overleaf report"
git push -u origin SP4-Report
```

Do not paste personal access tokens into chat. If Git asks for credentials, type the token directly into the terminal prompt.

If you want to push directly to the configured Overleaf Git remote, use:

```powershell
git subtree push --prefix overleaf-report overleaf SP4-Report:master
```

That command publishes only the `overleaf-report` folder to the Overleaf project root, so `main.tex` appears at the top level in Overleaf.