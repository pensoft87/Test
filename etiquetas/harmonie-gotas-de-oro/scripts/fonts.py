from PIL import ImageFont
import os
FDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fonts')

def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FDIR, name), size)
    if weight is not None:
        try:
            axes = f.get_variation_axes()
        except Exception:
            return f
        vals = []
        for ax in axes:
            n = ax['name'] if isinstance(ax['name'], str) else ax['name'].decode()
            vals.append(weight if n.lower().startswith('weight') else ax['default'])
        f.set_variation_by_axes(vals)
    return f
