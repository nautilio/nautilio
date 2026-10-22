"""Configuracion del viaje: semillas, los tres reinos, Il Passo, Caronte y el Lete."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # Inferno
PROCESSED_DIR = DATA_DIR / "processed"  # Purgatorio
GOLD_DIR = DATA_DIR / "gold"  # Paradiso

MANIFEST_PATH = RAW_DIR / "manifest.json"
CORPUS_PATH = GOLD_DIR / "corpus.jsonl"
INVENTORY_PATH = GOLD_DIR / "inventario_enmascarado.json"  # Registro del Lete
ANUNCIOS_DIR = RAW_DIR / "anuncios"  # Raccolta de Le Muse

EMPRESA = "{{EMPRESA}}"
DOMINIO = "{{DOMINIO}}"

# Correo de quien captura, nunca uno del dominio de la empresa: el robot no se hace pasar
# por ella. `make capture` se niega a correr mientras este campo este vacio.
CONTACTO = ""
# Siguiente paso de La Cronaca: correo o enlace de quien ofrece ayuda. Vacio = no se muestra.
CONTACTO_INFORME = ""
NOMBRE_TECNICO = "paquete_plantilla"
USER_AGENT = f"{NOMBRE_TECNICO}/0.1 (proyecto academico; contacto: {CONTACTO or 'sin configurar'})"

# Il Passo: segundos entre peticiones. Si robots.txt pide mas, sube este valor.
REQUEST_DELAY_SECONDS = 4.0
REQUEST_TIMEOUT_SECONDS = 30.0
MAX_BYTES = 40 * 1024 * 1024
# Caronte: codigos HTTP que detienen el lote.
STOP_STATUS_CODES = frozenset({403, 429})

CONFIANZA = "no_confiable"

# Excepciones del Lete. Ponlas en False para enmascarar todo.
CONSERVAR_CORREOS_INSTITUCIONALES = True
CONSERVAR_TELEFONOS_FIJOS = True
PREFIJOS_TELEFONO_FIJO = ("60",)


@dataclass(frozen=True, slots=True)
class Seed:
    """Semilla explicita de captura. Nunca se descubre navegando enlaces."""

    id: str
    url: str
    titulo: str
    categoria: str
    prioridad: str = "P1"


SEEDS: tuple[Seed, ...] = (
    Seed(
        id="inicio",
        url="https://{{DOMINIO}}/",
        titulo="Inicio",
        categoria="institucional",
    ),
    Seed(
        id="quienes-somos",
        url="https://{{DOMINIO}}/quienes-somos",
        titulo="Quienes somos",
        categoria="institucional",
    ),
    Seed(
        id="contacto",
        url="https://{{DOMINIO}}/contacto",
        titulo="Contacto",
        categoria="contacto",
    ),
)
