"""Tag the exported PNGs with their print resolution, from the size in the file name (..._WxHin.png)."""
import re, sys
from PIL import Image

for path in sys.argv[1:]:
    w_in = float(re.search(r'([\d.]+)x[\d.]+in\.png$', path).group(1))
    im = Image.open(path).convert('RGB')
    ppi = round(im.width / w_in)
    im.save(path, dpi=(ppi, ppi))
    print(path, im.size, '= %.2f x %.2f in at %d ppi' % (im.width / ppi, im.height / ppi, ppi))
