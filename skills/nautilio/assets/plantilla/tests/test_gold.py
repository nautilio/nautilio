"""Pruebas del inventario de enmascarado y del formato gold."""

from __future__ import annotations

import json
from pathlib import Path

from paquete_plantilla.gold import build_inventory, render_gold, write_inventory


def test_inventario_cuenta_por_archivo_por_tipo_y_total() -> None:
    # Arrange
    documents = {
        "a.md": "Contacto: [correo enmascarado] y [telefono enmascarado].",
        "b.md": "[correo enmascarado] [identificacion enmascarada]",
    }

    # Act
    inventory = build_inventory(documents)

    # Assert
    assert inventory["por_tipo"] == {"correo": 2, "telefono": 1, "identificacion": 1}
    assert inventory["por_archivo"]["a.md"] == {
        "correo": 1,
        "telefono": 1,
        "identificacion": 0,
    }
    assert inventory["por_archivo"]["b.md"] == {
        "correo": 1,
        "telefono": 0,
        "identificacion": 1,
    }
    assert inventory["total"] == 4


def test_escribe_el_inventario_en_json(tmp_path: Path) -> None:
    # Arrange
    documents = {"unico.md": "[telefono enmascarado]"}
    path = tmp_path / "inventario_enmascarado.json"

    # Act
    inventory = write_inventory(path, documents)

    # Assert
    assert json.loads(path.read_text(encoding="utf-8")) == inventory
    assert inventory["total"] == 1
    assert inventory["por_archivo"]["unico.md"]["telefono"] == 1


def test_render_gold_antepone_front_matter() -> None:
    # Arrange
    metadata = {"id": "inicio", "confianza": "no_confiable", "posible_inyeccion": False}

    # Act
    document = render_gold(metadata, "# Inicio\n\nTexto.")

    # Assert
    assert document.startswith("---\n")
    assert 'confianza: "no_confiable"' in document
    assert "posible_inyeccion: false" in document
    assert document.endswith("# Inicio\n\nTexto.\n")
