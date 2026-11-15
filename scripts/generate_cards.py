"""Generate animated MENDEX-styled SVG project cards for GitHub README."""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectCard:
    filename: str
    index: str
    title: str
    category: str
    line1: str
    line2: str
    stack: tuple[str, ...]
    accent: str  # "#E52B42" (crimson) or "#F2B632" (mustard)
    status: str
    cta: str


CARDS: tuple[ProjectCard, ...] = (
    ProjectCard(
        filename="droidlens.svg",
        index="01",
        title="DroidLens",
        category="SYSTEMS & MOBILE",
        line1="Ultra-low latency Android-to-Windows USB webcam",
        line2="(15-35 ms) with APCM v2 protocol & virtual cameras.",
        stack=("Python", "CameraX", "IMFVirtualCamera", "DirectShow"),
        accent="#E52B42",
        status="PUBLIC",
        cta="OPEN ->",
    ),
    ProjectCard(
        filename="gastroforge.svg",
        index="02",
        title="GastroForge",
        category="MULTI-TENANT SAAS",
        line1="Restaurant ERP monorepo with PostgreSQL RLS,",
        line2="OpenAPI TypeScript codegen & Redis telemetry.",
        stack=("NestJS 11", "React Router v7", "Prisma", "PostgreSQL"),
        accent="#F2B632",
        status="PRIVATE",
        cta="PRIVATE REPO",
    ),
    ProjectCard(
        filename="potetosapp.svg",
        index="03",
        title="PotetosApp",
        category="FULL-STACK · REAL-TIME",
        line1="Restaurant operations platform with kitchen module,",
        line2="table tracking, RBAC & live Socket.io updates.",
        stack=("React", "Node.js", "PostgreSQL", "Socket.io"),
        accent="#F2B632",
        status="LIVE DEMO",
        cta="OPEN ->",
    ),
    ProjectCard(
        filename="bravobot.svg",
        index="04",
        title="BravoBot_Quantix",
        category="AI & RAG",
        line1="Conversational RAG assistant for I.U. Pascual Bravo",
        line2="using hybrid retrieval, ChromaDB & Gemini API.",
        stack=("Python", "FastAPI", "ChromaDB", "Docker"),
        accent="#E52B42",
        status="PUBLIC",
        cta="OPEN ->",
    ),
    ProjectCard(
        filename="little-pets.svg",
        index="05",
        title="Little_Pets",
        category="WEB PLATFORM",
        line1="Pet adoption platform with automated workflows,",
        line2="dynamic PDF generation, email dispatch & RBAC.",
        stack=("Node.js", "Express", "MongoDB", "Render"),
        accent="#E52B42",
        status="PUBLIC",
        cta="OPEN ->",
    ),
    ProjectCard(
        filename="gastroforge-vision.svg",
        index="06",
        title="gastroforge-vision",
        category="COMPUTER VISION",
        line1="Real-time table monitoring & chair-aware spatial",
        line2="tracking telemetry powered by Ultralytics YOLO.",
        stack=("Python", "YOLO", "OpenCV", "Pytest"),
        accent="#F2B632",
        status="PUBLIC",
        cta="OPEN ->",
    ),
)


def render_halftone_dots() -> str:
    """Render subtle MENDEX-style halftone dots in the top-right corner."""
    dots = []
    for row in range(3):
        for col in range(5):
            cx = 342 + col * 13
            cy = 22 + row * 13
            dots.append(f'<circle cx="{cx}" cy="{cy}" r="1.6" fill="#3A302C"/>')
    return "\n    ".join(dots)


def render_stack_pills(stack: tuple[str, ...]) -> str:
    """Render compact tech pills along the bottom of the card."""
    pills = []
    x = 24
    y = 148
    for item in stack:
        width = max(48, len(item) * 7 + 16)
        pills.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="22" rx="4" fill="#241D1B" stroke="#3A302C" stroke-width="1"/>'
            f'<text x="{x + width / 2:.1f}" y="{y + 14.5}" text-anchor="middle" fill="#F4EDE4" '
            f'font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10.5">{html.escape(item)}</text>'
        )
        x += width + 7
    return "\n  ".join(pills)


def render_card_svg(card: ProjectCard, idx: int) -> str:
    """Render a single animated MENDEX project card SVG."""
    delay = f"{idx * 0.35:.2f}s"
    halftone = render_halftone_dots()
    pills = render_stack_pills(card.stack)
    cta_color = card.accent if card.status != "PRIVATE" else "#B3A79C"
    status_x = 396 - (len(card.status) * 6.8 + 26)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="190" viewBox="0 0 420 190" role="img" aria-label="{html.escape(card.title)} - {html.escape(card.category)}">
  <defs>
    <clipPath id="card-clip-{card.index}">
      <rect x="0" y="0" width="412" height="182" rx="12"/>
    </clipPath>
  </defs>

  <!-- Hard shadow (MENDEX pop-minimal) -->
  <rect x="6" y="6" width="412" height="182" rx="12" fill="{card.accent}"/>

  <!-- Main card surface -->
  <rect x="0.75" y="0.75" width="410.5" height="180.5" rx="11.5" fill="#120E0E" stroke="#3A302C" stroke-width="1.5"/>

  <!-- Subtle halftone corner -->
  <g opacity="0.85">
    {halftone}
  </g>

  <!-- Animated top accent sweep -->
  <g clip-path="url(#card-clip-{card.index})">
    <rect x="0" y="0" width="412" height="3" fill="#241D1B"/>
    <rect x="-120" y="0" width="120" height="3" fill="{card.accent}">
      <animate attributeName="x" values="-120;420" dur="3.6s" begin="{delay}" repeatCount="indefinite"/>
    </rect>
  </g>

  <!-- Index + Category -->
  <rect x="24" y="20" width="28" height="20" rx="4" fill="#241D1B" stroke="{card.accent}" stroke-width="1"/>
  <text x="38" y="34" text-anchor="middle" fill="{card.accent}" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" font-weight="700">{card.index}</text>
  <text x="62" y="34" fill="#B3A79C" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10.5" font-weight="700" letter-spacing="0.8">{html.escape(card.category)}</text>

  <!-- Pulsing status badge -->
  <g>
    <circle cx="{status_x + 10:.1f}" cy="30" r="3.5" fill="{card.accent}">
      <animate attributeName="opacity" values="1;0.35;1" dur="2s" begin="{delay}" repeatCount="indefinite"/>
    </circle>
    <circle cx="{status_x + 10:.1f}" cy="30" r="3.5" fill="none" stroke="{card.accent}" stroke-width="1.2">
      <animate attributeName="r" values="3.5;9" dur="2s" begin="{delay}" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0.85;0" dur="2s" begin="{delay}" repeatCount="indefinite"/>
    </circle>
    <text x="{status_x + 20:.1f}" y="34" fill="#F4EDE4" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10" font-weight="700" letter-spacing="0.6">{html.escape(card.status)}</text>
  </g>

  <!-- Title + CTA -->
  <text x="24" y="72" fill="#F4EDE4" font-family="ui-sans-serif, system-ui, -apple-system, sans-serif" font-size="22" font-weight="800" letter-spacing="-0.3">{html.escape(card.title)}</text>
  <text x="392" y="70" text-anchor="end" fill="{cta_color}" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" font-weight="700">{html.escape(card.cta)}</text>

  <!-- Description -->
  <text x="24" y="98" fill="#B3A79C" font-family="ui-sans-serif, system-ui, -apple-system, sans-serif" font-size="12.5">{html.escape(card.line1)}</text>
  <text x="24" y="116" fill="#B3A79C" font-family="ui-sans-serif, system-ui, -apple-system, sans-serif" font-size="12.5">{html.escape(card.line2)}</text>

  <!-- Stack pills -->
  {pills}
</svg>
"""


def main() -> int:
    out_dir = Path("assets/cards")
    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, card in enumerate(CARDS):
        svg = render_card_svg(card, idx)
        (out_dir / card.filename).write_text(svg, encoding="utf-8")
    print(f"Generated {len(CARDS)} animated SVG cards in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
