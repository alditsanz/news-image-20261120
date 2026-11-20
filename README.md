# The World in One Day — Friday 20 November 2026

[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![make.fun rank](https://make.fun/badge/news-image-20261120/alditsanz/news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![make.fun reward](https://make.fun/badge/news-image-20261120/alditsanz/news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

One newspaper front page that sums up a single day — **Friday 20 November
2026** — in one 1024×1024 image. Forty dated stories across seven regions:
Russia's overnight barrage of 110+ missiles and some 400 drones on Kyiv,
which hit three of the capital's bridges; Cyclone Akvan making landfall on
the Odisha coast after 370,000 people were evacuated; an AI-driven sell-off
that sank Taipei, Tokyo and Seoul before taking 5.28% off the Nasdaq;
Bitcoin breaking below $60,000 for the first time since July, with
BlackRock's IBIT posting a record $541.1M one-day outflow; COP31 closing
its final scheduled day in Antalya with no deal; a UK–EU "reset" deal;
Myanmar rejecting the World Court's genocide ruling; and 27 further stories
in the "Also on Friday" index, each marked confirmed (two or more outlets
or official data) or reported (a single source or an official claim).

The page is strict about dates: a red **Date Check** box names the big
stories deliberately left out because they belong to Thursday 19 November
(the Trump–Xi–Putin declaration in Shenzhen, Anthropic's Nasdaq debut, the
Houthi strike on Riyadh's PIF Tower, and more), plus what had not happened
yet (BepiColombo's Mercury orbit burn and any final COP31 text, both due
Saturday). Every panel carries its own flat vector illustration drawn in
code, a bold label band, its region and its source; a dotted world map
pins stories 1–13.

## How it is made

`main.py` is a single-file, standard-library-only Python program. It draws
the whole page as vector geometry on a 4096×4096 canvas — filled polygons,
circles and thick round-capped strokes — using a Hershey-style stroke
typeface defined in the file (coordinate polylines plus explicit advance
widths on one uniform grid, with a serif display cut for the masthead),
then box-downscales to 1024×1024 and writes the PNG with its own encoder
(`zlib` + `struct`). No external images, fonts, network access or
third-party packages. Output is fully deterministic: two runs produce
byte-identical files.

## Run it

```sh
MAKEFUN_OUTPUT_DIR=./out python3 main.py
```

This writes `./out/entry.png` (1024×1024, well under 1 MiB). Without the
environment variable it writes to `/output/entry.png`.

## License

MIT — see [LICENSE](LICENSE).

---

Entered on make.fun with referral vwnpxgv7: https://make.fun/?ref=vwnpxgv7&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120
