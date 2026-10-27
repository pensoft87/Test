"""Justified typesetting without hyphens, shared by the label and the sample sachet."""
from PIL import Image, ImageDraw
from fonts import font

FONT = 'NunitoSans.ttf'

# Justification without hyphens: the line breaks are chosen so every line is as evenly full as
# possible, and each line's leftover space is shared between the word gaps and a very slight
# change in letter spacing (at most +2% / -1.5% of the type size), so no gap gets wide.
TRACK_MAX, TRACK_MIN, SPACE_SHRINK = 0.02, -0.015, 0.2

def fit(words, f, width, size):
    """How a run of words sets on one line: (letter spacing, space width, badness) or None."""
    nat = f.getlength(' '.join(words))
    sp = f.getlength(' ')
    gaps = len(words) - 1
    chars = sum(len(w) for w in words) - 1 + gaps
    slack = width - nat
    if slack >= 0:
        t = min(slack / max(chars, 1), TRACK_MAX * size)
    else:
        t = max(slack / max(chars, 1), TRACK_MIN * size)
    rest = slack - t * chars
    if gaps == 0:
        return (t, sp, (rest / sp) ** 2 * 4) if rest >= 0 else None
    extra = rest / gaps
    if extra < -SPACE_SHRINK * sp:
        return None
    return t, sp + extra, gaps * (extra / sp) ** 2 + chars * (t / size * 10) ** 2

def wrap(text, f, width, size):
    words = text.split()
    n = len(words)
    best = [0.0] + [float('inf')] * n
    prev = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j, 0, -1):
            ws = words[i - 1:j]
            if j == n:                                   # last line: natural spacing, flush left
                ln = f.getlength(' '.join(ws))
                # ...and never a lone short word on it
                cost = None if ln > width else (0.0 if ln >= width * 0.35 else 50.0)
            else:
                r = fit(ws, f, width, size)
                cost = None if r is None else r[2]
            if cost is None:
                if f.getlength(' '.join(ws)) > width * 1.05:
                    break
                continue
            if best[i - 1] + cost < best[j]:
                best[j], prev[j] = best[i - 1] + cost, i - 1
    lines, j = [], n
    while j > 0:
        lines.append(words[prev[j]:j]); j = prev[j]
    return lines[::-1]

def text_block(text, width, size, lh, color, weight=600, justify=True):
    """Render a justified paragraph (last line flush left); the block's top is the cap height."""
    S = 4
    f1 = font(FONT, size, weight)
    f = font(FONT, size * S, weight)
    lines = wrap(text, f1, width, size)
    asc = f.getbbox('H')[1]
    h = lh * len(lines) + size
    im = Image.new('L', ((width + 20) * S, h * S), 0)
    d = ImageDraw.Draw(im)
    for i, ws in enumerate(lines):
        ty = i * lh * S - asc
        if justify and i < len(lines) - 1:
            t, spw, _ = fit(ws, f1, width, size)
        else:
            t, spw = 0.0, f1.getlength(' ')
        x = 0.0
        for w in ws:
            for k, ch in enumerate(w):              # keep kerning: position by prefix width
                d.text((x + f.getlength(w[:k]) + k * t * S, ty), ch, font=f, fill=255)
            x += f.getlength(w) + len(w) * t * S + spw * S
    im = im.resize((width + 20, h), Image.LANCZOS)
    rgba = Image.new('RGBA', im.size, color + (0,))
    rgba.putalpha(im)
    bb = im.getbbox()
    return rgba.crop((0, 0, bb[2], bb[3])), len(lines)
