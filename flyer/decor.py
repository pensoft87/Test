"""Second pass over the flyer: real logo, a background behind the bottles (variant A/B/C), and the
'Precio de introducción' seal.  Runs build.py first, so the whole flyer is:

    python3 decor.py [out.png] [A|B|C]   # -> flyer-harmonie.png, variant C
"""
import math, os, subprocess, sys, tempfile
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC = 'src'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'flyer-harmonie.png'
VARIANT = sys.argv[2] if len(sys.argv) > 2 else 'C'
IN = os.path.join(tempfile.mkdtemp(), 'base.png')
subprocess.run([sys.executable, 'build.py', SRC, IN], check=True)
GOLD_HI, GOLD, GOLD_LO = (255, 236, 180), (222, 182, 108), (160, 112, 48)


def font(name, size, weight):
    f = ImageFont.truetype(f'{SRC}/{name}', size)
    f.set_variation_by_name(weight)
    return f


def smooth_bg(rgb, is_bg, scale=8):
    """Estimate a smooth background under foreground pixels (downscaled inpaint)."""
    h, w = is_bg.shape
    small = cv2.resize(rgb, (w // scale, h // scale), interpolation=cv2.INTER_AREA)
    m = cv2.resize((~is_bg).astype(np.float32), (w // scale, h // scale), interpolation=cv2.INTER_AREA)
    m = cv2.dilate((m > 0).astype(np.uint8) * 255, np.ones((3, 3), np.uint8))
    small = cv2.inpaint(small, m, 5, cv2.INPAINT_TELEA)
    return cv2.GaussianBlur(cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC), (0, 0), 3).astype(np.float32)


flyer = np.array(Image.open(IN).convert('RGB'))
bottles_ref = flyer.copy()          # bottles as they look now, pasted back on top at the end

# ---------------------------------------------------------------- 1. logo
# remove the old logo (butterfly + lavender sprig + wordmark)
LX0, LY0, LX1, LY1 = 86, 10, 470, 226
reg = flyer[LY0:LY1, LX0:LX1].astype(np.float32)
bg_guess = np.array([252, 241, 234], np.float32)
diff = np.abs(reg - bg_guess).max(2)
is_bg = diff < 18
bg = smooth_bg(reg.astype(np.uint8), is_bg)
fg = np.abs(reg - bg).max(2) > 10
fg = cv2.dilate(fg.astype(np.uint8), np.ones((7, 7), np.uint8))
clean = bg * fg[..., None] + reg * (1 - fg[..., None])
flyer[LY0:LY1, LX0:LX1] = cv2.GaussianBlur(clean, (0, 0), 0.6).astype(np.uint8) * fg[..., None] + \
    flyer[LY0:LY1, LX0:LX1] * (1 - fg[..., None])

# cut the real logo out of the label artwork
lab = np.array(Image.open(f'{SRC}/2.webp').convert('RGB'))
CX0, CY0, CX1, CY1 = 546, 26, 1052, 402
crop = lab[CY0:CY1, CX0:CX1].astype(np.float32)
lbg = smooth_bg(crop.astype(np.uint8), np.abs(crop - np.array([254, 249, 228])).max(2) < 22)
d = np.abs(crop - lbg).max(2)
alpha = np.clip((d - 10) / 55, 0, 1)
a0 = np.maximum(alpha, 1e-3)[..., None]
fgc = np.clip((crop - (1 - a0) * lbg) / a0, 0, 255)      # un-mixed logo colour
# keep only the logo itself: a hand-traced outline that stays inside the label's gold oval
keep = Image.new('L', (CX1 - CX0, CY1 - CY0), 0)
poly = [(551, 230), (660, 215), (668, 120), (695, 62), (728, 46), (780, 58), (860, 128), (872, 212),
        (1015, 236), (1044, 280), (1044, 340), (1000, 346), (996, 397), (598, 397), (588, 352), (546, 352)]
ImageDraw.Draw(keep).polygon([(x - CX0, y - CY0) for x, y in poly], fill=255)
alpha *= np.array(keep.filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255
alpha[alpha < 0.06] = 0
alpha = cv2.GaussianBlur(alpha, (0, 0), 0.5)

# trim to the logo's own bounding box, then size it to the space above the headline and
# line its left edge up with the "P" of PEINA (x=80; the headline starts at y=257)
ys, xs = np.where(alpha > 0.05)
crop, fgc, alpha = (v[ys.min():ys.max() + 1, xs.min():xs.max() + 1] for v in (crop, fgc, alpha))
oy, bottom, ox = 6, 243, 80
scale = (bottom - oy) / crop.shape[0]
nw, nh = int(crop.shape[1] * scale), int(crop.shape[0] * scale)
dst = flyer[oy:oy + nh, ox:ox + nw].astype(np.float32)
a_s = cv2.resize(alpha, (nw, nh), interpolation=cv2.INTER_AREA)[..., None]
prem = cv2.resize(fgc * alpha[..., None], (nw, nh), interpolation=cv2.INTER_AREA)
out = prem + (1 - a_s) * dst
flyer[oy:oy + nh, ox:ox + nw] = np.clip(out, 0, 255).astype(np.uint8)

# ---------------------------------------------------------------- helpers for the overlays
SS = 3  # supersampling for everything drawn by hand


def lerp(c0, c1, t):
    t = np.asarray(t, np.float32)[..., None]
    return np.asarray(c0, np.float32) * (1 - t) + np.asarray(c1, np.float32) * t


def comp(base, rgb, a):
    """alpha-composite float rgb (h,w,3) with alpha (h,w) onto uint8 base, in place."""
    a = a[..., None]
    base[:] = np.clip(rgb * a + base.astype(np.float32) * (1 - a), 0, 255).astype(np.uint8)


def mask(size, draw_fn):
    """Draw a shape at SS x and return a downsampled float alpha of `size`."""
    w, h = size
    m = Image.new('L', (w * SS, h * SS), 0)
    draw_fn(ImageDraw.Draw(m), SS)
    return np.array(m.resize((w, h), Image.LANCZOS), np.float32) / 255


def star_pts(cx, cy, r_out, r_in, n, rot=0.0):
    pts = []
    for k in range(2 * n):
        r = r_out if k % 2 == 0 else r_in
        a = rot + math.pi * k / n - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


H, Wd = flyer.shape[:2]
YY, XX = np.mgrid[0:H, 0:Wd].astype(np.float32)

# ---------------------------------------------------------------- 2. bottle silhouettes
LEFTS = [133, 363, 598, 828]
CXS = [l + 79.5 for l in LEFTS]
SHOULDER = [(741, 32), (745, 34), (750, 41), (755, 51), (760, 61), (765, 67), (770, 71), (780, 75.5),
            (790, 78), (800, 79.5), (1052, 79.5)]


def half_width(y):
    if y < 625:
        return 0
    if y < 645:
        return math.sqrt(max(0, 19.5 ** 2 - (645 - y) ** 2))
    if y < 686:
        return 19.5
    if y < 741:
        return 38.5
    if y <= 1052:
        ys, ws = zip(*SHOULDER)
        return float(np.interp(y, ys, ws))
    if y < 1062.5:
        return 69.5 + math.sqrt(max(0, 100 - (y - 1052) ** 2))
    return 0


def bottle_mask():
    def draw(d, s):
        for cx in CXS:
            for yy in range(627 * s, 1064 * s):
                hw = half_width(yy / s) - 3.0
                if hw > 0:
                    d.line([((cx - hw) * s, yy), ((cx + hw) * s, yy)], fill=255)
    return mask((Wd, H), draw)


bmask = bottle_mask()
# the source render has a pale rim around the glass (old background bleeding in): along the
# edge of the amber glass (shoulders and base, not the cap or label) drop light pixels
ring = (bmask > 0) & (cv2.erode((bmask > 0.99).astype(np.uint8), np.ones((9, 9), np.uint8)) == 0)
glass = ((YY > 741) & (YY < 802)) | (YY > 1039)
lum = bottles_ref.astype(np.float32) @ np.array([0.3, 0.59, 0.11], np.float32)
bmask = np.where(ring & glass, bmask * np.clip((190 - lum) / 50, 0, 1), bmask)

# ---------------------------------------------------------------- 3. background behind the bottles
# three looks to choose from:  A = bokeh lights,  B = trail of gold glitter,  C = half-moon with gold rings
rng = np.random.default_rng(7)
SHELF = 1037
below_shelf = np.clip((SHELF - YY) / 4, 0, 1)


def smoothstep(e0, e1, x):
    x = np.clip((x - e0) / (e1 - e0), 0, 1)
    return x * x * (3 - 2 * x)


def screen(rgb, a):
    """Screen-blend light onto the flyer (shows on the dark band), plus a light tint (shows on the pale top)."""
    a = np.clip(a, 0, 1) * below_shelf
    comp(flyer, rgb, a * 0.45)
    base = flyer.astype(np.float32) / 255
    flyer[:] = np.clip(255 * (1 - (1 - base) * (1 - rgb / 255 * a[..., None])), 0, 255).astype(np.uint8)


def wash(color, cx, cy, rx, ry, strength):
    comp(flyer, np.full((H, Wd, 3), color, np.float32),
         np.exp(-(((XX - cx) / rx) ** 2 + ((YY - cy) / ry) ** 2)) * strength * below_shelf)


def bokeh():
    wash((214, 172, 236), 572, 900, 560, 230, 0.45)
    layer = np.zeros((H, Wd, 3), np.float32)
    alpha = np.zeros((H, Wd), np.float32)
    cols = [(255, 206, 120), (255, 206, 120), (178, 126, 246), (244, 128, 200), (255, 246, 236)]
    for _ in range(170):
        r = float(rng.choice([rng.uniform(5, 12), rng.uniform(12, 24), rng.uniform(24, 38)], p=[0.5, 0.35, 0.15]))
        x = rng.uniform(70, 1050)
        y = SHELF - abs(rng.normal(0, 190)) - r * 0.3
        if y < 600:
            continue
        col = np.array(cols[rng.integers(0, len(cols))], np.float32)
        x0, y0, x1, y1 = int(x - r - 12), int(max(y - r - 12, 0)), int(x + r + 12), int(min(y + r + 12, H))
        x0, x1 = max(x0, 0), min(x1, Wd)
        d = np.hypot(XX[y0:y1, x0:x1] - x, YY[y0:y1, x0:x1] - y) / r
        disc = smoothstep(1.0, 1.0 - 2.2 / r - 0.04 * r / 10, d)       # larger = softer edge
        disc = disc * (0.55 + 0.45 * smoothstep(0.55, 0.97, d))         # brighter rim, like a lens
        disc *= rng.uniform(0.45, 0.9)
        alpha[y0:y1, x0:x1] = 1 - (1 - alpha[y0:y1, x0:x1]) * (1 - disc)
        layer[y0:y1, x0:x1] = layer[y0:y1, x0:x1] * (1 - disc[..., None]) + col * disc[..., None]
    comp(flyer, layer, alpha * 0.5 * below_shelf)          # colour shows on the pale top
    screen(layer, alpha * 0.8)


def glitter():
    def bez(t, p):
        p = np.asarray(p, np.float32)
        return ((1 - t) ** 3)[:, None] * p[0] + (3 * (1 - t) ** 2 * t)[:, None] * p[1] + \
               (3 * (1 - t) * t * t)[:, None] * p[2] + (t ** 3)[:, None] * p[3]
    trails = [([(50, 1010), (250, 540), (820, 560), (1080, 900)], 8000, 26),
              ([(90, 1030), (330, 640), (760, 620), (1050, 980)], 3500, 12)]
    layer = Image.new('RGBA', (Wd * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    glow = np.zeros((H, Wd), np.float32)
    for pts, n, spread in trails:
        t = np.sort(rng.uniform(0, 1, n))
        c = bez(t, pts)
        tang = np.gradient(c, axis=0)
        nrm = np.stack([-tang[:, 1], tang[:, 0]], 1) / (np.linalg.norm(tang, axis=1, keepdims=True) + 1e-6)
        width = spread * (0.35 + np.sin(math.pi * t) ** 0.7)
        p = c + nrm * rng.normal(0, 1, n)[:, None] * width[:, None]
        for (x, y), tt in zip(p, t):
            if y > SHELF - 2:
                continue
            r = float(rng.choice([0.8, 1.2, 1.7, 2.5], p=[0.4, 0.32, 0.2, 0.08]))
            g = rng.uniform(0, 1)
            col = (255, int(190 + 60 * g), int(90 + 150 * g ** 2), int(rng.uniform(190, 255)))
            if rng.uniform() < 0.06:
                col = (214, 182, 255, 230)                              # a few lilac flecks
            d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=col)
        line = np.zeros((H, Wd), np.float32)
        cc = bez(np.linspace(0, 1, 600), pts).astype(np.int32)
        cv2.polylines(line, [cc], False, 1.0, thickness=int(spread * 0.9))
        glow += cv2.GaussianBlur(line, (0, 0), spread * 0.9)
    screen(np.full((H, Wd, 3), (255, 222, 160), np.float32), np.clip(glow, 0, 1) * 0.75)
    arr_l = np.array(layer.resize((Wd, H), Image.LANCZOS), np.float32)
    comp(flyer, arr_l[..., :3], arr_l[..., 3] / 255 * below_shelf)
    for _ in range(22):                                                  # sparkles riding the trail
        pts, _, _ = trails[0]
        t = rng.uniform(0.05, 0.95)
        x, y = bez(np.array([t]), pts)[0] + rng.normal(0, 12, 2)
        if y > SHELF - 10:
            continue
        r = rng.uniform(5, 11)
        m = mask((Wd, H), lambda dd, s, x=x, y=y, r=r: dd.polygon([(px * s, py * s) for px, py in star_pts(x, y, r, r * 0.18, 4)], fill=255))
        comp(flyer, np.full((H, Wd, 3), (255, 248, 222), np.float32), np.clip(m + cv2.GaussianBlur(m, (0, 0), r * 0.8) * 0.7, 0, 1))


def leaf_img(length, width, color, s=SS):
    """One lilac leaf (pointing +x) as an RGBA image, with a pale midrib and side veins."""
    L, Wl = length * s, width * s
    img = Image.new('RGBA', (int(L) + 4, int(2 * Wl) + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    t = np.linspace(0, 1, 40)
    half = Wl * np.sin(math.pi * t) ** 0.75 * (1 - 0.25 * t)
    top = [(2 + L * a, 2 + Wl - h) for a, h in zip(t, half)]
    bot = [(2 + L * a, 2 + Wl + h) for a, h in zip(t[::-1], half[::-1])]
    edge = tuple(int(c * 0.82) for c in color[:3]) + (color[3],)
    d.polygon(top + bot, fill=color, outline=edge)
    vein = (236, 222, 252, int(color[3] * 0.8))
    d.line([(2, 2 + Wl), (2 + L * 0.96, 2 + Wl)], fill=vein, width=max(1, int(0.9 * s)))
    for a in np.linspace(0.18, 0.78, 5):
        x0 = 2 + L * a
        hh = Wl * math.sin(math.pi * a) ** 0.75 * (1 - 0.25 * a) * 0.8
        for sg in (-1, 1):
            d.line([(x0, 2 + Wl), (x0 + L * 0.12, 2 + Wl + sg * hh)], fill=vein, width=max(1, int(0.6 * s)))
    return img


def lilac_leaves(cx, cy, r, disc):
    """Tone-on-tone sprigs of lilac leaves filling the half-moon, like the labels' leaf pattern."""
    layer = Image.new('RGBA', (Wd * SS, H * SS), (0, 0, 0, 0))
    palette = [(150, 100, 204), (172, 128, 222), (196, 162, 236), (132, 86, 192), (214, 186, 244)]

    def put_leaf(x, y, ang, length):
        col = palette[rng.integers(0, len(palette))] + (int(rng.uniform(150, 230)),)
        im = leaf_img(length, length * rng.uniform(0.26, 0.34), col)
        im = im.rotate(-math.degrees(ang), resample=Image.BICUBIC, expand=True)
        # rotate() keeps the image centre fixed; the leaf base was at the left-middle
        bx = x * SS - im.width / 2 + math.cos(ang) * (length * SS / 2)
        by = y * SS - im.height / 2 + math.sin(ang) * (length * SS / 2)
        layer.alpha_composite(im, (int(bx), int(by)))

    sprigs = 16
    for k in range(sprigs):
        bx = cx - r * 0.85 + 2 * r * 0.85 * (k + rng.uniform(0.2, 0.8)) / sprigs
        ang0 = -math.pi / 2 + (bx - cx) / r * 0.9 + rng.normal(0, 0.12)
        length = rng.uniform(220, 330)
        bend = rng.normal(0, 0.25)
        pts = []
        for i in range(60):
            t = i / 59
            a = ang0 + bend * t
            if not pts:
                pts.append((bx, SHELF + 4))
            px, py = pts[-1]
            pts.append((px + math.cos(a) * length / 59, py + math.sin(a) * length / 59))
        ImageDraw.Draw(layer).line([(x * SS, y * SS) for x, y in pts], fill=(140, 96, 190, 200), width=int(1.4 * SS))
        for j, i in enumerate(range(6, 60, 6)):
            x, y = pts[i]
            a = ang0 + bend * i / 59
            side = 1 if j % 2 else -1
            put_leaf(x, y, a + side * rng.uniform(0.6, 0.95), rng.uniform(40, 58) * (1 - 0.35 * i / 59))
        put_leaf(*pts[-1], ang0 + bend, rng.uniform(36, 46))
    for _ in range(28):                                   # loose leaves filling the upper arc
        a = rng.uniform(math.pi * 1.08, math.pi * 1.92)
        rad = rng.uniform(0.45, 0.92) * r
        put_leaf(cx + rad * math.cos(a), cy + rad * math.sin(a), rng.uniform(0, 2 * math.pi), rng.uniform(34, 52))
    arr = np.array(layer.resize((Wd, H), Image.LANCZOS), np.float32)
    inner = smoothstep(r - 4, r - 12, np.hypot(XX - cx, YY - cy))
    comp(flyer, arr[..., :3], arr[..., 3] / 255 * disc * inner * 0.8)


def moon():
    cx, cy, r = 572, 1005, 330
    rr = np.hypot(XX - cx, YY - cy)
    disc = smoothstep(r + 0.8, r - 0.8, rr) * below_shelf
    fillc = lerp((255, 244, 250), (222, 182, 238), smoothstep(0, r, rr))
    fillc = lerp(fillc, (246, 214, 236), 0.35 * smoothstep(0.3, 1, (XX - cx) / r + 0.5))
    # soft shadow, then the disc
    sh = cv2.GaussianBlur(np.roll(disc, (8, 6), (0, 1)), (0, 0), 10) * 0.35
    comp(flyer, np.full((H, Wd, 3), (60, 14, 60), np.float32), sh)
    comp(flyer, fillc, disc * 0.95)
    lilac_leaves(cx, cy, r, disc)
    gold = lerp(GOLD_HI, GOLD_LO, smoothstep(cy - r, cy, YY))
    for rc, ccx, ccy, w in ((r, cx, cy, 3.0), (r + 22, cx + 26, cy - 6, 1.4), (r - 16, cx, cy, 0.9)):
        ring = np.exp(-((np.hypot(XX - ccx, YY - ccy) - rc) / w) ** 2) * below_shelf
        comp(flyer, gold, ring)
    # small gold beads along the outer ring
    for k in range(17):
        ang = math.pi + math.pi * (k + 0.5) / 17
        x, y = cx + 26 + (r + 22) * math.cos(ang), cy - 6 + (r + 22) * math.sin(ang)
        if y > SHELF - 6:
            continue
        rad = 3.2 if k % 4 == 0 else 1.8
        m = mask((Wd, H), lambda dd, s, x=x, y=y, rad=rad: dd.ellipse([(x - rad) * s, (y - rad) * s, (x + rad) * s, (y + rad) * s], fill=255))
        comp(flyer, gold, m)


{'A': bokeh, 'B': glitter, 'C': moon}[VARIANT]()

# contact shadows on the shelf
shadow = np.zeros((H, Wd), np.float32)
for cx in CXS:
    shadow += np.exp(-(((XX - cx) / 92) ** 2 + ((YY - 1060) / 7) ** 2))
comp(flyer, np.zeros((H, Wd, 3), np.float32) + (50, 20, 30), np.clip(shadow, 0, 1) * 0.45)

# ---------------------------------------------------------------- 4. seal "Precio de introducción"
SCX, SCY = 992, 562
SZ = 340
seal = np.zeros((SZ * SS, SZ * SS, 4), np.float32)
c = SZ * SS / 2
gy, gx = np.mgrid[0:SZ * SS, 0:SZ * SS].astype(np.float32)
rr = np.hypot(gx - c, gy - c) / SS


def layer(draw_fn):
    m = Image.new('L', (SZ * SS, SZ * SS), 0)
    draw_fn(ImageDraw.Draw(m))
    return np.array(m, np.float32) / 255


def put(rgb, a):
    a = a[..., None]
    seal[..., :3] = rgb * a + seal[..., :3] * (1 - a)
    seal[..., 3:] = a + seal[..., 3:] * (1 - a)


def P(x, y):  # seal-local coords (centre 0,0) -> supersampled canvas
    return (c + x * SS, c + y * SS)


# ribbon tails
MAG, MAG_D = (214, 32, 124), (150, 14, 84)
for side in (-1, 1):
    ang = math.radians(24 * side)
    def tail(d, ang=ang):
        w, L = 24, 150
        ux, uy = math.sin(ang), math.cos(ang)
        px, py = uy, -ux
        base = [(px * -w, py * -w), (px * w, py * w)]
        pts = [base[0], base[1],
               (px * w + ux * L, py * w + uy * L),
               (ux * (L - 22), uy * (L - 22)),
               (px * -w + ux * L, py * -w + uy * L)]
        d.polygon([P(x, y) for x, y in pts], fill=255)
    a = layer(tail)
    put(lerp(MAG, MAG_D, np.clip((gy / SS - SZ / 2) / 130, 0, 1)), a)
    edge = cv2.morphologyEx(a, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))
    put(np.full(a.shape + (3,), GOLD, np.float32), np.clip(edge, 0, 1) * 0.9)

# scalloped gold rosette
ros = layer(lambda d: d.polygon([P(x, y) for x, y in star_pts(0, 0, 112, 101, 32)], fill=255))
ros = np.maximum(ros, layer(lambda d: d.ellipse([*P(-104, -104), *P(104, 104)], fill=255)))
ang = np.arctan2(gy - c, gx - c)
gold_rad = lerp(GOLD_HI, GOLD_LO, np.clip(0.5 + 0.5 * np.sin(ang * 2 + 0.6) * 0.8 + (rr - 95) / 60, 0, 1))
put(gold_rad, ros)
# magenta disc
disc = layer(lambda d: d.ellipse([*P(-92, -92), *P(92, 92)], fill=255))
put(lerp((236, 70, 150), (168, 16, 96), np.clip((gy - c) / (SS * 180) + 0.5 + (rr / 92) * 0.25, 0, 1)), disc)
put(np.full(disc.shape + (3,), GOLD_HI, np.float32),
    layer(lambda d: d.ellipse([*P(-92, -92), *P(92, 92)], outline=255, width=3 * SS)))
# dotted inner ring
dots = layer(lambda d: [d.ellipse([*P(84 * math.cos(t) - 1.6, 84 * math.sin(t) - 1.6), *P(84 * math.cos(t) + 1.6, 84 * math.sin(t) + 1.6)], fill=255)
                        for t in np.linspace(0, 2 * math.pi, 64, endpoint=False)])
put(np.full(dots.shape + (3,), GOLD_HI, np.float32), dots * 0.9)
# glossy top highlight
gloss = np.clip(1 - np.hypot((gx - c) / (SS * 80), (gy - c + SS * 48) / (SS * 42)), 0, 1) * disc * 0.22
put(np.full(gloss.shape + (3,), 255, np.float32), gloss)

simg = Image.fromarray(np.clip(seal, 0, 255).astype(np.uint8) if False else
                       np.dstack([np.clip(seal[..., :3], 0, 255), np.clip(seal[..., 3:] * 255, 0, 255)]).astype(np.uint8), 'RGBA')
sd = ImageDraw.Draw(simg)


def ctext_s(y, text, f, fill, spacing=0):
    if spacing:
        widths = [sd.textlength(ch, font=f) for ch in text]
        total = sum(widths) + spacing * SS * (len(text) - 1)
        x = c - total / 2
        for ch, w in zip(text, widths):
            sd.text((x, c + y * SS), ch, font=f, fill=fill, anchor='ls')
            x += w + spacing * SS
    else:
        sd.text((c, c + y * SS), text, font=f, fill=fill, anchor='ms')


for k, x in enumerate((-22, 0, 22)):
    r = 7 if x == 0 else 5
    sd.polygon([P(px, py) for px, py in star_pts(x, -50 - (3 if x == 0 else 0), r, r * 0.42, 5)], fill=GOLD_HI)
ctext_s(-6, 'Precio de', font('DancingScript.ttf', 38 * SS, 'Bold'), (255, 255, 255))
ctext_s(22, 'INTRODUCCIÓN', font('Montserrat.ttf', 15 * SS, 'ExtraBold'), GOLD_HI, spacing=0.6)
sd.line([P(-46, 36), P(46, 36)], fill=GOLD_HI, width=2 * SS)
sd.polygon([P(px, py) for px, py in star_pts(0, 36, 6, 2, 4)], fill=GOLD_HI)
for x in (-58, 58):
    sd.polygon([P(px, py) for px, py in star_pts(x, 36, 3.5, 1.2, 4)], fill=GOLD_HI)

simg = simg.rotate(-11, resample=Image.BICUBIC, center=(c, c)).resize((SZ, SZ), Image.LANCZOS)
sa = np.array(simg, np.float32)
x0, y0 = SCX - SZ // 2, SCY - SZ // 2
# drop shadow
shad = cv2.GaussianBlur(sa[..., 3] / 255, (0, 0), 6)
shad = np.roll(shad, (7, 4), (0, 1))
region = flyer[y0:y0 + SZ, x0:min(x0 + SZ, Wd)]
wcut = region.shape[1]
comp(region, np.zeros((SZ, wcut, 3), np.float32) + (60, 10, 40), shad[:, :wcut] * 0.45)
comp(region, sa[:, :wcut, :3], sa[:, :wcut, 3] / 255)

# ---------------------------------------------------------------- 5. bottles back on top
comp(flyer, bottles_ref.astype(np.float32), bmask)

Image.fromarray(flyer).save(OUT)
print('ok')
