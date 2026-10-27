"""Lift the Harmonie logo (butterfly + lettering + (R)) off the "Aceite de protección" label.

usage: logo.py <modelo.png> <out.png>
The logo sits on the oval's smooth cream glow: the background under it is rebuilt by harmonic
inpainting, and the logo's colour is un-blended from it, so it keeps its soft anti-aliased edges.
Only the pieces that hold purple are kept, which drops the gold sprigs and sparkles around it.
"""
import os, sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import inpaint

src, dst = sys.argv[1], sys.argv[2]
X0, Y0, X1, Y1 = 520, 30, 1080, 348                 # logo box on the 1600 x 800 label
a = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)[Y0:Y1, X0:X1]
r, g, b = a[..., 0], a[..., 1], a[..., 2]
mx, mn = a.max(2), a.min(2)
sat = (mx - mn) / np.maximum(mx, 1)

gold = (r - b > 60) & (g > 110) & ~((b - g > 25) & (r - g > 10))
purple = (b - g > 25) & (r - g > 10)
ink = ((sat > 0.22) | (mx < 170)) & ~gold           # anything that is not pale cream nor gold
lab, n = ndi.label(ink)
H, W = ink.shape
keep = np.zeros_like(ink)
for k, sl in enumerate(ndi.find_objects(lab), 1):
    ys, xs = sl
    if ys.start == 0 or xs.start == 0 or xs.stop == W:  # the oval frame's lilac leaves touch the box edge
        continue
    cy, cx = (ys.start + ys.stop) / 2, (xs.start + xs.stop) / 2
    if (cx < 140 and cy < 140) or (cx > W - 80 and cy < 255) or cx > W - 25 or (cx > 300 and cy < 60):
        continue
    piece = lab[sl] == k
    if (purple[sl] & piece).sum() >= 1 or (piece.sum() < 400 and xs.start > W - 60):   # (and the small (R))
        keep[sl] |= piece
# the butterfly's yellow and orange were left out with the gold: they are enclosed by its purple outline
keep = ndi.binary_fill_holes(ndi.binary_closing(keep, iterations=2))
hole = ndi.binary_dilation(keep, iterations=3)
bg = inpaint(a, hole, 300)

diff = a - bg
dd = np.sqrt((diff ** 2).sum(2))
alpha = np.clip((dd - 4) / 40.0, 0, 1) * hole
alpha = np.maximum(alpha, ndi.binary_erosion(keep, iterations=1))   # solid inside the shapes
fg = np.clip(bg + diff / np.maximum(alpha, 1e-3)[..., None], 0, 255)
im = Image.fromarray(np.dstack([fg, alpha * 255]).astype(np.uint8), 'RGBA')
im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 10 else 0).getbbox())
im.save(dst)
print(dst, im.size)
