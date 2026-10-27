"""Where the side-panel elements are on the model (1376 x 768), as (x0, y0, x1, y1)."""

# plate.py lifts these off the model; panels.py and sachet.py crop them from the lifted layer
BOXES = {
    'propiedades': (47, 126, 277, 172),
    'descripcion': (52, 174, 458, 252),
    'filete': (53, 252, 427, 276),
    'ingredientes': (47, 276, 280, 322),
    'lista': (52, 323, 398, 378),
    'formula': (46, 380, 302, 471),
    'belleza': (34, 474, 290, 606),
    'fecha': (302, 494, 503, 550),
    'sellos': (58, 584, 452, 706),
    'modo': (1102, 127, 1331, 173),
    'instrucciones': (922, 176, 1332, 357),
    'filete_r': (986, 359, 1333, 391),  # its lower left corner holds the top of the thermometer
    'termometro': (979, 384, 1023, 461),
    'uso_texto': (1030, 390, 1334, 449),
    'instagram': (1045, 460, 1190, 505),
    'tiktok': (1192, 460, 1331, 505),
    'qr_instagram': (1062, 503, 1170, 605),
    'qr_tiktok': (1208, 503, 1315, 605),
    'harmonieproducts': (1046, 610, 1332, 670),
    'filigrana': (866, 488, 1048, 614),          # dropped: no room for it beside the wider column
}

# the four "free" seals (centre x, centre y, radius): the "sellos" box also holds the foot of the
# "Belleza natural" stroke, so the seals are taken inside these circles only, and the stroke outside them
SEALS = [(106, 657, 47), (204, 650, 46), (303.5, 641.5, 46), (404, 632, 47)]
