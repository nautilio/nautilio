"""Pruebas de L'Eco: lo que los motores de respuesta repiten de la marca."""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

from paquete_plantilla.eco import (
    RITRATTO,
    Pregunta,
    Respuesta,
    escribir_ritratto,
    escuchar,
    reporte_markdown,
    respuestas_de_marca,
    ritratto_pendiente,
    validar_domande,
)

MARCA = "Marca Demo"


def _pregunta(id_: str, set_: str, etapa: str, prompt: str) -> Pregunta:
    return Pregunta(
        id=id_,
        set=set_,
        etapa=etapa,
        producto="producto",
        persona="familia",
        situacion="comprar",
        restricciones="presupuesto medio",
        prompt=prompt,
        insumo="ventas",
        resultado_negocio="ventas",
    )


PREGUNTAS = (
    _pregunta("c1", "conversacional", "decision", "Donde comprar a domicilio en tres ciudades?"),
    _pregunta("c2", "conversacional", "comparacion", "Que alternativas hay a Rival Uno?"),
    _pregunta("c3", "conversacional", "descubrimiento", "Que tiendas tienen decadas de historia?"),
    _pregunta("m1", "marca", "decision", "Que es Marca Demo?"),
)
RESPUESTAS = (
    Respuesta(
        "c1",
        "motor-a",
        "",
        "Marca Demo y Rival Uno venden a domicilio.",
        ("https://www.marca.example/",),
    ),
    Respuesta("c2", "motor-a", "", "Rival Dos, luego Rival Uno y al final Marca Demo.", ()),
    Respuesta(
        "c3", "motor-a", "", "Rival Uno tiene tiendas con historia.", ("https://otro.example/",)
    ),
    Respuesta("m1", "motor-b", "", "Marca Demo es una tienda.", ()),
)
CORPUS = (
    {
        "url": "https://marca.example/historia",
        "texto": "Nuestras tiendas tienen decadas de historia.",
    },
)


def test_validar_detecta_marca_en_pregunta_conversacional() -> None:
    # Arrange
    preguntas = (*PREGUNTAS, _pregunta("c4", "conversacional", "decision", "Es buena Marca Demo?"))

    # Act
    validacion = validar_domande(preguntas, MARCA, minimo=1)

    # Assert
    assert any(
        "c4" in problema and "no nombra la marca" in problema
        for problema in validacion["problemas"]
    )


def test_validar_exige_resultado_de_negocio_y_rango_de_preguntas() -> None:
    # Arrange
    sin_resultado = replace(
        _pregunta("c5", "conversacional", "decision", "Donde comprar hoy?"), resultado_negocio=""
    )

    # Act
    validacion = validar_domande((sin_resultado,), MARCA)

    # Assert
    problemas = validacion["problemas"]
    assert any(
        "c5" in problema and "sin resultado de negocio" in problema for problema in problemas
    )
    assert any("entre 20 y 40" in problema for problema in problemas)


def test_escuchar_cuenta_visibilidad_share_of_voice_y_citas() -> None:
    # Act
    escucha = escuchar(
        PREGUNTAS, RESPUESTAS, MARCA, "marca.example", ["Rival Uno", "Rival Dos"], CORPUS
    )

    # Assert
    assert escucha["con_respuesta"] == 3
    assert escucha["visibles"] == 2
    assert escucha["visibilidad"] == 66.7
    assert escucha["menciones"] == {"Marca Demo": 2, "Rival Uno": 3, "Rival Dos": 1}
    assert escucha["share_of_voice"] == 33.3
    assert escucha["posicion_promedio"] == 2.0
    assert escucha["citas_propias"] == 1
    assert len(escucha["apariciones"]) == 2
    assert {a["prompt_id"] for a in escucha["apariciones"]} <= {p.id for p in PREGUNTAS}
    assert sum(a["posicion"] for a in escucha["apariciones"]) / 2 == 2.0


def test_brechas_y_la_risposta_desde_el_paradiso() -> None:
    # Act
    escucha = escuchar(
        PREGUNTAS, RESPUESTAS, MARCA, "marca.example", ["Rival Uno", "Rival Dos"], CORPUS
    )

    # Assert
    assert [brecha["prompt_id"] for brecha in escucha["brechas"]] == ["c3"]
    assert escucha["brechas"][0]["paradiso"]["url"] == "https://marca.example/historia"
    assert escucha["cubiertas"] == 1


def test_el_set_de_marca_no_cuenta_en_la_visibilidad() -> None:
    # Act
    de_marca = respuestas_de_marca(PREGUNTAS, RESPUESTAS)

    # Assert
    assert de_marca == [
        {
            "prompt": "Que es Marca Demo?",
            "motor": "motor-b",
            "respuesta": "Marca Demo es una tienda.",
        }
    ]


def test_il_ritratto_trae_los_tres_bloques(tmp_path: Path) -> None:
    # Arrange
    ruta = tmp_path / "ritratto.csv"

    # Act
    escrito = escribir_ritratto(ruta)

    # Assert
    assert escrito is True
    with ruta.open(encoding="utf-8", newline="") as handle:
        filas = list(csv.DictReader(handle))
    assert len(filas) == len(RITRATTO)
    assert {fila["bloque"] for fila in filas} == {
        "1. Contexto del negocio",
        "2. Foco",
        "3. Narrativa para los motores",
    }
    assert len(ritratto_pendiente(ruta)) == len(RITRATTO)
    assert escribir_ritratto(ruta) is False


def test_reporte_cita_las_brechas(tmp_path: Path) -> None:
    # Arrange
    escucha = escuchar(
        PREGUNTAS, RESPUESTAS, MARCA, "marca.example", ["Rival Uno", "Rival Dos"], CORPUS
    )
    validacion = validar_domande(PREGUNTAS, MARCA, minimo=1)

    # Act
    ruta = reporte_markdown(
        MARCA, escucha, validacion, respuestas_de_marca(PREGUNTAS, RESPUESTAS), tmp_path / "eco.md"
    )

    # Assert
    texto = ruta.read_text(encoding="utf-8")
    assert "Visibilidad | 66.7 %" in texto
    assert "https://marca.example/historia" in texto
    assert "Que tiendas tienen decadas de historia?" in texto
