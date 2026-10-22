"""Pruebas de Le Scoperte: solo llega a La Cronaca lo que se puede citar."""

from __future__ import annotations

import json
from pathlib import Path

from paquete_plantilla.scoperte import (
    cargar_acciones,
    cargar_hallazgos,
    cargar_relato,
    textos_del_paradiso,
)

DOMINIO = "{{DOMINIO}}"
BASE = f"https://{DOMINIO}"


def _paradiso(tmp_path: Path) -> Path:
    gold = tmp_path / "gold"
    gold.mkdir()
    (gold / "historia.md").write_text(
        "---\nid: historia\n---\n# Historia\n\n"
        "**Fundada en 1958**, la empresa atiende tres ciudades con tiendas propias.\n\n"
        "Escribe a [correo enmascarado] para mas informacion.\n",
        encoding="utf-8",
    )
    registro = {"url_cita": f"{BASE}/historia", "ruta_gold": "data/gold/historia.md"}
    (gold / "corpus.jsonl").write_text(json.dumps(registro) + "\n", encoding="utf-8")
    return gold


def _hallazgo(cita: str, url: str = f"{BASE}/historia") -> dict[str, str]:
    return {
        "tema": "Historia",
        "hallazgo": "Tiene décadas de trayectoria.",
        "cita": cita,
        "url_cita": url,
    }


def test_conserva_la_cita_que_existe_aunque_cambien_negritas_y_espacios(tmp_path: Path) -> None:
    # Arrange
    gold = _paradiso(tmp_path)
    ruta = gold / "hallazgos.json"
    cita = "Fundada en 1958, la empresa  atiende tres ciudades"
    ruta.write_text(json.dumps({"hallazgos": [_hallazgo(cita)]}), encoding="utf-8")

    # Act
    resultado = cargar_hallazgos(textos_del_paradiso(gold), ruta)

    # Assert
    assert len(resultado["hallazgos"]) == 1
    assert resultado["descartados"] == []


def test_descarta_citas_inventadas_ajenas_o_con_datos_enmascarados(tmp_path: Path) -> None:
    # Arrange
    gold = _paradiso(tmp_path)
    ruta = gold / "hallazgos.json"
    hallazgos = [
        _hallazgo("Fundada en 1958, la empresa atiende cinco ciudades"),
        _hallazgo("Fundada en 1958, la empresa atiende tres ciudades", f"{BASE}/otra"),
        _hallazgo("Escribe a [correo enmascarado] para mas informacion"),
    ]
    ruta.write_text(json.dumps({"hallazgos": hallazgos}), encoding="utf-8")

    # Act
    resultado = cargar_hallazgos(textos_del_paradiso(gold), ruta)

    # Assert
    assert resultado["hallazgos"] == []
    motivos = [d["motivo"] for d in resultado["descartados"]]
    assert motivos == [
        "la cita no aparece en la pagina que nombra",
        "la pagina citada no esta en el Paradiso",
        "la cita contiene un dato enmascarado",
    ]


def test_las_acciones_solo_usan_evidencia_del_paradiso_y_se_ordenan(tmp_path: Path) -> None:
    # Arrange
    gold = _paradiso(tmp_path)
    ruta = gold / "risposta.json"
    acciones = [
        {"titulo": "Página de precios", "prioridad": 2, "evidencia_disponible": []},
        {
            "titulo": "Página de historia",
            "prioridad": 1,
            "que_debe_decir": "- Año de fundación\n- Ciudades que atiende",
            "evidencia_disponible": [f"{BASE}/historia", "https://otro.com/inventada"],
            "falta_confirmar": ["Ciudades nuevas"],
        },
    ]
    ruta.write_text(json.dumps({"acciones": acciones}), encoding="utf-8")

    # Act
    resultado = cargar_acciones(textos_del_paradiso(gold), ruta)

    # Assert
    assert [a["titulo"] for a in resultado] == ["Página de historia", "Página de precios"]
    assert resultado[0]["evidencia"] == [f"{BASE}/historia"]
    assert resultado[0]["que_debe_decir"] == ["Año de fundación", "Ciudades que atiende"]


def test_sin_archivos_no_hay_hallazgos_ni_acciones(tmp_path: Path) -> None:
    # Act
    hallazgos = cargar_hallazgos({}, tmp_path / "no-existe.json")
    acciones = cargar_acciones({}, tmp_path / "no-existe.json")

    # Assert
    assert hallazgos == {"hallazgos": [], "descartados": [], "vacios": [], "insights": []}
    assert acciones == []


def test_la_gran_idea_con_una_cifra_inventada_no_llega(tmp_path: Path) -> None:
    # Arrange
    ruta = tmp_path / "risposta.json"
    relato = {
        "gran_idea": "Aparece en 1 de 24 preguntas aunque el sitio ya responde.",
        "historia": ["Pierde el 80 % de las familias.", "Abrió admisiones en 2026."],
    }
    ruta.write_text(json.dumps(relato), encoding="utf-8")

    # Act
    resultado = cargar_relato({"1", "24", "2026"}, ruta)

    # Assert
    assert resultado["gran_idea"].startswith("Aparece en 1 de 24")
    assert resultado["historia"] == ["Abrió admisiones en 2026."]
    assert resultado["descartadas"] == 1


def test_los_insights_solo_agrupan_hallazgos_con_cita(tmp_path: Path) -> None:
    # Arrange
    gold = _paradiso(tmp_path)
    ruta = gold / "hallazgos.json"
    data = {
        "hallazgos": [_hallazgo("Fundada en 1958, la empresa atiende tres ciudades")],
        "insights": [
            {"titulo": "Décadas de oficio", "hallazgos": ["h1", "h9"]},
            {"titulo": "Sin sustento", "hallazgos": ["h9"]},
        ],
    }
    ruta.write_text(json.dumps(data), encoding="utf-8")

    # Act
    resultado = cargar_hallazgos(textos_del_paradiso(gold), ruta)

    # Assert
    assert [i["titulo"] for i in resultado["insights"]] == ["Décadas de oficio"]
    assert resultado["insights"][0]["hallazgos"] == ["h1"]


def test_las_acciones_aceptan_solo_plazos_y_esfuerzos_conocidos(tmp_path: Path) -> None:
    # Arrange
    ruta = tmp_path / "risposta.json"
    acciones = [{"titulo": "A", "cuando": "Hoy", "esfuerzo": "enorme"}]
    ruta.write_text(json.dumps({"acciones": acciones}), encoding="utf-8")

    # Act
    resultado = cargar_acciones({}, ruta)

    # Assert
    assert resultado[0]["cuando"] == "hoy"
    assert resultado[0]["esfuerzo"] == ""
