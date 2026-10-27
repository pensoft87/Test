"""Gold rules along the top and bottom edges, in the same gold as the label's own rules
(about 6 px of (200, 148, 55) with soft edges and a gentle metallic sheen along its length)."""
import sys, numpy as np
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
INSET, THICK = 0, 6             # flush with the edge; thickness in px (320 ppi)

a = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
H, W = a.shape[:2]

dark = np.array([190., 136., 46.])
light = np.array([238., 196., 108.])
x = np.arange(W) / W
sheen = 0.5 + 0.5 * np.cos(2 * np.pi * (x * 2.5 + 0.1)) ** 3          # broad highlights
sheen = np.clip(sheen * 0.8 + 0.2 * (0.5 + 0.5 * np.cos(2 * np.pi * x * 9)), 0, 1)

def rule(top):
    y = np.arange(H, dtype=np.float64)
    c = top + THICK / 2 - 0.5
    cov = np.clip(THICK / 2 + 0.6 - np.abs(y - c), 0, 1)            # anti-aliased band
    t = np.clip((y - top) / max(THICK - 1, 1), 0, 1)
    tone = 1 - 0.35 * np.abs(t - 0.35) / 0.65                        # lighter just above centre
    col = dark[None, None, :] + (light - dark)[None, None, :] * (sheen[None, :, None] * tone[:, None, None])
    return cov[:, None, None], col

for top in (INSET, H - INSET - THICK):
    cov, col = rule(top)
    a = a * (1 - cov) + col * cov

Image.fromarray(np.clip(a + 0.5, 0, 255).astype(np.uint8)).save(dst)
