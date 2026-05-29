# commie-doge

A Factorio 2.0 mod that reskins the player character as a comrade Shiba — 8-direction
animated waddle, curled tail, player-colored cap with gold star + hammer & sickle, and a
green toy water pistol when armed.

## Layout
- `commie-doge/` — the mod itself (this folder is what zips for the portal).
  - `info.json` — manifest. Internal `name` is `commie-doge`; it MUST match the folder name
    and the `__commie-doge__/...` paths in the lua. Renaming the mod = update all three.
  - `data-final-fixes.lua` — overwrites `data.raw.character.character.animations`.
  - `graphics/*.png` — 15 generated sheets (5 states x body/mask/emblem). Don't hand-edit.
- `tools/gen_commie_doge.py` — the parametric generator. **Edit art here, not the PNGs.**
  `python3 tools/gen_commie_doge.py contact` -> preview sheets in /tmp; `build` -> regenerate
  everything into `commie-doge/graphics/`. Needs Python 3 + ImageMagick (`magick`); no PIL.

## Sprite-sheet conventions
- Sheets are rows = directions, cols = frames, `line_length = frame_count`. Frame 72x92,
  drawn at `scale = 0.5`.
- Direction index 0 = North (facing away), increasing clockwise (N, NE, E, SE, S, SW, W, NW).
- Direction counts: idle / idle_with_gun / running / mining = 8; **running_with_gun = 18**.
- Three layers per state: body (untinted; includes the green pistol) + chest/cap tint-mask
  (`apply_runtime_tint`, takes player color) + gold emblem (star + hammer & sickle, drawn ON
  TOP so it stays gold over the player-colored cap). Emblem frames are empty facing away.

## Non-obvious gotchas
- **The tail draws ONLY in back facings (N/NE/NW), gated `if away > 0.15` (`away = max(0,-fy)`).**
  A tail curl on the flank in front/side views gets misread as a raised paw/"hand" (a real
  reported bug, twice). Side views (E/W) therefore show no tail — intentional; gating
  side-but-not-front would need `abs(fx)`, not `away`.
- **`running_with_gun` must be 18 (or 40) directions.** The 18-dir gun-aim x movement mapping
  is undocumented and buggy even in vanilla (forum: "moonwalk"), so `rungun` tiles ONE front
  pistol pose across all 18 (`south_only=True`) — non-directional but never broken. Directional
  aiming lives in `idle_with_gun` (8-dir, correct).
- A single `animations` entry with **no `armors` key** is the catch-all, so one entry covers
  every armor state (power armor included — all the same character).
- The green pistol is on the **body** layer (untinted); only chest + cap fill are on the mask.
- **Restart Factorio to see sprite changes** — it bakes sprites into a texture atlas at
  startup, so a running instance keeps the old art. Data-only reskin: conflicts with other
  character mods (only enable one; `! penguin-character` is declared in info.json).
- **`build` is not byte-deterministic** (re-runs `magick` per sheet), so `git status` shows
  all 15 PNGs changed even after a one-layer tweak; only changed layers differ in *pixels*
  (verify with `magick compare -metric AE`). Don't add `-flatten` to `+append`/`-append` — it
  re-crops to one frame; assemble with plain append on `PNG32:` inputs.

## Tuning knobs (gen_commie_doge.py + lua)
- `SHIFT = util.by_pixel(0, -17)` in the lua positions the paws on the entity origin; adjust
  if the dog floats above / sinks into the ground.
- Motion amplitudes: `RUN_MOTION` / `IDLE_MOTION` / `MINE_MOTION` dicts (sway/bob/foot/lean).

## History
Spun out of the `dog-character` branch of the `penguin-mod` repo (which also has a penguin
reskin). The two share the generator engine and both overwrite the character, hence the
mutual-incompatibility declaration.
