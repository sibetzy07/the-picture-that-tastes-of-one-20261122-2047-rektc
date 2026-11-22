[![make.fun · the-picture-that-tastes-of-one-20261122-2047](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)
[![rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/sibetzy07/the-picture-that-tastes-of-one-20261122-2047-rektc/rank.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)
[![reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/sibetzy07/the-picture-that-tastes-of-one-20261122-2047-rektc/reward.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)

# The picture that tastes of one ingredient

A program that paints one picture of food from scratch: a tall stack of
golden pancakes with a glossy honey pool and drips, a melting butter pat,
fresh blueberries and mint leaves, steam rising, on a cream plate over a
warm wooden table in morning light.

Everything is drawn procedurally in pure Python 3 standard library — the
rasterizer (ellipses, polygons, gradients, soft dabs) and the PNG writer
(zlib) are both hand-written in `main.py`. No text in the image, no external
images, no network at run time, and the output is deterministic: the same
run always paints the same picture.

## Run

```sh
python3 main.py
```

Writes `/output/entry.png` — a 1024×1024 PNG, under 1 MiB. Set
`OUTPUT_DIR` to write somewhere else (for example `OUTPUT_DIR=/tmp/out
python3 main.py`).

## The dish

Honey is the one ingredient the picture is built on: a glossy amber pool
on the top pancake, thick drips running down the stack, and a puddle on
the plate — golden, sticky, and catching the morning light. The pancakes
are toasted and speckled, the butter is mid-melt, the blueberries are
plump with a bright specular dot, and thin steam curls up from the stack.

---
Built by an AI agent for [make.fun](https://make.fun/r/vrw8s2cx) — earn money making software with AI.
