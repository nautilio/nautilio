"""Pruebas de La Cronaca: el viaje contado para personas."""

from __future__ import annotations

import json
from pathlib import Path

from paquete_plantilla.cronaca import DatosCronaca, escribir, extracto, render, reunir


def _datos(**cambios: object) -> DatosCronaca:
    base = DatosCronaca(
        empresa="Empresa Demo",
        dominio="ejemplo.com",
        fecha="2026-10-22",
        estados={"ok": 3, "robots_blocked": 1},
        paso=4.0,
        documentos=[
            {
                "titulo": "Quienes somos",
                "url": "https://ejemplo.com/quienes-somos",
                "caracteres": 900,
                "extracto": "Fundada en 1958, la empresa atiende tres ciudades "
                "con tiendas propias.",
            }
        ],
        lete={"total": 2, "por_tipo": {"correo": 1, "telefono": 1, "identificacion": 0}},
        limbo=0,
    )
    for clave, valor in cambios.items():
        setattr(base, clave, valor)
    return base


def test_cuenta_el_viaje_en_una_frase_con_cifras_del_codigo() -> None:
    # Act
    pagina = render(_datos())

    # Assert
    assert "Visitamos 3 páginas públicas de ejemplo.com." in pagina
    assert "22 de octubre de 2026" in pagina
    assert ", que cerraron 1" in pagina
    assert "el Lete borró 2 datos personales" in pagina
    assert "1 correo y 1 teléfono" in pagina


def test_cita_a_la_empresa_con_su_fuente() -> None:
    # Act
    pagina = render(_datos())

    # Assert
    assert "Fundada en 1958" in pagina
    assert 'href="https://ejemplo.com/quienes-somos"' in pagina


def test_escapa_el_texto_que_viene_del_sitio() -> None:
    # Arrange
    malicioso = [
        {
            "titulo": "<script>alert(1)</script>",
            "url": "javascript:alert(1)",
            "caracteres": 500,
            "extracto": "Texto <img src=x onerror=alert(1)> que llega del sitio "
            "con mas de sesenta letras.",
        }
    ]

    # Act
    pagina = render(_datos(documentos=malicioso))

    # Assert
    assert "<script>alert(1)</script>" not in pagina
    assert "&lt;script&gt;" in pagina
    assert "onerror=alert(1)>" not in pagina
    assert 'href="javascript' not in pagina


def test_propone_revisar_paginas_casi_vacias(tmp_path: Path) -> None:
    # Arrange
    vacia = [
        {"titulo": "Politica", "url": "https://ejemplo.com/p", "caracteres": 77, "extracto": ""}
    ]

    # Act
    ruta = escribir(_datos(documentos=vacia), tmp_path / "cronaca.html")

    # Assert
    texto = ruta.read_text(encoding="utf-8")
    assert "Revisar 1 página casi vacía (Politica)" in texto
    assert texto.startswith("<!doctype html>")


def test_lee_hallazgos_y_comprueba_sus_citas_al_reunir(tmp_path: Path) -> None:
    # Arrange
    gold = tmp_path / "gold"
    gold.mkdir()
    (gold / "historia.md").write_text(
        "---\nid: historia\n---\nFundada en 1958, la empresa atiende tres ciudades.\n",
        encoding="utf-8",
    )
    registro = {
        "titulo": "Historia",
        "url_cita": "https://ejemplo.com/historia",
        "ruta_gold": "data/gold/historia.md",
        "caracteres": 900,
    }
    (gold / "corpus.jsonl").write_text(json.dumps(registro) + "\n", encoding="utf-8")
    hallazgos = [
        {
            "tema": "Historia",
            "hallazgo": "Atiende tres ciudades.",
            "cita": cita,
            "url_cita": "https://ejemplo.com/historia",
        }
        for cita in ("la empresa atiende tres ciudades", "la empresa atiende cinco países")
    ]
    (gold / "hallazgos.json").write_text(json.dumps({"hallazgos": hallazgos}), encoding="utf-8")

    # Act
    datos = reunir(raw_dir=tmp_path / "raw", gold_dir=gold, eco_dir=tmp_path / "eco")

    # Assert
    assert [h["cita"] for h in datos.scoperte["hallazgos"]] == ["la empresa atiende tres ciudades"]
    assert len(datos.scoperte["descartados"]) == 1
    assert datos.specchio is None


def test_cuenta_hallazgos_vacios_y_acciones_con_su_fuente() -> None:
    # Arrange
    scoperte = {
        "hallazgos": [
            {
                "tema": "Historia",
                "hallazgo": "Lleva seis décadas en tres ciudades.",
                "cita": "Fundada en 1958, la empresa atiende tres ciudades",
                "url_cita": "https://ejemplo.com/quienes-somos",
            }
        ],
        "descartados": [{"motivo": "la cita no aparece en la pagina que nombra"}],
        "vacios": [{"tema": "Precios", "por_que_importa": "Deciden por el costo."}],
    }
    acciones = [
        {
            "titulo": "Página de precios",
            "prioridad": 1,
            "responde_a": [],
            "que_debe_decir": ["Costo del envío"],
            "evidencia": ["https://ejemplo.com/quienes-somos"],
            "falta_confirmar": ["el costo"],
        }
    ]

    # Act
    consulta = {"consultas": ["a"], "fecha": "2026-10-22"}
    pagina = render(_datos(scoperte=scoperte, acciones=acciones, muse_consulta=consulta))

    # Assert
    assert "Le Scoperte" in pagina
    assert "Lleva seis décadas en tres ciudades." in pagina
    assert "Lo que no aparece en la página leída" in pagina
    assert "1 hallazgo se descartó" in pagina
    assert "La Risposta" in pagina
    assert "Por confirmar con su equipo:" in pagina
    assert "<li>el costo</li>" in pagina
    assert "La empresa debe confirmar" not in pagina
    assert "Lo que sigue" not in pagina
    assert "Para completar el viaje" not in pagina


def test_muestra_la_vista_previa_y_los_perfiles_del_sitio() -> None:
    # Arrange
    sitio = {
        "paginas": 2,
        "paginas_con_og_completo": 1,
        "paginas_con_whatsapp": 0,
        "paginas_con_botones_compartir": 2,
        "perfiles": {"https://instagram.com/empresa": 2},
        "previsualizacion": {"title": "Empresa Demo", "description": "Desde 1958.", "image": ""},
        "problemas_frecuentes": {"falta og:image": 1},
    }

    # Act
    pagina = render(_datos(specchio=sitio))

    # Assert
    assert "Lo Specchio" in pagina
    assert "sin imagen de vista previa" in pagina
    assert 'href="https://instagram.com/empresa"' in pagina
    assert "enlazado desde 2 de 2 páginas" in pagina
    assert "ninguna ofrece escribir por mensajería" in pagina
    assert "no hay imagen para la vista previa" in pagina


def test_cuenta_la_busqueda_de_anuncios_aunque_no_haya_ninguno() -> None:
    # Act
    pagina = render(_datos(muse_consulta={"consultas": ["a", "b"], "fecha": "2026-10-22"}))

    # Assert
    assert "con 2 consultas en la biblioteca pública de anuncios el 22 de octubre de 2026" in pagina
    assert "y no apareció ninguno suyo entre los resultados revisados." in pagina


def test_l_eco_compara_motores_y_muestra_quien_aparece_en_su_lugar() -> None:
    # Arrange
    eco = {
        "con_respuesta": 4,
        "visibles": 1,
        "visibilidad": 25.0,
        "posicion_promedio": 2.0,
        "share_of_voice": 20.0,
        "citas_propias": 1,
        "menciones": {"Empresa Demo": 1, "Rival Uno": 4, "Rival Dos": 0},
        "dominios_citados": {"ejemplo.com": 1},
        "apariciones": [
            {
                "prompt_id": "c2",
                "prompt": "¿Quién vende desde 1958?",
                "motor": "motor-a",
                "posicion": 2,
            }
        ],
        "brechas": [
            {
                "prompt_id": "c1",
                "prompt": "¿Dónde comprar?",
                "rivales": ["Rival Uno"],
                "paradiso": {"url": "https://ejemplo.com/quienes-somos", "puntaje": 0.2},
                "etapa": "decision",
            }
        ],
    }
    por_motor = {
        "motor-a": {"visibles": 1, "con_respuesta": 4},
        "motor-b": {"visibles": 0, "con_respuesta": 4},
    }

    # Act
    pagina = render(_datos(eco=eco, eco_marca="Empresa Demo", eco_por_motor=por_motor))

    # Assert
    assert "Hicimos 4 preguntas a 2 asistentes de IA (motor-a y motor-b)" in pagina
    assert "Empresa Demo apareció en una sola." in pagina
    assert "aparece en 0 de 4 preguntas" in pagina
    assert "La única vez que aparece, sale en el puesto 2" in pagina
    assert "Dónde sí aparece" in pagina
    assert "Quién aparece en su lugar" in pagina
    assert '<li class="propia"><span>Empresa Demo</span>' in pagina
    assert "Rival Dos" not in pagina
    assert "Ninguna página leída comparte bastantes palabras" in pagina


def test_nombra_las_paginas_con_problemas_y_lista_competidores_completos() -> None:
    # Arrange
    sitio = {
        "paginas": 1,
        "paginas_con_og_completo": 0,
        "paginas_con_whatsapp": 1,
        "paginas_con_botones_compartir": 0,
        "perfiles": {},
        "previsualizacion": None,
        "problemas_frecuentes": {"falta og:image": 1},
        "detalle": [{"url": "https://ejemplo.com/quienes-somos/", "problemas": ["falta og:image"]}],
    }
    rivales = [f"Rival {n}" for n in range(1, 7)]
    eco = {
        "con_respuesta": 2,
        "visibles": 0,
        "visibilidad": 0.0,
        "posicion_promedio": None,
        "share_of_voice": 0.0,
        "citas_propias": 0,
        "menciones": {"Empresa Demo": 0, **dict.fromkeys(rivales, 1)},
        "dominios_citados": {},
        "brechas": [
            {
                "prompt_id": "c1",
                "prompt": "¿Dónde comprar?",
                "rivales": rivales,
                "paradiso": {"url": "https://ejemplo.com/quienes-somos", "puntaje": 0.5},
                "etapa": "decision",
            }
        ],
    }

    # Act
    pagina = render(_datos(specchio=sitio, eco=eco, eco_marca="Empresa Demo"))

    # Assert
    assert "<span>Quienes somos</span>" in pagina
    assert "Rival 1, Rival 2, Rival 3, Rival 4 y 2 más" in pagina
    assert "<span>Rival 6</span>" in pagina
    assert "La página que más palabras comparte con la pregunta:" in pagina
    assert "no apareció en ninguna" in pagina


def test_sin_hallazgos_pide_completar_el_viaje() -> None:
    # Act
    pagina = render(_datos())

    # Assert
    assert "Para completar el viaje" in pagina
    assert "Redactar Le Scoperte" in pagina


def test_extracto_salta_titulos_y_front_matter() -> None:
    # Arrange
    markdown = (
        "---\nid: x\n---\n# Titulo\n\n[Enlace suelto](https://ejemplo.com)\n\n"
        "El colegio nacio en 1978 para propiciar la busqueda creativa de la felicidad.\n"
    )

    # Act
    texto = extracto(markdown)

    # Assert
    assert texto == "El colegio nacio en 1978 para propiciar la busqueda creativa de la felicidad."


def test_extracto_quita_negritas_y_no_corta_palabras() -> None:
    # Arrange
    largo = "**Nuestro colegio** educa con " + "propósito y libertad " * 20

    # Act
    texto = extracto(largo)

    # Assert
    assert "**" not in texto
    assert texto.startswith("Nuestro colegio educa")
    assert texto.endswith("…")
    assert texto[:-1].split()[-1] in {"propósito", "y", "libertad"}


def test_extracto_no_cita_parrafos_con_datos_enmascarados() -> None:
    # Arrange
    markdown = (
        "Escribe a [correo enmascarado] o llama al [telefono enmascarado] para mas informacion."
        "\n\nFundada en 1958, la empresa atiende tres ciudades.\n"
    )

    # Act
    texto = extracto(markdown)

    # Assert
    assert texto == "Fundada en 1958, la empresa atiende tres ciudades."


def test_abre_con_la_gran_idea_y_titulares_que_concluyen() -> None:
    # Arrange
    relato = {"gran_idea": "La marca casi no aparece.", "historia": ["Una.", "Dos."]}
    acciones = [
        {
            "titulo": "Corregir fechas",
            "prioridad": 1,
            "responde_a": [],
            "que_debe_decir": [],
            "evidencia": [],
            "falta_confirmar": [],
            "resultado": "",
            "esfuerzo": "bajo",
            "cuando": "hoy",
        }
    ]

    # Act
    pagina = render(_datos(relato=relato, acciones=acciones))

    # Assert
    assert pagina.index("La marca casi no aparece.") < pagina.index("Cómo se hizo")
    assert "La historia en tres minutos" in pagina
    assert "1 acción en orden; 1 se puede hacer hoy" in pagina
    assert "Para hacer hoy" in pagina
    assert '<span class="tag hoy">hoy</span>' in pagina
    assert 'class="metodo"' in pagina
    assert "Siguiente paso" not in pagina


def test_l_eco_dibuja_una_casilla_por_pregunta() -> None:
    # Arrange
    eco = {
        "con_respuesta": 24,
        "visibles": 1,
        "visibilidad": 4.2,
        "posicion_promedio": 1.0,
        "share_of_voice": 5.0,
        "citas_propias": 1,
        "menciones": {"Empresa Demo": 1, "Rival Uno": 3},
        "dominios_citados": {},
        "brechas": [],
    }

    # Act
    pagina = render(_datos(eco=eco, eco_marca="Empresa Demo"))

    # Assert
    assert pagina.count('class="llena"') == 1
    assert pagina.count('class="vacia"') == 23
    assert "Empresa Demo aparece en 1 de 24 preguntas; 1 marca aparece más veces" in pagina


def test_el_siguiente_paso_solo_con_contacto_y_enlace_seguro() -> None:
    # Act
    con_correo = render(_datos(contacto_informe="equipo@ejemplo.com"))
    con_script = render(_datos(contacto_informe="javascript:alert(1)"))

    # Assert
    assert 'href="mailto:equipo@ejemplo.com"' in con_correo
    assert "Siguiente paso" in con_script
    assert 'href="javascript' not in con_script
