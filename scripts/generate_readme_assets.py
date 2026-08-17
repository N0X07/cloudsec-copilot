from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = PROJECT_ROOT / "docs" / "assets"


def font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts") / name,
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


MONO = font("consola.ttf", 22)
MONO_BOLD = font("consolab.ttf", 22)
UI = font("segoeui.ttf", 24)
UI_BOLD = font("segoeuib.ttf", 28)


def run(command: list[str]) -> str:
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    output = result.stdout.strip()
    if result.stderr.strip():
        output = f"{output}\n{result.stderr.strip()}".strip()
    return output


def terminal_screenshot(title: str, command: str, output: str, filename: str) -> None:
    lines = [f"$ {command}", *output.splitlines()]
    max_chars = max(len(line) for line in lines)
    width = max(980, min(1500, 58 + max_chars * 13))
    line_height = 32
    height = 86 + len(lines) * line_height + 34

    image = Image.new("RGB", (width, height), "#0b1020")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, width - 18, height - 18), radius=18, fill="#111827")
    draw.ellipse((42, 43, 56, 57), fill="#ef4444")
    draw.ellipse((66, 43, 80, 57), fill="#f59e0b")
    draw.ellipse((90, 43, 104, 57), fill="#22c55e")
    draw.text((126, 34), title, fill="#d1d5db", font=UI)

    y = 82
    for index, line in enumerate(lines):
        color = "#93c5fd" if index == 0 else "#e5e7eb"
        line_font = MONO_BOLD if index == 0 else MONO
        draw.text((42, y), line, fill=color, font=line_font)
        y += line_height

    image.save(ASSET_DIR / filename)


def box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    title: str,
    subtitle: str,
    *,
    fill: str,
    outline: str = "#334155",
) -> None:
    draw.rounded_rectangle(xy, radius=12, fill=fill, outline=outline, width=2)
    x1, y1, x2, _ = xy
    draw.text((x1 + 18, y1 + 18), title, fill="#f8fafc", font=UI_BOLD)
    draw.text((x1 + 18, y1 + 56), subtitle, fill="#cbd5e1", font=UI)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    draw.line((*start, *end), fill="#64748b", width=4)
    ex, ey = end
    sx, sy = start
    if abs(ex - sx) > abs(ey - sy):
        direction = 1 if ex > sx else -1
        points = [(ex, ey), (ex - direction * 14, ey - 8), (ex - direction * 14, ey + 8)]
    else:
        direction = 1 if ey > sy else -1
        points = [(ex, ey), (ex - 8, ey - direction * 14), (ex + 8, ey - direction * 14)]
    draw.polygon(points, fill="#64748b")


def architecture_diagram() -> None:
    width, height = 1680, 940
    image = Image.new("RGB", (width, height), "#f8fafc")
    draw = ImageDraw.Draw(image)
    draw.text((56, 38), "CloudSec Copilot Architecture", fill="#0f172a", font=font("segoeuib.ttf", 42))
    draw.text(
        (58, 92),
        "Security-event API with platform CLI, Docker/Kubernetes/Terraform, observability, SLO, and runbook layers",
        fill="#475569",
        font=UI,
    )

    box(draw, (70, 170, 350, 270), "CloudTrail events", "Synthetic AWS logs", fill="#1e3a8a")
    box(draw, (450, 170, 730, 270), "FastAPI ingestion", "Validation + API", fill="#075985")
    box(draw, (830, 170, 1110, 270), "Database", "SQLite / PostgreSQL", fill="#365314")
    box(draw, (1210, 170, 1490, 270), "Rule engine", "Rules + findings", fill="#7c2d12")

    box(draw, (450, 360, 730, 460), "Incident record", "Evidence + severity", fill="#581c87")
    box(draw, (830, 360, 1110, 460), "Report", "ATT&CK + actions", fill="#164e63")
    box(draw, (1210, 360, 1490, 460), "Approval", "Human decision", fill="#7f1d1d")

    box(draw, (450, 550, 730, 650), "AI analyst", "Read-only tools", fill="#3730a3")
    box(draw, (830, 550, 1110, 650), "Audit log", "Tools + approvals", fill="#0f766e")

    platform_top = 745
    draw.rounded_rectangle((55, platform_top - 34, width - 55, 890), radius=18, fill="#e2e8f0", outline="#94a3b8", width=2)
    draw.text((86, platform_top - 18), "Platform / DevOps layer", fill="#0f172a", font=UI_BOLD)
    box(draw, (90, platform_top + 40, 370, platform_top + 130), "cloudsecctl", "health / incidents", fill="#0f172a")
    box(draw, (430, platform_top + 40, 710, platform_top + 130), "Docker", "Image + Compose", fill="#1d4ed8")
    box(draw, (770, platform_top + 40, 1050, platform_top + 130), "Kubernetes", "Probes + rollout", fill="#0369a1")
    box(draw, (1110, platform_top + 40, 1390, platform_top + 130), "Terraform AWS", "ECS / ALB / RDS", fill="#4c1d95")
    box(draw, (1430, platform_top + 40, 1620, platform_top + 130), "SRE docs", "SLO / runbook", fill="#14532d")

    arrow(draw, (350, 220), (450, 220))
    arrow(draw, (730, 220), (830, 220))
    arrow(draw, (1110, 220), (1210, 220))
    arrow(draw, (1350, 270), (590, 360))
    arrow(draw, (730, 410), (830, 410))
    arrow(draw, (1110, 410), (1210, 410))
    arrow(draw, (590, 460), (590, 550))
    arrow(draw, (730, 600), (830, 600))
    arrow(draw, (1350, 460), (970, 550))
    arrow(draw, (230, platform_top + 40), (540, 270))
    arrow(draw, (910, platform_top + 40), (910, 650))
    arrow(draw, (1250, platform_top + 40), (1250, 270))

    image.save(ASSET_DIR / "architecture.png")


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    architecture_diagram()
    terminal_screenshot(
        "Infrastructure validation",
        "cloudsecctl validate-infra",
        run([".venv/Scripts/cloudsecctl.exe", "validate-infra"]),
        "validate-infra.png",
    )
    terminal_screenshot(
        "Test suite",
        "python -m pytest",
        run([".venv/Scripts/python.exe", "-m", "pytest"]),
        "pytest.png",
    )
    terminal_screenshot(
        "Kubernetes workloads",
        "kubectl -n cloudsec-copilot get pods,svc",
        run(["kubectl", "-n", "cloudsec-copilot", "get", "pods,svc"]),
        "kubectl-pods.png",
    )


if __name__ == "__main__":
    main()
