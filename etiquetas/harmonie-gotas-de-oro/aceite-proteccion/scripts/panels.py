"""Compose the two side panels of the 5 x 2.5 in label with the new copy.

usage: panels.py <base> <out.png>   (needs: pip install segno)
  <base>-plate.png  the empty widened label (1600 x 800), from plate.py
  <base>-layer.png  the model's panel elements (RGBA, model coordinates 1264 x 843)
  <base>-brush.json where the brush strokes' beds lie on the plate

Every graphic element (pills, seals, icons, ornaments, brush strokes) is the model's own artwork;
only the copy is typeset, in PT Serif like the model's text. The Instagram QR is a real code.
"""
import os, sys, json, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'scripts'))
import segno
import typeset

base, dst = sys.argv[1], sys.argv[2]
plate = Image.open(base + '-plate.png').convert('RGBA')
layer = Image.open(base + '-layer.png').convert('RGBA')
beds = json.load(open(base + '-brush.json'))
W, H = plate.size
SC = H / layer.size[1]                       # model -> label scale (800 / 843)

typeset.FONT = 'PTSerif-Regular.ttf'
INK = (36, 16, 60)                           # the model's dark aubergine copy
BODY_SIZE, BODY_LH = 20, 25
INSTAGRAM = 'https://www.instagram.com/harmonieproducts'

COPY = {
    'propiedades': 'Mezcla nutritiva de aceites diseñada para crear una barrera protectora que '
                   'ayuda a conservar la humedad natural del cabello, reducir la resequedad y '
                   'mejorar la apariencia de las hebras frente a las agresiones ambientales y el '
                   'desgaste diario.',
    'ingredientes': 'Aceite de salvado de arroz, aceite de jojoba, aceite de argán, aceite de '
                    'aguacate, vitamina E, aceite de oliva, aceite de ricino, aceite de coco y '
                    'fragancia natural.',
    'modo': 'Humedecer el cabello y aplicar el producto. Peinar como de costumbre o disfrutar '
            'del clima, playa o piscina.',
}

out = plate.copy()

def asset(x0, y0, x1, y1, scale=SC):
    """A model element, cropped tight to its visible pixels and scaled to the label."""
    im = layer.crop((x0, y0, x1, y1))
    im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
    return im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)

def place(im, x, y):
    out.alpha_composite(im, (int(round(x)), int(round(y))))

def text(s, width):
    return typeset.text_block(s, width, BODY_SIZE, BODY_LH, INK)[0]

# ------------------------------------------------------------------ left panel
def brush(k, anchor):
    """A brush stroke back on its bed (which the widening stretched): flush with the bed's end
    nearest the leaves, so the plain part of the bed is what stays uncovered."""
    im = Image.open('%s-%s.png' % (base, k))
    im = im.resize((round(im.width * SC), round(im.height * SC)), Image.LANCZOS)
    bd = beds[k]
    (mx0, my0, mx1, _), (cx0, cy0, cx1, _) = bd['model_box'], bd['cut_box']
    y = bd['plate_y0'] - (my0 - cy0) * SC
    x = bd['plate_x1'] - (mx1 - cx0) * SC if anchor == 'right' else bd['plate_x0'] - (mx0 - cx0) * SC
    place(im, x, y)
    return x, y, im

LX, LW = 40, 452                              # column: x from 40, text 452 px wide
pp = asset(27, 87, 276, 140)                 # "Propiedades" pill
orn = asset(40, 250, 296, 272)               # gold rule with a flower
pi = asset(27, 274, 270, 323)                # "Ingredientes" pill
formula = asset(20, 382, 323, 463, SC * 0.9)
seals = asset(17, 467, 330, 550, SC * 0.85)
fecha = asset(30, 565, 262, 624, SC * 0.85)  # calendar + "Fecha de caducidad" + small rule

tp, ti = text(COPY['propiedades'], LW), text(COPY['ingredientes'], LW)
y = 74
for item, dx, gap in ((pp, 0, 0), (tp, 4, 7), (orn, (LW - orn.width) / 2, 7), (pi, 0, 5),
                      (ti, 4, 7), (formula, 0, 9)):
    y += gap
    place(item, LX + dx, y)
    y += item.height
# the "free" seals with the expiry date beside them
y += 8
place(seals, LX + 2, y)
place(fecha, LX + LW - fecha.width, y + (seals.height - fecha.height) / 2)
y += seals.height
print('left column ends at', y)
# the "Belleza natural" stroke back on its bed, over the leaves it covered in the model
bx, by, bim = brush('belleza', 'left')
print('belleza stroke at', round(bx), round(by), bim.size)

# ------------------------------------------------------------------ right panel
RX0, RX1 = 1112, 1572                        # column
RW = RX1 - RX0
mu = asset(954, 84, 1210, 140)               # "Modo de uso" pill
orn_r = asset(964, 374, 1230, 396)
uso = asset(957, 398, 1238, 453)             # thermometer + "Uso externo..."
line_r = asset(947, 455, 1246, 469)
ig = asset(947, 470, 1110, 516)              # Instagram pill
tt = asset(1100, 470, 1246, 516)             # Tick-tock pill
tt_qr = asset(1100, 517, 1230, 613)          # (decorative QR from the model)

tm = text(COPY['modo'], RW - 8)
QM = 4                                        # Instagram QR module: 4 px = 0.0125 in
qr = segno.make(INSTAGRAM, error='m')
mods = np.array([list(r) for r in qr.matrix_iter(scale=1, border=2)], float)
q = np.kron(mods, np.ones((QM, QM)))
qrgb = (1 - q[..., None]) * 255 + q[..., None] * np.array([24., 8., 36.])
ig_qr = Image.fromarray(np.dstack([qrgb, np.full(q.shape, 255.)]).astype(np.uint8), 'RGBA')
tt_qr = tt_qr.resize((round(tt_qr.width * ig_qr.height / tt_qr.height), ig_qr.height), Image.LANCZOS)
social_h = max(ig.height, tt.height) + 8 + ig_qr.height

hx, hy, _ = brush('harmonieproducts', 'right')
# the column runs from the top of the panel to just above the stroke, its gaps shared out evenly
blocks = [mu, tm, orn_r, uso, line_r]
y0, y1 = 78, hy - 6
gap = (y1 - y0 - sum(b.height for b in blocks) - social_h - 8) / 5
y = y0
place(mu, RX0, y); y += mu.height + 8
place(tm, RX0 + 4, y); y += tm.height + gap
place(orn_r, RX0 + (RW - orn_r.width) / 2, y); y += orn_r.height + gap
place(uso, RX0 + 6, y); y += uso.height + gap
place(line_r, RX0 + (RW - line_r.width) / 2, y); y += line_r.height + gap
# social: pill over its code, the two pairs centred in the two halves of the column
for pill, code, cx in ((ig, ig_qr, RX0 + RW * 0.25), (tt, tt_qr, RX0 + RW * 0.75)):
    place(pill, cx - pill.width / 2, y)
    place(code, cx - code.width / 2, y + pill.height + 8)
print('right column: gap %.1f, QR codes end at %d, stroke at %d,%d | Instagram QR %s, version %d-%s'
      % (gap, y + social_h, hx, hy, ig_qr.size, qr.version, qr.error))

out.convert('RGB').save(dst)
