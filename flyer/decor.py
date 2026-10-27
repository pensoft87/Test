"""Second pass over the flyer: real logo, liquid-gold ribbons and oil drops behind the bottles, and the
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

# ---------------------------------------------------------------- 3. silk ribbons of liquid gold + floating oil drops
rng = np.random.default_rng(7)
SHELF = 1037
RY0, RY1 = 560, SHELF                         # band of the flyer the ribbons live in


def ramp(stops, t):
    """Map t in [0,1] through a list of colours."""
    stops = np.asarray(stops, np.float32)
    t = np.clip(t, 0, 0.9999) * (len(stops) - 1)
    i = t.astype(int)
    return lerp(stops[i], stops[i + 1], t - i)


def ribbon(center, half, twist, palette, seed_phase=0.0):
    """Render a twisting satin ribbon. Returns (rgb, alpha) for rows RY0..RY1 at full res."""
    xs = (np.arange(Wd * SS) + 0.5) / SS
    ys = RY0 + (np.arange((RY1 - RY0) * SS) + 0.5) / SS
    c, phi = center(xs), twist(xs)
    slope = np.gradient(c, xs)
    nz = np.abs(np.cos(phi))                                   # how much the ribbon faces us
    hv = half * (0.12 + 0.88 * nz) * np.sqrt(1 + slope ** 2)   # visible half-height
    v = (ys[:, None] - c[None, :]) / hv[None, :]               # -1..1 across the ribbon
    inside = np.abs(v) < 1
    sp = np.sin(phi)[None, :]
    shade = 0.5 + 0.5 * np.cos(math.pi * v * 0.85 - sp * 1.5 + seed_phase)
    shade = shade * (0.45 + 0.55 * nz[None, :]) * np.where(np.cos(phi)[None, :] > 0, 1.0, 0.78)
    spec = np.exp(-((v - 0.45 * sp) / 0.16) ** 2) * nz[None, :] ** 2
    edge = np.exp(-np.clip(1 - np.abs(v), 0, 1) / 0.06)                 # thin bright rim at the edges
    b = np.clip(0.08 + 0.78 * shade + 0.55 * spec + 0.18 * edge, 0, 1)
    rgb = ramp(palette, b)
    a = inside.astype(np.float32)
    small = lambda img: cv2.resize(img, (Wd, RY1 - RY0), interpolation=cv2.INTER_AREA)
    return small(rgb * a[..., None]), small(a)


def put_layer(rgb_pm, a, shadow=0.0, off=(10, 6)):
    """Composite a premultiplied layer into the ribbon band, with an optional soft shadow."""
    reg = flyer[RY0:RY1].astype(np.float32)
    if shadow:
        sh = cv2.GaussianBlur(np.roll(a, off, (0, 1)), (0, 0), 9) * shadow
        reg = reg * (1 - sh[..., None]) + np.array([40, 8, 44], np.float32) * sh[..., None]
    reg = rgb_pm + reg * (1 - a[..., None])
    flyer[RY0:RY1] = np.clip(reg, 0, 255).astype(np.uint8)


GOLD_RAMP = [(70, 34, 6), (138, 82, 18), (196, 138, 44), (236, 188, 92), (252, 226, 150), (255, 249, 226)]
LILAC_RAMP = [(52, 20, 78), (98, 56, 150), (150, 108, 210), (196, 166, 238), (232, 216, 252), (255, 252, 255)]

# lilac satin ribbon behind, liquid-gold ribbon in front of it; both sweep up from left to right
lilac = ribbon(lambda x: 905 - 0.16 * (x - 40) + 48 * np.sin(2 * math.pi * x / 470 + 2.3),
               21, lambda x: 2 * math.pi * x / 360 + 0.9 * np.sin(2 * math.pi * x / 610) + 1.2, LILAC_RAMP, 0.4)
gold = ribbon(lambda x: 960 - 0.2 * (x - 40) + 62 * np.sin(2 * math.pi * x / 540 + 0.5),
              31, lambda x: 2 * math.pi * x / 420 + 0.8 * np.sin(2 * math.pi * x / 700), GOLD_RAMP)
put_layer(*lilac, shadow=0.35)
put_layer(*gold, shadow=0.45)


def drop(cx, cy, r, tilt=0.0):
    """A glossy golden oil drop (teardrop pointing up)."""
    pad = int(r * 3)
    x0, y0 = int(cx) - pad, int(cy) - pad
    n = 2 * pad
    gy_, gx_ = np.mgrid[0:n * SS, 0:n * SS].astype(np.float32) / SS
    u, w = gx_ - (cx - x0), gy_ - (cy - y0)
    ca, sa = math.cos(tilt), math.sin(tilt)
    u, w = u * ca + w * sa, -u * sa + w * ca
    # teardrop: circle of radius r, with a point at height 2.1 r above its centre
    k = np.clip(-w / (2.1 * r), 0, 1)
    width = np.where(w > 0, np.sqrt(np.clip(r * r - w * w, 0, None)), r * (1 - k) ** 1.4 * np.sqrt(np.clip(1 - (k * 0.2) ** 2, 0, 1)))
    inside = (np.abs(u) < width) & (w < r) & (w > -2.1 * r)
    rr = np.hypot(u / r, (w - r * 0.15) / r)
    body = ramp([(150, 86, 10), (214, 150, 30), (246, 196, 60), (255, 226, 120)], np.clip(0.95 - 0.55 * rr + 0.25 * (u / r), 0, 1))
    hl = np.exp(-(((u + 0.38 * r) / (0.16 * r)) ** 2 + ((w + 0.05 * r) / (0.45 * r)) ** 2))       # long highlight
    dot = np.exp(-(((u - 0.3 * r) / (0.1 * r)) ** 2 + ((w - 0.45 * r) / (0.1 * r)) ** 2))          # small sparkle
    rim = np.exp(-((1 - np.clip(np.abs(u) / np.maximum(width, 1e-3), 0, 1)) / 0.12)) * 0.35
    col = body * (1 - rim[..., None]) + np.array([255, 236, 170]) * rim[..., None]
    col = col + 255 * np.clip(hl * 0.85 + dot, 0, 1)[..., None]
    a = inside.astype(np.float32)
    col = cv2.resize(np.clip(col, 0, 255) * a[..., None], (n, n), interpolation=cv2.INTER_AREA)
    a = cv2.resize(a, (n, n), interpolation=cv2.INTER_AREA)
    reg = flyer[y0:y0 + n, x0:x0 + n].astype(np.float32)
    sh = cv2.GaussianBlur(np.roll(a, (int(r * 0.5), int(r * 0.3)), (0, 1)), (0, 0), r * 0.35) * 0.3
    reg = reg * (1 - sh[..., None]) + np.array([60, 20, 40]) * sh[..., None]
    flyer[y0:y0 + n, x0:x0 + n] = np.clip(col + reg * (1 - a[..., None]), 0, 255).astype(np.uint8)


# drops scattered in the gaps between the bottles, as if splashing off the ribbon
for x, y, r, t in [(98, 868, 9, 0.25), (327, 760, 12, -0.2), (318, 845, 6, 0.3), (560, 700, 9, 0.15),
                   (548, 815, 13, -0.25), (790, 742, 11, 0.2), (800, 838, 6, -0.3), (1030, 830, 10, -0.2),
                   (1022, 760, 6, 0.3), (110, 760, 6, -0.2), (570, 905, 7, 0.1)]:
    drop(x, y, r, t)

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
