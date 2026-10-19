"""Flat 2D animated graphics (cards and charts), the shared look for every channel.

A plan shot can be a Wikimedia image ({"file": ...} / {"query": ...}) or one of these:

    {"card": {"style": "title",   "kicker": "THE BASICS", "text": "What is an ISA?"}}
    {"card": {"style": "stat",    "value": "£20,000", "label": "ISA allowance each tax year", "note": "2026/27 · GOV.UK"}}
    {"card": {"style": "list",    "title": "Four kinds of ISA", "items": ["Cash ISA", "Stocks and shares ISA", "..."]}}
    {"card": {"style": "quote",   "text": "...", "by": "James Madison, Federalist No. 51, 1788"}}
    {"card": {"style": "compare", "left": {"title": "Supporters say", "items": ["..."]},
                                  "right": {"title": "Critics say", "items": ["..."]}}}
    {"chart": {"type": "bar" | "line", "title": "...", "labels": ["2020", "2021"], "values": [1.5, 2.1],
               "prefix": "£", "suffix": "%", "source": "Bank of England", "highlight": 1}}

Each graphic builds in over the first second or two, then holds still, and is written straight to an
MP4 segment that joins the image segments. Drawing uses pycairo; no browser is involved.
"""
from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

import cairo

from .common import ROOT, hex_rgb, log

W, H = 1920, 1080
PAPER = (0.96, 0.93, 0.85)
INK = (0.17, 0.16, 0.15)
MUTED = (0.42, 0.40, 0.36)
RULE = (0.84, 0.80, 0.70)
SANS, SERIF = "Instrument Sans", "Young Serif"
RESERVE = 0          # px kept clear at the bottom for burned-in captions (set per video)
OUTFIT = "scarf"     # stick-figure outfit for this channel: cape, tie or scarf


# ------------------------------------------------------------------ fonts ----
def _install_fonts() -> None:
    """cairo finds fonts through fontconfig, so copy ours into the user font folder once."""
    dest = Path.home() / ".local" / "share" / "fonts"
    src = sorted((ROOT / "assets" / "fonts").glob("*.ttf"))
    if src and not all((dest / f.name).exists() for f in src):
        dest.mkdir(parents=True, exist_ok=True)
        for f in src:
            shutil.copy(f, dest / f.name)
        subprocess.run(["fc-cache", "-f"], capture_output=True)


_install_fonts()


# ---------------------------------------------------------------- helpers ----
def _clamp(x): return max(0.0, min(1.0, x))
def _ease(x): x = _clamp(x); return 1 - (1 - x) ** 3
def _mix(a, b, k): return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))


def _font(cr, size, bold=False, serif=False, italic=False):
    cr.select_font_face(SERIF if serif else SANS,
                        cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL,
                        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)


def _wrap(cr, text, width):
    lines, cur = [], ""
    for word in str(text).split():
        trial = f"{cur} {word}".strip()
        if cur and cr.text_extents(trial).x_advance > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + ([cur] if cur else [])


def _text(cr, s, x, y, colour=INK, a=1.0, align="left"):
    if a <= 0:
        return
    w = cr.text_extents(s).x_advance
    cr.move_to(x - w / 2 if align == "center" else x - w if align == "right" else x, y)
    cr.set_source_rgba(*colour, a)
    cr.show_text(s)


def _fits(cr, text, width, size, min_size, max_lines, **font):
    """Shrink the font until the text wraps into max_lines."""
    while True:
        _font(cr, size, **font)
        lines = _wrap(cr, text, width)
        if len(lines) <= max_lines or size <= min_size:
            return size, lines
        size -= 4


def fmt_value(v, prefix="", suffix="", dp=None):
    dp = 0 if dp is None else dp
    s = f"{abs(v):,.{dp}f}"
    return f"{'-' if v < 0 else ''}{prefix}{s}{suffix}"


# ------------------------------------------------------------------ cards ----
def _frame_base(cr, accent):
    cr.set_source_rgb(*PAPER)
    cr.paint()
    cr.set_source_rgb(*accent)
    cr.rectangle(0, 0, W, 10)
    cr.fill()


def _title(cr, spec, t, accent):
    a = _ease(t / 0.6)
    kicker = spec.get("kicker", "")
    size, lines = _fits(cr, spec.get("text", ""), 1500, 104, 60, 3, serif=True)
    lh = size * 1.18
    block = len(lines) * lh + (70 if kicker else 0)
    y = (H - block) / 2 + size * 0.85
    if kicker:
        _font(cr, 30, bold=True)
        _text(cr, kicker.upper(), W / 2, y - size * 0.85 + 20, accent, a, "center")
        cr.set_source_rgba(*accent, a)
        cr.rectangle(W / 2 - 40, y - size * 0.85 + 40, 80 * _ease(t / 0.9), 5)
        cr.fill()
        y += 70
    _font(cr, size, serif=True)
    for i, line in enumerate(lines):
        k = _ease((t - 0.15 - i * 0.12) / 0.6)
        _text(cr, line, W / 2, y + i * lh + (1 - k) * 24, INK, k, "center")
    return 1.2


def _stat(cr, spec, t, accent):
    k = _ease(t / 0.9)
    value = str(spec.get("value", ""))
    # numbers count up when the value is a plain number with prefix/suffix
    import re
    m = re.fullmatch(r"([^\d\-]*)(-?[\d,]+(?:\.\d+)?)(.*)", value)
    if m and t < 1.0:
        num = float(m.group(2).replace(",", ""))
        dp = len(m.group(2).split(".")[1]) if "." in m.group(2) else 0
        shown = m.group(1) + f"{num * _ease(t / 1.0):,.{dp}f}" + m.group(3)
    else:
        shown = value
    size, _ = _fits(cr, value, 1600, 220, 110, 1, serif=True)
    _font(cr, size, serif=True)
    _text(cr, shown, W / 2, H / 2 + 20, accent, k, "center")
    _font(cr, 46, bold=True)
    for i, line in enumerate(_wrap(cr, spec.get("label", ""), 1400)[:2]):
        _text(cr, line, W / 2, H / 2 + 130 + i * 58, INK, _ease((t - 0.3) / 0.6), "center")
    if spec.get("note"):
        _font(cr, 28)
        _text(cr, spec["note"], W / 2, H - 110 - RESERVE, MUTED, _ease((t - 0.6) / 0.6), "center")
    return 1.4


def _items(cr, items, x, y, width, t, t0, accent, size=44, gap=1.55, max_items=6):
    _font(cr, size)
    for i, item in enumerate(items[:max_items]):
        k = _ease((t - t0 - i * 0.3) / 0.5)
        if k <= 0:
            continue
        lines = _wrap(cr, item, width - 60)[:2]
        cr.set_source_rgba(*accent, k)
        cr.arc(x + 14, y - size * 0.32, 10, 0, 2 * math.pi)
        cr.fill()
        for j, line in enumerate(lines):
            _text(cr, line, x + 50 + (1 - k) * 20, y + j * size * 1.2, INK, k)
        y += size * (gap + 1.2 * (len(lines) - 1))
    return t0 + 0.3 * min(len(items), max_items) + 0.5


def _list(cr, spec, t, accent):
    _font(cr, 64, serif=True)
    _text(cr, spec.get("title", ""), 200, 250, INK, _ease(t / 0.5))
    cr.set_source_rgba(*accent, _ease(t / 0.5))
    cr.rectangle(200, 290, 120 * _ease(t / 0.8), 6)
    cr.fill()
    items = spec.get("items", [])
    size = 54 if len(items) <= 4 else 46 if len(items) <= 6 else 40
    return _items(cr, items, 200, 420, 1500, t, 0.4, accent, size, 1.75)


def _quote(cr, spec, t, accent):
    a = _ease(t / 0.7)
    _font(cr, 260, serif=True)
    _text(cr, "“", 210, 420, accent, a * 0.9)
    size, lines = _fits(cr, spec.get("text", ""), 1350, 64, 40, 5, serif=True)
    lh = size * 1.3
    y = H / 2 - (len(lines) - 1) * lh / 2
    _font(cr, size, serif=True)
    for i, line in enumerate(lines):
        _text(cr, line, 330, y + i * lh, INK, _ease((t - 0.2 - i * 0.1) / 0.6))
    if spec.get("by"):
        _font(cr, 34, bold=True)
        _text(cr, "— " + spec["by"], 330, y + len(lines) * lh + 40, MUTED, _ease((t - 0.8) / 0.6))
    return 1.6


def _compare(cr, spec, t, accent):
    end = 0.0
    tint = _mix(accent, PAPER, 0.86)
    for side, x in (("left", 120), ("right", W / 2 + 30)):
        col = spec.get(side, {})
        k = _ease((t - (0 if side == "left" else 0.25)) / 0.5)
        cr.set_source_rgba(*tint, k)
        cr.rectangle(x, 140, W / 2 - 150, H - 280 - RESERVE)
        cr.fill()
        _font(cr, 60, serif=True)
        _text(cr, col.get("title", ""), x + 50, 255, accent if side == "left" else INK, k)
        end = max(end, _items(cr, col.get("items", []), x + 50, 360, W / 2 - 260, t,
                              0.5 if side == "left" else 0.75, accent, 46, 1.7, 5))
    return end


# ----------------------------------------------------------------- charts ----
def _chart(cr, spec, t, accent):
    labels = [str(x) for x in spec.get("labels", [])]
    values = [float(v) for v in spec.get("values", [])]
    n = min(len(labels), len(values))
    labels, values = labels[:n], values[:n]
    pre, suf = spec.get("prefix", ""), spec.get("suffix", "")
    dp = max((len(str(v).split(".")[1]) if "." in str(v) and not float(v).is_integer() else 0)
             for v in spec.get("values", [0])[:n] or [0])
    dp = min(dp, 2)
    hi = spec.get("highlight", n - 1 if spec.get("type") == "line" else None)

    _font(cr, 56, serif=True)
    title_lines = _wrap(cr, spec.get("title", ""), 1600)[:2]
    for i, line in enumerate(title_lines):
        _text(cr, line, 160, 150 + i * 66, INK, _ease(t / 0.5))
    if spec.get("source"):
        _font(cr, 26)
        _text(cr, "Source: " + spec["source"], 160, H - 60 - RESERVE, MUTED, _ease((t - 0.5) / 0.5))
    if not n:
        return 0.6
    x0, x1 = 230, W - 160
    y0, y1 = 210 + 66 * len(title_lines), H - 170 - RESERVE          # plot area top / baseline
    lo, top = min(0.0, min(values)), max(0.0, max(values))
    if top == lo:
        top = lo + 1
    # tidy gridline step
    raw = (top - lo) / 4
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    top = math.ceil(top / step) * step
    lo = math.floor(lo / step) * step
    ymap = lambda v: y1 - (v - lo) / (top - lo) * (y1 - y0)
    _font(cr, 26)
    g = lo
    while g <= top + 1e-9:
        cr.set_source_rgb(*(INK if abs(g) < 1e-9 else RULE))
        cr.set_line_width(2 if abs(g) < 1e-9 else 1.5)
        cr.move_to(x0, ymap(g))
        cr.line_to(x1, ymap(g))
        cr.stroke()
        _text(cr, fmt_value(g, pre, suf, 0 if float(step).is_integer() else 1), x0 - 18, ymap(g) + 9,
              MUTED, 1, "right")
        g += step

    every = max(1, math.ceil(n / 12))                       # thin out crowded x labels
    if spec.get("type") == "line":
        xs = [x0 + 30 + i * (x1 - x0 - 60) / max(n - 1, 1) for i in range(n)]
        pts = [(x, ymap(v)) for x, v in zip(xs, values)]
        k = _ease((t - 0.3) / 1.6)
        seglen = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
        goal = sum(seglen) * k
        cr.set_source_rgb(*accent)
        cr.set_line_width(7)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.move_to(*pts[0])
        tip = pts[0]
        for (a, b), L in zip(zip(pts, pts[1:]), seglen):
            if goal <= 0:
                break
            f = min(1, goal / L) if L else 1
            tip = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            cr.line_to(*tip)
            goal -= L
        cr.stroke()
        cr.arc(*tip, 11, 0, 2 * math.pi)
        cr.fill()
        _font(cr, 26)
        for i, x in enumerate(xs):
            if i % every == 0 or i == n - 1:
                _text(cr, labels[i], x, y1 + 46, MUTED, 1, "center")
        if k > 0.98 and hi is not None and 0 <= hi < n:
            _font(cr, 40, bold=True)
            _text(cr, fmt_value(values[hi], pre, suf, dp), pts[hi][0], pts[hi][1] - 30, accent,
                  _ease((t - 1.9) / 0.4), "center")
        return 2.4

    # bars
    slot = (x1 - x0) / n
    bw = slot * 0.62
    soft = _mix(accent, PAPER, 0.45)
    for i, v in enumerate(values):
        k = _ease((t - 0.3 - i * 0.12) / 0.7)
        x = x0 + slot * i + (slot - bw) / 2
        yv, yz = ymap(v * k), ymap(0)
        cr.set_source_rgb(*(accent if hi is None or i == hi else soft))
        cr.rectangle(x, min(yv, yz), bw, abs(yz - yv))
        cr.fill()
        _font(cr, 34 if n <= 8 else 26, bold=True)
        _text(cr, fmt_value(v, pre, suf, dp), x + bw / 2, (yv - 16) if v >= 0 else (yv + 40), INK,
              _ease((t - 0.8 - i * 0.12) / 0.4), "center")
        _font(cr, 28 if n <= 8 else 22)
        if i % every == 0:
            for j, line in enumerate(_wrap(cr, labels[i], slot - 10)[:2]):
                _text(cr, line, x + bw / 2, y1 + 44 + j * 32, MUTED, 1, "center")
    return 1.3 + 0.12 * n


DRAW = {"title": _title, "stat": _stat, "list": _list, "quote": _quote, "compare": _compare}


def _chapter_box(cr, chapter, t, accent):
    """On cards and charts the chapter title is a small tag in the top-left corner for 4 seconds."""
    a = _clamp(min(t / 0.3, (4.0 - t) / 0.4))
    if a <= 0:
        return
    _font(cr, 28, bold=True)
    s = chapter.upper()
    w = cr.text_extents(s).x_advance
    cr.set_source_rgba(*accent, a)
    cr.rectangle(60, 44, w + 40, 50)
    cr.fill()
    _text(cr, s, 80, 79, PAPER, a)


def draw(cr, shot: dict, t: float, accent) -> float:
    """Draw one frame at time t; returns when the build-in animation is finished."""
    if "stick" in shot:                        # animated stick-figure scene (moves the whole time)
        from . import sticks
        sticks.scene(cr, shot["stick"], t, accent, OUTFIT)
        return 99.0
    _frame_base(cr, accent)
    if "chart" in shot:
        return _chart(cr, shot["chart"], t, accent)
    spec = shot["card"]
    return DRAW.get(spec.get("style", "title"), _title)(cr, spec, t, accent)


# ---------------------------------------------------------------- output ----
def _reserve(cfg: dict) -> None:
    global RESERVE, OUTFIT
    RESERVE = 130 if cfg.get("burn_captions", True) else 0
    OUTFIT = cfg.get("figure_outfit") or {"history": "cape", "finance": "tie"}.get(cfg.get("channel"), "scarf")


def still(shot: dict, cfg: dict, path: Path) -> Path:
    """The finished graphic as a picture (used for thumbnails when a video has no photos)."""
    global RESERVE
    RESERVE = 0                                    # thumbnails never have captions
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    draw(cairo.Context(surf), shot, 30.0, hex_rgb(cfg.get("colour", "#c0392b")))
    surf.write_to_png(str(path))
    return path


def segment(shot: dict, cfg: dict, seconds: float, fps: int, out: Path, chapter: str = "") -> None:
    accent = hex_rgb(cfg.get("colour", "#c0392b"))
    _reserve(cfg)
    frames = max(1, round(seconds * fps))
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
         "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
         "-pix_fmt", "yuv420p", "-r", str(fps), "-an", str(out)],
        stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    held, settle = None, 99.0
    for i in range(frames):
        t = i / fps
        if held is not None and t > settle:
            ff.stdin.write(held)                     # nothing moves any more: reuse the frame
            continue
        cr = cairo.Context(surf)
        settle = draw(cr, shot, t, accent)
        if chapter:
            _chapter_box(cr, chapter, t, accent)
            settle = max(settle, 4.0)
        surf.flush()
        frame = bytes(surf.get_data())
        if t > settle:
            held = frame
        ff.stdin.write(frame)
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on a graphic: {ff.stderr.read().decode()[-800:]}")


STICK_SCENES = ("walk", "march", "think", "worried", "celebrate", "point", "shrug", "cross_river",
                "deposit", "coins_jar", "crowd_shocked", "dig", "read", "talk", "ship", "lifeboat", "radio")


def check(shot: dict) -> str | None:
    """Return a problem with a graphic shot, or None if it looks fine (used to validate plans)."""
    if "stick" in shot:
        from .sticks import PRESETS
        st = shot["stick"]
        sc = st.get("scene")
        if sc not in STICK_SCENES:
            return f"unknown stick scene '{sc}' (use one of: {', '.join(STICK_SCENES)})"
        names = []
        for key in ("who", "other", "others"):
            v = st.get(key)
            for item in (v if isinstance(v, list) else [v]):
                name = item.get("preset") if isinstance(item, dict) else item
                if name:
                    names.append(name)
        bad = [n for n in names if n not in PRESETS]
        return f"unknown character '{bad[0]}' (use one of: {', '.join(PRESETS)})" if bad else None
    if "chart" in shot:
        c = shot["chart"]
        if c.get("type", "bar") not in ("bar", "line"):
            return "chart type must be bar or line"
        if not c.get("labels") or len(c.get("labels", [])) != len(c.get("values", [])):
            return "chart needs labels and values of the same length"
        try:
            [float(v) for v in c["values"]]
        except (TypeError, ValueError):
            return "chart values must be numbers"
        return None
    style = shot.get("card", {}).get("style", "title")
    if style not in DRAW:
        return f"unknown card style '{style}'"
    return None


