"""Transcripcion local opcional para la Lettura de Le Muse.

Solo se transcriben archivos locales que la persona tenga derecho a usar. El
transcriptor no es obligatorio: vive en el extra ``audio`` de ``pyproject.toml``.
"""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path

INSTRUCCIONES = (
    "Falta el transcriptor local. Instala el extra de audio con `uv sync --extra audio` "
    "y vuelve a ejecutar el comando."
)


def disponible() -> bool:
    """Indica si el transcriptor local esta instalado en el entorno actual."""
    return find_spec("faster_whisper") is not None


def instrucciones_instalacion() -> str:
    """Devuelve el comando exacto para habilitar la transcripcion."""
    return INSTRUCCIONES


def transcribir_archivo(
    ruta: Path,
    modelo: str = "small",
    idioma: str | None = None,
) -> str:
    """Transcribe un archivo local con el transcriptor opcional, si esta disponible."""
    if not ruta.is_file():
        raise FileNotFoundError(f"no existe el archivo local: {ruta}")
    if not disponible():
        raise RuntimeError(INSTRUCCIONES)

    from faster_whisper import WhisperModel

    engine = WhisperModel(modelo, device="cpu", compute_type="int8")
    segments, _info = engine.transcribe(str(ruta), language=idioma, vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()
