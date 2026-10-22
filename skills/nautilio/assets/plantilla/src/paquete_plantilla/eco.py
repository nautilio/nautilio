"""L'Eco: lo que los motores de respuesta repiten de la marca.

Cuatro pasos:
- Il Ritratto: el brief de la marca (contexto, foco y narrativa) en ``data/eco/ritratto.csv``.
- Le Domande: la matriz de preguntas en ``data/eco/domande.csv``.
- L'Ascolto: las respuestas de los motores en ``data/raw/eco/<marca>.jsonl``, contadas aqui.
- La Risposta: para cada brecha, si el Paradiso ya tiene una pagina que responda.

Las respuestas las recoge una persona en cada motor, o un agente con una API autorizada.
Este modulo nunca automatiza el acceso a un motor. Ninguna cifra sale de un modelo de
lenguaje: todas se calculan sobre los archivos de entrada.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from paquete_plantilla.config import DATA_DIR, GOLD_DIR, RAW_DIR

ECO_DIR = DATA_DIR / "eco"
RITRATTO_PATH = ECO_DIR / "ritratto.csv"
DOMANDE_PATH = ECO_DIR / "domande.csv"
COMPETIDORES_PATH = ECO_DIR / "competidores.json"
ASCOLTO_DIR = RAW_DIR / "eco"

SETS = ("conversacional", "marca")
ETAPAS = ("decision", "comparacion", "descubrimiento")
MINIMO_CONVERSACIONAL = 20
MAXIMO_CONVERSACIONAL = 40
UMBRAL_COBERTURA = 0.12
COLUMNAS_DOMANDE = (
    "id",
    "set",
    "etapa",
    "producto",
    "persona",
    "situacion",
    "restricciones",
    "prompt",
    "insumo",
    "resultado_negocio",
)
COLUMNAS_RITRATTO = (
    "bloque",
    "componente",
    "respuesta",
    "quien_responde",
    "definicion",
    "preguntas_clave",
)

# (bloque, componente, quien responde, definicion, preguntas clave)
RITRATTO: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "1. Contexto del negocio",
        "Descripcion del negocio",
        "Direccion, mercadeo",
        "Que vende la empresa, a quien y con que modelo.",
        "Que venden y a quien? Que la diferencia en una frase?",
    ),
    (
        "1. Contexto del negocio",
        "Mercados e idiomas",
        "Direccion, mercadeo",
        "Paises, ciudades e idiomas donde la marca quiere aparecer en las respuestas.",
        "Donde operan? En que idiomas preguntan sus clientes? Que mercados vienen?",
    ),
    (
        "1. Contexto del negocio",
        "Canales actuales y papel de L'Eco",
        "Mercadeo, ventas",
        "Como llega hoy la demanda y que debe aportar aparecer en los motores.",
        "De donde vienen hoy los clientes? Que deberia resolver L'Eco?",
    ),
    (
        "1. Contexto del negocio",
        "Objetivos de negocio",
        "Direccion",
        "Las metas del ano que esta estrategia debe apoyar.",
        "Cuales son las dos o tres prioridades? Que producto o segmento debe crecer?",
    ),
    (
        "1. Contexto del negocio",
        "Lo que los motores ya saben de la marca",
        "Mercadeo",
        "Revision rapida en varios motores: conocen la marca y la describen bien?",
        "Que dicen si se les pregunta que es la marca y donde esta? Hay errores?",
    ),
    (
        "2. Foco",
        "Prioridad de productos, servicios o categorias",
        "Direccion, producto, comercial",
        "Que parte de la oferta se trabaja primero.",
        "Que deja mas ingreso o margen? Sobre que pregunta la gente antes de comprar?",
    ),
    (
        "2. Foco",
        "Personas",
        "Comercial, servicio al cliente",
        "A quienes queremos llegar, con sus palabras y preocupaciones.",
        "Quien compra y quien influye? Como describe su problema con sus palabras?",
    ),
    (
        "2. Foco",
        "Casos de uso",
        "Comercial, servicio al cliente",
        "Las situaciones que llevan a alguien a preguntarle a un motor.",
        "Que pasa justo antes de necesitarlos? Que preguntan en ventas o soporte?",
    ),
    (
        "2. Foco",
        "Competidores y alternativas",
        "Comercial",
        "Contra quien comparan a la marca, incluida la opcion de no hacer nada.",
        "Con quien perdemos ventas? Quien aparece hoy en las respuestas de la categoria?",
    ),
    (
        "2. Foco",
        "Transaccion",
        "Comercial, servicio al cliente",
        "Lo que el cliente necesita resolver para comprar una vez decidio.",
        "Que preguntan justo antes de cerrar? Que frena la compra al final?",
    ),
    (
        "2. Foco",
        "Etapa prioritaria",
        "Mercadeo, comercial",
        "Descubrimiento, comparacion o decision: donde importa mas aparecer.",
        "Donde se pierden hoy mas clientes potenciales?",
    ),
    (
        "3. Narrativa para los motores",
        "Atributos y diferenciadores",
        "Direccion, producto",
        "Lo que queremos que un motor asocie con la marca cuando la recomiende.",
        "Por que eligen la marca? Que dicen los clientes satisfechos?",
    ),
    (
        "3. Narrativa para los motores",
        "Pruebas y evidencia",
        "Mercadeo, comercial",
        "Datos, resenas o certificaciones publicas que respaldan cada atributo.",
        "Que prueba publica existe para cada atributo? Esta en el sitio?",
    ),
    (
        "3. Narrativa para los motores",
        "Como queremos ser descritos",
        "Direccion, mercadeo",
        "Una o dos frases con la descripcion ideal en una respuesta.",
        "Si un motor recomendara la marca en una frase, que deberia decir?",
    ),
    (
        "3. Narrativa para los motores",
        "Claims a evitar",
        "Legal, direccion",
        "Afirmaciones que la marca no puede o no quiere que se le asocien.",
        "Hay temas regulados? Con que segmento o precio no quieren asociarse?",
    ),
)

_PALABRAS_VACIAS = frozenset(
    {
        "para",
        "como",
        "cual",
        "cuales",
        "que",
        "con",
        "por",
        "una",
        "unos",
        "unas",
        "los",
        "las",
        "del",
        "mas",
        "mejor",
        "tiene",
        "tienen",
        "este",
        "esta",
        "sobre",
        "donde",
        "cuanto",
        "cuesta",
        "hay",
        "son",
    }
)


@dataclass(frozen=True, slots=True)
class Pregunta:
    """Una fila de Le Domande."""

    id: str
    set: str
    etapa: str
    producto: str
    persona: str
    situacion: str
    restricciones: str
    prompt: str
    insumo: str
    resultado_negocio: str


@dataclass(frozen=True, slots=True)
class Respuesta:
    """Lo que un motor respondio a una pregunta, tal como se recogio."""

    prompt_id: str
    motor: str
    fecha: str
    respuesta: str
    fuentes: tuple[str, ...]


# --- Il Ritratto ---------------------------------------------------------------------


def escribir_ritratto(path: Path = RITRATTO_PATH, force: bool = False) -> bool:
    """Escribe la plantilla del brief si no existe. Devuelve True si la escribio."""
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNAS_RITRATTO)
        for bloque, componente, quien, definicion, preguntas in RITRATTO:
            writer.writerow([bloque, componente, "", quien, definicion, preguntas])
    return True


def ritratto_pendiente(path: Path = RITRATTO_PATH) -> list[str]:
    """Componentes del brief que siguen sin respuesta."""
    if not path.exists():
        return [componente for _, componente, *_ in RITRATTO]
    with path.open(encoding="utf-8", newline="") as handle:
        filas = list(csv.DictReader(handle))
    return [fila["componente"] for fila in filas if not (fila.get("respuesta") or "").strip()]


# --- Le Domande ----------------------------------------------------------------------


def escribir_domande(path: Path = DOMANDE_PATH, force: bool = False) -> bool:
    """Escribe la matriz vacia de preguntas si no existe. Devuelve True si la escribio."""
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerow(COLUMNAS_DOMANDE)
    return True


def cargar_domande(path: Path = DOMANDE_PATH) -> list[Pregunta]:
    """Lee la matriz de preguntas."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            Pregunta(**{columna: (fila.get(columna) or "").strip() for columna in COLUMNAS_DOMANDE})
            for fila in csv.DictReader(handle)
            if any((valor or "").strip() for valor in fila.values())
        ]


def validar_domande(
    preguntas: Sequence[Pregunta],
    marca: str,
    minimo: int = MINIMO_CONVERSACIONAL,
    maximo: int = MAXIMO_CONVERSACIONAL,
) -> dict[str, Any]:
    """Revisa la matriz contra las reglas de Le Domande y devuelve conteos y problemas."""
    problemas: list[str] = []
    conversacionales = [p for p in preguntas if p.set == "conversacional"]
    for pregunta in preguntas:
        etiqueta = pregunta.id or "(sin id)"
        if pregunta.set not in SETS:
            problemas.append(f"{etiqueta}: set debe ser conversacional o marca")
        if pregunta.etapa not in ETAPAS:
            problemas.append(f"{etiqueta}: etapa debe ser decision, comparacion o descubrimiento")
        if not pregunta.resultado_negocio:
            problemas.append(f"{etiqueta}: sin resultado de negocio; es ruido y se descarta")
        if not pregunta.prompt:
            problemas.append(f"{etiqueta}: sin prompt")
        menciona = _menciona(pregunta.prompt, marca)
        if pregunta.set == "conversacional":
            if menciona:
                problemas.append(f"{etiqueta}: una pregunta conversacional no nombra la marca")
            if not (pregunta.situacion and pregunta.persona and pregunta.restricciones):
                problemas.append(f"{etiqueta}: falta situacion, persona o restricciones")
        if pregunta.set == "marca" and not menciona:
            problemas.append(f"{etiqueta}: una pregunta de marca debe nombrar la marca")
    if not minimo <= len(conversacionales) <= maximo:
        problemas.append(
            f"hay {len(conversacionales)} preguntas conversacionales; se esperan entre "
            f"{minimo} y {maximo}"
        )
    if conversacionales and not any(p.etapa == "decision" for p in conversacionales):
        problemas.append("falta la etapa de decision: las preguntas se arman desde la compra")
    return {
        "total": len(preguntas),
        "por_set": dict(Counter(p.set for p in preguntas)),
        "por_etapa": dict(Counter(p.etapa for p in preguntas)),
        "problemas": problemas,
    }


# --- L'Ascolto -----------------------------------------------------------------------


def cargar_respuestas(path: Path) -> list[Respuesta]:
    """Lee el JSONL de respuestas recogidas en los motores."""
    respuestas: list[Respuesta] = []
    with path.open(encoding="utf-8") as handle:
        for numero, linea in enumerate(handle, start=1):
            if not linea.strip():
                continue
            data = json.loads(linea)
            prompt_id = str(data.get("prompt_id", "")).strip()
            if not prompt_id:
                raise ValueError(f"linea {numero}: falta prompt_id")
            fuentes = data.get("fuentes") or []
            respuestas.append(
                Respuesta(
                    prompt_id=prompt_id,
                    motor=str(data.get("motor", "")).strip() or "(sin motor)",
                    fecha=str(data.get("fecha", "")).strip(),
                    respuesta=str(data.get("respuesta", "")),
                    fuentes=tuple(str(fuente) for fuente in fuentes),
                )
            )
    return respuestas


def escuchar(
    preguntas: Sequence[Pregunta],
    respuestas: Sequence[Respuesta],
    marca: str,
    dominio: str,
    competidores: Sequence[str],
    corpus: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Cuenta visibilidad, menciones, citas, posicion y brechas sin usar un modelo."""
    por_id = {p.id: p for p in preguntas}
    conversacionales = {p.id for p in preguntas if p.set == "conversacional"}
    nombres = [marca, *[c for c in competidores if c.strip()]]
    menciones: Counter[str] = Counter()
    dominios: Counter[str] = Counter()
    visibles: set[str] = set()
    con_respuesta: set[str] = set()
    posiciones: list[int] = []
    apariciones: list[dict[str, Any]] = []
    citas_propias = 0
    rivales_por_prompt: dict[str, set[str]] = {}
    propia_por_prompt: dict[str, bool] = {}

    for respuesta in respuestas:
        if respuesta.prompt_id not in conversacionales:
            continue
        con_respuesta.add(respuesta.prompt_id)
        nombrados = _nombrados_en_orden(respuesta.respuesta, nombres)
        menciones.update(nombrados)
        cita_propia = any(_es_del_dominio(fuente, dominio) for fuente in respuesta.fuentes)
        citas_propias += int(cita_propia)
        for fuente in respuesta.fuentes:
            dominios[_dominio(fuente)] += 1
        if marca in nombrados:
            visibles.add(respuesta.prompt_id)
            posiciones.append(nombrados.index(marca) + 1)
            apariciones.append(
                {
                    "prompt_id": respuesta.prompt_id,
                    "prompt": por_id[respuesta.prompt_id].prompt,
                    "motor": respuesta.motor,
                    "posicion": nombrados.index(marca) + 1,
                }
            )
        rivales = {nombre for nombre in nombrados if nombre != marca}
        rivales_por_prompt.setdefault(respuesta.prompt_id, set()).update(rivales)
        presente = marca in nombrados or cita_propia
        propia_por_prompt[respuesta.prompt_id] = (
            propia_por_prompt.get(respuesta.prompt_id, False) or presente
        )

    brechas = []
    for prompt_id in sorted(con_respuesta):
        rivales = rivales_por_prompt.get(prompt_id, set())
        if rivales and not propia_por_prompt.get(prompt_id, False):
            pregunta = por_id[prompt_id]
            brechas.append(
                {
                    "prompt_id": prompt_id,
                    "prompt": pregunta.prompt,
                    "etapa": pregunta.etapa,
                    "rivales": sorted(rivales),
                    "paradiso": _mejor_pagina(pregunta.prompt, corpus),
                }
            )

    total_menciones = sum(menciones.values())
    return {
        "preguntas_conversacionales": len(conversacionales),
        "con_respuesta": len(con_respuesta),
        "visibles": len(visibles),
        "visibilidad": _porcentaje(len(visibles), len(con_respuesta)),
        "menciones": {nombre: menciones.get(nombre, 0) for nombre in nombres},
        "share_of_voice": _porcentaje(menciones.get(marca, 0), total_menciones),
        "posicion_promedio": round(sum(posiciones) / len(posiciones), 2) if posiciones else None,
        "apariciones": apariciones,
        "citas_propias": citas_propias,
        "dominios_citados": dict(dominios.most_common(10)),
        "brechas": brechas,
        "cubiertas": sum(1 for brecha in brechas if brecha["paradiso"]),
    }


def escuchar_por_motor(
    preguntas: Sequence[Pregunta],
    respuestas: Sequence[Respuesta],
    marca: str,
    dominio: str,
    competidores: Sequence[str],
    corpus: Sequence[Mapping[str, Any]] = (),
) -> dict[str, dict[str, Any]]:
    """La misma escucha separada por motor: lo que dice cada uno por su cuenta."""
    motores = sorted({respuesta.motor for respuesta in respuestas})
    return {
        motor: escuchar(
            preguntas,
            [respuesta for respuesta in respuestas if respuesta.motor == motor],
            marca,
            dominio,
            competidores,
            corpus,
        )
        for motor in motores
    }


def cargar_competidores(path: Path = COMPETIDORES_PATH) -> list[str]:
    """Competidores que aparecieron en las respuestas, en ``data/eco/competidores.json``."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    nombres = data.get("competidores", []) if isinstance(data, dict) else data
    return [str(nombre).strip() for nombre in nombres if str(nombre).strip()]


def respuestas_de_marca(
    preguntas: Sequence[Pregunta], respuestas: Sequence[Respuesta], maximo: int = 220
) -> list[dict[str, str]]:
    """Lo que dicen los motores en el set de marca, para compararlo con Il Ritratto."""
    de_marca = {p.id: p for p in preguntas if p.set == "marca"}
    return [
        {
            "prompt": de_marca[r.prompt_id].prompt,
            "motor": r.motor,
            "respuesta": _recortar(r.respuesta, maximo),
        }
        for r in respuestas
        if r.prompt_id in de_marca
    ]


# --- La Risposta y el reporte --------------------------------------------------------


def reporte_markdown(
    marca: str,
    escucha: Mapping[str, Any],
    validacion: Mapping[str, Any],
    de_marca: Sequence[Mapping[str, str]],
    salida: Path | None = None,
) -> Path:
    """Escribe ``data/gold/eco-<marca>.md`` y devuelve su ruta."""
    ruta = salida or ruta_reporte(marca, GOLD_DIR)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        f"# L'Eco · {marca}",
        "",
        "> Lo que los motores de respuesta repiten de la marca. Las cifras las calcula el",
        "> codigo sobre las respuestas recogidas; ninguna sale de un modelo de lenguaje.",
        "",
        "## L'Ascolto",
        "",
        "| Medida | Valor |",
        "|---|---|",
        f"| Preguntas conversacionales con respuesta | {escucha['con_respuesta']} |",
        f"| Preguntas donde aparece la marca | {escucha['visibles']} |",
        f"| Visibilidad | {escucha['visibilidad']} % |",
        f"| Share of voice | {escucha['share_of_voice']} % |",
        f"| Posicion promedio cuando aparece | {escucha['posicion_promedio'] or '-'} |",
        f"| Respuestas que citan el sitio propio | {escucha['citas_propias']} |",
        "",
        "## Menciones por marca",
        "",
        "| Marca | Menciones |",
        "|---|---|",
        *[f"| {_celda(nombre)} | {total} |" for nombre, total in escucha["menciones"].items()],
        "",
        "## Sitios citados",
        "",
        "| Dominio | Veces |",
        "|---|---|",
        *[f"| {_celda(d)} | {total} |" for d, total in escucha["dominios_citados"].items()],
        "",
        "## La Risposta: brechas",
        "",
    ]
    if escucha["brechas"]:
        lineas += ["| Pregunta | Etapa | Aparecen | El Paradiso |", "|---|---|---|---|"]
        for brecha in escucha["brechas"]:
            pagina = brecha["paradiso"]
            destino = f"tiene {pagina['url']}" if pagina else "falta contenido"
            rivales = ", ".join(brecha["rivales"])
            lineas.append(
                f"| {_celda(brecha['prompt'])} | {brecha['etapa']} | {_celda(rivales)} "
                f"| {_celda(destino)} |"
            )
    else:
        lineas.append("Sin brechas en las respuestas recogidas.")
    lineas += ["", "## Lo que dicen de la marca", ""]
    if de_marca:
        lineas += ["| Pregunta | Motor | Respuesta |", "|---|---|---|"]
        lineas += [
            f"| {_celda(r['prompt'])} | {_celda(r['motor'])} | {_celda(r['respuesta'])} |"
            for r in de_marca
        ]
    else:
        lineas.append("Sin respuestas del set de marca.")
    lineas += ["", "## Le Domande", ""]
    if validacion["problemas"]:
        lineas += [f"- {problema}" for problema in validacion["problemas"]]
    else:
        lineas.append("La matriz cumple las reglas.")
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def ruta_reporte(marca: str, gold_dir: Path) -> Path:
    """Ruta convencional del reporte de L'Eco."""
    return gold_dir / f"eco-{_slug(marca)}.md"


def ruta_respuestas(marca: str, ascolto_dir: Path = ASCOLTO_DIR) -> Path:
    """Ruta convencional del JSONL de respuestas."""
    return ascolto_dir / f"{_slug(marca)}.jsonl"


def leer_corpus(path: Path) -> list[dict[str, Any]]:
    """Lee el corpus del Paradiso con el texto de cada pagina."""
    if not path.exists():
        return []
    documentos = []
    for linea in path.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        registro = json.loads(linea)
        ruta_gold = registro.get("ruta_gold") or ""
        texto = ""
        archivo = path.parent / Path(ruta_gold).name if ruta_gold else None
        if archivo and archivo.exists():
            texto = re.sub(
                r"\A---\n.*?\n---\n", "", archivo.read_text(encoding="utf-8"), flags=re.S
            )
        documentos.append({"url": registro.get("url_cita", ""), "texto": texto})
    return documentos


# --- utilidades ----------------------------------------------------------------------


def _normalizar(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto)
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", plano).lower().strip()


def _menciona(texto: str, nombre: str) -> bool:
    if not nombre.strip():
        return False
    patron = r"(?<!\w)" + re.escape(_normalizar(nombre)) + r"(?!\w)"
    return re.search(patron, _normalizar(texto)) is not None


def _nombrados_en_orden(texto: str, nombres: Iterable[str]) -> list[str]:
    normal = _normalizar(texto)
    hallados = []
    for nombre in nombres:
        patron = r"(?<!\w)" + re.escape(_normalizar(nombre)) + r"(?!\w)"
        coincidencia = re.search(patron, normal)
        if coincidencia:
            hallados.append((coincidencia.start(), nombre))
    return [nombre for _, nombre in sorted(hallados)]


def _dominio(url: str) -> str:
    host = urlsplit(url if "//" in url else f"//{url}").netloc.lower()
    return host.removeprefix("www.") or "(sin dominio)"


def _es_del_dominio(url: str, dominio: str) -> bool:
    host = _dominio(url)
    propio = dominio.lower().removeprefix("www.")
    return host == propio or host.endswith(f".{propio}")


def _palabras(texto: str) -> set[str]:
    return {
        palabra
        for palabra in re.findall(r"[a-z0-9]{4,}", _normalizar(texto))
        if palabra not in _PALABRAS_VACIAS
    }


def _mejor_pagina(prompt: str, corpus: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    buscadas = _palabras(prompt)
    if not buscadas:
        return None
    mejor: tuple[float, Mapping[str, Any]] | None = None
    for documento in corpus:
        palabras = _palabras(str(documento.get("texto", "")))
        if not palabras:
            continue
        puntaje = len(buscadas & palabras) / len(buscadas)
        if mejor is None or puntaje > mejor[0]:
            mejor = (puntaje, documento)
    if mejor is None or mejor[0] < UMBRAL_COBERTURA:
        return None
    return {"url": mejor[1].get("url", ""), "puntaje": round(mejor[0], 2)}


def _porcentaje(parte: int, total: int) -> float:
    return round(parte / total * 100, 1) if total else 0.0


def _slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _normalizar(texto)).strip("-") or "marca"


def _recortar(texto: str, maximo: int) -> str:
    plano = re.sub(r"\s+", " ", texto).strip()
    return plano if len(plano) <= maximo else plano[: maximo - 1].rstrip() + "…"


def _celda(texto: str) -> str:
    return str(texto).replace("|", "\\|").replace("\n", " ")
