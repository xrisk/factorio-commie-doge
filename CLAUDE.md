# commie-doge

A Factorio 2.0 mod that reskins the player character as a comrade Shiba — 8-direction
animated waddle, curled tail, player-colored cap with gold star + hammer & sickle, a green
toy water pistol when armed, a gold hammer & sickle swung when mining, projected cast shadows,
and optional doge-speak flying-text toasts that narrate your factory in broken comrade grammar.

## Layout
- `commie-doge/` — the mod itself (this folder is what zips for the portal).
  - `info.json` — manifest. Internal `name` is `commie-doge`; it MUST match the folder name
    and the `__commie-doge__/...` paths in the lua. Renaming the mod = update all three.
  - `data-final-fixes.lua` — overwrites `data.raw.character.character.animations`.
  - `control.lua` — runtime doge-speak toasts (cosmetic flying text, no state changes).
    `settings.lua` — the per-player `commie-doge-toasts` toggle (default on).
  - `graphics/*.png` — 21 generated sheets (5 states × body/mask/emblem/shadow, plus a
    flipped gun-run shadow). Don't hand-edit.
- `tools/gen_commie_doge.py` — the parametric generator. **Edit art here, not the PNGs.**
  `python3 tools/gen_commie_doge.py contact` -> preview sheets in /tmp; `build` -> regenerate
  everything into `commie-doge/graphics/`. Needs Python 3 + ImageMagick (`magick`); no PIL.
- `tools/assets/*.png` — raster assets the generator composites in via `image_op` (the real
  hammer & sickle, a public-domain Wikimedia symbol). See `tools/assets/README.md`.

## Sprite-sheet conventions
- Sheets are rows = directions, cols = frames, `line_length = frame_count`. Frame 72x92,
  drawn at `scale = 0.5`.
- Direction index 0 = North (facing away), increasing clockwise (N, NE, E, SE, S, SW, W, NW).
- Direction counts: idle / idle_with_gun / running / mining = 8; **running_with_gun = 18**.
- Up to four layers per state: body (untinted; includes the green pistol and the gold mining
  hammer & sickle) + chest/cap tint-mask (`apply_runtime_tint`, takes player color) + gold
  emblem (star + hammer & sickle, drawn ON TOP so it stays gold over the player-colored cap;
  empty facing away) + a `draw_as_shadow` cast shadow. A thin dark outer outline is baked onto
  the body layer by `render_frame` (a silhouette dilate), which is what makes it read crisply.

## Non-obvious gotchas
- **The tail draws ONLY in back facings (N/NE/NW), gated `if away > 0.15` (`away = max(0,-fy)`).**
  A tail curl on the flank in front/side views gets misread as a raised paw/"hand" (a real
  reported bug, twice). Side views (E/W) therefore show no tail — intentional; gating
  side-but-not-front would need `abs(fx)`, not `away`.
- **`running_with_gun` must be 18 (or 40) directions, and the row order is undocumented.** The
  engine expects what the vanilla `level1_running_gun.png` shows: 18 rows sweeping the gun aim
  N → E → S over the EAST hemisphere only, then mirrored for the west half (that's why base ships
  a `*_shadow_flipped`). We replicate it via `half_sweep` (theta = pi·d/(dirs−1)); filling the rows
  in any other order is the infamous "moonwalk". Decoded once by montaging frame-0 of all 18
  vanilla rows (`magick … -crop 108x136+0+r*136`) — re-derive the same way if it ever drifts.
- **Shadows are baked-in casts sharing the body's frame & shift.** `make_shadow` recolors the
  silhouette flat black and Affine-projects it east (`SHADOW_AFFINE`); `draw_as_shadow` lets the
  engine tint it. Vanilla uses wider shadow sheets + a custom shift for a longer flat cast; we keep
  the 72x92 frame/shift so alignment is automatic (shorter cast, suits the cartoon). The gun-run's
  west half is engine-mirrored, so it needs a hand-made `rungun_shadow_flipped` (rendered with
  `flip_sweep`: west-aim bodies, same east cast), wired via `flipped_shadow_running_with_gun`.
  Shadows + the gun-run flip are correct by construction but **unverified in a running game**.
- **Doge-speak toasts are cosmetic and desync-safe.** `control.lua` only emits
  `create_local_flying_text` (player-local, unsaved) and never mutates state. Frequent events
  (mine/build/craft/kill) are gated by a per-player 150-tick cooldown + random chance; rare ones
  (research/rocket/death/respawn) bypass it; low-HP, nearby-enemy and day↔night are edge-triggered
  in an `on_nth_tick(53)` poll. State lives in `storage` (the 2.0 rename of `global`).
- A single `animations` entry with **no `armors` key** is the catch-all, so one entry covers
  every armor state (power armor included — all the same character).
- The green pistol is drawn (MVG primitives) on the **body** layer; the **hammer & sickle is a
  raster** (`tools/assets/hammer_sickle*.png`, the real Wikimedia symbol) composited via `image_op`
  — gold on the body layer for the mining tool, dark-gold on the emblem layer over the cap star.
  Only chest + cap fill are on the mask. The old procedural h&s line-art was removed because it
  read as "a circle with a line through it" at this size; a recolored raster silhouette reads.
- **Restart Factorio to see sprite changes** — it bakes sprites into a texture atlas at
  startup, so a running instance keeps the old art. Data-only reskin: conflicts with other
  character mods (only enable one; `! penguin-character` is declared in info.json).
- **`build` is not byte-deterministic** (re-runs `magick` per sheet), so `git status` shows
  all 21 PNGs changed even after a one-layer tweak; only changed layers differ in *pixels*
  (verify with `magick compare -metric AE`). Don't add `-flatten` to `+append`/`-append` — it
  re-crops to one frame; assemble with plain append on `PNG32:` inputs.

## Tuning knobs (gen_commie_doge.py + lua)
- `SHIFT = util.by_pixel(0, -17)` in the lua positions the paws on the entity origin; adjust
  if the dog floats above / sinks into the ground.
- Motion amplitudes: `RUN_MOTION` / `IDLE_MOTION` / `MINE_MOTION` dicts (sway/bob/foot/lean).
- `SHADOW_AFFINE` — the cast-shadow projection (feet anchor, east shear, vertical squash).
- `OUTLINE` color + the `disk:2` dilate in `render_frame` — the baked body-outline thickness.
- The mining swing (`rdx/rdy` raised → `sdx/sdy` struck) + the `image_op(... HS_GOLD ... hw)`
  size — how the hammer & sickle is held and how big it reads.
- `control.lua`: `COOLDOWN`, per-category `maybe(...)` chances, and the `LINES` doge-speak pools.

## README media (`media/*.png`)
- `commie-doge.png` (hero) is a **real in-game screenshot** (grass, the game's own shadow), so
  the tool can't regenerate it. It was shot with a *purple* player color; the README wants red,
  so the purple cap+chest are recolored in place by a hue-selective ImageMagick pass (see
  `tools/recolor_hero.sh`): split HSL, mask = (hue band 165–215/255) AND (sat ≥ 25%), morphology
  Open+Dilate, then inside the mask set hue→0, sat→168, **clamp lightness ≤47%** (so the light
  lavender belly reads as solid red, not pink), recombine, and composite the masked region back
  onto the untouched original (keeps grass/tan/gold byte-identical — no HSL round-trip noise).
- `commie-doge-armed.png` is the green-pistol shot: armed frames from
  `gen_commie_doge.render_preview(theta, 0, IDLE_MOTION, True, …)` (its `SAMPLE_TINT` is already
  red) for dirs E/SE/S/SW/W, composited onto a seamless grass strip tiled from a swatch cropped
  out of the hero (`magick media/commie-doge.png -crop 60x60+2+2`), with hand-drawn soft shadows.
  Built by `tools/gen_media_armed.py`.

## History
Spun out of the `dog-character` branch of the `penguin-mod` repo (which also has a penguin
reskin). The two share the generator engine and both overwrite the character, hence the
mutual-incompatibility declaration.

A later pass (v0.2.0) added directional gun-run aiming (the `half_sweep` fix, decoded from the
vanilla sheet), `draw_as_shadow` cast shadows on every state, the gold hammer & sickle mining
tool, a baked body outline + chunkier Shiba ears / better snout, and the doge-speak toasts
(`control.lua` + `settings.lua`).
