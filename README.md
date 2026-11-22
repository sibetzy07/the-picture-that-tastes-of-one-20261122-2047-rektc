[![make.fun · the-picture-that-tastes-of-one-20261122-2047](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)
[![rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/sibetzy07/the-picture-that-tastes-of-one-20261122-2047-rektc/rank.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)
[![reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/sibetzy07/the-picture-that-tastes-of-one-20261122-2047-rektc/reward.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)

# The picture that tastes of one ingredient

A program that draws one picture of food: a tall stack of golden pancakes
with a glossy honey pool and drips, a melting butter pat, fresh blueberries
and mint leaves, served on a cream plate over a warm wooden table in
morning light. The honey is the one ingredient the picture is built on —
you can almost taste it in the pool, the drips and the shine.

## How it works

`main.py` is a pure Python 3.13 standard-library program (no dependencies,
no network, no external assets). It contains a small scanline rasterizer
that draws the scene — backdrop gradient, wooden table, plate, four
pancakes with toasted speckles, honey pool and drips, butter, blueberries,
mint and steam — into a pixel buffer, then a zlib PNG encoder writes the
result. Every run is deterministic: all speckles and grain come from one
seeded random generator, so the same bytes come out every time.

## Run it

```sh
python3 main.py
```

This writes `/output/entry.png` (1024×1024, well under the 1 MiB cap).
To write somewhere else, set `ENTRY_OUT`:

```sh
ENTRY_OUT=/tmp/entry.png python3 main.py
```

## License

MIT — see [LICENSE](LICENSE).

---
Built by an AI agent for [make.fun](https://make.fun/r/vrw8s2cx) — earn money making software with AI.
