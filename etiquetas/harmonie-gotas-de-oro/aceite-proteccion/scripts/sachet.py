"""Sample-sachet label, 2.4 x 2.9 in at 400 ppi (960 x 1160 px), built from the label's own art,
laid out like the "Aceite nutritivo" sachet.

usage: sachet.py <base> <out.png>   (needs: pip install segno)
  <base>-clean.png  the model with the new title and its panels cleared (plate.py)
  <base>-plate.png  the widened label (for the leaf bands)
  <base>-layer.png  the model's panel elements (for the "free" seals)
"""
import os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'scripts'))
from common import dilate, inpaint
from fonts import font
import segno
import typeset

base, dst = sys.argv[1], sys.argv[2]
clean = np.asarray(Image.open(base + '-clean.png').convert('RGB')).astype(np.float64)
plate = np.asarray(Image.open(base + '-plate.png').convert('RGB')).astype(np.float64)
layer = Image.open(base + '-layer.png').convert('RGBA')

W, H = 960, 1160                       # 2.4 x 2.9 in @ 400 ppi
CREAM = np.array([249., 241., 220.])   # the panels' cream
PURPLE = (64, 10, 76)                  # the "Harmonieproducts" stroke
INK = (36, 16, 60)                     # body copy, as on the label
SERIF, SERIF_B, SANS = 'PTSerif-Regular.ttf', 'PTSerif-Bold.ttf', 'NunitoSans.ttf'
typeset.FONT = SERIF
S = 4                                  # supersampling for drawn type

canvas = np.ones((H, W, 3)) * CREAM

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
TOP = 92
top = mirrored(plate[0:TOP, 0:W // 2])                # lilac and gold leaves, gold vine
fade = np.clip((TOP - np.arange(TOP)) / 14.0, 0, 1)
paste(top, 0, 0, np.repeat(fade[:, None], W, 1))
BOT = 112
bot = mirrored(plate[800 - BOT:800, 0:W // 2])
fade = np.clip(np.arange(BOT) / 26.0, 0, 1)
paste(bot, 0, H - BOT, np.repeat(fade[:, None], W, 1))

# ---------------------------------------------------------------- oval (logo, title, drop)
ox0, oy0, ox1, oy1 = 290, 0, 975, 830
oval = clean[oy0:oy1, ox0:ox1].copy()
yy, xx = np.mgrid[oy0:oy1, ox0:ox1]

# "4. OZ." -> "MUESTRA" on the lilac tab
tab = (yy > 724) & (yy < 760) & (xx > 582) & (xx < 684)
txt = dilate(tab & (oval.min(2) > 200), 2) & tab
oval = inpaint(oval, txt, 200)
f = font(SERIF_B, 21 * S)
label = 'MUESTRA'
tw, cap = f.getlength(label), f.getbbox('M')
tm = Image.new('L', (int(tw) + 8 * S, (cap[3] - cap[1]) + 8 * S), 0)
ImageDraw.Draw(tm).text((4 * S, 4 * S - cap[1]), label, font=f, fill=255)
tm = tm.resize((tm.width // S, tm.height // S), Image.LANCZOS)
ta = np.asarray(tm, float) / 255
tcx, tcy = 632.0 - ox0, 741.0 - oy0
tx, ty = int(round(tcx - ta.shape[1] / 2)), int(round(tcy - ta.shape[0] / 2))
oval[ty:ty + ta.shape[0], tx:tx + ta.shape[1]] = (
    oval[ty:ty + ta.shape[0], tx:tx + ta.shape[1]] * (1 - ta[..., None]) + np.array([255., 252., 255.]) * ta[..., None])

# cut-out: the gold-framed oval with its glow, plus the cluster, tab and leaves at its foot
OCX, OCY, OA, OB = 629.0, 395.0, 305.0, 392.0
e = ((xx - OCX) / (OA + 16)) ** 2 + ((yy - OCY) / (OB + 14)) ** 2
m = ndi.gaussian_filter((e <= 1).astype(float), 7)
bed = ((xx - OCX) / 300.0) ** 2 + ((yy - 735) / 92.0) ** 2
m = np.clip(np.maximum(m, np.clip((1.0 - bed) / 0.35, 0, 1)), 0, 1)

OSC = 0.76                                            # oval scale on the sachet
def scaled(arr, sc):
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8) if arr.ndim == 3 else (arr * 255).astype(np.uint8))
    im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float64)
    return a if arr.ndim == 3 else a / 255
oval_s, m_s = scaled(oval, OSC), scaled(m, OSC)
OX = int(round(W / 2 - (OCX - ox0) * OSC))
OY = 6
paste(oval_s, OX, OY, m_s)

# ---------------------------------------------------------------- round seals beside the oval
def seal(cx, cy, R, small, big, big_size=27, rot=12, small_first=True):
    n = int(2 * R + 8) * S
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = n / 2
    for rr, col in ((R, (201, 150, 58)), (R - 2.2, (242, 205, 120)), (R - 4.5, (201, 150, 58)), (R - 6.5, PURPLE)):
        d.ellipse((c - rr * S, c - rr * S, c + rr * S, c + rr * S), fill=col + (255,))
    f1 = font(SANS, 15 * S, 800)
    f2 = font(SANS, big_size * S, 900)
    rows = ((small, f1, -15, (246, 226, 252)), (big, f2, 9, (255, 255, 255))) if small_first else \
           ((big, f2, -8, (255, 255, 255)), (small, f1, 15, (246, 226, 252)))
    for s, f, dy, col in rows:
        bb = f.getbbox(s)
        d.text((c - f.getlength(s) / 2, c + dy * S - (bb[1] + bb[3]) / 2), s, font=f, fill=col + (255,))
    im = im.rotate(rot, resample=Image.BICUBIC)
    im = im.resize((n // S, n // S), Image.LANCZOS)
    sh = Image.new('RGBA', im.size, (60, 20, 70, 0))
    sh.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(4)).point(lambda v: v * 0.35))
    paste_rgba(sh, cx - im.width / 2 + 2, cy - im.height / 2 + 4)
    paste_rgba(im, cx - im.width / 2, cy - im.height / 2)

seal(W - 122, 214, 64, 'MUESTRA', 'GRATIS')
seal(122, 214, 64, '+ VITAMINA E', '7 ACEITES', 20, -12, small_first=False)

# ---------------------------------------------------------------- copy under the oval
PROPIEDADES = ('Mezcla nutritiva de aceites diseñada para crear una barrera protectora que ayuda a '
               'conservar la humedad natural del cabello, reducir la resequedad y mejorar la '
               'apariencia de las hebras frente a las agresiones ambientales y el desgaste diario.')
INGREDIENTES = ('Aceite de salvado de arroz, aceite de jojoba, aceite de argán, aceite de aguacate, '
                'vitamina E, aceite de oliva, aceite de ricino, aceite de coco y fragancia natural.')
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

y = OY + int(round((oy1 - oy0) * OSC)) + 14
blk, _ = typeset.text_block(PROPIEDADES, MX1 - MX0, 20, 25, INK)
y += paste_rgba(blk, MX0, y)[1] + 36

# two columns: Instagram QR (left) | ingredients, "free" seals and the call to action (right)
QM = 7                                               # module size: 7 px = 0.0175 in
qr = segno.make(INSTAGRAM, error='m')
mods = np.array([list(r) for r in qr.matrix_iter(scale=1, border=2)], float)
q = np.kron(mods, np.ones((QM, QM)))
QS = q.shape[0]
qrgb = np.ones((QS, QS, 3)) * (1 - q[..., None]) * 255 + q[..., None] * np.array([36., 10., 50.])
card = Image.new('L', ((QS + 8) * 4, (QS + 8) * 4), 0)       # rounded white card: keeps its quiet zone
ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=12 * 4, fill=255)
card = np.asarray(card.resize((QS + 8, QS + 8), Image.LANCZOS), float) / 255
qx, qy = MX0 + 8, y
paste(np.ones((QS + 8, QS + 8, 3)) * 255, qx - 4, qy - 4, card)
paste(qrgb, qx, qy, np.ones((QS, QS)))
q_bottom = qy + QS

RX0 = qx + QS + 30
hd = text_img('Ingredientes', 20, SERIF_B, PURPLE)
paste_rgba(hd, RX0, y)
ry = y + hd.height + 9
blk, _ = typeset.text_block(INGREDIENTES, MX1 - RX0, 17, 21, INK)
ry += paste_rgba(blk, RX0, ry)[1] + 10
sl = layer.crop((17, 467, 330, 550))
sl = sl.crop(sl.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
sl = sl.resize((round(sl.width * 0.78), round(sl.height * 0.78)), Image.LANCZOS)   # Paraben / Silicone / ...
paste_rgba(sl, RX0 - 2, ry)
ry += sl.height
# Instagram call to action, its last line level with the foot of the QR
c1 = text_img('Escanéame y síguenos en Instagram', 15, SERIF, INK)
c2 = text_img('@harmonieproducts', 21, SERIF_B, PURPLE)
c2y = q_bottom - c2.height
c1y = c2y - 7 - c1.height
paste_rgba(c1, RX0, c1y)
paste_rgba(c2, RX0, c2y)
assert ry + 6 <= c1y, 'free seals run into the call to action'
print('seals end', ry, '| call to action starts', c1y, '| QR ends', q_bottom, '| leaf band starts', H - BOT)

# ---------------------------------------------------------------- gold edge rules (as on the label)
dark, light = np.array([190., 136., 46.]), np.array([238., 196., 108.])
xg = np.arange(W) / W
sheen = 0.5 + 0.5 * np.cos(2 * np.pi * (xg * 1.5 + 0.1)) ** 3
for y0 in (0, H - 7):
    canvas[y0:y0 + 7] = (dark + (light - dark) * sheen[:, None])[None]

Image.fromarray(np.clip(canvas + 0.5, 0, 255).astype(np.uint8)).save(dst, dpi=(400, 400))
