"""Lift the side-panel elements off the model and widen the empty label to 5 x 2.5 in.

usage: plate.py <titulo.png> <base>
  writes <base>-plate.png  the empty label, 1600 x 800 px (320 ppi)
         <base>-clean.png  the model with its panels cleared (1376 x 768, for the sachet)
         <base>-layer.png  the lifted elements (RGBA, model coordinates, 1376 x 768)

The model is 1376 x 768. Its panels are cleared, then 80 seams are inserted on each side
(1536 x 768 = 2:1) and the result is scaled to 1600 x 800.
On this gold model every element sits on plain gold, so each one is lifted with its whole box.
"""
import os, sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'scripts'))
from common import inpaint
from seams import widen
sys.path.insert(0, HERE)

src, base = sys.argv[1], sys.argv[2]
a = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
H, W = a.shape[:2]

from boxes import BOXES

hole = np.zeros((H, W), bool)
for x0, y0, x1, y1 in BOXES.values():
    hole[y0 - 2:y1 + 2, x0 - 2:x1 + 2] = True
clean = inpaint(a, hole, 300)
soft = np.stack([ndi.gaussian_filter(clean[..., c], 1.5) for c in range(3)], -1)
clean[hole] = soft[hole]
# the fill is smooth; a faint grain like the model's keeps it from looking flat
rng = np.random.default_rng(7)
clean[hole] += rng.normal(0, 1.2, (int(hole.sum()), 1))

# lifted layer: colour un-blended from the clean background
diff = a - clean
dd = np.sqrt((diff ** 2).sum(2))
alpha = np.clip((dd - 4) / 30.0, 0, 1) * hole
fg = np.clip(clean + diff / np.maximum(alpha, 1e-3)[..., None], 0, 255)
Image.fromarray(np.dstack([fg, alpha * 255]).astype(np.uint8), 'RGBA').save(base + '-layer.png')
Image.fromarray(np.clip(clean + 0.5, 0, 255).astype(np.uint8)).save(base + '-clean.png')

# ---- widen: 80 seams in each side panel (left of x=462, right of x=908 the oval is untouched)
K, XL, XR = 80, 462, 908
cost = np.zeros((H, W))
left, _ = widen(clean[:, :XL], cost[:, :XL], K)
right, _ = widen(clean[:, XR:][:, ::-1], cost[:, XR:][:, ::-1], K)
right = right[:, ::-1]
wide = np.concatenate([left, clean[:, XL:XR], right], 1)
OUT_W, OUT_H = 1600, 800
plate = Image.fromarray(np.clip(wide + 0.5, 0, 255).astype(np.uint8)).resize((OUT_W, OUT_H), Image.LANCZOS)
plate.save(base + '-plate.png')
sc = OUT_W / wide.shape[1]
print('wide', wide.shape, '->', plate.size, '| oval on the plate: x %.0f..%.0f'
      % ((XL + K) * sc, (XR + K) * sc))
