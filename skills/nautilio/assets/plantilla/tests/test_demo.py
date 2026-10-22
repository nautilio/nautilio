"""Pruebas del viaje de prueba: la ciudad local muestra cada circulo con cifras reales."""

from __future__ import annotations

import json
from pathlib import Path

from paquete_plantilla.demo import narrar, recorrer


def test_el_viaje_de_prueba_recorre_cada_circulo(tmp_path: Path) -> None:
    # Act
    resultado = recorrer(destino=tmp_path, paso=0)

    # Assert
    estados = resultado.viaje.statuses
    assert estados["ok"] == 2
    assert estados["robots_blocked"] == 1
    assert estados["stopped"] == 1
    assert estados["not_attempted"] == 1
    assert resultado.viaje.counts.gold == 2


def test_el_lete_borra_lo_personal_del_paradiso(tmp_path: Path) -> None:
    # Act
    resultado = recorrer(destino=tmp_path, paso=0)

    # Assert
    por_tipo = resultado.viaje.inventory["por_tipo"]
    assert por_tipo["correo"] == 2
    assert por_tipo["telefono"] == 1
    assert por_tipo["identificacion"] == 1
    corpus = (tmp_path / "gold" / "corpus.jsonl").read_text(encoding="utf-8")
    citable = "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "gold").glob("*.md"))
    for dato in ("maria.perez@gmail.com", "310 555 1234", "1.144.555.666", "juan.ruiz@hotmail.com"):
        assert dato not in corpus
        assert dato not in citable


def test_le_muse_cuenta_creativos_unicos(tmp_path: Path) -> None:
    # Act
    resultado = recorrer(destino=tmp_path, paso=0)

    # Assert
    assert resultado.muse["total"] == 6
    assert resultado.muse["unicos"] == 4
    assert resultado.muse["repetidos"] == 2
    assert resultado.reporte_muse.is_file()


def test_la_narracion_usa_cifras_del_codigo(tmp_path: Path) -> None:
    # Arrange
    resultado = recorrer(destino=tmp_path, paso=0)
    lineas: list[str] = []

    # Act
    narrar(resultado, paso=0, escribir=lineas.append)

    # Assert
    texto = "\n".join(lineas)
    assert "el Lete borró 4 datos personales" in texto
    assert "6 anuncios: 4 creativos únicos" in texto
    assert "make capture" in texto
    manifiesto = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert manifiesto
