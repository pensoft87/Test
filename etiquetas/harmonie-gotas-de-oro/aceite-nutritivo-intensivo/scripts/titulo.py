"""Replace the lettering on the brown banner ("Aceite nutricion intensiva") with
"Aceite nutritivo intensivo", and fix two spellings of the model ("Tick-tock", "SILICONY").

The model is 1376 x 768 and is worked at that size. "GOTAS DE ORO" stays as it is.
The banner is not a circular arc: its edges, measured on the model, are the parabolas
    top(x) = 342.63 - 0.003407 dx + 0.0005475 dx^2      dx = x - 686
    bot(x) = 375.10 - 0.010290 dx + 0.0010204 dx^2
and its shading runs across the band. So the band is straightened (x, v) with v = 0 at its top
edge and 1 at its bottom edge, and each row of constant v is filled along x from the band's own
pixels between the letters. That keeps the band's shading across its width (no blur in the middle).
The new title is set along the band's centre line, cream, in PT Serif like the label's serif.
"""
import os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from common import dilate, inpaint
from fonts import font

src, dst = sys.argv[1], sys.argv[2]
TITLE = 'Aceite nutritivo intensivo'

a = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
H, W = a.shape[:2]
lum = a.mean(2)
TOP = np.array([5.47479e-04, -3.40740e-03, 342.6318])
BOT = np.array([1.02038e-03, -1.02899e-02, 375.1041])
X0, X1 = 528, 848                                   # the straight part of the banner (ends curl)

# ---------------------------------------------------------------- remove the old lettering
xs = np.arange(X0, X1)
top, bot = np.polyval(TOP, xs - 686), np.polyval(BOT, xs - 686)
NV = 96
v = (np.arange(NV) + 0.5) / NV
Y = top[None, :] + v[:, None] * (bot - top)[None, :]          # NV x len(xs) sample rows
Xg = np.broadcast_to(xs[None, :].astype(float), Y.shape)
def straight(img):
    return np.stack([ndi.map_coordinates(img[..., c], [Y, Xg], order=1) for c in range(3)], -1)
st = straight(a)
sl = st.mean(2)
# letters: cream on brown, grown over their anti-aliased edge; the gold rims are left alone
letters = (sl > 150) & (v[:, None] > 0.06) & (v[:, None] < 0.95)
letters = ndi.binary_dilation(letters, iterations=2) & (v[:, None] > 0.03) & (v[:, None] < 0.975)
fill = st.copy()
for i in range(NV):
    m = letters[i]
    if m.any() and (~m).sum() > 4:
        for c in range(3):
            fill[i, m, c] = np.interp(xs[m], xs[~m], st[i, ~m, c])
# a light smoothing along x of the filled stretches only, so the joins don't show
sm = ndi.uniform_filter1d(fill, 7, axis=1)
fill[letters] = sm[letters]

# back to the image: every pixel of the band takes the filled value at its (x, v)
yy, xx = np.mgrid[0:H, X0:X1]
t_, b_ = np.polyval(TOP, xx - 686), np.polyval(BOT, xx - 686)
vv = (yy - t_) / (b_ - t_)
inside = (vv > 0.0) & (vv < 1.0)
vi = np.clip(vv * NV - 0.5, 0, NV - 1)
lm = ndi.map_coordinates(letters.astype(float), [vi, xx - X0], order=1)
band_new = np.stack([ndi.map_coordinates(fill[..., c], [vi, xx - X0], order=1) for c in range(3)], -1)
w = np.clip(lm * 2, 0, 1) * inside
clean = a.copy()
clean[:, X0:X1] = a[:, X0:X1] * (1 - w[..., None]) + band_new * w[..., None]
print('old lettering removed from %d px of the band' % int((w > 0).sum()))

# ---------------------------------------------------------------- new title along the band
S = 4
SPAN = 300.0                          # px of banner the title may take (the old one took ~285)
TRACK = 0.5
for SIZE in range(26, 16, -1):
    f = font('PTSerif-Regular.ttf', SIZE * S)
    widths = [(f.getlength(TITLE[:i + 1]) - f.getlength(TITLE[:i])) / S for i in range(len(TITLE))]
    total = sum(widths) + TRACK * (len(TITLE) - 1)
    if total <= SPAN:
        break
cap = (f.getbbox('H')[3] - f.getbbox('H')[1]) / S
print('title size', SIZE, 'width %.1f' % total, 'cap %.1f' % cap)

# baseline: the band's centre line, lowered by half the cap height so the capitals sit centred
fx = np.linspace(470, 900, 4301)
mid = (np.polyval(TOP, fx - 686) + np.polyval(BOT, fx - 686)) / 2
base = mid + cap / 2 + 0.5
arc = np.concatenate([[0], np.cumsum(np.hypot(np.diff(fx), np.diff(base)))])
s_mid = np.interp(688.0, fx, arc)     # centred where the old title was centred
start = s_mid - total / 2

cover = Image.new('L', (W * S, H * S), 0)
pos = 0.0
for ch, wd in zip(TITLE, widths):
    if ch != ' ':
        g = Image.new('L', (int(wd * S) + 8 * S, int(SIZE * 1.6 * S)), 0)
        oy = int(SIZE * 0.3 * S)
        ImageDraw.Draw(g).text((4 * S, oy), ch, font=f, fill=255)
        s = start + pos + wd / 2
        px, py = np.interp(s, arc, fx), np.interp(s, arc, base)
        slope = np.interp(px, fx[1:], np.diff(base) / np.diff(fx))
        ang = np.degrees(np.arctan(slope))
        gx, gy = 4 * S + wd * S / 2, oy + f.getbbox('H')[3]
        rot = g.rotate(-ang, resample=Image.BICUBIC, center=(gx, gy))
        cover.paste(Image.new('L', rot.size, 255), (int(round(px * S - gx)), int(round(py * S - gy))), rot)
    pos += wd + TRACK
cover = np.asarray(cover.resize((W, H), Image.LANCZOS), float) / 255
# the old lettering's colour: its brightest pixels
CREAM = np.percentile(st[letters & (sl > 200)], 60, axis=0)
sh = np.asarray(Image.fromarray((cover * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.4)), float) / 255
sh = np.roll(sh, 1, 0) * 0.30
out = clean * (1 - sh[..., None]) + np.array([40., 22., 6.]) * sh[..., None]
out = out * (1 - cover[..., None]) + CREAM * cover[..., None]
print('title colour', CREAM.round())

# ---------------------------------------------------------------- "Tick-tock" -> "TikTok"
box = np.zeros((H, W), bool); box[469:497, 1238:1318] = True
old = box & dilate(lum > 135, 3)
out = inpaint(out, old, 200)
f2 = font('PTSerif-Regular.ttf', 16 * S)
g = Image.new('L', (100 * S, 30 * S), 0)
ImageDraw.Draw(g).text((0, 0), 'TikTok', font=f2, fill=255)
g = np.asarray(g.resize((100, 30), Image.LANCZOS), float) / 255
bb = f2.getbbox('TikTok')
ty = int(round(488 - bb[3] / S + 0.5))          # baseline as "Instagram"'s
PILL = np.array([243., 227., 192.])
reg = out[ty:ty + 30, 1244:1344]
out[ty:ty + 30, 1244:1344] = reg * (1 - g[..., None]) + PILL * g[..., None]

# ---------------------------------------------------------------- "SILICONY" -> "SILICONE"
# the Y is removed and the last E of "FREE" just below (same type, same size) is copied in its place
box = np.zeros((H, W), bool); box[655:669, 225:235] = True
out = inpaint(out, box & dilate(lum < 112, 1), 200)
src_e = a[671:684, 213:220]
el = src_e.mean(2)
al = (np.clip((np.percentile(el, 90) - el) / (np.percentile(el, 90) - el.min()), 0, 1) ** 0.9)[..., None]
ink = src_e[np.unravel_index(el.argmin(), el.shape)]
out[656:669, 226:233] = out[656:669, 226:233] * (1 - al) + ink * al

Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)).save(dst)
