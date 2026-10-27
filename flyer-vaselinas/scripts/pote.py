"""A jar of Vaselina with its 6 x 2.5 in label: pote.py <label.png> <out.png>

A wide, low jar with a white lid: the whole jar is about as tall as half its width plus a little.
The label's 2.5 in fill the body's height, which sets the jar's scale; at that scale the jar is
wider than the label is long divided by pi, so the label covers only part of the way round and
the white jar shows at the sides. Seen from a little above: the edges bow downward in the middle.
"""
import math, sys, numpy as np
from PIL import Image, ImageFilter

src, dst = sys.argv[1], sys.argv[2]
label = Image.open(src).convert('RGB')

SS = 3
K = 2                                     # drawn at twice the size it shows on the flyer, for print
W = 560 * K                               # jar width (px)
E = 30 * K                                # depth of the ellipses (view from above)
LID = 70 * K                              # white screw lid
LIP = 10 * K                              # bare jar above and below the label
BODY = 300 * K                            # label height (px) = 2.5 in
PPI = BODY / 2.5
R_IN = W / 2 / PPI                        # jar radius in inches
H = E + LID + E + LIP + BODY + LIP + E + 4

# filter the label down to the size it is drawn at before wrapping it, so its fine print stays clean
# (sampling the full-size label straight onto the jar would alias)
LH = BODY * SS
LW = round(label.width * LH / label.height)
lab = np.asarray(label.resize((LW, LH), Image.LANCZOS)).astype(np.float64)

w, h = W * SS, H * SS
x = (np.arange(w) + 0.5) / w * 2 - 1
th = np.arcsin(np.clip(x, -1, 1))
bow = np.cos(th)                          # 1 at the middle, 0 at the sides
img = np.zeros((h, w, 4))
yy = (np.arange(h) + 0.5)[:, None] / SS

lx, lz = -0.4, 1.0
d = np.clip((np.sin(th) * lx + np.cos(th) * lz) / math.hypot(lx, lz), 0, 1)
sh = 0.62 + 0.42 * d ** 1.3
spec = 0.20 * np.exp(-((x + 0.52) / 0.06) ** 2) + 0.08 * np.exp(-((x - 0.7) / 0.05) ** 2)
WHITE = np.array([250., 248., 246.])

def put(mask, col):
    img[..., :3] = np.where(mask[..., None], col, img[..., :3])
    img[..., 3] = np.where(mask, 1, img[..., 3])

# --- body: white plastic, the label round its front
top_body = E + LID
y_rel = yy - top_body - E * bow[None, :]
body_h = LIP + BODY + LIP
inside = (y_rel >= 0) & (y_rel < body_h)
arc = th * R_IN                           # inches round the jar from the front
v = (y_rel - LIP) / BODY
on_label = (v >= 0) & (v < 1) & (np.abs(arc) < 3)[None, :]
u = np.clip((LW / 2 + arc * LW / 6).astype(int), 0, LW - 1)
vi = np.clip((v * LH).astype(int), 0, LH - 1)
col = np.where(on_label[..., None], lab[vi, u[None, :].repeat(h, 0)], WHITE)
put(inside, col * sh[None, :, None] + 255 * spec[None, :, None])
by = top_body + body_h                    # the rounded bottom
bottom = (((yy - by) / E) ** 2 + x[None, :] ** 2 <= 1) & (yy >= by) & ~inside
put(bottom, (WHITE * 0.93) * sh[None, :, None])

# --- lid: white, finely ridged, with an elliptical top
lt = E
ly = yy - lt
in_lid = (ly >= 0) & (ly < LID + E * bow[None, :]) & ~inside
ridges = 0.93 + 0.07 * np.cos(th * 90) ** 2
lid = WHITE[None, :] * (sh * ridges)[:, None] + 255 * spec[:, None]
seam = 1 - 0.16 * np.exp(-((ly - LID - E * bow[None, :]) / 5) ** 2)
put(in_lid, lid[None, :, :] * seam[..., None])
r = np.sqrt(x[None, :] ** 2 + ((yy - lt) / E) ** 2)
top = r <= 1
tcol = WHITE * (1.0 - 0.07 * r[..., None]) + 10 * np.exp(-(((x[None, :] + 0.3) / 0.35) ** 2 + ((yy - lt + E * .3) / (E * .5)) ** 2))[..., None]
tcol = np.where((np.abs(r - 0.92) < 0.025)[..., None], WHITE * 0.86, tcol)
tcol = np.where((r > 0.975)[..., None], WHITE * 0.8, tcol)          # a soft edge so it reads on a pale ground
put(top, tcol)

im = Image.fromarray(np.clip(np.dstack([img[..., :3], img[..., 3] * 255]), 0, 255).astype(np.uint8), 'RGBA')
im = im.resize((W, H), Image.LANCZOS)
rgb = im.convert('RGB').filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
im = Image.merge('RGBA', (*rgb.split(), im.getchannel('A')))
im.save(dst)
print(dst, im.size, 'label covers %.0f deg of the jar' % math.degrees(6 / R_IN))
