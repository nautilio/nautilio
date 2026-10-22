# Corpus e inteligencia de {{EMPRESA}}

> «Per me si va ne la città dei dati.»

Proyecto generado por la skill `nautilio`. Recorre dos caminos:

- **Il Viaggio:** lleva páginas públicas de `{{DOMINIO}}` por tres reinos. En el **Inferno**
  queda el crudo con su manifiesto; en el **Purgatorio**, el texto limpio que cruzó el
  **Lete**; en el **Paradiso**, los documentos citables y `corpus.jsonl`.
- **Le Muse:** estudia los anuncios públicos de una marca o competencia con cifras que calcula
  el código. Lema: **«Inspírate, no copies»**.

> Repositorio privado por defecto. No publiques copias completas del sitio.

## Requisitos

- `uv` y Python 3.13.

## Primeros pasos

```bash
uv sync
make demo                       # el primer encuentro: viaje de prueba sin internet
uv run pytest -q
make capture                    # Il Viaggio: cruza La Porta antes de ejecutarlo
make status
make anuncios MARCA=competidor  # Le Muse
make eco MARCA="Marca" COMPETIDORES="a,b"  # L'Eco
make check                      # Il Giudizio
```

La transcripción de videos es opcional y solo aplica a archivos locales que tengas derecho a
usar:

```bash
uv sync --extra audio
uv run paquete_plantilla transcribir ruta/al/video.mp4 --idioma es
```

## Estructura

```text
src/paquete_plantilla/
├── config.py       # semillas, Il Passo, Caronte y excepciones del Lete
├── fetching.py     # La Porta, Il Passo y Caronte
├── extracting.py   # Purgatorio, Lete y Limbo
├── gold.py         # Paradiso y Registro del Lete
├── pipeline.py     # el viaje del Inferno al Paradiso
├── anuncios.py     # Le Muse: cuentas y reporte
├── transcribir.py  # transcriptor local opcional (extra audio)
└── cli.py          # capture / status / anuncios / transcribir
```

## Los tres reinos

- **Inferno:** crudo y manifiesto. Git ignora el crudo y versiona solo el manifiesto.
- **Purgatorio:** texto limpio que cruzó el Lete. No se versiona.
- **Paradiso:** documentos citables, `corpus.jsonl`, Registro del Lete y reportes de Le Muse.
  Se versiona.
- **Limbo:** páginas que solo cargan con JavaScript. Esperan revisión humana; nadie abre un
  navegador para forzarlas.

Los anuncios de Le Muse entran como `data/raw/anuncios/<marca>.jsonl`, recolectados a mano o
con un conector autorizado de las bibliotecas públicas de anuncios.

## Ética

Lee `CONSTITUTION.md` antes de cambiar las semillas, Il Passo o las reglas del Lete.
