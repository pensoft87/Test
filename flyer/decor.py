"""Second pass over the flyer: real logo, backdrop behind the bottles, and the
'Precio de introducción' seal.  Runs build.py first, so the whole flyer is:

    python3 decor.py            # -> flyer-harmonie.png
"""
import math, os, subprocess, sys, tempfile
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC = 'src'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'flyer-harmonie.png'
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

scale = 0.6
nw, nh = int(crop.shape[1] * scale), int(crop.shape[0] * scale)
ox, oy = 278 - nw // 2, 14
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
            for yy in range(620 * s, 1064 * s):
                hw = half_width(yy / s) - 0.6
                if hw > 0:
                    d.line([((cx - hw) * s, yy), ((cx + hw) * s, yy)], fill=255)
    return mask((Wd, H), draw)


bmask = bottle_mask()

# ---------------------------------------------------------------- 3. backdrop behind the bottles
rng = np.random.default_rng(7)
SHELF = 1037
AR, ATOP = 101, 666                        # arch half-width and top
tints = [((252, 242, 255), (211, 186, 233)),   # lavender  - nutritivo
         ((255, 249, 238), (236, 213, 178)),   # champagne - protección
         ((247, 235, 252), (196, 164, 222)),   # violet    - fortalecimiento
         ((255, 247, 224), (230, 197, 132))]   # gold      - intensivo


def arch_draw(cx, inset=0.0, width=0):
    def draw(d, s):
        r = AR - inset
        top = ATOP + inset
        box = [(cx - r) * s, top * s, (cx + r) * s, (top + 2 * r) * s]
        if width:
            d.arc(box, 180, 360, fill=255, width=int(width * s))
            d.line([((cx - r) * s + width * s / 2, (top + r) * s), ((cx - r) * s + width * s / 2, SHELF * s)], fill=255, width=int(width * s))
            d.line([((cx + r) * s - width * s / 2, (top + r) * s), ((cx + r) * s - width * s / 2, SHELF * s)], fill=255, width=int(width * s))
        else:
            d.pieslice(box, 180, 360, fill=255)
            d.rectangle([(cx - r) * s, (top + r) * s, (cx + r) * s, SHELF * s], fill=255)
    return draw


# soft drop shadow of the arches
sh = sum(mask((Wd, H), arch_draw(cx)) for cx in CXS)
sh = cv2.GaussianBlur(np.roll(sh, (6, 3), (0, 1)), (0, 0), 7)
sh[SHELF:] = 0
comp(flyer, np.zeros((H, Wd, 3), np.float32) + (40, 10, 40), np.clip(sh, 0, 1) * 0.35)

gold_v = lerp(GOLD_HI, GOLD_LO, np.clip((YY - ATOP) / (SHELF - ATOP), 0, 1))
for cx, (t0, t1) in zip(CXS, tints):
    a = mask((Wd, H), arch_draw(cx))
    t = np.clip((YY - ATOP) / (SHELF - ATOP), 0, 1)
    fillc = lerp(t0, t1, t ** 0.9)
    glow = np.exp(-(((XX - cx) / 95) ** 2 + ((YY - 905) / 150) ** 2))
    fillc = fillc * (1 - 0.55 * glow[..., None]) + np.array([255, 252, 246]) * 0.55 * glow[..., None]
    comp(flyer, fillc, a * 0.96)
    # faint diagonal sheen
    sheen = np.clip(1 - np.abs((XX - cx) + 0.5 * (YY - 800) + 30) / 22, 0, 1) * a * 0.18
    comp(flyer, np.full((H, Wd, 3), 255, np.float32), sheen)
    comp(flyer, gold_v, mask((Wd, H), arch_draw(cx, 0, 3)))
    comp(flyer, gold_v, mask((Wd, H), arch_draw(cx, 7, 1)) * 0.75)
    # keystone ornament at the top of the arch
    comp(flyer, gold_v, mask((Wd, H), lambda d, s, cx=cx: d.polygon(
        [(x * s, y * s) for x, y in star_pts(cx, ATOP, 11, 3.2, 4)], fill=255)))

# lavender sprigs growing from the shelf between the arches (drawn on an RGBA layer)
def sprig(d, s, x0, lean, height, rng):
    path = [(x0 + lean * (k / 39) ** 2, SHELF - height * k / 39) for k in range(40)]
    d.line([(x * s, y * s) for x, y in path], fill=(92, 112, 78, 255), width=int(1.3 * s))
    for side in (-1, 1):                                  # slim leaves near the base
        lx, ly = path[3]
        leaf = [(lx, ly), (lx + side * 7, ly - 12), (lx + side * 11, ly - 30), (lx + side * 3, ly - 14)]
        d.polygon([(x * s, y * s) for x, y in leaf], fill=(118, 146, 104, 255))
    n = 26
    for k in range(n):                                    # buds, bottom to top, getting smaller
        t = 0.42 + 0.58 * k / (n - 1)
        bx, by = x0 + lean * t * t, SHELF - height * t
        sz = 2.9 - 1.3 * (t - 0.42) / 0.58
        off = (1 if k % 2 else -1) * sz * rng.uniform(0.6, 1.1)
        base = np.array(lerp((118, 66, 176), (176, 128, 228), rng.uniform(0, 1)))
        for dx, dy, f in ((0, 0, 1.0), (-0.35, -0.5, 1.25)):   # body + highlight
            col = tuple(int(v) for v in np.clip(base * f, 0, 255)) + (255,)
            r = sz * (1 if f == 1.0 else 0.45)
            cx_, cy_ = bx + off + dx * sz, by + dy * sz
            d.ellipse([(cx_ - r) * s, (cy_ - r * 1.35) * s, (cx_ + r) * s, (cy_ + r * 1.35) * s], fill=col)


spr = Image.new('RGBA', (Wd * SS, H * SS), (0, 0, 0, 0))
dd = ImageDraw.Draw(spr)
gaps = [CXS[0] - 104, (CXS[0] + CXS[1]) / 2, (CXS[1] + CXS[2]) / 2, (CXS[2] + CXS[3]) / 2, CXS[3] + 104]
for gx in gaps:
    for dx, lean, hgt in ((-5, -22, 112), (0, 3, 136), (5, 24, 104)):
        sprig(dd, SS, gx + dx, lean, hgt + rng.uniform(-8, 8), rng)
spr = np.array(spr.resize((Wd, H), Image.LANCZOS), np.float32)
comp(flyer, spr[..., :3], spr[..., 3] / 255)

# golden sparkles and bokeh around the display
for _ in range(70):
    x, y = rng.uniform(70, 1050), rng.uniform(620, 1030)
    r = rng.uniform(2, 6)
    a = mask((Wd, H), lambda d, s, x=x, y=y, r=r: d.ellipse([(x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s], fill=255))
    comp(flyer, np.full((H, Wd, 3), (255, 236, 190), np.float32), cv2.GaussianBlur(a, (0, 0), 1.2) * rng.uniform(0.25, 0.6))
for _ in range(26):
    x, y = rng.uniform(80, 1045), rng.uniform(630, 1020)
    r = rng.uniform(4, 10)
    a = mask((Wd, H), lambda d, s, x=x, y=y, r=r: d.polygon([(px * s, py * s) for px, py in star_pts(x, y, r, r * 0.22, 4)], fill=255))
    comp(flyer, np.full((H, Wd, 3), (255, 230, 160), np.float32), a * 0.95)
    comp(flyer, np.full((H, Wd, 3), (255, 240, 200), np.float32), cv2.GaussianBlur(a, (0, 0), r * 0.6) * 0.5)

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
