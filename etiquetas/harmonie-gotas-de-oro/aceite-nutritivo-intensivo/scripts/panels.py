"""Compose the two side panels of the 5 x 2.5 in label with the new copy.

usage: panels.py <base> <out.png>   (needs: pip install segno)
  <base>-plate.png  the empty widened label (1600 x 800), from plate.py
  <base>-layer.png  the model's panel elements (RGBA, model coordinates 1376 x 768)

Every graphic element (pills, seals, icons, ornaments, brush strokes) is the model's own artwork,
but for the expiry-date calendar, which is redrawn; the copy is typeset, justified, in PT Serif like the model's text. The Instagram QR is a real code.
"""
import os, sys, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'scripts'))
import segno
import typeset
import rico
from fonts import font
from boxes import BOXES, SEALS

base, dst = sys.argv[1], sys.argv[2]
plate = Image.open(base + '-plate.png').convert('RGBA')
layer = Image.open(base + '-layer.png').convert('RGBA')
W, H = plate.size
SC = H / layer.size[1]                       # model -> label scale (800 / 768)

typeset.FONT = 'PTSerif-Regular.ttf'
INK = (40, 22, 6)                            # the model's dark brown copy
BODY_SIZE, BODY_LH = 19, 24
TOP_Y = 122                                  # both columns start below the leaves of the top corners
INSTAGRAM = 'https://www.instagram.com/harmonieproducts'

COPY = {
    'propiedades': 'Ayuda a acondicionar intensamente el cabello seco, aportando suavidad, brillo y una '
                   'apariencia más saludable. Contribuye a mejorar la manejabilidad y a reducir la sensación '
                   'de aspereza, dejando el cabello con una apariencia más flexible y nutrida.',
    'ingredientes': 'Aceite de batana, aceite de argán, manteca de karité, aceite de aguacate, vitamina E, '
                    'aceite de oliva, aceite de ricino, aceite de coco.',
    'modo': [
        [('1. Como tratamiento pre-poo:', True),
         ('Mezclar 1 cucharada de aceite con 1 cucharada de tu mascarilla capilar habitual. Aplicar en el '
          'cabello y dejar actuar durante 20 o 30 minutos antes de lavar como de costumbre.', False)],
        [('2. Uso profundo:', True),
         ('Aplicar en el cuero cabelludo y la hebra capilar, colocar un gorro plástico. Dejar actuar '
          'durante unas horas o toda la noche y retirar con el lavado habitual.', False)],
    ],
}

out = plate.copy()

def seal_mask(box):
    x0, y0, x1, y1 = box
    yy, xx = np.mgrid[y0:y1, x0:x1]
    m = np.zeros(yy.shape, bool)
    for cx, cy, r in SEALS:
        m |= (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    return m

def asset(name, scale=SC):
    """A model element, cropped tight to its visible pixels and scaled to the label."""
    im = layer.crop(BOXES[name])
    if name in ('sellos', 'belleza'):
        m = seal_mask(BOXES[name])
        al = np.asarray(im.getchannel('A'), float) * (m if name == 'sellos' else ~m)
        im.putalpha(Image.fromarray(al.astype(np.uint8)))
    if name == 'filete_r':                   # leave out the top of the thermometer
        x0, y0 = BOXES[name][:2]
        tx1, ty0 = BOXES['termometro'][2], BOXES['termometro'][1]
        al = np.asarray(im.getchannel('A')).copy()
        al[ty0 - y0:, :tx1 - x0] = 0
        im.putalpha(Image.fromarray(al))
    im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
    return im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)

def place(im, x, y):
    out.alpha_composite(im, (int(round(x)), int(round(y))))

def text(s, width, size=BODY_SIZE, lh=BODY_LH):
    return typeset.text_block(s, width, size, lh, INK, weight=None)[0]

def fecha_block():
    """Calendar + "Fecha de caducidad" + a small gold rule, drawn afresh: the model's own one carries the
    lighter gold it sat on, which shows as a pale halo on this darker part of the label."""
    S = 4
    CAL = (62, 34, 10)                       # the model's icon brown
    cw, gap, size = 40, 12, 18
    f = font('PTSerif-Regular.ttf', size * S)
    label = 'Fecha de caducidad'
    tw = f.getlength(label) / S
    w, h = int(cw + gap + tw + 4), 46
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = lambda *v: [c * S for c in v]
    # calendar: rounded body, filled header, two rings, check mark
    d.rounded_rectangle(s(2, 7, cw - 2, h - 3), radius=6 * S, outline=CAL + (255,), width=round(3.2 * S))
    d.rounded_rectangle(s(2, 7, cw - 2, 16), radius=6 * S, fill=CAL + (255,))
    d.rectangle(s(2, 12, cw - 2, 16), fill=CAL + (255,))
    for rx in (11, cw - 15):
        d.rounded_rectangle(s(rx, 2, rx + 4, 12), radius=2 * S, fill=CAL + (255,))
    d.line(s(11.5, 29, 17.5, 35, 28.5, 23), fill=CAL + (255,), width=round(3.8 * S), joint='curve')
    for cx, cy in ((11.5, 29), (28.5, 23)):
        r = 1.9 * S
        d.ellipse((cx * S - r, cy * S - r, cx * S + r, cy * S + r), fill=CAL + (255,))
    # label, its cap height level with the top of the calendar body
    tx = (cw + gap) * S
    d.text((tx, 9 * S - f.getbbox('F')[1]), label, font=f, fill=INK + (255,))
    im = im.resize((w, h), Image.LANCZOS)
    # a thin gold rule under the label, fading at its ends, with a small four-point star in the middle
    rw = tw * 0.92
    x0 = cw + gap + (tw - rw) / 2
    ry, cx = h - 7, cw + gap + tw / 2
    rule = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rule)
    dark, light = np.array([176., 124., 38.]), np.array([250., 220., 140.])
    for i in range(int(rw * S)):
        t = i / (rw * S)
        fade = min(1.0, t / 0.18, (1 - t) / 0.18)
        col = dark + (light - dark) * (1 - abs(t - 0.5) * 2) ** 2
        rd.line([(x0 * S + i, ry * S - 0.7 * S), (x0 * S + i, ry * S + 0.7 * S)],
                fill=tuple(int(c) for c in col) + (int(255 * fade),))
    for r, col in ((6.5, (176, 124, 38)), (5.0, (252, 226, 150))):
        k = 0.22 * r
        pts = [(cx, ry - r), (cx + k, ry - k), (cx + r, ry), (cx + k, ry + k),
               (cx, ry + r), (cx - k, ry + k), (cx - r, ry), (cx - k, ry - k)]
        rd.polygon([(px * S, py * S) for px, py in pts], fill=col + (255,))
    im.alpha_composite(rule.resize((w, h), Image.LANCZOS))
    return im

# ------------------------------------------------------------------ left panel
LX, LW = 40, 496                             # column: x from 40 to the oval's glow (496: the evenest lines)
pp = asset('propiedades')
orn = asset('filete')
pi = asset('ingredientes')
formula = asset('formula', SC * 0.9)
belleza = asset('belleza', SC * 0.8)
seals = asset('sellos', SC * 0.74)
fecha = fecha_block()

tp, ti = text(COPY['propiedades'], LW), text(COPY['ingredientes'], LW)
y = TOP_Y
for item, dx, gap in ((pp, 0, 0), (tp, 4, 8), (orn, (LW - orn.width) / 2, 8), (pi, 0, 6), (ti, 4, 8)):
    y += gap
    place(item, LX + dx, y)
    y += item.height
# "Formula rica..." with the "Belleza natural" stroke beside it
y += 10
row = max(formula.height, belleza.height)
place(formula, LX, y + (row - formula.height) / 2)
place(belleza, LX + LW - belleza.width, y + (row - belleza.height) / 2)
y += row + 6
# the "free" seals, and the expiry date in the free space under them, between the leaves at the foot
SX = LX + 60
place(seals, SX, y)
y += seals.height + 6
place(fecha, SX + (seals.width - fecha.width) / 2, y)
y += fecha.height
print('left column ends at', y)

# ------------------------------------------------------------------ right panel
RX0, RX1 = 1060, 1564                        # column
RW = RX1 - RX0
mu = asset('modo')                           # "Modo de uso" pill, at the head of the column
orn_r = asset('filete_r', SC * 0.95)
termo = asset('termometro', SC * 0.7)
ig = asset('instagram')
tt = asset('tiktok')
tt_qr = asset('qr_tiktok')                   # (decorative QR from the model, as on the other labels)
hp = asset('harmonieproducts')

steps = [rico.block(p, RW - 8, BODY_SIZE, BODY_LH, INK, 'PTSerif-Regular.ttf', 'PTSerif-Bold.ttf')
         for p in COPY['modo']]
uso = [typeset.text_block(s, 400, 17, 21, INK, weight=None, justify=False)[0]
       for s in ('Uso externo.', 'No someter a calor extremo.')]
QM = 4                                       # Instagram QR module: 4 px = 0.0125 in
qr = segno.make(INSTAGRAM, error='m')
mods = np.array([list(r) for r in qr.matrix_iter(scale=1, border=2)], float)
q = np.kron(mods, np.ones((QM, QM)))
qrgb = (1 - q[..., None]) * np.array([244., 232., 200.]) + q[..., None] * np.array([24., 12., 2.])
ig_qr = Image.fromarray(np.dstack([qrgb, np.full(q.shape, 255.)]).astype(np.uint8), 'RGBA')
tt_qr = tt_qr.resize((round(tt_qr.width * ig_qr.height / tt_qr.height), ig_qr.height), Image.LANCZOS)
social_h = max(ig.height, tt.height) + 8 + ig_qr.height

y0, y1 = TOP_Y, 712                          # from below the top leaves to the leaves at the foot
used = mu.height + 8 + sum(s.height for s in steps) + 8 + orn_r.height + termo.height + social_h + hp.height
gap = (y1 - y0 - used) / 4
print('right column: free %.1f px -> gap %.1f' % (y1 - y0 - used, gap))
y = y0
place(mu, RX0, y); y += mu.height + 8
for k, s in enumerate(steps):
    place(s, RX0 + 4, y); y += s.height + (8 if k == 0 else 0)
y += gap
place(orn_r, RX0 + (RW - orn_r.width) / 2, y); y += orn_r.height + gap
place(termo, RX0 + 8, y)
th = sum(u.height for u in uso) + 6
uy = y + (termo.height - th) / 2
for u in uso:
    place(u, RX0 + 8 + termo.width + 14, uy); uy += u.height + 6
y += termo.height + gap
for pill, code, cx in ((ig, ig_qr, RX0 + RW * 0.25), (tt, tt_qr, RX0 + RW * 0.75)):
    place(pill, cx - pill.width / 2, y)
    place(code, cx - code.width / 2, y + pill.height + 8)
y += social_h + gap
place(hp, RX0 + (RW - hp.width) / 2, y)
print('right column ends at %d | Instagram QR %s, version %d-%s' % (y + hp.height, ig_qr.size, qr.version, qr.error))

out.convert('RGB').save(dst)
