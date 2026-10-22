"""Le Muse: cuentas y reporte determinista de anuncios publicos.

Lema: inspirate, no copies. Ninguna cifra sale de un modelo de lenguaje; todas se
calculan sobre el JSONL de entrada.

El JSONL lo recolecta una persona en el navegador o un agente con un conector
autorizado de las bibliotecas publicas de anuncios. Este modulo nunca descarga videos.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from paquete_plantilla.config import GOLD_DIR

SIN_FORMATO = "(sin formato)"
SIN_CTA = "(sin cta)"
SIN_DESTINO = "(sin destino)"
PLATAFORMAS = frozenset({"meta", "google"})
TEXTO_MAXIMO = 120


@dataclass(frozen=True, slots=True)
class Anuncio:
    """Un anuncio publico recolectado a mano o con un conector autorizado."""

    id: str
    plataforma: str
    pagina: str = ""
    fecha_inicio: str = ""
    formato: str = ""
    texto: str = ""
    titulo: str = ""
    cta: str = ""
    url_destino: str = ""
    url_ficha: str = ""
    duracion_s: float | None = None
    transcripcion: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Anuncio:
        """Valida y normaliza una fila del JSONL de anuncios."""
        anuncio_id = str(data.get("id", "")).strip()
        if not anuncio_id:
            raise ValueError("el anuncio no tiene id")
        plataforma = str(data.get("plataforma", "")).strip().lower()
        if plataforma not in PLATAFORMAS:
            raise ValueError(
                f"plataforma invalida para {anuncio_id!r}: "
                f"se esperaba meta o google, no {plataforma!r}"
            )
        return cls(
            id=anuncio_id,
            plataforma=plataforma,
            pagina=str(data.get("pagina", "")).strip(),
            fecha_inicio=str(data.get("fecha_inicio", "")).strip(),
            formato=str(data.get("formato", "")).strip(),
            texto=str(data.get("texto", "")).strip(),
            titulo=str(data.get("titulo", "")).strip(),
            cta=str(data.get("cta", "")).strip(),
            url_destino=str(data.get("url_destino", "")).strip(),
            url_ficha=str(data.get("url_ficha", "")).strip(),
            duracion_s=_numero(data.get("duracion_s")),
            transcripcion=str(data.get("transcripcion", "")).strip(),
        )


@dataclass(frozen=True, slots=True)
class CreativoUnico:
    """Un creativo agrupado por huella de texto, titulo y formato."""

    huella: str
    formato: str
    titulo: str
    texto: str
    anuncios: tuple[str, ...]
    plataformas: tuple[str, ...]

    @property
    def repeticiones(self) -> int:
        """Cuantos anuncios comparten esta huella."""
        return len(self.anuncios)


def cargar_anuncios(path: str | Path) -> list[Anuncio]:
    """Carga ``data/raw/anuncios/<marca>.jsonl`` y valida cada fila."""
    ruta = Path(path)
    anuncios: list[Anuncio] = []
    with ruta.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{ruta.name}, linea {number}: JSON invalido") from exc
            if not isinstance(data, dict):
                raise ValueError(f"{ruta.name}, linea {number}: se esperaba un objeto JSON")
            try:
                anuncios.append(Anuncio.from_dict(data))
            except ValueError as exc:
                raise ValueError(f"{ruta.name}, linea {number}: {exc}") from exc
    return anuncios


def huella(anuncio: Anuncio) -> str:
    """Huella estable de texto, titulo y formato (sin plataforma ni fechas)."""
    payload = "\x1f".join(
        (
            _normalizar(anuncio.texto),
            _normalizar(anuncio.titulo),
            _normalizar(anuncio.formato),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def creativos_unicos(anuncios: Sequence[Anuncio]) -> list[CreativoUnico]:
    """Agrupa anuncios por huella y devuelve los creativos unicos."""
    grupos: dict[str, list[Anuncio]] = {}
    for anuncio in anuncios:
        grupos.setdefault(huella(anuncio), []).append(anuncio)

    creativos: list[CreativoUnico] = []
    for clave, grupo in grupos.items():
        primero = grupo[0]
        creativos.append(
            CreativoUnico(
                huella=clave,
                formato=primero.formato or SIN_FORMATO,
                titulo=primero.titulo,
                texto=primero.texto,
                anuncios=tuple(item.id for item in grupo),
                plataformas=tuple(sorted({item.plataforma for item in grupo})),
            )
        )
    creativos.sort(key=lambda item: (-item.repeticiones, item.huella))
    return creativos


def resumen(anuncios: Sequence[Anuncio]) -> dict[str, Any]:
    """Calcula totales, repetidos, formatos, destinos y CTA sin usar un LLM."""
    total = len(anuncios)
    unicos = len(creativos_unicos(anuncios))
    repetidos = total - unicos
    porcentaje = round(repetidos / total * 100, 2) if total else 0.0
    return {
        "total": total,
        "unicos": unicos,
        "repetidos": repetidos,
        "porcentaje_repetido": porcentaje,
        "por_formato": _conteos(
            anuncio.formato.strip().lower() or SIN_FORMATO for anuncio in anuncios
        ),
        "por_dominio": _conteos(_dominio(anuncio.url_destino) for anuncio in anuncios),
        "por_cta": _conteos(anuncio.cta.strip() or SIN_CTA for anuncio in anuncios),
    }


def reporte_markdown(
    anuncios: Sequence[Anuncio],
    marca: str,
    salida: str | Path | None = None,
) -> Path:
    """Escribe ``inteligencia-anuncios-<marca>.md`` y devuelve su ruta."""
    destino = Path(salida) if salida is not None else ruta_reporte(marca, GOLD_DIR)
    datos = resumen(anuncios)
    creativos = creativos_unicos(anuncios)
    lineas = [
        f"# Inteligencia de anuncios — {marca}",
        "",
        "> Datos publicos de las bibliotecas publicas de anuncios de las plataformas.",
        "> Le Muse: inspirate, no copies. Este reporte no descarga videos ni inventa cifras.",
        "",
        "## Resumen",
        "",
        "| Metrica | Valor |",
        "|---------|-------|",
        f"| Anuncios | {datos['total']} |",
        f"| Creativos unicos | {datos['unicos']} |",
        f"| Anuncios repetidos | {datos['repetidos']} |",
        f"| Porcentaje repetido | {datos['porcentaje_repetido']:.2f} % |",
        "",
        "## Formatos",
        "",
        *_tabla_conteos(datos["por_formato"], "Formato"),
        "",
        "## Destinos",
        "",
        *_tabla_conteos(datos["por_dominio"], "Dominio"),
        "",
        "## Llamados a la accion",
        "",
        *_tabla_conteos(datos["por_cta"], "CTA"),
        "",
        "## Creativos unicos",
        "",
    ]

    if creativos:
        lineas.extend(
            [
                "| # | Formato | Titulo | Texto | Repeticiones | Fichas |",
                "|---|---------|--------|-------|--------------|--------|",
            ]
        )
        for index, creativo in enumerate(creativos, start=1):
            fichas = _fichas(anuncios, creativo.anuncios)
            lineas.append(
                "| "
                + " | ".join(
                    (
                        str(index),
                        _celda(creativo.formato),
                        _celda(creativo.titulo or "—"),
                        _celda(_recortar(creativo.texto) or "—"),
                        str(creativo.repeticiones),
                        fichas,
                    )
                )
                + " |"
            )
    else:
        lineas.append("Sin anuncios cargados.")

    lineas.extend(["", "## Anuncios repetidos", ""])
    repetidos = [creativo for creativo in creativos if creativo.repeticiones > 1]
    if repetidos:
        for creativo in repetidos:
            ids = ", ".join(creativo.anuncios)
            lineas.append(
                f"- {creativo.repeticiones} veces ({creativo.formato}): {ids}. "
                f"Fichas: {_fichas(anuncios, creativo.anuncios)}"
            )
    else:
        lineas.append("No hay creativos repetidos.")

    lineas.extend(["", "## Fichas consultadas", ""])
    fichas_unicas = sorted({anuncio.url_ficha for anuncio in anuncios if anuncio.url_ficha})
    if fichas_unicas:
        lineas.extend(f"- [{url}]({url})" for url in fichas_unicas)
    else:
        lineas.append("Sin fichas registradas.")

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas).rstrip() + "\n", encoding="utf-8")
    return destino


def ruta_reporte(marca: str, gold_dir: Path) -> Path:
    """Devuelve la ruta convencional del reporte para una marca."""
    return gold_dir / f"inteligencia-anuncios-{marca}.md"


def _numero(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalizar(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _dominio(url: str) -> str:
    if not url:
        return SIN_DESTINO
    host = urlsplit(url).netloc.lower()
    if not host:
        return SIN_DESTINO
    host = host.rsplit("@", 1)[-1].split(":", 1)[0]
    return host[4:] if host.startswith("www.") else host


def _conteos(values: Iterable[str]) -> dict[str, int]:
    counter = Counter(values)
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def _tabla_conteos(conteos: Mapping[str, int], etiqueta: str) -> list[str]:
    if not conteos:
        return ["Sin datos."]
    lines = [f"| {etiqueta} | Anuncios |", "|---------|----------|"]
    lines.extend(f"| {_celda(valor)} | {total} |" for valor, total in conteos.items())
    return lines


def _fichas(anuncios: Sequence[Anuncio], ids: Sequence[str]) -> str:
    por_id = {anuncio.id: anuncio.url_ficha for anuncio in anuncios}
    urls = sorted({por_id.get(anuncio_id, "") for anuncio_id in ids} - {""})
    if not urls:
        return "—"
    return "<br>".join(f"[ficha]({url})" for url in urls)


def _recortar(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= TEXTO_MAXIMO:
        return clean
    return clean[: TEXTO_MAXIMO - 1].rstrip() + "…"


def _celda(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")
