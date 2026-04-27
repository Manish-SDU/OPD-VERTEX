# Componentclass — Week 17 Assignment

Two PDFs for the OPD-Vertex group assignment:

- `Assignment1_Microservices_Redesign.pdf` — microservices redesign at 50M users / 1M+ concurrent (4 pages).
- `Assignment2_Testing_Report.pdf` — 10 component + 5 integration + 5 end-to-end + 5 load/stress tests (3 pages, with real terminal screenshots).

Authors: Aleksandra Kwiatkowska, Gabija Staskeviciute, Gabriele Solazzo, Luigi Colluto, Manish Raj Moriche, Mats Pete Haertel.

## Folder layout

```
Componenetclass-week17_assignment/
├── Assignment1_Microservices_Redesign.pdf
├── Assignment2_Testing_Report.pdf
├── build_pdfs.py            # builds both PDFs from screenshots + diagrams
├── render_screenshots.py    # turns runs/*.txt into terminal-style PNGs
├── diagrams/                # *.puml sources + rendered *.png
├── screenshots/             # 01..05 PNGs embedded in the testing PDF
├── runs/                    # raw `pytest -v` captures (gitignored, regenerable)
└── tools/                   # plantuml.jar (gitignored, download locally)
```

## Regenerate after a change

Prereqs (one time): Python 3.12, Java 21, then on Python 3.12:

```powershell
py -3.12 -m pip install --user fpdf2 pillow pypdf pymupdf
```

Drop `plantuml.jar` (1.2024.7+) into `tools/` if it isn't there.

### Edit text or layout only

```powershell
py -3.12 Componenetclass-week17_assignment\build_pdfs.py
```

### Edit a diagram (`diagrams/*.puml`)

```powershell
java -jar Componenetclass-week17_assignment\tools\plantuml.jar `
     -tpng -o . Componenetclass-week17_assignment\diagrams\*.puml
py -3.12 Componenetclass-week17_assignment\build_pdfs.py
```

### Refresh test screenshots (re-run the suites)

```powershell
.\.venv312\Scripts\python.exe -m pytest app/tests/unit          -v --tb=line --color=no `
    | Tee-Object Componenetclass-week17_assignment\runs\unit.txt
.\.venv312\Scripts\python.exe -m pytest app/tests/integration   -v --tb=line --color=no `
    --ignore=app/tests/integration/test_real_llm.py `
    | Tee-Object Componenetclass-week17_assignment\runs\integration.txt
.\.venv312\Scripts\python.exe -m pytest app/tests/smoke         -v --tb=line --color=no `
    | Tee-Object Componenetclass-week17_assignment\runs\smoke.txt
.\.venv312\Scripts\python.exe -m pytest app/tests/stress        -v --tb=line --color=no `
    | Tee-Object Componenetclass-week17_assignment\runs\stress.txt
.\.venv312\Scripts\python.exe -m pytest app/tests/benchmarks    -v --tb=line --color=no `
    | Tee-Object Componenetclass-week17_assignment\runs\benchmarks.txt

py -3.12 Componenetclass-week17_assignment\render_screenshots.py
py -3.12 Componenetclass-week17_assignment\build_pdfs.py
```

`render_screenshots.py` auto-detects the UTF-16 BOM that `Tee-Object` writes, so the captures render correctly.
