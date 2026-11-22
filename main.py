#!/usr/bin/env python3
"""The picture that tastes of one ingredient.

A program that paints one picture of food from scratch: a tall stack of
golden pancakes with a glossy honey pool and drips, a melting butter pat,
fresh blueberries and mint, steam rising, on a cream plate over a warm
wooden table in morning light. No text, no external images, no network.

Pure standard library: the rasterizer and the PNG writer (zlib) are both
hand-written here. Deterministic: the same run always paints the same
picture. Writes /output/entry.png (or $OUTPUT_DIR/entry.png).
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
OUT_DIR = os.environ.get("OUTPUT_DIR", "/output")

RNG = random.Random(20261123)

# ---------------------------------------------------------------- canvas

class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.rows = [bytearray(w * 3) for _ in range(h)]

    def set_px(self, x, y, r, g, b):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = x * 3
            row = self.rows[y]
            row[i] = r
            row[i + 1] = g
            row[i + 2] = b

    def blend_px(self, x, y, r, g, b, a):
        """Alpha-blend one pixel; a in 0..1."""
        if 0 <= x < self.w and 0 <= y < self.h and a > 0.0:
            i = x * 3
            row = self.rows[y]
            ia = 1.0 - a
            row[i] = int(row[i] * ia + r * a)
            row[i + 1] = int(row[i + 1] * ia + g * a)
            row[i + 2] = int(row[i + 2] * ia + b * a)

    def fill_rect(self, x0, y0, x1, y1, color):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        if x1 <= x0 or y1 <= y0:
            return
        px = bytes(color) * (x1 - x0)
        for y in range(y0, y1):
            self.rows[y][x0 * 3:x1 * 3] = px

    def vgrad_rect(self, x0, y0, x1, y1, top, bottom):
        """Vertical gradient rectangle."""
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        span = max(1, y1 - y0)
        for y in range(y0, y1):
            t = (y - y0) / span
            c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            self.rows[y][x0 * 3:x1 * 3] = bytes(c) * (x1 - x0)

    def fill_ellipse(self, cx, cy, rx, ry, color):
        self.fill_ellipse_grad(cx, cy, rx, ry, color, color)

    def fill_ellipse_grad(self, cx, cy, rx, ry, top, bottom):
        """Filled ellipse with a vertical colour gradient."""
        if rx <= 0 or ry <= 0:
            return
        y0 = max(0, int(cy - ry))
        y1 = min(self.h - 1, int(cy + ry) + 1)
        for y in range(y0, y1 + 1):
            dy = (y - cy) / ry
            if abs(dy) > 1.0:
                continue
            dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            x0 = max(0, int(cx - dx))
            x1 = min(self.w - 1, int(cx + dx))
            if x1 < x0:
                continue
            t = (y - (cy - ry)) / (2.0 * ry)
            t = max(0.0, min(1.0, t))
            c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            self.rows[y][x0 * 3:(x1 + 1) * 3] = bytes(c) * (x1 - x0 + 1)

    def ellipse_ring(self, cx, cy, rx, ry, color, thick):
        """Thin ring around an ellipse (drawn as two ellipses)."""
        for k in range(thick):
            self._ellipse_outline(cx, cy, rx - k, ry - k, color)

    def _ellipse_outline(self, cx, cy, rx, ry, color):
        if rx <= 0 or ry <= 0:
            return
        steps = int(2 * math.pi * max(rx, ry))
        steps = max(64, min(3000, steps))
        for i in range(steps):
            a = 2 * math.pi * i / steps
            x = int(cx + rx * math.cos(a))
            y = int(cy + ry * math.sin(a))
            self.set_px(x, y, *color)

    def fill_poly(self, pts, color):
        """Scanline polygon fill."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys)))
        y1 = min(self.h - 1, int(max(ys)))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, y1p = pts[i]
                x2, y2p = pts[(i + 1) % n]
                if (y1p <= y < y2p) or (y2p <= y < y1p):
                    if y2p != y1p:
                        x = x1 + (y - y1p) * (x2 - x1) / (y2p - y1p)
                        xs.append(x)
            if len(xs) < 2:
                continue
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                xa = max(0, int(xs[j]))
                xb = min(self.w - 1, int(xs[j + 1]))
                if xb >= xa:
                    self.rows[y][xa * 3:(xb + 1) * 3] = bytes(color) * (xb - xa + 1)

    def dab(self, cx, cy, r, color, alpha=1.0):
        """Soft round dab with a falloff edge."""
        if r <= 0:
            return
        r = int(r)
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            for x in range(cx - r, cx + r + 1):
                dx = x - cx
                d = math.sqrt(dx * dx + dy * dy)
                if d <= r:
                    a = alpha * (1.0 - (d / r) ** 2)
                    a = min(1.0, a * 1.6)
                    self.blend_px(x, y, *color, a)

    def line(self, x0, y0, x1, y1, color, width=1, alpha=1.0):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(steps + 1):
            t = i / steps
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            for wy in range(-(width // 2), width // 2 + 1):
                for wx in range(-(width // 2), width // 2 + 1):
                    self.blend_px(x + wx, y + wy, *color, alpha)


def lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# ---------------------------------------------------------------- picture

def paint():
    cv = Canvas(W, H)

    # --- wall: warm morning gradient, cream to soft peach
    cv.vgrad_rect(0, 0, W, 560, (250, 232, 205), (244, 214, 176))

    # --- soft window light: a pale glow upper left (a few mid-size dabs;
    # large-radius dabs are far too slow in pure Python)
    for r in (140, 110, 80, 55, 35):
        cv.dab(300, 130, r, (255, 246, 220), 0.10)

    # --- wooden table from y=560 down, warm planks
    cv.vgrad_rect(0, 560, W, H, (176, 124, 78), (146, 98, 58))
    for plank_y in (560, 668, 776, 884, 992):
        cv.fill_rect(0, plank_y, W, plank_y + 3, (120, 78, 44))
    # wood grain: gentle wavy darker streaks
    for _ in range(26):
        gy = RNG.randint(575, 1010)
        gx = RNG.randint(-40, 900)
        length = RNG.randint(120, 320)
        amp = RNG.randint(2, 6)
        col = (128, 84, 48) if RNG.random() < 0.5 else (198, 148, 96)
        prev = None
        for s in range(0, length, 8):
            x = gx + s
            y = gy + int(amp * math.sin(s / 46.0 + gy))
            if prev is not None:
                cv.line(prev[0], prev[1], x, y, col, width=2, alpha=0.35)
            prev = (x, y)
    # light pooling on the table in front of the plate (subtle)

    # --- plate shadow on the table
    cv.fill_ellipse(512, 700, 400, 108, (110, 70, 38))
    for r in range(0, 0):  # (kept simple: solid soft shadow via dabs)
        pass
    cv.dab(512, 700, 330, (110, 70, 38), 0.18)

    # --- cream plate
    cv.fill_ellipse_grad(512, 660, 392, 128, (252, 244, 228), (232, 218, 196))
    cv.fill_ellipse_grad(512, 652, 392, 122, (250, 242, 226), (238, 226, 206))
    # plate rim
    cv.ellipse_ring(512, 652, 352, 106, (206, 190, 164), 3)
    cv.ellipse_ring(512, 652, 300, 88, (222, 208, 184), 2)
    # plate highlight, upper left
    cv.dab(360, 600, 130, (255, 252, 244), 0.35)

    # --- pancake stack: four golden slabs, bottom to top
    pancakes = [
        # (cx, cy, rx, ry, top colour, side colour)
        (512, 640, 268, 62, (226, 164, 74), (176, 112, 40)),
        (512, 590, 252, 58, (232, 172, 82), (182, 118, 44)),
        (512, 542, 232, 54, (238, 180, 90), (188, 124, 48)),
        (512, 496, 208, 50, (244, 190, 100), (194, 130, 52)),
    ]
    for cx, cy, rx, ry, top, side in pancakes:
        # side / lower edge: darker, slightly lower and wider
        cv.fill_ellipse_grad(cx, cy + 10, rx, ry, side, (150, 92, 30))
        # top surface
        cv.fill_ellipse_grad(cx, cy - 4, rx, ry - 6, top, lerp(top, side, 0.45))
        # golden-brown toasted speckles on the top
        for _ in range(46):
            ang = RNG.uniform(0, 2 * math.pi)
            rr = math.sqrt(RNG.random())
            sx = int(cx + math.cos(ang) * rr * (rx - 14))
            sy = int(cy - 4 + math.sin(ang) * rr * (ry - 12))
            rad = RNG.randint(2, 6)
            col = (196, 128, 48) if RNG.random() < 0.6 else (248, 205, 120)
            cv.dab(sx, sy, rad, col, RNG.uniform(0.25, 0.55))
        # crisp edge highlight along the upper rim
        cv.ellipse_ring(cx, cy - 4, rx - 2, ry - 8, (250, 205, 120), 2)

    # --- honey pool on the top pancake
    cv.fill_ellipse_grad(512, 470, 150, 30, (246, 178, 52), (214, 128, 22))
    cv.fill_ellipse_grad(512, 466, 132, 24, (252, 190, 66), (226, 146, 30))
    # glossy highlight on the honey pool
    cv.dab(470, 458, 46, (255, 222, 130), 0.55)
    cv.dab(540, 476, 26, (255, 214, 110), 0.4)

    # --- honey drips running down the front of the stack
    drips = [
        (392, 500, 12, 150), (448, 505, 15, 205), (512, 505, 13, 120),
        (580, 505, 16, 225), (636, 500, 11, 165),
    ]
    for dx, dy, dr, length in drips:
        cv.fill_rect(dx - dr, dy, dx + dr, dy + length, (232, 152, 34))
        cv.fill_ellipse(dx, dy + length, dr + 2, dr + 6, (222, 140, 28))
        cv.line(dx - dr // 2, dy + 8, dx - dr // 2, dy + length - 10,
                (255, 205, 100), width=3, alpha=0.6)
    # honey puddle on the plate, front right
    cv.fill_ellipse_grad(640, 690, 92, 22, (240, 170, 44), (210, 124, 20))
    cv.dab(620, 684, 30, (255, 214, 110), 0.5)

    # --- melting butter pat on top, tilted
    butter = [(468, 440), (556, 432), (566, 470), (478, 478)]
    cv.fill_poly(butter, (252, 214, 92))
    cv.fill_poly([(478, 448), (548, 442), (554, 462), (486, 468)],
                 (255, 230, 130))
    # butter gloss + a melting drip down its side
    cv.dab(500, 446, 22, (255, 244, 170), 0.6)
    cv.fill_ellipse(560, 482, 10, 16, (250, 208, 84))
    cv.dab(560, 490, 9, (255, 230, 130), 0.5)

    # --- blueberries: plump, dark, with bloom and a bright specular dot
    def blueberry(cx, cy, r):
        cv.fill_ellipse_grad(cx, cy, r, r, (72, 78, 150), (34, 36, 84))
        cv.dab(cx - int(r * 0.35), cy - int(r * 0.35), int(r * 0.55),
               (110, 120, 190), 0.55)
        cv.dab(cx - int(r * 0.3), cy - int(r * 0.3), int(r * 0.18),
               (225, 230, 255), 0.9)
        # star scar on top
        cv.dab(cx + int(r * 0.25), cy - int(r * 0.45), int(r * 0.22),
               (52, 54, 110), 0.8)

    berries = [
        (352, 622, 34), (300, 648, 28), (392, 664, 30),
        (668, 636, 32), (716, 664, 26), (622, 668, 24),
        (596, 478, 22), (428, 470, 20),
    ]
    for bx, by, br in berries:
        # soft contact shadow under each berry
        cv.fill_ellipse(bx, by + br - 2, br + 4, int(br * 0.35), (120, 84, 40))
        blueberry(bx, by, br)

    # --- mint leaves: fresh green, veined, beside the berries
    def mint_leaf(cx, cy, length, angle_deg, tilt=0):
        a = math.radians(angle_deg)
        dx, dy = math.cos(a), math.sin(a)
        px, py = -dy, dx  # perpendicular
        tip = (cx + dx * length, cy + dy * length)
        base = (cx - dx * length * 0.25, cy - dy * length * 0.25)
        wdt = length * 0.34
        left = (cx + px * wdt, cy + py * wdt)
        right = (cx - px * wdt, cy - py * wdt)
        cv.fill_poly([base, left, tip, right], (58, 138, 74))
        cv.fill_poly([(base[0] + dx * 6, base[1] + dy * 6),
                      (cx + px * wdt * 0.45, cy + py * wdt * 0.45),
                      tip,
                      (cx - px * wdt * 0.45, cy - py * wdt * 0.45)],
                     (86, 176, 96))
        cv.line(base[0], base[1], tip[0], tip[1], (34, 96, 52),
                width=2, alpha=0.7)

    mint_leaf(330, 700, 52, -160)
    mint_leaf(700, 700, 48, -20)
    mint_leaf(600, 452, 40, -55)
    mint_leaf(438, 452, 36, -125)

    # --- steam: soft translucent ribbons rising above the stack
    for sx, phase, amp, height in ((470, 0.0, 16, 150),
                                   (512, 1.4, 20, 185),
                                   (556, 2.6, 15, 150)):
        for step in range(0, height, 6):
            t = step / height
            x = int(sx + amp * math.sin(phase + t * 5.0) * (0.4 + t))
            y = 430 - step
            rad = int(10 + t * 26)
            cv.dab(x, y, rad, (255, 250, 240), 0.10 * (1.0 - t * 0.55))

    # --- warm light wash over the whole scene, upper left
    for r in (170, 130, 90, 55):
        cv.dab(280, 120, r, (255, 240, 200), 0.05)

    return cv


# ---------------------------------------------------------------- PNG out

def write_png(cv, path):
    raw = bytearray()
    prev = bytearray(W * 3)
    for y in range(H):
        row = cv.rows[y]
        raw.append(2)  # filter: Up
        for i in range(W * 3):
            raw.append((row[i] - prev[i]) & 0xFF)
        prev = row
    comp = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = bytearray()
    png += b"\x89PNG\r\n\x1a\n"
    for tag, data in ((b"IHDR", ihdr), (b"IDAT", comp), (b"IEND", b"")):
        png += struct.pack(">I", len(data)) + tag + data
        png += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)  # create only; never remove /output
    cv = paint()
    size = write_png(cv, os.path.join(OUT_DIR, "entry.png"))
    print(f"Wrote {os.path.join(OUT_DIR, 'entry.png')} ({W}x{H}, {size} bytes)")


if __name__ == "__main__":
    main()
