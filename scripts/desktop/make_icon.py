#!/usr/bin/env python3
"""Generate the desktop app icon — `appicon.icns` — from the app's own visual language.

Deep-space squircle (the app's `#0a0812` background + starfield) with the signature top-accent
sweep in rose → purple → teal (v4 `topAccent`). Not sacred: drop your own 1024×1024 PNG at
`scripts/desktop/icon_source.png` and re-run — that image is used verbatim as the master instead.

Run:  .venv-desktop/bin/python scripts/desktop/make_icon.py
Output: scripts/desktop/appicon.icns  (+ icon_master.png to eyeball)
"""
import os
import math
import subprocess

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_OVERRIDE = os.path.join(HERE, "icon_source.png")
MASTER = os.path.join(HERE, "icon_master.png")
ICNS = os.path.join(HERE, "appicon.icns")

S = 1024
BG_TOP = (21, 16, 51)     # deep indigo — lifts the icon off a dark dock
BG_BOT = (7, 6, 15)       # near-black, the app's ground
ROSE = (242, 166, 200)
PURPLE = (213, 143, 216)
TEAL = (95, 198, 214)


def _lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _accent(t):
    """rose → purple → teal across t in [0,1] — the app's top-accent gradient."""
    return _lerp(ROSE, PURPLE, t * 2) if t < 0.5 else _lerp(PURPLE, TEAL, (t - 0.5) * 2)


def _squircle_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def _draw_master():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # ── the squircle body — macOS icon grid: ~824px art centred in 1024, ~0.2237 corner ──
    pad = 100
    body_size = S - 2 * pad          # 824
    radius = round(body_size * 0.2237)
    body = Image.new("RGBA", (body_size, body_size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    for y in range(body_size):       # vertical gradient
        t = y / (body_size - 1)
        bd.line([(0, y), (body_size, y)], fill=_lerp(BG_TOP, BG_BOT, t) + (255,))

    # faint starfield (the app's theme), brighter near the top
    rnd = _Rng(20260718)
    stars = Image.new("RGBA", (body_size, body_size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stars)
    for _ in range(90):
        x, y = rnd.rand() * body_size, rnd.rand() * body_size
        r = 1.2 + rnd.rand() * 1.8
        a = int(40 + rnd.rand() * 90 * (1 - y / body_size))
        sd.ellipse([x - r, y - r, x + r, y + r], fill=(220, 225, 255, a))
    body.alpha_composite(stars)

    # ── the accent sweep — a thick rounded gradient stroke along a shallow arc ──
    glow = Image.new("RGBA", (body_size, body_size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    stroke = Image.new("RGBA", (body_size, body_size), (0, 0, 0, 0))
    st = ImageDraw.Draw(stroke)
    # arc from lower-left to upper-right, bowed gently upward
    x0, y0 = body_size * 0.20, body_size * 0.66
    x1, y1 = body_size * 0.80, body_size * 0.40
    bow = -body_size * 0.14
    w = body_size * 0.085   # stroke half-width
    steps = 260
    for i in range(steps + 1):
        t = i / steps
        # quadratic bezier via a lifted midpoint control
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + bow
        px = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        py = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        col = _accent(t)
        st.ellipse([px - w, py - w, px + w, py + w], fill=col + (255,))
        gd.ellipse([px - w, py - w, px + w, py + w], fill=col + (120,))
    glow = glow.filter(ImageFilter.GaussianBlur(38))
    body.alpha_composite(glow)
    body.alpha_composite(stroke)

    # a single bright accent star at the sweep's leading end
    lead = ImageDraw.Draw(body)
    lx, ly = body_size * 0.80, body_size * 0.40
    lead.ellipse([lx - 10, ly - 10, lx + 10, ly + 10], fill=(255, 255, 255, 235))

    # top inner highlight — the glassy macOS sheen
    sheen = Image.new("RGBA", (body_size, body_size), (0, 0, 0, 0))
    ImageDraw.Draw(sheen).rounded_rectangle(
        [6, 6, body_size - 6, body_size - 6], radius=radius, outline=(255, 255, 255, 30), width=3
    )
    body.alpha_composite(sheen)

    body.putalpha(_squircle_mask(body_size, radius))

    # soft ambient drop shadow so it sits on any dock
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sm = _squircle_mask(body_size, radius)
    shpad = Image.new("L", (S, S), 0)
    shpad.paste(sm, (pad, pad + 12))
    shadow.putalpha(shpad.filter(ImageFilter.GaussianBlur(24)))
    img.alpha_composite(shadow)
    img.alpha_composite(body, (pad, pad))
    return img


class _Rng:
    """Tiny deterministic PRNG — no Math.random-style nondeterminism in the build."""
    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFF

    def rand(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s / 0x7FFFFFFF


def main():
    if os.path.exists(SRC_OVERRIDE):
        master = Image.open(SRC_OVERRIDE).convert("RGBA").resize((S, S), Image.LANCZOS)
        print(f"[icon] using your override: {SRC_OVERRIDE}")
    else:
        master = _draw_master()
        print("[icon] generated the default deep-space icon")
    master.save(MASTER)

    iconset = os.path.join(HERE, "AppIcon.iconset")
    os.makedirs(iconset, exist_ok=True)
    specs = [(16, 1), (16, 2), (32, 1), (32, 2), (128, 1), (128, 2),
             (256, 1), (256, 2), (512, 1), (512, 2)]
    for base, scale in specs:
        px = base * scale
        name = f"icon_{base}x{base}{'@2x' if scale == 2 else ''}.png"
        master.resize((px, px), Image.LANCZOS).save(os.path.join(iconset, name))
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", ICNS], check=True)
    print(f"[icon] wrote {ICNS}")


if __name__ == "__main__":
    main()
