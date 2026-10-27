"""A jar of Vaselina with its 6 x 2.5 in label wrapped around it: pote.py <label.png> <out.png>

The label goes all the way round the jar, so the front shows half of it (the 3 in around the oval).
Seen from a little above, so the label's edges and the lid bow downward toward the middle.
"""
import math, sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter

src, dst = sys.argv[1], sys.argv[2]
lab = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
LH, LW = lab.shape[:2]

SS = 3
W = 560                                   # jar width (px)
E = 34                                    # depth of the ellipses (view from above)
BODY = round(W * (2.5 / (6 / math.pi)))   # label height for this diameter, keeps the true proportion
LIP = 16                                  # bare jar above and below the label
LID = 118
H = E + LID + E + LIP + BODY + LIP + E + 4  # lid top, lid, bow of the body top, body, bow of the bottom

w, h = W * SS, H * SS
x = (np.arange(w) + 0.5) / w * 2 - 1
th = np.arcsin(np.clip(x, -1, 1))
bow = np.cos(th)                          # 1 at the middle, 0 at the sides
img = np.zeros((h, w, 4))
yy = (np.arange(h) + 0.5)[:, None] / SS

def shade(th):
    lx, lz = -0.4, 1.0
    n = math.hypot(lx, lz)
    d = np.clip(np.sin(th) * lx / n + np.cos(th) * lz / n, 0, 1)
    return 0.55 + 0.48 * d ** 1.3

sh = shade(th)
spec = 0.20 * np.exp(-((x + 0.52) / 0.06) ** 2) + 0.08 * np.exp(-((x - 0.7) / 0.05) ** 2)

# --- jar body (white plastic) with the label
top_body = E + LID                        # where the body's top edge sits at the sides
y_rel = yy - top_body - E * bow[None, :]  # distance below the body's top edge, following the bow
body_h = LIP + BODY + LIP
inside = (y_rel >= 0) & (y_rel < body_h)
col = np.ones((h, w, 3)) * np.array([246., 242., 238.])
v = (y_rel - LIP) / BODY
on_label = (v >= 0) & (v < 1)
u = np.clip((LW / 2 + th / (math.pi / 2) * (LW / 4)).astype(int), 0, LW - 1)
vi = np.clip((v * LH).astype(int), 0, LH - 1)
col = np.where(on_label[..., None], lab[vi, u[None, :].repeat(h, 0)], col)
col = col * sh[None, :, None] + 255 * spec[None, :, None]
img[..., :3] = np.where(inside[..., None], col, img[..., :3])
img[..., 3] = np.where(inside, 1, img[..., 3])
# the bottom rounds off: an ellipse under the body
by = top_body + body_h
ell = ((yy - by) / E) ** 2 + x[None, :] ** 2 <= 1
bottom = ell & (yy >= by)
img[..., :3] = np.where(bottom[..., None], np.array([236., 230., 224.]) * sh[None, :, None], img[..., :3])
img[..., 3] = np.where(bottom, 1, img[..., 3])

# --- gold lid: a ridged cylinder with an elliptical top
lt = E                                    # lid's top edge at the sides
ly = yy - lt
in_lid = (ly >= 0) & (ly < LID + E * bow[None, :]) & ~inside
ridges = 0.86 + 0.14 * np.cos(th * 70) ** 2
gold_dark, gold_light = np.array([150., 102., 30.]), np.array([255., 233., 160.])
g = gold_dark + (gold_light - gold_dark) * np.clip((sh - 0.55) / 0.5, 0, 1)[:, None]
g = g * ridges[:, None] + 255 * spec[:, None] * 1.2
band = 1 - 0.18 * np.exp(-((ly - LID - E * bow[None, :]) / 6) ** 2)      # dark seam where it meets the jar
img[..., :3] = np.where(in_lid[..., None], g[None, :, :] * band[..., None], img[..., :3])
img[..., 3] = np.where(in_lid, 1, img[..., 3])
top = ((yy - lt) / E) ** 2 + x[None, :] ** 2 <= 1
r = np.sqrt(x[None, :] ** 2 + ((yy - lt) / E) ** 2)
tcol = gold_light[None, None, :] * (1 - 0.35 * r[..., None]) + gold_dark * 0.35 * r[..., None]
tcol = tcol + 40 * np.exp(-(((x[None, :] + 0.3) / 0.3) ** 2 + ((yy - lt + E * 0.3) / (E * 0.4)) ** 2))[..., None]
ring = np.abs(r - 0.93) < 0.03
tcol = np.where(ring[..., None], gold_dark, tcol)
img[..., :3] = np.where(top[..., None], tcol, img[..., :3])
img[..., 3] = np.where(top, 1, img[..., 3])

im = Image.fromarray(np.clip(np.dstack([img[..., :3], img[..., 3] * 255]), 0, 255).astype(np.uint8), 'RGBA')
im = im.resize((W, H), Image.LANCZOS)
im.save(dst)
print(dst, im.size)
