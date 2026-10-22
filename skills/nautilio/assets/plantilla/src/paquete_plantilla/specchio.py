"""Lo Specchio: como se ve la marca cuando alguien comparte su sitio en redes sociales.

Tres miradas sobre el HTML ya capturado en el Inferno:
- La vista previa: las etiquetas ``og:`` y la tarjeta que acompanan un enlace compartido.
- Los perfiles: los enlaces a perfiles sociales y los que declaran los datos estructurados.
- Los atajos: botones para compartir y enlaces de mensajeria directa.

Este modulo nunca hace peticiones de red ni visita los perfiles: solo lee los archivos
``.html`` de ``data/raw``. Ninguna cifra sale de un modelo de lenguaje: todas se cuentan
sobre el HTML de entrada, y cada pagina conserva su URL como fuente.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from paquete_plantilla.config import GOLD_DIR, RAW_DIR

SPECCHIO_PATH = GOLD_DIR / "specchio.json"
CAMPOS_OG = ("title", "description", "image", "type", "url")
ARCHIVOS_INICIO = frozenset({"inicio", "index", "home"})

# Dominio base -> red. Un subdominio (m., es-la., co.) cuenta como su dominio base.
REDES: dict[str, str] = {
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "x.com": "x",
    "twitter.com": "x",
    "linkedin.com": "linkedin",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "pinterest.com": "pinterest",
    "threads.net": "threads",
    "threads.com": "threads",
}
# Primer segmento de ruta que no es un perfil: compartir, incrustar o una publicacion suelta.
NO_PERFIL = frozenset(
    {
        "sharer",
        "sharer.php",
        "share",
        "share.php",
        "dialog",
        "plugins",
        "tr",
        "login",
        "watch",
        "hashtag",
        "events",
        "photo",
        "photo.php",
        "story.php",
        "permalink.php",
        "p",
        "reel",
        "reels",
        "explore",
        "stories",
        "accounts",
        "tv",
        "direct",
        "intent",
        "home",
        "search",
        "i",
        "pin",
        "media",
        "help",
        "policies",
        "privacy",
        "business",
        "marketplace",
        "gaming",
    }
)
# Primer segmento que abre un perfil de varios segmentos y cuantos ocupa
# (/groups/<id>, /pages/<nombre>/<id>, /company/<nombre>, /channel/<id>).
PREFIJOS_COMPUESTOS: dict[str, dict[str, int]] = {
    "facebook": {"groups": 2, "pages": 3, "people": 3},
    "linkedin": {"company": 2, "in": 2, "school": 2, "showcase": 2},
    "youtube": {"channel": 2, "c": 2, "user": 2},
}
# Redes en que un segmento suelto no es perfil, salvo un identificador con arroba.
REDES_SOLO_COMPUESTAS = frozenset({"linkedin", "youtube"})
# Redes cuyo perfil siempre empieza con arroba.
REDES_CON_ARROBA = frozenset({"tiktok", "threads"})
# Redes en que mayusculas y minusculas distinguen perfiles (identificadores de canal).
REDES_SENSIBLES = frozenset({"youtube"})

# Mensajeria directa: enlaces para escribirle a la marca o para compartir por chat.
HOSTS_MENSAJERIA = frozenset({"wa.me", "api.whatsapp.com", "web.whatsapp.com"})
ESQUEMAS_MENSAJERIA = ("whatsapp:",)
# Fragmentos de ruta que delatan un boton para compartir en una red.
RUTAS_COMPARTIR = ("/sharer", "/share", "/intent/", "/sharing/", "/sharearticle", "/pin/create")
CLASE_COMPARTIR = re.compile(r"(?:^|[-_])shares?(?:$|[-_])|addtoany|a2a_|sharethis", re.I)


def analizar_html(html: str, url: str) -> dict[str, Any]:
    """Revisa la vista previa, los perfiles y los atajos de una pagina capturada."""
    return _analizar_sopa(BeautifulSoup(html, "lxml"), url)


def analizar_bronze(raw_dir: str | Path = RAW_DIR) -> dict[str, Any]:
    """Resume el sitio a partir de los ``.html`` del Inferno, sin tocar la red.

    La URL de cada pagina sale de su enlace canonico (resuelto contra ``og:url`` si es
    relativo) o de su ``og:url``. El manifiesto y cualquier archivo que no sea ``.html``
    se ignoran. ``detalle`` repite por pagina cada dato contado, con su URL como fuente.
    """
    carpeta = Path(raw_dir)
    paginas: list[tuple[str, dict[str, Any]]] = []
    for archivo in sorted(carpeta.glob("*.html")):
        if not archivo.is_file():
            continue
        sopa = BeautifulSoup(archivo.read_text(encoding="utf-8", errors="replace"), "lxml")
        canonico = _canonico(sopa)
        og_url = _og(sopa).get("url", "")
        url = urljoin(og_url, canonico) if canonico else og_url
        paginas.append((archivo.name, _analizar_sopa(sopa, url)))

    _marcar_repetidos(paginas, "title", "og:title repetido en otra pagina")
    _marcar_repetidos(paginas, "description", "og:description repetida en otra pagina")

    perfiles: Counter[str] = Counter()
    red_por_perfil: dict[str, str] = {}
    imagenes: Counter[str] = Counter()
    problemas: Counter[str] = Counter()
    same_as: list[str] = []
    for _, datos in paginas:
        for perfil in datos["perfiles"]:
            perfiles[perfil["url"]] += 1
            red_por_perfil[perfil["url"]] = perfil["red"]
        if datos["og"]["image"]:
            imagenes[datos["og"]["image"]] += 1
        problemas.update(datos["problemas"])
        same_as.extend(datos["schema_same_as"])

    return {
        "paginas": len(paginas),
        "paginas_con_og_completo": sum(_og_completo(datos["og"]) for _, datos in paginas),
        "paginas_con_twitter_card": sum(bool(datos["twitter_card"]) for _, datos in paginas),
        "paginas_con_botones_compartir": sum(datos["botones_compartir"] for _, datos in paginas),
        "paginas_con_whatsapp": sum(datos["whatsapp"] for _, datos in paginas),
        "perfiles": _ordenar(perfiles),
        "red_por_perfil": dict(sorted(red_por_perfil.items())),
        "schema_same_as": _unicos(same_as),
        "imagenes_og": _ordenar(imagenes),
        "previsualizacion": _previsualizacion(paginas),
        "problemas_frecuentes": _ordenar(problemas),
        "detalle": [
            {
                "archivo": archivo,
                "url": datos["url"],
                "og_completo": _og_completo(datos["og"]),
                "og_image": datos["og"]["image"],
                "twitter_card": datos["twitter_card"],
                "perfiles": [perfil["url"] for perfil in datos["perfiles"]],
                "whatsapp": datos["whatsapp"],
                "botones_compartir": datos["botones_compartir"],
                "problemas": datos["problemas"],
            }
            for archivo, datos in paginas
        ],
    }


def escribir(resultado: Mapping[str, Any], ruta: str | Path = SPECCHIO_PATH) -> Path:
    """Guarda el resultado como JSON legible y devuelve su ruta."""
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(resultado, ensure_ascii=False, indent=2)
    destino.write_text(texto + "\n", encoding="utf-8")
    return destino


# --- analisis de una pagina -----------------------------------------------------------


def _analizar_sopa(sopa: BeautifulSoup, url: str) -> dict[str, Any]:
    og = _og(sopa)
    twitter_card = _meta(sopa, "twitter:card")
    enlaces = [_atributo(tag, "href") for tag in sopa.find_all("a")]
    enlaces = [enlace for enlace in enlaces if enlace]
    perfiles = _perfiles(enlaces)
    same_as, json_invalido = _same_as(sopa)
    resultado = {
        "url": url,
        "og": {campo: og.get(campo, "") for campo in CAMPOS_OG},
        "twitter_card": twitter_card,
        "perfiles": perfiles,
        "botones_compartir": _hay_botones_compartir(sopa, enlaces),
        "schema_same_as": same_as,
        "whatsapp": any(_es_mensajeria(enlace) for enlace in enlaces),
        "problemas": [],
    }
    problemas = _problemas_og(sopa, og, url)
    if not twitter_card:
        problemas.append("falta twitter:card")
    if json_invalido:
        problemas.append("datos estructurados con JSON invalido")
    if not perfiles:
        problemas.append("sin enlaces a perfiles sociales")
    elif not same_as:
        problemas.append("perfiles enlazados sin sameAs en datos estructurados")
    else:
        declarados = {_clave_perfil(item) for item in same_as}
        if any(_clave_perfil(perfil["url"]) not in declarados for perfil in perfiles):
            problemas.append("perfil enlazado ausente de sameAs")
    resultado["problemas"] = problemas
    return resultado


def _problemas_og(sopa: BeautifulSoup, og: Mapping[str, str], url: str) -> list[str]:
    problemas: list[str] = []
    declaradas = Counter(_nombre_meta(tag) for tag in sopa.find_all("meta"))
    for campo in CAMPOS_OG:
        nombre = f"og:{campo}"
        if declaradas[nombre] == 0 and not og.get(campo):
            problemas.append(f"falta {nombre}")
        elif not og.get(campo):
            problemas.append(f"{nombre} sin contenido")
        if declaradas[nombre] > 1:
            problemas.append(f"{nombre} declarado mas de una vez")

    descripcion = og.get("description", "")
    if descripcion and not re.search(r"\s", descripcion) and re.search(r"[_-]", descripcion):
        problemas.append("og:description parece un nombre de archivo")

    imagen = og.get("image", "")
    if imagen:
        if not imagen.lower().startswith(("http://", "https://")):
            problemas.append("og:image no es una URL absoluta")
        ancho = _meta(sopa, "og:image:width")
        alto = _meta(sopa, "og:image:height")
        if not ancho and not alto:
            problemas.append("og:image sin ancho ni alto declarados")
        elif not ancho:
            problemas.append("og:image sin ancho declarado")
        elif not alto:
            problemas.append("og:image sin alto declarado")

    og_url = og.get("url", "")
    if og_url and url and _comparable(og_url) != _comparable(url):
        problemas.append("og:url distinta de la URL de la pagina")
    return problemas


def _og(sopa: BeautifulSoup) -> dict[str, str]:
    valores: dict[str, str] = {}
    for tag in sopa.find_all("meta"):
        nombre = _nombre_meta(tag)
        if not nombre.startswith("og:"):
            continue
        contenido = _limpiar(_atributo(tag, "content"))
        if contenido and not valores.get(nombre[3:]):
            valores[nombre[3:]] = contenido
    if not valores.get("image"):
        valores["image"] = valores.get("image:url") or valores.get("image:secure_url", "")
    return valores


def _meta(sopa: BeautifulSoup, nombre: str) -> str:
    for tag in sopa.find_all("meta"):
        if _nombre_meta(tag) == nombre:
            contenido = _limpiar(_atributo(tag, "content"))
            if contenido:
                return contenido
    return ""


def _nombre_meta(tag: Tag) -> str:
    return (_atributo(tag, "property") or _atributo(tag, "name")).strip().lower()


def _canonico(sopa: BeautifulSoup) -> str:
    for tag in sopa.find_all("link"):
        relaciones = tag.get("rel") or []
        if isinstance(relaciones, str):
            relaciones = relaciones.split()
        if "canonical" in {rel.lower() for rel in relaciones}:
            return _atributo(tag, "href").strip()
    return ""


def _same_as(sopa: BeautifulSoup) -> tuple[list[str], bool]:
    encontrados: list[str] = []
    invalido = False
    for script in sopa.find_all("script"):
        if _atributo(script, "type").strip().lower() != "application/ld+json":
            continue
        try:
            datos = json.loads(script.get_text())
        except json.JSONDecodeError:
            invalido = True
            continue
        encontrados.extend(_valores_same_as(datos))
    return _unicos(encontrados), invalido


def _valores_same_as(datos: Any) -> Iterator[str]:
    if isinstance(datos, dict):
        for clave, valor in datos.items():
            if clave == "sameAs":
                valores = valor if isinstance(valor, list) else [valor]
                yield from (item.strip() for item in valores if isinstance(item, str))
            else:
                yield from _valores_same_as(valor)
    elif isinstance(datos, list):
        for item in datos:
            yield from _valores_same_as(item)


# --- perfiles y atajos ----------------------------------------------------------------


def _perfiles(enlaces: Iterable[str]) -> list[dict[str, str]]:
    vistos: dict[str, str] = {}
    for enlace in enlaces:
        perfil = _perfil(enlace)
        if perfil is not None:
            vistos.setdefault(perfil[0], perfil[1])
    return [
        {"url": url, "red": red}
        for url, red in sorted(vistos.items(), key=lambda item: (item[1], item[0]))
    ]


def _perfil(enlace: str) -> tuple[str, str] | None:
    """Normaliza un enlace a perfil social y devuelve ``(url, red)``, o ``None``."""
    partes = _partir(enlace)
    if partes is None:
        return None
    host, ruta, consulta = partes
    base = _dominio_red(host)
    if base is None:
        return None
    red = REDES[base]
    segmentos = [segmento for segmento in ruta.split("/") if segmento]
    if not segmentos:
        return None
    primero = segmentos[0].lower()

    if base == "facebook.com" and primero == "profile.php":
        identificador = (parse_qs(consulta).get("id") or [""])[0]
        if not identificador.isdigit():
            return None
        return f"https://{base}/profile.php?id={identificador}", red

    compuestos = PREFIJOS_COMPUESTOS.get(red, {})
    if primero in compuestos:
        largo = compuestos[primero]
        if len(segmentos) < largo:
            return None
        perfil = segmentos[:largo]
    elif red in REDES_SOLO_COMPUESTAS:
        if red != "youtube" or not primero.startswith("@") or len(primero) < 2:
            return None
        perfil = segmentos[:1]
    elif red in REDES_CON_ARROBA:
        if not primero.startswith("@") or len(primero) < 2:
            return None
        perfil = segmentos[:1]
    else:
        if primero in NO_PERFIL or primero.endswith(".php"):
            return None
        perfil = segmentos[:1]

    camino = "/".join(perfil)
    if red not in REDES_SENSIBLES:
        camino = camino.lower()
    return f"https://{base}/{camino}", red


def _hay_botones_compartir(sopa: BeautifulSoup, enlaces: Iterable[str]) -> bool:
    for enlace in enlaces:
        partes = _partir(enlace)
        if partes is None:
            continue
        host, ruta, consulta = partes
        if host in HOSTS_MENSAJERIA:
            parametros = parse_qs(consulta)
            sin_destinatario = not ruta.strip("/") or ruta.strip("/") == "send"
            if "text" in parametros and sin_destinatario and "phone" not in parametros:
                return True
            continue
        if _dominio_red(host) and any(marca in ruta.lower() for marca in RUTAS_COMPARTIR):
            return True
    for tag in sopa.find_all(class_=True):
        clases = tag.get("class") or []
        if isinstance(clases, str):
            clases = clases.split()
        if any(CLASE_COMPARTIR.search(clase) for clase in clases):
            return True
    return False


def _es_mensajeria(enlace: str) -> bool:
    if enlace.strip().lower().startswith(ESQUEMAS_MENSAJERIA):
        return True
    partes = _partir(enlace)
    return partes is not None and partes[0] in HOSTS_MENSAJERIA


# --- resumen del sitio ----------------------------------------------------------------


def _marcar_repetidos(paginas: list[tuple[str, dict[str, Any]]], campo: str, problema: str) -> None:
    conteo = Counter(datos["og"][campo].casefold() for _, datos in paginas if datos["og"][campo])
    for _, datos in paginas:
        valor = datos["og"][campo].casefold()
        if valor and conteo[valor] > 1:
            datos["problemas"].append(problema)


def _previsualizacion(paginas: list[tuple[str, dict[str, Any]]]) -> dict[str, str] | None:
    for archivo, datos in paginas:
        ruta = urlsplit(datos["url"]).path if datos["url"] else None
        if ruta in ("", "/") or Path(archivo).stem.lower() in ARCHIVOS_INICIO:
            return {
                "title": datos["og"]["title"],
                "description": datos["og"]["description"],
                "image": datos["og"]["image"],
                "fuente": datos["url"] or archivo,
            }
    return None


def _og_completo(og: Mapping[str, str]) -> bool:
    return all(og.get(campo) for campo in CAMPOS_OG)


def _ordenar(conteo: Counter[str]) -> dict[str, int]:
    return dict(sorted(conteo.items(), key=lambda item: (-item[1], item[0])))


# --- utilidades -----------------------------------------------------------------------


def _partir(enlace: str) -> tuple[str, str, str] | None:
    """Devuelve ``(host, ruta, consulta)`` de un enlace absoluto, o ``None``."""
    texto = enlace.strip()
    if texto.startswith("//"):
        texto = f"https:{texto}"
    partes = urlsplit(texto)
    if partes.scheme.lower() not in ("http", "https") or not partes.netloc:
        return None
    host = partes.netloc.lower().rsplit("@", 1)[-1].split(":", 1)[0]
    return host.removeprefix("www."), partes.path, partes.query


def _dominio_red(host: str) -> str | None:
    for base in REDES:
        if host == base or host.endswith(f".{base}"):
            return base
    return None


def _clave_perfil(url: str) -> str:
    perfil = _perfil(url)
    return perfil[0] if perfil else _comparable(url)


def _comparable(url: str) -> str:
    texto = url.strip()
    if texto.startswith("//"):
        texto = f"https:{texto}"
    partes = urlsplit(texto if "//" in texto else f"//{texto}")
    host = partes.netloc.lower().removeprefix("www.")
    return f"{host}{partes.path.rstrip('/')}"


def _atributo(tag: Tag, nombre: str) -> str:
    valor = tag.get(nombre)
    if isinstance(valor, list):
        return " ".join(valor)
    return valor or ""


def _limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def _unicos(valores: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(valor for valor in valores if valor))
