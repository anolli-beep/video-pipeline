"""Thumbnail and YouTube description."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import graphics
from .common import font_path
from .render import chapter_lines

DESC_LIMIT = 4900


def _hero(script: dict, cfg: dict, out: Path) -> str:
    """The plan's thumbnail_file if given, else the first photo, else the first card or chart."""
    shots = [sh for sc in script["scenes"] for sh in sc["shots"]]
    want = script.get("thumbnail_file", "").replace("File:", "")
    for sh in shots:
        if want and sh.get("path") and sh.get("title") == want:
            return sh["path"]
    for sh in shots:
        if sh.get("path"):
            return sh["path"]
    return str(graphics.still(shots[0]["graphic"], cfg, out.with_suffix(".hero.png")))


def _rgb255(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _heavy_font(size: int):
    """Archivo Black if it is in assets/fonts, otherwise the bold channel font."""
    assets = Path(__file__).resolve().parent.parent / "assets"
    for heavy in (assets / "fonts" / "ArchivoBlack-Regular.ttf", assets / "ArchivoBlack-Regular.ttf"):
        if heavy.exists():
            return ImageFont.truetype(str(heavy), size)
    return ImageFont.truetype(font_path(True), size)


def _crack_points(x0, y0, x1, y1, seed):
    """A jagged crack running down through a letter, from above its top right to below its bottom left."""
    import random
    rnd = random.Random(seed)
    w, h = x1 - x0, y1 - y0
    sx, sy = x1 + w * 0.05, y0 - h * 0.22
    ex, ey = x0 + w * 0.05, y1 + h * 0.22
    n = 9
    pts = []
    for i in range(n + 1):
        k = i / n
        x, y = sx + (ex - sx) * k, sy + (ey - sy) * k
        if 0 < i < n:
            x += rnd.uniform(0.04, 0.09) * w * (1 if i % 2 else -1)
            y += rnd.uniform(-0.02, 0.02) * h
        pts.append((x, y))
    return pts


def thumbnail(script: dict, out: Path, cfg: dict | None = None) -> Path:
    """1280x720, documentary style: a black-and-white photo with grain and a dark smoky patch behind the text,
    huge off-white heavy letters, one letter split by a jagged red crack, and an optional red tag.
    Plan options: thumbnail_text (1-4 words; wrap a word in *stars* to choose where the crack goes, otherwise
    the last word), thumbnail_tag (short label for the red box, e.g. "DALLAS, 22 NOV 1963"), thumbnail_file."""
    import hashlib
    import random
    from PIL import ImageEnhance, ImageOps

    cfg = cfg or {}
    red = _rgb255(cfg.get("thumbnail_accent", "#d0242b"))
    ink = (246, 244, 238)
    W_, H_ = 1280, 720
    seed = int(hashlib.md5(script.get("title", "x").encode()).hexdigest()[:6], 16)
    rnd = random.Random(seed)

    hero = _hero(script, cfg, out)
    img = Image.open(hero).convert("RGB")
    if str(hero).endswith(".hero.png"):     # a drawn scene: drop its heading strip at the top
        img = img.crop((0, int(img.height * 0.15), img.width, img.height))
    scale = max(W_ / img.width, H_ / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.LANCZOS)
    left, top = (img.width - W_) // 2, (img.height - H_) // 2
    img = img.crop((left, top, left + W_, top + H_))

    # black and white, punchy contrast, darkened
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g, cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(1.25)
    g = ImageEnhance.Brightness(g).enhance(0.8)
    img = Image.merge("RGB", (g, g, g))

    # text layout
    raw = script.get("thumbnail_text", script["title"]).upper().split()
    starred = [i for i, w in enumerate(raw) if w.startswith("*") and w.endswith("*")]
    words = [w.strip("*") for w in raw]
    hot_i = starred[0] if starred else len(words) - 1
    lines, cur = [], []
    for i, w in enumerate(words):
        if cur and len(" ".join(words[j] for j in cur + [i])) > 12:
            lines.append(cur); cur = [i]
        else:
            cur.append(i)
    lines.append(cur)
    lines = lines[:3]
    size = 170 if len(lines) == 1 else (140 if len(lines) == 2 else 110)
    font = _heavy_font(size)
    probe = ImageDraw.Draw(img)
    width = lambda ln: probe.textlength(" ".join(words[i] for i in ln), font=font)
    while max(width(l) for l in lines) > W_ * 0.74 and size > 70:
        size -= 6
        font = _heavy_font(size)
    gap = int(size * 0.05)
    asc, desc = font.getmetrics()
    block = len(lines) * asc + (len(lines) - 1) * gap
    tag = (script.get("thumbnail_tag") or "").upper()
    tag_h = 76 if tag else 0
    y_text = (H_ - block - (tag_h + 34 if tag else 0)) // 2
    x_text = 62

    # dark smoky patch behind the text, vignette and grain
    smoke = Image.new("L", (W_, H_), 0)
    sd = ImageDraw.Draw(smoke)
    sd.ellipse((x_text - 220, y_text - 160, x_text + max(width(l) for l in lines) + 160, y_text + block + tag_h + 200), fill=235)
    for _ in range(6):
        cx, cy = rnd.uniform(x_text, x_text + 600), rnd.uniform(y_text, y_text + block)
        r = rnd.uniform(120, 260)
        sd.ellipse((cx - r, cy - r * 0.6, cx + r, cy + r * 0.6), fill=170)
    smoke = smoke.filter(ImageFilter.GaussianBlur(90))
    img = Image.composite(Image.new("RGB", img.size, (8, 8, 8)), img, smoke)
    vig = Image.new("L", (W_, H_), 0)
    ImageDraw.Draw(vig).ellipse((-W_ * 0.2, -H_ * 0.3, W_ * 1.2, H_ * 1.3), fill=255)
    img = Image.composite(img, Image.new("RGB", img.size, (0, 0, 0)), vig.filter(ImageFilter.GaussianBlur(140)))
    noise = Image.effect_noise((W_, H_), 28).convert("L")
    img = Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.07)

    # the words, on their own layer so one letter can be split
    layer = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    hot_box = None
    y = y_text
    for ln in lines:
        x = x_text
        for k, i in enumerate(ln):
            piece = words[i] + (" " if k < len(ln) - 1 else "")
            ld.text((x, y), piece, font=font, fill=ink + (255,))
            if i == hot_i and hot_box is None:
                w = words[i]
                letters = [j for j, ch in enumerate(w) if ch.isalnum()]
                j = letters[len(letters) // 2] if letters else 0
                if letters and len(letters) % 2 == 0 and len(letters) >= 2:
                    j = letters[len(letters) // 2 - (0 if len(letters) > 2 else -0)]
                lx0 = x + ld.textlength(w[:j], font=font)
                lx1 = x + ld.textlength(w[:j + 1], font=font)
                bb = font.getbbox(w[j])
                hot_box = (lx0, y + bb[1], lx1, y + bb[3])
            x += ld.textlength(piece, font=font)
        y += asc + gap

    if hot_box:
        x0, y0, x1, y1 = hot_box
        pts = _crack_points(x0, y0, x1, y1, seed)
        mask = Image.new("L", (W_, H_), 0)
        ImageDraw.Draw(mask).polygon(pts + [(x1 + size * 0.2, y1 + size * 0.2), (x1 + size * 0.2, y0 - size * 0.2)], fill=255)
        box = Image.new("L", (W_, H_), 0)
        ImageDraw.Draw(box).rectangle((x0 - 4, y0 - size * 0.2, x1 + 6, y1 + size * 0.2), fill=255)
        from PIL import ImageChops
        mask = ImageChops.multiply(mask, box)
        piece = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
        piece.paste(layer, (0, 0), mask)
        layer.paste((0, 0, 0, 0), (0, 0), mask)
        dx, dy = max(5, size // 22), max(6, size // 16)
        layer.alpha_composite(piece, (dx, dy))
        cd = ImageDraw.Draw(layer)
        cd.line(pts, fill=red + (255,), width=max(5, size // 26), joint="curve")
        cd.line([(px + 2, py - 1) for px, py in pts], fill=(255, 255, 255, 140), width=max(1, size // 90))

    shadow = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 200), (0, 0), layer.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    img = img.convert("RGBA")
    img.alpha_composite(shadow, (4, 8))
    img.alpha_composite(layer)

    if tag:
        d = ImageDraw.Draw(img)
        tf = _heavy_font(44)
        tw = d.textlength(tag, font=tf)
        ty = y_text + block + 34
        d.rectangle((x_text, ty, x_text + tw + 40, ty + tag_h), fill=red + (255,))
        d.text((x_text + 20, ty + (tag_h - 44) // 2 - 6), tag, font=tf, fill=(255, 255, 255, 255))

    img.convert("RGB").save(out, "JPEG", quality=92)
    return out


def description(cfg: dict, script: dict, brief: dict) -> str:
    parts = [script["description_summary"].strip(), ""]
    ch = chapter_lines(script)
    if ch:
        parts += ["CHAPTERS", *ch, ""]
    srcs = brief.get("sources", [])[:10]
    if srcs:
        parts.append("SOURCES")
        parts += [f"{s.get('title', 'Source')}: {s.get('url', '')}" for s in srcs]
        parts.append("")
    note = cfg.get("description_note") or ("Some details of this history are debated by historians; where "
                                           "accounts differ, the video says so. Spotted an error? Leave a "
                                           "comment with a source.")
    tail = [note.strip(),
            "",
            f"Narration is AI-generated. Research, script checks and editing by {cfg['channel_name']}."]
    credits = script.get("image_credits", [])

    def credit_block(short: bool) -> list[str]:
        if not credits:
            return []
        lines = ["IMAGE CREDITS (Wikimedia Commons)"]
        for c in credits:
            if short:
                lines.append(f"{c['title'][:60]} ({c['licence']})")
            else:
                lines.append(f"{c['title'][:80]} by {c['artist'][:50]}, {c['licence']}: {c['page']}")
        return lines + [""]

    for short in (False, True):
        text = "\n".join(parts + credit_block(short) + tail)
        if len(text) <= DESC_LIMIT:
            return text
    # Still too long: keep as many credits as fit and point to the list.
    base = "\n".join(parts + tail)
    budget = DESC_LIMIT - len(base) - 120
    lines, used = ["IMAGE CREDITS (Wikimedia Commons, shortened)"], 0
    for c in credits:
        s = f"{c['title'][:50]} ({c['licence']})"
        if used + len(s) + 1 > budget:
            break
        lines.append(s)
        used += len(s) + 1
    return "\n".join(parts + lines + ["Full credits in the pinned comment.", ""] + tail)


def credits_comment(script: dict) -> str:
    lines = ["Image credits (Wikimedia Commons):"]
    for c in script.get("image_credits", []):
        lines.append(f"• {c['title'][:70]} by {c['artist'][:40]}, {c['licence']}: {c['page']}")
    return "\n".join(lines)[:9500]
