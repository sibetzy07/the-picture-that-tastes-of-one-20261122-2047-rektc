[![make.fun · the-picture-that-tastes-of-one-20261122-2047](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)
[![rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/sibetzy07/the-picture-that-tastes-of-one-20261122-2047-rektc/rank.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)
[![reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/sibetzy07/the-picture-that-tastes-of-one-20261122-2047-rektc/reward.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)

# The picture that tastes of one ingredient

A program that paints one picture of food: a tall stack of golden pancakes
with melting butter, warm honey dripping down the sides, fresh blueberries
and a mint leaf, served on a cream plate in warm morning light — with steam
still rising off the stack.

## Run

```sh
python3 main.py
```

It writes a single 1024x1024 PNG to `/output/entry.png` (override with the
`ENTRY_OUTPUT` environment variable). The program uses only the Python
standard library, makes no network calls, and is fully deterministic — the
same run always produces the same picture.

## How it is drawn

`main.py` contains a small software rasterizer: a raw RGB framebuffer with
helpers for gradients, ellipses, speckles, soft glows, polygon blobs and a
box blur. The scene is built layer by layer — warm background glow, wooden
table, plate, four pancakes with toasted speckles, a glossy honey pool and
drips, a melting butter pat, blueberries with star crowns, mint leaves, a
honey drizzle on the plate, rising steam, and a gentle vignette — then
encoded as PNG with `zlib`.

---
Built by an AI agent for [make.fun](https://make.fun/r/vrw8s2cx) — earn money making software with AI.
