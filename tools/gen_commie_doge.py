#!/usr/bin/env python3
"""
Parametric Shiba-dog sprite generator for the `commie-doge` mod.

Same engine as tools/gen_penguin.py: one parametric renderer draws a sitting
Shiba ("doge") at an arbitrary facing orientation and waddle phase using
ImageMagick `-draw` primitives (no PIL), assembled into sheets laid out
rows=directions, cols=frames (line_length = frame_count), matching the base
game. Only the drawing + palette differ from the penguin; the sheet/build/
contact machinery is identical.

The penguin's biped layout (head-on-top, body-below, feet-blobs) maps onto a
*sitting* Shiba: tan body, cream chest (the team-color tint-mask layer), erect
triangular ears, a cream muzzle with a black nose, and a curled tail at the
rear. The green toy water pistol carries over.

Direction convention (verified against base game): index 0 = North (facing
away), increasing clockwise. orientation = index / direction_count ;
theta = orientation * 2pi.

Usage:
    gen_commie_doge.py contact   # write preview contact sheets to /tmp for inspection
    gen_commie_doge.py build     # write final animation sheets into ../commie-doge/graphics
"""
import math, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GFX = os.path.normpath(os.path.join(HERE, "..", "commie-doge", "graphics"))

FW, FH = 72, 92          # frame size (px), scale=0.5 in-game
CX, CY = 36, 46          # frame center == body center
KV = 0.55                # vertical foreshorten for the 3/4 camera

FUR     = "rgb(224,162,95)"     # Shiba tan
FUR_D   = "rgb(174,114,58)"     # darker tan: shading, ear-backs, tail
CREAM   = "rgb(247,240,226)"    # muzzle / chest / inner ear / paws
NOSE    = "rgb(40,34,33)"       # black nose
EYE     = "rgb(30,24,22)"       # eyes
CAP_EDGE = "rgb(58,52,52)"      # cap outline/brim rim (the cap fill is the player color, via the mask)
GOLD    = "rgb(247,201,62)"     # star + hammer & sickle (fixed gold; never tinted)
GOLD_D  = "rgb(176,128,24)"     # gold outline
WHITE   = "rgb(248,248,248)"    # tint-mask core (kept near-white so team color reads true)
ORANGE  = "rgb(255,155,26)"     # pistol nozzle
GREEN   = "rgb(60,214,92)"
GREEN_D = "rgb(28,140,54)"

def vec(theta):
    """screen facing unit vector; theta=0 -> north(away), +x=east, +y=toward viewer."""
    return math.sin(theta), -math.cos(theta)

def f2(v): return f"{v:.2f}"

# ---- MVG primitive helpers (append strings to an ops list) -------------------
def ellipse(ops, color, cx, cy, rx, ry):
    ops.append(f"fill {color} stroke none ellipse {f2(cx)},{f2(cy)} {f2(rx)},{f2(ry)} 0,360")

def circle(ops, color, cx, cy, r):
    ellipse(ops, color, cx, cy, r, r)

def polygon(ops, color, pts, outline=None, ow=1.0):
    s = " ".join(f"{f2(x)},{f2(y)}" for x, y in pts)
    if outline:
        ops.append(f"fill {color} stroke {outline} stroke-width {f2(ow)} polygon {s}")
    else:
        ops.append(f"fill {color} stroke none polygon {s}")

def capsule(ops, color, x0, y0, x1, y1, w):
    ops.append(f"stroke {color} stroke-width {f2(w)} stroke-linecap round fill none "
               f"line {f2(x0)},{f2(y0)} {f2(x1)},{f2(y1)}")

def arc(ops, color, cx, cy, rx, ry, a0, a1, w):
    ops.append(f"fill none stroke {color} stroke-width {f2(w)} stroke-linecap round "
               f"ellipse {f2(cx)},{f2(cy)} {f2(rx)},{f2(ry)} {f2(a0)},{f2(a1)}")

def star(ops, color, cx, cy, R, outline=None, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(2 * n):
        ang = rot + i * math.pi / n
        rad = R if i % 2 == 0 else R * 0.42
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    polygon(ops, color, pts, outline=outline, ow=0.4)

# ---- shared layout (so body + chest-mask stay pixel-aligned) -----------------
def layout(theta, phase, motion):
    fx, fy = vec(theta)
    sway = motion.get("sway", 0.0) * math.sin(phase)
    bob  = motion.get("bob", 0.0) * (0.5 - 0.5 * math.cos(2 * phase))
    lean = motion.get("lean", 0.0) * math.sin(phase)
    X0, Y0 = CX + sway, CY - bob
    # head leans toward facing during a "sniff"/peck
    HCx = X0 + lean * fx * 6
    HCy = (Y0 - 15) + lean * fy * KV * 6
    toward = fy  # +1 south(front), -1 north(back)
    chest_vis = max(0.0, 0.18 + 0.82 * (0.5 + 0.5 * fy))
    BCx = X0 + fx * 6
    BCy = Y0 + 5 + fy * KV * 6
    brx = 10.0 * max(0.30, chest_vis)
    bry = 15.0 * max(0.42, 0.5 + 0.5 * fy)
    return dict(fx=fx, fy=fy, X0=X0, Y0=Y0, HCx=HCx, HCy=HCy,
                toward=toward, chest_vis=chest_vis, BCx=BCx, BCy=BCy, brx=brx, bry=bry,
                foot=motion.get("foot", 0.0), phase=phase)

def cap_geom(L, theta):
    """Crown ellipse (cx,cy,rx,ry) + brim quad for the stylized cap, shared by the
    body layer (a thin dark rim) and the tint-mask layer (the player-color fill,
    inset so the rim shows). The brim points in the facing direction."""
    fx, fy = L["fx"], L["fy"]
    HCx, HCy = L["HCx"], L["HCy"]
    perp = (math.cos(theta), math.sin(theta))
    CCx, CCy = HCx + fx * 1.5, HCy - 6.5 + fy * KV * 1.5
    crown = (CCx, CCy, 9.4, 7.0)
    il = (CCx + perp[0] * 8.2, CCy + perp[1] * KV * 8.2)
    ir = (CCx - perp[0] * 8.2, CCy - perp[1] * KV * 8.2)
    ol = (CCx + fx * 11.5 + perp[0] * 6.4, CCy + fy * KV * 11.5 + perp[1] * KV * 6.4)
    orr = (CCx + fx * 11.5 - perp[0] * 6.4, CCy + fy * KV * 11.5 - perp[1] * KV * 6.4)
    return crown, [il, ol, orr, ir]

def inset_poly(pts, t=0.20):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return [(x * (1 - t) + cx * t, y * (1 - t) + cy * t) for x, y in pts]

# ---- body layer --------------------------------------------------------------
def body_ops(theta, phase, motion, gun=False):
    L = layout(theta, phase, motion)
    fx, fy = L["fx"], L["fy"]
    X0, Y0 = L["X0"], L["Y0"]
    HCx, HCy = L["HCx"], L["HCy"]
    perp = (math.cos(theta), math.sin(theta))   # screen-horizontal of the head
    toward = L["toward"]
    ops = []

    # paws (behind body; bottoms peek out below) -- two animated foot-blobs
    fa = L["foot"]
    fL, fR = math.sin(phase) * fa, math.sin(phase + math.pi) * fa
    ellipse(ops, CREAM, X0 - 7 + fL * 2.2, 81 - max(0, fL) * 2.0, 5.0, 3.2)
    ellipse(ops, CREAM, X0 + 7 + fR * 2.2, 81 - max(0, fR) * 2.0, 5.0, 3.2)

    # body (tan)
    ellipse(ops, FUR, X0, Y0, 18, 25)

    # chest (cream) -- the tinted region; only the rim shows past the mask layer
    if L["chest_vis"] > 0.18:
        ellipse(ops, CREAM, L["BCx"], L["BCy"], L["brx"], L["bry"])

    # curled tail -- the "this is a dog" read for the BACK views ONLY. In front
    # and side views a curl on the flank gets misread as a raised paw/hand (the
    # reported bug), so we draw it solely once the dog has turned away enough
    # (N/NE/NW; away>0.15). Its size and upward reach both grow with `away`.
    away = max(0.0, -fy)                            # 0 facing toward, 1 facing away
    if away > 0.15:
        side = -1.0 if fx >= 0 else 1.0             # trailing side
        tsz  = 0.34 + 0.9 * away                    # overall size
        rise = 0.22 + 0.78 * away                   # upward reach
        hx, hy = perp[0] * side, perp[1] * KV * side    # foreshortened "outward"
        bx, by = X0 + hx * 12, Y0 + 4 + hy * 12     # hip base of the tail
        curl = [(0, 0), (hx * 4 * tsz, -10 * rise), (hx * tsz, -18 * rise), (-hx * 6 * tsz, -19 * rise)]
        pts = [(bx + dx, by + dy) for dx, dy in curl]
        for (x0, y0), (x1, y1), w in zip(pts, pts[1:], (8.0, 6.6, 5.2)):
            capsule(ops, FUR_D, x0, y0, x1, y1, w + 1.4)   # subtle darker underlay
        for (x0, y0), (x1, y1), w in zip(pts, pts[1:], (6.4, 5.2, 3.8)):
            capsule(ops, FUR, x0, y0, x1, y1, w)           # tapering tan curl

    # head (tan) on top of the body
    circle(ops, FUR, HCx, HCy, 11)

    # ears (erect triangles); backs darker when facing away, cream inner when toward
    for sgn in (-1, 1):
        ebx = HCx + perp[0] * 6.5 * sgn
        eby = HCy - 6 + perp[1] * KV * 6.5 * sgn
        tip = (ebx + perp[0] * 2 * sgn, eby - 13)
        b1, b2 = (ebx - 4.0, eby + 2.5), (ebx + 4.0, eby + 2.5)
        polygon(ops, FUR_D if fy < -0.1 else FUR, [tip, b1, b2])
        if toward > -0.15:
            itip = (ebx + perp[0] * 1.5 * sgn, eby - 8.5)
            polygon(ops, CREAM, [itip, (ebx - 2.0, eby + 1.2), (ebx + 2.0, eby + 1.2)])

    # stylized cap on the crown -- only a dark rim/brim is on the body layer; the
    # fill is the player color on the tint-mask layer. Drawn over the ears so the
    # dog "wears" it with the ear tips poking up behind. Brim points where it faces.
    crown, brim = cap_geom(L, theta)
    polygon(ops, CAP_EDGE, brim)
    ellipse(ops, CAP_EDGE, *crown)

    # muzzle (cream) + nose (black), front/3-4 only
    vb = max(0.0, 0.5 + 0.5 * fy + 0.30 * abs(fx))
    if vb > 0.22:
        m = min(1.1, max(0.45, vb))
        mcx, mcy = HCx + fx * 4, HCy + fy * KV * 4 + 4
        ellipse(ops, CREAM, mcx, mcy, 5.6 * m, 4.6 * m)
        nx, ny = HCx + fx * 7, HCy + fy * KV * 7 + 4
        circle(ops, NOSE, nx, ny, 2.3)

    # eyes (small, dark) + cream brow dots
    def eye(ex, ey):
        circle(ops, CREAM, ex, ey, 2.2)
        circle(ops, EYE, ex + fx * 0.6, ey + fy * KV * 0.6, 1.7)
    if toward > 0.05:                       # front: two eyes
        for sgn in (-1, 1):
            ex = HCx + fx * 2 + perp[0] * 5 * sgn
            ey = HCy + fy * KV * 2 + perp[1] * KV * 5 * sgn - 1
            eye(ex, ey)
    elif toward > -0.35:                     # side/3-4: single near eye
        eye(HCx + fx * 5, HCy + fy * KV * 5 - 1)
    # else facing away: no eyes

    # water pistol (toy, green) held toward facing
    if gun:
        HPx = X0 + fx * 14 + 2
        HPy = Y0 + 7 + fy * KV * 12
        bx1 = HPx + fx * 15
        by1 = HPy + fy * KV * 15
        capsule(ops, FUR, X0 + fx * 7, Y0 + 5, HPx, HPy, 5.5)    # paw/arm holding it
        capsule(ops, GREEN_D, HPx - fx * 4, HPy - fy * KV * 4, HPx + fx * 2, HPy + fy * KV * 2, 8.5)  # tank
        capsule(ops, GREEN_D, HPx, HPy, bx1, by1, 8.0)            # barrel outline
        capsule(ops, GREEN, HPx, HPy, bx1, by1, 5.5)             # barrel
        capsule(ops, GREEN, HPx, HPy, HPx, HPy + 6, 5.0)         # grip
        circle(ops, ORANGE, bx1, by1, 2.6)                       # nozzle
    return ops

# ---- chest mask layer (team color) ------------------------------------------
def mask_ops(theta, phase, motion):
    L = layout(theta, phase, motion)
    ops = []
    if L["chest_vis"] > 0.18:
        # inset slightly so a cream chest rim remains on the body layer
        ellipse(ops, WHITE, L["BCx"], L["BCy"], L["brx"] - 1.0, L["bry"] - 1.5)
    # cap fill = player color (inset from the body's dark cap so the rim shows)
    crown, brim = cap_geom(L, theta)
    cx, cy, rx, ry = crown
    ellipse(ops, WHITE, cx, cy, rx - 1.0, ry - 1.0)
    polygon(ops, WHITE, inset_poly(brim))
    return ops

# ---- emblem layer (fixed gold; rendered ABOVE the tinted cap, never tinted) --
def hammer_sickle(ops, color, cx, cy, s):
    arc(ops, color, cx - s * 0.2, cy, s, s, 35, 320, 1.1)                       # sickle blade
    capsule(ops, color, cx - s * 0.7, cy + s * 0.9, cx + s * 0.8, cy - s * 0.7, 1.1)  # hammer handle
    capsule(ops, color, cx + s * 0.2, cy - s * 1.0, cx + s * 1.0, cy - s * 0.2, 1.1)  # hammer head

def emblem_ops(theta, phase, motion):
    L = layout(theta, phase, motion)
    fx, fy, toward = L["fx"], L["fy"], L["toward"]
    ops = []
    if toward <= -0.1:           # cap front is hidden when facing away
        return ops
    (CCx, CCy, _, _), _ = cap_geom(L, theta)
    ex = CCx + fx * 1.5
    ey = CCy + fy * KV * 1.5
    star(ops, GOLD, ex, ey, 4.2, outline=GOLD_D)            # big gold star (reads at game zoom)
    hammer_sickle(ops, GOLD_D, ex, ey + 0.3, 1.7)          # hammer & sickle inside it (combined badge)
    return ops

# ---- rendering ---------------------------------------------------------------
def render_frame(ops, path):
    cmd = ["magick", "-size", f"{FW}x{FH}", "xc:none"]
    if ops:                      # emblem frames are empty when facing away
        cmd += ["-draw", " ".join(ops)]
    cmd += ["-depth", "8", "PNG32:" + path]
    subprocess.run(cmd, check=True)

def hcat(paths, out):
    subprocess.run(["magick"] + paths + ["+append", "PNG32:" + out], check=True)

def vcat(paths, out):
    subprocess.run(["magick"] + paths + ["-append", "PNG32:" + out], check=True)

def build_sheet(out_path, dirs, frames, motion, gun=False, mask=False, emblem=False, south_only=False):
    """rows = directions (0=N clockwise), cols = frames. south_only tiles the
    south(front) pose across every direction (used for running_with_gun)."""
    tmp = tempfile.mkdtemp(prefix="dog_")
    rows = []
    for d in range(dirs):
        theta = math.pi if south_only else (d / dirs) * 2 * math.pi
        cols = []
        for f in range(frames):
            phase = (f / frames) * 2 * math.pi
            if mask:
                ops = mask_ops(theta, phase, motion)
            elif emblem:
                ops = emblem_ops(theta, phase, motion)
            else:
                ops = body_ops(theta, phase, motion, gun=gun)
            fp = os.path.join(tmp, f"d{d}_f{f}.png")
            render_frame(ops, fp)
            cols.append(fp)
        rp = os.path.join(tmp, f"row{d}.png")
        hcat(cols, rp)
        rows.append(rp)
    vcat(rows, out_path)
    dim = subprocess.run(["magick", "identify", "-format", "%wx%h", out_path],
                         capture_output=True, text=True).stdout
    print(f"  {os.path.basename(out_path)}: {dim}  (dirs={dirs} frames={frames})")

# Animation specs: (frames, motion, gun, dirs, south_only)
RUN_MOTION   = dict(sway=3.0, bob=1.6, foot=2.4)
IDLE_MOTION  = dict(sway=0.6, bob=1.0, foot=0.4)
MINE_MOTION  = dict(sway=0.8, bob=0.6, foot=0.4, lean=1.4)

def cmd_build():
    os.makedirs(GFX, exist_ok=True)
    print("Building sheets ->", GFX)
    # per state: body (untinted) + mask (player-tinted chest & cap) + emblem (gold)
    specs = [
        ("run",     8, 8, RUN_MOTION,  dict()),
        ("idle",    8, 4, IDLE_MOTION, dict()),
        ("mine",    8, 6, MINE_MOTION, dict()),
        ("idlegun", 8, 4, IDLE_MOTION, dict(gun=True)),
        ("rungun", 18, 8, RUN_MOTION,  dict(gun=True, south_only=True)),
    ]
    for name, dirs, frames, motion, extra in specs:
        so = extra.get("south_only", False)
        build_sheet(os.path.join(GFX, f"{name}.png"),        dirs, frames, motion, **extra)
        build_sheet(os.path.join(GFX, f"{name}_mask.png"),   dirs, frames, motion, mask=True,   south_only=so)
        build_sheet(os.path.join(GFX, f"{name}_emblem.png"), dirs, frames, motion, emblem=True, south_only=so)
    print("done.")

# A sample player color for representative previews -- the cap & chest take this;
# the gold star + hammer & sickle stay gold regardless.
SAMPLE_TINT = "rgb(196,40,40)"

def render_preview(theta, phase, motion, gun, path):
    """body + sample-tinted mask + gold emblem, composited (preview only)."""
    tmp = tempfile.mkdtemp(prefix="dog_pv_")
    b = os.path.join(tmp, "b.png"); m = os.path.join(tmp, "m.png"); e = os.path.join(tmp, "e.png")
    render_frame(body_ops(theta, phase, motion, gun=gun), b)
    render_frame(mask_ops(theta, phase, motion), m)
    render_frame(emblem_ops(theta, phase, motion), e)
    subprocess.run(["magick", b,
                    "(", m, "-fill", SAMPLE_TINT, "-colorize", "100", ")", "-compose", "over", "-composite",
                    e, "-compose", "over", "-composite", "PNG32:" + path], check=True)

def cmd_contact():
    tmp = tempfile.mkdtemp(prefix="dog_contact_")
    # 8 directions static (no gun), then 8 directions with gun
    for tag, gun in (("walk", False), ("gun", True)):
        cols = []
        for d in range(8):
            theta = (d / 8) * 2 * math.pi
            fp = os.path.join(tmp, f"{tag}_{d}.png")
            render_preview(theta, 0.0, IDLE_MOTION, gun, fp)
            cols.append(fp)
        out = f"/tmp/dog_contact_{tag}.png"
        subprocess.run(["magick"] + cols + ["+append", "-bordercolor", "gray70",
                        "-border", "2", "-background", "gray40", "-alpha", "remove",
                        "-alpha", "off", "-filter", "point", "-resize", "300%",
                        "PNG32:" + out], check=True)
        print("wrote", out, "(dirs: N NE E SE S SW W NW)")
    # waddle filmstrip: south, 8 frames
    cols = []
    for f in range(8):
        phase = (f / 8) * 2 * math.pi
        fp = os.path.join(tmp, f"film_{f}.png")
        render_preview(math.pi, phase, RUN_MOTION, False, fp)
        cols.append(fp)
    out = "/tmp/dog_contact_film.png"
    subprocess.run(["magick"] + cols + ["+append", "-bordercolor", "gray70",
                    "-border", "2", "-background", "gray40", "-alpha", "remove",
                    "-alpha", "off", "-filter", "point", "-resize", "300%",
                    "PNG32:" + out], check=True)
    print("wrote", out, "(south waddle, 8 frames)")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "contact"
    {"contact": cmd_contact, "build": cmd_build}[cmd]()
