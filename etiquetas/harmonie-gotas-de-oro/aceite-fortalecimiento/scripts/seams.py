"""Content-aware widening by seam insertion (Avidan & Shamir, with forward energy).

Vertical seams of least visible change run through the plain cream of the panels and the softest
parts of the leaf bands, so the side panels grow without stretching the artwork evenly.
"""
import numpy as np
from scipy import ndimage as ndi

BIG = 1e12

def seam(gray, cost):
    """Cheapest 8-connected top-to-bottom seam. gray: H x W, cost: H x W extra cost per pixel."""
    H, W = gray.shape
    M = cost[0].copy()
    back = np.zeros((H, W), int)
    cols = np.arange(W)
    for y in range(1, H):
        g, up = gray[y], gray[y - 1]
        L = np.concatenate([[g[0]], g[:-1]])
        R = np.concatenate([g[1:], [g[-1]]])
        cU = np.abs(R - L)                       # forward energy: new edges a removal creates
        mL = np.concatenate([[BIG], M[:-1]]) + cU + np.abs(up - L)
        mU = M + cU
        mR = np.concatenate([M[1:], [BIG]]) + cU + np.abs(up - R)
        st = np.stack([mL, mU, mR])
        k = st.argmin(0)
        M = st[k, cols] + cost[y]
        back[y] = cols + k - 1
    s = np.zeros(H, int)
    s[-1] = M.argmin()
    for y in range(H - 1, 0, -1):
        s[y - 1] = back[y, s[y]]
    return s

def _remove(arr, s):
    H, W = arr.shape[:2]
    keep = np.ones((H, W), bool)
    keep[np.arange(H), s] = False
    return arr[keep].reshape((H, W - 1) + arr.shape[2:])

def widen(img, cost, k):
    """Insert k seams into img (H x W x 3). Returns the widened image and, per row, the new x of
    every original column (H x W)."""
    H, W = img.shape[:2]
    gray = ndi.gaussian_filter(img.mean(2), 1.0)
    idx = np.tile(np.arange(W), (H, 1))
    g, c = gray.copy(), cost.astype(np.float64).copy()
    cnt = np.zeros((H, W), int)
    rows = np.arange(H)
    for _ in range(k):                           # the k cheapest seams, found by removing them in turn
        s = seam(g, c)
        cnt[rows, idx[rows, s]] += 1
        idx, g, c = _remove(idx, s), _remove(g, s), _remove(c, s)
    out = np.zeros((H, W + k, img.shape[2]))
    xmap = np.zeros((H, W), int)
    for y in range(H):
        row = img[y]
        nxt = np.concatenate([row[1:], row[-1:]])
        reps = 1 + cnt[y]
        src = np.repeat(np.arange(W), reps)
        j = np.arange(len(src)) - np.repeat(np.cumsum(reps) - reps, reps)
        frac = j / reps[src]                     # copies step smoothly towards the next column
        out[y] = row[src] * (1 - frac[:, None]) + nxt[src] * frac[:, None]
        xmap[y] = np.cumsum(reps) - reps
    return out, xmap
