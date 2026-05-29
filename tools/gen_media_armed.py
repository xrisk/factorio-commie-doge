#!/usr/bin/env python3
"""Build media/commie-doge-armed.png: the green-pistol showcase.

Renders the armed Shiba (red player color via gen_commie_doge.SAMPLE_TINT) facing
E/SE/S/SW/W and composites the frames onto a seamless grass strip tiled from a
swatch cropped out of the hero screenshot, with soft drop shadows. Needs Python 3
and ImageMagick (magick). Run from anywhere: `python3 tools/gen_media_armed.py`.
"""
import os, sys, math, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gen_commie_doge as g  # noqa: E402

OUT = os.path.join(REPO, "media", "commie-doge-armed.png")
HERO = os.path.join(REPO, "media", "commie-doge.png")
DIRS = [2, 3, 4, 5, 6]          # E, SE, S, SW, W
W, H, SCALE = 600, 150, 160     # strip size; doge scale in %


def run(args):
    subprocess.run(args, check=True)


def main():
    tmp = tempfile.mkdtemp(prefix="armed_")
    grass = os.path.join(tmp, "grass.png")
    run(["magick", HERO, "-crop", "60x60+2+2", "+repage", grass])

    frames = []
    for d in DIRS:
        theta = (d / 8) * 2 * math.pi
        p = os.path.join(tmp, f"armed_{d}.png")
        g.render_preview(theta, 0.0, g.IDLE_MOTION, True, p)
        frames.append(p)

    scene = os.path.join(tmp, "scene.png")
    run(["magick", "-size", f"{W}x{H}", f"tile:{grass}", scene])

    sh = os.path.join(tmp, "sh.png")
    shargs = ["magick", "-size", f"{W}x{H}", "xc:none", "-fill", "rgba(0,0,0,0.30)"]
    for i in range(len(frames)):
        cx = 60 + i * 120
        shargs += ["-draw", f"ellipse {cx},133 24,6 0,360"]
    shargs += ["-blur", "0x2", sh]
    run(shargs)
    run(["magick", scene, sh, "-compose", "over", "-composite", scene])

    for i, p in enumerate(frames):
        cx = 60 + i * 120
        scaled = os.path.join(tmp, f"sc_{i}.png")
        run(["magick", p, "-filter", "point", "-resize", f"{SCALE}%", scaled])
        run(["magick", scene, scaled, "-gravity", "northwest",
             "-geometry", f"+{cx - 58}+3", "-compose", "over", "-composite", scene])

    run(["magick", scene, OUT])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
