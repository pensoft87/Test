"""Sample-sachet label, 2.4 x 2.9 in at 400 ppi (960 x 1160 px), built from the main label's art.

usage: sachet.py <plate.png> <layer.png> <out.png>  (needs: pip install segno)
  plate.png -- empty full-bleed label from layout.py (oval with the fixed title, empty panels)
  layer.png -- original panel elements from layout.py (seals, "Harmonieproducts" stroke)
"""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
sys.path.insert(0, sys.path[0])
from common import dilate, inpaint
from fonts import font
import segno
import typeset

plate_path, layer_path, dst = sys.argv[1:4]
plate = np.asarray(Image.open(plate_path).convert('RGB')).astype(np.float64)
layer = Image.open(layer_path).convert('RGBA')
PH, PW = plate.shape[:2]

W, H = 960, 1160                       # 2.4 x 2.9 in @ 400 ppi
CREAM = np.array([253., 248., 236.])
PURPLE = (88, 16, 112)
INK = (78, 46, 124)
FONT = 'NunitoSans.ttf'

canvas = np.ones((H, W, 3)) * CREAM

def paste(img, x, y, alpha):
    """Alpha-blend an RGB float image at (x, y)."""
    global canvas
    h, w = img.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    sub = img[y0 - y:y1 - y, x0 - x:x1 - x]
    al = alpha[y0 - y:y1 - y, x0 - x:x1 - x][..., None]
    canvas[y0:y1, x0:x1] = canvas[y0:y1, x0:x1] * (1 - al) + sub * al

def mirrored(strip):
    """Make a symmetric band of width W from a strip of width W/2 (mirror at its right edge)."""
    return np.concatenate([strip, strip[:, ::-1]], axis=1)

# ---------------------------------------------------------------- bands
top = mirrored(plate[0:84, 0:W // 2])                 # leaves + gold rule
fade = np.clip((84 - np.arange(84)) / 8.0, 0, 1)      # soften into the cream below the rule
paste(top, 0, 0, np.repeat(fade[:, None], W, 1))

bot = mirrored(plate[640:800, 1120:1120 + W // 2])   # purple flower band
BH = bot.shape[0]
fade = np.clip(np.arange(BH) / 24.0, 0, 1)
paste(bot, 0, H - BH, np.repeat(fade[:, None], W, 1))

# ---------------------------------------------------------------- oval (logo, title, drop)
OCX, OCY, OA, OB = 796.5, 316.4, 269.3, 301.1
ox0, oy0, ox1, oy1 = 470, 8, 1125, 748
oval = plate[oy0:oy1, ox0:ox1].copy()
yy, xx = np.mgrid[oy0:oy1, ox0:ox1]

# "4. OZ." -> "MUESTRA" on the purple tab
r, g, b = oval[..., 0], oval[..., 1], oval[..., 2]
tab = (yy > 668) & (yy < 720) & (xx > 720) & (xx < 882)
txt = tab & (oval.min(2) > 150)
txt = dilate(txt, 2) & tab
oval = inpaint(oval, txt, 200)
f = font(FONT, 4 * 25, 900)
label = 'MUESTRA'
tw = f.getlength(label)
cap = f.getbbox('M')
S = 4
tm = Image.new('L', (int(tw) + 8, (cap[3] - cap[1]) + 8), 0)
ImageDraw.Draw(tm).text((4, 4 - cap[1]), label, font=f, fill=255)
tm = tm.resize((tm.width // S, tm.height // S), Image.LANCZOS)
ta = np.asarray(tm, float) / 255
tcx, tcy = 800.5 - ox0, 695.5 - oy0
tx, ty = int(round(tcx - ta.shape[1] / 2)), int(round(tcy - ta.shape[0] / 2))
oval[ty:ty + ta.shape[0], tx:tx + ta.shape[1]] = (
    oval[ty:ty + ta.shape[0], tx:tx + ta.shape[1]] * (1 - ta[..., None]) + np.array([255., 252., 255.]) * ta[..., None])

# cut-out: the gold-framed oval with its glow, plus the drop / nuts cluster and tab underneath
e = ((xx - OCX) / (OA + 30)) ** 2 + ((yy - OCY) / (OB + 30)) ** 2
m = (e <= 1).astype(float)
m = ndi.gaussian_filter(m, 10)
# the bed of lavender leaves under the drop fades out in a soft rounded shape
bed = ((xx - OCX) / 250.0) ** 2 + ((yy - 655) / 105.0) ** 2
m = np.maximum(m, np.clip((1.0 - bed) / 0.45, 0, 1))
m = np.clip(m, 0, 1)

OSC = 0.86                                            # oval scale on the sachet
def scaled(arr, sc):
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8) if arr.ndim == 3 else (arr * 255).astype(np.uint8))
    im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float64)
    return a if arr.ndim == 3 else a / 255
oval_s, m_s = scaled(oval, OSC), scaled(m, OSC)

# lavender + green leaf sprig (from the label's lower-left corner) framing the oval base
spr = plate[556:724, 0:95].copy()               # (layout.py moved it to the corner)
sr, sg = spr[..., 0], spr[..., 1]
leaf = (sr - sg > 22) | (sg - sr > 8) | (spr.mean(2) < 200)
leaf = ndi.binary_opening(leaf, iterations=1)
leaf[150:] = False                                    # drop the gold rule at its foot
sa = ndi.gaussian_filter(ndi.binary_dilation(leaf, iterations=1).astype(float), 0.8)
sa *= np.clip((150 - np.arange(spr.shape[0])) / 45.0, 0, 1)[:, None]   # fade out at its foot
SPS = 1.6
spr_s, sa_s = scaled(spr, SPS), scaled(sa, SPS)

OX = int(round((W - oval_s.shape[1]) / 2))
OY = 16
SY = OY + int(395 * OSC)
paste(spr_s, 0, SY, sa_s)                             # leaves enter from the sachet's edges
paste(spr_s[:, ::-1], W - spr_s.shape[1], SY, sa_s[:, ::-1])
paste(oval_s, OX, OY, m_s)

# ---------------------------------------------------------------- text helpers
def text_img(s, size, weight, color, track=0.0):
    f = font(FONT, size * S, weight)
    bb = f.getbbox(s)
    w = int(f.getlength(s) + track * S * size * len(s)) + 8 * S
    im = Image.new('L', (w, int(size * 1.5 * S)), 0)
    d = ImageDraw.Draw(im)
    x = 4 * S
    for ch in s:
        d.text((x, size * 0.2 * S), ch, font=f, fill=255)
        x += f.getlength(ch) + track * S * size
    im = im.resize((im.width // S, im.height // S), Image.LANCZOS)
    a = np.asarray(im, float) / 255
    ys, xs = np.where(a > 0.02)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    rgb = np.ones(a.shape + (3,)) * np.array(color, float)
    return rgb, a

def put_center(rgb_a, cy):
    rgb, a = rgb_a
    paste(rgb, int(round(W / 2 - a.shape[1] / 2)), int(round(cy - a.shape[0] / 2)), a)
    return a.shape

def asset(x0, y0, x1, y1, scale=1.0):
    im = layer.crop((x0, y0, x1, y1))
    bb = im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
    im = im.crop(bb)
    if scale != 1.0:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    arr = np.asarray(im).astype(np.float64)
    return arr[..., :3], arr[..., 3] / 255

# ---------------------------------------------------------------- "GRATIS" seal (top right)
def seal(cx, cy, R, small, big, big_size=27, rot=12, small_first=True):
    S2 = 4
    n = int(2 * R + 8) * S2
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = n / 2
    d.ellipse((c - R * S2, c - R * S2, c + R * S2, c + R * S2), fill=(201, 150, 58, 255))
    d.ellipse((c - (R - 2.2) * S2, c - (R - 2.2) * S2, c + (R - 2.2) * S2, c + (R - 2.2) * S2), fill=(242, 205, 120, 255))
    d.ellipse((c - (R - 4.5) * S2, c - (R - 4.5) * S2, c + (R - 4.5) * S2, c + (R - 4.5) * S2), fill=(201, 150, 58, 255))
    d.ellipse((c - (R - 6.5) * S2, c - (R - 6.5) * S2, c + (R - 6.5) * S2, c + (R - 6.5) * S2), fill=PURPLE + (255,))
    f1 = font(FONT, 15 * S2, 800)
    f2 = font(FONT, big_size * S2, 900)
    rows = ((small, f1, -15, (246, 226, 252)), (big, f2, 9, (255, 255, 255))) if small_first else \
           ((big, f2, -8, (255, 255, 255)), (small, f1, 15, (246, 226, 252)))
    for s, f, dy, col in rows:
        bb = f.getbbox(s)
        d.text((c - f.getlength(s) / 2, c + dy * S2 - (bb[1] + bb[3]) / 2), s, font=f, fill=col + (255,))
    im = im.rotate(rot, resample=Image.BICUBIC)
    im = im.resize((n // S2, n // S2), Image.LANCZOS)
    sh = Image.new('RGBA', im.size, (60, 20, 70, 0))
    sh.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(4)).point(lambda v: v * 0.35))
    arr = np.asarray(sh).astype(float)
    paste(arr[..., :3], int(cx - im.width / 2) + 2, int(cy - im.height / 2) + 4, arr[..., 3] / 255)
    arr = np.asarray(im).astype(float)
    paste(arr[..., :3], int(cx - im.width / 2), int(cy - im.height / 2), arr[..., 3] / 255)

seal(W - 150, 178, 66, 'MUESTRA', 'GRATIS')
seal(150, 178, 66, '+ VITAMINA E', '6 ACEITES', 20, -12, small_first=False)

# ---------------------------------------------------------------- copy under the oval
PROPIEDADES = ('Mezcla nutritiva diseñada para acondicionar, suavizar y aportar brillo, mejorando '
               'la apariencia del cabello. Contribuye a reducir la sensación de resequedad y '
               'facilita el manejo del cabello.')
INGREDIENTES = ('Aceite de jojoba, aceite de argán, aceite de aguacate, vitamina E, aceite de oliva, '
                'aceite de ricino, aceite de coco y fragancia natural.')
INSTAGRAM = 'https://www.instagram.com/harmonieproducts'
MX0, MX1 = 92, W - 92                                # text margins

def put_block(blk, x, y):
    arr = np.asarray(blk).astype(np.float64)
    paste(arr[..., :3], int(round(x)), int(round(y)), arr[..., 3] / 255)
    return arr.shape[0]

y = OY + oval_s.shape[0] + 16
blk, _ = typeset.text_block(PROPIEDADES, MX1 - MX0, 20, 25, INK)
y += put_block(blk, MX0, y) + 22

# two columns: Instagram QR (left) | ingredients + "free" seals (right)
QM = 6                                               # module size: 6 px = 0.015 in
qr = segno.make(INSTAGRAM, error='m')
mods = np.array([list(r) for r in qr.matrix_iter(scale=1, border=2)], float)
q = np.kron(mods, np.ones((QM, QM)))
QS = q.shape[0]
qrgb = np.ones((QS, QS, 3)) * (1 - q[..., None]) * 255 + q[..., None] * np.array([42., 10., 58.])
# rounded white card behind the code so it keeps its quiet zone on the cream
card = Image.new('L', ((QS + 8) * 4, (QS + 8) * 4), 0)
ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=12 * 4, fill=255)
card = np.asarray(card.resize((QS + 8, QS + 8), Image.LANCZOS), float) / 255
qx, qy = MX0 + 6, y
paste(np.ones((QS + 8, QS + 8, 3)) * 255, qx - 4, qy - 4, card)
paste(qrgb, qx, qy, np.ones((QS, QS)))
q_bottom = qy + QS

RX0 = qx + QS + 36
hd_rgb, hd_a = text_img('Ingredientes', 19, 800, PURPLE)
paste(hd_rgb, RX0, y + 2, hd_a)
ry = y + 2 + hd_a.shape[0] + 9
blk, _ = typeset.text_block(INGREDIENTES, MX1 - RX0, 18, 23, INK)
ry += put_block(blk, RX0, ry) + 14
rgb, a = asset(305, 428, 560, 503, 0.86)            # Paraben / Silicone / Cruelty / Sulfate free
paste(rgb, RX0 - 4, ry, a)
ry += a.shape[0]
# Instagram call to action, its last line level with the foot of the QR
c1_rgb, c1_a = text_img('Escanéame y síguenos en Instagram', 15, 600, INK)
c2_rgb, c2_a = text_img('@harmonieproducts', 21, 800, PURPLE)
c2y = q_bottom - c2_a.shape[0]
c1y = c2y - 7 - c1_a.shape[0]
paste(c1_rgb, RX0, c1y, c1_a)
paste(c2_rgb, RX0, c2y, c2_a)
print('seals end', ry, '| call to action starts', c1y, '| QR ends', q_bottom, '| flower band starts', H - BH)

# ---------------------------------------------------------------- gold edge rules (as on the label)
dark, light = np.array([190., 136., 46.]), np.array([238., 196., 108.])
xg = np.arange(W) / W
sheen = 0.5 + 0.5 * np.cos(2 * np.pi * (xg * 1.5 + 0.1)) ** 3
for y0 in (0, H - 7):
    col = dark + (light - dark) * sheen[:, None]
    canvas[y0:y0 + 7] = col[None]

out = Image.fromarray(np.clip(canvas + 0.5, 0, 255).astype(np.uint8))
out.save(dst, dpi=(400, 400))
