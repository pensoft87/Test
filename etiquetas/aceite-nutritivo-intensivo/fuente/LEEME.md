# Fuente – Etiqueta Aceite Nutritivo Intensivo

- `modelo.png`: diseño de referencia (1376×768).
- `limpiar_modelo.py`: borra los textos del modelo y rellena el fondo.
  - `python3 limpiar_modelo.py` → `bg_clean.png` (etiqueta principal)
  - `python3 limpiar_modelo.py muestra` → `bg_muestra.png` (sin "4. OZ.")
- `etiqueta.html` / `muestra.html`: textos de cada etiqueta sobre el fondo limpio.
- `render.js`: exporta a PNG con Playwright.
  - `node render.js etiqueta.html salida.png 1376 768 1` (usar `2` al final para alta resolución)
