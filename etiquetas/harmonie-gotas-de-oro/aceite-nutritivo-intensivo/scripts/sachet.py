"""Sample-sachet label, 2.4 x 2.9 in at 400 ppi (960 x 1160 px), built from the label's own art,
laid out like the "Aceite nutritivo", "Aceite de protección" and "Aceite de fortalecimiento" sachets,
in this model's gold.

usage: sachet.py <base> <out.png>   (needs: pip install segno)
  <base>-clean.png  the model with the new title and its panels cleared (plate.py)
  <base>-plate.png  the widened label (for the leaf bands)
  <base>-layer.png  the model's panel elements (for the "free" seals)
"""
import os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'scripts'))
from common import dilate, inpaint
from fonts import font
from boxes import BOXES, SEALS
import segno
import typeset

base, dst = sys.argv[1], sys.argv[2]
clean = np.asarray(Image.open(base + '-clean.png').convert('RGB')).astype(np.float64)
plate = np.asarray(Image.open(base + '-plate.png').convert('RGB')).astype(np.float64)
layer = Image.open(base + '-layer.png').convert('RGBA')

W, H = 960, 1160                       # 2.4 x 2.9 in @ 400 ppi
BROWN = (66, 34, 8)                    # the pills' dark brown
INK = (40, 22, 6)                      # body copy, as on the label
SERIF, SERIF_B, SANS = 'PTSerif-Regular.ttf', 'PTSerif-Bold.ttf', 'NunitoSans.ttf'
typeset.FONT = SERIF
S = 4                                  # supersampling for drawn type

# ---------------------------------------------------------------- gold ground
# the model's own plain gold (its cleared left panel), stretched over half the sachet and mirrored
half = Image.fromarray(np.clip(clean[125:585, 10:450], 0, 255).astype(np.uint8)).resize((W // 2, H), Image.BICUBIC)
half = np.asarray(half).astype(np.float64)
canvas = np.concatenate([half, half[:, ::-1]], axis=1)

def paste(img, x, y, alpha):
    """Alpha-blend an RGB float image at (x, y)."""
    h, w = img.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    sub = img[y0 - y:y1 - y, x0 - x:x1 - x]
    al = alpha[y0 - y:y1 - y, x0 - x:x1 - x][..., None]
    canvas[y0:y1, x0:x1] = canvas[y0:y1, x0:x1] * (1 - al) + sub * al

def paste_rgba(im, x, y):
    arr = np.asarray(im).astype(np.float64)
    paste(arr[..., :3], int(round(x)), int(round(y)), arr[..., 3] / 255)
    return im.size

def mirrored(strip):
    """A symmetric band of width W from a strip of width W/2 (mirrored at its right edge)."""
    return np.concatenate([strip, strip[:, ::-1]], axis=1)

# ---------------------------------------------------------------- leaf bands
TOP = 110
top = mirrored(plate[0:TOP, 0:W // 2])                # the gold leaves of the top corners
fade = np.clip((TOP - np.arange(TOP)) / 22.0, 0, 1)
paste(top, 0, 0, np.repeat(fade[:, None], W, 1))
BOT = 130
bot = mirrored(plate[800 - BOT:800, 1600 - W // 2:1600][:, ::-1])
fade = np.clip(np.arange(BOT) / 30.0, 0, 1)
paste(bot, 0, H - BOT, np.repeat(fade[:, None], W, 1))

# ---------------------------------------------------------------- oval (logo, title, drop)
ox0, oy0, ox1, oy1 = 440, 30, 935, 768
oval = clean[oy0:oy1, ox0:ox1].copy()
yy, xx = np.mgrid[oy0:oy1, ox0:ox1]

# "4. OZ." -> "MUESTRA" on the brown tab
tab = (yy > 688) & (yy < 712) & (xx > 646) & (xx < 722)
txt = dilate(tab & (oval.mean(2) > 135), 2) & tab
oval = inpaint(oval, txt, 200)
f = font(SERIF_B, 17 * S)
label = 'MUESTRA'
tw, cap = f.getlength(label), f.getbbox('M')
tm = Image.new('L', (int(tw) + 8 * S + int(1.2 * S * len(label)), (cap[3] - cap[1]) + 8 * S), 0)
x = 4 * S
for ch in label:                                      # a little letter spacing, as on the label's tab
    ImageDraw.Draw(tm).text((x, 4 * S - cap[1]), ch, font=f, fill=255)
    x += f.getlength(ch) + 1.2 * S
tm = tm.resize((tm.width // S, tm.height // S), Image.LANCZOS)
ta = np.asarray(tm, float) / 255
tcx, tcy = 686.0 - ox0, 701.0 - oy0
tx, ty = int(round(tcx - ta.shape[1] / 2)), int(round(tcy - ta.shape[0] / 2))
oval[ty:ty + ta.shape[0], tx:tx + ta.shape[1]] = (
    oval[ty:ty + ta.shape[0], tx:tx + ta.shape[1]] * (1 - ta[..., None]) + np.array([243., 227., 192.]) * ta[..., None])

# cut-out: the gold-framed oval with its glow, plus the cup, tab and leaves at its foot
OCX, OCY, OA, OB = 686.0, 300.0, 224.0, 262.0
e = ((xx - OCX) / (OA + 14)) ** 2 + ((yy - OCY) / (OB + 14)) ** 2
m = ndi.gaussian_filter((e <= 1).astype(float), 7)
cup = ((xx - OCX) / 205.0) ** 2 + ((yy - 610) / 150.0) ** 4
m = np.clip(np.maximum(m, np.clip((1.0 - cup) / 0.3, 0, 1)), 0, 1)
m *= np.clip((oy1 - 6 - yy) / 20.0, 0, 1)            # soft foot

OSC = 0.86                                            # oval scale on the sachet
def scaled(arr, sc):
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8) if arr.ndim == 3 else (arr * 255).astype(np.uint8))
    im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float64)
    return a if arr.ndim == 3 else a / 255
oval_s, m_s = scaled(oval, OSC), scaled(m, OSC)
OX = int(round(W / 2 - (OCX - ox0) * OSC))
OY = 4
paste(oval_s, OX, OY, m_s)

# ---------------------------------------------------------------- round seals beside the oval
def seal(cx, cy, R, rows, rot):
    """rows: [(text, size, weight, dy, colour)]"""
    n = int(2 * R + 8) * S
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = n / 2
    for rr, col in ((R, (190, 136, 46)), (R - 2.2, (246, 214, 140)), (R - 4.5, (190, 136, 46)), (R - 6.5, BROWN)):
        d.ellipse((c - rr * S, c - rr * S, c + rr * S, c + rr * S), fill=col + (255,))
    for s, size, wt, dy, col in rows:
        f = font(SANS, size * S, wt)
        bb = f.getbbox(s)
        d.text((c - f.getlength(s) / 2, c + dy * S - (bb[1] + bb[3]) / 2), s, font=f, fill=col + (255,))
    im = im.rotate(rot, resample=Image.BICUBIC)
    im = im.resize((n // S, n // S), Image.LANCZOS)
    sh = Image.new('RGBA', im.size, (50, 25, 0, 0))
    sh.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(4)).point(lambda v: v * 0.35))
    paste_rgba(sh, cx - im.width / 2 + 2, cy - im.height / 2 + 4)
    paste_rgba(im, cx - im.width / 2, cy - im.height / 2)

CREAM, WHITE = (250, 232, 190), (255, 248, 230)
seal(W - 122, 214, 64, [('MUESTRA', 15, 800, -15, CREAM), ('GRATIS', 27, 900, 9, WHITE)], 12)
seal(122, 214, 64, [('6 ACEITES', 20, 900, -16, WHITE), ('+ KARITÉ', 14, 800, 5, CREAM),
                    ('+ VITAMINA E', 14, 800, 21, CREAM)], -12)

# ---------------------------------------------------------------- copy under the oval
PROPIEDADES = ('Ayuda a acondicionar intensamente el cabello seco, aportando suavidad, brillo y una '
               'apariencia más saludable. Contribuye a mejorar la manejabilidad y a reducir la sensación '
               'de aspereza, dejando el cabello con una apariencia más flexible y nutrida.')
INGREDIENTES = ('Aceite de batana, aceite de argán, manteca de karité, aceite de aguacate, vitamina E, '
                'aceite de oliva, aceite de ricino, aceite de coco.')
INSTAGRAM = 'https://www.instagram.com/harmonieproducts'
MX0, MX1 = 70, W - 70                                 # text margins

def text_img(s, size, fname, color):
    f = font(fname, size * S)
    im = Image.new('L', (int(f.getlength(s)) + 8 * S, int(size * 1.6 * S)), 0)
    ImageDraw.Draw(im).text((4 * S, size * 0.2 * S), s, font=f, fill=255)
    im = im.resize((im.width // S, im.height // S), Image.LANCZOS)
    im = im.crop(im.getbbox())
    rgba = Image.new('RGBA', im.size, color + (0,))
    rgba.putalpha(im)
    return rgba

y = OY + int(round((oy1 - oy0) * OSC)) + 4
blk, _ = typeset.text_block(PROPIEDADES, MX1 - MX0, 20, 25, INK, weight=None)
y += paste_rgba(blk, MX0, y)[1] + 30

# two columns: Instagram QR (left) | ingredients, "free" seals and the call to action (right)
QM = 7                                               # module size: 7 px = 0.0175 in
qr = segno.make(INSTAGRAM, error='m')
mods = np.array([list(r) for r in qr.matrix_iter(scale=1, border=2)], float)
q = np.kron(mods, np.ones((QM, QM)))
QS = q.shape[0]
PAPER = np.array([250., 242., 222.])
qrgb = (1 - q[..., None]) * PAPER + q[..., None] * np.array([30., 14., 2.])
card = Image.new('L', ((QS + 8) * 4, (QS + 8) * 4), 0)       # rounded card: keeps its quiet zone
ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=12 * 4, fill=255)
card = np.asarray(card.resize((QS + 8, QS + 8), Image.LANCZOS), float) / 255
qx, qy = MX0 + 8, y
paste(np.ones((QS + 8, QS + 8, 3)) * PAPER, qx - 4, qy - 4, card)
paste(qrgb, qx, qy, np.ones((QS, QS)))
q_bottom = qy + QS

RX0 = qx + QS + 30
hd = text_img('Ingredientes', 20, SERIF_B, BROWN)
paste_rgba(hd, RX0, y)
ry = y + hd.height + 9
blk, _ = typeset.text_block(INGREDIENTES, MX1 - RX0, 17, 21, INK, weight=None)
ry += paste_rgba(blk, RX0, ry)[1] + 10
x0, y0, x1, y1 = BOXES['sellos']
sl = layer.crop((x0, y0, x1, y1))
yy, xx = np.mgrid[y0:y1, x0:x1]
inside = np.zeros(yy.shape, bool)
for cx, cy, r in SEALS:                              # the seals only, not the stroke above them
    inside |= (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
sl.putalpha(Image.fromarray((np.asarray(sl.getchannel('A'), float) * inside).astype(np.uint8)))
sl = sl.crop(sl.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
sl = sl.resize((round(sl.width * 0.68), round(sl.height * 0.68)), Image.LANCZOS)   # Paraben / Silicone / ...
paste_rgba(sl, RX0 - 2, ry)
ry += sl.height
# Instagram call to action, its last line level with the foot of the QR
c1 = text_img('Escanéame y síguenos en Instagram', 15, SERIF, INK)
c2 = text_img('@harmonieproducts', 21, SERIF_B, BROWN)
c2y = q_bottom - c2.height
c1y = c2y - 7 - c1.height
paste_rgba(c1, RX0, c1y)
paste_rgba(c2, RX0, c2y)
assert ry + 4 <= c1y, 'free seals run into the call to action (%d > %d)' % (ry + 4, c1y)
print('seals end', ry, '| call to action starts', c1y, '| QR ends', q_bottom, '| leaf band starts', H - BOT)

# ---------------------------------------------------------------- gold edge rules (as on the label)
dark, light = np.array([190., 136., 46.]), np.array([238., 196., 108.])
xg = np.arange(W) / W
sheen = 0.5 + 0.5 * np.cos(2 * np.pi * (xg * 1.5 + 0.1)) ** 3
for y0 in (0, H - 7):
    canvas[y0:y0 + 7] = (dark + (light - dark) * sheen[:, None])[None]

Image.fromarray(np.clip(canvas + 0.5, 0, 255).astype(np.uint8)).save(dst, dpi=(400, 400))
