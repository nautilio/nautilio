"""La Cronaca: el viaje contado para personas.

Un HTML autocontenido, en tinta sobre papel, que se abre en cualquier navegador y se imprime
como PDF. Cuenta en lenguaje humano lo que encontro el viaje: lo que la empresa dice de si
misma, los hallazgos con su cita, como se ve al compartirla, lo que ensenan sus anuncios,
como la ven los motores de respuesta, que hacer primero y, al final, como se hizo.

Las cifras salen de los archivos del viaje, contadas por el codigo. Los hallazgos y las
acciones los redacta el agente y solo llegan aqui si su cita existe en el Paradiso. El texto
que viene del sitio se escapa siempre: es contenido no confiable.
"""

from __future__ import annotations

import csv
import html
import json
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from paquete_plantilla import config, scoperte, specchio
from paquete_plantilla.anuncios import cargar_anuncios, resumen
from paquete_plantilla.extracting import mask_personal_data

EXTRACTO_MAXIMO = 320
EXTRACTO_MINIMO = 45
PAGINA_CASI_VACIA = 200
MUSE_CONSULTA = "muse-sin-anuncios.json"
RESPUESTA_MAXIMA = 260
# Por debajo de este parecido de palabras, una pagina no se ofrece como respuesta a una brecha.
UMBRAL_CERCANA = 0.3
MAXIMO_RIVALES = 10
MAXIMO_BRECHAS = 10
MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
PROBLEMAS_LEGIBLES = {
    "falta og:image": "no hay imagen para la vista previa",
    "falta og:description": "no hay descripción para la vista previa",
    "falta og:title": "no hay título para la vista previa",
    "falta og:type": "no declara qué tipo de contenido es al compartirlo",
    "falta og:url": "no declara la dirección que debe mostrar al compartirlo",
    "og:title repetido en otra pagina": "el mismo título se repite en varias páginas",
    "og:description repetida en otra pagina": "la misma descripción se repite en varias páginas",
    "og:image sin ancho ni alto declarados": "la imagen de vista previa no declara su tamaño",
    "falta twitter:card": "no declara cómo mostrar el enlace en redes de mensajes cortos",
    "perfiles enlazados sin sameAs en datos estructurados": "los perfiles no están atados a la "
    "marca en los datos estructurados (sameAs)",
    "perfil enlazado ausente de sameAs": "un perfil enlazado falta en los datos estructurados",
    "sin enlaces a perfiles sociales": "la página no lleva a ningún perfil social",
    "og:description parece un nombre de archivo": "la descripción para compartir parece el "
    "nombre de un archivo",
    "og:image no es una URL absoluta": "la imagen de vista previa no tiene una dirección completa",
    "og:url distinta de la URL de la pagina": "la vista previa apunta a otra dirección",
    "datos estructurados con JSON invalido": "los datos estructurados tienen un error de formato",
}


@dataclass(slots=True)
class DatosCronaca:
    """Todo lo que La Cronaca necesita, ya contado por el codigo."""

    empresa: str
    dominio: str
    fecha: str
    estados: dict[str, int]
    paso: float
    documentos: list[dict[str, Any]]
    lete: dict[str, Any]
    limbo: int
    muse: list[dict[str, Any]] = field(default_factory=list)
    eco: dict[str, Any] | None = None
    eco_marca: str = ""
    eco_preguntas: list[str] = field(default_factory=list)
    eco_conteo: dict[str, int] = field(default_factory=dict)
    ritratto_pendientes: int | None = None
    eco_por_motor: dict[str, dict[str, Any]] = field(default_factory=dict)
    eco_de_marca: list[dict[str, str]] = field(default_factory=list)
    scoperte: dict[str, Any] = field(default_factory=dict)
    acciones: list[dict[str, Any]] = field(default_factory=list)
    specchio: dict[str, Any] | None = None
    muse_consulta: dict[str, Any] | None = None
    relato: dict[str, Any] = field(default_factory=dict)
    contacto_informe: str = ""


def reunir(
    raw_dir: Path = config.RAW_DIR,
    gold_dir: Path = config.GOLD_DIR,
    eco_dir: Path = config.DATA_DIR / "eco",
    empresa: str = config.EMPRESA,
    dominio: str = config.DOMINIO,
    eco: dict[str, Any] | None = None,
    eco_marca: str = "",
    muse: list[dict[str, Any]] | None = None,
    paso: float | None = None,
    eco_por_motor: dict[str, dict[str, Any]] | None = None,
    eco_de_marca: list[dict[str, str]] | None = None,
) -> DatosCronaca:
    """Lee los archivos del viaje y arma los datos de La Cronaca."""
    manifiesto = _leer_json(raw_dir / "manifest.json") or {}
    entradas = manifiesto.get("entradas", [])
    estados: dict[str, int] = {}
    for entrada in entradas:
        estado = str(entrada.get("status", ""))
        estados[estado] = estados.get(estado, 0) + 1
    politica = manifiesto.get("politica", {})
    fecha = str(manifiesto.get("generado_en", ""))[:10] or date.today().isoformat()

    documentos = []
    for registro in _leer_jsonl(gold_dir / "corpus.jsonl"):
        ruta = gold_dir / Path(str(registro.get("ruta_gold", ""))).name
        texto = ruta.read_text(encoding="utf-8") if ruta.is_file() else ""
        documentos.append(
            {
                "titulo": str(registro.get("titulo", "")),
                "url": str(registro.get("url_cita", "")),
                "caracteres": int(registro.get("caracteres", 0) or 0),
                "extracto": extracto(texto),
            }
        )

    if muse is None:
        muse = []
        anuncios_dir = raw_dir / "anuncios"
        for archivo in sorted(anuncios_dir.glob("*.jsonl")) if anuncios_dir.is_dir() else []:
            anuncios = cargar_anuncios(archivo)
            if anuncios:
                muse.append({"marca": archivo.stem, **resumen(anuncios)})

    domande = eco_dir / "domande.csv"
    preguntas, conteo = _preguntas_de_decision(domande)
    ritratto = eco_dir / "ritratto.csv"
    textos = scoperte.textos_del_paradiso(gold_dir)
    sitio = specchio.analizar_bronze(raw_dir) if any(raw_dir.glob("*.html")) else None
    hallazgos = scoperte.cargar_hallazgos(textos, gold_dir / scoperte.HALLAZGOS_PATH.name)
    acciones = scoperte.cargar_acciones(textos, gold_dir / scoperte.RISPOSTA_PATH.name)
    # Cifras que la Gran Idea puede usar: las del sitio y las que conto el codigo.
    contadas = [len(documentos), len(hallazgos["hallazgos"]), len(acciones), *estados.values()]
    if sitio:
        contadas += [len(sitio.get("perfiles", {}))]
    permitidas = scoperte.cifras(" ".join(textos.values()))
    permitidas |= scoperte.cifras(json.dumps([eco, sitio, contadas], ensure_ascii=False))
    if eco:
        rivales = [
            n
            for n, t in eco["menciones"].items()
            if t > eco["menciones"].get(eco_marca or empresa, 0)
        ]
        permitidas |= {str(len(rivales)), str(len(eco["menciones"]) - 1)}
    return DatosCronaca(
        empresa=empresa,
        dominio=dominio,
        fecha=fecha,
        estados=estados,
        paso=paso
        if paso is not None
        else float(politica.get("retardo_segundos", config.REQUEST_DELAY_SECONDS)),
        documentos=documentos,
        lete=_leer_json(gold_dir / "inventario_enmascarado.json") or {"total": 0, "por_tipo": {}},
        limbo=sum(1 for entrada in entradas if entrada.get("requiere_js")),
        muse=muse,
        eco=eco,
        eco_marca=eco_marca or empresa,
        eco_preguntas=preguntas,
        eco_conteo=conteo,
        ritratto_pendientes=_ritratto_pendientes(ritratto) if ritratto.is_file() else None,
        eco_por_motor=eco_por_motor or {},
        eco_de_marca=eco_de_marca or [],
        scoperte=hallazgos,
        acciones=acciones,
        specchio=sitio if sitio and sitio.get("paginas") else None,
        muse_consulta=None if muse else _leer_json(gold_dir / MUSE_CONSULTA),
        relato=scoperte.cargar_relato(permitidas, gold_dir / scoperte.RISPOSTA_PATH.name),
        contacto_informe=str(getattr(config, "CONTACTO_INFORME", "") or ""),
    )


def escribir(datos: DatosCronaca, salida: Path | None = None) -> Path:
    """Escribe La Cronaca y devuelve su ruta."""
    ruta = salida or config.GOLD_DIR / "cronaca.html"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(render(datos), encoding="utf-8")
    return ruta


def extracto(markdown: str) -> str:
    """Primer parrafo con sustancia, sin front matter, titulos ni enlaces sueltos."""
    cuerpo = re.sub(r"\A---\n.*?\n---\n", "", markdown, flags=re.S)
    for parrafo in re.split(r"\n\s*\n", cuerpo):
        if re.match(r"\s*(#|[-*+] |\d+[.)] )", parrafo):  # titulos y listas no son una cita
            continue
        texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", parrafo)
        texto = re.sub(r"\*\*|__|(?<!\w)[*_]|[*_](?!\w)", "", texto)  # negritas y cursivas
        texto = re.sub(r"\s+", " ", texto).strip()
        if len(texto) < EXTRACTO_MINIMO or "enmascarad" in texto or texto.endswith(":"):
            continue
        if len(texto) <= EXTRACTO_MAXIMO:
            return texto
        corte = texto[:EXTRACTO_MAXIMO]
        punto = corte.rfind(". ")
        if punto > EXTRACTO_MINIMO:
            return corte[: punto + 1]
        return corte[: corte.rfind(" ")].rstrip(",;:") + "…"
    return ""


# --- Render ---------------------------------------------------------------------------


def render(datos: DatosCronaca) -> str:
    """Devuelve el HTML completo de La Cronaca."""
    idea = _gran_idea(datos)
    secciones = [
        _portada(datos),
        idea or _en_una_frase(datos),
        _lo_esencial(datos),
        _l_eco(datos),
        _le_scoperte(datos),
        _lo_specchio(datos),
        _le_muse(datos),
        _la_risposta(datos),
        _siguiente_paso(datos),
        _para_completar(datos),
        _con_sus_palabras(datos),
        _los_circulos(datos, con_resumen=bool(idea)),
        _colofon(datos),
    ]
    titulo = _e(f"La Cronaca · {datos.empresa}")
    return (
        '<!doctype html>\n<html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{titulo}</title><style>{_CSS}</style></head><body><main class="hoja">'
        + "".join(secciones)
        + "</main></body></html>\n"
    )


def _portada(datos: DatosCronaca) -> str:
    return (
        '<header class="portada">'
        f"{_espiral()}"
        '<div><p class="epigrafe">Per me si va ne la città dei dati</p>'
        f"<h1>{_e(datos.empresa)}</h1>"
        f'<p class="sub">La Cronaca de un viaje por <span>{_e(datos.dominio)}</span> · '
        f"{_e(_fecha_larga(datos.fecha))}</p></div></header>"
    )


def _gran_idea(datos: DatosCronaca) -> str:
    relato = datos.relato
    if not relato.get("gran_idea"):
        return ""
    historia = "".join(f"<li>{_e(frase)}</li>" for frase in relato.get("historia", []))
    return (
        '<section class="idea"><p class="etiqueta">La idea en una frase</p>'
        f'<p class="grande">{_e(relato["gran_idea"])}</p>'
        + (
            '<p class="etiqueta">La historia en tres minutos</p>'
            f'<ol class="historia">{historia}</ol>'
            if historia
            else ""
        )
        + "</section>"
    )


def _siguiente_paso(datos: DatosCronaca) -> str:
    contacto = datos.contacto_informe.strip()
    if not contacto:
        return ""
    if re.match(r"https?://", contacto):
        destino = contacto
    elif re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contacto):
        destino = f"mailto:{contacto}"
    else:
        destino = ""
    enlace = f'<a href="{_e(destino)}">{_e(contacto)}</a>' if destino else _e(contacto)
    return (
        '<section class="cta">'
        + _cabecera("Siguiente paso", "Este informe dice qué hacer; el cómo se puede hacer juntos")
        + f"<p>Si quiere ayuda para llevar estas acciones a su sitio, escriba a {enlace}.</p>"
        "</section>"
    )


def _cabecera(etiqueta: str, titular: str) -> str:
    """Titular que dice la conclusion; el nombre de la seccion queda como etiqueta."""
    return f"<h2><small>{_e(etiqueta)}</small>{_e(titular)}</h2>"


def _en_una_frase(datos: DatosCronaca) -> str:
    visitadas = datos.estados.get("ok", 0)
    cerradas = datos.estados.get("robots_blocked", 0)
    citables = len(_citables(datos))
    borrados = int(datos.lete.get("total", 0))
    frase = f"Visitamos {_n(visitadas, 'página pública', 'páginas públicas')} de {datos.dominio}. "
    frase += "Antes de entrar revisamos las reglas del sitio para robots (robots.txt)"
    frase += f", que cerraron {cerradas}" if cerradas else ""
    fallidas = sum(
        datos.estados.get(estado, 0)
        for estado in ("http_error", "network_error", "missing", "extract_error")
    )
    frase += (
        f"; {_n(fallidas, 'página no se pudo leer', 'páginas no se pudieron leer')}"
        if fallidas
        else ""
    )
    frase += f", avanzamos sin prisa y salimos con {_n(citables, 'documento', 'documentos')} "
    frase += "con texto que se puede citar"
    if borrados:
        frase += (
            f"; en el camino el Lete borró {_n(borrados, 'dato personal', 'datos personales')}."
        )
    else:
        frase += ", sin correos, teléfonos ni números de identificación de personas."
    parrafos = [frase]
    if datos.eco and datos.eco["con_respuesta"]:
        eco = datos.eco
        motores = list(datos.eco_por_motor)
        if len(motores) > 1:
            a_quien = f"a {len(motores)} asistentes de IA ({_enumerar(motores)})"
        else:
            a_quien = "a los asistentes de IA"
        veces = {0: "no apareció en ninguna", 1: "apareció en una sola"}.get(
            eco["visibles"], f"apareció en {eco['visibles']}"
        )
        parrafos.append(
            f"Hicimos {_n(eco['con_respuesta'], 'pregunta', 'preguntas')} {a_quien} como las "
            f"haría un cliente, sin decir su nombre: {datos.eco_marca} {veces}."
        )
    return '<section class="lede">' + "".join(f"<p>{_e(p)}</p>" for p in parrafos) + "</section>"


def _lo_esencial(datos: DatosCronaca) -> str:
    cifras = []
    hallazgos = datos.scoperte.get("hallazgos", [])
    if hallazgos:
        cifras.append((str(len(hallazgos)), "hallazgos con su cita"))
    if datos.specchio:
        cifras.append((str(len(datos.specchio["perfiles"])), "perfiles sociales enlazados"))
    if datos.eco and datos.eco["con_respuesta"]:
        eco = datos.eco
        cifras.append(
            (
                f"{eco['visibles']} de {eco['con_respuesta']}",
                "preguntas simuladas de clientes donde aparece",
            )
        )
    if datos.acciones:
        cifras.append((str(len(datos.acciones)), "acciones para empezar"))
    if len(cifras) < 2:
        return ""
    celdas = "".join(
        f"<div><strong>{_e(cifra)}</strong><span>{_e(texto)}</span></div>"
        for cifra, texto in cifras
    )
    return f'<section class="esencial">{celdas}</section>'


def _con_sus_palabras(datos: DatosCronaca) -> str:
    citas = [d for d in datos.documentos if d["extracto"]][:4]
    if not citas:
        return ""
    bloques = "".join(
        f"<figure><blockquote>«{_e(d['extracto'])}»</blockquote>"
        f"<figcaption>{_enlace(d['url'], d['titulo'])}</figcaption></figure>"
        for d in citas
    )
    return (
        "<section>"
        + _cabecera("Con sus propias palabras", "Así se presenta en su sitio")
        + '<p class="nota">Así se describe en su sitio. Cada cita lleva su fuente.</p>'
        f'<div class="citas">{bloques}</div></section>'
    )


def _le_scoperte(datos: DatosCronaca) -> str:
    hallazgos = datos.scoperte.get("hallazgos", [])
    vacios = datos.scoperte.get("vacios", [])
    if not hallazgos and not vacios:
        return ""
    titulos = {d["url"]: d["titulo"] for d in datos.documentos}
    partes = [
        "<section>" + _cabecera("Le Scoperte · lo que dice el sitio", _titular_scoperte(datos)),
        '<p class="nota">Primero la idea; debajo, la frase exacta del sitio que la sostiene.</p>',
    ]

    def lista(grupo: list[dict[str, str]]) -> str:
        items = "".join(
            f'<li><p>{_e(h["hallazgo"])}</p><p class="cita">«{_e(_sin_marcas(h["cita"]))}» · '
            f"{_enlace(h['url_cita'], titulos.get(h['url_cita'], 'fuente'))}</p></li>"
            for h in grupo
        )
        return f'<ul class="hallazgos">{items}</ul>'

    por_id = {h["id"]: h for h in hallazgos if "id" in h}
    usados: set[str] = set()
    for insight in datos.scoperte.get("insights", []):
        grupo = [por_id[i] for i in insight["hallazgos"] if i in por_id]
        usados.update(insight["hallazgos"])
        partes.append(
            f'<div class="insight"><h3>{_e(insight["titulo"])}</h3>'
            + (f"<p>{_e(insight['por_que_importa'])}</p>" if insight["por_que_importa"] else "")
            + lista(grupo)
            + "</div>"
        )
    temas: dict[str, list[dict[str, str]]] = {}
    for hallazgo in hallazgos:
        if hallazgo.get("id") not in usados:
            temas.setdefault(hallazgo["tema"], []).append(hallazgo)
    if usados and temas:
        partes.append('<p class="etiqueta">Otros hallazgos</p>')
    for tema, grupo in temas.items():
        partes.append(f"<h3>{_e(tema)}</h3>" + lista(grupo))
    if vacios:
        total = len(datos.documentos)
        leidas = "la página leída" if total == 1 else f"las {total} páginas leídas"
        items = "".join(
            f"<li><b>{_e(v['tema'])}</b><span>{_e(v['por_que_importa'])}</span></li>"
            for v in vacios
        )
        partes.append(f'<h3>Lo que no aparece en {leidas}</h3><ul class="vacios">{items}</ul>')
    descartados = len(datos.scoperte.get("descartados", []))
    if descartados:
        partes.append(
            f'<p class="nota">{_n(descartados, "hallazgo se descartó", "hallazgos se descartaron")}'
            " porque su cita no aparece tal cual en el sitio.</p>"
        )
    partes.append("</section>")
    return "".join(partes)


def _lo_specchio(datos: DatosCronaca) -> str:
    sitio = datos.specchio
    if not sitio:
        return ""
    total = sitio["paginas"]
    partes = [
        "<section>" + _cabecera("Lo Specchio · al compartirlo", _titular_specchio(sitio)),
        '<p class="nota">Cómo se ve la marca cuando alguien comparte su sitio, y a qué redes '
        "lleva. Todo sale de las páginas leídas: no se visitó ningún perfil.</p>",
    ]
    vista = sitio.get("previsualizacion")
    if vista:
        imagen = (
            "con imagen de vista previa" if vista.get("image") else "sin imagen de vista previa"
        )
        partes.append(
            f'<div class="tarjeta"><span>{_e(datos.dominio)}</span>'
            f"<b>{_e(_sin_datos(vista.get('title')) or 'Sin título para compartir')}</b>"
            f"<p>{_e(_sin_datos(vista.get('description')) or 'Sin descripción.')}</p>"
            f"<span>{imagen}</span></div>"
        )
    perfiles = sitio.get("perfiles", {})
    if perfiles:
        items = "".join(
            f"<li>{_enlace(url, _sin_esquema(url))}"
            f"<span>enlazado desde {veces} de {total} páginas</span></li>"
            for url, veces in perfiles.items()
        )
        partes.append(f'<h3>Adónde lleva el sitio</h3><ul class="perfiles">{items}</ul>')
    else:
        partes.append("<p>El sitio no enlaza ningún perfil social.</p>")
    senales = [
        f"{sitio['paginas_con_og_completo']} de {total} páginas tienen la vista previa completa",
        _cuantas(sitio["paginas_con_whatsapp"], "ofrece", "ofrecen") + " escribir por mensajería",
        _cuantas(sitio["paginas_con_botones_compartir"], "tiene", "tienen")
        + " botones para compartir",
    ]
    partes.append(f"<p>{_e(_enumerar(senales))}.</p>")
    problemas = list(sitio.get("problemas_frecuentes", {}).items())[:5]
    if problemas:
        titulos = {_clave_url(d["url"]): d["titulo"] for d in datos.documentos}
        donde: dict[str, list[str]] = {}
        for pagina in sitio.get("detalle", []):
            titulo = titulos.get(_clave_url(pagina.get("url", "")))
            for problema in pagina.get("problemas", []):
                if titulo:
                    donde.setdefault(problema, []).append(titulo)
        items = "".join(
            f"<li>{_e(PROBLEMAS_LEGIBLES.get(problema, problema))}"
            f"<span>{_e(_donde(veces, donde.get(problema, [])))}</span></li>"
            for problema, veces in problemas
        )
        partes.append(f'<h3>Lo que conviene corregir</h3><ul class="perfiles">{items}</ul>')
    partes.append("</section>")
    return "".join(partes)


def _los_circulos(datos: DatosCronaca, con_resumen: bool = False) -> str:
    e = datos.estados
    por_tipo = datos.lete.get("por_tipo", {})
    detalle_lete = _enumerar(
        _n(int(por_tipo.get(clave, 0)), singular, plural)
        for clave, singular, plural in (
            ("correo", "correo", "correos"),
            ("telefono", "teléfono", "teléfonos"),
            ("identificacion", "identificación", "identificaciones"),
        )
        if por_tipo.get(clave)
    )
    filas = [
        (
            "Permiso",
            "La Porta",
            f"Consultó robots.txt antes de cada página. Leyó {e.get('ok', 0)}"
            + (f" y cerró {e.get('robots_blocked', 0)}" if e.get("robots_blocked") else "")
            + ".",
        ),
        (
            "Ritmo",
            "Il Passo",
            f"Una página a la vez, con {_decimal(datos.paso)} segundos entre una y otra.",
        ),
        (
            "Bloqueos",
            "Caronte",
            "Nadie negó el paso."
            if not e.get("stopped")
            else f"El sitio negó el paso y el viaje se detuvo a tiempo; "
            f"{_n(e.get('not_attempted', 0), 'página quedó', 'páginas quedaron')} sin visitar.",
        ),
        (
            "Datos personales",
            "Purgatorio y el Lete",
            "No hubo datos personales que borrar."
            if not datos.lete.get("total")
            else f"Se borraron {detalle_lete} antes de guardar el texto.",
        ),
        (
            "Documentos",
            "Paradiso",
            f"{_n(len(_citables(datos)), 'documento', 'documentos')} con texto citable, cada uno "
            "con su fuente y la fecha en que se leyó.",
        ),
        (
            "Páginas con JavaScript",
            "Limbo",
            "Ninguna necesitó un navegador."
            if not datos.limbo
            else f"{_n(datos.limbo, 'página espera', 'páginas esperan')} revisión humana.",
        ),
    ]
    items = "".join(
        f"<li><b>{_e(llano)}<i>{_e(nombre)}</i></b><span>{_e(texto)}</span></li>"
        for llano, nombre, texto in filas
    )
    return (
        "<section>"
        + _cabecera("Cómo se hizo", "Los círculos del viaje, del permiso a la cita")
        + (_en_una_frase(datos).replace('class="lede"', 'class="metodo"') if con_resumen else "")
        + f'<ol class="circulos">{items}</ol></section>'
    )


def _le_muse(datos: DatosCronaca) -> str:
    if not datos.muse and datos.muse_consulta:
        consultas = len(datos.muse_consulta.get("consultas", []))
        fecha = _fecha_larga(str(datos.muse_consulta.get("fecha", ""))[:10])
        biblioteca = str(
            datos.muse_consulta.get("biblioteca") or "la biblioteca pública de anuncios"
        )
        return (
            "<section>"
            + _cabecera("Le Muse · anuncios", "No encontramos anuncios suyos")
            + f"<p>Buscamos sus anuncios con {_n(consultas, 'consulta', 'consultas')} en "
            f"{_e(biblioteca)}"
            + (f" el {_e(fecha)}" if fecha else "")
            + " y no apareció ninguno suyo entre los resultados revisados.</p>"
            '<p class="nota">La búsqueda encuentra los anuncios que nombran la marca en su texto; '
            "uno que no la nombre puede escaparse. Conviene confirmarlo con su equipo.</p>"
            "</section>"
        )
    if not datos.muse:
        return ""
    bloques = []
    for m in datos.muse:
        formato = max(m["por_formato"], key=m["por_formato"].get) if m["por_formato"] else "-"
        cta = max(m["por_cta"], key=m["por_cta"].get) if m["por_cta"] else "-"
        bloques.append(
            f'<div class="cifra"><strong>{m["unicos"]}</strong><span>creativos únicos de '
            f"{_n(m['total'], 'anuncio', 'anuncios')} de {_e(m['marca'])}</span></div>"
            f"<p>Su formato preferido es <b>{_e(formato)}</b> y su llamado más repetido es "
            f"<b>«{_e(cta)}»</b>. {_n(m['repetidos'], 'anuncio repite', 'anuncios repiten')} "
            "un creativo: ahí está lo que la marca ya sabe que funciona.</p>"
        )
    return (
        "<section>"
        + _cabecera("Le Muse · anuncios", _titular_muse(datos))
        + "".join(bloques)
        + '<p class="nota">Inspírate, no copies: '
        "se aprende el mecanismo, no la pieza.</p></section>"
    )


def _l_eco(datos: DatosCronaca) -> str:
    partes = [
        "<section>" + _cabecera("L'Eco · lo que responden los asistentes", _titular_eco(datos))
    ]
    if datos.eco:
        partes.append(_l_ascolto(datos, datos.eco))
    elif datos.eco_preguntas:
        total = sum(datos.eco_conteo.values())
        partes.append(
            f"<p>Preparamos {_n(total, 'pregunta', 'preguntas')} que la gente hace a los "
            "asistentes de IA antes de decidir, sin nombrar la marca. Estas son las primeras:</p>"
        )
        partes.append(
            '<ul class="preguntas">'
            + "".join(f"<li>«{_e(p)}»</li>" for p in datos.eco_preguntas[:3])
            + "</ul>"
        )
        partes.append(
            '<p class="nota">El siguiente paso es llevarlas a los asistentes y anotar qué '
            "responden. Nautilio no inventa esas respuestas.</p>"
        )
    else:
        partes.append(
            "<p>Aún no hay preguntas preparadas. <code>make eco</code> arma el retrato de la "
            "marca y la matriz de preguntas.</p>"
        )
    if datos.ritratto_pendientes:
        pendientes = _n(datos.ritratto_pendientes, "dato sigue", "datos siguen")
        partes.append(
            f'<p class="nota">Del retrato de la marca, {pendientes} por confirmar con su '
            "equipo.</p>"
        )
    partes.append("</section>")
    return "".join(partes)


def _l_ascolto(datos: DatosCronaca, eco: Mapping[str, Any]) -> str:
    marca = _e(datos.eco_marca)
    titulos = {d["url"]: d["titulo"] for d in datos.documentos}
    partes = [
        f'<div class="cifra">{_waffle(eco["visibles"], eco["con_respuesta"])}'
        f"<strong>{eco['visibles']} de {eco['con_respuesta']}</strong>"
        f"<span>preguntas simuladas de clientes en las que aparece {marca}</span></div>"
    ]
    if len(datos.eco_por_motor) > 1:
        items = "".join(
            f"<li><b>{_e(motor)}</b><span>aparece en {m['visibles']} de "
            f"{_n(m['con_respuesta'], 'pregunta', 'preguntas')}</span></li>"
            for motor, m in datos.eco_por_motor.items()
        )
        partes.append(f'<ul class="motores">{items}</ul>')
    if eco["visibles"]:
        apariciones = eco.get("apariciones", [])
        if len(apariciones) == 1:
            puesto = f"La única vez que aparece, sale en el puesto {apariciones[0]['posicion']}"
        else:
            puesto = f"Cuando aparece, sale en el puesto {_decimal(eco['posicion_promedio'])}"
        partes.append(
            f"<p>{_e(puesto)} y se lleva el {_decimal(eco['share_of_voice'])}&nbsp;% de las "
            f"menciones entre las {len(eco['menciones'])} marcas contadas. "
            + _e(
                f"{_n(eco['citas_propias'], 'respuesta usa', 'respuestas usan')} su sitio como "
                "fuente."
            )
            + "</p>"
        )
        if apariciones:
            items = "".join(
                f"<li>«{_e(a['prompt'])}»"
                f"<span>{_e(a['motor'])}, puesto {a['posicion']}.</span></li>"
                for a in apariciones
            )
            partes.append(f'<h3>Dónde sí aparece</h3><ul class="brechas">{items}</ul>')
    rivales = sorted(
        (
            (nombre, total)
            for nombre, total in eco["menciones"].items()
            if nombre != datos.eco_marca and total
        ),
        key=lambda item: -item[1],
    )
    if rivales:
        propias = eco["menciones"].get(datos.eco_marca, 0)
        corte = rivales[MAXIMO_RIVALES - 1][1] if len(rivales) >= MAXIMO_RIVALES else 0
        visibles = [r for r in rivales if r[1] >= max(corte, propias)] or rivales[:MAXIMO_RIVALES]
        filas = [(datos.eco_marca, propias, True), *[(n, t, False) for n, t in visibles]]
        filas.sort(key=lambda fila: -fila[1])
        mayor = max(total for _, total, _ in filas) or 1
        barras = "".join(_barra(nombre, total, mayor, propia) for nombre, total, propia in filas)
        resto = len(rivales) - len(visibles)
        partes.append(
            "<h3>Quién aparece en su lugar</h3>"
            '<p class="nota">Menciones en las respuestas a las preguntas simuladas de clientes.</p>'
            f'<ul class="barras">{barras}</ul>'
            + (f'<p class="nota">Y {_n(resto, "marca más", "marcas más")}.</p>' if resto else "")
        )
    orden = {"decision": 0, "comparacion": 1, "descubrimiento": 2}
    todas = sorted(eco["brechas"], key=lambda b: orden.get(b.get("etapa", ""), 3))
    brechas = todas if len(todas) <= MAXIMO_BRECHAS else todas[:6]
    if brechas:
        filas_brecha = "".join(
            f"<li>«{_e(b['prompt'])}»<span>{'Aparece' if len(b['rivales']) == 1 else 'Aparecen'} "
            f"{_e(_lista_corta(b['rivales'], 4))}. "
            + (
                "La página que más palabras comparte con la pregunta: "
                f"{_enlace(b['paradiso']['url'], titulos.get(b['paradiso']['url'], 'ver'))}."
                if b["paradiso"] and b["paradiso"].get("puntaje", 0) >= UMBRAL_CERCANA
                else "Ninguna página leída comparte bastantes palabras con la pregunta."
            )
            + "</span></li>"
            for b in brechas
        )
        resto = len(eco["brechas"]) - len(brechas)
        partes.append(
            f'<h3>Donde gana la competencia</h3><ul class="brechas">{filas_brecha}</ul>'
            + (
                f'<p class="nota">Y {_n(resto, "pregunta más", "preguntas más")}.</p>'
                if resto
                else ""
            )
        )
    if datos.eco_de_marca:
        por_pregunta: dict[str, list[dict[str, str]]] = {}
        for respuesta in datos.eco_de_marca:
            por_pregunta.setdefault(respuesta["prompt"], []).append(respuesta)
        bloques = []
        for pregunta, respuestas in list(por_pregunta.items())[:3]:
            citas = "".join(
                f"<figure><blockquote>«{_e(_legible(r['respuesta']))}»</blockquote>"
                f"<figcaption>{_e(r['motor'])}</figcaption></figure>"
                for r in respuestas
            )
            bloques.append(
                f'<p class="pregunta">«{_e(pregunta)}»</p><div class="citas">{citas}</div>'
            )
        partes.append(f"<h3>Lo que dicen cuando preguntan por {marca}</h3>" + "".join(bloques))
    fuentes = list(eco.get("dominios_citados", {}).items())[:5]
    if fuentes:
        lista = _enumerar(f"{dominio} ({veces})" for dominio, veces in fuentes)
        partes.append(f'<p class="nota">Las fuentes que más citan: {_e(lista)}.</p>')
    return "".join(partes)


def _la_risposta(datos: DatosCronaca) -> str:
    if not datos.acciones:
        return ""
    titulos = {d["url"]: d["titulo"] for d in datos.documentos}
    brechas = {b["prompt_id"] for b in (datos.eco or {}).get("brechas", [])}
    items = []
    for accion in datos.acciones:
        partes = [f"<li><b>{_e(accion['titulo'])}</b>"]
        etiquetas = []
        if accion.get("cuando"):
            clase = "tag hoy" if accion["cuando"] == "hoy" else "tag"
            etiquetas.append(f'<span class="{clase}">{_e(accion["cuando"])}</span>')
        if accion.get("esfuerzo"):
            etiquetas.append(f'<span class="tag">esfuerzo {_e(accion["esfuerzo"])}</span>')
        if etiquetas:
            partes.append(f'<p class="tags">{"".join(etiquetas)}</p>')
        if accion.get("resultado"):
            partes.append(f'<p class="apoyo">Para lograr: {_e(accion["resultado"])}</p>')
        temas = [r for r in accion["responde_a"] if not re.fullmatch(r"[a-z]\d+", r)]
        preguntas = sum(1 for r in accion["responde_a"] if r in brechas)
        if preguntas:
            temas.append(
                _n(
                    preguntas,
                    "pregunta donde gana la competencia",
                    "preguntas donde gana la competencia",
                )
            )
        if temas:
            partes.append(f'<p class="apoyo">Responde a: {_e(_enumerar(temas))}.</p>')
        if accion["que_debe_decir"]:
            puntos = "".join(f"<li>{_e(punto)}</li>" for punto in accion["que_debe_decir"])
            partes.append(f'<ul class="puntos">{puntos}</ul>')
        if accion["evidencia"]:
            enlaces = ", ".join(_enlace(url, titulos.get(url, url)) for url in accion["evidencia"])
            partes.append(f'<p class="apoyo">Ya está en el sitio: {enlaces}.</p>')
        if accion["falta_confirmar"]:
            datos_faltantes = "".join(
                f"<li>{_e(dato.rstrip('.'))}</li>" for dato in accion["falta_confirmar"]
            )
            partes.append(
                '<p class="apoyo">Por confirmar con su equipo:</p>'
                f'<ul class="puntos confirmar">{datos_faltantes}</ul>'
            )
        partes.append("</li>")
        items.append("".join(partes))
    hoy = [accion["titulo"] for accion in datos.acciones if accion.get("cuando") == "hoy"]
    franja = (
        '<div class="hoy"><p class="etiqueta">Para hacer hoy</p><ul>'
        + "".join(f"<li>{_e(titulo)}</li>" for titulo in hoy)
        + "</ul></div>"
        if hoy
        else ""
    )
    return (
        "<section>"
        + _cabecera("La Risposta · qué hacer", _titular_risposta(datos))
        + franja
        + '<p class="nota">En orden de impacto. Cada acción responde a un hallazgo, a un vacío o '
        "a una pregunta donde gana la competencia.</p>"
        f'<ol class="acciones">{"".join(items)}</ol></section>'
    )


def _titular_eco(datos: DatosCronaca) -> str:
    eco = datos.eco
    if not eco or not eco.get("con_respuesta"):
        return "Lo que la gente pregunta antes de decidir"
    marca = datos.eco_marca
    propias = eco["menciones"].get(marca, 0)
    antes = sum(
        1 for nombre, total in eco["menciones"].items() if nombre != marca and total > propias
    )
    total = eco["con_respuesta"]
    if not eco["visibles"]:
        return (
            f"Los asistentes no nombran a {marca} en ninguna de las {total} preguntas "
            "simuladas de clientes"
        )
    if antes:
        return (
            f"{marca} aparece en {eco['visibles']} de {total} preguntas; "
            f"{_n(antes, 'marca aparece', 'marcas aparecen')} más veces"
        )
    return f"{marca} aparece en {eco['visibles']} de {total} preguntas simuladas de clientes"


def _titular_scoperte(datos: DatosCronaca) -> str:
    insights = datos.scoperte.get("insights", [])
    hallazgos = len(datos.scoperte.get("hallazgos", []))
    vacios = len(datos.scoperte.get("vacios", []))
    if insights:
        return (
            f"{_n(len(insights), 'idea sale', 'ideas salen')} del sitio, sostenidas por "
            f"{_n(hallazgos, 'cita', 'citas')}"
        )
    if vacios:
        return (
            f"{_n(hallazgos, 'hallazgo', 'hallazgos')} con su cita y "
            f"{_n(vacios, 'cosa', 'cosas')} que el sitio no dice"
        )
    return f"{_n(hallazgos, 'hallazgo', 'hallazgos')} con su cita"


def _titular_specchio(sitio: Mapping[str, Any]) -> str:
    perfiles = len(sitio.get("perfiles", {}))
    destino = _n(perfiles, "perfil social", "perfiles sociales") if perfiles else "ningún perfil"
    return (
        f"{sitio['paginas_con_og_completo']} de {sitio['paginas']} páginas se ven completas al "
        f"compartirlas, y el sitio lleva a {destino}"
    )


def _titular_muse(datos: DatosCronaca) -> str:
    unicos = sum(m["unicos"] for m in datos.muse)
    total = sum(m["total"] for m in datos.muse)
    return (
        f"{_n(unicos, 'creativo único', 'creativos únicos')} en {_n(total, 'anuncio', 'anuncios')}"
    )


def _titular_risposta(datos: DatosCronaca) -> str:
    hoy = sum(1 for accion in datos.acciones if accion.get("cuando") == "hoy")
    titular = f"{_n(len(datos.acciones), 'acción', 'acciones')} en orden"
    if hoy:
        titular += f"; {_n(hoy, 'se puede hacer hoy', 'se pueden hacer hoy')}"
    return titular


def _waffle(visibles: int, total: int, columnas: int = 12) -> str:
    """Una casilla por pregunta: llenas las que nombran la marca."""
    if total <= 0:
        return ""
    lado, paso = 12, 16
    filas = -(-total // columnas)
    casillas = "".join(
        f'<rect x="{(i % columnas) * paso}" y="{(i // columnas) * paso}" width="{lado}" '
        f'height="{lado}" class="{"llena" if i < visibles else "vacia"}"/>'
        for i in range(total)
    )
    return (
        f'<svg class="waffle" viewBox="0 0 {columnas * paso} {filas * paso}" '
        f'width="{columnas * paso}" height="{filas * paso}" role="img" '
        f'aria-label="{visibles} de {total}">{casillas}</svg>'
    )


def _para_completar(datos: DatosCronaca) -> str:
    pasos = []
    vacias = [d for d in datos.documentos if d["caracteres"] < PAGINA_CASI_VACIA]
    if vacias:
        nombres = ", ".join(d["titulo"] for d in vacias[:2])
        pasos.append(
            f"Revisar {_n(len(vacias), 'página casi vacía', 'páginas casi vacías')} ({nombres}): "
            "su texto puede estar en un PDF o en una imagen que este viaje no leyó."
        )
    if datos.limbo:
        pasos.append("Revisar a mano las páginas del Limbo.")
    if not datos.scoperte.get("hallazgos"):
        pasos.append("Redactar Le Scoperte: los hallazgos de las páginas, cada uno con su cita.")
    if not datos.muse and not datos.muse_consulta:
        pasos.append("Buscar los anuncios públicos de la marca para Le Muse.")
    if not datos.eco and datos.eco_preguntas:
        pasos.append("Llevar Le Domande a los asistentes y anotar lo que responden.")
    if not datos.acciones:
        pasos.append("Escribir La Risposta: qué hacer primero con lo encontrado.")
    if not pasos:
        return ""
    items = "".join(f"<li>{_e(paso)}</li>" for paso in pasos)
    return (
        "<section>"
        + _cabecera("Para completar el viaje", "Lo que este viaje no alcanzó a leer")
        + f'<ol class="sigue">{items}</ol></section>'
    )


def _colofon(datos: DatosCronaca) -> str:
    redacto = (
        " Los hallazgos y las acciones los redactó un asistente de IA, y cada cita se comprobó "
        "letra por letra contra el texto del sitio; vacíos y acciones son su lectura."
        if datos.scoperte.get("hallazgos") or datos.acciones
        else ""
    )
    lete = (
        "Los datos personales se borraron antes de escribir esta página."
        if datos.lete.get("total")
        else "El Lete no encontró datos personales que borrar."
    )
    return (
        "<footer><p>Hecha con Nautilio. Las cifras las contó el código sobre los archivos del "
        f"viaje.{redacto} {lete}</p>"
        f"<p>{_e(datos.dominio)} · {_e(_fecha_larga(datos.fecha))}</p></footer>"
    )


# --- utilidades -----------------------------------------------------------------------


def _espiral() -> str:
    crecimiento = math.log(3) / (2 * math.pi)
    fin = 3 * math.pi
    a = 34 / math.exp(crecimiento * fin)

    def punto(t: float, factor: float = 1.0) -> tuple[float, float]:
        r = a * math.exp(crecimiento * t) * factor
        return 40 + r * math.cos(t), 40 - r * math.sin(t)

    pasos = [-6 + i * (fin + 6) / 240 for i in range(241)]
    contorno = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in map(punto, pasos))
    septos = "".join(
        f'<line x1="{punto(t)[0]:.1f}" y1="{punto(t)[1]:.1f}" '
        f'x2="{punto(t - 2 * math.pi)[0]:.1f}" y2="{punto(t - 2 * math.pi)[1]:.1f}"/>'
        for t in (fin - 1.9 - k * 0.56 for k in range(12))
    )
    return (
        '<svg class="espiral" viewBox="0 0 80 80" aria-hidden="true">'
        f'<path d="{contorno}"/><g>{septos}</g></svg>'
    )


def _preguntas_de_decision(ruta: Path) -> tuple[list[str], dict[str, int]]:
    if not ruta.is_file():
        return [], {}
    with ruta.open(encoding="utf-8", newline="") as handle:
        filas = [fila for fila in csv.DictReader(handle) if (fila.get("prompt") or "").strip()]
    conteo: dict[str, int] = {}
    for fila in filas:
        conteo[fila.get("set", "")] = conteo.get(fila.get("set", ""), 0) + 1
    orden = {"decision": 0, "comparacion": 1, "descubrimiento": 2}
    conversacionales = [f for f in filas if f.get("set") == "conversacional"]
    conversacionales.sort(key=lambda f: orden.get(f.get("etapa", ""), 3))
    return [f["prompt"].strip() for f in conversacionales], conteo


def _ritratto_pendientes(ruta: Path) -> int:
    with ruta.open(encoding="utf-8", newline="") as handle:
        filas = list(csv.DictReader(handle))
    return sum(
        1
        for fila in filas
        if not (fila.get("respuesta") or "").strip()
        or "por confirmar" in (fila.get("respuesta") or "").lower()
    )


def _leer_json(ruta: Path) -> dict[str, Any] | None:
    if not ruta.is_file():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def _leer_jsonl(ruta: Path) -> list[dict[str, Any]]:
    if not ruta.is_file():
        return []
    return [
        json.loads(linea)
        for linea in ruta.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]


def _citables(datos: DatosCronaca) -> list[dict[str, Any]]:
    return [d for d in datos.documentos if d["caracteres"] >= PAGINA_CASI_VACIA]


def _fecha_larga(fecha: str) -> str:
    """``2026-10-22`` se lee «22 de octubre de 2026»; otra forma se deja tal cual."""
    partes = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", fecha or "")
    if not partes or not 1 <= int(partes[2]) <= 12:
        return fecha
    return f"{int(partes[3])} de {MESES[int(partes[2]) - 1]} de {partes[1]}"


def _lista_corta(nombres: list[str], maximo: int) -> str:
    if len(nombres) <= maximo:
        return _enumerar(nombres)
    return ", ".join(nombres[:maximo]) + f" y {len(nombres) - maximo} más"


def _donde(veces: int, titulos: list[str]) -> str:
    unicos = list(dict.fromkeys(titulos))
    if unicos and len(unicos) == veces and veces <= 3:
        return _enumerar(unicos)
    return _n(veces, "página", "páginas")


def _clave_url(url: str) -> str:
    partes = urlsplit(url or "")
    return f"{partes.netloc.removeprefix('www.')}{partes.path.rstrip('/')}"


def _barra(nombre: str, total: int, mayor: int, propia: bool) -> str:
    clase = ' class="propia"' if propia else ""
    ancho = round(total / mayor * 100)
    return f'<li{clase}><span>{_e(nombre)}</span><i style="width:{ancho}%"></i><b>{total}</b></li>'


def _cuantas(cantidad: int, singular: str, plural: str) -> str:
    if not cantidad:
        return f"ninguna {singular}"
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _sin_esquema(url: str) -> str:
    partes = urlsplit(url)
    return f"{partes.netloc.removeprefix('www.')}{partes.path.rstrip('/')}"


def _sin_datos(texto: object) -> str:
    return mask_personal_data(str(texto or ""), keep_institutional_emails=False)


def _legible(respuesta: str) -> str:
    """Respuesta de un motor lista para citar: sin markdown, sin datos personales, corta."""
    texto = re.sub(r"\[([^\]]*)\]\([^)]*\)?", r"\1", respuesta)
    texto = re.sub(r"https?://\S+", "", texto)
    texto = re.sub(r"^\s*\|?[-:| ]+\|?\s*$", " ", texto, flags=re.M)
    texto = re.sub(r"\*\*|__", "", texto)
    texto = re.sub(r"^#+\s*|[|\[\]]", " ", texto, flags=re.M)
    texto = re.sub(r"\s+([,.;:])", r"\1", texto)
    texto = mask_personal_data(texto, keep_institutional_emails=False, keep_landlines=False)
    return _recortar(texto, RESPUESTA_MAXIMA)


def _sin_marcas(texto: str) -> str:
    plano = re.sub(r"\*\*|__", "", texto)
    plano = re.sub(r":(?=[^\W\d_])", ": ", plano)  # «Kínder 4:**Niños» -> «Kínder 4: Niños»
    return re.sub(r"\s+", " ", plano).strip()


def _recortar(texto: str, maximo: int) -> str:
    plano = re.sub(r"\s+", " ", texto).strip()
    if len(plano) <= maximo:
        return plano
    return plano[:maximo].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _enlace(url: str, texto: str) -> str:
    if not re.match(r"https?://", url or ""):
        return _e(texto)
    return f'<a href="{_e(url)}">{_e(texto)}</a>'


def _enumerar(partes: Iterable[str]) -> str:
    lista = list(partes)
    if len(lista) < 2:
        return "".join(lista)
    return ", ".join(lista[:-1]) + " y " + lista[-1]


def _decimal(valor: float | None) -> str:
    if valor is None:
        return "-"
    return f"{valor:g}".replace(".", ",")


def _n(cantidad: int, singular: str, plural: str) -> str:
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _e(texto: object) -> str:
    return html.escape(str(texto), quote=True)


_CSS = """
:root{--papel:#EFE7D6;--hoja:#F7F1E5;--tinta:#15110D;--gris:#5E554A;--suave:#8A7F70;
--acento:#9B3A1E;
--serif:'Cormorant Garamond',Garamond,'Palatino Linotype',Georgia,'Times New Roman',serif}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);font-family:var(--serif);
font-size:19px;line-height:1.55}
.hoja{max-width:860px;margin:32px auto;padding:48px 56px;background:var(--hoja);
border:1.2px solid var(--tinta);outline:1px solid var(--tinta);outline-offset:-10px}
.portada{display:flex;gap:28px;align-items:center;border-bottom:1px solid var(--tinta);
padding-bottom:24px;margin-bottom:28px}
.espiral{width:96px;height:96px;flex:none}
.espiral path{fill:none;stroke:var(--tinta);stroke-width:1.6}
.espiral line{stroke:var(--tinta);stroke-width:.8;opacity:.7}
.epigrafe{margin:0;font-style:italic;letter-spacing:.18em;color:var(--gris);font-size:15px}
h1{margin:.1em 0 .1em;font-size:46px;letter-spacing:.06em;line-height:1.05}
.sub{margin:0;color:var(--gris)}
.sub span{font-style:italic}
.lede p{font-size:24px;line-height:1.45;margin:0 0 8px}
h2{font-size:27px;line-height:1.2;margin:44px 0 14px;font-weight:700;
border-top:1px solid var(--tinta);padding-top:16px}
h2 small{display:block;font-size:13px;letter-spacing:.28em;text-transform:uppercase;
color:var(--gris);font-weight:400;margin-bottom:8px}
.etiqueta{font-size:13px;letter-spacing:.28em;text-transform:uppercase;color:var(--gris);
margin:18px 0 6px}
.idea{margin:26px 0 8px}
.idea .grande{font-size:31px;line-height:1.3;margin:0 0 10px;font-weight:700;
border-left:4px solid var(--acento);padding-left:16px}
.historia li{margin:6px 0;font-size:20px}
.metodo p{color:var(--gris);font-size:17px}
.insight{margin:18px 0 22px}
.insight h3{font-size:21px;margin:0 0 4px}
.insight>p{margin:0 0 6px}
.waffle{flex:none;margin-right:6px}
.waffle .llena{fill:var(--acento)}
.waffle .vacia{fill:none;stroke:var(--suave);stroke-width:1}
.tags{margin:4px 0}
.tag{display:inline-block;font-size:13px;letter-spacing:.08em;text-transform:uppercase;
border:1px solid var(--suave);padding:1px 7px;margin-right:6px;color:var(--gris)}
.tag.hoy{border-color:var(--acento);color:var(--acento)}
.hoy{border:1px solid var(--acento);padding:10px 16px;margin:10px 0 16px}
.hoy .etiqueta{margin-top:0;color:var(--acento)}
.cta{border-top:2px solid var(--acento)}
h3{font-size:18px;margin:20px 0 8px}
.nota{color:var(--gris);font-style:italic;font-size:16px}
.citas{display:grid;gap:18px}
figure{margin:0;padding-left:18px;border-left:3px double var(--tinta)}
blockquote{margin:0;font-size:19px}
figcaption{font-size:14px;color:var(--gris);margin-top:4px;letter-spacing:.04em}
a{color:var(--tinta)}
.circulos{list-style:none;padding:0;margin:0}
.circulos li{display:grid;grid-template-columns:150px 1fr;gap:16px;padding:9px 0;
border-bottom:1px dotted var(--suave)}
.circulos b{letter-spacing:.06em}
.circulos b i{display:block;font-weight:400;letter-spacing:.04em;color:var(--gris);
font-size:15px}
.cifra{display:flex;align-items:baseline;gap:14px;margin:6px 0 4px}
.cifra strong{font-size:44px;line-height:1;white-space:nowrap}
.cifra span{color:var(--gris)}
.preguntas li,.brechas li{margin:6px 0}
.pregunta{margin:14px 0 6px;font-style:italic}
.brechas span{display:block;color:var(--gris);font-size:16px}
.sigue li{margin:6px 0}
.esencial{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:0;
margin:22px 0 4px;border-top:1px solid var(--tinta);border-bottom:1px solid var(--tinta)}
.esencial div{padding:12px 14px;border-left:1px dotted var(--suave)}
.esencial div:first-child{border-left:none}
.esencial strong{display:block;font-size:38px;line-height:1.05}
.esencial span{color:var(--gris);font-size:15px}
.hallazgos,.vacios,.perfiles,.motores{list-style:none;padding:0;margin:0}
.hallazgos li{padding:8px 0;border-bottom:1px dotted var(--suave)}
.hallazgos p{margin:0}
.hallazgos .cita{color:var(--gris);font-size:15px;font-style:italic;margin-top:3px}
.vacios li,.perfiles li,.motores li{display:grid;grid-template-columns:minmax(150px,34%) 1fr;
gap:14px;padding:7px 0;border-bottom:1px dotted var(--suave)}
.vacios span,.perfiles span,.motores span{color:var(--gris)}
.tarjeta{border:1px solid var(--tinta);padding:14px 18px;margin:8px 0 14px;max-width:560px;
background:var(--papel)}
.tarjeta span{display:block;font-size:13px;letter-spacing:.12em;text-transform:uppercase;
color:var(--gris)}
.tarjeta b{display:block;font-size:21px;margin:4px 0}
.tarjeta p{margin:0 0 6px}
.barras{list-style:none;padding:0;margin:6px 0}
.barras li{display:grid;grid-template-columns:minmax(150px,38%) 1fr 34px;align-items:center;
gap:10px;padding:3px 0}
.barras i{display:block;height:9px;background:var(--tinta);min-width:2px}
.barras b{text-align:right}
.barras .propia span{font-weight:700}
.barras .propia i{background:var(--acento)}
.barras .propia span,.barras .propia b{color:var(--acento)}
.acciones li{margin:12px 0}
.acciones .puntos{margin:6px 0;padding-left:20px}
.acciones .puntos li{margin:2px 0}
.apoyo{margin:4px 0;color:var(--gris);font-size:16px}
footer{margin-top:36px;border-top:1px solid var(--tinta);padding-top:12px;color:var(--gris);
font-size:14px;font-style:italic}
code{font-size:15px}
@media (max-width:640px){.hoja{margin:0;padding:28px 18px}.portada{flex-direction:column;
align-items:flex-start}.circulos li,.vacios li,.perfiles li,.motores li{
grid-template-columns:1fr;gap:2px}.barras li{grid-template-columns:1fr 34px}
.barras i{grid-column:1/-1;grid-row:2}h1{font-size:34px}}
@media print{body{background:#fff}.hoja{margin:0;border:none;outline:none;max-width:none}}
"""
