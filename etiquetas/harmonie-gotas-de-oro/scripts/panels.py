"""Re-compose the two side panels with the new copy.

Inputs (from layout.py): <base>-plate.png  -- the full-bleed label with empty side panels
                         <base>-layer.png  -- the original panel elements (RGBA, original positions)
and the title-fixed original (for the round "modo" icons, which touch the oval's frame).

Every graphic element (pills, icons, seals, brush strokes, QR codes...) is the original artwork;
only the changed copy is typeset, in Nunito Sans to match the label.
"""
import sys, os, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
sys.path.insert(0, sys.path[0])
from fonts import font

base, src_path, dst = sys.argv[1], sys.argv[2], sys.argv[3]
plate = Image.open(base + '-plate.png').convert('RGBA')
layer = Image.open(base + '-layer.png').convert('RGBA')
src = np.asarray(Image.open(src_path).convert('RGB')).astype(np.float64)
W, H = plate.size

INK = (62, 44, 94)            # body copy colour sampled from the label
PILL = (88, 16, 112)          # small pill purple
PILL_TXT = (246, 226, 252)
BODY_SIZE, BODY_LH = 18, 22
FONT = 'NunitoSans.ttf'

COPY = {
    'propiedades': 'Mezcla nutritiva diseñada para acondicionar, suavizar y aportar brillo, '
                   'mejorando la apariencia del cabello. Contribuye a reducir la sensación de '
                   'resequedad y facilita el manejo del cabello.',
    'ingredientes': 'Aceite de jojoba, aceite de argán, aceite de aguacate, vitamina E, aceite de '
                    'oliva, aceite de ricino, aceite de coco y fragancia natural.',
    'modo1_title': 'Después del lavado',
    'modo1': 'Aplicar en todo el cabello, procede a utilizar tus productos de uso habitual para '
             'definir el cabello.',
    'modo2_title': 'Para Peinar',
    'modo2': 'Aplicar sobre el cabello seco según necesidad, distribuyendo uniformemente de medios '
             'a puntas. Proceder con el peinado deseado.',
}

out = plate.copy()

def asset(x0, y0, x1, y1):
    """An original element, cropped tight to its visible pixels. Returns (image, offset)."""
    im = layer.crop((x0, y0, x1, y1))
    bb = im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
    return im.crop(bb), (x0 + bb[0], y0 + bb[1])

def place(im, x, y):
    out.alpha_composite(im, (int(round(x)), int(round(y))))

def wrap(text, f, width):
    lines, cur = [], ''
    for w in text.split():
        cand = (cur + ' ' + w).strip()
        if f.getlength(cand) <= width or not cur:
            cur = cand
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines

def text_block(text, width, size=BODY_SIZE, lh=BODY_LH, color=INK, weight=600):
    """Render a left-aligned paragraph; the block's top is the top of the cap height."""
    f = font(FONT, size * 4, weight)
    lines = wrap(text, font(FONT, size, weight), width)
    asc = f.getbbox('H')[1]
    h = lh * len(lines) + size
    im = Image.new('L', ((width + 20) * 4, h * 4), 0)
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        d.text((0, i * lh * 4 - asc), ln, font=f, fill=255)
    im = im.resize((width + 20, h), Image.LANCZOS)
    rgba = Image.new('RGBA', im.size, color + (0,))
    rgba.putalpha(im)
    bb = im.getbbox()
    return rgba.crop((0, 0, bb[2], bb[3])), len(lines)

def pill(label, size=17, pad=12, height=26):
    """Small purple pill with white label, drawn like the label's own 'Modo 1' pill."""
    f = font(FONT, size * 4, 800)
    tw = f.getlength(label) / 4
    w = int(round(tw + 2 * pad))
    S = 4
    m = Image.new('L', (w * S, height * S), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * S - 1, height * S - 1), radius=height * S // 2, fill=255)
    t = Image.new('L', (w * S, height * S), 0)
    cap = f.getbbox('H')
    ty = (height * S - (cap[3] - cap[1])) / 2 - cap[1]
    ImageDraw.Draw(t).text((pad * S, ty), label, font=f, fill=255)
    m = m.resize((w, height), Image.LANCZOS)
    t = t.resize((w, height), Image.LANCZOS)
    # gentle top-to-bottom shading like the originals
    g = np.linspace(1.06, 0.94, height)[:, None, None]
    body = np.clip(np.array(PILL, float)[None, None, :] * g, 0, 255) * np.ones((height, w, 1))
    ta = np.asarray(t, float)[..., None] / 255
    rgb = body * (1 - ta) + np.array(PILL_TXT, float) * ta
    rgba = np.dstack([rgb, np.asarray(m, float)]).astype(np.uint8)
    return Image.fromarray(rgba, 'RGBA')

def round_icon(cx, cy, r):
    """Cut a round icon from the original; the part that touched the oval frame is mirrored."""
    R = int(np.ceil(r + 3))
    ys, xs = np.mgrid[-R:R + 1, -R:R + 1]
    X, Y = xs + cx, ys + cy
    d = np.hypot(xs, ys)
    OCX, OCY, OA, OB = 796.5, 316.4, 269.3, 301.1
    oR = OCX + OA * np.sqrt(np.clip(1 - ((Y - OCY) / OB) ** 2, 0, None))
    bad = X < oR + 8
    Xs = np.where(bad, 2 * cx - X, X)
    xi, yi = np.clip(np.round(Xs).astype(int), 0, src.shape[1] - 1), np.clip(np.round(Y).astype(int), 0, src.shape[0] - 1)
    rgb = src[yi, xi]
    a = np.clip(r + 2.2 - d, 0, 1)
    return Image.fromarray(np.dstack([rgb, a * 255]).astype(np.uint8), 'RGBA')

# ------------------------------------------------------------------ left panel
LX = 100                                   # left edge of the column
L_TEXT_W = 395
pp, _ = asset(315, 86, 548, 141)           # "Propiedades" pill
pi, _ = asset(312, 246, 522, 290)          # "Ingredientes" pill
formula, _ = asset(305, 342, 540, 420)
seals, _ = asset(305, 428, 560, 503)
rule, _ = asset(305, 503, 560, 516)
cal, _ = asset(310, 516, 368, 576)
fecha, fecha_off = asset(368, 518, 535, 546)   # "Fecha de caducidad" (the date line is left out)
brush, _ = asset(330, 572, 592, 710)

tp, _ = text_block(COPY['propiedades'], L_TEXT_W)
ti, _ = text_block(COPY['ingredientes'], L_TEXT_W)

stack = [  # (item, x offset from column, gap above)
    (pp, 0, 0), (tp, 5, 9), (pi, -1, 10), (ti, 5, 8), (formula, -6, 12),
    (seals, -4, 12), (rule, 0, 3),
]
y = 90
for item, dx, gap in stack:
    y += gap
    place(item, LX + dx, y)
    y += item.size[1]
# bottom row: expiry-date caption (date line left blank) beside the "Belleza natural" stroke
fy = y + 12
place(cal, LX, fy)
place(fecha, LX + 60, fy + 4)
by = 714 - brush.size[1]
place(brush, 572 - brush.size[0], by)
y = max(fy + cal.size[1], by + brush.size[1])
print('left column bottom', y)

# ------------------------------------------------------------------ right panel
RX = 1100                                  # left edge of the icons
mu, _ = asset(1054, 86, 1284, 143)         # "Modo de uso" pill
uso, _ = asset(1068, 346, 1300, 409)
rule_r, _ = asset(1080, 409, 1290, 426)
social, _ = asset(1052, 425, 1300, 563)
hp, _ = asset(1010, 563, 1302, 658)
icon1 = round_icon(1089.17, 193.58, 39.6)
icon2 = round_icon(1094.64, 292.44, 38.2)
p1, p2 = pill(COPY['modo1_title']), pill(COPY['modo2_title'])
TX = RX + 88
R_TEXT_W = 1520 - TX
t1, n1 = text_block(COPY['modo1'], R_TEXT_W)
t2, n2 = text_block(COPY['modo2'], R_TEXT_W)

y = 88
place(mu, RX + 6, y); y += mu.size[1]
for pl, tx, icon, gap in ((p1, t1, icon1, 10), (p2, t2, icon2, 10)):
    y += gap
    gh = pl.size[1] + 7 + tx.size[1]
    place(pl, TX - 5, y)
    place(tx, TX, y + pl.size[1] + 7)
    place(icon, RX, y + (gh - icon.size[1]) / 2)
    y += max(gh, icon.size[1])
y += 10; place(uso, RX + 24, y); y += uso.size[1]
y += 4; place(rule_r, RX + 30, y); y += rule_r.size[1]
y += 0; place(social, RX + 6, y); y += social.size[1]
y += 0; place(hp, RX - 34, y); y += hp.size[1]
print('right column bottom', y)

out.convert('RGB').save(dst)
