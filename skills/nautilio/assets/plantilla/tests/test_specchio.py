"""Pruebas de Lo Specchio: la vista previa y los perfiles sociales, sin tocar la red."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from paquete_plantilla.specchio import (
    HOSTS_MENSAJERIA,
    analizar_bronze,
    analizar_html,
    escribir,
)

DOMINIO = "{{DOMINIO}}"
BASE = f"https://{DOMINIO}"

IMAGEN = f"{BASE}/img/vista-previa.jpg"
PERFIL_FB = "https://facebook.com/empresademo"
PERFIL_IG = "https://instagram.com/empresa_demo"
PERFIL_IN = "https://linkedin.com/company/empresa-demo"


def _pagina(head: str = "", body: str = "") -> str:
    return f"<!doctype html><html><head>{head}</head><body>{body}</body></html>"


def _og(
    url: str,
    titulo: str,
    descripcion: str = "Una descripcion clara de la pagina.",
    imagen: str = IMAGEN,
    tipo: str = "website",
) -> str:
    etiquetas = [
        f'<link rel="canonical" href="{url}">',
        f'<meta property="og:title" content="{titulo}">',
        f'<meta property="og:description" content="{descripcion}">',
        f'<meta property="og:type" content="{tipo}">',
        f'<meta property="og:url" content="{url}">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    if imagen:
        etiquetas.extend(
            [
                f'<meta property="og:image" content="{imagen}">',
                '<meta property="og:image:width" content="1200">',
                '<meta property="og:image:height" content="630">',
            ]
        )
    return "".join(etiquetas)


def _same_as(*perfiles: str) -> str:
    datos = {"@context": "https://schema.org", "@graph": [{"sameAs": list(perfiles)}]}
    return f'<script type="application/ld+json">{json.dumps(datos)}</script>'


def test_detecta_og_completo_sin_problemas() -> None:
    # Arrange
    html = _pagina(
        head=_og(f"{BASE}/", "Empresa Demo") + _same_as("https://www.facebook.com/EmpresaDemo"),
        body='<a href="https://www.facebook.com/EmpresaDemo/">Siguenos</a>',
    )

    # Act
    datos = analizar_html(html, f"{BASE}/")

    # Assert
    assert datos["og"] == {
        "title": "Empresa Demo",
        "description": "Una descripcion clara de la pagina.",
        "image": IMAGEN,
        "type": "website",
        "url": f"{BASE}/",
    }
    assert datos["twitter_card"] == "summary_large_image"
    assert datos["schema_same_as"] == ["https://www.facebook.com/EmpresaDemo"]
    assert datos["problemas"] == []


def test_detecta_perfiles_sin_duplicados_y_atajos() -> None:
    # Arrange
    body = "".join(
        f'<a href="{href}">enlace</a>'
        for href in (
            "https://www.facebook.com/EmpresaDemo/",
            "https://facebook.com/empresademo?ref=pie",
            "https://m.facebook.com/empresademo",
            "https://www.instagram.com/empresa_demo/",
            "https://instagram.com/empresa_demo",
            "https://www.instagram.com/p/abc123/",
            "https://www.linkedin.com/company/empresa-demo/about/",
            "https://www.youtube.com/watch?v=abc",
            f"https://www.facebook.com/sharer/sharer.php?u={BASE}/",
            "https://wa.me/?text=Hola",
            f"{BASE}/contacto",
        )
    )

    # Act
    datos = analizar_html(_pagina(head=_og(f"{BASE}/", "Empresa Demo"), body=body), f"{BASE}/")

    # Assert
    assert datos["perfiles"] == [
        {"url": PERFIL_FB, "red": "facebook"},
        {"url": PERFIL_IG, "red": "instagram"},
        {"url": PERFIL_IN, "red": "linkedin"},
    ]
    assert datos["botones_compartir"] is True
    assert datos["whatsapp"] is True


def test_detecta_problemas_de_la_vista_previa() -> None:
    # Arrange
    head = (
        '<meta property="og:title" content="Inicio">'
        '<meta property="og:title" content="Otra cosa">'
        '<meta property="og:description" content="">'
        '<meta property="og:type" content="website">'
        f'<meta property="og:url" content="{BASE}/otra-pagina">'
    )
    body = '<a href="https://wa.me/570000000000">Escribenos</a>'

    # Act
    datos = analizar_html(_pagina(head=head, body=body), f"{BASE}/")

    # Assert
    assert datos["og"]["title"] == "Inicio"
    assert "falta og:image" in datos["problemas"]
    assert "og:description sin contenido" in datos["problemas"]
    assert "og:title declarado mas de una vez" in datos["problemas"]
    assert "og:url distinta de la URL de la pagina" in datos["problemas"]
    assert "falta twitter:card" in datos["problemas"]
    assert "sin enlaces a perfiles sociales" in datos["problemas"]
    assert datos["whatsapp"] is True
    assert datos["botones_compartir"] is False


@pytest.mark.parametrize("host", sorted(HOSTS_MENSAJERIA))
def test_un_enlace_para_escribir_a_la_marca_no_es_un_boton_para_compartir(host: str) -> None:
    # Arrange
    body = f'<a href="https://{host}/send?phone=570000000000">Escribenos</a>'

    # Act
    datos = analizar_html(_pagina(body=body), f"{BASE}/")

    # Assert
    assert datos["whatsapp"] is True
    assert datos["botones_compartir"] is False


def test_detecta_descripcion_con_nombre_de_archivo_y_perfil_fuera_de_same_as() -> None:
    # Arrange
    head = _og(f"{BASE}/politica", "Politica", descripcion="politica_de_datos-v2") + _same_as(
        PERFIL_FB
    )
    body = f'<a href="{PERFIL_FB}">fb</a><a href="{PERFIL_IG}">ig</a>'

    # Act
    datos = analizar_html(_pagina(head=head, body=body), f"{BASE}/politica/")

    # Assert
    assert datos["problemas"] == [
        "og:description parece un nombre de archivo",
        "perfil enlazado ausente de sameAs",
    ]


def test_resume_varias_paginas(tmp_path: Path) -> None:
    # Arrange
    perfiles = (
        f'<a href="{PERFIL_FB}">fb</a><a href="https://www.instagram.com/empresa_demo/">ig</a>'
    )
    paginas = {
        "inicio.html": _pagina(
            head=_og(f"{BASE}/", "Empresa Demo") + _same_as(PERFIL_FB, PERFIL_IG),
            body=perfiles,
        ),
        "servicios.html": _pagina(
            head=_og(f"{BASE}/servicios/", "Servicios", descripcion="Lo que hacemos.")
            + _same_as(PERFIL_FB),
            body=f'<a href="{PERFIL_FB}/">fb</a>',
        ),
        "precios.html": _pagina(
            head=_og(f"{BASE}/precios/", "Servicios", descripcion="Precios y planes.", imagen=""),
            body="<p>Sin perfiles</p>",
        ),
    }
    for nombre, html in paginas.items():
        (tmp_path / nombre).write_text(html, encoding="utf-8")
    (tmp_path / "manifest.json").write_text('{"entradas": []}', encoding="utf-8")

    # Act
    resumen = analizar_bronze(tmp_path)

    # Assert
    assert resumen["paginas"] == 3
    assert resumen["paginas_con_og_completo"] == 2
    assert resumen["perfiles"] == {PERFIL_FB: 2, PERFIL_IG: 1}
    assert resumen["red_por_perfil"] == {PERFIL_FB: "facebook", PERFIL_IG: "instagram"}
    assert resumen["previsualizacion"] == {
        "title": "Empresa Demo",
        "description": "Una descripcion clara de la pagina.",
        "image": IMAGEN,
        "fuente": f"{BASE}/",
    }
    assert resumen["imagenes_og"] == {IMAGEN: 2}
    assert resumen["problemas_frecuentes"] == {
        "og:title repetido en otra pagina": 2,
        "falta og:image": 1,
        "sin enlaces a perfiles sociales": 1,
    }
    assert [pagina["archivo"] for pagina in resumen["detalle"]] == [
        "inicio.html",
        "precios.html",
        "servicios.html",
    ]


def test_normaliza_perfiles_compuestos_y_descarta_rutas_que_no_son_perfil() -> None:
    # Arrange
    body = "".join(
        f'<a href="{href}">enlace</a>'
        for href in (
            "https://www.facebook.com/groups/123456/",
            "https://www.facebook.com/pages/Empresa-Demo/987654",
            "https://www.facebook.com/media/set/?set=a.1",
            "https://www.youtube.com/@EmpresaDemo",
        )
    )

    # Act
    datos = analizar_html(_pagina(head=_og(f"{BASE}/", "Empresa Demo"), body=body), f"{BASE}/")

    # Assert
    assert datos["perfiles"] == [
        {"url": "https://facebook.com/groups/123456", "red": "facebook"},
        {"url": "https://facebook.com/pages/empresa-demo/987654", "red": "facebook"},
        {"url": "https://youtube.com/@EmpresaDemo", "red": "youtube"},
    ]


def test_no_confunde_clases_compartidas_con_botones_y_precisa_la_dimension_faltante() -> None:
    # Arrange
    head = _og(f"{BASE}/", "Empresa Demo").replace(
        '<meta property="og:image:height" content="630">', ""
    )
    body = '<div class="shared-layout">contenido</div>'

    # Act
    datos = analizar_html(_pagina(head=head, body=body), f"{BASE}/")

    # Assert
    assert datos["botones_compartir"] is False
    assert "og:image sin alto declarado" in datos["problemas"]
    assert "og:image sin ancho ni alto declarados" not in datos["problemas"]


def test_resuelve_canonico_relativo_y_detalla_la_fuente_de_cada_dato(tmp_path: Path) -> None:
    # Arrange
    head = _og(f"{BASE}/nosotros/", "Nosotros").replace(
        f'href="{BASE}/nosotros/"', 'href="/nosotros/"'
    )
    body = f'<a href="{PERFIL_FB}">fb</a><a href="https://wa.me/570000000000">chat</a>'
    (tmp_path / "nosotros.html").write_text(_pagina(head=head, body=body), encoding="utf-8")

    # Act
    resumen = analizar_bronze(tmp_path)

    # Assert
    assert resumen["detalle"] == [
        {
            "archivo": "nosotros.html",
            "url": f"{BASE}/nosotros/",
            "og_completo": True,
            "og_image": IMAGEN,
            "twitter_card": "summary_large_image",
            "perfiles": [PERFIL_FB],
            "whatsapp": True,
            "botones_compartir": False,
            "problemas": ["perfiles enlazados sin sameAs en datos estructurados"],
        }
    ]


def test_analizar_bronze_no_toca_la_red(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    (tmp_path / "inicio.html").write_text(
        _pagina(head=_og(f"{BASE}/", "Empresa Demo"), body=f'<a href="{PERFIL_FB}">fb</a>'),
        encoding="utf-8",
    )

    def _sin_red(*args: object, **kwargs: object) -> None:
        raise AssertionError("Lo Specchio no debe abrir conexiones")

    monkeypatch.setattr(socket, "socket", _sin_red)
    monkeypatch.setattr(socket, "create_connection", _sin_red)

    # Act
    resumen = analizar_bronze(tmp_path)

    # Assert
    assert resumen["paginas"] == 1
    assert resumen["perfiles"] == {PERFIL_FB: 1}


def test_escribir_guarda_json_legible(tmp_path: Path) -> None:
    # Arrange
    resultado = {"paginas": 1, "previsualizacion": {"title": "Educacion sin limites"}}
    ruta = tmp_path / "gold" / "specchio.json"

    # Act
    destino = escribir(resultado, ruta)

    # Assert
    assert destino == ruta
    assert json.loads(ruta.read_text(encoding="utf-8")) == resultado
