import numpy as np

def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out

def inpaint(img, mask, iters=None):
    """Fill masked pixels by harmonic (Laplace) interpolation from the border, multigrid style."""
    img = img.astype(np.float64).copy()
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return img
    y0, y1 = max(ys.min() - 2, 0), min(ys.max() + 3, img.shape[0])
    x0, x1 = max(xs.min() - 2, 0), min(xs.max() + 3, img.shape[1])
    sub = img[y0:y1, x0:x1]
    m = mask[y0:y1, x0:x1]

    def solve(sub, m, n):
        # coarse initialisation
        h, w = m.shape
        if min(h, w) > 16 and m.sum() > 64:
            hs, ws = (h + 1) // 2, (w + 1) // 2
            pad = np.pad(sub, ((0, hs * 2 - h), (0, ws * 2 - w), (0, 0)), mode='edge')
            mp = np.pad(m, ((0, hs * 2 - h), (0, ws * 2 - w)), mode='edge')
            known = (~mp).astype(float)
            ks = known.reshape(hs, 2, ws, 2).sum((1, 3))
            vs = (pad * known[..., None]).reshape(hs, 2, ws, 2, -1).sum((1, 3))
            cm = ks == 0
            cs = vs / np.maximum(ks, 1)[..., None]
            cs = solve(cs, cm, n)
            up = cs.repeat(2, 0).repeat(2, 1)[:h, :w]
            sub = sub.copy()
            sub[m] = up[m]
        else:
            sub = sub.copy()
            sub[m] = sub[~m].mean(0) if (~m).any() else 0
        for _ in range(n):
            p = np.pad(sub, ((1, 1), (1, 1), (0, 0)), mode='edge')
            avg = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4
            sub[m] = avg[m]
        return sub

    img[y0:y1, x0:x1] = solve(sub, m, iters or 60)
    return img
