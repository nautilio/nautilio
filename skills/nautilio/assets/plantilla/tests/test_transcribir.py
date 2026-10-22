"""Pruebas de la transcripcion opcional, sin instalar el extra de audio."""

from __future__ import annotations

from pathlib import Path

import pytest

from paquete_plantilla.transcribir import (
    disponible,
    instrucciones_instalacion,
    transcribir_archivo,
)


def test_disponible_devuelve_un_booleano() -> None:
    # Act
    resultado = disponible()

    # Assert
    assert isinstance(resultado, bool)


def test_instrucciones_nombran_el_extra_de_uv() -> None:
    # Act
    texto = instrucciones_instalacion()

    # Assert
    assert "uv sync --extra audio" in texto


def test_falla_si_el_archivo_no_existe(tmp_path: Path) -> None:
    # Arrange
    ruta = tmp_path / "no-existe.mp4"

    # Act / Assert
    with pytest.raises(FileNotFoundError, match="no existe el archivo local"):
        transcribir_archivo(ruta)
