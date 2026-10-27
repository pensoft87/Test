"""Write the Instagram and TikTok QR codes as SVG paths: qr.py <assets dir>"""
import os, sys, segno

out = sys.argv[1]
for name, url in (('instagram', 'https://www.instagram.com/harmonieproducts'),
                  ('tiktok', 'https://www.tiktok.com/@harmonieproducts')):
    qr = segno.make(url, error='m')
    path = os.path.join(out, 'qr-%s.svg' % name)
    qr.save(path, kind='svg', border=0, dark='#1c0f06', light=None, xmldecl=False, svgns=True)
    print(path, qr.version, qr.error, qr.symbol_size(border=0))
