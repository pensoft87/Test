"""Write the Instagram and TikTok QR codes as SVG: qr.py <assets dir>"""
import os, sys, segno

for name, url in (('instagram', 'https://www.instagram.com/harmonieproducts'),
                  ('tiktok', 'https://www.tiktok.com/@harmonieproducts')):
    segno.make(url, error='m').save(os.path.join(sys.argv[1], 'qr-%s.svg' % name), kind='svg', border=0,
                                    dark='#2a0f2a', light=None, xmldecl=False)
