#!/usr/bin/env python3
"""Genera el mapa del viaje de Nautilio (flujo.svg), grabado en tinta sobre papel.

Solo usa la biblioteca estandar. Uso: ``python docs/assets/generar_imagenes.py``.
La portada (portada.svg) es un grabado isometrico aparte y no se genera aqui.
"""

from __future__ import annotations

from pathlib import Path

DESTINO = Path(__file__).resolve().parent
SERIF = "'Cormorant Garamond', Garamond, 'Palatino Linotype', Georgia, 'Times New Roman', serif"
TINTA = "#15110D"
PAPEL = "#EFE7D6"
GRIS = "#5E554A"

VIAGGIO = [
    ("La Porta", "pide permiso"),
    ("Il Passo", "sin prisa"),
    ("Caronte", "sabe cuándo parar"),
    ("Inferno", "lo crudo"),
    ("Purgatorio", "el Lete borra lo personal"),
    ("Paradiso", "lo citable"),
]
MUSE = [
    ("Raccolta", "anuncios públicos"),
    ("Conteggio", "lo cuenta el código"),
    ("Lettura", "gancho, ángulo y guion"),
    ("Ispirazione", "una idea propia"),
    ("Il Giudizio", "antes de publicar"),
]
ECO = [
    ("Il Ritratto", "el retrato de la marca"),
    ("Le Domande", "lo que pregunta la gente"),
    ("L'Ascolto", "lo que responden"),
    ("La Risposta", "reforzar o escribir"),
]


def _caja(x: float, y: float, ancho: float, titulo: str, detalle: str, tramado: bool) -> str:
    acento = "url(#tramado)" if tramado else TINTA
    return (
        f'<rect x="{x}" y="{y}" width="{ancho}" height="74" fill="#F7F1E5" stroke="{TINTA}" stroke-width="1.2"/>'
        f'<rect x="{x}" y="{y}" width="7" height="74" fill="{acento}" stroke="{TINTA}" stroke-width="1.2"/>'
        f'<text x="{x + 20}" y="{y + 32}" font-family="{SERIF}" font-size="21" font-weight="700" fill="{TINTA}">{titulo}</text>'
        f'<text x="{x + 20}" y="{y + 56}" font-family="{SERIF}" font-size="15" font-style="italic" fill="{GRIS}">{detalle}</text>'
    )


def _flecha(x1: float, y: float, x2: float) -> str:
    return (
        f'<line x1="{x1}" y1="{y}" x2="{x2 - 8}" y2="{y}" stroke="{TINTA}" stroke-width="1.4"/>'
        f'<path d="M{x2 - 9},{y - 5} L{x2},{y} L{x2 - 9},{y + 5} Z" fill="{TINTA}"/>'
    )


def _bajada(x: float, y1: float, y2: float) -> str:
    return (
        f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 8}" stroke="{TINTA}" stroke-width="1.4"/>'
        f'<path d="M{x - 5},{y2 - 9} L{x},{y2} L{x + 5},{y2 - 9} Z" fill="{TINTA}"/>'
    )


def _cronaca(x: float, y: float, ancho: float) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{ancho}" height="74" fill="#F7F1E5" stroke="{TINTA}" stroke-width="2"/>'
        f'<rect x="{x + 5}" y="{y + 5}" width="{ancho - 10}" height="64" fill="none" stroke="{TINTA}" stroke-width="0.7"/>'
        f'<text x="{x + 22}" y="{y + 33}" font-family="{SERIF}" font-size="22" font-weight="700" letter-spacing="2" fill="{TINTA}">La Cronaca</text>'
        f'<text x="{x + 22}" y="{y + 57}" font-family="{SERIF}" font-size="15" font-style="italic" fill="{GRIS}">el viaje contado para personas · make cronaca</text>'
    )


def flujo() -> str:
    ancho, alto = 1200, 634
    caja, paso, x0 = 172, 192, 36
    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" role="img" aria-label="Mapa del viaje de Nautilio: Il Viaggio, Le Muse y L’Eco desembocan en La Cronaca">',
        "<defs>"
        f'<pattern id="tramado" width="2.6" height="2.6" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><rect width="2.6" height="2.6" fill="{PAPEL}"/><path d="M0 0V2.6M0 0H2.6" stroke="{TINTA}" stroke-width=".9" opacity=".85"/></pattern>'
        '<filter id="grano" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7"/>'
        '<feColorMatrix type="matrix" values="0 0 0 0 0.08  0 0 0 0 0.07  0 0 0 0 0.05  0 0 0 0.09 0"/></filter>'
        "</defs>",
        f'<rect width="{ancho}" height="{alto}" fill="{PAPEL}"/>',
        f'<rect x="14" y="14" width="{ancho - 28}" height="{alto - 28}" fill="none" stroke="{TINTA}" stroke-width="1.2"/>',
        f'<rect x="22" y="22" width="{ancho - 44}" height="{alto - 44}" fill="none" stroke="{TINTA}" stroke-width="0.6"/>',
        f'<text x="{x0}" y="66" font-family="{SERIF}" font-size="26" font-weight="700" letter-spacing="4" fill="{TINTA}">EL MAPA DEL VIAJE</text>',
        f'<text x="{x0}" y="94" font-family="{SERIF}" font-size="16" font-style="italic" fill="{GRIS}">Le das la empresa, su dominio, unas pocas páginas, la marca y sus competidores; Nautilio arma el proyecto y recorre los círculos.</text>',
        f'<text x="{x0}" y="142" font-family="{SERIF}" font-size="17" letter-spacing="3" fill="{TINTA}">IL VIAGGIO · make capture</text>',
        f'<text x="{x0}" y="306" font-family="{SERIF}" font-size="17" letter-spacing="3" fill="{TINTA}">LE MUSE · make anuncios</text>',
    ]
    partes.append(
        f'<text x="{x0}" y="470" font-family="{SERIF}" font-size="17" letter-spacing="3" fill="{TINTA}">L\'ECO · make eco</text>'
    )
    for fila, (pasos, y) in enumerate(((VIAGGIO, 158), (MUSE, 322), (ECO, 486))):
        for i, (titulo, detalle) in enumerate(pasos):
            x = x0 + i * paso
            partes.append(_caja(x, y, caja, titulo, detalle, tramado=fila >= 1))
            if i < len(pasos) - 1:
                partes.append(_flecha(x + caja, y + 37, x + paso))
    x_cronaca = x0 + 4 * paso
    ancho_cronaca = paso + caja
    partes.append(_flecha(x0 + 3 * paso + caja, 486 + 37, x_cronaca))
    partes.append(_bajada(x0 + 4 * paso + caja / 2, 322 + 74, 486))
    partes.append(_bajada(x0 + 5 * paso + caja / 2, 158 + 74, 486))
    partes.append(_cronaca(x_cronaca, 486, ancho_cronaca))
    partes.append(
        f'<text x="{x0}" y="600" font-family="{SERIF}" font-size="15" font-style="italic" fill="{GRIS}">Ninguna cifra sale del modelo de lenguaje: las cuenta el código y cada dato cita su fuente.</text>'
    )
    partes.append(f'<rect width="{ancho}" height="{alto}" filter="url(#grano)"/>')
    partes.append("</svg>\n")
    return "\n".join(partes)


def main() -> None:
    (DESTINO / "flujo.svg").write_text(flujo(), encoding="utf-8")
    print(f"Mapa escrito en {DESTINO / 'flujo.svg'}")


if __name__ == "__main__":
    main()
