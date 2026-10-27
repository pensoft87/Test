import math, sys
import numpy as np
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W = sys.argv[1] if len(sys.argv) > 1 else 'src'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'flyer-harmonie.png'
FONT = f'{W}/Montserrat.ttf'
BG = (55, 24, 52)
GOLD = (214, 184, 140)


def font(size, weight):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f


flyer = Image.open(f'{W}/1.webp').convert('RGB')
arr = np.array(flyer).astype(np.float32)

# ---------------------------------------------------------------- 1. labels on bottles
# label rects (left, top, right, bottom) measured on the original flyer
bottles = [(133, 802, 291, 1039), (363, 802, 521, 1039), (598, 803, 756, 1038), (828, 803, 986, 1038)]
labels = ['2.webp', '3.webp', '5.webp', '4.webp']   # nutritivo, protección, fortalecimiento, intensivo
SS = 4          # supersampling
S_HALF = 420    # half of the source width visible on the front of the bottle

for (L, T, R, B), lab in zip(bottles, labels):
    src = np.array(Image.open(f'{W}/{lab}').convert('RGB')).astype(np.float32)
    sh, sw = src.shape[:2]
    w, h = R - L, B - T
    xs = (np.arange(w * SS) + 0.5) / (w * SS) * 2 - 1          # -1..1 across the cylinder
    th = np.arcsin(np.clip(xs, -1, 1))
    sx = np.clip((sw / 2 + th / (math.pi / 2) * S_HALF).astype(int), 0, sw - 1)
    sy = np.clip(((np.arange(h * SS) + 0.5) / (h * SS) * sh).astype(int), 0, sh - 1)
    warped = src[sy][:, sx]
    # cylinder shading: soft key light from front-left, darker rims, two specular streaks
    lx, lz = -0.35, 1.0
    n = math.hypot(lx, lz)
    diff = np.clip(np.sin(th) * lx / n + np.cos(th) * lz / n, 0, 1)
    shade = 0.62 + 0.40 * diff ** 1.4
    spec = 0.16 * np.exp(-((xs + 0.55) / 0.07) ** 2) + 0.07 * np.exp(-((xs - 0.72) / 0.05) ** 2)
    warped = warped * shade[None, :, None] + 255 * spec[None, :, None]
    # thin vertical tone falloff at the top and bottom edge of the label
    yy = np.linspace(0, 1, h * SS)
    vshade = 1 - 0.10 * np.exp(-(yy / 0.03)) - 0.12 * np.exp(-((1 - yy) / 0.03))
    warped *= vshade[:, None, None]
    patch = Image.fromarray(np.clip(warped, 0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
    # rim mask: fade 1px at left/right so the edge sits on the glass naturally
    mask = Image.new('L', (w, h), 255)
    md = ImageDraw.Draw(mask)
    md.line([(0, 0), (0, h)], fill=150)
    md.line([(w - 1, 0), (w - 1, h)], fill=150)
    flyer.paste(patch, (L, T), mask)

# ---------------------------------------------------------------- helpers
d = ImageDraw.Draw(flyer)


def fill(box, color=BG):
    d.rectangle(box, fill=color)


def ctext(cx, y, text, f, color):
    w = d.textlength(text, font=f)
    d.text((cx - w / 2, y), text, font=f, fill=color)


# ---------------------------------------------------------------- 2. captions under icons
caps = [
    (213, 'Nutre y suaviza', '(Después del lavado)'),
    (443, 'Protege e hidrata', '(Sol, playa y piscina)'),
    (676, 'Fortalece y cuida', '(Cuero cabelludo)'),
    (912, 'Repara y da brillo', '(Nutrición intensiva)'),
]
for cx, _, _ in caps:
    fill((cx - 108, 1146, cx + 108, 1200))
f1, f2 = font(17, 'Bold'), font(15, 'Regular')
for cx, t1, t2 in caps:
    ctext(cx, 1151, t1, f1, (255, 244, 255))
    ctext(cx, 1174, t2, f2, (229, 207, 227))

# ---------------------------------------------------------------- 3. phone number
# keep the pill's own soft vertical gradient: copy a clean column from just right of the divider
col = arr[1230:1288, 466:467]
patch = np.repeat(col, 790 - 470, axis=1)
flyer.paste(Image.fromarray(patch.astype(np.uint8)), (470, 1230))
ctext(628, 1238, '829-889-6187', font(34, 'ExtraBold'), (52, 10, 45))

# ---------------------------------------------------------------- 5. footer handle
old = flyer.crop((325, 1322, 600, 1356))        # "WWW.HARMONIE.ES |"
fill((60, 1322, 1062, 1356))
handle = '@Harmonieproducts'
fh = font(19, 'Regular')
hw = d.textlength(handle, font=fh)
total = 275 + 12 + hw
start = int(561 - total / 2)
flyer.paste(old, (start, 1322))
hx = start + 275 + 12
d.text((hx, 1326), handle, font=fh, fill=(230, 207, 228))
# gold rules either side
def rule(a, b):
    for i, a_ in enumerate((0.55, 1.0, 0.45)):
        c = tuple(int(BG[k] + (GOLD[k] - BG[k]) * a_) for k in range(3))
        d.line([(a, 1336 + i), (b, 1336 + i)], fill=c)
rule(72, start - 22)
rule(int(hx + hw + 22), 1050)

# ---------------------------------------------------------------- 4. QR cards (Instagram / TikTok)
def qr_img(url, px):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=1, box_size=10)
    q.add_data(url)
    q.make(fit=True)
    return q.make_image(fill_color=(40, 8, 36), back_color=(255, 251, 246)).convert('RGB').resize((px, px), Image.NEAREST)


def qr_card(cx, url, title):
    size, pad = 88, 6
    x0, y0 = cx - (size + 2 * pad) // 2, 1206
    x1, y1 = x0 + size + 2 * pad, y0 + size + 2 * pad
    d.rounded_rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), 12, fill=GOLD)
    d.rounded_rectangle((x0, y0, x1, y1), 10, fill=(255, 251, 246))
    flyer.paste(qr_img(url, size), (x0 + pad, y0 + pad))
    ctext(cx, y1 + 5, title, font(13, 'SemiBold'), (229, 207, 227))


fill((60, 1240, 262, 1262))      # remove the gold rules beside the pill
fill((860, 1240, 1062, 1262))
qr_card(165, 'https://www.instagram.com/harmonieproducts', 'Instagram')
qr_card(957, 'https://www.tiktok.com/@harmonieproducts', 'TikTok')

flyer.save(OUT)
print('ok')
