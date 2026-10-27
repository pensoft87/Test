#!/bin/sh
# Builds the Vaselinas flyer, a quarter of A4 (105 x 148.5 mm): PNG at 600 ppi and a vector PDF.
# The jars carry the real labels from ../etiquetas/harmonie-vaselina-nutritiva (build those first).
# Needs: pip install numpy pillow segno, and Node with playwright (Chromium).
set -e
cd "$(dirname "$0")"
L=../etiquetas/harmonie-vaselina-nutritiva
python3 scripts/pote.py $L/etiqueta-vaselina-nutritiva-sin-fragancia-6x2.5in.png assets/pote-sin-fragancia.png
python3 scripts/pote.py $L/etiqueta-vaselina-nutritiva-batana-6x2.5in.png assets/pote-batana.png
cp $L/assets/logo-harmonie.png assets/
python3 scripts/qr.py assets
node scripts/render.js .
python3 -c "from PIL import Image; f='flyer-vaselinas-harmonie-A6.png'; Image.open(f).convert('RGB').save(f, dpi=(600, 600))"
