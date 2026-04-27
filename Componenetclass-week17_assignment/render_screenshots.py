"""Render captured pytest output files into terminal-style PNG screenshots."""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import re

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"
SHOTS = ROOT.parent / "reports" / "test-screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

BG = (24, 24, 28)
HEADER_BG = (45, 45, 52)
TXT = (220, 220, 220)
DIM = (140, 140, 150)
GREEN = (78, 201, 122)
RED = (240, 90, 90)
YELLOW = (240, 200, 90)
BLUE = (96, 170, 255)
MAGENTA = (200, 130, 220)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        ("C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"),
        "C:/Windows/Fonts/cour.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    return ImageFont.load_default()


def colorize(line: str) -> list[tuple[str, tuple[int, int, int]]]:
    out: list[tuple[str, tuple[int, int, int]]] = []
    if "PASSED" in line:
        idx = line.index("PASSED")
        out.append((line[:idx], TXT))
        out.append(("PASSED", GREEN))
        out.append((line[idx + 6 :], DIM))
        return out
    if "FAILED" in line:
        idx = line.index("FAILED")
        out.append((line[:idx], TXT))
        out.append(("FAILED", RED))
        out.append((line[idx + 6 :], DIM))
        return out
    if line.startswith("===") or "test session" in line:
        return [(line, MAGENTA)]
    if re.match(r"^\d+ passed", line.strip()) or "passed" in line and "warning" in line:
        return [(line, GREEN)]
    if line.strip().startswith("collected") or "collecting" in line:
        return [(line, BLUE)]
    if line.strip().startswith("--") or line.startswith("=="):
        return [(line, DIM)]
    if "warning" in line.lower() or "deprecation" in line.lower():
        return [(line, YELLOW)]
    return [(line, TXT)]


def render(text_path: Path, title: str, out_path: Path, max_lines: int = 60) -> None:
    raw_bytes = text_path.read_bytes()
    if raw_bytes.startswith(b"\xff\xfe"):
        text_data = raw_bytes.decode("utf-16-le", errors="replace")
    elif raw_bytes.startswith(b"\xfe\xff"):
        text_data = raw_bytes.decode("utf-16-be", errors="replace")
    else:
        text_data = raw_bytes.decode("utf-8", errors="replace")
    lines_raw = text_data.replace("\r", "").splitlines()
    # keep last N lines so we have the summary
    if len(lines_raw) > max_lines:
        lines = lines_raw[-max_lines:]
    else:
        lines = lines_raw

    f = _font(13)
    fb = _font(13, bold=True)
    fh = _font(14, bold=True)

    pad = 14
    line_h = 17
    # measure widest line
    sample = max(lines, key=len) if lines else ""
    char_w = f.getlength("M")
    width = max(900, int(pad * 2 + char_w * (min(len(sample), 130) + 2)))
    header_h = 32
    height = header_h + pad * 2 + line_h * len(lines)

    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    # window header
    d.rectangle([0, 0, width, header_h], fill=HEADER_BG)
    cx = 14
    for col in [(255, 95, 86), (255, 189, 46), (39, 201, 63)]:
        d.ellipse([cx, 10, cx + 12, 22], fill=col)
        cx += 20
    d.text((width // 2 - len(title) * 4, 8), title, fill=TXT, font=fh)

    y = header_h + pad
    for line in lines:
        if len(line) > 160:
            line = line[:157] + "..."
        x = pad
        for chunk, color in colorize(line):
            d.text((x, y), chunk, fill=color, font=f)
            x += int(f.getlength(chunk))
        y += line_h

    img.save(out_path, "PNG")
    print("wrote", out_path)


if __name__ == "__main__":
    render(RUNS / "unit.txt", "PowerShell - pytest app/tests/unit", SHOTS / "01_component.png", 28)
    render(RUNS / "integration.txt", "PowerShell - pytest app/tests/integration", SHOTS / "02_integration.png", 32)
    render(RUNS / "smoke.txt", "PowerShell - pytest app/tests/smoke (E2E)", SHOTS / "03_e2e.png", 14)
    render(RUNS / "stress.txt", "PowerShell - pytest app/tests/stress", SHOTS / "04_stress.png", 22)
    render(RUNS / "benchmarks.txt", "PowerShell - pytest app/tests/benchmarks (load)", SHOTS / "05_benchmarks.png", 18)
