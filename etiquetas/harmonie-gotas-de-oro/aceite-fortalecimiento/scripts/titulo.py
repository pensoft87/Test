"""Replace the lettering on the purple banner ("Aceite nutricion intensiva") with
"Aceite de fortalecimiento capilar".

The model (1536 x 1024) is first brought to 1264 x 843, the size the other scripts work in. There the
banner is an arc of a circle centred at (642, 1241): purple band r = 783..827 between thin gold edges.
The old lettering is removed from the band and the new title is set along the same arc, white, in
PT Serif Bold like the label's serif; it is longer than the old one, so its size is chosen to take the
same stretch of the banner.
"""
import os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from common import dilate, inpaint
from fonts import font

src, dst = sys.argv[1], sys.argv[2]
TITLE = 'Aceite de fortalecimiento capilar'

a = np.asarray(Image.open(src).convert('RGB').resize((1264, 843), Image.LANCZOS)).astype(np.float64)
H, W = a.shape[:2]
CX, CY = 642.0, 1241.0
R_IN, R_OUT = 783.5, 826.5                     # lilac band between the two gold edges
yy, xx = np.mgrid[0:H, 0:W]
rr = np.hypot(xx - CX, yy - CY)
th = np.degrees(np.arctan2(xx - CX, CY - yy))   # 0 at the top, positive to the right

band = (rr > R_IN) & (rr < R_OUT) & (np.abs(th) < 16.5)
inner = (rr > R_IN + 1.5) & (rr < R_OUT - 1.5) & (np.abs(th) < 16.5)
# old lettering: white-ish pixels on the lilac band, grown to take its anti-aliased edge
letters = inner & (a[..., 1] > 196)
old = dilate(letters, 3) & inner
print('old lettering: radius %.1f..%.1f, angle %.2f..%.2f'
      % (rr[letters].min(), rr[letters].max(), th[letters].min(), th[letters].max()))
clean = inpaint(a, old, 200)

# ---- new title, set along the arc
S = 4                                           # supersampling
base_r = 796.0                                  # baseline radius: the title centred on the band (r = 783..827)
TRACK = 0.6                                     # px of extra letter spacing, as in the model
SPAN = 31.0                                     # degrees of banner the title may take
for SIZE in range(31, 20, -1):                  # px: the largest that fits the span
    f = font('PTSerif-Bold.ttf', SIZE * S)
    widths = [f.getlength(TITLE[:i + 1]) / S - f.getlength(TITLE[:i]) / S for i in range(len(TITLE))]
    total = sum(widths) + TRACK * (len(TITLE) - 1)
    if np.degrees(total / base_r) <= SPAN:
        break
print('title size', SIZE)
# arc length at the baseline -> angle; the phrase is centred on the banner's middle (0 deg)
start = -np.degrees(total / 2 / base_r)

cover = Image.new('L', (W * S, H * S), 0)
pos = 0.0
for ch, w in zip(TITLE, widths):
    if ch != ' ':
        g = Image.new('L', (int(w * S) + 8 * S, int(SIZE * 1.6 * S)), 0)
        ImageDraw.Draw(g).text((4 * S, int(SIZE * 0.3 * S)), ch, font=f, fill=255)
        ang = start + np.degrees((pos + w / 2) / base_r)
        # glyph box centre in its own image: x at middle of the advance, baseline at y0
        gx, gy = 4 * S + w * S / 2, SIZE * 0.3 * S + f.getbbox('H')[3]
        rot = g.rotate(-ang, resample=Image.BICUBIC, center=(gx, gy), expand=False)
        px = CX + base_r * np.sin(np.radians(ang))
        py = CY - base_r * np.cos(np.radians(ang))
        cover.paste(Image.new('L', rot.size, 255), (int(round(px * S - gx)), int(round(py * S - gy))), rot)
    pos += w + TRACK
cover = np.asarray(cover.resize((W, H), Image.LANCZOS), float) / 255
cover *= band
# soft, faint shadow under the lettering (the model's white type sits on a slight shade)
sh = np.asarray(Image.fromarray((cover * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6)), float) / 255
sh = np.roll(sh, 1, 0) * band * 0.28
WHITE = np.array([255., 252., 255.])
out = clean * (1 - sh[..., None]) + np.array([70., 40., 90.]) * sh[..., None]
out = out * (1 - cover[..., None]) + WHITE * cover[..., None]
print('new title: %.1f px along the arc, %.2f..%.2f deg' % (total, start, start + np.degrees(total / base_r)))
Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)).save(dst)
