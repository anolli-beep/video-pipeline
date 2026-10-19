"""ElevenLabs narration, one audio file per scene, with the exact time each word is spoken
(used for burned-in captions and the short clips' captions)."""
from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

import requests

import yaml

from .common import ROOT, log, media_duration

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}"
API_TIMED = "https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps"


def _words(alignment: dict | None) -> list[list]:
    """Turn ElevenLabs' per-character timings into [word, start, end] (seconds)."""
    if not alignment:
        return []
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    out, cur, t0, t1 = [], "", None, None
    for ch, a, b in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                out.append([cur, round(t0, 3), round(t1, 3)])
            cur, t0 = "", None
            continue
        if t0 is None:
            t0 = a
        cur += ch
        t1 = b
    if cur:
        out.append([cur, round(t0, 3), round(t1, 3)])
    return out


def pronunciations(cfg: dict, script: dict) -> dict[str, str]:
    """Word -> how the voice should say it. pronunciations.yaml (all channels), then the channel file's
    `pronunciations`, then the plan's own `pronunciations` (later ones win)."""
    out: dict[str, str] = {}
    shared = ROOT / "pronunciations.yaml"
    if shared.exists():
        out.update(yaml.safe_load(shared.read_text(encoding="utf-8")) or {})
    out.update(cfg.get("pronunciations") or {})
    out.update(script.get("pronunciations") or {})
    # one spoken "word" per written word, so captions can be matched back to the real spelling
    return {str(k): re.sub(r"\s+", "-", str(v).strip()) for k, v in out.items() if k and v}


def respell(text: str, table: dict[str, str]) -> str:
    """Swap whole words only, case-sensitive, keeping punctuation: 'ISA,' -> 'eye-sa,'."""
    for word in sorted(table, key=len, reverse=True):          # longer first: ISAs before ISA
        text = re.sub(rf"(?<![\w-]){re.escape(word)}(?![\w-])", table[word], text)
    return text


def narrate(cfg: dict, script: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    key = os.environ["ELEVENLABS_API_KEY"]
    scenes = script["scenes"]
    table = pronunciations(cfg, script)
    if table:
        log(f"Pronunciations: {len(table)} words respelt for the voice")
    spoken = [respell(s["narration"], table) for s in scenes]
    for i, scene in enumerate(scenes):
        path = out_dir / f"scene_{i:03d}.mp3"
        timing = out_dir / f"scene_{i:03d}.words.json"
        if not path.exists():
            body = {
                "text": spoken[i],
                "model_id": cfg["elevenlabs_model"],
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.15},
                # Continuity hints keep intonation natural across scene boundaries.
                "previous_text": spoken[i - 1] if i else None,
                "next_text": spoken[i + 1] if i + 1 < len(scenes) else None,
            }
            timed = True
            for attempt in range(5):
                r = requests.post((API_TIMED if timed else API).format(voice=cfg["elevenlabs_voice_id"]),
                                  params={"output_format": "mp3_44100_128"},
                                  headers={"xi-api-key": key, "Content-Type": "application/json"},
                                  json=body, timeout=180)
                if r.status_code == 200 and timed:
                    try:
                        data = r.json()
                        path.write_bytes(base64.b64decode(data["audio_base64"]))
                        words = _words(data.get("alignment") or data.get("normalized_alignment"))
                        timing.write_text(json.dumps(words), encoding="utf-8")
                        break
                    except (ValueError, KeyError) as e:   # unexpected reply: fall back to plain audio
                        log(f"Word timings unavailable ({e}); using estimated caption timing")
                        timed = False
                        continue
                if r.status_code == 200:
                    path.write_bytes(r.content)
                    break
                if timed and r.status_code in (404, 405, 422):     # timings not offered: plain audio
                    log(f"Word timings unavailable (HTTP {r.status_code}); using estimated caption timing")
                    timed = False
                    continue
                log(f"ElevenLabs error {r.status_code}: {r.text[:200]}")
                if r.status_code in (401, 402, 403):
                    raise RuntimeError("ElevenLabs rejected the request: check API key and credits")
                time.sleep(15 * (attempt + 1))
            else:
                raise RuntimeError("ElevenLabs failed repeatedly")
        scene["audio"] = str(path)
        if timing.exists():
            words = json.loads(timing.read_text(encoding="utf-8"))
            written = scene["narration"].split()
            if len(words) == len(written):      # show the real spelling in captions, not the respelling
                words = [[w, a, b] for w, (_, a, b) in zip(written, words)]
            scene["words"] = words
        # 0.45s breathing gap after each scene
        scene["duration"] = round(media_duration(path) + 0.45, 3)
    total = sum(s["duration"] for s in scenes)
    log(f"Narration: {total/60:.1f} minutes")
    script["narration_seconds"] = total
