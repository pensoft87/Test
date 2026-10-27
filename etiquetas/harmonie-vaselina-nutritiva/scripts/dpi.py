"""Tag the exported PNGs with their print resolution (1920 x 800 px = 6 x 2.5 in at 320 ppi)."""
import sys
from PIL import Image

for path in sys.argv[1:]:
    im = Image.open(path).convert('RGB')
    im.save(path, dpi=(320, 320))
    print(path, im.size, '= %.2f x %.2f in' % (im.width / 320, im.height / 320))
