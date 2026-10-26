"""Turn the 996x800 label (centred on a white 1600x800 canvas) into a full-bleed 2:1 label.

1. lift the text/graphic blocks off the two side panels,
2. rebuild the empty panels and extend the artwork to the canvas edges,
3. put the blocks back, spread outwards so the panels are balanced in the wider format.
"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0, sys.path[0])
from common import inpaint

src, dst, shift = sys.argv[1], sys.argv[2], int(sys.argv[3])
a = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
H, W = a.shape[:2]
yy, xx = np.mgrid[0:H, 0:W]
CREAM = np.array([254., 247., 234.])
dist = np.sqrt(((a - CREAM) ** 2).sum(2))

# central oval (gold frame), fitted to its border; content masks must stay clear of it
OCX, OCY, OA, OB = 796.5, 316.4, 269.3, 301.1
t = np.clip(1 - ((np.arange(H) - OCY) / OB) ** 2, 0, None)
half = np.where(t > 0, OA * np.sqrt(t), -1e4)
ovalL = (OCX - half)[:, None]
ovalR = (OCX + half)[:, None]

# (x0, x1, y0, y1, threshold, core) -- core: keep only components touching this rect
LEFT = [
    (320, 548, 90, 141, 14, None),      # Propiedades
    (318, 548, 141, 246, 14, None),     # descripcion
    (312, 522, 247, 290, 14, None),     # Ingredientes
    (318, 532, 290, 341, 14, None),     # lista de ingredientes
    (310, 534, 342, 418, 7, None),      # Formula rica...
    (310, 556, 430, 516, 9, None),      # sellos + linea divisoria
    (316, 532, 516, 574, 14, None),     # Fecha de caducidad
    (336, 590, 566, 704, 12, (380, 560, 600, 680)),   # Belleza natural en cada gota
]
RIGHT = [
    (1054, 1280, 88, 143, 14, None),    # Modo de uso
    (1046, 1292, 143, 251, 12, None),   # Modo 1
    (1054, 1297, 251, 338, 12, None),   # Modo 2
    (1072, 1297, 348, 409, 14, None),   # Uso externo
    (1080, 1280, 409, 425, 5, None),    # linea divisoria
    (1058, 1296, 425, 562, 14, None),   # redes + QR
    (1018, 1297, 566, 656, 12, (1060, 1280, 588, 640)),  # Harmonieproducts
]

def block_mask(x0, x1, y0, y1, thr, core, side):
    m = np.zeros((H, W), bool)
    if core:
        # brush-stroke banners: take the saturated purple stroke itself, not the pale paper around it
        r, g = a[..., 0], a[..., 1]
        m[y0:y1, x0:x1] = (r - g)[y0:y1, x0:x1] > 25
        lab, n = ndi.label(m)
        # cut thin bridges to neighbouring leaves before picking the stroke
        op = ndi.binary_opening(m, iterations=4)
        ol, on = ndi.label(op)
        cx0, cx1, cy0, cy1 = core
        keep = np.unique(ol[cy0:cy1, cx0:cx1])
        main = np.isin(ol, keep[keep > 0])
        main = ndi.binary_dilation(main, iterations=5) & m
        main = ndi.binary_fill_holes(main)
        # loose bristle specks of the stroke travel with it
        # (sizes measured on the whole image so leaves clipped by the box don't look like specks)
        fl, fn = ndi.label((r - g) > 25)
        sizes = ndi.sum(np.ones_like(fl), fl, index=np.arange(1, fn + 1))
        small = np.isin(fl, np.where(sizes < 150)[0] + 1)
        near = ndi.binary_dilation(main, iterations=30)
        boxm = np.zeros((H, W), bool); boxm[y0:y1, x0:x1] = True
        dl, dn = ndi.label((dist > 35) & ~main)
        dsz = ndi.sum(np.ones_like(dl), dl, index=np.arange(1, dn + 1))
        dark_small = np.isin(dl, np.where(dsz < 40)[0] + 1)
        specks = (small | dark_small) & near & boxm
        m = ndi.binary_dilation(main | specks, iterations=2)
    else:
        m[y0:y1, x0:x1] = dist[y0:y1, x0:x1] > thr
        m = ndi.binary_closing(m, iterations=2) | m
    # stay off the oval's gold frame and its warm glow; only purple ink may come closer
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    ink = (b - g > 8) & (r - g > 5)
    box = np.zeros((H, W), bool)
    if not core:                      # brush strokes sit among lavender leaves: no ink grab there
        box[y0:y1, x0:x1] = True
    if side == 'L':
        m = (m & (xx < ovalL - 9)) | (box & ink & (xx < ovalL + 2))
    else:
        m = (m & (xx > ovalR + 9)) | (box & ink & (xx > ovalR - 2))
    return m

mL = np.zeros((H, W), bool); mR = np.zeros((H, W), bool)
for blk in LEFT:
    mL |= block_mask(*blk, 'L')
for blk in RIGHT:
    mR |= block_mask(*blk, 'R')
hole = ndi.binary_dilation(mL | mR, iterations=3)
ink = (a[..., 2] - a[..., 1] > 8) & (a[..., 0] - a[..., 1] > 5)
hole &= (xx < ovalL - 3) | (xx > ovalR + 3) | (yy > OCY + OB) | (ink & (mL | mR))
# tinted fringe where a block touched the frame (not the gold itself)
not_gold = (a[..., 0] - a[..., 2]) < 40
fringe = (((xx >= ovalL - 10) & (xx < ovalL + 1)) | ((xx <= ovalR + 10) & (xx > ovalR - 1))) & (yy < OCY + OB)
hole |= fringe & not_gold & ndi.binary_dilation(mL | mR, iterations=6)
clean = inpaint(a, hole, 250)
# soften the fill so no streaks of the frame's glow are left behind
soft = np.stack([ndi.gaussian_filter(clean[..., c], 2.0) for c in range(3)], -1)
clean[hole] = soft[hole]

diff = a - clean
dd = np.sqrt((diff ** 2).sum(2))
alpha = np.clip((dd - 3) / 30.0, 0, 1) * hole
fg = clean + diff / np.maximum(alpha, 1e-3)[..., None]

# ---------------- plate: the empty label extended to the full canvas
def refl(k, w):
    m = k % (2 * w)
    return m if m <= w else 2 * w - m

def extend(axis_l, wl, axis_r, wr):
    e = clean.copy()
    for x in range(0, axis_l):
        e[:, x] = clean[:, axis_l + refl(axis_l - x, wl)]
    for x in range(axis_r + 1, W):
        e[:, x] = clean[:, axis_r - refl(x - axis_r, wr)]
    return e

# leaf band at the top: wide mirror for a natural look; panel + gold rule: mirror where the
# rule is perfectly straight so it continues without kinks
AL, AR = 410, 1220
top = extend(335, 170, 1270, 170)
mid = extend(AL, 95, AR, 130)
plate = mid.copy()
wt = np.clip((62 - np.arange(H)) / 6.0, 0, 1)[:, None, None]          # rows < 56 -> top
plate = top * wt + plate * (1 - wt)
wb = np.clip((np.arange(H) - 634) / 12.0, 0, 1)[:, None, None]        # rows > 646 -> top (right bottom band)
right = (np.arange(W) > AR)[None, :, None]
plate = np.where(right, top * wb + plate * (1 - wb), plate)

# bottom-left: the panel's lower gold rule runs straight; rebuild cream / rule / leaf band
YB, XJ = 556, 400                          # region rebuilt: y >= YB, x < XJ
LINE0, LINE1 = 724, 736                   # rows spanning the gold rule (incl. soft edges)
syn = np.zeros((H - YB, XJ, 3))
prof = np.median(clean[YB:, 410:470], axis=1)          # rule / band, per row
paper = np.median(plate[530:556, 0:AL].reshape(-1, 3), axis=0)
prof[:LINE0 - 2 - YB] = paper                            # plain panel above the rule
syn[:] = prof[:, None, :]
band0 = LINE1 - YB
for x in range(XJ):
    syn[band0:, x] = clean[LINE1:, XJ + refl(XJ - x, 160)]
wj = np.clip((np.arange(XJ) - (XJ - 24)) / 24.0, 0, 1)[None, :, None]   # blend into original
cur = syn * (1 - wj) + clean[YB:, :XJ] * wj
wv = np.clip((np.arange(H - YB)) / 16.0, 0, 1)[:, None, None]            # blend from rows above
plate[YB:, :XJ] = plate[YB:, :XJ] * (1 - wv) + cur * wv

# the leaf cluster that sat in the panel's bottom-left corner goes back to the new corner
CX0, CX1, CY0 = 305, 400, 556
blk = clean[CY0:, CX0:CX1]
bh, bw = blk.shape[:2]
r_, g_, b_ = blk[..., 0], blk[..., 1], blk[..., 2]
leaf = ((r_ - g_ > 22) | (g_ - r_ > 8) | (blk.mean(2) < 200))      # purple or green foliage
leaf = ndi.binary_opening(leaf, iterations=1)
la = ndi.gaussian_filter(ndi.binary_dilation(leaf, iterations=1).astype(float), 0.8)
rows = np.arange(bh)[:, None] + CY0
la = np.where(rows >= LINE0 - 2, 1.0, la)                  # rule + band below: copy as is
fx = np.clip((bw - 1 - np.arange(bw)) / 18.0, 0, 1)[None, :]
fy = np.clip(np.arange(bh) / 18.0, 0, 1)[:, None]
fm = (la * fx * fy)[..., None]
plate[CY0:, 0:bw] = plate[CY0:, 0:bw] * (1 - fm) + blk * fm

# ---------------- put the content back, moved outwards
out = plate.copy()
for mask, dx in ((mL, -shift), (mR, shift)):
    sel = ndi.binary_dilation(mask, iterations=3)
    ys, xs = np.where(sel)
    nx = xs + dx
    ok = (nx >= 0) & (nx < W)
    al = np.zeros((H, W)); f = np.zeros_like(a)
    al[ys[ok], nx[ok]] = alpha[ys[ok], xs[ok]]
    f[ys[ok], nx[ok]] = fg[ys[ok], xs[ok]]
    out = out * (1 - al[..., None]) + f * al[..., None]

Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)).save(dst)

# optional: export the empty extended background and the lifted blocks (original coordinates)
if len(sys.argv) > 4:
    base = sys.argv[4]
    Image.fromarray(np.clip(plate + 0.5, 0, 255).astype(np.uint8)).save(base + '-plate.png')
    rgba = np.dstack([np.clip(fg, 0, 255), alpha * 255]).astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(base + '-layer.png')
