"""Vertical short clips (1080x1920, under a minute) cut from the finished video, for YouTube Shorts,
Instagram Reels, TikTok, Facebook Reels and Snapchat Spotlight.

Each clip is a run of whole scenes, so it starts and ends on a complete thought. Layout:
blurred background, the main video in the middle, a hook title above, big captions below
(most people watch shorts muted), and the channel name at the bottom.

A plan can choose its clips (best: written to make sense on their own):
    "clips": [{"scenes": [4, 6], "hook": "The river that started a civil war",
               "caption": "One small river, one huge decision.", "hashtags": ["romanhistory"]}]
Scene numbers count from 1 and are inclusive. Without "clips", up to `clips_per_video` are picked
automatically from the chapter openings.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .common import font_path, log, run

W, H = 1080, 1920
VIDEO_Y = 700                     # top of the 16:9 picture (1080x608)
CAPTION_Y = 1390                  # captions sit just below the picture


def _windows(script: dict, max_s: float, min_s: float) -> list[tuple[int, int]]:
    """Runs of whole scenes starting at each chapter, as long as possible under max_s."""
    scenes = script["scenes"]
    starts = [i for i, s in enumerate(scenes) if s.get("chapter")] or list(range(0, len(scenes), 4))
    out = []
    for a in starts:
        total, b = 0.0, a
        while b < len(scenes) and total + scenes[b]["duration"] <= max_s:
            total += scenes[b]["duration"]
            b += 1
        if b > a and total >= min_s:
            out.append((a, b - 1))
    return out


def _pick(script: dict, cfg: dict) -> list[dict]:
    max_s = float(cfg.get("clip_max_seconds", 59))
    want = script.get("clips")
    picked = []
    if want:
        for c in want:
            a, b = (int(x) - 1 for x in c["scenes"])
            a, b = max(a, 0), min(b, len(script["scenes"]) - 1)
            # too long once narrated? drop scenes from the end until it fits
            while b > a and sum(s["duration"] for s in script["scenes"][a:b + 1]) > max_s:
                b -= 1
            picked.append(dict(c, a=a, b=b))
        return picked
    wins = _windows(script, max_s, float(cfg.get("clip_min_seconds", 25)))
    n = int(cfg.get("clips_per_video", 3))
    if len(wins) > n:  # spread them through the video
        wins = [wins[round(i * (len(wins) - 1) / (n - 1))] for i in range(n)] if n > 1 else wins[:1]
    for a, b in wins:
        hook = script["scenes"][a].get("chapter") or script["title"]
        if hook.lower() in ("introduction", "intro"):
            hook = script["title"]
        picked.append({"a": a, "b": b, "hook": hook})
    return picked


def _chunks(scene: dict, offset: float, words_per: int = 4) -> list[tuple[float, float, str]]:
    """Short caption chunks: exact ElevenLabs word timings when available, otherwise estimated."""
    if scene.get("words"):
        w = scene["words"]
        out = []
        for i in range(0, len(w), words_per):
            part = w[i:i + words_per]
            end = w[i + words_per][1] if i + words_per < len(w) else part[-1][2] + 0.3
            out.append((offset + part[0][1], offset + end, " ".join(x[0] for x in part)))
        return out
    speech = scene["duration"] - 0.45
    words = scene["narration"].split()
    parts = [" ".join(words[i:i + words_per]) for i in range(0, len(words), words_per)]
    total = sum(len(p) for p in parts) or 1
    out, t = [], offset
    for p in parts:
        d = speech * len(p) / total
        out.append((t, t + d, p))
        t += d
    return out


def _overlay(path: Path, hook: str, cfg: dict) -> None:
    """Static layer: hook title box at the top, channel line and note at the bottom."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    accent = tuple(int(cfg.get("colour", "#c0392b").lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    size = 76
    while True:
        font = ImageFont.truetype(font_path(True), size)
        lines = textwrap.wrap(hook.upper(), width=max(8, int(940 / (size * 0.58))))
        if len(lines) <= 3 or size <= 52:
            break
        size -= 6
    lh = int(size * 1.18)
    box_h = lh * len(lines) + 70
    top = VIDEO_Y - 60 - box_h
    d.rounded_rectangle((50, top, W - 50, top + box_h), radius=26, fill=accent + (240,))
    y = top + 35
    for line in lines:
        w = d.textlength(line, font=font)
        d.text(((W - w) / 2, y), line, font=font, fill=(255, 255, 255))
        y += lh
    small = ImageFont.truetype(font_path(True), 38)
    name = cfg["channel_name"]
    w = d.textlength(name, font=small)
    d.text(((W - w) / 2, H - 400), name, font=small, fill=(255, 255, 255, 235))
    note = cfg.get("clip_note", "Full video on the channel")
    tiny = ImageFont.truetype(font_path(False), 30)
    w = d.textlength(note, font=tiny)
    d.text(((W - w) / 2, H - 345), note, font=tiny, fill=(255, 255, 255, 200))
    img.save(path)


def _esc(p: Path) -> str:
    return str(p).replace("\\", "/").replace(":", r"\:")


def make_clip(cfg: dict, script: dict, video: Path, clip: dict, out: Path, tmp: Path) -> float:
    scenes = script["scenes"][clip["a"]:clip["b"] + 1]
    start = scenes[0]["start"]
    dur = sum(s["duration"] for s in scenes)
    tmp.mkdir(parents=True, exist_ok=True)
    layer = tmp / f"{out.stem}_layer.png"
    _overlay(layer, clip.get("hook") or script["title"], cfg)

    caps = []
    for s in scenes:
        caps += _chunks(s, s["start"] - start)
    bold = _esc(Path(font_path(True)))
    draws = []
    for i, (t0, t1, text) in enumerate(caps):
        tf = tmp / f"{out.stem}_c{i:03d}.txt"
        tf.write_text(text, encoding="utf-8")
        draws.append(f"drawtext=fontfile='{bold}':textfile='{_esc(tf)}':fontsize=74:fontcolor=white:"
                     f"borderw=7:bordercolor=black@0.85:x=(w-tw)/2:y={CAPTION_Y}:"
                     f"enable='gte(t,{t0:.2f})*lt(t,{t1:.2f})'")
    fade = max(dur - 0.6, 0)
    graph = (
        "[0:v]split[a][b];"
        "[a]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=12:2,"
        f"scale={W}:{H},colorchannelmixer=rr=0.5:gg=0.5:bb=0.5[bg];"
        f"[b]scale={W}:-2[fg];"
        f"[bg][fg]overlay=0:{VIDEO_Y}[v1];"
        "[v1][1:v]overlay=0:0[v2];"
        f"[v2]{','.join(draws) if draws else 'null'},fade=t=out:st={fade:.2f}:d=0.6[v];"
        f"[0:a]afade=t=in:d=0.15,afade=t=out:st={fade:.2f}:d=0.6[aud]"
    )
    script_file = tmp / f"{out.stem}_graph.txt"
    script_file.write_text(graph, encoding="utf-8")
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(video),
         "-i", str(layer), "-filter_complex_script", str(script_file), "-map", "[v]", "-map", "[aud]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "25",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)])
    return dur


def _hashtags(script: dict, clip: dict) -> str:
    tags = clip.get("hashtags") or script.get("tags", [])[:4]
    clean = ["#" + re.sub(r"[^A-Za-z0-9]", "", t) for t in tags]
    return " ".join(t for t in clean if len(t) > 1)


def clips_sheet(cfg: dict, script: dict, made: list[dict]) -> str:
    parts = [f"SHORT CLIPS: {script['title']}",
             f"CHANNEL: {cfg['channel_name']} ({cfg['label']})", "=" * 64, ""]
    for i, c in enumerate(made, 1):
        caption = c.get("caption") or script.get("description_summary", "").split(". ")[0].rstrip(".") + "."
        parts += [f"CLIP {i}: {c['file']}  ({c['seconds']:.0f} seconds, scenes {c['a'] + 1}-{c['b'] + 1})",
                  f"Hook on screen: {c.get('hook') or script['title']}",
                  "",
                  "Title (YouTube Shorts, Facebook):",
                  (c.get("hook") or script["title"])[:95],
                  "",
                  "Caption (TikTok, Instagram, Facebook, Snapchat):",
                  f"{caption} {cfg.get('clip_caption_extra', '')} Full video on our YouTube channel: "
                  f"{cfg['channel_name']}.".replace("  ", " "),
                  _hashtags(script, c),
                  "", "-" * 64, ""]
    parts += [
        "POSTING CHECKLIST (the same clip works on every app)",
        "- YouTube Shorts: upload on the same channel as the main video. In the upload screen, set",
        "  'Related video' to the full video so viewers can tap through to it.",
        "- TikTok: turn on 'AI-generated content' (under More options) because the voice is AI.",
        "- Instagram Reels and Facebook Reels: turn on the 'AI info' label if offered.",
        "- Snapchat Spotlight: clips must be 60 seconds or less (these are).",
        "- Space them out: one clip a day per app does better than all at once.",
    ]
    return "\n".join(p for p in parts if p is not None)


def make_all(cfg: dict, script: dict, video: Path, out_dir: Path, tmp: Path) -> list[dict]:
    if not cfg.get("make_clips", True):
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for i, clip in enumerate(_pick(script, cfg), 1):
        path = out_dir / f"clip{i}.mp4"
        try:
            secs = make_clip(cfg, script, video, clip, path, tmp)
        except Exception as e:       # a failed clip never stops the main video
            log(f"Clip {i} failed: {e}")
            continue
        made.append(dict(clip, file=path.name, seconds=secs))
        log(f"Clip {i}: scenes {clip['a'] + 1}-{clip['b'] + 1}, {secs:.0f}s")
    return made
