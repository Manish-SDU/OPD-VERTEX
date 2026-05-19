# OPD-Vertex Editable Overleaf Project

This is the clean editable LaTeX project for the OPD-Vertex fourth semester report.

Use this Overleaf project:

https://www.overleaf.com/project/6a0c607dd8122cdf4b668d6a

Do not use the imported project created from the repository `main` branch:

https://www.overleaf.com/project/6a0c73576ee207e406d1f536

`main.tex` is the only report entry point. It uses the SDU `bachelorthesis.cls` template and compiles editable LaTeX content directly.

## Files

- `main.tex` is the Overleaf main file.
- `bachelorthesis.cls` and `assets/sdu_logo.pdf` come from `SDU_Template.zip`.
- `config/metadata.tex` stores title, author, date, and repository metadata.
- `config/preamble.tex` stores layout, colors, tables, figures, and PDF settings.
- `sections/` stores the editable report chapters.
- `assets/charts/` stores chart images used in the validation section.

## Compile on Overleaf

1. Open Overleaf.
2. Create or import a project using this folder.
3. Set the main document to `main.tex`.
4. Set the compiler to `pdfLaTeX`.
5. Recompile.

The SDU class loads `minted`, so `latexmkrc` enables shell escape for Overleaf builds.

To edit the report, change `main.tex`, `config/`, or the files in `sections/`. The source PDF, extraction text, duplicate entry files, and embedded generated PDF appendices were removed so Overleaf has one clear build path.

## SDU template note

The SDU template class and logo have been copied into this project, so Overleaf can compile the report without needing the original `SDU_Template.zip` upload.

## Recommended branch flow

This workspace is currently on the `SP4-Report` branch. Commit report changes there and push that branch to GitHub for version history.

```powershell
git add overleaf-report
git commit -m "Create editable SDU Overleaf report"
git push -u origin SP4-Report
```

Do not paste personal access tokens into chat. If Git asks for credentials, type the token directly into the terminal prompt.

To update the good Overleaf project directly, publish only this folder to the Overleaf Git remote:

```powershell
git subtree push --prefix overleaf-report overleaf SP4-Report:master
```

That command publishes only the `overleaf-report` folder to the Overleaf project root, so `main.tex` appears at the top level in Overleaf.