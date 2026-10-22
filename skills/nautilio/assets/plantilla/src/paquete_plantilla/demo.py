"""Viaje de prueba sin internet: el primer encuentro con Nautilio.

Levanta en esta maquina una ciudad de prueba (127.0.0.1) con una puerta, una pagina con
datos personales, una pagina prohibida y una que niega el paso. Recorre los circulos con
el mismo codigo del viaje real, lee unos anuncios de muestra y escucha lo que unos
motores de respuesta de muestra dicen de la marca. Nada sale a la red.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from paquete_plantilla import config
from paquete_plantilla.anuncios import cargar_anuncios, reporte_markdown, resumen
from paquete_plantilla.config import Seed
from paquete_plantilla.eco import (
    Pregunta,
    Respuesta,
    escuchar,
    leer_corpus,
    respuestas_de_marca,
    validar_domande,
)
from paquete_plantilla.eco import reporte_markdown as reporte_eco
from paquete_plantilla.fetching import PoliteFetcher
from paquete_plantilla.pipeline import CaptureReport, capture

DEMO_DIR = config.DATA_DIR / "demo"
PASO_DEMO = 0.3

_HTML = "text/html; charset=utf-8"
CIUDAD: dict[str, tuple[int, str, str]] = {
    "/robots.txt": (200, "text/plain; charset=utf-8", "User-agent: *\nDisallow: /privado\n"),
    "/": (
        200,
        _HTML,
        "<html><head><title>Citta di prova</title></head><body><main>"
        "<h1>Citta di prova</h1>"
        "<p>Una empresa de prueba con tiendas, productos y un equipo de atencion.</p>"
        '<p><a href="/quienes-somos">Quienes somos</a></p>'
        "</main></body></html>",
    ),
    "/quienes-somos": (
        200,
        _HTML,
        "<html><head><title>Quienes somos</title></head><body><main>"
        "<h1>Quienes somos</h1>"
        "<p>Fundada en 1958, la empresa atiende tres ciudades.</p>"
        "<p>Atencion al cliente: escribe a maria.perez@gmail.com"
        " o llama al +57 310 555 1234.</p>"
        "<p>Gerente de tienda: Juan Ruiz, C.C. 1.144.555.666, juan.ruiz@hotmail.com.</p>"
        "</main></body></html>",
    ),
    "/privado": (200, _HTML, "<html><body><p>Zona privada.</p></body></html>"),
    "/cerrado": (403, "text/plain; charset=utf-8", "prohibido"),
    "/despues": (200, _HTML, "<html><body><p>Nunca deberia visitarse.</p></body></html>"),
}

ANUNCIOS_MUESTRA: list[dict[str, Any]] = [
    {
        "id": "m1",
        "plataforma": "meta",
        "pagina": "Marca Demo",
        "formato": "video",
        "texto": "Prueba el sabor que vuelve.",
        "titulo": "Nuevo",
        "cta": "Comprar",
        "url_destino": "https://tienda.ejemplo.com/nuevo",
        "url_ficha": "https://anuncios.ejemplo.com/m1",
        "duracion_s": 15,
    },
    {
        "id": "m2",
        "plataforma": "meta",
        "pagina": "Marca Demo",
        "formato": "video",
        "texto": "Prueba el sabor que vuelve.",
        "titulo": "Nuevo",
        "cta": "Comprar",
        "url_destino": "https://tienda.ejemplo.com/nuevo",
        "url_ficha": "https://anuncios.ejemplo.com/m2",
        "duracion_s": 15,
    },
    {
        "id": "m3",
        "plataforma": "meta",
        "pagina": "Marca Demo",
        "formato": "imagen",
        "texto": "Gana un viaje con cada empaque.",
        "titulo": "Promo",
        "cta": "Registrarse",
        "url_destino": "https://promo.ejemplo.com",
        "url_ficha": "https://anuncios.ejemplo.com/m3",
    },
    {
        "id": "m4",
        "plataforma": "google",
        "pagina": "Marca Demo",
        "formato": "video",
        "texto": "Cincuenta anos de historia.",
        "titulo": "Historia",
        "cta": "Ver mas",
        "url_destino": "https://ejemplo.com/historia",
        "url_ficha": "https://anuncios.ejemplo.com/m4",
        "duracion_s": 120,
    },
    {
        "id": "m5",
        "plataforma": "meta",
        "pagina": "Marca Demo",
        "formato": "carrusel",
        "texto": "Pide a domicilio hoy.",
        "titulo": "Domicilio",
        "cta": "Enviar mensaje",
        "url_destino": "https://mensajes.ejemplo.com/demo",
        "url_ficha": "https://anuncios.ejemplo.com/m5",
    },
    {
        "id": "m6",
        "plataforma": "google",
        "pagina": "Marca Demo",
        "formato": "imagen",
        "texto": "Gana un viaje con cada empaque.",
        "titulo": "Promo",
        "cta": "Registrarse",
        "url_destino": "https://promo.ejemplo.com",
        "url_ficha": "https://anuncios.ejemplo.com/m6",
    },
]


MARCA_DEMO = "Citta di prova"
DOMINIO_DEMO = "citta-di-prova.example"
RIVALES_DEMO = ("Rival Uno", "Rival Dos")
ECO_PREGUNTAS = (
    Pregunta(
        id="c1",
        set="conversacional",
        etapa="decision",
        producto="domicilios",
        persona="familia de cuatro",
        situacion="comprar a domicilio",
        restricciones="presupuesto medio, tres ciudades",
        prompt="Que empresa en tres ciudades vende a domicilio productos de temporada "
        "para una familia de cuatro con presupuesto medio?",
        insumo="ventas",
        resultado_negocio="pedidos a domicilio",
    ),
    Pregunta(
        id="c2",
        set="conversacional",
        etapa="comparacion",
        producto="tiendas",
        persona="cliente que ya compra a un rival",
        situacion="cambiar de proveedor",
        restricciones="atencion rapida",
        prompt="Que alternativas hay a Rival Uno para comprar productos de temporada "
        "con atencion al cliente rapida?",
        insumo="soporte",
        resultado_negocio="clientes nuevos",
    ),
    Pregunta(
        id="c3",
        set="conversacional",
        etapa="descubrimiento",
        producto="marca",
        persona="persona que se muda a la ciudad",
        situacion="buscar una empresa confiable",
        restricciones="trayectoria larga, varias ciudades",
        prompt="Que empresas con decadas de trayectoria tienen tiendas en varias ciudades "
        "y buena atencion al cliente?",
        insumo="foros",
        resultado_negocio="reconocimiento de marca",
    ),
    Pregunta(
        id="c4",
        set="conversacional",
        etapa="decision",
        producto="pedidos para oficinas",
        persona="oficina pequena",
        situacion="pedido urgente",
        restricciones="envio el mismo dia, pedido minimo bajo",
        prompt="Donde comprar con envio el mismo dia para una oficina pequena con pedido "
        "minimo bajo?",
        insumo="ventas",
        resultado_negocio="pedidos corporativos",
    ),
    Pregunta(
        id="m1",
        set="marca",
        etapa="descubrimiento",
        producto="marca",
        persona="",
        situacion="",
        restricciones="",
        prompt="Que es Citta di prova y donde tiene tiendas?",
        insumo="brief",
        resultado_negocio="narrativa de marca",
    ),
    Pregunta(
        id="m2",
        set="marca",
        etapa="decision",
        producto="servicio",
        persona="",
        situacion="",
        restricciones="",
        prompt="Citta di prova tiene buena atencion al cliente?",
        insumo="brief",
        resultado_negocio="narrativa de marca",
    ),
)
ECO_RESPUESTAS = (
    Respuesta(
        "c1",
        "motor-a",
        "2026-10-22",
        "Citta di prova vende a domicilio en tres ciudades; Rival Uno tambien es una opcion.",
        ("https://citta-di-prova.example/",),
    ),
    Respuesta("c1", "motor-b", "2026-10-22", "Prueba Rival Uno.", ("https://rival-uno.example/",)),
    Respuesta(
        "c2",
        "motor-a",
        "2026-10-22",
        "Rival Dos y Citta di prova responden rapido.",
        ("https://blog.example/comparativa",),
    ),
    Respuesta(
        "c3",
        "motor-a",
        "2026-10-22",
        "Rival Uno y Rival Dos tienen tiendas en varias ciudades.",
        ("https://directorio.example/tiendas",),
    ),
    Respuesta(
        "c4",
        "motor-a",
        "2026-10-22",
        "Rival Dos envia el mismo dia.",
        ("https://rival-dos.example/",),
    ),
    Respuesta(
        "m1",
        "motor-a",
        "2026-10-22",
        "Citta di prova es una empresa con tiendas, productos y atencion al cliente.",
        (),
    ),
    Respuesta("m2", "motor-b", "2026-10-22", "No tengo informacion suficiente sobre ella.", ()),
)


@dataclass(frozen=True, slots=True)
class ResultadoDemo:
    """Lo que vio el viaje de prueba, con cifras contadas por el codigo."""

    viaje: CaptureReport
    muse: dict[str, Any]
    reporte_muse: Path
    eco: dict[str, Any]
    reporte_eco: Path
    destino: Path


class _Ciudad(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        no_existe = (404, "text/plain", "no existe")
        status, content_type, body = CIUDAD.get(self.path, no_existe)
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: Any) -> None:
        return


def recorrer(destino: Path = DEMO_DIR, paso: float = PASO_DEMO) -> ResultadoDemo:
    """Hace el viaje completo en la ciudad de prueba y devuelve lo que encontro."""
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Ciudad)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    base = f"http://127.0.0.1:{servidor.server_address[1]}"
    semillas = (
        Seed(id="inicio", url=f"{base}/", titulo="Inicio", categoria="demo"),
        Seed(
            id="quienes-somos",
            url=f"{base}/quienes-somos",
            titulo="Quienes somos",
            categoria="demo",
        ),
        Seed(id="privado", url=f"{base}/privado", titulo="Zona privada", categoria="demo"),
        Seed(id="cerrado", url=f"{base}/cerrado", titulo="Puerta cerrada", categoria="demo"),
        Seed(id="despues", url=f"{base}/despues", titulo="Despues", categoria="demo"),
    )
    try:
        viaje = capture(
            seeds=semillas,
            fetcher=PoliteFetcher(delay_seconds=paso),
            raw_dir=destino / "raw",
            processed_dir=destino / "processed",
            gold_dir=destino / "gold",
            manifest_path=destino / "raw" / "manifest.json",
            corpus_path=destino / "gold" / "corpus.jsonl",
            inventory_path=destino / "gold" / "inventario_enmascarado.json",
        )
    finally:
        servidor.shutdown()
        servidor.server_close()

    muestra = destino / "raw" / "anuncios" / "demo.jsonl"
    muestra.parent.mkdir(parents=True, exist_ok=True)
    muestra.write_text(
        "\n".join(json.dumps(a, ensure_ascii=False) for a in ANUNCIOS_MUESTRA) + "\n",
        encoding="utf-8",
    )
    anuncios = cargar_anuncios(muestra)
    reporte = reporte_markdown(
        anuncios, "demo", salida=destino / "gold" / "inteligencia-anuncios-demo.md"
    )
    corpus = leer_corpus(destino / "gold" / "corpus.jsonl")
    escucha = escuchar(
        ECO_PREGUNTAS, ECO_RESPUESTAS, MARCA_DEMO, DOMINIO_DEMO, RIVALES_DEMO, corpus
    )
    ruta_eco = reporte_eco(
        MARCA_DEMO,
        escucha,
        validar_domande(ECO_PREGUNTAS, MARCA_DEMO, minimo=4),
        respuestas_de_marca(ECO_PREGUNTAS, ECO_RESPUESTAS),
        salida=destino / "gold" / "eco-demo.md",
    )
    return ResultadoDemo(
        viaje=viaje,
        muse=resumen(anuncios),
        reporte_muse=reporte,
        eco=escucha,
        reporte_eco=ruta_eco,
        destino=destino,
    )


def narrar(
    resultado: ResultadoDemo,
    paso: float = PASO_DEMO,
    escribir: Callable[[str], None] = print,
) -> None:
    """Cuenta el viaje círculo por círculo, con cifras reales."""
    estados = resultado.viaje.statuses
    conteo = resultado.viaje.counts
    mascaras = resultado.viaje.inventory.get("por_tipo", {})
    muse = resultado.muse

    pasaron = _n(estados.get("ok", 0), "página", "páginas")
    cerradas = estados.get("robots_blocked", 0)
    sin_visitar = _n(estados.get("not_attempted", 0), "página quedó", "páginas quedaron")
    crudos = _n(conteo.bronze, "documento crudo", "documentos crudos")
    borrados = _n(resultado.viaje.inventory.get("total", 0), "dato personal", "datos personales")
    correos = _n(mascaras.get("correo", 0), "correo", "correos")
    telefonos = _n(mascaras.get("telefono", 0), "teléfono", "teléfonos")
    ids = _n(mascaras.get("identificacion", 0), "identificación", "identificaciones")
    citables = _n(conteo.gold, "documento citable", "documentos citables")
    limbo = _n(resultado.viaje.requiere_js, "página espera", "páginas esperan")
    anuncios = _n(muse["total"], "anuncio", "anuncios")
    unicos = _n(muse["unicos"], "creativo único", "creativos únicos")
    repetidos = _n(muse["repetidos"], "repetido", "repetidos")
    real = config.REQUEST_DELAY_SECONDS
    eco = resultado.eco
    aparece = f"{eco['visibles']} de {eco['con_respuesta']} preguntas ({eco['visibilidad']:g} %)"
    citas = _n(eco["citas_propias"], "cita propia", "citas propias")
    brechas = _n(len(eco["brechas"]), "brecha", "brechas")
    responde = eco["cubiertas"]

    lineas = [
        "",
        "NAUTILIO · viaje de prueba en una ciudad local, sin internet",
        "Per me si va ne la città dei dati",
        "",
        f"La Porta     dejó pasar {pasaron} y cerró {cerradas} que el sitio prohíbe",
        f"Il Passo     {paso:g} s entre peticiones en la prueba ({real:g} s en un viaje real)",
        f"Caronte      negó el paso y detuvo el viaje; {sin_visitar} sin visitar",
        f"Inferno      {crudos} en {_relativa(resultado.destino / 'raw')}",
        f"Purgatorio   el Lete borró {borrados}: {correos}, {telefonos} y {ids}",
        f"Paradiso     {citables} en {_relativa(resultado.destino / 'gold')}, con su fuente",
        f"Limbo        {limbo} revisión humana",
        "",
        f"Le Muse      {anuncios}: {unicos} y {repetidos}",
        f"             lectura en {_relativa(resultado.reporte_muse)}",
        "",
        f"L'Eco        la marca aparece en {aparece}; share of voice {eco['share_of_voice']:g} %",
        f"             {citas}; {brechas}, y el Paradiso ya responde {responde}",
        f"             escucha en {_relativa(resultado.reporte_eco)}",
        "",
        "Il Giudizio  tu turno:",
        "  1. Pon tu correo en CONTACTO (config.py).",
        "  2. Cambia las semillas por páginas reales que den permiso.",
        "  3. make capture",
        "",
    ]
    for linea in lineas:
        escribir(linea)


def _n(cantidad: int, singular: str, plural: str) -> str:
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _relativa(path: Path) -> str:
    try:
        return path.resolve().relative_to(config.PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
