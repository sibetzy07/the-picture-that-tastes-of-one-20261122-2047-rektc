#!/usr/bin/env python3
"""The picture that tastes of one ingredient.

A tall stack of golden pancakes with a glossy honey pool and drips, a
melting butter pat, fresh blueberries and mint leaves, on a cream plate
over a warm wooden table in morning light.

Pure Python 3.13 standard library: a small scanline rasterizer draws
into a byte buffer and a zlib PNG encoder writes /output/entry.png.
No network, no external assets, fully deterministic (one seeded RNG).
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
OUT = os.environ.get("ENTRY_OUT", "/output/entry.png")

rng = random.Random(20261123)


# ---------------------------------------------------------------- canvas

class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)

    def _row(self, y):
        return y * self.w * 3

    def set_px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._row(y) + x * 3
            self.buf[i] = color[0]
            self.buf[i + 1] = color[1]
            self.buf[i + 2] = color[2]

    def blend_px(self, x, y, color, alpha):
        """Alpha-blend one pixel (alpha 0..1)."""
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._row(y) + x * 3
            b = self.buf
            b[i] = int(b[i] + (color[0] - b[i]) * alpha)
            b[i + 1] = int(b[i + 1] + (color[1] - b[i + 1]) * alpha)
            b[i + 2] = int(b[i + 2] + (color[2] - b[i + 2]) * alpha)

    def hline(self, x0, x1, y, color):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0:
            return
        i = self._row(y) + x0 * 3
        n = x1 - x0 + 1
        self.buf[i:i + n * 3] = bytes(color) * n

    def hline_alpha(self, x0, x1, y, color, alpha):
        if y < 0 or y >= self.h or alpha <= 0:
            return
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        for x in range(x0, x1 + 1):
            self.blend_px(x, y, color, alpha)

    def vgrad(self, y0, y1, top, bottom):
        """Vertical linear gradient over rows y0..y1."""
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            t = (y - y0) / max(1, y1 - y0)
            c = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
            self.hline(0, self.w - 1, y, c)

    def ellipse(self, cx, cy, rx, ry, color):
        """Filled ellipse, scanline based."""
        if rx <= 0 or ry <= 0:
            return
        for dy in range(-ry, ry + 1):
            y = cy + dy
            if y < 0 or y >= self.h:
                continue
            f = 1.0 - (dy * dy) / float(ry * ry)
            if f < 0:
                continue
            dx = int(rx * math.sqrt(f))
            self.hline(cx - dx, cx + dx, y, color)

    def ellipse_alpha(self, cx, cy, rx, ry, color, alpha):
        if rx <= 0 or ry <= 0:
            return
        for dy in range(-ry, ry + 1):
            y = cy + dy
            if y < 0 or y >= self.h:
                continue
            f = 1.0 - (dy * dy) / float(ry * ry)
            if f < 0:
                continue
            dx = int(rx * math.sqrt(f))
            self.hline_alpha(cx - dx, cx + dx, y, color, alpha)

    def disc(self, cx, cy, r, color):
        self.ellipse(cx, cy, r, r, color)

    def disc_alpha(self, cx, cy, r, color, alpha):
        self.ellipse_alpha(cx, cy, r, r, color, alpha)

    def rect(self, x0, y0, x1, y1, color):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            self.hline(x0, x1, y, color)

    def thick_line(self, x0, y0, x1, y1, r, color):
        """A thick line drawn as discs along the segment."""
        steps = int(math.hypot(x1 - x0, y1 - y0)) + 1
        for s in range(steps + 1):
            t = s / max(1, steps)
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            self.disc(x, y, r, color)

    def poly(self, pts, color):
        """Filled polygon via scanline intersection."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h - 1, max(ys)) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / float(y1 - y0)
                    xs.append(x0 + (x1 - x0) * t)
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                self.hline(int(xs[j]), int(xs[j + 1]), y, color)


def lerp(a, b, t):
    return tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))


# ---------------------------------------------------------------- scene

def draw_background(c):
    c.vgrad(0, 640, (255, 243, 214), (246, 214, 163))
    # morning light glow, upper left — kept faint so no disc edge shows
    c.ellipse_alpha(300, 180, 520, 380, (255, 252, 235), 0.20)
    c.ellipse_alpha(300, 180, 320, 230, (255, 253, 240), 0.14)
    # soft warm glow lower right, balancing the light
    c.ellipse_alpha(820, 420, 380, 280, (250, 205, 140), 0.08)


def draw_table(c):
    c.vgrad(640, H - 1, (186, 128, 74), (138, 90, 48))
    # plank seams
    for y in (712, 830, 948):
        c.hline_alpha(0, W - 1, y, (96, 60, 30), 0.35)
        c.hline_alpha(0, W - 1, y + 2, (214, 158, 100), 0.25)
    # wood grain streaks
    for _ in range(26):
        y = rng.randint(660, 1000)
        x0 = rng.randint(0, 500)
        ln = rng.randint(120, 420)
        c.hline_alpha(x0, x0 + ln, y, (110, 70, 36), rng.uniform(0.06, 0.16))
    # light pool on the table under the plate
    c.ellipse_alpha(512, 830, 430, 130, (255, 220, 160), 0.10)


def draw_plate(c):
    # soft shadow under the plate
    c.ellipse_alpha(512, 872, 372, 62, (70, 40, 18), 0.28)
    c.ellipse_alpha(512, 862, 350, 54, (70, 40, 18), 0.20)
    # plate body: rim, then inner dish
    c.ellipse(512, 800, 372, 138, (232, 216, 188))
    c.ellipse(512, 796, 356, 128, (253, 248, 236))
    c.ellipse(512, 792, 322, 112, (250, 244, 228))
    # thin rim ring highlight
    for dy in range(-6, 7):
        y = 800 + dy
        f = 1.0 - (dy * dy) / 49.0
        if f <= 0:
            continue
        dx = int(340 * math.sqrt(f))
        c.set_px(512 - dx, y, (255, 252, 244))
        c.set_px(512 + dx, y, (255, 252, 244))


def pancake(c, cx, cy, rw, rh, top, side, speck):
    """One pancake: golden side band + toasted top with speckles."""
    # side band
    c.rect(cx - rw, cy, cx + rw, cy + rh, side)
    # rounded lower edge of the side
    c.ellipse(cx, cy + rh, rw, 14, side)
    # dark separation line where this pancake meets the one below it,
    # so the four layers read as a stack instead of one flat cake
    c.ellipse_alpha(cx, cy + rh - 2, rw, 7, (110, 62, 16), 0.55)
    # top surface: toasted rim ring, then the pale golden middle
    c.ellipse(cx, cy, rw, 30, (196, 128, 44))
    c.ellipse(cx, cy, rw - 14, 26, top)
    # toasted speckles on the top
    for _ in range(46):
        a = rng.uniform(0, 2 * math.pi)
        rr = math.sqrt(rng.random())
        x = int(cx + math.cos(a) * rw * 0.86 * rr)
        y = int(cy + math.sin(a) * 26 * rr)
        r = rng.randint(2, 6)
        shade = rng.random()
        col = lerp(top, speck, 0.35 + 0.55 * shade)
        c.disc(x, y, r, col)
    # a few pale golden highlights
    for _ in range(10):
        a = rng.uniform(0, 2 * math.pi)
        rr = math.sqrt(rng.random())
        x = int(cx + math.cos(a) * rw * 0.7 * rr)
        y = int(cy + math.sin(a) * 22 * rr)
        c.disc(x, y, rng.randint(2, 4), (246, 205, 120))
    # bottom shadow line where it meets the pancake below
    c.ellipse_alpha(cx, cy + rh + 8, rw - 6, 8, (120, 70, 20), 0.25)


def draw_stack(c):
    gold_top = (238, 178, 84)
    gold_side = (208, 144, 58)
    toast = (150, 94, 28)
    layers = [
        (516, 700, 268, 52),
        (506, 648, 276, 52),
        (518, 596, 270, 52),
        (510, 544, 258, 52),
    ]
    for cx, cy, rw, rh in layers:
        pancake(c, cx, cy, rw, rh, gold_top, gold_side, toast)
    return layers


def draw_honey(c):
    honey = (206, 128, 14)
    honey_deep = (176, 106, 12)
    honey_light = (246, 196, 90)
    # glossy pool on the top pancake — wide and deep amber so it reads wet
    c.ellipse(510, 538, 226, 40, honey_deep)
    c.ellipse(510, 536, 210, 34, honey)
    c.ellipse(500, 532, 172, 24, honey_light)
    c.ellipse(505, 536, 142, 18, honey)
    # bright wet highlight on the pool
    c.ellipse_alpha(462, 526, 96, 11, (255, 228, 150), 0.85)
    c.ellipse_alpha(566, 542, 64, 8, (255, 228, 150), 0.55)
    # drips running down the stack
    drips = [
        (330, 540, 560, 14),
        (700, 540, 600, 16),
        (636, 544, 700, 12),
        (420, 542, 640, 11),
    ]
    for x, y0, y1, r in drips:
        c.thick_line(x, y0, x + rng.randint(-8, 8), y1, r, honey)
        c.disc(x, y1, r + 2, honey)
        c.thick_line(x - 3, y0 + 6, x - 3, y1 - 8, 3, honey_light)
    # honey droplets on the plate
    for x, y, r in [(820, 830, 12), (848, 842, 8), (210, 848, 9)]:
        c.disc(x, y, r, honey)
        c.disc(x - 3, y - 3, max(2, r // 3), honey_light)


def draw_butter(c):
    # melting butter pat, tilted, on the honey pool
    cx, cy = 520, 512
    ang = -0.14
    hw, hh = 62, 26
    corners = []
    for sx, sy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
        x = cx + sx * math.cos(ang) - sy * math.sin(ang)
        y = cy + sx * math.sin(ang) + sy * math.cos(ang)
        corners.append((int(x), int(y)))
    # soft melt halo under the pat
    c.ellipse_alpha(cx, cy + 16, 74, 18, (255, 232, 150), 0.45)
    # side face, slightly darker and shifted down, so the pat has body
    side = []
    for sx, sy in ((-hw, -hh + 12), (hw, -hh + 12), (hw, hh + 8), (-hw, hh + 8)):
        x = cx + sx * math.cos(ang) - sy * math.sin(ang)
        y = cy + sx * math.sin(ang) + sy * math.cos(ang)
        side.append((int(x), int(y)))
    c.poly(side, (240, 196, 84))
    c.poly(corners, (255, 216, 96))
    # top face highlight and edge
    top = []
    for sx, sy in ((-hw + 6, -hh + 4), (hw - 6, -hh + 4), (hw - 10, -hh + 16), (-hw + 10, -hh + 16)):
        x = cx + sx * math.cos(ang) - sy * math.sin(ang)
        y = cy + sx * math.sin(ang) + sy * math.cos(ang)
        top.append((int(x), int(y)))
    c.poly(top, (255, 240, 170))
    c.ellipse_alpha(cx - 12, cy - 8, 34, 7, (255, 250, 210), 0.6)


def draw_blueberry(c, cx, cy, r):
    deep = (38, 38, 110)
    mid = (62, 62, 150)
    light = (96, 96, 190)
    c.disc(cx, cy, r, deep)
    c.disc(cx - r // 4, cy - r // 4, int(r * 0.72), mid)
    # crown star
    for k in range(5):
        a = -math.pi / 2 + k * 2 * math.pi / 5
        x1 = int(cx + math.cos(a) * r * 0.28)
        y1 = int(cy + math.sin(a) * r * 0.28)
        x2 = int(cx + math.cos(a + 0.5) * r * 0.12)
        y2 = int(cy + math.sin(a + 0.5) * r * 0.12)
        c.thick_line(x1, y1, x2, y2, 2, (24, 24, 70))
    c.disc(cx, cy, max(2, r // 5), (24, 24, 70))
    # specular shine
    c.disc_alpha(cx - int(r * 0.38), cy - int(r * 0.42), max(2, r // 4), (220, 225, 255), 0.9)
    c.disc_alpha(cx - int(r * 0.15), cy - int(r * 0.5), max(1, r // 8), (240, 240, 255), 0.8)


def draw_mint_leaf(c, cx, cy, ang, size):
    leaf = (52, 130, 62)
    dark = (34, 96, 44)
    pts = []
    for t in range(0, 13):
        f = t / 12.0
        # leaf outline: pointed at both ends, wide in the middle
        wdt = math.sin(f * math.pi) * size * 0.42
        along = (f - 0.5) * size
        px = cx + along * math.cos(ang)
        py = cy + along * math.sin(ang)
        nx = -math.sin(ang)
        ny = math.cos(ang)
        pts.append((int(px + nx * wdt), int(py + ny * wdt)))
    for t in range(12, -1, -1):
        f = t / 12.0
        wdt = math.sin(f * math.pi) * size * 0.42
        along = (f - 0.5) * size
        px = cx + along * math.cos(ang)
        py = cy + along * math.sin(ang)
        nx = -math.sin(ang)
        ny = math.cos(ang)
        pts.append((int(px - nx * wdt), int(py - ny * wdt)))
    c.poly(pts, leaf)
    # centre vein
    x0 = int(cx - math.cos(ang) * size * 0.42)
    y0 = int(cy - math.sin(ang) * size * 0.42)
    x1 = int(cx + math.cos(ang) * size * 0.42)
    y1 = int(cy + math.sin(ang) * size * 0.42)
    c.thick_line(x0, y0, x1, y1, 2, dark)


def draw_garnish(c):
    # blueberries on top of the stack
    draw_blueberry(c, 420, 516, 26)
    draw_blueberry(c, 620, 520, 24)
    draw_blueberry(c, 590, 500, 18)
    # blueberries resting on the plate
    draw_blueberry(c, 300, 812, 24)
    draw_blueberry(c, 740, 818, 22)
    draw_blueberry(c, 770, 800, 15)
    # mint leaves
    draw_mint_leaf(c, 660, 512, -0.5, 64)
    draw_mint_leaf(c, 380, 528, 0.4, 56)
    draw_mint_leaf(c, 330, 788, 0.9, 52)


def draw_steam(c):
    # three curling wisps above the hot stack
    for base_x, phase, height in ((430, 0.0, 150), (512, 2.1, 185), (600, 4.2, 160)):
        y = 470
        step = 0
        while y > 470 - height:
            t = step / 12.0
            x = int(base_x + math.sin(t * 1.6 + phase) * (10 + step * 0.35))
            r = max(4, int(7 + step * 0.55))
            alpha = max(0.05, 0.20 - step * 0.008)
            c.disc_alpha(x, y, r, (255, 252, 245), alpha)
            y -= 9
            step += 1


def draw_vignette(c):
    c.ellipse_alpha(0, 0, 260, 200, (120, 70, 20), 0.04)
    c.ellipse_alpha(W, 0, 260, 200, (120, 70, 20), 0.04)
    c.ellipse_alpha(0, H, 300, 220, (90, 50, 15), 0.04)
    c.ellipse_alpha(W, H, 300, 220, (90, 50, 15), 0.04)


# ---------------------------------------------------------------- png

def write_png(c, path):
    raw = bytearray()
    prev = bytes(W * 3)
    for y in range(H):
        row = bytes(c.buf[y * W * 3:(y + 1) * W * 3])
        # Up filter: store deltas against the previous row
        filt = bytes((row[i] - prev[i]) & 0xFF for i in range(len(row)))
        raw.append(2)
        raw.extend(filt)
        prev = row
    data = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)

    def chunk(kind, payload):
        out = struct.pack(">I", len(payload)) + kind + payload
        out += struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        return out

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", data)
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    c = Canvas(W, H)
    draw_background(c)
    draw_table(c)
    draw_plate(c)
    draw_stack(c)
    draw_honey(c)
    draw_butter(c)
    draw_garnish(c)
    draw_steam(c)
    draw_vignette(c)
    size = write_png(c, OUT)
    print(f"wrote {OUT} {W}x{H} {size} bytes")


if __name__ == "__main__":
    main()
