"""Generate the profile README assets in the visual language of colacco.github.io.

Every SVG is self-contained (fonts and images embedded as data URIs) so it renders
inside GitHub's <img> sandbox, and is emitted in a light and a dark variant that the
README switches with <picture> + prefers-color-scheme.

Usage:  python scripts/build_assets.py
Needs:  Pillow (text metrics + image resizing). Inputs live in scripts/vendor/.
"""

from __future__ import annotations

import base64
import io
import json
from html import escape
from pathlib import Path

from PIL import Image, ImageFont

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "scripts" / "vendor"
OUT = ROOT / "assets"

# --------------------------------------------------------------------------- tokens
# Mirrors personal-portfolio/src/index.css (:root and [data-pf-theme='dark']).
THEMES = {
    "light": {
        "bg0": "#eef0fc", "bg1": "#f5f6ff", "bg2": "#e9ebfa",
        "surface": "#ffffff", "text": "#232532", "muted": "#595d6c",
        "border": "#cfd3e5", "rule": "#cfd0e6",
        "accent": "#5d5294", "accent_soft": "#796cbf",
        "accent_tint": "rgba(121,108,191,0.1)", "glow": "rgba(121,108,191,0.3)",
        "on_accent": "#ffffff",
        "code_bg": ("#1d2033", "#171a2a", "#101220"),
        "code_border": "#343953", "code_line": "#2a2e44",
        "statue_opacity": 0.55, "card_shadow": True,
    },
    "dark": {
        "bg0": "#141624", "bg1": "#121421", "bg2": "#0d0f18",
        "surface": "#232532", "text": "#e9e9ed", "muted": "#9397ab",
        "border": "#3f424d", "rule": "#454864",
        "accent": "#b5abfc", "accent_soft": "#9184d9",
        "accent_tint": "rgba(145,132,217,0.14)", "glow": "rgba(145,132,217,0.42)",
        "on_accent": "#161826",
        "code_bg": ("#2a2f4a", "#232741", "#1c1f33"),
        "code_border": "#4a5175", "code_line": "#3a3f5c",
        "statue_opacity": 0.28, "card_shadow": False,
    },
}

TOKEN = {  # HeroCodePanel.tsx TOKEN_COLOR
    "cm": "#9aa0bd", "kw": "#c4a2ff", "ty": "#7fd4c1",
    "st": "#f0b982", "pr": "#8f93ad", "in": "#e6e8f5",
}

SANS = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"
MONO = "'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace"


# --------------------------------------------------------------------------- helpers
def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def font_face(*which: str) -> str:
    table = {
        "inter-400": ("Inter", 400), "inter-500": ("Inter", 500), "inter-600": ("Inter", 600),
        "jbm-400": ("JetBrains Mono", 400), "jbm-700": ("JetBrains Mono", 700),
    }
    rules = []
    for key in which:
        family, weight = table[key]
        data = b64((VENDOR / "fonts" / f"{key}.woff2").read_bytes())
        rules.append(f"@font-face{{font-family:'{family}';font-weight:{weight};"
                     f"src:url(data:font/woff2;base64,{data}) format('woff2');}}")
    return "".join(rules)


_metric_cache: dict[tuple[str, float], ImageFont.FreeTypeFont] = {}


def text_width(text: str, font: str, size: float, tracking: float = 0.0) -> float:
    """Advance width in px. font: 'inter-600' | 'inter-400' | 'jbm-400'."""
    key = (font, size)
    if key not in _metric_cache:
        _metric_cache[key] = ImageFont.truetype(str(VENDOR / "fonts" / f"{font}.woff"), size)
    return _metric_cache[key].getlength(text) + tracking * len(text)


GLYPHS = json.loads((VENDOR / "phosphor-glyphs.json").read_text())


def glyph(name: str, x: float, y: float, size: float, fill: str) -> str:
    """Phosphor (regular) icon in a size×size box with top-left at x,y."""
    s = size / 1024
    return (f'<path d="{GLYPHS[name]["d"]}" fill="{fill}" '
            f'transform="translate({x:.2f} {y + 960 * s:.2f}) scale({s:.5f} {-s:.5f})"/>')


def icon_data_uri(filename: str, theme: str) -> str:
    """Brand icon as a data URI, recolored where it would vanish on that theme."""
    if filename == "ollama":
        filename = "ollama-dark.svg" if theme == "dark" else "ollama-light.svg"
    svg = (VENDOR / "icons" / filename).read_text(encoding="utf-8")
    simple_icons = {"nodedotjs.svg": "#5FA04E", "rabbitmq.svg": "#FF6600"}  # monochrome → brand color
    if filename in simple_icons:
        svg = svg.replace("<svg ", f'<svg fill="{simple_icons[filename]}" ', 1)
    if theme == "dark" and filename == "aws.svg":
        svg = svg.replace("#252F3E", "#e9e9ed")
    return "data:image/svg+xml;base64," + b64(svg.encode("utf-8"))


def jpeg_data_uri(img: Image.Image, quality: int = 72) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + b64(buf.getvalue())


def svg_doc(w: float, h: float, label: str, style: str, body: str, defs: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
            f'viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="{escape(label)}">\n'
            f"<title>{escape(label)}</title>\n"
            f"<defs><style>{style}</style>{defs}</defs>\n{body}\n</svg>\n")


def write(name: str, content: str) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  {name:<34} {len(content.encode()) / 1024:7.1f} KB")


def orbit_mark(cx: float, cy: float, t: dict, r: float = 12) -> str:
    """BrandMark: two flattened rings orbiting a dot (Orbit.tsx)."""
    ry = r * 0.42
    return (
        f'<g transform="translate({cx} {cy})">'
        f'<g><ellipse rx="{r}" ry="{ry:.2f}" fill="none" stroke="{t["accent"]}" stroke-width="1.5"/>'
        f'<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="9s" repeatCount="indefinite"/></g>'
        f'<g opacity="0.75"><ellipse rx="{r}" ry="{ry:.2f}" fill="none" stroke="{t["accent_soft"]}" stroke-width="1.5"/>'
        f'<animateTransform attributeName="transform" type="rotate" from="60" to="-300" dur="12s" repeatCount="indefinite"/></g>'
        f'<circle r="3" fill="{t["accent"]}"/></g>'
    )


# --------------------------------------------------------------------------- hero
HELLO = "Hello, I'm"
NAME_LINES = ["Gabriel", "Colaço"]
TAGLINE = "Software Engineer · Back-end · Cloud · DevOps"
SUB_LINES = [
    "Building a multi-tenant control plane on AWS at Solutions BI,",
    "with Terraform and Docker. Exploring RAG, local LLMs and MCP.",
]

CODE: list[list[tuple[str, str]]] = [
    [("cm", "// engineer.ts")],
    [("kw", "export type "), ("ty", "Engineer"), ("pr", " = {")],
    [("in", "  role"), ("pr", ": "), ("ty", "string"), ("pr", ";")],
    [("in", "  company"), ("pr", ": "), ("ty", "string"), ("pr", ";")],
    [("in", "  focus"), ("pr", ": "), ("ty", "string"), ("pr", "[];")],
    [("in", "  exploring"), ("pr", ": "), ("ty", "string"), ("pr", "[];")],
    [("pr", "};")],
    [],
    [("kw", "export const "), ("in", "gabriel"), ("pr", ": "), ("ty", "Engineer"), ("pr", " = {")],
    [("in", "  role"), ("pr", ": "), ("st", '"software engineer"'), ("pr", ",")],
    [("in", "  company"), ("pr", ": "), ("st", '"Solutions BI"'), ("pr", ",")],
    [("in", "  focus"), ("pr", ": ["), ("st", '"backend"'), ("pr", ", "), ("st", '"cloud"'),
     ("pr", ", "), ("st", '"devops"'), ("pr", "],")],
    [("in", "  exploring"), ("pr", ": ["), ("st", '"RAG"'), ("pr", ", "), ("st", '"local LLMs"'),
     ("pr", ", "), ("st", '"MCP"'), ("pr", "],")],
    [("pr", "};")],
]


def typed_text(lines, x, y0, lh, font, size, tracking, fill, start, per_char):
    """Text revealed char by char with SMIL <set>. Returns (svg, caret_frames, end_time)."""
    weight = {"inter-600": 600, "inter-400": 400}[font]
    parts, frames, t = [], [], start
    for li, line in enumerate(lines):
        y = y0 + li * lh
        spans = []
        for ci, ch in enumerate(line):
            t += per_char
            spans.append(f'<tspan opacity="0">{escape(ch)}'
                         f'<set attributeName="opacity" to="1" begin="{t:.3f}s" fill="freeze"/></tspan>')
            frames.append((t, x + text_width(line[: ci + 1], font, size, tracking), y))
        parts.append(f'<text x="{x}" y="{y}" font-family="{SANS}" font-weight="{weight}" font-size="{size}" '
                     f'letter-spacing="{tracking}" fill="{fill}" xml:space="preserve">{"".join(spans)}</text>')
    return "".join(parts), frames, t


def hero(theme: str) -> str:
    t = THEMES[theme]
    W, H, X = 1200, 480, 64

    statue = Image.open(VENDOR / "images" / "hero_statue.png").convert("L").resize((720, 480), Image.LANCZOS)
    statue_uri = jpeg_data_uri(statue, 70)

    defs = f"""
<clipPath id="frame"><rect width="{W}" height="{H}" rx="18"/></clipPath>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="0.6">
  <stop offset="0" stop-color="{t['bg0']}"/><stop offset="0.42" stop-color="{t['bg1']}"/><stop offset="1" stop-color="{t['bg2']}"/>
</linearGradient>
<radialGradient id="glow" cx="{W * 0.78}" cy="{H * 0.38}" r="{W * 0.36}" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="{t['glow']}"/><stop offset="0.72" stop-color="{t['glow']}" stop-opacity="0"/>
</radialGradient>
<pattern id="grid" width="64" height="64" patternUnits="userSpaceOnUse">
  <path d="M64 0H0V64" fill="none" stroke="{t['border']}" stroke-width="1"/>
</pattern>
<radialGradient id="gridFade" cx="0.5" cy="0.4" r="0.6">
  <stop offset="0" stop-color="#fff"/><stop offset="0.76" stop-color="#fff" stop-opacity="0"/>
</radialGradient>
<mask id="gridMask"><rect width="{W}" height="{H}" fill="url(#gridFade)"/></mask>
<linearGradient id="statueFade" x1="0" x2="1">
  <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.25" stop-color="#fff" stop-opacity="0"/>
  <stop offset="0.5" stop-color="#fff" stop-opacity="0.55"/><stop offset="0.85" stop-color="#fff"/>
</linearGradient>
<mask id="statueMask"><rect x="{W - 720}" width="720" height="{H}" fill="url(#statueFade)"/></mask>
<linearGradient id="codeBg" x1="0" y1="0" x2="0.55" y2="1">
  <stop offset="0" stop-color="{t['code_bg'][0]}"/><stop offset="0.55" stop-color="{t['code_bg'][1]}"/><stop offset="1" stop-color="{t['code_bg'][2]}"/>
</linearGradient>
<linearGradient id="codeHair" x1="0" x2="1">
  <stop offset="0" stop-color="#c4a2ff" stop-opacity="0"/><stop offset="0.4" stop-color="#c4a2ff" stop-opacity="0.55"/>
  <stop offset="0.7" stop-color="#7fd4c1" stop-opacity="0.4"/><stop offset="1" stop-color="#7fd4c1" stop-opacity="0"/>
</linearGradient>
<filter id="codeShadow" x="-20%" y="-20%" width="140%" height="160%">
  <feDropShadow dx="0" dy="24" stdDeviation="22" flood-color="#0a0820" flood-opacity="{0.45 if theme == 'light' else 0.8}"/>
</filter>
"""
    style = font_face("inter-400", "inter-600", "jbm-400", "jbm-700") + (
        ".caret{animation:blink 1s steps(1,end) infinite}"
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}")

    # name typed letter by letter (useTypedHero: ~82ms/char, 480ms pause, fast sub)
    name_size, name_track = 76, -0.04 * 76
    name_svg, name_frames, t_name = typed_text(
        NAME_LINES, X, 222, 78, "inter-600", name_size, name_track, t["text"], 0.35, 0.085)
    dot_x = X + text_width(NAME_LINES[-1], "inter-600", name_size, name_track) + 1
    t_dot = t_name + 0.48
    dot = (f'<text x="{dot_x:.1f}" y="300" font-family="{SANS}" font-weight="600" font-size="{name_size}" '
           f'fill="{t["accent"]}" opacity="0">.<set attributeName="opacity" to="1" begin="{t_dot:.3f}s" fill="freeze"/></text>')
    sub_svg, sub_frames, _ = typed_text(
        SUB_LINES, X, 402, 27, "inter-400", 16.5, 0, t["muted"], t_dot + 0.15, 0.016)

    def caret(frames, h, w, dy, begin, end=None):
        xs = ";".join(f"{fx + 3:.1f}" for _, fx, _ in frames)
        ys = ";".join(f"{fy - dy:.1f}" for _, _, fy in frames)
        span = frames[-1][0] - frames[0][0]
        kt = ";".join(f"{(ft - frames[0][0]) / span:.4f}" for ft, _, _ in frames)
        vis = f'<set attributeName="visibility" to="visible" begin="{begin:.3f}s"/>'
        if end is not None:
            vis += f'<set attributeName="visibility" to="hidden" begin="{end:.3f}s"/>'
        return (f'<rect class="caret" x="{X}" y="{frames[0][2] - dy}" width="{w}" height="{h}" fill="{t["accent"]}" visibility="hidden">'
                f'{vis}'
                f'<animate attributeName="x" values="{xs}" keyTimes="{kt}" calcMode="discrete" begin="{frames[0][0]:.3f}s" dur="{span:.3f}s" fill="freeze"/>'
                f'<animate attributeName="y" values="{ys}" keyTimes="{kt}" calcMode="discrete" begin="{frames[0][0]:.3f}s" dur="{span:.3f}s" fill="freeze"/>'
                f'</rect>')

    name_caret = caret(name_frames, 60, 16, 56, 0.3, t_dot)
    sub_caret = caret(sub_frames, 19, 8, 15, t_dot + 0.15)

    # code panel (HeroCodePanel.tsx)
    PX, PY, PW = 652, 74, 488
    LH, FS, head_h = 19.5, 12.5, 44
    PH = head_h + 18 + LH * len(CODE) + 14
    code_lines = []
    for i, toks in enumerate(CODE):
        y = PY + head_h + 18 + LH * i + 13
        spans = "".join(
            f'<tspan fill="{TOKEN[k]}"{" font-style=\"italic\"" if k == "cm" else ""}>{escape(s)}</tspan>'
            for k, s in toks) or " "
        code_lines.append(
            f'<g opacity="0"><set attributeName="opacity" to="1" begin="{0.5 + i * 0.11:.2f}s" fill="freeze"/>'
            f'<text x="{PX + 36}" y="{y:.1f}" text-anchor="end" font-family="{MONO}" font-size="{FS}" fill="#9298b5">{i + 1}</text>'
            f'<text x="{PX + 50}" y="{y:.1f}" font-family="{MONO}" font-size="{FS}" xml:space="preserve">{spans}</text></g>')
    run_w = 118
    panel = f"""
<g filter="url(#codeShadow)"><rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="14" fill="url(#codeBg)"/></g>
<rect x="{PX + 0.5}" y="{PY + 0.5}" width="{PW - 1}" height="{PH - 1}" rx="13.5" fill="none" stroke="{t['code_border']}"/>
<rect x="{PX + 14}" y="{PY}" width="{PW - 28}" height="1" fill="url(#codeHair)"/>
<line x1="{PX}" y1="{PY + head_h}" x2="{PX + PW}" y2="{PY + head_h}" stroke="{t['code_line']}"/>
<circle cx="{PX + 20}" cy="{PY + 22}" r="4.5" fill="#e06a72"/>
<circle cx="{PX + 34}" cy="{PY + 22}" r="4.5" fill="#e0b45f"/>
<circle cx="{PX + 48}" cy="{PY + 22}" r="4.5" fill="#68c48f"/>
<rect x="{PX + 64}" y="{PY + 14.5}" width="15" height="15" rx="3" fill="#3178c6"/>
<text x="{PX + 71.5}" y="{PY + 25}" text-anchor="middle" font-family="{SANS}" font-weight="600" font-size="8" fill="#fff">TS</text>
<text x="{PX + 86}" y="{PY + 26}" font-family="{MONO}" font-size="11.5" fill="#c8cbe0">engineer.ts</text>
<rect x="{PX + PW - run_w - 14}" y="{PY + 9}" width="{run_w}" height="26" rx="6" fill="none" stroke="#c4a2ff" stroke-opacity="0.5"/>
{glyph('play', PX + PW - run_w - 3, PY + 16.5, 11, '#c4a2ff')}
<text x="{PX + PW - run_w + 13}" y="{PY + 26}" font-family="{MONO}" font-size="12" fill="#c4a2ff">Run profile</text>
{''.join(code_lines)}
"""
    body = f"""
<g clip-path="url(#frame)">
<rect width="{W}" height="{H}" fill="url(#bg)"/>
<image href="{statue_uri}" x="{W - 720}" y="0" width="720" height="{H}" opacity="{t['statue_opacity']}" mask="url(#statueMask)" preserveAspectRatio="xMidYMid slice"/>
<rect width="{W}" height="{H}" fill="url(#glow)" opacity="0.45"/>
<rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#gridMask)" opacity="0.32"/>
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="17.5" fill="none" stroke="{t['border']}"/>
{orbit_mark(X + 13, 44, t)}
<text x="{X + 34}" y="49" font-family="{MONO}" font-weight="700" font-size="14" fill="{t['text']}">colaco.dev</text>
<text x="{X}" y="132" font-family="{MONO}" font-size="13" fill="{t['muted']}">{HELLO}</text>
{name_svg}{dot}{name_caret}
<text x="{X}" y="358" font-family="{SANS}" font-weight="600" font-size="21" letter-spacing="-0.4" fill="{t['text']}">{escape(TAGLINE)}</text>
{sub_svg}{sub_caret}
{panel}
"""
    return svg_doc(W, H, "Gabriel Colaço — Software Engineer · Back-end · Cloud · DevOps", style, body, defs)


# --------------------------------------------------------------------------- section heading
def heading(kicker: str, title: str, theme: str) -> str:
    t = THEMES[theme]
    body = (f'<text x="2" y="20" font-family="{MONO}" font-size="13" fill="{t["accent_soft"]}">{escape(kicker)}</text>'
            f'<text x="0" y="62" font-family="{SANS}" font-weight="600" font-size="34" letter-spacing="-1" fill="{t["text"]}">{escape(title)}</text>')
    return svg_doc(1200, 78, title, font_face("inter-600", "jbm-400"), body)


# --------------------------------------------------------------------------- stack
STACK = [("TypeScript", "typescript.svg"), ("Python", "python.svg"), ("Node.js", "nodedotjs.svg"),
         ("FastAPI", "fastapi.svg"), ("React", "react.svg"), ("PostgreSQL", "postgresql.svg"),
         ("RabbitMQ", "rabbitmq.svg"), ("Docker", "docker.svg"), ("Terraform", "terraform.svg"),
         ("AWS", "aws.svg")]


def stack(theme: str) -> str:
    """One SkillCard (stack/SkillCard.tsx) with the tools I use day to day, in a single row."""
    t = THEMES[theme]
    W, H = 1200, 132
    defs = ('<filter id="cardShadow" x="-10%" y="-20%" width="120%" height="160%">'
            '<feDropShadow dx="0" dy="1" stdDeviation="1" flood-color="#292b31" flood-opacity="0.06"/>'
            '<feDropShadow dx="0" dy="10" stdDeviation="15" flood-color="#292b31" flood-opacity="0.07"/></filter>')
    shadow = ' filter="url(#cardShadow)"' if t["card_shadow"] else ""
    parts = [f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 25}" rx="16" fill="{t["surface"]}" stroke="{t["border"]}"{shadow}/>']
    cell_w = (W - 32) / len(STACK)
    for i, (name, icon) in enumerate(STACK):
        cx = 16 + cell_w * i + cell_w / 2
        parts.append(f'<image href="{icon_data_uri(icon, theme)}" x="{cx - 16:.1f}" y="22" width="32" height="32"/>')
        parts.append(f'<text x="{cx:.1f}" y="80" text-anchor="middle" font-family="{SANS}" '
                     f'font-weight="500" font-size="12" fill="{t["text"]}">{escape(name)}</text>')
    return svg_doc(W, H, "Stack: " + ", ".join(n for n, _ in STACK), font_face("inter-500"), "".join(parts), defs)


# --------------------------------------------------------------------------- buttons
def button(label: str, icon: str, accent: bool, theme: str) -> str:
    """Hero CTA (HeroIntro.tsx): outlined, mono 12.5px, tracking .04em, 16px icon."""
    t = THEMES[theme]
    size, track = 12.5, 0.5
    W, H = 22 + 16 + 9 + text_width(label, "jbm-400", size, track) + 22, 48
    color = t["accent"] if accent else t["text"]
    stroke = t["accent"] if accent else t["border"]
    body = (f'<rect x="0.5" y="0.5" width="{W - 1:.1f}" height="{H - 1}" rx="8" fill="none" stroke="{stroke}"/>'
            f'{glyph(icon, 22, 16, 16, color)}'
            f'<text x="47" y="28.5" font-family="{MONO}" font-size="{size}" letter-spacing="{track}" fill="{color}">{escape(label)}</text>')
    return svg_doc(W, H, label, font_face("jbm-400"), body)


# --------------------------------------------------------------------------- project chips
CHIPS = {
    "rag-info": [("Python", "python.svg"), ("FastAPI", "fastapi.svg"), ("LangChain", "langchain.svg"),
                 ("Ollama", "ollama"), ("Chroma", "chroma.svg"), ("MongoDB", "mongodb.svg"),
                 ("React", "react.svg")],
    "pomodoro-inu": [("React", "react.svg"), ("TypeScript", "typescript.svg"),
                     ("Tailwind CSS", "tailwind.svg"), ("Framer Motion", None)],
}


def chips(slug: str, theme: str) -> str:
    """ProjectCard.tsx tech chips: accent-tint pill, mono, 12px icon. Wraps at 520px."""
    t = THEMES[theme]
    size, max_w, h, gap = 11, 520, 24, 8
    x = y = 0
    parts = []
    for name, icon in CHIPS[slug]:
        w = 9 + (16 if icon else 0) + text_width(name, "jbm-400", size) + 9
        if x and x + w > max_w:
            x, y = 0, y + h + gap
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="6" fill="{t["accent_tint"]}"/>')
        tx = x + 9
        if icon:
            parts.append(f'<image href="{icon_data_uri(icon, theme)}" x="{tx:.1f}" y="{y + 6}" width="12" height="12"/>')
            tx += 16
        parts.append(f'<text x="{tx:.1f}" y="{y + 16}" font-family="{MONO}" font-size="{size}" fill="{t["accent"]}">{escape(name)}</text>')
        x += w + gap
    return svg_doc(max_w, y + h, "Stack: " + ", ".join(n for n, _ in CHIPS[slug]), font_face("jbm-400"), "".join(parts))


# --------------------------------------------------------------------------- divider
def divider(theme: str) -> str:
    """Services rule gradient + Experience pulsing dot."""
    t = THEMES[theme]
    W, H = 1200, 32
    defs = (f'<linearGradient id="rule" x1="0" x2="1">'
            f'<stop offset="0" stop-color="{t["rule"]}" stop-opacity="0"/><stop offset="0.15" stop-color="{t["rule"]}"/>'
            f'<stop offset="0.85" stop-color="{t["rule"]}"/><stop offset="1" stop-color="{t["rule"]}" stop-opacity="0"/></linearGradient>')
    body = (f'<rect x="0" y="15.5" width="{W}" height="1" fill="url(#rule)"/>'
            f'<circle cx="{W / 2}" cy="16" r="4" fill="none" stroke="{t["accent"]}" stroke-width="1.5">'
            f'<animate attributeName="r" values="4;14;14" keyTimes="0;0.7;1" dur="2.4s" repeatCount="indefinite"/>'
            f'<animate attributeName="stroke-opacity" values="0.6;0;0" keyTimes="0;0.7;1" dur="2.4s" repeatCount="indefinite"/></circle>'
            f'<circle cx="{W / 2}" cy="16" r="4" fill="{t["accent"]}"/>')
    return svg_doc(W, H, "divider", "", body, defs)


# --------------------------------------------------------------------------- footer
def footer(theme: str) -> str:
    t = THEMES[theme]
    W, H = 420, 64
    body = (f'{orbit_mark(W / 2 - 62, 20, t)}'
            f'<text x="{W / 2 - 42}" y="25" font-family="{MONO}" font-weight="700" font-size="14" fill="{t["text"]}">colaco.dev</text>'
            f'<text x="{W / 2}" y="54" text-anchor="middle" font-family="{MONO}" font-size="11.5" fill="{t["muted"]}">Back-end · Cloud · DevOps · IA</text>')
    return svg_doc(W, H, "colaco.dev", font_face("jbm-400", "jbm-700"), body)


# --------------------------------------------------------------------------- project covers
def covers() -> None:
    """Project screenshots from the portfolio, cropped to 4:3 and resized for the README."""
    for name, anchor in {"rag-info.jpg": 0.0, "pomodoro-inu.jpg": 0.5}.items():
        im = Image.open(VENDOR / "images" / name).convert("RGB")
        w, h = im.size
        ch = round(w * 3 / 4)
        top = round((h - ch) * anchor)
        im = im.crop((0, top, w, top + ch)).resize((800, 600), Image.LANCZOS)
        path = OUT / "projects" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        im.save(path, "JPEG", quality=84, optimize=True, progressive=True)
        print(f"  projects/{name:<25} {path.stat().st_size / 1024:7.1f} KB")


def main() -> None:
    print("writing assets/")
    for th in THEMES:
        write(f"hero-{th}.svg", hero(th))
        write(f"stack-{th}.svg", stack(th))
        write(f"divider-{th}.svg", divider(th))
        write(f"footer-{th}.svg", footer(th))
        for slug, (kicker, title) in {
            "projects": ("// 01 · projects", "Featured projects"),
            "stack": ("// 02 · stack", "My stack"),
            "activity": ("// 03 · activity", "GitHub activity"),
        }.items():
            write(f"headings/{slug}-{th}.svg", heading(kicker, title, th))
        write(f"buttons/portfolio-{th}.svg", button("Portfolio", "globe", True, th))
        write(f"buttons/linkedin-{th}.svg", button("LinkedIn", "linkedin-logo", False, th))
        write(f"buttons/email-{th}.svg", button("Email", "envelope-simple", False, th))
        for slug in CHIPS:
            write(f"chips/{slug}-{th}.svg", chips(slug, th))
    covers()


if __name__ == "__main__":
    main()
