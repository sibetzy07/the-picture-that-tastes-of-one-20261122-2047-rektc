#!/usr/bin/env python3
"""The picture that tastes of one ingredient.

A program that paints, from scratch, one picture of food: a tall stack of
golden pancakes with melting butter, warm honey dripping down the sides,
fresh blueberries and a mint leaf, on a cream plate in warm morning light.

Everything is drawn procedurally with the Python standard library only:
a small software rasterizer (ellipses, gradients, speckles, soft steam)
writes RGB pixels into a framebuffer, which is encoded as a PNG with
zlib. No network, no external files, no copied assets, fully deterministic.
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
OUT = os.environ.get("ENTRY_OUTPUT", "/output/entry.png")

RNG = random.Random(20261123)

# ---------------------------------------------------------------- framebuffer
buf = bytearray(W * H * 3)


def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


def px(x, y):
    return (y * W + x) * 3


def blend(x, y, r, g, b, a):
    """Blend colour (r,g,b) over pixel (x,y) with alpha a in [0,1]."""
    if x < 0 or x >= W or y < 0 or y >= H or a <= 0:
        return
    i = px(x, y)
    ia = 1.0 - a
    buf[i] = clamp(int(buf[i] * ia + r * a))
    buf[i + 1] = clamp(int(buf[i + 1] * ia + g * a))
    buf[i + 2] = clamp(int(buf[i + 2] * ia + b * a))


def set_px(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = px(x, y)
        buf[i] = clamp(int(r))
        buf[i + 1] = clamp(int(g))
        buf[i + 2] = clamp(int(b))


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_col(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


# ---------------------------------------------------------------- primitives
def fill_rect(x0, y0, x1, y1, col, alpha=1.0):
    for y in range(max(0, y0), min(H, y1)):
        for x in range(max(0, x0), min(W, x1)):
            blend(x, y, col[0], col[1], col[2], alpha)


def ellipse(cx, cy, rx, ry, col_top, col_bottom=None, alpha=1.0,
            edge_dark=None, squash=1.0):
    """Filled ellipse; vertical gradient top->bottom, optional darker rim."""
    if col_bottom is None:
        col_bottom = col_top
    y0 = max(0, int(cy - ry))
    y1 = min(H, int(cy + ry) + 1)
    for y in range(y0, y1):
        dy = (y - cy) / ry
        if abs(dy) > 1:
            continue
        half = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
        x0 = int(cx - half)
        x1 = int(cx + half)
        t = (y - (cy - ry)) / (2.0 * ry)
        col = lerp_col(col_top, col_bottom, t)
        # rim darkening near the horizontal edge
        for x in range(max(0, x0), min(W, x1 + 1)):
            nx = abs((x - cx) / max(1.0, half)) if half > 0 else 0.0
            r, g, b = col
            if edge_dark is not None and nx > 0.82:
                f = (nx - 0.82) / 0.18
                r, g, b = lerp_col((r, g, b), edge_dark, f * 0.85)
            blend(x, y, r, g, b, alpha)


def circle(cx, cy, r, col, alpha=1.0):
    ellipse(cx, cy, r, r, col, col, alpha)


def soft_disc(cx, cy, r, col, alpha):
    """Radial falloff disc (soft glow / shadow)."""
    y0 = max(0, int(cy - r))
    y1 = min(H, int(cy + r) + 1)
    for y in range(y0, y1):
        for x in range(max(0, int(cx - r)), min(W, int(cx + r) + 1)):
            d = math.hypot(x - cx, y - cy) / r
            if d >= 1:
                continue
            a = alpha * (1.0 - d * d)
            blend(x, y, col[0], col[1], col[2], a)


def speckle(cx, cy, rx, ry, n, cols, rmin=1, rmax=3, alpha=0.5):
    """Deterministic toasted speckles inside an ellipse."""
    for _ in range(n):
        ang = RNG.uniform(0, 2 * math.pi)
        rad = math.sqrt(RNG.random())
        x = int(cx + math.cos(ang) * rad * rx)
        y = int(cy + math.sin(ang) * rad * ry)
        c = RNG.choice(cols)
        circle(x, y, RNG.randint(rmin, rmax), c, alpha * RNG.uniform(0.5, 1.0))


def wobbly_blob(points, col, alpha=1.0):
    """Fill a polygon (scanline fill) - used for syrup drips and leaves."""
    ys = [p[1] for p in points]
    y0, y1 = max(0, int(min(ys))), min(H, int(max(ys)) + 1)
    n = len(points)
    for y in range(y0, y1):
        xs = []
        for i in range(n):
            x1, y1p = points[i]
            x2, y2p = points[(i + 1) % n]
            if (y1p <= y < y2p) or (y2p <= y < y1p):
                t = (y - y1p) / (y2p - y1p)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(max(0, int(xs[k])), min(W, int(xs[k + 1]) + 1)):
                blend(x, y, col[0], col[1], col[2], alpha)


def box_blur_region(x0, y0, x1, y1, radius):
    """Cheap separable box blur on a rectangular region (steam softening)."""
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    tmp = bytearray(buf)
    w = x1 - x0
    h = y1 - y0
    # horizontal pass into tmp copy, vertical pass back into buf
    horiz = bytearray(w * h * 3)
    for y in range(y0, y1):
        for x in range(x0, x1):
            sr = sg = sb = cnt = 0
            for dx in range(-radius, radius + 1):
                xx = min(max(x + dx, x0), x1 - 1)
                i = px(xx, y)
                sr += tmp[i]
                sg += tmp[i + 1]
                sb += tmp[i + 2]
                cnt += 1
            j = ((y - y0) * w + (x - x0)) * 3
            horiz[j] = sr // cnt
            horiz[j + 1] = sg // cnt
            horiz[j + 2] = sb // cnt
    for y in range(y0, y1):
        for x in range(x0, x1):
            sr = sg = sb = cnt = 0
            for dy in range(-radius, radius + 1):
                yy = min(max(y + dy, y0), y1 - 1)
                j = ((yy - y0) * w + (x - x0)) * 3
                sr += horiz[j]
                sg += horiz[j + 1]
                sb += horiz[j + 2]
                cnt += 1
            i = px(x, y)
            buf[i] = sr // cnt
            buf[i + 1] = sg // cnt
            buf[i + 2] = sb // cnt


# ---------------------------------------------------------------- scene
def paint_background():
    # Warm morning gradient: pale cream at top to soft honey at the bottom.
    top = (253, 240, 214)
    mid = (250, 214, 160)
    bot = (238, 178, 110)
    for y in range(H):
        t = y / (H - 1)
        if t < 0.55:
            col = lerp_col(top, mid, t / 0.55)
        else:
            col = lerp_col(mid, bot, (t - 0.55) / 0.45)
        i = y * W * 3
        for x in range(W):
            buf[i] = int(col[0])
            buf[i + 1] = int(col[1])
            buf[i + 2] = int(col[2])
            i += 3
    # Soft golden glow behind the dish.
    soft_disc(512, 470, 430, (255, 226, 160), 0.55)
    soft_disc(512, 470, 260, (255, 240, 200), 0.5)


def paint_table():
    # Warm wooden table band across the lower third, with faint grain.
    for y in range(770, H):
        t = (y - 770) / (H - 770)
        col = lerp_col((176, 118, 66), (140, 88, 46), t)
        for x in range(W):
            blend(x, y, col[0], col[1], col[2], 0.9)
    for _ in range(26):
        y = RNG.randint(790, 1010)
        x0 = RNG.randint(0, 500)
        ln = RNG.randint(200, 1024)
        for x in range(x0, min(W, x0 + ln)):
            blend(x, y, 120, 74, 38, 0.10)


def paint_plate():
    # Soft shadow under the plate, then the plate itself.
    soft_disc(512, 782, 430, (120, 70, 30), 0.28)
    ellipse(512, 716, 420, 136, (255, 251, 242), (232, 214, 190), 1.0,
            edge_dark=(196, 172, 140))
    # Inner rim ring.
    ellipse(512, 712, 352, 110, (250, 242, 226), (238, 222, 196), 1.0)
    ellipse(512, 712, 344, 106, (255, 253, 246), (244, 230, 206), 1.0)
    # Gloss highlight on the rim, upper left.
    ellipse(300, 660, 160, 28, (255, 255, 255), (255, 255, 255), 0.35)


def paint_pancake(cx, cy, rx, ry):
    # Golden-brown body with a toasted rim and a lighter, fluffy top.
    ellipse(cx, cy, rx, ry, (233, 178, 92), (176, 110, 44), 1.0,
            edge_dark=(146, 88, 30))
    ellipse(cx, cy - ry * 0.28, rx * 0.88, ry * 0.62,
            (246, 205, 128), (228, 168, 88), 0.9)
    # Toasted speckles and a few darker golden bubbles.
    speckle(cx, cy - ry * 0.2, rx * 0.85, ry * 0.55, 260,
            [(190, 122, 48), (168, 100, 34), (214, 150, 70)], 1, 3, 0.5)
    speckle(cx, cy - ry * 0.2, rx * 0.7, ry * 0.45, 60,
            [(222, 164, 84), (240, 196, 120)], 2, 5, 0.55)
    # Bottom edge shadow so the stack reads as separate layers.
    ellipse(cx, cy + ry * 0.55, rx * 0.96, ry * 0.42,
            (120, 70, 24), (120, 70, 24), 0.35)


def paint_syrup_drip(x, top_y, length, width):
    """A glossy honey drip running down the front of the stack."""
    pts = []
    steps = 10
    for s in range(steps + 1):
        t = s / steps
        y = top_y + t * length
        wob = math.sin(t * 9.0) * 2.5
        pts.append((x - width / 2 + wob, y))
    for s in range(steps, -1, -1):
        t = s / steps
        y = top_y + t * length
        wob = math.sin(t * 9.0) * 2.5
        pts.append((x + width / 2 + wob, y))
    wobbly_blob(pts, (196, 118, 16), 0.95)
    # Rounded bulb at the bottom of the drip.
    circle(x, top_y + length, width * 0.62, (196, 118, 16), 0.95)
    # Gloss streak down the drip.
    for s in range(steps + 1):
        t = s / steps
        y = int(top_y + t * length)
        blend(int(x - width * 0.18), y, 255, 214, 120, 0.55)


def paint_syrup_pool(cx, cy, rx, ry):
    # Amber syrup pooled on the top pancake, glossy with highlights.
    ellipse(cx, cy, rx, ry, (232, 158, 32), (190, 110, 14), 0.96,
            edge_dark=(160, 92, 10))
    ellipse(cx - rx * 0.25, cy - ry * 0.3, rx * 0.45, ry * 0.4,
            (255, 205, 90), (255, 205, 90), 0.5)
    ellipse(cx + rx * 0.35, cy + ry * 0.25, rx * 0.3, ry * 0.3,
            (255, 190, 70), (255, 190, 70), 0.35)


def paint_butter(cx, cy):
    # A pat of butter, melting: soft yellow square with rounded corners.
    w, h = 92, 46
    pts = [(cx - w / 2 + 12, cy - h / 2), (cx + w / 2 - 12, cy - h / 2),
           (cx + w / 2, cy - h / 2 + 12), (cx + w / 2, cy + h / 2 - 12),
           (cx + w / 2 - 12, cy + h / 2), (cx - w / 2 + 12, cy + h / 2),
           (cx - w / 2, cy + h / 2 - 12), (cx - w / 2, cy - h / 2 + 12)]
    wobbly_blob(pts, (255, 226, 130), 1.0)
    wobbly_blob([(cx - w / 2 + 18, cy - h / 2 + 6),
                 (cx + w / 2 - 18, cy - h / 2 + 6),
                 (cx + w / 2 - 6, cy - h / 2 + 16),
                 (cx - w / 2 + 6, cy - h / 2 + 16)],
                (255, 244, 190), 0.9)
    # Melted butter pooling at its base.
    ellipse(cx + 6, cy + h / 2 + 4, 58, 10, (255, 222, 120), (250, 200, 90),
            0.95)


def paint_blueberry(cx, cy, r):
    # Plump blueberry: deep indigo body, dusty bloom, bright highlight,
    # little star crown on top.
    ellipse(cx, cy, r, r * 0.92, (74, 74, 150), (38, 38, 96), 1.0,
            edge_dark=(24, 24, 66))
    ellipse(cx - r * 0.3, cy - r * 0.35, r * 0.55, r * 0.45,
            (120, 122, 190), (120, 122, 190), 0.45)
    circle(cx - r * 0.38, cy - r * 0.42, r * 0.22, (235, 238, 255), 0.9)
    # Star crown.
    for k in range(5):
        ang = -math.pi / 2 + k * 2 * math.pi / 5
        x1 = cx + math.cos(ang) * r * 0.28
        y1 = cy - r * 0.92 + math.sin(ang) * r * 0.28
        x2 = cx + math.cos(ang + 0.5) * r * 0.12
        y2 = cy - r * 0.92 + math.sin(ang + 0.5) * r * 0.12
        blend(int(x1), int(y1), 30, 30, 70, 0.8)
        blend(int(x2), int(y2), 30, 30, 70, 0.8)
    circle(cx, cy - r * 0.92, r * 0.16, (28, 28, 64), 0.9)


def paint_mint_leaf(cx, cy, size, angle_deg):
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    px_, py_ = -dy, dx
    pts = []
    for s in range(13):
        t = s / 12
        along = (t - 0.5) * size
        width = math.sin(t * math.pi) * size * 0.32
        pts.append((cx + dx * along - px_ * width,
                    cy + dy * along - py_ * width))
    for s in range(12, -1, -1):
        t = s / 12
        along = (t - 0.5) * size
        width = math.sin(t * math.pi) * size * 0.32
        pts.append((cx + dx * along + px_ * width,
                    cy + dy * along + py_ * width))
    wobbly_blob(pts, (74, 148, 74), 1.0)
    # Centre vein.
    for s in range(9):
        t = s / 8
        blend(int(cx + dx * (t - 0.5) * size * 0.9),
              int(cy + dy * (t - 0.5) * size * 0.9),
              190, 230, 170, 0.7)


def paint_honey_on_plate():
    # A smooth honey swirl on the plate, right of the stack.
    for i in range(260):
        t = i / 259
        x = 690 + t * 170
        y = 800 + math.sin(t * math.pi) * 26 - t * 10
        circle(int(x), int(y), 5, (214, 138, 24), 0.85)
        circle(int(x), int(y), 2, (255, 200, 90), 0.6)


def paint_steam():
    # Three rising wisps of steam above the hot stack, then softened.
    for cx0, amp, ph in ((452, 26, 0.0), (512, 34, 1.3), (572, 26, 2.6)):
        for y in range(170, 365):
            t = (365 - y) / 195
            wob = math.sin(y * 0.045 + ph) * amp * t
            cx = cx0 + wob
            half = 26 * (0.5 + t * 0.7)
            for x in range(int(cx - half), int(cx + half) + 1):
                d = abs(x - cx) / half
                a = 0.22 * (1 - d) * (0.4 + 0.6 * t)
                blend(x, y, 255, 250, 240, a)
    box_blur_region(380, 150, 650, 375, 6)


def paint_vignette():
    for y in range(H):
        for x in range(W):
            d = math.hypot((x - 512) / 512, (y - 512) / 512)
            if d > 0.95:
                blend(x, y, 90, 50, 20, min(0.22, (d - 0.95) * 0.8))


# ---------------------------------------------------------------- PNG encode
def write_png(path, width, height, data):
    def chunk(typ, payload):
        c = struct.pack(">I", len(payload)) + typ + payload
        c += struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter: None
        raw += data[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    paint_background()
    paint_table()
    paint_plate()
    # Pancake stack, bottom to top.
    paint_pancake(512, 622, 288, 62)
    paint_pancake(512, 554, 276, 60)
    paint_pancake(512, 490, 262, 58)
    paint_pancake(512, 428, 244, 56)
    # Honey syrup: pool on top, drips down the front of the stack.
    paint_syrup_pool(512, 398, 205, 36)
    paint_syrup_drip(428, 428, 170, 28)
    paint_syrup_drip(606, 426, 210, 26)
    paint_syrup_drip(512, 432, 120, 32)
    # Melting butter on top, blueberries, mint.
    paint_butter(512, 368)
    paint_blueberry(386, 404, 32)
    paint_blueberry(648, 398, 29)
    paint_blueberry(600, 376, 24)
    paint_mint_leaf(656, 430, 78, -28)
    # Berries and honey resting on the plate.
    paint_blueberry(292, 716, 28)
    paint_blueberry(348, 738, 24)
    paint_mint_leaf(768, 668, 68, 18)
    paint_honey_on_plate()
    # Steam, then a gentle vignette.
    paint_steam()
    paint_vignette()
    n = write_png(OUT, W, H, buf)
    print(f"wrote {OUT} ({W}x{H}, {n} bytes)")


if __name__ == "__main__":
    main()
