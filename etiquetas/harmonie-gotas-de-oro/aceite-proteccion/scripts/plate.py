"""Lift the side-panel elements off the model and widen the empty label to 5 x 2.5 in.

usage: plate.py <titulo.png> <base>
  writes <base>-plate.png  the empty label, 1600 x 800 px (320 ppi)
         <base>-clean.png  the model with its panels cleared (1264 x 843, for the sachet)
         <base>-layer.png  the lifted elements (RGBA, model coordinates, 1264 x 843)
         <base>-<brush>.png the two brush strokes, each on its own (RGBA, model scale)
         <base>-brush.json where the two brush strokes' backgrounds ended up on the plate

The model is 1264 x 843 (3:2). Its panels are cleared, then 211 seams are inserted on each side
(1686 x 843 = 2:1) and the result is scaled to 1600 x 800.
"""
import os, sys, json, numpy as np
from PIL import Image
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'scripts'))
from common import inpaint
from seams import widen

src, base = sys.argv[1], sys.argv[2]
a = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
H, W = a.shape[:2]
r, g, b = a[..., 0], a[..., 1], a[..., 2]

# side-panel elements on plain cream: lifted with their whole box
BOXES = [
    (30, 90, 273, 137),      # Propiedades
    (33, 148, 336, 249),     # descripcion
    (43, 253, 293, 273),     # filete con flor
    (30, 277, 267, 320),     # Ingredientes
    (33, 325, 267, 379),     # lista
    (23, 385, 320, 460),     # Formula rica...
    (20, 470, 327, 547),     # sellos free
    (33, 555, 315, 565),     # linea
    (33, 568, 262, 625),     # Fecha de caducidad
    (957, 87, 1207, 137),    # Modo de uso
    (955, 145, 1249, 369),   # instrucciones
    (967, 373, 1227, 393),   # filete con flor
    (960, 397, 1235, 450),   # Uso externo
    (950, 458, 1243, 466),   # linea
    (950, 473, 1243, 513),   # Instagram / Tick-tock
    (973, 520, 1227, 610),   # QR
]
# brush strokes sit on leaves: lifted by their colour
BRUSHES = {
    'belleza': (52, 610, 346, 764),
    'harmonieproducts': (922, 612, 1252, 706),
}

boxes = np.zeros((H, W), bool)
for x0, y0, x1, y1 in BOXES:
    boxes[y0 - 3:y1 + 3, x0 - 3:x1 + 3] = True

def brush_mask(x0, y0, x1, y1):
    box = np.zeros((H, W), bool)
    box[y0:y1, x0:x1] = True
    lilac = box & (b - g > 14) & (r - g > 8)            # the stroke: lilac to deep purple
    body = ndi.binary_opening(lilac, iterations=3)       # cut thin bridges into the leaves
    lab, n = ndi.label(body)
    sizes = ndi.sum(body, lab, np.arange(1, n + 1))
    main = lab == (np.argmax(sizes) + 1)
    main = ndi.binary_dilation(main, iterations=4) & lilac
    main = ndi.binary_fill_holes(ndi.binary_closing(main, iterations=6))   # + the lettering
    # loose bristle specks near the stroke travel with it
    fl, fn = ndi.label(lilac & ~main)
    fs = ndi.sum(np.ones_like(fl), fl, np.arange(1, fn + 1))
    specks = np.isin(fl, np.where(fs < 60)[0] + 1) & ndi.binary_dilation(main, iterations=14)
    return ndi.binary_dilation(main | specks, iterations=2) & box

bm = {k: brush_mask(*v) for k, v in BRUSHES.items()}
hole = boxes.copy()
leafy = (r - b > 45) | ((b - g > 14) & (r - g > 8))          # gold and lilac leaves stay put
for k, m in bm.items():
    x0, y0, x1, y1 = BRUSHES[k]
    box = np.zeros((H, W), bool); box[y0 - 8:y1 + 8, x0 - 8:x1 + 8] = True
    box &= ~ndi.binary_dilation(boxes, iterations=2)          # never reach into the other elements
    near = ndi.binary_dilation(m, iterations=14) & box
    specks = near & (a.mean(2) < 215) & (b > g)                # stray purple bristle marks
    lum = a.mean(2)                                            # ...and small dark flecks
    dark = (lum < ndi.median_filter(lum, 11) - 18) & ~(r - b > 45)
    dark |= (b - g > 6) & (r - g > 2) & ~m                    # faint lilac flecks too
    dark &= ~ndi.binary_dilation(m, iterations=2)              # (not the stroke's own edge)
    dl, dn = ndi.label(dark & ndi.binary_dilation(m, iterations=22) & box)
    ds = ndi.sum(np.ones_like(dl), dl, np.arange(1, dn + 1))
    specks |= np.isin(dl, np.where(ds < 40)[0] + 1)
    halo = ndi.binary_dilation(m, iterations=7) & ~ndi.binary_dilation(leafy & ~m, iterations=2)
    bm[k] = m | ndi.binary_dilation(specks, iterations=2)
    hole |= ndi.binary_dilation(bm[k], iterations=2) | (halo & box)
clean = inpaint(a, hole, 300)
soft = np.stack([ndi.gaussian_filter(clean[..., c], 1.5) for c in range(3)], -1)
clean[hole] = soft[hole]

# lifted layer: colour un-blended from the clean background
diff = a - clean
dd = np.sqrt((diff ** 2).sum(2))
alpha = np.clip((dd - 3) / 30.0, 0, 1) * hole
fg = np.clip(clean + diff / np.maximum(alpha, 1e-3)[..., None], 0, 255)
Image.fromarray(np.dstack([fg, alpha * 255]).astype(np.uint8), 'RGBA').save(base + '-layer.png')
Image.fromarray(np.clip(clean + 0.5, 0, 255).astype(np.uint8)).save(base + '-clean.png')
cut = {}
for k, m in bm.items():                                  # each stroke on its own, with its glow
    sel = ndi.binary_dilation(m, iterations=7) & hole
    ys, xs = np.where(sel)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    cut[k] = [int(x0), int(y0), int(x1), int(y1)]
    rgba = np.dstack([fg, alpha * sel * 255])[y0:y1, x0:x1]
    Image.fromarray(rgba.astype(np.uint8), 'RGBA').save('%s-%s.png' % (base, k))

# ---- widen: 211 seams in each side panel (left of x=334, right of x=935 the oval is untouched)
K, XL, XR = 211, 334, 935
cost = np.zeros((H, W))
for m in bm.values():                                    # keep the strokes' beds in one piece
    cost[ndi.binary_dilation(m, iterations=6)] = 40.0
left, mapL = widen(clean[:, :XL], cost[:, :XL], K)
right, mapR = widen(clean[:, XR:][:, ::-1], cost[:, XR:][:, ::-1], K)
right = right[:, ::-1]
mapR = (right.shape[1] - 1 - mapR)[:, ::-1]               # new x of each original column
wide = np.concatenate([left, clean[:, XL:XR], right], 1)
NW = wide.shape[1]
OUT_W, OUT_H = 1600, 800
sc = OUT_H / H
plate = Image.fromarray(np.clip(wide + 0.5, 0, 255).astype(np.uint8)).resize((OUT_W, OUT_H), Image.LANCZOS)
plate.save(base + '-plate.png')

def new_x(ys, xs):
    """x on the widened image (before scaling) of model pixels (ys, xs)."""
    lw = left.shape[1]
    return np.where(xs < XL, mapL[ys, np.minimum(xs, XL - 1)],
                    np.where(xs < XR, lw + xs - XL, lw + (XR - XL) + mapR[ys, np.clip(xs - XR, 0, W - XR - 1)]))

# where each stroke's bed now lies, in plate pixels
pos = {}
for k, m in bm.items():
    ys, xs = np.where(m)
    nx = new_x(ys, xs)
    sx = OUT_W / NW
    pos[k] = {'model_box': [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], 'cut_box': cut[k],
              'plate_x0': float(nx.min() * sx), 'plate_x1': float((nx.max() + 1) * sx),
              'plate_y0': float(ys.min() * sc), 'plate_y1': float((ys.max() + 1) * sc)}
json.dump(pos, open(base + '-brush.json', 'w'), indent=1)
print('wide', wide.shape, '->', plate.size, json.dumps(pos))
