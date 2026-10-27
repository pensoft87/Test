"""Borra los textos del modelo (ref.png) y rellena el fondo con interpolación armónica."""
import numpy as np
import sys
from PIL import Image

SAMPLE = 'muestra' in sys.argv[1:]

SRC = "modelo.png"
img = np.asarray(Image.open(SRC).convert('RGB')).astype(np.float64)
H, W, _ = img.shape
lum = img @ np.array([0.299, 0.587, 0.114])


def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r:
                continue
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def harmonic_fill(im, mask, iters=300):
    """Rellena im[mask] resolviendo Laplace con multiescala."""
    h, w = mask.shape
    if min(h, w) > 32:
        h2, w2 = (h + 1) // 2, (w + 1) // 2
        pad = np.ones((h2 * 2, w2 * 2), bool); pad[:h, :w] = mask
        padi = np.zeros((h2 * 2, w2 * 2, 3)); padi[:h, :w] = im
        m2 = pad.reshape(h2, 2, w2, 2).all(axis=(1, 3))
        known = (~pad).astype(float)[..., None]
        s = (padi * known).reshape(h2, 2, w2, 2, 3).sum(axis=(1, 3))
        c = known.reshape(h2, 2, w2, 2, 1).sum(axis=(1, 3))
        i2 = np.where(c > 0, s / np.maximum(c, 1), 0)
        i2 = harmonic_fill(i2, m2, iters)
        up = np.repeat(np.repeat(i2, 2, 0), 2, 1)[:h, :w]
        im = im.copy(); im[mask] = up[mask]
    else:
        im = im.copy(); im[mask] = im[~mask].mean(axis=0)
    for _ in range(iters):
        p = np.pad(im, ((1, 1), (1, 1), (0, 0)), mode='edge')
        avg = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4
        im[mask] = avg[mask]
    return im


mask = np.zeros((H, W), bool)


def boxblur(a, r):
    c = np.cumsum(np.cumsum(np.pad(a.astype(float), ((r + 1, r), (r + 1, r))), 0), 1)
    k = 2 * r + 1
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


ribbon = boxblur(lum < 125, 9) > 0.35


def rect(x0, y0, x1, y1):
    m = np.zeros((H, W), bool); m[y0:y1, x0:x1] = True; return m


# Columnas de texto completas (se redibujan en HTML)
mask |= rect(38, 124, 468, 476)
mask |= rect(918, 124, 1376, 460)
# Geometría del arco del título y de la cinta (coordenadas del modelo)
YY, XX = np.mgrid[0:H, 0:W]
dx2 = (XX - 686.0) ** 2
title_top = 300 + 0.00066 * dx2
ribbon_top = 343 + 0.00037 * dx2
ribbon_bot = 383 + 0.00040 * dx2
# Nombre del producto "GOTAS DE ORO"
mask |= rect(528, 290, 846, 360) & (YY >= title_top) & (YY < ribbon_top - 1)
# Texto claro dentro de la cinta
mask |= rect(536, 330, 842, 400) & (YY > ribbon_top + 4) & (YY < ribbon_bot - 3) & dilate(lum > 150, 2)
# "Nutre • Protege • Embellece"
mask |= rect(562, 384, 812, 416) & (YY > ribbon_bot + 2) & dilate(lum < 150, 3)
# "Tick-tock" -> se reescribe
mask |= rect(1238, 469, 1318, 497) & dilate(lum > 135, 3)
# "SILICONY" -> solo se borra la "Y" (se reemplaza por una "E" copiada de "FREE")
mask |= rect(225, 655, 235, 669) & dilate(lum < 112, 1)

if SAMPLE:
    # Texto "4. OZ." de la placa inferior
    mask |= rect(646, 688, 722, 712) & dilate(lum > 135, 2)

out = img.copy()
ys, xs = np.where(mask)
pad = 24
y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, H)
x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, W)
# Procesa cada bloque por separado (más rápido)
from itertools import product
blocks = [(38, 124, 468, 476), (918, 124, 1376, 460), (520, 262, 850, 420),
          (1230, 462, 1324, 504), (222, 650, 244, 675)]
if SAMPLE:
    blocks.append((640, 682, 728, 716))
for bx0, by0, bx1, by1 in blocks:
    bx0 -= pad; by0 -= pad; bx1 += pad; by1 += pad
    sub = out[by0:by1, bx0:bx1]
    sm = mask[by0:by1, bx0:bx1]
    out[by0:by1, bx0:bx1] = harmonic_fill(sub, sm)

# Grano sutil para que el relleno no se vea plano
rng = np.random.default_rng(7)
noise = rng.normal(0, 1.6, (H, W, 1))
out[mask] += noise[mask]
# Pega la "E" final de "FREE" en lugar de la "Y" (misma tipografía del modelo)
src = img[671:684, 213:220]
src_l = src @ np.array([0.299, 0.587, 0.114])
bg_l = np.percentile(src_l, 90)
ink_l = src_l.min()
alpha = np.clip((bg_l - src_l) / (bg_l - ink_l), 0, 1)[..., None] ** 0.9
ty, tx = 656, 226
dst = out[ty:ty + 13, tx:tx + 7]
ink = src[np.unravel_index(src_l.argmin(), src_l.shape)]
out[ty:ty + 13, tx:tx + 7] = dst * (1 - alpha) + ink * alpha
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save('bg_muestra.png' if SAMPLE else 'bg_clean.png')
print('ok')
