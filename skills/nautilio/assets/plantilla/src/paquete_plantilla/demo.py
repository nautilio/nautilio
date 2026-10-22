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

from paquete_plantilla import config, cronaca
from paquete_plantilla.anuncios import cargar_anuncios, reporte_markdown, resumen
from paquete_plantilla.config import Seed
from paquete_plantilla.eco import (
    Pregunta,
    Respuesta,
    escuchar,
    escuchar_por_motor,
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
        "<html><head><title>Citta di prova</title>"
        '<meta property="og:title" content="Citta di prova">'
        '<meta property="og:description" content="Tiendas propias en tres ciudades y '
        'entregas a domicilio todos los días.">'
        '<meta property="og:image" content="/portada.jpg">'
        "</head><body><main>"
        "<h1>Citta di prova</h1>"
        "<p>Una empresa de prueba con tiendas propias en tres ciudades, productos de temporada "
        "y un equipo de atención al cliente. Desde 1958 vende a domicilio y "
        "abre sus tiendas los siete días de la semana.</p>"
        '<p><a href="/quienes-somos">Quiénes somos</a></p>'
        '</main><footer><a href="https://www.instagram.com/cittadiprova/">Instagram</a> '
        '<a href="https://www.facebook.com/cittadiprova">Facebook</a></footer></body></html>',
    ),
    "/quienes-somos": (
        200,
        _HTML,
        "<html><head><title>Quiénes somos</title></head><body><main>"
        "<h1>Quiénes somos</h1>"
        "<p>Fundada en 1958, la empresa atiende tres ciudades.</p>"
        "<p>Atención al cliente: escribe a maria.perez@gmail.com"
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
        "texto": "Cincuenta años de historia.",
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
        prompt="¿Qué empresa en tres ciudades vende a domicilio productos de temporada "
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
        restricciones="atención rápida",
        prompt="¿Qué alternativas hay a Rival Uno para comprar productos de temporada "
        "con atención al cliente rápida?",
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
        prompt="¿Qué empresas con décadas de trayectoria tienen tiendas en varias ciudades "
        "y buena atención al cliente?",
        insumo="foros",
        resultado_negocio="reconocimiento de marca",
    ),
    Pregunta(
        id="c4",
        set="conversacional",
        etapa="decision",
        producto="pedidos para oficinas",
        persona="oficina pequeña",
        situacion="pedido urgente",
        restricciones="envío el mismo día, pedido mínimo bajo",
        prompt="¿Dónde comprar con envío el mismo día para una oficina pequeña con pedido "
        "mínimo bajo?",
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
        prompt="¿Qué es Citta di prova y dónde tiene tiendas?",
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
        prompt="¿Citta di prova tiene buena atención al cliente?",
        insumo="brief",
        resultado_negocio="narrativa de marca",
    ),
)
ECO_RESPUESTAS = (
    Respuesta(
        "c1",
        "motor-a",
        "2026-10-22",
        "Citta di prova vende a domicilio en tres ciudades; Rival Uno también es una opción.",
        ("https://citta-di-prova.example/",),
    ),
    Respuesta("c1", "motor-b", "2026-10-22", "Prueba Rival Uno.", ("https://rival-uno.example/",)),
    Respuesta(
        "c2",
        "motor-a",
        "2026-10-22",
        "Rival Dos y Citta di prova responden rápido.",
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
        "Rival Dos envía el mismo día.",
        ("https://rival-dos.example/",),
    ),
    Respuesta(
        "m1",
        "motor-a",
        "2026-10-22",
        "Citta di prova es una empresa con tiendas, productos y atención al cliente.",
        (),
    ),
    Respuesta("m2", "motor-b", "2026-10-22", "No tengo información suficiente sobre ella.", ()),
)


def _scoperte_demo(base: str) -> dict[str, Any]:
    """Hallazgos de muestra como los redactaria el agente. El tercero cita algo que el sitio
    no dice: el codigo lo descarta y no llega a La Cronaca."""
    return {
        "hallazgos": [
            {
                "tema": "Servicio",
                "hallazgo": "Vende a domicilio y no cierra ningún día de la semana.",
                "cita": "Desde 1958 vende a domicilio y abre sus tiendas los siete días de la "
                "semana.",
                "url_cita": f"{base}/",
            },
            {
                "tema": "Historia",
                "hallazgo": "Lleva más de seis décadas en el oficio y hoy atiende tres ciudades.",
                "cita": "Fundada en 1958, la empresa atiende tres ciudades.",
                "url_cita": f"{base}/quienes-somos",
            },
            {
                "tema": "Historia",
                "hallazgo": "Tiene tiendas en cinco países.",
                "cita": "Fundada en 1958, la empresa atiende cinco países.",
                "url_cita": f"{base}/quienes-somos",
            },
        ],
        "vacios": [
            {
                "tema": "Costo del envío",
                "por_que_importa": "Quien pide a domicilio quiere saber cuánto paga antes de "
                "pedir.",
            }
        ],
        "insights": [
            {
                "titulo": "Su fuerza es la constancia: décadas vendiendo a domicilio",
                "por_que_importa": "Es lo que la distingue de un rival nuevo, y el sitio lo dice "
                "dos veces.",
                "hallazgos": ["h1", "h2"],
            }
        ],
    }


def _risposta_demo(base: str) -> dict[str, Any]:
    """Acciones de muestra: lo primero que haria la marca con lo encontrado."""
    return {
        "gran_idea": "Citta di prova aparece en 2 de 4 preguntas a los asistentes, pero su sitio "
        "no dice lo primero que pregunta quien compra a domicilio: cuánto cuesta el envío.",
        "historia": [
            "Desde 1958 vende a domicilio en tres ciudades: es su diferencia.",
            "Los asistentes la recomiendan en 2 de 4 preguntas y Rival Uno aparece más.",
            "Lo primero es publicar el costo del envío; lo demás puede esperar un mes.",
        ],
        "acciones": [
            {
                "titulo": "Una página de envíos que diga cuánto cuesta y cuándo llega",
                "prioridad": 1,
                "resultado": "que el asistente la recomiende cuando alguien pregunta por envíos",
                "esfuerzo": "bajo",
                "cuando": "hoy",
                "que_debe_decir": [
                    "Costo del envío en cada ciudad",
                    "Pedido mínimo y hora de corte para recibir el mismo día",
                ],
                "evidencia_disponible": [f"{base}/"],
                "falta_confirmar": ["el costo del envío", "el pedido mínimo"],
            },
            {
                "titulo": "Quiénes somos con las tres ciudades por su nombre",
                "prioridad": 2,
                "esfuerzo": "bajo",
                "cuando": "este mes",
                "que_debe_decir": ["Las tres ciudades y la dirección de cada tienda"],
                "evidencia_disponible": [f"{base}/quienes-somos"],
                "falta_confirmar": ["las direcciones de las tiendas"],
            },
        ],
    }


@dataclass(frozen=True, slots=True)
class ResultadoDemo:
    """Lo que vio el viaje de prueba, con cifras contadas por el codigo."""

    viaje: CaptureReport
    muse: dict[str, Any]
    reporte_muse: Path
    eco: dict[str, Any]
    reporte_eco: Path
    cronaca: Path
    datos_cronaca: cronaca.DatosCronaca
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
            titulo="Quiénes somos",
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
    for nombre, contenido in (
        ("hallazgos.json", _scoperte_demo(base)),
        ("risposta.json", _risposta_demo(base)),
    ):
        (destino / "gold" / nombre).write_text(
            json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    datos = cronaca.reunir(
        raw_dir=destino / "raw",
        gold_dir=destino / "gold",
        eco_dir=destino / "eco",
        empresa=MARCA_DEMO,
        dominio=DOMINIO_DEMO,
        eco=escucha,
        eco_marca=MARCA_DEMO,
        muse=[{"marca": "Marca Demo", **resumen(anuncios)}],
        paso=paso,
        eco_por_motor=escuchar_por_motor(
            ECO_PREGUNTAS, ECO_RESPUESTAS, MARCA_DEMO, DOMINIO_DEMO, RIVALES_DEMO, corpus
        ),
        eco_de_marca=respuestas_de_marca(ECO_PREGUNTAS, ECO_RESPUESTAS, maximo=4000),
    )
    ruta_cronaca = cronaca.escribir(datos, destino / "gold" / "cronaca.html")
    return ResultadoDemo(
        viaje=viaje,
        muse=resumen(anuncios),
        reporte_muse=reporte,
        eco=escucha,
        reporte_eco=ruta_eco,
        cronaca=ruta_cronaca,
        datos_cronaca=datos,
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
    scoperte = resultado.datos_cronaca.scoperte
    hallados = _n(len(scoperte["hallazgos"]), "hallazgo", "hallazgos")
    descartados = _n(len(scoperte["descartados"]), "descartado", "descartados")
    sitio = resultado.datos_cronaca.specchio or {"paginas": 0, "paginas_con_og_completo": 0}
    perfiles = _n(len(sitio.get("perfiles", {})), "perfil social", "perfiles sociales")
    acciones = resultado.datos_cronaca.acciones

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
        f"Le Scoperte  {hallados} con su cita; {descartados} porque su cita no está en el sitio",
        f"Lo Specchio  vista previa completa en {sitio['paginas_con_og_completo']} de "
        f"{sitio['paginas']} páginas; {perfiles} enlazados",
        "",
        f"Le Muse      {anuncios}: {unicos} y {repetidos}",
        f"             lectura en {_relativa(resultado.reporte_muse)}",
        "",
        f"L'Eco        la marca aparece en {aparece}; share of voice {eco['share_of_voice']:g} %",
        f"             {citas}; {brechas}, y el Paradiso ya responde {responde}",
        f"             escucha en {_relativa(resultado.reporte_eco)}",
        "",
        f"La Risposta  {_n(len(acciones), 'acción', 'acciones')}; la primera: "
        f"{acciones[0]['titulo'] if acciones else '-'}",
        "",
        f"La Cronaca   el viaje contado para personas: {_relativa(resultado.cronaca)}",
        "             ábrela en el navegador; se imprime como PDF",
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
