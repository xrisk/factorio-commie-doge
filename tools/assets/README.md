# tools/assets

Raster assets composited into the generated sprites by `gen_commie_doge.py`.

## hammer_sickle.png / hammer_sickle_dark.png

A gold (and dark-gold) hammer & sickle silhouette on transparency, used for the mining tool
and the cap emblem (so it reads as an actual hammer & sickle instead of procedural line-art).

- **Source:** the public-domain hammer-and-sickle symbol from Wikimedia Commons
  (`Special:FilePath/Hammer_and_sickle.svg`). The hammer and sickle is a basic political
  emblem in the public domain.
- **Processing:** rendered to PNG, red background keyed out via the green channel
  (`-channel G -separate -level …` → alpha), trimmed, scaled to 72px, and recolored to the
  generator's `GOLD` (`#f7c93e`) and a dark-gold (`#785214`).

To regenerate from a fresh download, see the keying recipe in the project history / CLAUDE.md.
