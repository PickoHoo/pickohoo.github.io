# PickoHoo Reels — generator + first batch

**Status:** 3 reels ready to publish (Claude, 22 Nov 2026). Branch `reels` — not merged to `main`, so the live site is untouched.

| # | Reel | Length | Hook | Links to |
|---|------|--------|------|----------|
| 01 | `out/pickohoo_01_dad_types.mp4` | 20.8s | "What kind of dad is yours?" — 3 dad types, 3 real picks under £30 (Faithfull £22.95, Sealey £26.95, Sirius £26.99), Santa-hat Hoo + snow + bells | christmas-gifts-for-dad pages |
| 02 | `out/pickohoo_02_black_friday_checks.mp4` | 18.6s | "Don't buy anything yet…" — 3 Black Friday checks, no products | profile / follow |
| 03 | `out/pickohoo_03_regret_test.mp4` | 21.4s | "Which mistake would YOU make? Comment A, B or C" | toolkit-regret-test.html |

All 1080×1920, 30fps, H.264 + AAC, original synthesized music (no licensing issues). Product scenes carry "Ad · price from retailer feed, check before you buy". Prices = Awin feed snapshot 22 Nov 05:19 UTC — **re-check before posting**.

## Make a new reel
```
python3 reel.py specs/01_dad_types.json out/new.mp4
FRAMES="0:2.5,1:2.5" python3 reel.py specs/x.json out/x.mp4   # preview stills only
```
Scene types: `hook`, `pick` (label, image, price, name, why), `tip`, `quiz`, `reveal`, `cta`. Spec options: `snow`, `music.bpm`, `music.bells`, `music.key`, per-scene `hat` (Santa hat on Hoo).
Product images: crop the white square from `cards/*-pin.png` → `(207,581,792,1166)`.

Rule: never invent products or prices — `pick` scenes only from the Awin feed / live pages.
