#!/bin/sh
# Builds the two "Vaselina nutritiva" labels (6 x 2.5 in): sin fragancia and enriquecida con batana.
# The design is etiqueta.html (open it with #sin-fragancia or #batana to preview it in a browser).
# Needs: pip install numpy scipy pillow segno, and Node with playwright (Chromium).
set -e
cd "$(dirname "$0")"
python3 scripts/logo.py assets/modelo-aceite-proteccion.png assets/logo-harmonie.png
python3 scripts/qr.py assets
node scripts/render.js .
python3 scripts/dpi.py etiqueta-vaselina-nutritiva-*-6x2.5in.png
