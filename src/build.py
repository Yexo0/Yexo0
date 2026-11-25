"""Builds the SVG cards of the GitHub profile from src/profile.yml.

Text is converted to vector paths (Inter Tight + Geist), so the cards look the same
everywhere, without depending on the fonts installed on the visitor's machine.

    pip install -r src/requirements.txt
    python src/build.py
"""

from __future__ import annotations

import datetime as dt
import html
import json
import math
from pathlib import Path

import contourpy
import numpy as np
import uharfbuzz as hb
import yaml
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUT = ROOT / "assets"

# ---------------------------------------------------------------- design tokens
# Taken from yexofps.org: black background, near-black cards, Valorant red.
RED = "#FF4655"
RED_DEEP = "#E02F3D"
GOLD = "#F2C14E"
TEXT = "#F5F5F7"
SOFT = "#D1D1D6"
MUTED = "#8E8E93"
DIM = "#5E5E63"
CARD_TOP = "#18181C"
CARD_BOTTOM = "#0D0D10"
LIGHT_TEXT = "#0B0B0D"
LIGHT_MUTED = "#6E6E73"


def num(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


# ---------------------------------------------------------------- text to paths
class Font:
    def __init__(self, file: str):
        path = SRC / "fonts" / file
        self.tt = TTFont(path)
        self.upem = self.tt["head"].unitsPerEm
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))

    def _shape(self, text: str):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True, "liga": True})
        return buf.glyph_infos, buf.glyph_positions

    def width(self, text: str, size: float, tracking: float = 0) -> float:
        infos, pos = self._shape(text)
        s = size / self.upem
        return sum(p.x_advance for p in pos) * s + tracking * size * max(len(infos) - 1, 0)

    def path(self, text: str, size: float, x: float, y: float, tracking: float = 0, anchor: str = "start") -> str:
        w = self.width(text, size, tracking)
        if anchor == "end":
            x -= w
        elif anchor == "middle":
            x -= w / 2
        infos, pos = self._shape(text)
        s = size / self.upem
        cmds, pen_x = [], x
        for info, p in zip(infos, pos):
            name = self.order[info.codepoint]
            pen = SVGPathPen(self.glyphs, ntos=num)
            t = TransformPen(pen, (s, 0, 0, -s, pen_x + p.x_offset * s, y - p.y_offset * s))
            self.glyphs[name].draw(t)
            cmds.append(pen.getCommands())
            pen_x += p.x_advance * s + tracking * size
        return "".join(cmds)

    def wrap(self, text: str, size: float, max_w: float) -> list[str]:
        lines, cur = [], ""
        for word in text.split():
            test = f"{cur} {word}".strip()
            if cur and self.width(test, size) > max_w:
                lines.append(cur)
                cur = word
            else:
                cur = test
        if cur:
            lines.append(cur)
        return lines


DISPLAY = Font("InterTight-800.ttf")
HEAD = Font("InterTight-700.ttf")
SUBHEAD = Font("InterTight-600.ttf")
BODY = Font("Geist-Regular.ttf")
MEDIUM = Font("Geist-Medium.ttf")
SEMI = Font("Geist-SemiBold.ttf")


def text(font: Font, s: str, size: float, x: float, y: float, fill: str = TEXT, tracking: float = 0,
         anchor: str = "start", opacity: float | None = None) -> str:
    op = f' fill-opacity="{num(opacity)}"' if opacity is not None else ""
    return f'<path fill="{fill}"{op} d="{font.path(s, size, x, y, tracking, anchor)}"/>'


# ---------------------------------------------------------------- icons
BRANDS = json.loads((SRC / "icons.json").read_text())

# Line icons drawn on a 24 grid (shapes in the style of Lucide, ISC license).
LINE_ICONS = {
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    "mail": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "crosshair": '<circle cx="12" cy="12" r="10"/><path d="M22 12h-4M6 12H2M12 6V2M12 22v-4"/>',
    "server": '<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 6h.01M6 18h.01"/>',
    "layers": '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65M22 12.65l-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    "arrow": '<path d="M7 17 17 7M7 7h10v10"/>',
    "directory": '<rect x="9" y="2" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3M12 12V8"/>',
    "ticket": '<path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2ZM13 5v2M13 17v2M13 11v2"/>',
    "pulse": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "router": '<rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6.01 18H6M10.01 18H10M15 10v4M17.84 7.17a4 4 0 0 0-5.66 0M20.66 4.34a8 8 0 0 0-11.31 0"/>',
    "box": '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5M12 22V12"/>',
}


def windows_icon() -> str:
    return '<path d="M2 2h9.5v9.5H2zM12.5 2H22v9.5h-9.5zM2 12.5h9.5V22H2zM12.5 12.5H22V22h-9.5z"/>'


def icon(name: str, x: float, y: float, size: float, color: str) -> str:
    """Icon whose top-left corner sits at (x, y)."""
    k = size / 24
    head = f'<g transform="translate({num(x)} {num(y)}) scale({num(k)})"'
    if name in BRANDS:
        return f'{head} fill="{color}"><path d="{BRANDS[name]["path"]}"/></g>'
    if name == "windows":
        return f'{head} fill="{color}">{windows_icon()}</g>'
    if name == "ae":
        inner = SEMI.path("Ae", 11.5, 12, 16.2, -0.02, "middle")
        return (f'{head}><rect x="2" y="2" width="20" height="20" rx="5" fill="none" stroke="{color}" stroke-width="2"/>'
                f'<path fill="{color}" d="{inner}"/></g>')
    shape = LINE_ICONS[name]
    return (f'{head} fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round">{shape}</g>')


# ---------------------------------------------------------------- shared pieces
STYLE = """<style>
.ping{animation:ping 2.6s cubic-bezier(.16,1,.3,1) infinite;transform-box:fill-box;transform-origin:center}
.blink{animation:blink 2.6s ease-in-out infinite}
@keyframes ping{0%{transform:scale(1);opacity:.55}70%,100%{transform:scale(3.2);opacity:0}}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.45}}
@media (prefers-reduced-motion:reduce){.ping,.blink{animation:none}.ping{opacity:0}}
</style>"""


def svg(w: float, h: float, body: str, title: str, defs: str = "") -> str:
    title = html.escape(title, quote=True)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(w)}" height="{num(h)}" viewBox="0 0 {num(w)} {num(h)}" '
            f'role="img" aria-label="{title}"><title>{title}</title>{STYLE}<defs>{defs}</defs>{body}</svg>\n')


def card_defs(uid: str, w: float, h: float, r: float) -> str:
    return (f'<linearGradient id="{uid}-bg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{CARD_TOP}"/><stop offset="1" stop-color="{CARD_BOTTOM}"/></linearGradient>'
            f'<clipPath id="{uid}-clip"><rect width="{num(w)}" height="{num(h)}" rx="{r}"/></clipPath>')


def card_bg(uid: str, w: float, h: float, r: float) -> str:
    return f'<rect width="{num(w)}" height="{num(h)}" rx="{r}" fill="url(#{uid}-bg)"/>'


def card_edge(w: float, h: float, r: float) -> str:
    return (f'<rect x=".5" y=".5" width="{num(w - 1)}" height="{num(h - 1)}" rx="{r - .5}" fill="none" '
            f'stroke="#FFFFFF" stroke-opacity=".09"/>')


def live_dot(x: float, y: float, color: str = RED, r: float = 3.5) -> str:
    return (f'<circle class="ping" cx="{num(x)}" cy="{num(y)}" r="{r}" fill="{color}"/>'
            f'<circle cx="{num(x)}" cy="{num(y)}" r="{r}" fill="{color}"/>')


def icon_badge(name: str, cx: float, cy: float, r: float = 17, size: float = 16) -> str:
    return (f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{r}" fill="#FFFFFF" fill-opacity=".06" stroke="#FFFFFF" stroke-opacity=".1"/>'
            + icon(name, cx - size / 2, cy - size / 2, size, TEXT))


def card_header(icon_name: str, title: str, meta: str, w: float, live: bool = False) -> str:
    out = icon_badge(icon_name, 52, 50)
    out += text(HEAD, title, 24, 80, 58.5, TEXT, -0.03)
    mx = w - 40
    out += text(BODY, meta, 12.5, mx, 55, MUTED, anchor="end")
    if live:
        out += live_dot(mx - BODY.width(meta, 12.5) - 12, 50.6)
    return out


# ---------------------------------------------------------------- topographic lines
def _rdp(points: np.ndarray, eps: float) -> np.ndarray:
    if len(points) < 3:
        return points
    a, b = points[0], points[-1]
    ab = b - a
    n = np.hypot(*ab)
    if n == 0:
        d = np.hypot(*(points - a).T)
    else:
        d = np.abs(ab[0] * (points[:, 1] - a[1]) - ab[1] * (points[:, 0] - a[0])) / n
    i = int(np.argmax(d))
    if d[i] > eps:
        left = _rdp(points[: i + 1], eps)
        right = _rdp(points[i:], eps)
        return np.vstack([left[:-1], right])
    return np.array([a, b])


def _smooth(points: np.ndarray) -> str:
    """Catmull-Rom spline through the points, written as cubic Bezier curves."""
    p = points
    out = [f"M{num(p[0][0])} {num(p[0][1])}"]
    for i in range(len(p) - 1):
        p0 = p[i - 1] if i > 0 else p[i]
        p1, p2 = p[i], p[i + 1]
        p3 = p[i + 2] if i + 2 < len(p) else p2
        c1 = p1 + (p2 - p0) / 6
        c2 = p2 - (p3 - p1) / 6
        out.append(f"C{num(c1[0])} {num(c1[1])} {num(c2[0])} {num(c2[1])} {num(p2[0])} {num(p2[1])}")
    return "".join(out)


def topo_paths(w: float, h: float, seed: int, levels: int = 15) -> str:
    rng = np.random.default_rng(seed)
    nx = 200
    ny = int(nx * h / w)
    xs = np.linspace(-20, w + 20, nx)
    ys = np.linspace(-20, h + 20, ny)
    X, Y = np.meshgrid(xs, ys)
    Z = np.zeros_like(X)
    for _ in range(9):
        cx, cy = rng.uniform(-0.1, 1.1) * w, rng.uniform(-0.2, 1.2) * h
        sx, sy = rng.uniform(0.12, 0.32) * w, rng.uniform(0.25, 0.6) * h
        Z += rng.uniform(-1, 1) * np.exp(-((X - cx) ** 2 / (2 * sx ** 2) + (Y - cy) ** 2 / (2 * sy ** 2)))
    Z += 0.08 * np.sin(X / 47 + rng.uniform(0, 6)) * np.cos(Y / 61 + rng.uniform(0, 6))
    gen = contourpy.contour_generator(X, Y, Z)
    d = []
    for lvl in np.linspace(Z.min(), Z.max(), levels + 2)[1:-1]:
        for line in gen.lines(lvl):
            if len(line) < 6:
                continue
            pts = _rdp(np.asarray(line), 0.6)
            if len(pts) >= 2:
                d.append(_smooth(pts))
    return "".join(d)


# ---------------------------------------------------------------- hero
def build_hero(c: dict) -> str:
    W, H, R = 800, 468, 26
    gx, gy = 620, 190
    defs = card_defs("h", W, H, R) + (
        f'<radialGradient id="h-glow" cx="{gx}" cy="{gy}" r="360" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{RED_DEEP}" stop-opacity=".5"/>'
        f'<stop offset=".45" stop-color="{RED_DEEP}" stop-opacity=".13"/>'
        f'<stop offset="1" stop-color="{RED_DEEP}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="h-fade" cx="{gx}" cy="{gy}" r="520" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="#fff" stop-opacity=".95"/>'
        f'<stop offset=".55" stop-color="#fff" stop-opacity=".35"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity=".08"/></radialGradient>'
        f'<mask id="h-mask"><rect width="{W}" height="{H}" fill="url(#h-fade)"/></mask>'
        f'<linearGradient id="h-shade" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{CARD_BOTTOM}" stop-opacity=".75"/>'
        f'<stop offset=".55" stop-color="{CARD_BOTTOM}" stop-opacity="0"/></linearGradient>'
    )
    b = card_bg("h", W, H, R)
    b += f'<g clip-path="url(#h-clip)">'
    b += f'<rect width="{W}" height="{H}" fill="url(#h-glow)"/>'
    b += (f'<g mask="url(#h-mask)"><path fill="none" stroke="{RED}" stroke-opacity=".42" stroke-width="1" '
          f'd="{topo_paths(W, H, seed=8)}"/></g>')
    b += f'<rect width="{W}" height="{H}" fill="url(#h-shade)"/>'
    # Reticle in the glow: the gaming side
    b += (f'<g fill="none" stroke="#FFFFFF" stroke-opacity=".10">'
          f'<circle cx="{gx}" cy="{gy}" r="62"/><circle cx="{gx}" cy="{gy}" r="118" stroke-dasharray="2 6"/></g>')
    b += (f'<g stroke="{TEXT}" stroke-opacity=".55" stroke-width="2" stroke-linecap="round">'
          f'<path d="M{gx - 22} {gy}h-12M{gx + 22} {gy}h12M{gx} {gy - 22}v-12M{gx} {gy + 22}v12"/></g>')
    b += f'<circle cx="{gx}" cy="{gy}" r="3" fill="{RED}"/>'
    b += "</g>"
    b += card_edge(W, H, R)

    b += text(BODY, c["label"], 13, 40, 52, MUTED)
    bw = MEDIUM.width(c["badge"], 12.5)
    b += text(MEDIUM, c["badge"], 12.5, W - 40, 52, TEXT, anchor="end")
    b += live_dot(W - 40 - bw - 12, 47.6)

    b += text(DISPLAY, c["name"], 128, 33, 178, TEXT, -0.05)
    for i, line in enumerate(c["tagline"]):
        b += text(SUBHEAD, line, 26, 40, 222 + i * 32, TEXT, -0.03)

    # "Two profiles, two worlds" switch, as on the site
    b += text(BODY, c["worlds_label"], 12, 40, 296, MUTED)
    y0, h = 308, 50
    first, second = c["worlds"]
    w1 = 44 + max(SEMI.width(first["name"], 13.5), BODY.width(first["sub"], 11.5)) + 20
    w2 = 44 + max(SEMI.width(second["name"], 13.5), BODY.width(second["sub"], 11.5)) + 22
    b += (f'<rect x="40" y="{y0}" width="{num(w1 + w2 + 12)}" height="{h}" rx="{h / 2}" fill="#FFFFFF" '
          f'fill-opacity=".05" stroke="#FFFFFF" stroke-opacity=".09"/>')
    b += f'<rect x="44" y="{y0 + 4}" width="{num(w1)}" height="{h - 8}" rx="{(h - 8) / 2}" fill="{TEXT}"/>'
    b += f'<circle cx="67" cy="{y0 + 25}" r="15" fill="{RED_DEEP}"/>' + icon(first["icon"], 59, y0 + 17, 16, "#FFFFFF")
    b += text(SEMI, first["name"], 13.5, 90, y0 + 22, LIGHT_TEXT)
    b += text(BODY, first["sub"], 11.5, 90, y0 + 37, "#48484A")
    x2 = 44 + w1 + 6
    b += (f'<circle cx="{num(x2 + 23)}" cy="{y0 + 25}" r="15" fill="#FFFFFF" fill-opacity=".08" '
          f'stroke="#FFFFFF" stroke-opacity=".1"/>') + icon(second["icon"], x2 + 16, y0 + 18, 14, TEXT)
    b += text(SEMI, second["name"], 13.5, x2 + 46, y0 + 22, TEXT)
    b += text(BODY, second["sub"], 11.5, x2 + 46, y0 + 37, MUTED)

    b += f'<path d="M40 386H{W - 40}" stroke="#FFFFFF" stroke-opacity=".08"/>'
    col = (W - 80) / len(c["stats"])
    for i, s in enumerate(c["stats"]):
        x = 40 + i * col
        b += text(HEAD, s["value"], 28, x - 1, 424, TEXT, -0.035)
        b += text(BODY, s["label"], 12, x, 444, MUTED)
    title = f'{c["name"]}: {" ".join(c["tagline"])}'
    return svg(W, H, b, title, defs)


# ---------------------------------------------------------------- buttons
def build_button(c: dict) -> str:
    H = 44
    label_w = SEMI.width(c["label"], 14)
    W = 18 + 16 + 9 + label_w + 20
    primary = c.get("primary", False)
    fill = RED_DEEP if primary else "#111114"
    b = f'<rect width="{num(W)}" height="{H}" rx="{H / 2}" fill="{fill}"/>'
    if not primary:
        b += (f'<rect x=".5" y=".5" width="{num(W - 1)}" height="{H - 1}" rx="{(H - 1) / 2}" fill="none" '
              f'stroke="#FFFFFF" stroke-opacity=".16"/>')
    b += icon(c["icon"], 18, (H - 16) / 2, 16, "#FFFFFF")
    b += text(SEMI, c["label"], 14, 18 + 16 + 9, 27, "#FFFFFF")
    return svg(W, H, b, c["label"])


# ---------------------------------------------------------------- now
def build_now(c: dict) -> str:
    W, R = 800, 26
    row_h = 60
    H = 96 + row_h * len(c["items"]) + 14
    meta = c["meta"].replace("{month}", dt.date.today().strftime("%b %Y"))
    b = card_bg("n", W, H, R) + card_edge(W, H, R)
    b += card_header("clock", c["title"], meta, W, live=True)
    top = 96
    for i, it in enumerate(c["items"]):
        y = top + i * row_h
        b += text(BODY, f"{i + 1:02d}", 12, 40, y + 21, DIM)
        # Tree connector
        b += (f'<path d="M{72} {y - (row_h - 34) if i else y + 4}V{y + 16}h10" fill="none" stroke="#FFFFFF" '
              f'stroke-opacity=".16" stroke-linecap="round"/>')
        b += text(MEDIUM, it["title"], 15.5, 92, y + 21, TEXT, -0.005)
        b += text(BODY, it["sub"], 13, 92, y + 41, MUTED)
    return svg(W, H, b, f'{c["title"]}: ' + "; ".join(i["title"] for i in c["items"]), card_defs("n", W, H, R))


# ---------------------------------------------------------------- section heading (light + dark variants)
def build_heading(c: dict, dark: bool) -> str:
    W, H = 800, 62
    fg, muted = (TEXT, MUTED) if dark else (LIGHT_TEXT, LIGHT_MUTED)
    b = text(HEAD, c["title"], 34, 2, 44, fg, -0.04)
    lw = MEDIUM.width(c["link"], 13)
    b += text(MEDIUM, c["link"], 13, W - 24, 40, muted, anchor="end")
    b += (f'<circle cx="{W - 9}" cy="35.5" r="9" fill="{muted}" fill-opacity=".12"/>'
          + icon("arrow", W - 15, 29.5, 12, fg))
    _ = lw
    return svg(W, H, b, c["title"])


# ---------------------------------------------------------------- project cards
def visual_curve(x0: float, y0: float, w: float, h: float) -> str:
    """After Effects graph editor: the cubic-bezier(.16, 1, .3, 1) ease used on the site."""
    gw = 190
    b = ""
    for k in range(4):
        y = y0 + k * h / 3
        b += f'<path d="M{x0} {num(y)}h{gw}" stroke="#FFFFFF" stroke-opacity=".06"/>'
    px0, py0, px3, py3 = x0 + 4, y0 + h - 4, x0 + gw - 6, y0 + 6
    dx, dy = px3 - px0, py3 - py0
    p1 = (px0 + .16 * dx, py0 + 1 * dy)
    p2 = (px0 + .30 * dx, py3)
    b += (f'<path d="M{num(px0)} {num(py0)}L{num(p1[0])} {num(p1[1])}M{num(px3)} {num(py3)}L{num(p2[0])} {num(p2[1])}" '
          f'stroke="{SOFT}" stroke-opacity=".45" stroke-dasharray="3 3"/>')
    curve = f'M{num(px0)} {num(py0)}C{num(p1[0])} {num(p1[1])} {num(p2[0])} {num(p2[1])} {num(px3)} {num(py3)}'
    b += f'<path d="{curve}" fill="none" stroke="{RED}" stroke-opacity=".35" stroke-width="7" filter="url(#blur)"/>'
    b += f'<path d="{curve}" fill="none" stroke="{RED}" stroke-width="2.4" stroke-linecap="round"/>'
    for (hx, hy) in (p1, p2):
        b += f'<circle cx="{num(hx)}" cy="{num(hy)}" r="3.6" fill="{CARD_BOTTOM}" stroke="{TEXT}" stroke-width="1.4"/>'
    for (hx, hy) in ((px0, py0), (px3, py3)):
        b += f'<rect x="{num(hx - 4)}" y="{num(hy - 4)}" width="8" height="8" transform="rotate(45 {num(hx)} {num(hy)})" fill="{TEXT}"/>'
    # Chips on the right
    cx = x0 + gw + 22
    for i, label in enumerate(("592 presets", "22 edit styles", "After Effects 2025")):
        cy = y0 + 4 + i * 30
        cw = MEDIUM.width(label, 11.5) + 22
        b += (f'<rect x="{num(cx)}" y="{num(cy)}" width="{num(cw)}" height="24" rx="12" fill="#FFFFFF" fill-opacity=".05" '
              f'stroke="#FFFFFF" stroke-opacity=".09"/>')
        b += text(MEDIUM, label, 11.5, cx + 11, cy + 16, SOFT)
    return b


def visual_handles(x0: float, y0: float, w: float, h: float) -> str:
    b = ""
    sw = 200
    b += (f'<rect x="{x0}" y="{y0}" width="{sw}" height="34" rx="17" fill="#FFFFFF" fill-opacity=".05" '
          f'stroke="#FFFFFF" stroke-opacity=".12"/>')
    b += icon("search", x0 + 13, y0 + 10, 14, MUTED)
    b += text(MEDIUM, "@yexofps", 13.5, x0 + 36, y0 + 22, TEXT)
    b += f'<rect x="{num(x0 + 36 + MEDIUM.width("@yexofps", 13.5) + 3)}" y="{y0 + 10}" width="1.5" height="15" fill="{RED}" class="blink"/>'
    b += text(MEDIUM, "1 / 7 free", 12.5, x0 + w, y0 + 22, TEXT, anchor="end")
    plats = ["twitch", "youtube", "instagram", "tiktok", "kick", "bluesky", "steam"]
    free = "kick"
    step = (w - 2) / len(plats)
    for i, p in enumerate(plats):
        cx = x0 + 16 + i * step
        cy = y0 + 70
        if p == free:
            b += f'<circle cx="{num(cx)}" cy="{cy}" r="16" fill="{RED_DEEP}" fill-opacity=".18" stroke="{RED}" stroke-width="1.4"/>'
            b += icon(p, cx - 7.5, cy - 7.5, 15, TEXT)
        else:
            b += f'<circle cx="{num(cx)}" cy="{cy}" r="16" fill="#FFFFFF" fill-opacity=".05" stroke="#FFFFFF" stroke-opacity=".1"/>'
            b += icon(p, cx - 7.5, cy - 7.5, 15, MUTED)
    return b


def visual_timeline(x0: float, y0: float, w: float, h: float) -> str:
    b = text(MEDIUM, "ShadowPlay · 21:34:12", 11.5, x0, y0 + 14, MUTED)
    chip = "120 FPS · CFR"
    cw = SEMI.width(chip, 11) + 20
    b += (f'<rect x="{num(x0 + w - cw)}" y="{y0}" width="{num(cw)}" height="22" rx="11" fill="{RED_DEEP}" '
          f'fill-opacity=".16" stroke="{RED}" stroke-opacity=".5"/>')
    b += text(SEMI, chip, 11, x0 + w - cw / 2, y0 + 15, TEXT, anchor="middle")
    ty, th = y0 + 52, 30
    b += f'<rect x="{x0}" y="{ty}" width="{w}" height="{th}" rx="7" fill="#FFFFFF" fill-opacity=".05"/>'
    rng = np.random.default_rng(3)
    n = 58
    for i in range(n):
        bx = x0 + 6 + i * (w - 12) / n
        bh = 4 + abs(math.sin(i * .5)) * 8 + rng.uniform(0, 10)
        b += f'<rect x="{num(bx)}" y="{num(ty + th / 2 - bh / 2)}" width="2.2" height="{num(bh)}" rx="1.1" fill="#FFFFFF" fill-opacity=".16"/>'
    kills = [x0 + w * .46, x0 + w * .55, x0 + w * .66]
    cs, ce = x0 + w * .33, x0 + w * .76
    b += (f'<rect x="{num(cs)}" y="{ty - 2}" width="{num(ce - cs)}" height="{th + 4}" rx="8" fill="{RED_DEEP}" '
          f'fill-opacity=".16" stroke="{RED}" stroke-width="1.4"/>')
    b += text(HEAD, "3K", 15, cs, ty - 10, TEXT, -0.02)
    for kx in kills:
        b += (f'<rect x="{num(kx - 4.5)}" y="{ty - 14.5}" width="9" height="9" fill="{RED}" '
              f'transform="rotate(45 {num(kx)} {ty - 10})"/>')
        b += f'<path d="M{num(kx)} {ty - 4}V{ty + th}" stroke="{RED}" stroke-opacity=".7"/>'
    b += text(BODY, "-4 s", 10.5, cs, ty + th + 16, DIM)
    b += text(BODY, "+3 s", 10.5, ce, ty + th + 16, DIM, anchor="end")
    return b


def visual_browser(x0: float, y0: float, w: float, h: float) -> str:
    bh = h + 4
    b = (f'<rect x="{x0}" y="{y0}" width="{w}" height="{bh}" rx="10" fill="#000000" fill-opacity=".55" '
         f'stroke="#FFFFFF" stroke-opacity=".1"/>')
    for i, col in enumerate((RED, "#FFFFFF", "#FFFFFF")):
        op = "1" if i == 0 else ".18"
        b += f'<circle cx="{x0 + 14 + i * 12}" cy="{y0 + 13}" r="3.6" fill="{col}" fill-opacity="{op}"/>'
    uw = 130
    ux = x0 + w / 2 - uw / 2
    b += f'<rect x="{num(ux)}" y="{y0 + 5}" width="{uw}" height="16" rx="8" fill="#FFFFFF" fill-opacity=".06"/>'
    b += text(MEDIUM, "yexofps.org", 10.5, x0 + w / 2, y0 + 16.5, SOFT, anchor="middle")
    b += f'<path d="M{x0} {y0 + 26}h{w}" stroke="#FFFFFF" stroke-opacity=".08"/>'
    # Mini hero
    b += (f'<defs><radialGradient id="mini-glow" cx="{num(x0 + w * .78)}" cy="{y0 + 58}" r="90" gradientUnits="userSpaceOnUse">'
          f'<stop offset="0" stop-color="{RED_DEEP}" stop-opacity=".55"/><stop offset="1" stop-color="{RED_DEEP}" stop-opacity="0"/>'
          f'</radialGradient></defs>')
    b += f'<rect x="{x0 + 1}" y="{y0 + 27}" width="{w - 2}" height="{bh - 28}" rx="9" fill="url(#mini-glow)"/>'
    # Mini side rail
    b += f'<rect x="{x0 + 10}" y="{y0 + 36}" width="16" height="{bh - 46}" rx="8" fill="#FFFFFF" fill-opacity=".06"/>'
    b += text(DISPLAY, "Y", 10, x0 + 18, y0 + 48, RED, anchor="middle")
    for k in range(3):
        b += f'<rect x="{x0 + 14}" y="{y0 + 56 + k * 10}" width="8" height="5" rx="1.5" fill="#FFFFFF" fill-opacity=".22"/>'
    b += text(DISPLAY, "Yexo", 28, x0 + 38, y0 + 60, TEXT, -0.05)
    b += f'<rect x="{x0 + 39}" y="{y0 + 67}" width="120" height="5" rx="2.5" fill="#FFFFFF" fill-opacity=".3"/>'
    b += f'<rect x="{x0 + 39}" y="{y0 + 76}" width="80" height="5" rx="2.5" fill="#FFFFFF" fill-opacity=".18"/>'
    b += f'<rect x="{x0 + 39}" y="{y0 + 86}" width="34" height="10" rx="5" fill="{RED_DEEP}"/>'
    b += f'<rect x="{x0 + 77}" y="{y0 + 86}" width="34" height="10" rx="5" fill="none" stroke="#FFFFFF" stroke-opacity=".25"/>'
    gx, gy = x0 + w * .78, y0 + 62
    b += f'<circle cx="{num(gx)}" cy="{gy}" r="20" fill="none" stroke="#FFFFFF" stroke-opacity=".18"/>'
    b += f'<circle cx="{num(gx)}" cy="{gy}" r="2.5" fill="{RED}"/>'
    return b


VISUALS = {"curve": visual_curve, "handles": visual_handles, "timeline": visual_timeline, "browser": visual_browser}


def build_project(c: dict, index: int) -> str:
    W, H, R = 396, 292, 24
    uid = f"p{index}"
    defs = card_defs(uid, W, H, R) + '<filter id="blur" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="4"/></filter>'
    b = card_bg(uid, W, H, R) + card_edge(W, H, R)
    b += text(BODY, f"{index:02d}", 12, 26, 38, MUTED)
    b += (f'<circle cx="{W - 42}" cy="34" r="17" fill="#FFFFFF" fill-opacity=".07"/>'
          + icon("arrow", W - 49, 27, 14, TEXT))
    b += f'<g clip-path="url(#{uid}-clip)">' + VISUALS[c["visual"]](26, 62, W - 52, 100) + "</g>"
    b += text(HEAD, c["title"], 30, 25, 206, TEXT, -0.04)
    lines = BODY.wrap(c["desc"], 13.5, W - 52)
    for i, line in enumerate(lines[:2]):
        b += text(BODY, line, 13.5, 26, 230 + i * 19, MUTED)
    color = GOLD if "dev" in c["status"].lower() else RED
    sy = 274
    b += f'<circle cx="30" cy="{sy - 4.5}" r="3.5" fill="{color}"/>'
    b += text(MEDIUM, c["status"], 12, 40, sy, TEXT)
    b += text(BODY, "  ·  " + c["meta"], 12, 40 + MEDIUM.width(c["status"], 12), sy, MUTED)
    return svg(W, H, b, f'{c["title"]}: {c["desc"]}', defs)


# ---------------------------------------------------------------- stack
def _wrap_chips(widths: list[float], max_w: float, gap: float) -> list[list[int]]:
    """Greedy wrap, then the narrowest width that keeps the same number of lines (balanced rows)."""
    def greedy(limit: float) -> list[list[int]]:
        lines, cur, x = [], [], 0.0
        for i, w in enumerate(widths):
            need = w if not cur else x + gap + w
            if cur and need > limit:
                lines.append(cur)
                cur, x = [i], w
            else:
                cur.append(i)
                x = need
        return lines + ([cur] if cur else [])

    target = len(greedy(max_w))
    lo, hi = max(widths), max_w
    for _ in range(30):
        mid = (lo + hi) / 2
        if len(greedy(mid)) <= target:
            hi = mid
        else:
            lo = mid
    return greedy(hi)


def build_stack(c: dict) -> str:
    W, R = 800, 26
    label_x, chips_x, max_x = 40, 186, W - 40
    ch, gap, row_gap, group_gap = 32, 8, 10, 26
    rows = []  # (group index, y)
    layout = []
    y = 96
    for gi, g in enumerate(c["groups"]):
        widths = [12 + 15 + 8 + MEDIUM.width(it["label"], 13) + 14 for it in g["items"]]
        rows.append((gi, y))
        for li, line in enumerate(_wrap_chips(widths, max_x - chips_x, gap)):
            if li:
                y += ch + row_gap
            x = chips_x
            for i in line:
                layout.append((x, y, widths[i], g["items"][i]))
                x += widths[i] + gap
        y += ch + group_gap
    H = y - group_gap + 36
    b = card_bg("s", W, H, R) + card_edge(W, H, R)
    b += card_header("layers", c["title"], c["meta"], W)
    for gi, gy in rows:
        g = c["groups"][gi]
        b += text(BODY, f"{gi + 1:02d}", 11.5, label_x, gy + 21, DIM)
        b += text(MEDIUM, g["name"], 13, label_x + 24, gy + 21, SOFT)
        if gi:
            b += f'<path d="M{label_x} {gy - 13}H{W - 40}" stroke="#FFFFFF" stroke-opacity=".06"/>'
    for x, y, cw, it in layout:
        b += (f'<rect x="{num(x)}" y="{y}" width="{num(cw)}" height="{ch}" rx="{ch / 2}" fill="#FFFFFF" '
              f'fill-opacity=".045" stroke="#FFFFFF" stroke-opacity=".09"/>')
        b += icon(it["icon"], x + 12, y + (ch - 15) / 2, 15, TEXT)
        b += text(MEDIUM, it["label"], 13, x + 12 + 15 + 8, y + 20.5, "#E5E5EA")
    title = f'{c["title"]}: ' + "; ".join(f'{g["name"]}: ' + ", ".join(i["label"] for i in g["items"]) for g in c["groups"])
    return svg(W, H, b, title, card_defs("s", W, H, R))


# ---------------------------------------------------------------- footer
def build_footer(c: dict) -> str:
    W, H, R = 800, 84, 22
    defs = card_defs("f", W, H, R) + (
        f'<linearGradient id="f-y" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{RED}"/>'
        f'<stop offset="1" stop-color="{RED_DEEP}"/></linearGradient>')
    b = card_bg("f", W, H, R) + card_edge(W, H, R)
    name = c["name"]
    b += text(DISPLAY, name[0], 30, 30, 53, "url(#f-y)", -0.05)
    b += text(DISPLAY, name[1:], 30, 30 + DISPLAY.width(name[0], 30, -0.05) - 1.5, 53, TEXT, -0.05)
    nx = 30 + DISPLAY.width(name, 30, -0.05) + 18
    b += f'<path d="M{num(nx)} 30v24" stroke="#FFFFFF" stroke-opacity=".12"/>'
    b += text(BODY, c["text"], 13, nx + 18, 47, MUTED)
    b += text(MEDIUM, c["link"], 13, W - 58, 47, TEXT, anchor="end")
    b += (f'<circle cx="{W - 38}" cy="42.5" r="13" fill="#FFFFFF" fill-opacity=".07"/>'
          + icon("arrow", W - 44, 36.5, 12, TEXT))
    return svg(W, H, b, f'{name}: {c["text"]}', defs)


# ---------------------------------------------------------------- main
def main() -> None:
    c = yaml.safe_load((SRC / "profile.yml").read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    files = {
        "hero.svg": build_hero(c["hero"]),
        "now.svg": build_now(c["now"]),
        "projects-dark.svg": build_heading(c["projects_heading"], dark=True),
        "projects-light.svg": build_heading(c["projects_heading"], dark=False),
        "stack.svg": build_stack(c["stack"]),
        "footer.svg": build_footer(c["footer"]),
    }
    for btn in c["buttons"]:
        files[f'btn-{btn["id"]}.svg'] = build_button(btn)
    for i, p in enumerate(c["projects"], 1):
        files[f'project-{p["id"]}.svg'] = build_project(p, i)
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
        print(f"{name:28s} {len(content) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
