"""Save a finished label as PNG and PDF at its print resolution: export.py <in.png> <out-base> <ppi>"""
import sys
from PIL import Image

src, out, ppi = sys.argv[1], sys.argv[2], int(sys.argv[3])
im = Image.open(src).convert('RGB')
im.save(out + '.png', dpi=(ppi, ppi))
im.save(out + '.pdf', resolution=ppi, quality=95)
print(out, im.size, '= %.2f x %.2f in' % (im.width / ppi, im.height / ppi))
