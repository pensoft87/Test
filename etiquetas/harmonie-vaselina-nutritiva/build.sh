#!/bin/sh
# Builds the two "Vaselina nutritiva" labels (6 x 2.5 in) and their sample sachets (2.3 x 1.5 in):
# sin fragancia and enriquecida con batana.
# The designs are etiqueta.html and muestra.html (open them with #sin-fragancia or #batana to preview).
# Needs: pip install numpy scipy pillow segno, and Node with playwright (Chromium).
set -e
cd "$(dirname "$0")"
python3 scripts/logo.py assets/modelo-aceite-proteccion.png assets/logo-harmonie.png
python3 scripts/qr.py assets
node scripts/render.js .
python3 scripts/dpi.py etiqueta-vaselina-nutritiva-*-6x2.5in.png sobrecito-muestra-vaselina-nutritiva-*-2.3x1.5in.png
