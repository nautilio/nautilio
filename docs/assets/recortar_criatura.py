"""Quita el fondo del grabado de la criatura y deja un PNG transparente.

Uso: uv run --no-project --with pillow --with numpy --with scipy python
     docs/assets/recortar_criatura.py <grabado.jpg>

Conserva cada trazo del grabado. El papel solo queda dentro de la silueta, para que la
criatura se lea igual en temas claros y oscuros.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

UMBRAL_TINTA = 135
DESTINO = Path(__file__).with_name("criatura.png")
ANCHO_FINAL = 760


def main() -> None:
    imagen = Image.open(sys.argv[1]).convert("RGB")
    gris = np.asarray(imagen.convert("L"), dtype=np.float32)
    tinta = gris < UMBRAL_TINTA
    silueta = ndimage.binary_closing(tinta, structure=np.ones((3, 3)), iterations=9)
    silueta = ndimage.binary_fill_holes(silueta)
    etiquetas, total = ndimage.label(silueta)
    tamanos = ndimage.sum(silueta, etiquetas, range(1, total + 1))
    silueta = np.isin(etiquetas, [i + 1 for i, t in enumerate(tamanos) if t > 0.002 * silueta.size])
    alfa = ndimage.gaussian_filter(silueta.astype(np.float32), sigma=1.6)
    alfa = np.clip((alfa - 0.35) / 0.3, 0, 1)  # borde suave, sin halo
    rgba = np.dstack([np.asarray(imagen), (alfa * 255).astype(np.uint8)])
    filas, columnas = np.where(alfa > 0)
    margen = 10
    recorte = rgba[
        max(filas.min() - margen, 0) : filas.max() + margen,
        max(columnas.min() - margen, 0) : columnas.max() + margen,
    ]
    salida = Image.fromarray(recorte, "RGBA")
    alto = round(salida.height * ANCHO_FINAL / salida.width)
    salida = salida.resize((ANCHO_FINAL, alto), Image.LANCZOS)
    salida.save(DESTINO, optimize=True)
    print(f"{DESTINO} · {salida.size} · {DESTINO.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
