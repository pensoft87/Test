#!/bin/sh
# Builds the "Aceite de fortalecimiento capilar" label (5 x 2.5 in) and its sample sachet (2.4 x 2.9 in)
# from the model etiqueta-original.webp (1536 x 1024).  Needs: pip install numpy scipy pillow segno
set -e
cd "$(dirname "$0")"
T=$(mktemp -d)
python3 scripts/titulo.py etiqueta-original.webp "$T/titulo.png"
python3 scripts/plate.py "$T/titulo.png" "$T/p"
python3 scripts/panels.py "$T/p" "$T/etiqueta.png"
python3 ../scripts/borders.py "$T/etiqueta.png" "$T/etiqueta-bordes.png"
python3 scripts/export.py "$T/etiqueta-bordes.png" etiqueta-aceite-fortalecimiento-5x2.5in 320
python3 scripts/sachet.py "$T/p" "$T/sobre.png"
python3 scripts/export.py "$T/sobre.png" sobrecito-muestra-fortalecimiento-2.4x2.9in 400
rm -r "$T"
