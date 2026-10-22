"""Pruebas del brazo de marketing con anuncios falsos, sin tocar la red."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paquete_plantilla.anuncios import (
    Anuncio,
    cargar_anuncios,
    creativos_unicos,
    reporte_markdown,
    resumen,
    ruta_reporte,
)


def _anuncio(anuncio_id: str, **overrides: object) -> Anuncio:
    values: dict[str, object] = {
        "id": anuncio_id,
        "plataforma": "meta",
        "texto": "Compra ya",
        "titulo": "Demo",
        "formato": "imagen",
        "cta": "Comprar",
        "url_destino": "https://ejemplo.com/",
        "url_ficha": f"https://fichas.ejemplo.com/{anuncio_id}",
    }
    values.update(overrides)
    return Anuncio(**values)


def test_carga_jsonl_y_conserva_los_campos(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "anuncios.jsonl"
    rows = [
        {
            "id": "a1",
            "plataforma": "meta",
            "pagina": "Empresa Demo",
            "fecha_inicio": "2026-01-01",
            "formato": "video",
            "texto": "Texto",
            "titulo": "Titulo",
            "cta": "Comprar",
            "url_destino": "https://ejemplo.com",
            "url_ficha": "https://fichas.ejemplo.com/1",
            "duracion_s": "12.5",
            "transcripcion": "Hola",
        }
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    # Act
    anuncios = cargar_anuncios(path)

    # Assert
    assert len(anuncios) == 1
    assert anuncios[0].id == "a1"
    assert anuncios[0].plataforma == "meta"
    assert anuncios[0].duracion_s == 12.5
    assert anuncios[0].transcripcion == "Hola"


def test_carga_rechaza_una_plataforma_desconocida(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "invalido.jsonl"
    path.write_text('{"id": "x", "plataforma": "tiktok"}\n', encoding="utf-8")

    # Act / Assert
    with pytest.raises(ValueError, match="plataforma invalida"):
        cargar_anuncios(path)


def test_deduplica_por_texto_titulo_y_formato() -> None:
    # Arrange
    anuncios = [
        _anuncio("a1", texto="Compra ya", titulo="Demo", formato="imagen"),
        _anuncio(
            "a2",
            plataforma="google",
            texto="  COMPRA   YA ",
            titulo="demo",
            formato="Imagen",
        ),
        _anuncio("a3", texto="Compra ya", titulo="Demo", formato="imagen"),
        _anuncio("a4", texto="Descubre", formato="video"),
    ]

    # Act
    unicos = creativos_unicos(anuncios)

    # Assert
    assert len(unicos) == 2
    assert unicos[0].repeticiones == 3
    assert unicos[0].anuncios == ("a1", "a2", "a3")
    assert unicos[0].plataformas == ("google", "meta")


def test_resumen_cuenta_formatos_destinos_y_cta() -> None:
    # Arrange
    anuncios = [
        _anuncio("a1", url_destino="https://ejemplo.com/x"),
        _anuncio(
            "a2",
            plataforma="google",
            texto="  COMPRA   YA ",
            titulo="demo",
            formato="Imagen",
            url_destino="https://www.ejemplo.com/y",
        ),
        _anuncio("a3", url_destino="https://ejemplo.com/z"),
        _anuncio(
            "a4",
            texto="Descubre",
            formato="video",
            cta="Ver mas",
            url_destino="https://otro.com/a",
        ),
        _anuncio("a5", texto="", titulo="", formato="carrusel", cta="", url_destino=""),
    ]

    # Act
    datos = resumen(anuncios)

    # Assert
    assert datos["total"] == 5
    assert datos["unicos"] == 3
    assert datos["repetidos"] == 2
    assert datos["porcentaje_repetido"] == 40.0
    assert datos["por_formato"] == {"imagen": 3, "carrusel": 1, "video": 1}
    assert datos["por_dominio"] == {"ejemplo.com": 3, "otro.com": 1, "(sin destino)": 1}
    assert datos["por_cta"] == {"Comprar": 3, "Ver mas": 1, "(sin cta)": 1}


def test_reporte_cita_las_fichas_y_no_inventa_cifras(tmp_path: Path) -> None:
    # Arrange
    anuncios = [
        _anuncio("a1", url_ficha="https://fichas.ejemplo.com/1"),
        _anuncio("a2", url_ficha="https://fichas.ejemplo.com/2"),
        _anuncio("a3", texto="Otro", formato="video", url_ficha="https://fichas.ejemplo.com/3"),
    ]
    salida = tmp_path / "inteligencia-anuncios-empresa-demo.md"

    # Act
    path = reporte_markdown(anuncios, "Empresa Demo", salida)

    # Assert
    texto = path.read_text(encoding="utf-8")
    assert path == salida
    assert "# Inteligencia de anuncios — Empresa Demo" in texto
    assert "| Anuncios | 3 |" in texto
    assert "| Creativos unicos | 2 |" in texto
    assert "| Porcentaje repetido | 33.33 % |" in texto
    assert "https://fichas.ejemplo.com/1" in texto
    assert "https://fichas.ejemplo.com/2" in texto
    assert "https://fichas.ejemplo.com/3" in texto


def test_reporte_vacio_es_explicito(tmp_path: Path) -> None:
    # Arrange
    salida = tmp_path / "inteligencia-anuncios-sin-datos.md"

    # Act
    path = reporte_markdown([], "Sin Datos", salida)

    # Assert
    texto = path.read_text(encoding="utf-8")
    assert "| Anuncios | 0 |" in texto
    assert "Sin anuncios cargados." in texto


def test_ruta_reporte_usa_el_nombre_convencional(tmp_path: Path) -> None:
    # Arrange
    gold_dir = tmp_path / "gold"

    # Act
    path = ruta_reporte("empresa-demo", gold_dir)

    # Assert
    assert path == gold_dir / "inteligencia-anuncios-empresa-demo.md"
