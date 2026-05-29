#!/usr/bin/env bash
# Recolor the player-color cap+chest of the hero screenshot from purple to red.
#
# media/commie-doge.png is a real in-game screenshot (grass + the game's own
# shadow), captured with a *purple* player color. The README wants red, so this
# does a hue-selective ImageMagick recolor in place: only the purple cap+chest
# become red; grass, tan fur and the gold star stay byte-identical.
#
# Idempotent: re-running on an already-red image is a no-op (no purple to select).
# To reproduce from the original purple capture: `git show <commit>:media/commie-doge.png`.
#
# Usage: tools/recolor_hero.sh [input.png] [output.png]   (default: media/commie-doge.png, in place)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IN="${1:-$HERE/media/commie-doge.png}"
OUT="${2:-$IN}"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT

# split into HSL planes
magick "$IN" -colorspace HSL -separate "$T/hsl_%d.png"

# purple selection mask: hue in band [165,215]/255  AND  saturation >= ~64
magick "$T/hsl_0.png" -threshold 64.7% "$T/m_lo.png"
magick "$T/hsl_0.png" -threshold 84.3% -negate "$T/m_hi.png"
magick "$T/hsl_1.png" -threshold 25% "$T/m_sat.png"
magick "$T/m_lo.png" "$T/m_hi.png" -compose multiply -composite \
       "$T/m_sat.png" -compose multiply -composite "$T/m_raw.png"
# drop grass speckles, then grow 1px to cover the anti-aliased rim
magick "$T/m_raw.png" -morphology Open Disk:1 -morphology Dilate Disk:1 "$T/mask.png"

# inside the mask: hue->0 (red), sat->168 (~0.66, matches rgb(196,40,40)), and
# clamp lightness <=47% so the light lavender belly reads as solid red, not pink.
magick "$T/hsl_0.png" -evaluate set 0     "$T/const_h.png"
magick "$T/hsl_1.png" -evaluate set 65.9% "$T/const_s.png"
magick "$T/hsl_2.png" -evaluate Min 47%   "$T/L_clamped.png"
magick "$T/hsl_0.png" "$T/const_h.png"   "$T/mask.png" -composite "$T/newH.png"
magick "$T/hsl_1.png" "$T/const_s.png"   "$T/mask.png" -composite "$T/newS.png"
magick "$T/hsl_2.png" "$T/L_clamped.png" "$T/mask.png" -composite "$T/newL.png"

magick "$T/newH.png" "$T/newS.png" "$T/newL.png" -set colorspace HSL -combine -colorspace sRGB "$T/red_full.png"
# composite only the masked region back onto the untouched original
magick "$IN" "$T/red_full.png" "$T/mask.png" -composite "$OUT"
echo "recolored -> $OUT"
