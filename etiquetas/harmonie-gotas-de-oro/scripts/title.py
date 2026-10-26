"""Remove the word "protector" from the purple banner and re-centre "Aceite nutritivo" on the arc.

The original lettering is reused (rotated along the banner's arc) so the typeface stays identical.
"""
import sys, numpy as np
from PIL import Image
sys.path.insert(0, sys.path[0])
from common import dilate, inpaint

src, dst = sys.argv[1], sys.argv[2]
a = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
H, W = a.shape[:2]
cx, cy = 797.96, 1332.01            # centre of the banner arc (fitted to its top edge)
yy, xx = np.mgrid[0:H, 0:W]
rr = np.hypot(xx - cx, yy - cy)
th = np.degrees(np.arctan2(xx - cx, cy - yy))
r, g, b = a[..., 0], a[..., 1], a[..., 2]
lum = a.mean(2)

roi = (rr > 880) & (rr < 950) & (xx > 585) & (xx < 1012)
purple = roi & (b - g > 40) & (r - g > 25)
# banner = purple plus the holes it encloses (the lettering)
from collections import deque
outside = ~purple & roi
# flood fill from ROI border through non-purple pixels: those are outside the banner
seen = np.zeros_like(outside)
q = deque()
ys, xs = np.where(roi)
for y, x in zip(ys, xs):
    if outside[y, x] and (not roi[y - 1, x] or not roi[y + 1, x] or not roi[y, x - 1] or not roi[y, x + 1]):
        seen[y, x] = True; q.append((y, x))
while q:
    y, x = q.popleft()
    for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
        if outside[ny, nx] and not seen[ny, nx]:
            seen[ny, nx] = True; q.append((ny, nx))
banner = roi & ~seen
inner = banner & ~dilate(~banner, 3)
light = banner & (lum > 125) & ~dilate(~banner, 2) & (xx > 620) & (xx < 978)
# the descender of the old "p" reaches the banner's lower edge
light |= banner & (lum > 105) & (xx > 840) & (xx < 864) & (yy > 425)
tmask = dilate(light, 4) & banner

# smooth model of the banner colour in polar coordinates
fit_px = inner & ~tmask
tn = th / 15.0
rn = (rr - 915) / 25.0
def basis(t, rv):
    return np.stack([t ** i * rv ** j for i in range(7) for j in range(3)], -1)
Bm = basis(tn[fit_px], rn[fit_px])
coef = np.linalg.lstsq(Bm, a[fit_px], rcond=None)[0]
model = np.zeros_like(a)
model[banner] = basis(tn[banner], rn[banner]) @ coef
resid = np.zeros_like(a)
resid[banner] = a[banner] - model[banner]
resid_f = inpaint(resid, tmask, 150)
P = a.copy()
P[tmask] = model[tmask] + resid_f[tmask]

# decompose lettering into white coverage (alpha) and a soft dark shadow (s)
Wc = np.array([255., 252., 255.])
d = Wc - P
alpha = np.clip(((a - P) * d).sum(2) / np.maximum((d * d).sum(2), 1), 0, 1) * tmask
alpha[alpha < 0.03] = 0
lp = P.mean(2)
s = np.clip(1 - lum / np.maximum(lp, 1), 0, 0.6) * tmask * (alpha == 0)

gap_x = 842                          # gap between "nutritivo" and "protector"
keep = xx < gap_x
ys, xs = np.where((alpha > 0.3) & keep)
angs = np.degrees(np.arctan2(xs - cx, cy - ys))
centre = (angs.min() + angs.max()) / 2
print('phrase angular span %.2f..%.2f, shifting by %.2f deg' % (angs.min(), angs.max(), -centre))

def rotate(m):
    im = Image.fromarray(m.astype(np.float32), mode='F')
    # PIL rotates counter-clockwise for positive angles; clockwise along the arc = positive x
    return np.asarray(im.rotate(centre, resample=Image.BICUBIC, center=(cx, cy)))
na = np.clip(rotate(alpha * keep), 0, 1)
ns = np.clip(rotate(s * keep), 0, 1)

out = P * (1 - ns[..., None]) * (1 - na[..., None]) + Wc * na[..., None]
res = a.copy()
res[banner] = out[banner]

# where the old "p" descender crossed the banner's lower edge, rebuild that stretch of the edge
# from the clean edge just to its left, following the arc
XL, XR, Y0, Y1 = 832, 874, 430, 450
ref = res[Y0 - 4:Y1 + 4, XL].copy()
def edge_y(x):
    return cy - np.sqrt(893.0 ** 2 - (x - cx) ** 2)
for x in range(XL + 1, XR):
    dy = edge_y(x) - edge_y(XL)
    ys = np.arange(Y0, Y1) - dy - (Y0 - 4)
    i0 = np.clip(np.floor(ys).astype(int), 0, len(ref) - 2)
    t = (ys - np.floor(ys))[:, None]
    col = ref[i0] * (1 - t) + ref[i0 + 1] * t
    w = min(1.0, (x - XL) / 4.0, (XR - x) / 4.0)          # blend in/out at the ends
    res[Y0:Y1, x] = res[Y0:Y1, x] * (1 - w) + col * w
Image.fromarray(np.clip(res + 0.5, 0, 255).astype(np.uint8)).save(dst)
