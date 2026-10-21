"""Simple 2D stick-figure animations in the channels' flat style.

A plan shot like {"stick": {"scene": "think", "label": "Caesar hesitates"}} becomes a short animated
clip. Each scene is a small, reusable template; the figure wears the channel's colour (a cape for
history, a tie for finance, a scarf for politics).

Scenes: walk, march, think, worried, celebrate, point, shrug, cross_river, deposit, coins_jar,
bill, crowd_shocked, dig, read, talk, ship, lifeboat, radio, lookout, glider, fleet, landing, paradrop, control_room, power_plant, evacuation, helicopter.
"""
from __future__ import annotations

import math
import random

import cairo

W, H = 1920, 1080
PAPER = (0.96, 0.93, 0.85)
INK = (0.17, 0.16, 0.15)
MUTED = (0.42, 0.40, 0.36)
GROUND = (0.87, 0.83, 0.73)
WATER = (0.45, 0.62, 0.72)
GOLD = (0.85, 0.66, 0.22)

# body proportions (px at scale 1)
BASE = 1.3             # overall figure size
TORSO, NECK, HEAD_R = 150 * BASE, 18 * BASE, 44 * BASE
UPPER, FORE, THIGH, SHIN = 82 * BASE, 78 * BASE, 96 * BASE, 96 * BASE
LINE = 15


def _v(angle_deg, length, facing=1):
    """Vector for a limb: angle measured from straight down, positive = towards facing."""
    a = math.radians(angle_deg)
    return math.sin(a) * length * facing, math.cos(a) * length


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _mix(a, b, k):
    return a + (b - a) * k


def pose_mix(p, q, k):
    return {key: _mix(p.get(key, 0), q.get(key, 0), k) for key in set(p) | set(q)}


POSES = {
    "stand":     dict(lean=0, head=0, ls=8, le=10, rs=-8, re=10, lh=4, lk=0, rh=-4, rk=0),
    "think":     dict(lean=2, head=8, ls=10, le=8, rs=35, re=150, lh=4, lk=0, rh=-4, rk=0),
    "worried":   dict(lean=0, head=-4, ls=135, le=75, rs=-135, re=-75, lh=6, lk=0, rh=-6, rk=0),
    "cheer":     dict(lean=0, head=-6, ls=145, le=15, rs=-145, re=-15, lh=10, lk=0, rh=-10, rk=0),
    "point":     dict(lean=4, head=-4, ls=8, le=10, rs=100, re=0, lh=4, lk=0, rh=-6, rk=0),
    "shrug":     dict(lean=0, head=10, ls=55, le=-95, rs=-55, re=95, lh=4, lk=0, rh=-4, rk=0),
    "carry":     dict(lean=4, head=0, ls=40, le=70, rs=40, re=70, lh=4, lk=0, rh=-4, rk=0),
    "hold":      dict(lean=2, head=6, ls=55, le=40, rs=55, re=40, lh=4, lk=0, rh=-4, rk=0),
    "dig":       dict(lean=25, head=10, ls=60, le=10, rs=40, re=20, lh=20, lk=25, rh=-10, rk=5),
    "sleep":     dict(lean=0, head=20, ls=5, le=5, rs=-5, re=5, lh=2, lk=0, rh=-2, rk=0),
}


def walk_pose(phase, stride=26, carry=False):
    s = math.sin(phase)
    p = dict(lean=4, head=0, lh=stride * s, lk=max(0, -math.sin(phase)) * 40 + 4,
             rh=-stride * s, rk=max(0, math.sin(phase)) * 40 + 4)
    if carry:
        p.update(ls=40, le=70, rs=40, re=70)
    else:
        p.update(ls=-22 * s, le=18, rs=22 * s, re=18)
    return p


def _rgb(c, default=(0.75, 0.2, 0.15)):
    if c is None:
        return default
    if isinstance(c, str):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(c)


# Ready-made characters. A plan can use one by name ("who": "roman_general") or describe its own
# ("who": {"hat": "crown", "outfit": "robe", "colour": "#5b3f8c", "facial": "beard", "name": "Henry VIII"}).
PRESETS = {
    "roman_general": dict(hat="laurel", hair="short", outfit="cape", colour="#a3241b"),
    "roman_soldier": dict(hat="helmet", hair="none", outfit="none", colour="#a3241b", shield=True),
    "senator":       dict(hat="none", hair="short", outfit="toga", colour="#f2ede0", facial="beard"),
    "emperor":       dict(hat="crown", hair="short", outfit="robe", colour="#5b3f8c", facial="beard"),
    "king":          dict(hat="crown", hair="long_curly", outfit="cape", colour="#24457a"),
    "queen":         dict(hat="crown", hair="long", outfit="robe", colour="#8c2f5b"),
    "sultan":        dict(hat="turban", hair="none", outfit="robe", colour="#2f6b4f", facial="beard"),
    "knight":        dict(hat="helmet_closed", hair="none", outfit="tabard", colour="#7a1f1f", shield=True),
    "monk":          dict(hat="none", hair="tonsure", outfit="robe", colour="#6b5032"),
    "baker":         dict(hat="baker", hair="short", outfit="apron", colour="#f5f2ea", build="stout"),
    "diarist":       dict(hat="none", hair="long_curly", outfit="scarf", colour="#3d5a80", facial="moustache"),
    "merchant":      dict(hat="cap", hair="short", outfit="scarf", colour="#7a5a2a", build="stout"),
    "sailor":        dict(hat="tricorn", hair="short", outfit="scarf", colour="#24457a"),
    "worker":        dict(hat="cap", hair="short", outfit="none", colour="#555555"),
    "saver":         dict(hat="none", hair="short", outfit="tie", colour="#1f7a4d"),
    "student":       dict(hat="none", hair="bun", outfit="scarf", colour="#c98a1b", glasses=True, height=0.92),
    "parent":        dict(hat="none", hair="long", outfit="scarf", colour="#8c2f5b"),
    "retiree":       dict(hat="none", hair="bald", outfit="tie", colour="#24457a", glasses=True, facial="moustache"),
    "banker":        dict(hat="tophat", hair="short", outfit="tie", colour="#1a1a1a", build="stout"),
    "official":      dict(hat="none", hair="short", outfit="tie", colour="#2a6f86", glasses=True),
    # early 20th century: ships, the world wars, the interwar years
    "captain":       dict(hat="peaked", hair="short", hair_colour="#a9a69e", facial="beard", outfit="jacket", colour="#1d2b4a", build="stout"),
    "officer":       dict(hat="peaked", hair="short", outfit="jacket", colour="#1d2b4a"),
    "lookout":       dict(hat="cap", hair="short", outfit="scarf", colour="#24457a"),
    "wireless_op":   dict(hat="headphones", hair="short", outfit="jacket", colour="#1d2b4a", height=0.95),
    "gentleman":     dict(hat="tophat", hair="short", outfit="tie", colour="#1a1a1a", facial="moustache"),
    "lady":          dict(hat="widehat", hair="long", outfit="dress", colour="#7a3b5c"),
    "steward":       dict(hat="none", hair="short", outfit="jacket", colour="#e9e4d8"),
    "child":         dict(hat="cap", hair="short", outfit="scarf", colour="#b5651d", height=0.62),
    "soldier":       dict(hat="tin_helmet", hair="none", outfit="jacket", colour="#5b6b3a"),
    "pilot":         dict(hat="flying_cap", hair="none", outfit="scarf", colour="#5a6e8c"),
    "scientist":     dict(hat="none", hair="curly", outfit="coat", colour="#f2f2ee", glasses=True),
    # Second World War
    "us_soldier":    dict(hat="m1_helmet", hair="none", outfit="jacket", colour="#5f6b3c"),
    "british_soldier": dict(hat="tin_helmet", hair="none", outfit="jacket", colour="#7a6a45"),
    "paratrooper":   dict(hat="m1_helmet", hair="none", outfit="scarf", colour="#5f6b3c"),
    "general":       dict(hat="peaked", cap_colour="#6b6a4a", hair="short", outfit="jacket", colour="#5f6b3c"),
    "german_officer": dict(hat="peaked", cap_colour="#7d8078", hair="short", outfit="jacket", colour="#6f726b"),
    "operator":      dict(hat="none", hair="short", outfit="coat", colour="#eeeeea"),
    "firefighter":   dict(hat="fire_helmet", hair="none", outfit="jacket", colour="#3b3f4a"),
    "weatherman":    dict(hat="peaked", cap_colour="#5a6e8c", hair="short", outfit="jacket", colour="#5a6e8c", facial="moustache"),
}
NARRATOR = {
    "cape": dict(hat="none", hair="short", outfit="scarf", glasses=True),     # history guide
    "tie": dict(hat="none", hair="short", outfit="tie"),                     # finance guide
    "scarf": dict(hat="none", hair="bun", outfit="scarf"),                   # politics guide
}


def resolve(who, accent, outfit="scarf"):
    """Turn a preset name, a look dict or nothing into a full look."""
    if who:
        look = dict(hat="none", hair="short", outfit="none", colour=accent)   # clean start for a character
    else:
        look = dict(NARRATOR.get(outfit, NARRATOR["scarf"]), colour=accent)   # the channel's guide
    if isinstance(who, str):
        look.update(PRESETS.get(who, {}))
    elif isinstance(who, dict):
        base = PRESETS.get(who.get("preset", ""), {})
        look.update(base)
        look.update({k: v for k, v in who.items() if k != "preset"})
    look["colour"] = _rgb(look.get("colour"), accent)
    return look


def variant(look, seed):
    """A slightly different version of a look, so a group of soldiers or a crowd isn't identical."""
    rnd = random.Random(seed)
    v = dict(look)
    v["height"] = look.get("height", 1.0) * rnd.uniform(0.9, 1.07)
    v["build"] = rnd.choice(["slim", "normal", "normal", "stout"])
    if look.get("hat") in (None, "none", "cap", "tophat"):
        v["hair"] = rnd.choice(["short", "bald", "long", "curly", "bun", "short"])
        v["hat"] = rnd.choice(["none", "none", "none", "cap"])
    v["facial"] = rnd.choice(["none", "none", look.get("facial", "none"), "beard", "moustache"])
    v["glasses"] = rnd.random() < 0.15
    v["name"] = None
    return v


CROWD_POOL = ["senator", "merchant", "worker", "monk", "parent", "baker", "retiree", "student"]
MODERN_POOL = ["saver", "parent", "retiree", "student", "official", "worker", "banker"]
EDWARDIAN_POOL = ["gentleman", "lady", "worker", "child", "steward", "lady", "merchant"]


def figure(cr, x, ground, pose, *, scale=1.0, facing=1, accent=None, outfit="scarf",
           face="calm", t=0.0, jump=0.0, colour=INK, look=None):
    """Draw one stick figure standing on `ground` at x. Returns key points (hands, head) for props."""
    if look is None:
        look = resolve(None, accent or (0.75, 0.2, 0.15), outfit) if accent else dict(hat="none", hair="short", outfit="none", colour=(0.5, 0.5, 0.5))
    k = scale * look.get("height", 1.0)
    face_k = k * BASE
    width = {"slim": LINE * 0.8, "stout": LINE * 1.45}.get(look.get("build"), LINE)
    lc = look.get("colour", (0.75, 0.2, 0.15))
    hip = (0.0, 0.0)

    def leg(h_ang, knee):
        kx, ky = _v(h_ang, THIGH * k, facing)
        fx, fy = _v(h_ang - knee, SHIN * k, facing)
        return (kx, ky), (kx + fx, ky + fy)
    lknee, lfoot = leg(pose.get("lh", 0), pose.get("lk", 0))
    rknee, rfoot = leg(pose.get("rh", 0), pose.get("rk", 0))
    drop = max(lfoot[1], rfoot[1])
    ox, oy = x, ground - drop - jump
    P = lambda pt: (ox + pt[0], oy + pt[1])

    lean = math.radians(pose.get("lean", 0))
    neck = (math.sin(lean) * TORSO * k * facing, -math.cos(lean) * TORSO * k)
    shoulder = (neck[0] * 0.9, neck[1] * 0.9)

    def arm(s_ang, bend):
        ex, ey = _v(s_ang, UPPER * k, facing)
        hx, hy = _v(s_ang + bend, FORE * k, facing)
        e = (shoulder[0] + ex, shoulder[1] + ey)
        return e, (e[0] + hx, e[1] + hy)
    lelb, lhand = arm(pose.get("ls", 0), pose.get("le", 0))
    relb, rhand = arm(pose.get("rs", 0), pose.get("re", 0))

    head_ang = lean + math.radians(pose.get("head", 0)) * 0.6
    hc = (neck[0] + math.sin(head_ang) * (NECK + HEAD_R) * k * facing,
          neck[1] - math.cos(head_ang) * (NECK + HEAD_R) * k)
    hx, hy = P(hc)
    R = HEAD_R * k

    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.save(); cr.translate(x, ground + 4); cr.scale(1, 0.18)
    cr.arc(0, 0, 70 * k * BASE * max(0.5, 1 - jump / 200), 0, 2 * math.pi); cr.restore()
    cr.set_source_rgba(0, 0, 0, 0.12); cr.fill()

    out = look.get("outfit", "none")
    fk = face_k
    if out == "cape":
        sway = math.sin(t * 2.2) * 10 * fk
        cr.move_to(*P((shoulder[0] - 6 * facing * fk, shoulder[1])))
        cr.line_to(*P((shoulder[0] + 10 * facing * fk, shoulder[1])))
        cr.line_to(*P((-28 * facing * fk + sway * -facing, 18 * fk)))
        cr.line_to(*P((-62 * facing * fk + sway * -facing, 4 * fk)))
        cr.close_path(); cr.set_source_rgb(*lc); cr.fill()
    # long hair hangs behind the head
    hair = look.get("hair", "short")
    hair_col = _rgb(look.get("hair_colour"), (0.35, 0.25, 0.18))
    if hair in ("long", "long_curly"):
        cr.set_source_rgb(*(hair_col if hair == "long" else (0.85, 0.82, 0.75)))
        cr.move_to(hx - R * 0.95 * facing, hy - R * 0.2)
        cr.line_to(hx - R * 1.05 * facing, hy + R * 1.5)
        cr.line_to(hx + R * 0.1 * facing, hy + R * 1.35)
        cr.line_to(hx + R * 0.2 * facing, hy)
        cr.close_path(); cr.fill()
        if hair == "long_curly":
            cr.set_source_rgb(0.85, 0.82, 0.75)
            for i in range(5):
                cr.arc(hx - R * 0.9 * facing, hy + R * (0.1 + i * 0.3), R * 0.28, 0, 2 * math.pi); cr.fill()

    def seg(a, b, c=None, col=colour):
        cr.set_source_rgb(*col)
        cr.set_line_width(width * k)
        cr.move_to(*P(a)); cr.line_to(*P(b))
        if c is not None:
            cr.line_to(*P(c))
        cr.stroke()

    back = tuple(min(1, ch + 0.25) for ch in colour)
    seg(hip, rknee, rfoot, back)
    seg(shoulder, relb, rhand, back)
    if out in ("robe", "toga", "tabard", "dress", "coat", "jacket"):
        # a garment from the shoulders down: long (robe, dress, coat) or short (tabard, jacket)
        hem = {"tabard": 0.45, "jacket": 0.38, "coat": 0.62, "dress": 0.82}.get(out, 0.75)
        cr.move_to(*P((shoulder[0] - 22 * fk, shoulder[1])))
        cr.line_to(*P((shoulder[0] + 22 * fk, shoulder[1])))
        cr.line_to(*P((48 * fk, (THIGH + SHIN) * k * hem)))
        cr.line_to(*P((-48 * fk, (THIGH + SHIN) * k * hem)))
        cr.close_path()
        cr.set_source_rgb(*lc); cr.fill_preserve()
        cr.set_source_rgb(*colour); cr.set_line_width(4 * fk); cr.stroke()
        if out == "toga":    # coloured sash across the body
            cr.set_source_rgb(0.6, 0.2, 0.25); cr.set_line_width(9 * fk)
            cr.move_to(*P((shoulder[0] - 18 * fk * facing, shoulder[1] + 4 * fk)))
            cr.line_to(*P((30 * fk * facing, (THIGH + SHIN) * k * 0.4))); cr.stroke()
        if out in ("jacket", "coat"):    # a row of buttons
            cr.set_source_rgb(*GOLD if out == "jacket" else colour)
            for i in range(3):
                yy = shoulder[1] * (0.75 - i * 0.28)
                cr.arc(*P((shoulder[0] * (0.75 - i * 0.28) + 6 * fk * facing, yy)), 5 * fk, 0, 2 * math.pi); cr.fill()
    else:
        seg(hip, neck)
    if out == "tie":
        top = (neck[0] * 0.92, neck[1] * 0.92)
        cr.move_to(*P(top))
        cr.line_to(*P((top[0] - 9 * fk, top[1] + 22 * fk)))
        cr.line_to(*P((top[0], top[1] + 62 * fk)))
        cr.line_to(*P((top[0] + 9 * fk, top[1] + 22 * fk)))
        cr.close_path(); cr.set_source_rgb(*lc); cr.fill()
    if out == "apron":
        cr.rectangle(*P((-26 * fk, neck[1] * 0.55)), 52 * fk, -neck[1] * 0.75)
        cr.set_source_rgb(0.98, 0.98, 0.96); cr.fill_preserve()
        cr.set_source_rgb(*colour); cr.set_line_width(4 * fk); cr.stroke()
    seg(hip, lknee, lfoot)
    seg(shoulder, lelb, lhand)
    if out == "scarf":
        cr.set_source_rgb(*lc); cr.set_line_width(16 * fk)
        cr.move_to(*P((neck[0] - 18 * fk, neck[1] + 6 * fk)))
        cr.line_to(*P((neck[0] + 18 * fk, neck[1] + 6 * fk))); cr.stroke()

    # head
    cr.arc(hx, hy, R, 0, 2 * math.pi)
    cr.set_source_rgb(*PAPER); cr.fill_preserve()
    cr.set_source_rgb(*colour); cr.set_line_width(LINE * fk * 0.85); cr.stroke()
    if hair in ("short", "curly", "bun", "tonsure", "long"):
        cr.set_source_rgb(*hair_col)
        if hair == "curly":
            for i in range(6):
                a = math.radians(200 + i * 28)
                cr.arc(hx + math.cos(a) * R, hy + math.sin(a) * R, R * 0.26, 0, 2 * math.pi); cr.fill()
        elif hair == "tonsure":
            cr.set_line_width(10 * fk); cr.arc(hx, hy, R * 0.95, math.radians(160), math.radians(220)); cr.stroke()
            cr.arc(hx, hy, R * 0.95, math.radians(320), math.radians(380)); cr.stroke()
        else:
            cr.set_line_width(13 * fk)
            cr.arc(hx, hy, R * 0.92, math.radians(190 if facing > 0 else 210), math.radians(330 if facing > 0 else 350)); cr.stroke()
        if hair == "bun":
            cr.arc(hx - R * 0.95 * facing, hy - R * 0.75, R * 0.36, 0, 2 * math.pi); cr.fill()
    # face
    ex = hx + 12 * fk * facing
    cr.set_source_rgb(*colour)
    for dx in (-11, 11):
        cr.arc(ex + dx * fk, hy - 6 * fk, 4.2 * fk, 0, 2 * math.pi); cr.fill()
    if look.get("glasses"):
        cr.set_line_width(3.5 * fk)
        for dx in (-11, 11):
            cr.new_sub_path(); cr.arc(ex + dx * fk, hy - 6 * fk, 9 * fk, 0, 2 * math.pi)
        cr.move_to(ex - 2 * fk, hy - 6 * fk); cr.line_to(ex + 2 * fk, hy - 6 * fk); cr.stroke()
    facial = look.get("facial", "none")
    if facial == "beard":
        cr.set_source_rgb(*hair_col)
        cr.arc(hx + 6 * fk * facing, hy + 8 * fk, R * 0.78, math.radians(20), math.radians(160)); cr.close_path(); cr.fill()
    cr.set_source_rgb(*colour)
    cr.set_line_width(4 * fk)
    my = hy + 16 * fk
    if facial == "moustache":
        cr.set_source_rgb(*hair_col); cr.set_line_width(7 * fk)
        cr.move_to(ex - 11 * fk, my - 5 * fk); cr.line_to(ex + 11 * fk, my - 5 * fk); cr.stroke()
        cr.set_source_rgb(*colour); cr.set_line_width(4 * fk)
    mood_col = (1, 1, 1) if facial == "beard" else colour
    cr.set_source_rgb(*mood_col)
    if face == "happy":
        cr.arc(ex, my - 8 * fk, 13 * fk, math.radians(20), math.radians(160))
    elif face == "worried":
        cr.arc(ex, my + 10 * fk, 11 * fk, math.radians(200), math.radians(340))
    elif face == "surprised":
        cr.new_sub_path(); cr.arc(ex, my, 6 * fk, 0, 2 * math.pi)
    else:
        cr.move_to(ex - 8 * fk, my); cr.line_to(ex + 8 * fk, my)
    cr.stroke()

    # hats
    hat = look.get("hat", "none")
    top = hy - R
    if hat == "laurel":
        cr.set_source_rgb(0.42, 0.55, 0.22); cr.set_line_width(7 * fk)
        cr.arc(hx, hy, R + 3, math.radians(195), math.radians(345)); cr.stroke()
        for i in range(7):
            a = math.radians(200 + i * 22)
            cr.save(); cr.translate(hx + math.cos(a) * (R + 4), hy + math.sin(a) * (R + 4)); cr.rotate(a + 0.9)
            cr.scale(1, 0.45); cr.arc(0, 0, 9 * fk, 0, 2 * math.pi); cr.restore(); cr.fill()
    elif hat == "crown":
        w = R * 1.25
        cr.move_to(hx - w / 2, top + 6 * fk)
        for i in range(5):
            cr.line_to(hx - w / 2 + w * (i + 0.5) / 5, top - (26 if i % 2 == 0 else 10) * fk)
        cr.line_to(hx + w / 2, top + 6 * fk); cr.close_path()
        cr.set_source_rgb(*GOLD); cr.fill_preserve(); cr.set_source_rgb(*colour); cr.set_line_width(3 * fk); cr.stroke()
    elif hat in ("helmet", "helmet_closed"):
        cr.arc(hx, hy - 4 * fk, R * 1.08, math.radians(180), math.radians(360)); cr.close_path()
        cr.set_source_rgb(0.62, 0.62, 0.66); cr.fill_preserve(); cr.set_source_rgb(*colour); cr.set_line_width(4 * fk); cr.stroke()
        if hat == "helmet":    # Roman crest in the character's colour
            cr.save(); cr.translate(hx, top - 14 * fk); cr.scale(1.4, 0.55)
            cr.arc(0, 0, R * 0.55, math.radians(180), math.radians(360)); cr.restore()
            cr.set_source_rgb(*lc); cr.fill()
        else:
            cr.rectangle(hx - R * 0.9, hy - 12 * fk, R * 1.8, 7 * fk); cr.set_source_rgb(*colour); cr.fill()
    elif hat == "turban":
        cr.save(); cr.translate(hx, top + 2 * fk); cr.scale(1.2, 0.75); cr.arc(0, 0, R * 0.85, 0, 2 * math.pi); cr.restore()
        cr.set_source_rgb(0.97, 0.96, 0.92); cr.fill_preserve(); cr.set_source_rgb(*colour); cr.set_line_width(3 * fk); cr.stroke()
        cr.arc(hx, top + 8 * fk, 6 * fk, 0, 2 * math.pi); cr.set_source_rgb(*lc); cr.fill()
    elif hat == "cap":
        cr.arc(hx, hy - 6 * fk, R * 0.98, math.radians(185), math.radians(355)); cr.close_path()
        cr.set_source_rgb(0.4, 0.37, 0.33); cr.fill()
        cr.rectangle(hx + (R * 0.2 if facing > 0 else -R * 1.2), hy - 10 * fk, R, 7 * fk); cr.fill()
    elif hat == "tophat":
        cr.rectangle(hx - R * 0.6, top - 52 * fk, R * 1.2, 56 * fk); cr.set_source_rgb(0.12, 0.12, 0.12); cr.fill()
        cr.rectangle(hx - R * 0.95, top + 2 * fk, R * 1.9, 7 * fk); cr.fill()
    elif hat == "tricorn":
        cr.move_to(hx - R * 1.15, top + 10 * fk); cr.line_to(hx, top - 26 * fk); cr.line_to(hx + R * 1.15, top + 10 * fk)
        cr.close_path(); cr.set_source_rgb(0.15, 0.15, 0.18); cr.fill()
    elif hat == "peaked":    # officer's cap: white top, dark band, peak and a gold badge
        cr.rectangle(hx - R * 1.0, top - 16 * fk, R * 2.0, 14 * fk); cr.set_source_rgb(*_rgb(look.get("cap_colour"), (0.97, 0.97, 0.95))); cr.fill_preserve()
        cr.set_source_rgb(*colour); cr.set_line_width(3 * fk); cr.stroke()
        cr.rectangle(hx - R * 0.92, top - 3 * fk, R * 1.84, 14 * fk); cr.set_source_rgb(0.1, 0.12, 0.2); cr.fill()
        cr.move_to(hx + R * 0.2 * facing, top + 11 * fk); cr.line_to(hx + R * 1.25 * facing, top + 15 * fk)
        cr.set_line_width(7 * fk); cr.stroke()
        cr.arc(hx + R * 0.15 * facing, top + 2 * fk, 6 * fk, 0, 2 * math.pi); cr.set_source_rgb(*GOLD); cr.fill()
    elif hat == "widehat":   # Edwardian lady's wide hat with a ribbon
        cr.save(); cr.translate(hx, top + 6 * fk); cr.scale(1, 0.22); cr.arc(0, 0, R * 1.7, 0, 2 * math.pi); cr.restore()
        cr.set_source_rgb(*lc); cr.fill()
        cr.arc(hx, top + 4 * fk, R * 0.75, math.radians(180), math.radians(360)); cr.close_path(); cr.fill()
        cr.set_source_rgb(0.97, 0.95, 0.9); cr.rectangle(hx - R * 0.75, top - 2 * fk, R * 1.5, 6 * fk); cr.fill()
    elif hat == "headphones":
        cr.set_source_rgb(0.15, 0.15, 0.17); cr.set_line_width(7 * fk)
        cr.arc(hx, hy, R * 1.08, math.radians(185), math.radians(355)); cr.stroke()
        for s in (-1, 1):
            cr.rectangle(hx + s * R * 1.05 - 8 * fk, hy - 12 * fk, 16 * fk, 26 * fk); cr.fill()
    elif hat == "tin_helmet":   # Brodie-style helmet with a wide brim
        cr.save(); cr.translate(hx, top + 10 * fk); cr.scale(1, 0.2); cr.arc(0, 0, R * 1.45, 0, 2 * math.pi); cr.restore()
        cr.set_source_rgb(0.36, 0.4, 0.27); cr.fill()
        cr.arc(hx, top + 10 * fk, R * 0.9, math.radians(180), math.radians(360)); cr.close_path(); cr.fill()
    elif hat == "m1_helmet":     # rounded American-style helmet
        cr.arc(hx, hy - 2 * fk, R * 1.12, math.radians(175), math.radians(365)); cr.close_path()
        cr.set_source_rgb(0.33, 0.37, 0.24); cr.fill_preserve(); cr.set_source_rgb(*colour); cr.set_line_width(3 * fk); cr.stroke()
        cr.move_to(hx - R * 1.2, hy - 2 * fk); cr.line_to(hx + R * 1.2, hy - 2 * fk); cr.set_line_width(5 * fk)
        cr.set_source_rgb(0.25, 0.28, 0.18); cr.stroke()
    elif hat == "fire_helmet":
        cr.save(); cr.translate(hx, top + 12 * fk); cr.scale(1, 0.24); cr.arc(0, 0, R * 1.4, 0, 2 * math.pi); cr.restore()
        cr.set_source_rgb(0.55, 0.5, 0.42); cr.fill()
        cr.arc(hx, top + 12 * fk, R * 0.95, math.radians(180), math.radians(360)); cr.close_path(); cr.fill()
        cr.rectangle(hx - 4 * fk, top - 30 * fk, 8 * fk, 30 * fk); cr.fill()
    elif hat == "flying_cap":
        cr.arc(hx, hy - 2 * fk, R * 1.03, math.radians(160), math.radians(380)); cr.close_path()
        cr.set_source_rgb(0.45, 0.32, 0.2); cr.fill()
        for dx in (-11, 11):    # goggles pushed up
            cr.arc(hx + 12 * fk * facing + dx * fk, top + 12 * fk, 9 * fk, 0, 2 * math.pi)
            cr.set_source_rgb(0.75, 0.85, 0.9); cr.fill_preserve(); cr.set_source_rgb(*colour); cr.set_line_width(3 * fk); cr.stroke()
    elif hat == "baker":
        cr.rectangle(hx - R * 0.7, top - 34 * fk, R * 1.4, 40 * fk)
        cr.set_source_rgb(0.99, 0.99, 0.97); cr.fill_preserve(); cr.set_source_rgb(*colour); cr.set_line_width(3 * fk); cr.stroke()
        for dx in (-0.45, 0, 0.45):
            cr.arc(hx + R * dx, top - 34 * fk, R * 0.35, math.radians(180), math.radians(360))
            cr.set_source_rgb(0.99, 0.99, 0.97); cr.fill_preserve(); cr.set_source_rgb(*colour); cr.stroke()

    if look.get("shield"):
        shield_spear(cr, P(lhand), k * BASE * 0.85, lc, facing)
    if look.get("name"):
        cr.select_font_face("Instrument Sans", 0, 1); cr.set_font_size(30)
        w = cr.text_extents(look["name"]).x_advance
        cr.set_source_rgb(*colour)
        cr.move_to(x - w / 2, ground + 48); cr.show_text(look["name"])
    cr.new_path()
    return {"lhand": P(lhand), "rhand": P(rhand), "head": (hx, hy), "top": (hx, top)}


# ------------------------------------------------------------------- props ----
def ground_line(cr, y=820):
    cr.set_source_rgb(*GROUND)
    cr.rectangle(0, y, W, H - y)
    cr.fill()
    cr.set_source_rgb(*INK)
    cr.set_line_width(4)
    cr.move_to(0, y); cr.line_to(W, y); cr.stroke()


def bubble(cr, x, y, r, a, text="?", colour=INK):
    cr.new_path()
    if a <= 0:
        return
    s = _ease(a)
    for i, (dx, dy, rr) in enumerate(((-r * 0.9, r * 1.25, r * 0.12), (-r * 0.6, r * 0.95, r * 0.18))):
        cr.arc(x + dx, y + dy, rr * s, 0, 2 * math.pi)
        cr.set_source_rgb(*PAPER); cr.fill_preserve(); cr.set_source_rgb(*colour); cr.set_line_width(4); cr.stroke()
    cr.save()
    cr.translate(x, y)
    cr.scale(1.25 * s, 0.9 * s)
    cr.arc(0, 0, r, 0, 2 * math.pi)
    cr.restore()
    cr.set_source_rgb(*PAPER); cr.fill_preserve(); cr.set_source_rgb(*colour); cr.set_line_width(5); cr.stroke()
    if s > 0.6:
        cr.select_font_face("Young Serif", 0, 0)
        cr.set_font_size(r * 1.1 * s)
        w = cr.text_extents(text).x_advance
        cr.move_to(x - w / 2, y + r * 0.38 * s)
        cr.show_text(text)


def coin(cr, x, y, r=26, label="£"):
    cr.new_path()
    cr.arc(x, y, r, 0, 2 * math.pi)
    cr.set_source_rgb(*GOLD); cr.fill_preserve()
    cr.set_source_rgb(*INK); cr.set_line_width(4); cr.stroke()
    cr.select_font_face("Instrument Sans", 0, 1); cr.set_font_size(r * 1.15)
    w = cr.text_extents(label).x_advance
    cr.move_to(x - w / 2, y + r * 0.4); cr.show_text(label)


def box(cr, x, y, w, h, label, accent):
    cr.rectangle(x, y, w, h)
    cr.set_source_rgb(*accent); cr.fill_preserve()
    cr.set_source_rgb(*INK); cr.set_line_width(5); cr.stroke()
    cr.rectangle(x + w * 0.35, y - 6, w * 0.3, 12)
    cr.set_source_rgb(*INK); cr.fill()
    cr.select_font_face("Instrument Sans", 0, 1); cr.set_font_size(h * 0.32)
    tw = cr.text_extents(label).x_advance
    cr.set_source_rgb(*PAPER); cr.move_to(x + w / 2 - tw / 2, y + h * 0.62); cr.show_text(label)


def bill(cr, x, y, ang=0):
    cr.save(); cr.translate(x, y); cr.rotate(ang)
    cr.rectangle(-55, -75, 110, 150)
    cr.set_source_rgb(1, 1, 1); cr.fill_preserve(); cr.set_source_rgb(*INK); cr.set_line_width(4); cr.stroke()
    for i in range(4):
        cr.move_to(-38, -45 + i * 22); cr.line_to(38 - (i % 2) * 20, -45 + i * 22)
    cr.set_line_width(5); cr.stroke()
    cr.select_font_face("Instrument Sans", 0, 1); cr.set_font_size(42)
    cr.set_source_rgb(0.75, 0.2, 0.15); cr.move_to(-14, 62); cr.show_text("£")
    cr.restore()


def jar(cr, x, ground, fill, accent):
    w, h = 190, 240
    top = ground - h
    level = h * 0.9 * fill
    cr.rectangle(x - w / 2 + 8, ground - level, w - 16, level)
    cr.set_source_rgb(*GOLD); cr.fill()
    for i in range(int(fill * 12)):
        cx = x - w / 2 + 30 + (i * 53) % (w - 60)
        cy = ground - 20 - (i // 3) * 22
        cr.arc(cx, cy, 18, 0, 2 * math.pi); cr.set_source_rgb(0.75, 0.56, 0.16); cr.set_line_width(3); cr.stroke()
    cr.set_source_rgb(*INK); cr.set_line_width(6)
    cr.move_to(x - w / 2, top); cr.line_to(x - w / 2, ground); cr.line_to(x + w / 2, ground); cr.line_to(x + w / 2, top)
    cr.stroke()
    cr.rectangle(x - w / 2 - 10, top - 26, w + 20, 26)
    cr.set_source_rgb(*accent); cr.fill_preserve(); cr.set_source_rgb(*INK); cr.stroke()


def river(cr, x0, x1, ground, t):
    cr.rectangle(x0, ground - 4, x1 - x0, 70)
    cr.set_source_rgb(*WATER); cr.fill()
    cr.set_source_rgb(1, 1, 1); cr.set_line_width(4)
    for row in range(3):
        y = ground + 14 + row * 18
        cr.move_to(x0, y)
        for xx in range(int(x0), int(x1), 12):
            cr.line_to(xx, y + math.sin(xx / 30 + t * 3 + row) * 4)
        cr.stroke()


def shield_spear(cr, hand, k=1.0, accent=(0.75, 0.2, 0.15), facing=1):
    x, y = hand
    cr.set_source_rgb(*INK); cr.set_line_width(6 * k)
    cr.move_to(x + 10 * facing, y + 60 * k); cr.line_to(x + 10 * facing, y - 160 * k); cr.stroke()
    cr.move_to(x + 10 * facing, y - 160 * k); cr.line_to(x + 10 * facing - 12, y - 132 * k)
    cr.line_to(x + 10 * facing + 12, y - 132 * k); cr.close_path(); cr.fill()
    cr.save(); cr.translate(x + 26 * facing * k, y - 10 * k); cr.scale(1, 1.35)
    cr.arc(0, 0, 34 * k, 0, 2 * math.pi); cr.restore()
    cr.set_source_rgb(*accent); cr.fill_preserve(); cr.set_source_rgb(*INK); cr.set_line_width(5 * k); cr.stroke()


def sparkles(cr, x, y, t, accent):
    rnd = random.Random(7)
    for i in range(14):
        a = rnd.uniform(0, 2 * math.pi); sp = rnd.uniform(120, 260)
        d = (t % 1.6) / 1.6
        px, py = x + math.cos(a) * sp * d, y + math.sin(a) * sp * d - 60 * d
        cr.set_source_rgba(*(accent if i % 2 else GOLD), 1 - d)
        cr.rectangle(px - 7, py - 7, 14, 14); cr.fill()


def sweat(cr, head, t, k=1.0):
    x, y = head
    d = (t % 1.2) / 1.2
    cr.save(); cr.translate(x - 60 * k, y - 10 * k + d * 40)
    cr.move_to(0, -14); cr.curve_to(12, 4, 8, 14, 0, 14); cr.curve_to(-8, 14, -12, 4, 0, -14)
    cr.restore()
    cr.set_source_rgba(*WATER, 1 - d); cr.fill()


def shovel(cr, hand, t):
    x, y = hand
    cr.set_source_rgb(*INK); cr.set_line_width(7)
    cr.move_to(x - 30, y - 40); cr.line_to(x + 40, y + 70); cr.stroke()
    cr.save(); cr.translate(x + 48, y + 84); cr.rotate(0.55)
    cr.rectangle(-18, 0, 36, 44); cr.restore()
    cr.set_source_rgb(0.55, 0.55, 0.58); cr.fill()


def cheese(cr, x, y):
    cr.move_to(x - 50, y); cr.line_to(x + 50, y); cr.line_to(x + 50, y - 40); cr.close_path()
    cr.set_source_rgb(0.98, 0.83, 0.35); cr.fill_preserve(); cr.set_source_rgb(*INK); cr.set_line_width(4); cr.stroke()
    for cx, cy in ((x + 10, y - 10), (x + 32, y - 22)):
        cr.arc(cx, cy, 5, 0, 2 * math.pi); cr.fill()


def label(cr, text, t, accent):
    if not text:
        return
    a = _ease(t / 0.5)
    cr.select_font_face("Young Serif", 0, 0); cr.set_font_size(52)
    w = cr.text_extents(text).x_advance
    cr.set_source_rgba(*INK, a); cr.move_to(W / 2 - w / 2, 110); cr.show_text(text)
    cr.set_source_rgba(*accent, a); cr.rectangle(W / 2 - 50, 135, 100 * a, 6); cr.fill()


def waves(cr, y, t, colour=WATER, amp=10):
    """A band of sea from y to the bottom of the frame, with a moving wavy top."""
    cr.move_to(0, H)
    for x in range(0, W + 41, 40):
        cr.line_to(x, y + math.sin(x / 90 + t * 2.2) * amp)
    cr.line_to(W, H); cr.close_path(); cr.set_source_rgb(*colour); cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.5); cr.set_line_width(4)
    for i in range(6):
        x = (i * 330 + t * 60) % (W + 200) - 100
        cr.move_to(x, y + 60 + (i % 3) * 50); cr.line_to(x + 70, y + 60 + (i % 3) * 50); cr.stroke()


def liner(cr, x, y, s, funnels=4, tilt=0.0):
    """A simple side-on ocean liner, bow to the right, waterline at y."""
    cr.save(); cr.translate(x, y); cr.rotate(tilt); cr.scale(s, s)
    # hull: black above a red waterline band
    cr.move_to(-520, -120); cr.line_to(560, -120); cr.line_to(500, 0); cr.line_to(-470, 0); cr.close_path()
    cr.set_source_rgb(0.1, 0.1, 0.11); cr.fill()
    cr.rectangle(-480, -18, 990, 18); cr.set_source_rgb(0.62, 0.17, 0.13); cr.fill()
    # white superstructure
    cr.rectangle(-380, -175, 720, 55); cr.set_source_rgb(0.97, 0.96, 0.93); cr.fill()
    cr.rectangle(-300, -205, 560, 30); cr.fill()
    cr.set_source_rgb(0.3, 0.3, 0.32)
    for i in range(22):
        cr.arc(-460 + i * 46, -80, 6, 0, 2 * math.pi); cr.fill()
    for i in range(14):
        cr.rectangle(-360 + i * 50, -162, 22, 18); cr.fill()
    # funnels: buff with black tops, raked back
    for i in range(funnels):
        fx = -250 + i * (500 / max(1, funnels - 1)) if funnels > 1 else 0
        cr.move_to(fx - 28, -205); cr.line_to(fx - 48, -360); cr.line_to(fx + 4, -360); cr.line_to(fx + 24, -205); cr.close_path()
        cr.set_source_rgb(0.86, 0.6, 0.25); cr.fill()
        cr.move_to(fx - 43, -320); cr.line_to(fx - 48, -360); cr.line_to(fx + 4, -360); cr.line_to(fx + 9, -320); cr.close_path()
        cr.set_source_rgb(0.1, 0.1, 0.11); cr.fill()
    # masts
    cr.set_source_rgb(0.25, 0.22, 0.2); cr.set_line_width(7)
    for mx in (-440, 430):
        cr.move_to(mx, -120); cr.line_to(mx - 12, -430); cr.stroke()
    cr.restore()


def iceberg(cr, x, y, s=1.0):
    cr.move_to(x - 230 * s, y + 4); cr.line_to(x - 150 * s, y - 120 * s); cr.line_to(x - 60 * s, y - 150 * s)
    cr.line_to(x + 10 * s, y - 260 * s); cr.line_to(x + 90 * s, y - 140 * s); cr.line_to(x + 190 * s, y - 90 * s)
    cr.line_to(x + 240 * s, y + 4); cr.close_path()
    cr.set_source_rgb(0.93, 0.96, 0.98); cr.fill_preserve(); cr.set_source_rgb(0.6, 0.72, 0.8); cr.set_line_width(5); cr.stroke()
    cr.move_to(x + 10 * s, y - 260 * s); cr.line_to(x - 10 * s, y - 60 * s); cr.line_to(x + 90 * s, y - 140 * s)
    cr.close_path(); cr.set_source_rgba(0.75, 0.86, 0.92, 0.9); cr.fill()


def rowboat(cr, x, y, w=620):
    cr.move_to(x - w / 2, y - 60); cr.line_to(x + w / 2, y - 60); cr.line_to(x + w / 2 - 70, y + 20)
    cr.line_to(x - w / 2 + 70, y + 20); cr.close_path()
    cr.set_source_rgb(0.97, 0.96, 0.93); cr.fill_preserve(); cr.set_source_rgb(*INK); cr.set_line_width(6); cr.stroke()
    cr.rectangle(x - w / 2 + 10, y - 60, w - 20, 12); cr.set_source_rgb(0.55, 0.38, 0.22); cr.fill()


NIGHT = (0.06, 0.08, 0.15)


def night_sky(cr, t, seed=3, y0=150, y1=560, moon=None):
    cr.set_source_rgb(*NIGHT); cr.rectangle(0, y0, W, H); cr.fill()
    rnd = random.Random(seed)
    for i in range(80):
        cr.set_source_rgba(1, 1, 1, 0.35 + 0.4 * abs(math.sin(t * 2 + i)))
        cr.arc(rnd.uniform(0, W), rnd.uniform(y0 + 20, y1), 2.2, 0, 2 * math.pi); cr.fill()
    if moon:
        cr.arc(moon[0], moon[1], 46, 0, 2 * math.pi); cr.set_source_rgb(0.95, 0.93, 0.82); cr.fill()


def dawn_sky(cr, y0=150, y1=700):
    g = cairo.LinearGradient(0, y0, 0, y1)
    g.add_color_stop_rgb(0, 0.42, 0.46, 0.55); g.add_color_stop_rgb(1, 0.86, 0.72, 0.58)
    cr.set_source(g); cr.rectangle(0, y0, W, y1 - y0); cr.fill()


def glider_shape(cr, x, y, s=1.0, ang=0.0, colour=(0.12, 0.12, 0.13)):
    """A Horsa-style glider seen from the side: long body, high wing, tall tail."""
    cr.save(); cr.translate(x, y); cr.rotate(ang); cr.scale(s, s)
    cr.move_to(-260, -10); cr.curve_to(-200, -46, 200, -46, 250, -18); cr.line_to(250, 18)
    cr.curve_to(150, 30, -150, 30, -260, 14); cr.close_path(); cr.set_source_rgb(*colour); cr.fill()
    cr.move_to(-250, -14); cr.line_to(-300, -100); cr.line_to(-250, -100); cr.line_to(-200, -20); cr.close_path(); cr.fill()
    cr.rectangle(-60, -52, 200, 16); cr.fill()
    cr.set_source_rgb(0.75, 0.78, 0.8)
    for i in range(5):
        cr.rectangle(-150 + i * 60, -18, 20, 14); cr.fill()
    cr.restore()


def bascule_bridge(cr, x, ground, colour=(0.62, 0.64, 0.66)):
    """A canal lifting bridge: a flat deck with a big curved counterweight frame over one end."""
    cr.set_source_rgb(*colour)
    cr.rectangle(x - 260, ground - 30, 520, 20); cr.fill()
    cr.set_line_width(14)
    cr.move_to(x - 160, ground - 30); cr.curve_to(x - 140, ground - 210, x + 40, ground - 230, x + 120, ground - 120); cr.stroke()
    cr.move_to(x - 160, ground - 30); cr.line_to(x + 120, ground - 120); cr.stroke()
    for i in range(5):
        xx = x - 130 + i * 55
        cr.move_to(xx, ground - 30 - i * 18); cr.line_to(xx, ground - 30); cr.set_line_width(6); cr.stroke()


def landing_craft(cr, x, y, ramp=0.0, s=1.0):
    """A boxy landing craft, ramp at the front (right). ramp 0 = up, 1 = down."""
    cr.save(); cr.translate(x, y); cr.scale(s, s)
    cr.move_to(-260, -90); cr.line_to(150, -90); cr.line_to(170, 20); cr.line_to(-240, 20); cr.close_path()
    cr.set_source_rgb(0.36, 0.41, 0.37); cr.fill()
    cr.rectangle(-250, -110, 60, 30); cr.set_source_rgb(0.3, 0.34, 0.3); cr.fill()
    cr.save(); cr.translate(160, 20); cr.rotate(ramp * 1.35)
    cr.rectangle(-14, -120, 22, 125); cr.set_source_rgb(0.42, 0.47, 0.42); cr.fill(); cr.restore()
    cr.restore()


def hedgehog(cr, x, ground, s=1.0):
    cr.set_source_rgb(0.2, 0.2, 0.22); cr.set_line_width(9 * s)
    cr.move_to(x - 34 * s, ground); cr.line_to(x + 34 * s, ground - 64 * s); cr.stroke()
    cr.move_to(x + 34 * s, ground); cr.line_to(x - 34 * s, ground - 64 * s); cr.stroke()
    cr.move_to(x, ground + 4); cr.line_to(x, ground - 70 * s); cr.stroke()


def plane_c47(cr, x, y, s=1.0, colour=(0.12, 0.12, 0.13)):
    cr.save(); cr.translate(x, y); cr.scale(s, s); cr.set_source_rgb(*colour)
    cr.move_to(-220, 0); cr.curve_to(-120, -36, 160, -36, 230, -6); cr.curve_to(160, 22, -120, 22, -220, 10); cr.close_path(); cr.fill()
    cr.move_to(-200, -6); cr.line_to(-240, -80); cr.line_to(-195, -80); cr.line_to(-150, -10); cr.close_path(); cr.fill()
    cr.save(); cr.scale(1, 0.25); cr.arc(30, 20, 150, 0, 2 * math.pi); cr.restore(); cr.fill()
    cr.restore()


def parachute(cr, x, y, s=1.0, sway=0.0, light=(0.92, 0.9, 0.84)):
    cr.save(); cr.translate(x, y); cr.rotate(sway); cr.scale(s, s)
    cr.arc(0, 0, 60, math.pi, 2 * math.pi); cr.close_path(); cr.set_source_rgb(*light); cr.fill()
    cr.set_line_width(2.5); cr.set_source_rgba(*light, 0.8)
    for dx in (-58, -20, 20, 58):
        cr.move_to(dx, 0); cr.line_to(0, 90); cr.stroke()
    cr.set_line_width(7)
    cr.arc(0, 104, 13, 0, 2 * math.pi); cr.stroke()
    cr.move_to(0, 117); cr.line_to(0, 160); cr.stroke()
    cr.move_to(0, 160); cr.line_to(-14, 196); cr.move_to(0, 160); cr.line_to(14, 196); cr.stroke()
    cr.move_to(0, 128); cr.line_to(-24, 112); cr.move_to(0, 128); cr.line_to(24, 112); cr.stroke()
    cr.restore()


def plant_building(cr, x, ground, s=1.0, lit=True, broken=0.0):
    """A blocky reactor building with a striped ventilation stack. broken 0-1 tears the roof off one block."""
    cr.save(); cr.translate(x, ground); cr.scale(s, s)
    cr.set_source_rgb(0.62, 0.64, 0.66); cr.rectangle(-520, -220, 640, 220); cr.fill()
    cr.set_source_rgb(0.55, 0.57, 0.6); cr.rectangle(120, -330, 300, 330); cr.fill()
    if broken > 0:
        cr.set_source_rgb(0.08, 0.08, 0.1)
        cr.move_to(140, -330); cr.line_to(180, -330 + 120 * broken); cr.line_to(260, -330 + 60 * broken)
        cr.line_to(330, -330 + 150 * broken); cr.line_to(400, -330); cr.close_path(); cr.fill()
    cr.set_source_rgb(0.5, 0.52, 0.55); cr.rectangle(-640, -150, 120, 150); cr.fill()
    # ventilation stack, red and white bands
    for i in range(8):
        cr.set_source_rgb(*((0.78, 0.2, 0.17) if i % 2 == 0 else (0.94, 0.93, 0.9)))
        w0, w1 = 52 - i * 2.5, 52 - (i + 1) * 2.5
        y0, y1 = -330 - i * 38, -330 - (i + 1) * 38
        cr.move_to(70 - w0 / 2, y0); cr.line_to(70 + w0 / 2, y0); cr.line_to(70 + w1 / 2, y1); cr.line_to(70 - w1 / 2, y1)
        cr.close_path(); cr.fill()
    if lit:
        cr.set_source_rgb(0.98, 0.86, 0.45)
        for i in range(10):
            cr.rectangle(-490 + i * 58, -150, 22, 14); cr.fill()
    cr.restore()


def bus(cr, x, ground, colour=(0.85, 0.66, 0.2), s=1.0):
    cr.save(); cr.translate(x, ground); cr.scale(s, s)
    cr.rectangle(-180, -130, 360, 110); cr.set_source_rgb(*colour); cr.fill()
    cr.set_source_rgb(0.75, 0.86, 0.92)
    for i in range(6):
        cr.rectangle(-165 + i * 56, -118, 44, 40); cr.fill()
    cr.set_source_rgb(0.15, 0.15, 0.16)
    for wx in (-110, 110):
        cr.arc(wx, -18, 24, 0, 2 * math.pi); cr.fill()
    cr.restore()


def flat_block(cr, x, ground, w, h, colour=(0.82, 0.8, 0.76)):
    cr.rectangle(x, ground - h, w, h); cr.set_source_rgb(*colour); cr.fill()
    cr.set_source_rgb(0.55, 0.62, 0.68)
    for r in range(int(h // 50)):
        for c in range(int(w // 45)):
            cr.rectangle(x + 12 + c * 45, ground - h + 14 + r * 50, 22, 26); cr.fill()


def helicopter(cr, x, y, t, s=1.0, colour=(0.33, 0.38, 0.3)):
    cr.save(); cr.translate(x, y); cr.scale(s, s); cr.set_source_rgb(*colour)
    cr.save(); cr.scale(1.6, 1); cr.arc(0, 0, 60, 0, 2 * math.pi); cr.restore(); cr.fill()
    cr.rectangle(60, -16, 200, 22); cr.fill()
    cr.rectangle(240, -60, 20, 60); cr.fill()
    cr.set_source_rgb(0.75, 0.86, 0.92); cr.save(); cr.scale(1.6, 1); cr.arc(-28, -12, 26, math.pi, 2 * math.pi); cr.restore(); cr.fill()
    blade = 280 * abs(math.cos(t * 30))
    cr.set_source_rgb(0.15, 0.15, 0.16); cr.set_line_width(8)
    cr.move_to(-blade, -72); cr.line_to(blade, -72); cr.stroke()
    cr.rectangle(-6, -72, 12, 14); cr.fill()
    cr.restore()


def smoke_plume(cr, x, y, t, colour=(0.55, 0.55, 0.58), n=10, rise=300):
    for i in range(n):
        ph = (t * 0.35 + i / n) % 1
        cr.arc(x + math.sin(i * 1.7 + t) * 30 + ph * 120, y - ph * rise, 30 + ph * 70, 0, 2 * math.pi)
        cr.set_source_rgba(*colour, 0.55 * (1 - ph)); cr.fill()


# ------------------------------------------------------------------ scenes ----
def scene(cr, spec, t, accent, outfit):
    """Draw one frame of a stick scene at time t (seconds)."""
    cr.set_source_rgb(*PAPER); cr.paint()
    cr.set_source_rgb(*accent); cr.rectangle(0, 0, W, 10); cr.fill()
    G = 850
    kind = spec.get("scene", "think")
    ground_line(cr, G)
    label(cr, spec.get("label", ""), t, accent)
    main = resolve(spec.get("who"), accent, outfit)
    kw = dict(t=t, look=main)

    if kind == "walk":
        x = _mix(300, 1500, min(1, t / 4.5))
        figure(cr, x, G, walk_pose(t * 7), **kw)
    elif kind == "march":
        follower = resolve(spec.get("others", "roman_soldier"), accent, outfit)
        lead = spec.get("who")
        for i in range(5):
            x = -200 + t * 330 - i * 230
            p = walk_pose(t * 7 + i * 0.7, 22)
            look = main if (i == 0 and lead) else variant(follower, i * 31 + 7)
            figure(cr, x, G, p, scale=0.8, face="calm", t=t, look=look)
    elif kind == "cross_river":
        river(cr, 820, 1100, G, t)
        x = _mix(350, 1500, min(1, t / 4.6))
        pts = figure(cr, x, G, walk_pose(t * 6), **kw)
        if 820 < x < 1100:   # splash
            cr.set_source_rgba(1, 1, 1, 0.9)
            for i in range(5):
                cr.arc(x - 30 + i * 15, G + 6 - abs(math.sin(t * 9 + i)) * 26, 6, 0, 2 * math.pi); cr.fill()
    elif kind == "think":
        if spec.get("river"):
            river(cr, 1050, 1920, G, t)
        k = _ease(t / 0.8)
        p = pose_mix(POSES["stand"], POSES["think"], k)
        pts = figure(cr, 760, G, p, **kw)
        bubble(cr, pts["head"][0] + 230, pts["head"][1] - 70, 75, (t - 0.8) / 0.6, spec.get("bubble", "?"))
    elif kind == "worried":
        k = _ease(t / 0.6)
        p = pose_mix(POSES["stand"], POSES["worried"], k)
        pts = figure(cr, 760, G, p, face="worried", **kw)
        sweat(cr, pts["head"], t)
        if spec.get("prop") == "bill":
            bill(cr, 1160, 560 + math.sin(t * 2) * 10, 0.12)
    elif kind == "celebrate":
        jump = abs(math.sin(t * 4)) * 60
        pts = figure(cr, 960, G, POSES["cheer"], face="happy", jump=jump, **kw)
        sparkles(cr, 960, 420, t, accent)
    elif kind == "point":
        p = pose_mix(POSES["stand"], POSES["point"], _ease(t / 0.6))
        figure(cr, 600, G, p, **kw)
        bubble(cr, 1250, 470, 110, (t - 0.6) / 0.5, spec.get("bubble", "!"))
    elif kind == "shrug":
        k = (math.sin(t * 3) + 1) / 2
        p = pose_mix(POSES["stand"], POSES["shrug"], 0.5 + 0.5 * k)
        figure(cr, 960, G, p, face="worried", **kw)
    elif kind == "deposit":
        # walk in with a coin, drop it into a labelled box
        bx = 1180
        box(cr, bx, G - 170, 230, 170, spec.get("box", "ISA"), accent)
        if t < 2.6:
            x = _mix(260, bx - 120, t / 2.6)
            pts = figure(cr, x, G, walk_pose(t * 7, carry=True), **kw)
            coin(cr, pts["rhand"][0] + 10, pts["rhand"][1] - 20)
        else:
            pts = figure(cr, bx - 120, G, POSES["point"], face="happy", **kw)
            d = min(1, (t - 2.6) / 0.7)
            coin(cr, _mix(pts["rhand"][0], bx + 115, d), _mix(pts["rhand"][1], G - 175, d) - math.sin(d * math.pi) * 90)
            if t > 3.4:
                cr.select_font_face("Instrument Sans", 0, 1); cr.set_font_size(48)
                cr.set_source_rgba(*accent, min(1, (t - 3.4) / 0.4))
                cr.move_to(bx + 70, G - 220 - (t - 3.4) * 30); cr.show_text(spec.get("pop", "+ tax-free"))
    elif kind == "coins_jar":
        fill = min(1, t / 4.0)
        jar(cr, 1180, G, fill, accent)
        for i in range(3):
            ph = (t * 1.3 + i / 3) % 1
            coin(cr, 1180 + (i - 1) * 40, _mix(420, G - 240 * fill, ph), 22)
        pts = figure(cr, 700, G, POSES["cheer"] if t > 3.2 else POSES["point"], face="happy" if t > 3.2 else "calm",
                     jump=abs(math.sin(t * 4)) * 40 if t > 3.2 else 0, **kw)
        if t > 3.2:
            sparkles(cr, 1180, 520, t, accent)
    elif kind == "crowd_shocked":
        pool = spec.get("others") or (CROWD_POOL if outfit == "cape" else MODERN_POOL)
        for i, x in enumerate((420, 700, 980, 1260, 1540)):
            k = _ease((t - i * 0.15) / 0.5)
            p = pose_mix(POSES["stand"], POSES["worried"] if i % 2 else POSES["shrug"], k)
            if i == 2 and spec.get("who"):
                look = main
            else:
                look = variant(resolve(pool[(i * 3 + len(pool)) % len(pool)], accent, outfit), i * 17 + 3)
            figure(cr, x, G, p, scale=0.75, face="surprised" if k > 0.5 else "calm", t=t,
                   facing=1 if i < 2 else -1, look=look)
    elif kind == "dig":
        cr.save(); cr.translate(1150, G); cr.scale(1, 0.35); cr.arc(0, 0, 150, 0, math.pi); cr.restore()
        cr.set_source_rgb(0.45, 0.33, 0.22); cr.fill()
        swing = (math.sin(t * 5) + 1) / 2
        p = pose_mix(POSES["dig"], dict(POSES["dig"], lean=10, ls=90, rs=70), swing)
        pts = figure(cr, 900, G, p, **kw)
        shovel(cr, pts["lhand"], t)
        if spec.get("prop") == "cheese":
            cheese(cr, 1150, G + 10 - min(1, t / 4) * 0 )
    elif kind == "read":
        p = POSES["hold"]
        pts = figure(cr, 900, G, p, **kw)
        x, y = pts["rhand"]
        cr.rectangle(x - 10, y - 90, 150, 110)
        cr.set_source_rgb(0.98, 0.95, 0.85); cr.fill_preserve(); cr.set_source_rgb(*INK); cr.set_line_width(4); cr.stroke()
        for i in range(4):
            cr.move_to(x + 10, y - 66 + i * 22); cr.line_to(x + 110 - (i % 2) * 30, y - 66 + i * 22)
        cr.stroke()
    elif kind == "talk":
        other = resolve(spec.get("other", "worker"), accent, outfit)
        speaker = int(t / 1.6) % 2
        p1 = pose_mix(POSES["stand"], POSES["point"], 0.6 if speaker == 0 else 0)
        p2 = pose_mix(POSES["stand"], POSES["shrug"], 0.6 if speaker == 1 else 0)
        a = figure(cr, 700, G, p1, **kw)
        b = figure(cr, 1220, G, p2, t=t, look=other, facing=-1)
        head = a["head"] if speaker == 0 else b["head"]
        bubble(cr, head[0] + (160 if speaker == 0 else -160), head[1] - 120, 60, ((t % 1.6) / 0.4),
               spec.get("bubbles", ["!", "?"])[speaker])
    elif kind == "ship":
        night = spec.get("night", False)
        if night:
            cr.set_source_rgb(0.08, 0.1, 0.18); cr.rectangle(0, 150, W, H); cr.fill()
            rnd = random.Random(5)
            for _ in range(70):
                cr.set_source_rgba(1, 1, 1, 0.4 + 0.4 * abs(math.sin(t * 2 + _)))
                cr.arc(rnd.uniform(0, W), rnd.uniform(170, 600), 2.2, 0, 2 * math.pi); cr.fill()
        sea_y = 780
        hit = spec.get("iceberg", False)
        stop_t = 4.2
        if hit:
            k = min(1, t / stop_t)
            sx = _mix(-300, 900, 1 - (1 - k) ** 2)
            shake = math.sin(t * 40) * 5 if stop_t - 0.3 < t < stop_t + 0.6 else 0
            liner(cr, sx + shake, sea_y + 20, 0.9, spec.get("funnels", 4))
            iceberg(cr, 1560, sea_y + 10, 1.1)
            if t > stop_t - 0.3:
                sparkles(cr, 1380, sea_y - 60, t, (0.85, 0.85, 0.9))
        else:
            liner(cr, _mix(560, 1360, min(1, t / 8)), sea_y + 20, 0.9, spec.get("funnels", 4))
            if spec.get("smoke", True):
                for i in range(6):
                    ph = (t * 0.6 + i / 6) % 1
                    cr.arc(_mix(560, 1360, min(1, t / 8)) - 200 - ph * 260, sea_y - 360 - ph * 120, 20 + ph * 40, 0, 2 * math.pi)
                    cr.set_source_rgba(0.5, 0.5, 0.5, 0.35 * (1 - ph)); cr.fill()
        waves(cr, sea_y, t, (0.16, 0.24, 0.36) if night else WATER)
    elif kind == "lifeboat":
        sea_y = 800
        if spec.get("night"):
            cr.set_source_rgb(0.08, 0.1, 0.18); cr.rectangle(0, 150, W, H); cr.fill()
            rnd = random.Random(9)
            for _ in range(60):
                cr.set_source_rgba(1, 1, 1, 0.4 + 0.4 * abs(math.sin(t * 2 + _)))
                cr.arc(rnd.uniform(0, W), rnd.uniform(170, 520), 2.2, 0, 2 * math.pi); cr.fill()
        pool = spec.get("others") or EDWARDIAN_POOL
        bob = math.sin(t * 1.8) * 10
        bx = 960 + math.sin(t * 0.6) * 30
        n = max(2, min(6, int(spec.get("count", 5))))
        xs = [bx + (i - (n - 1) / 2) * 150 for i in range(n)]
        for i, x in enumerate(xs):
            look = main if (i == n // 2 and spec.get("who")) else variant(resolve(pool[i % len(pool)], accent, outfit), i * 13 + 5)
            row = math.sin(t * 2.5 + i) * 18
            p = dict(POSES["hold"], ls=55 + row, rs=55 - row)
            figure(cr, x, sea_y + bob + 150, p, scale=0.85, face=spec.get("face", "worried"), t=t, look=look,
                   facing=1 if i < n / 2 else -1)
        rowboat(cr, bx, sea_y + bob, 150 * n + 200)
        waves(cr, sea_y + 25, t, (0.16, 0.24, 0.36) if spec.get("night") else WATER)
    elif kind == "radio":
        # an operator at a desk, tapping a key; signals rise from an aerial
        cr.rectangle(1010, G - 330, 360, 26); cr.set_source_rgb(0.55, 0.38, 0.22); cr.fill()
        cr.rectangle(1040, G - 304, 20, 304); cr.rectangle(1320, G - 304, 20, 304); cr.fill()
        cr.rectangle(1180, G - 470, 170, 140); cr.set_source_rgb(0.3, 0.28, 0.26); cr.fill()
        for i in range(3):
            cr.arc(1215 + i * 50, G - 420, 13, 0, 2 * math.pi); cr.set_source_rgb(0.85, 0.66, 0.22); cr.fill()
        tap = 1 if (t * 6) % 1 < 0.5 else 0
        cr.set_source_rgb(*INK); cr.rectangle(1070, G - 345 + tap * 6, 70, 14); cr.fill()
        cr.set_line_width(8); cr.move_to(1265, G - 470); cr.line_to(1265, G - 560); cr.stroke()
        for i in range(3):
            ph = (t * 0.7 + i / 3) % 1
            cr.set_source_rgba(*accent, 1 - ph); cr.set_line_width(6)
            cr.arc(1265, G - 560, 30 + ph * 150, math.radians(200), math.radians(340)); cr.stroke()
        p = dict(POSES["hold"], ls=70 + tap * 8, le=30, rs=65, re=35, lean=6)
        figure(cr, 860, G, p, **kw)
        msg = spec.get("bubble", "SOS")
        if t > 0.8:
            cr.select_font_face("Instrument Sans", 0, 1); cr.set_font_size(64)
            w_ = cr.text_extents(msg).x_advance
            cr.set_source_rgba(*accent, min(1, (t - 0.8) / 0.4)); cr.move_to(1600 - w_ / 2, G - 520); cr.show_text(msg)
            dots = "\u2022 \u2022 \u2022  \u2013 \u2013 \u2013  \u2022 \u2022 \u2022"
            cr.set_font_size(40); cr.set_source_rgba(*INK, min(1, (t - 0.8) / 0.4) * 0.8)
            cr.move_to(1600 - cr.text_extents(dots).x_advance / 2, G - 460); cr.show_text(dots)
    elif kind == "lookout":
        # night: a lookout high in the crow's nest spots an iceberg looming out of the dark and rings the bell
        cr.set_source_rgb(0.06, 0.08, 0.15); cr.rectangle(0, 150, W, H); cr.fill()
        rnd = random.Random(3)
        for _ in range(80):
            cr.set_source_rgba(1, 1, 1, 0.35 + 0.4 * abs(math.sin(t * 2 + _)))
            cr.arc(rnd.uniform(0, W), rnd.uniform(170, 560), 2.2, 0, 2 * math.pi); cr.fill()
        sea_y = 900
        grow = _ease(t / 5.5)
        ix = _mix(1900, 1450, grow)
        iceberg(cr, ix, sea_y, _mix(0.25, 1.6, grow))
        cr.set_source_rgba(0.06, 0.08, 0.15, 0.6 * (1 - grow)); cr.rectangle(1100, 150, 820, sea_y - 150); cr.fill()
        waves(cr, sea_y, t, (0.13, 0.2, 0.32))
        # mast, rigging and crow's nest
        mx, nest_y = 480, 610
        cr.set_source_rgb(0.33, 0.27, 0.22); cr.set_line_width(26)
        cr.move_to(mx, H); cr.line_to(mx, 200); cr.stroke()
        cr.set_line_width(4); cr.set_source_rgba(0.6, 0.55, 0.5, 0.7)
        for dx in (-260, -130, 130, 260):
            cr.move_to(mx, 260); cr.line_to(mx + dx, H); cr.stroke()
        look_ = main if spec.get("who") else resolve("lookout", accent, outfit)
        sway = math.sin(t * 1.2) * 3
        p = pose_mix(POSES["stand"], POSES["point"], _ease((t - 1.2) / 0.5))
        pts = figure(cr, mx + 30, nest_y + 175, p, scale=0.8, face="surprised" if t > 1.4 else "calm",
                     t=t, look=dict(look_, name=None))
        cr.rectangle(mx - 110, nest_y, 220, 185); cr.set_source_rgb(0.42, 0.3, 0.2); cr.fill()
        cr.set_source_rgb(0.3, 0.21, 0.14); cr.set_line_width(5)
        for i in range(1, 7):
            cr.move_to(mx - 110, nest_y + i * 26); cr.line_to(mx + 110, nest_y + i * 26); cr.stroke()
        # the warning bell, swinging, with three rings
        ring = t > 2.0 and (t - 2.0) < 2.4
        swing = math.sin((t - 2.0) * 9) * 0.5 if ring else 0
        cr.save(); cr.translate(mx - 150, nest_y - 50); cr.rotate(swing)
        cr.move_to(-28, 52); cr.curve_to(-28, -6, 28, -6, 28, 52); cr.close_path()
        cr.set_source_rgb(*GOLD); cr.fill(); cr.restore()
        cr.set_source_rgb(0.33, 0.27, 0.22); cr.set_line_width(8); cr.move_to(mx - 150, nest_y - 52); cr.line_to(mx, nest_y - 52); cr.stroke()
        cr.select_font_face("Instrument Sans", 0, 1); cr.set_font_size(46)
        for i in range(3):
            st = 2.0 + i * 0.7
            if t > st:
                a = max(0, 1 - (t - st) / 1.6)
                cr.set_source_rgba(*GOLD, a)
                cr.move_to(mx - 330 - i * 40, nest_y - 110 - i * 60 - (t - st) * 25); cr.show_text("DING")
        if t > 4.0 and spec.get("bubble"):
            cr.set_font_size(64); msg = spec["bubble"]
            w_ = cr.text_extents(msg).x_advance
            a = min(1, (t - 4.0) / 0.3)
            cr.set_source_rgba(0.97, 0.95, 0.9, a); cr.rectangle(780 - 30, 330 - 70, w_ + 60, 100); cr.fill()
            cr.set_source_rgba(*accent, a); cr.move_to(780, 330); cr.show_text(msg)
        if spec.get("who") and isinstance(spec["who"], dict) and spec["who"].get("name"):
            cr.set_font_size(30); cr.set_source_rgb(0.95, 0.93, 0.88)
            nm = spec["who"]["name"]; cr.move_to(mx + 130, nest_y + 70); cr.show_text(nm)
    elif kind == "glider":
        # night: a glider swoops in and skids to a stop beside a canal bridge ("phase": "land"),
        # then its troops run for the bridge ("phase": "assault")
        night_sky(cr, t, 11, moon=(1600, 260))
        field = 860
        cr.set_source_rgb(0.1, 0.14, 0.12); cr.rectangle(0, field, W, H); cr.fill()
        cr.set_source_rgb(0.16, 0.24, 0.34); cr.rectangle(1180, field, 560, 70); cr.fill()
        bascule_bridge(cr, 1460, field + 6)
        pale = (0.9, 0.89, 0.84)
        if spec.get("phase", "land") == "land":
            k = min(1, t / 4.2)
            gx = _mix(-300, 640, 1 - (1 - k) ** 2)
            gy = _mix(320, field - 30, min(1, k * 1.25))
            ang = _mix(0.18, 0.0, min(1, k * 1.4))
            glider_shape(cr, gx, gy, 1.0, ang)
            if k >= 0.8:
                for i in range(8):
                    ph = ((t - 3.3) * 1.5 + i / 8) % 1
                    cr.arc(gx - 240 - ph * 160 + i * 12, field - 10 - ph * 70, 16 + ph * 26, 0, 2 * math.pi)
                    cr.set_source_rgba(0.6, 0.55, 0.45, 0.45 * (1 - ph)); cr.fill()
        else:
            glider_shape(cr, 640, field - 30, 1.0, 0.03)
            pool = spec.get("others") or ["british_soldier"]
            lead = spec.get("who")
            for i in range(5):
                st = i * 0.6
                if t < st:
                    continue
                x = _mix(900, 1500, min(1, (t - st) / 3.6)) - i * 20
                look = main if (i == 0 and lead) else variant(resolve(pool[i % len(pool)], accent, outfit), i * 19 + 2)
                gnd = field + 6 if x < 1180 else field - 24
                figure(cr, x, gnd, walk_pose((t - st) * 10, 30), scale=0.45, t=t, look=dict(look, name=None), colour=pale)
            if lead and isinstance(lead, dict) and lead.get("name"):
                cr.select_font_face("Instrument Sans", 0, 1); cr.set_font_size(30); cr.set_source_rgb(*pale)
                cr.move_to(560, field + 70); cr.show_text(lead["name"])
    elif kind == "fleet":
        # dawn: the invasion fleet fills the horizon, barrage balloons above, landing craft heading in
        dawn_sky(cr, 150, 640)
        rnd = random.Random(21)
        horizon = 640
        cr.set_source_rgb(0.3, 0.38, 0.45); cr.rectangle(0, horizon, W, H); cr.fill()
        for i in range(34):
            x = rnd.uniform(-50, W + 50); s = rnd.uniform(0.18, 0.4)
            cr.set_source_rgb(0.32, 0.33, 0.36)
            cr.rectangle(x - 200 * s, horizon - 40 * s, 400 * s, 40 * s); cr.fill()
            cr.rectangle(x - 60 * s, horizon - 90 * s, 120 * s, 50 * s); cr.fill()
            if rnd.random() < 0.5:
                bx, by = x + rnd.uniform(-30, 30), horizon - rnd.uniform(160, 330) + math.sin(t + i) * 6
                cr.set_line_width(1.5); cr.set_source_rgba(0.3, 0.3, 0.3, 0.6)
                cr.move_to(x, horizon - 90 * s); cr.line_to(bx, by + 14); cr.stroke()
                cr.save(); cr.translate(bx, by); cr.scale(1, 0.45); cr.arc(0, 0, 30 * (s + 0.4), 0, 2 * math.pi); cr.restore()
                cr.set_source_rgb(0.62, 0.64, 0.66); cr.fill()
        waves(cr, horizon + 40, t, (0.3, 0.42, 0.52), 6)
        for i in range(4):
            x = (i * 520 + t * 120) % (W + 400) - 200
            landing_craft(cr, x, 905 + (i % 2) * 80, 0, 0.8)
        waves(cr, 985, t * 1.2, (0.26, 0.38, 0.48), 8)
    elif kind == "landing":
        # a landing craft runs in, drops its ramp and soldiers wade towards a beach with obstacles
        dawn_sky(cr, 150, 820)
        beach_y = 760
        cr.move_to(1150, beach_y); cr.line_to(W, beach_y - 40); cr.line_to(W, H); cr.line_to(900, H); cr.close_path()
        cr.set_source_rgb(0.82, 0.74, 0.56); cr.fill()
        cr.move_to(1500, beach_y - 30); cr.line_to(1700, 430); cr.line_to(W, 400); cr.line_to(W, beach_y - 40); cr.close_path()
        cr.set_source_rgb(0.45, 0.5, 0.36); cr.fill()
        for hx_ in (1240, 1390, 1560, 1730):
            hedgehog(cr, hx_, beach_y + 10, 0.9)
        sea_top = 790
        stop = 2.4
        cx = _mix(-200, 760, min(1, t / stop) * (2 - min(1, t / stop)))
        ramp = _ease((t - stop) / 0.7)
        bob = math.sin(t * 2) * 6
        landing_craft(cr, cx, sea_top + 8 + bob, ramp, 1.0)
        pool = spec.get("others") or ["us_soldier"]
        if t > stop + 0.6:
            for i in range(4):
                st = stop + 0.6 + i * 0.5
                if t < st:
                    continue
                x = _mix(cx + 190, 1400, min(1, (t - st) / 6.0)) - i * 70
                depth = max(0, min(1, (1150 - x) / 300))
                gnd = sea_top + 150 * depth + (beach_y - sea_top + 20) * (1 - depth)
                look = main if (i == 0 and spec.get("who")) else variant(resolve(pool[i % len(pool)], accent, outfit), i * 23 + 4)
                figure(cr, x, gnd, walk_pose((t - st) * 6, 18), scale=0.5, t=t, look=dict(look, name=None))
        cr.move_to(0, sea_top)
        for x in range(0, 1121, 40):
            cr.line_to(x, sea_top + math.sin(x / 80 + t * 2.4) * 9)
        cr.line_to(1150, beach_y + 25); cr.line_to(900, H); cr.line_to(0, H); cr.close_path()
        cr.set_source_rgba(0.3, 0.42, 0.5, 0.92); cr.fill()
    elif kind == "paradrop":
        # night: transport planes pass over and parachutes open over the fields
        night_sky(cr, t, 17, moon=(300, 260))
        cr.set_source_rgb(0.08, 0.12, 0.1); cr.rectangle(0, 900, W, H); cr.fill()
        cr.set_source_rgb(0.05, 0.08, 0.06)
        for i in range(9):
            cr.save(); cr.translate(i * 230 + 60, 905); cr.scale(1, 0.4); cr.arc(0, 0, 110, math.pi, 2 * math.pi); cr.restore(); cr.fill()
        for j, (py, ps, sp) in enumerate([(300, 0.8, 260), (420, 0.6, 210)]):
            px = -300 + t * sp + j * 300
            plane_c47(cr, px, py, ps, (0.4, 0.43, 0.48))
            for i in range(6):
                drop_t = i * 0.55 + j * 0.3
                if t < drop_t + 0.2:
                    continue
                age = t - drop_t
                x0 = -300 + drop_t * sp + j * 300 - 120 * ps
                x = x0 + age * 25
                y = py + 40 + min(age, 0.4) * 300 + max(0, age - 0.4) * 70
                if y < 870:
                    parachute(cr, x, y, ps * 0.8 * min(1, age / 0.4 + 0.2), math.sin(t * 2 + i) * 0.08)
    elif kind == "control_room":
        # operators at a big control panel; with "alarm", the lights turn red, an alarm flashes and a
        # power gauge races up after the button is pressed
        cr.set_source_rgb(0.78, 0.8, 0.76); cr.rectangle(0, 150, W, G - 150); cr.fill()
        cr.set_source_rgb(0.55, 0.6, 0.56); cr.rectangle(980, 230, 860, 470); cr.fill()
        press_t = spec.get("press_at", 2.0)
        alarm = spec.get("alarm", False) and t > press_t + 0.4
        rnd = random.Random(8)
        for r in range(6):
            for c in range(14):
                on = rnd.random() < 0.6
                col = (0.9, 0.2, 0.15) if alarm and (r * 14 + c + int(t * 6)) % 3 == 0 else ((0.95, 0.85, 0.4) if on else (0.35, 0.4, 0.36))
                cr.arc(1020 + c * 57, 270 + r * 40, 9, 0, 2 * math.pi); cr.set_source_rgb(*col); cr.fill()
        # gauge
        gx, gy = 1180, 590
        cr.arc(gx, gy, 80, math.pi, 2 * math.pi); cr.set_source_rgb(0.97, 0.96, 0.92); cr.fill()
        level = 0.15 if not alarm else min(1.0, 0.15 + (t - press_t - 0.4) * 1.2)
        ang = math.pi + level * math.pi
        cr.set_source_rgb(*INK); cr.set_line_width(6); cr.move_to(gx, gy); cr.line_to(gx + math.cos(ang) * 70, gy + math.sin(ang) * 70); cr.stroke()
        cr.select_font_face("Instrument Sans", 0, 1); cr.set_font_size(26); cr.set_source_rgb(*INK)
        cr.move_to(gx - 40, gy + 34); cr.show_text("POWER")
        # the button
        bx_, by_ = 1500, 600
        cr.rectangle(bx_ - 70, by_ - 40, 140, 80); cr.set_source_rgb(0.3, 0.32, 0.3); cr.fill()
        pushed = t > press_t
        cr.arc(bx_, by_ - (2 if pushed else 10), 30, 0, 2 * math.pi); cr.set_source_rgb(0.85, 0.18, 0.14); cr.fill()
        if spec.get("button"):
            cr.set_font_size(30); cr.set_source_rgb(0.97, 0.96, 0.92)
            w_ = cr.text_extents(spec["button"]).x_advance; cr.move_to(bx_ - w_ / 2, by_ + 72); cr.show_text(spec["button"])
        cr.set_source_rgb(0.4, 0.42, 0.4); cr.rectangle(980, 700, 860, G - 700); cr.fill()
        others = spec.get("others") or ["operator", "operator"]
        p_main = pose_mix(POSES["stand"], POSES["point"], _ease((t - press_t + 0.6) / 0.6)) if t < press_t + 0.5 else POSES["point"]
        if alarm:
            p_main = POSES["worried"]
        figure(cr, 1680, G, p_main, face="surprised" if alarm else "calm", t=t, look=main, facing=-1)
        for i, o in enumerate(others[:2]):
            p = POSES["worried"] if alarm else POSES["hold"]
            figure(cr, 520 + i * 300, G, p, face="worried" if alarm else "calm", t=t, look=resolve(o, accent, outfit) if isinstance(o, (str, dict)) else o)
        if alarm and int(t * 4) % 2 == 0:
            cr.set_source_rgba(0.9, 0.1, 0.08, 0.18); cr.rectangle(0, 150, W, H); cr.fill()
            cr.arc(980, 200, 28, 0, 2 * math.pi); cr.set_source_rgb(0.95, 0.15, 0.1); cr.fill()
    elif kind == "power_plant":
        # night: the plant; with "explode", a flash, the roof torn open, fire and a rising plume
        night_sky(cr, t, 29)
        cr.set_source_rgb(0.1, 0.12, 0.12); cr.rectangle(0, 880, W, H); cr.fill()
        boom = spec.get("explode_at", 2.4) if spec.get("explode") else 99
        broken = 0 if t < boom else min(1, (t - boom) / 0.3)
        if spec.get("aftermath"):
            broken, boom = 1, -10
        plant_building(cr, 1000, 880, 1.0, lit=t < boom, broken=broken)
        if t > boom:
            k = t - boom
            if k < 0.5:
                cr.set_source_rgba(1, 0.97, 0.85, 0.85 * (1 - k / 0.5)); cr.rectangle(0, 150, W, H); cr.fill()
            for i in range(14):
                a = i * 0.45 + 0.3
                d = min(k, 1.6) * (260 + i * 25)
                cr.rectangle(1270 + math.cos(-a) * d, 560 - math.sin(a) * d * 0.9 + max(0, k - 0.8) * 160, 14, 10)
                cr.set_source_rgba(0.75, 0.42, 0.18, max(0, 1 - k / 3)); cr.fill()
            for i in range(6):
                ph = (t * 1.3 + i / 6) % 1
                cr.arc(1270 + math.sin(i + t * 3) * 40, 560 - ph * 90, 34 * (1 - ph) + 8, 0, 2 * math.pi)
                cr.set_source_rgba(1.0, 0.55 - 0.3 * ph, 0.12, 0.8 * (1 - ph)); cr.fill()
            smoke_plume(cr, 1270, 470, t, (0.5, 0.5, 0.55), 12, 330)
    elif kind == "evacuation":
        # a column of buses takes residents away from a town of apartment blocks
        cr.set_source_rgb(0.78, 0.85, 0.9); cr.rectangle(0, 150, W, G - 150); cr.fill()
        for bx0, w0, h0 in ((60, 300, 420), (420, 260, 340), (1180, 320, 460), (1560, 300, 380)):
            flat_block(cr, bx0, G - 60, w0, h0)
        cr.set_source_rgb(0.42, 0.42, 0.44); cr.rectangle(0, G - 60, W, 80); cr.fill()
        for i in range(4):
            x = 2200 - t * 260 + i * 470
            bus(cr, x, G + 10, s=0.9)
        pool = spec.get("others") or ["parent", "child", "worker", "retiree", "lady"]
        for i in range(4):
            x = 700 + i * 110 + (t * 40) % 60
            look = variant(resolve(pool[i % len(pool)], accent, outfit), i * 11 + 9)
            figure(cr, x, G - 60, walk_pose(t * 6 + i, 18), scale=0.5, t=t, look=look, face="worried")
    elif kind == "helicopter":
        night = spec.get("night", False)
        if night:
            night_sky(cr, t, 41)
        else:
            dawn_sky(cr, 150, 880)
        cr.set_source_rgb(0.18, 0.2, 0.18); cr.rectangle(0, 880, W, H); cr.fill()
        plant_building(cr, 1000, 880, 0.9, lit=False, broken=1)
        smoke_plume(cr, 1250, 560, t, (0.45, 0.45, 0.5), 12, 360)
        hx_ = _mix(-300, 1250, min(1, t / 3.2))
        hy_ = 300 + math.sin(t * 2) * 10
        helicopter(cr, hx_, hy_, t, 0.8)
        if t > 3.2:
            for i in range(4):
                ph = ((t - 3.2) * 1.2 + i / 4) % 1
                cr.rectangle(hx_ - 14, hy_ + 50 + ph * 260, 28, 22); cr.set_source_rgba(0.7, 0.58, 0.38, 1 - ph * 0.6); cr.fill()
    else:
        figure(cr, 960, G, POSES["stand"], **kw)
