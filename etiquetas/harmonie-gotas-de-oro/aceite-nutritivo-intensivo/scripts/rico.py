"""Justified paragraphs, without hyphens, where some words are bold (the "Modo de uso" steps).

Same rules as ../../scripts/typeset.py: line breaks chosen so every line is evenly full, the slack of
each line shared between its word gaps (and a very slight letter spacing), last line flush left.
"""
import os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from fonts import font

TRACK_MAX, TRACK_MIN, SPACE_SHRINK = 0.02, -0.015, 0.2


def words_of(runs):
    """runs: [(text, bold)] -> [(word, bold)]"""
    out = []
    for s, b in runs:
        out += [(w, b) for w in s.split()]
    return out


def block(runs, width, size, lh, color, regular, bold):
    S = 4
    f1 = {False: font(regular, size), True: font(bold, size)}
    fS = {False: font(regular, size * S), True: font(bold, size * S)}
    ws = words_of(runs)
    n = len(ws)
    wl = [f1[b].getlength(w) for w, b in ws]
    sp = f1[False].getlength(' ')

    def fit(i, j):                       # words i..j-1 on one line
        nat = sum(wl[i:j]) + sp * (j - i - 1)
        gaps = j - i - 1
        chars = sum(len(w) for w, _ in ws[i:j]) - 1 + gaps
        slack = width - nat
        t = min(slack / max(chars, 1), TRACK_MAX * size) if slack >= 0 else max(slack / max(chars, 1), TRACK_MIN * size)
        rest = slack - t * chars
        if gaps == 0:
            return (t, sp, (rest / sp) ** 2 * 4) if rest >= 0 else None
        extra = rest / gaps
        if extra < -SPACE_SHRINK * sp:
            return None
        return t, sp + extra, gaps * (extra / sp) ** 2 + chars * (t / size * 10) ** 2

    best = [0.0] + [float('inf')] * n
    prev = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            nat = sum(wl[i:j]) + sp * (j - i - 1)
            if j == n:
                cost = None if nat > width else (0.0 if nat >= width * 0.35 else 50.0)
            else:
                r = fit(i, j)
                cost = None if r is None else r[2]
            if cost is None:
                if nat > width * 1.05:
                    break
                continue
            if best[i] + cost < best[j]:
                best[j], prev[j] = best[i] + cost, i
    lines, j = [], n
    while j > 0:
        lines.append((prev[j], j)); j = prev[j]
    lines = lines[::-1]

    asc = fS[False].getbbox('H')[1]
    h = lh * len(lines) + size
    im = Image.new('L', ((width + 20) * S, h * S), 0)
    d = ImageDraw.Draw(im)
    for k, (i, j) in enumerate(lines):
        ty = k * lh * S - asc
        t, spw = (fit(i, j)[:2]) if k < len(lines) - 1 else (0.0, sp)
        x = 0.0
        for w, b in ws[i:j]:
            f = fS[b]
            for c, ch in enumerate(w):
                d.text((x + f.getlength(w[:c]) + c * t * S, ty), ch, font=f, fill=255)
            x += f.getlength(w) + len(w) * t * S + spw * S
    im = im.resize((width + 20, h), Image.LANCZOS)
    rgba = Image.new('RGBA', im.size, color + (0,))
    rgba.putalpha(im)
    bb = im.getbbox()
    return rgba.crop((0, 0, bb[2], bb[3]))
