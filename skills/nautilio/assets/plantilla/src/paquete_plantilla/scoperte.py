"""Le Scoperte: lo que encontro el viaje, con cada cita comprobada contra el Paradiso.

El agente redacta los hallazgos y los vacios en ``data/gold/hallazgos.json`` y las acciones
de La Risposta en ``data/gold/risposta.json``. Este modulo no redacta nada: comprueba que
cada cita exista letra por letra en el documento que nombra, deja como evidencia solo las
paginas que estan en el Paradiso y descarta lo que no se pueda sostener. Lo que no pasa la
prueba no llega a La Cronaca.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from paquete_plantilla.config import GOLD_DIR

HALLAZGOS_PATH = GOLD_DIR / "hallazgos.json"
RISPOSTA_PATH = GOLD_DIR / "risposta.json"
CITA_MINIMA = 20
CITA_MAXIMA = 280
ESFUERZOS = ("bajo", "medio", "alto")
PLAZOS = ("hoy", "este mes", "este semestre")
# Comillas tipograficas a comillas rectas: una cita no se descarta por el tipo de comilla.
_COMILLAS = str.maketrans(
    {
        chr(0x201C): '"',
        chr(0x201D): '"',
        chr(0xAB): '"',
        chr(0xBB): '"',
        chr(0x2018): "'",
        chr(0x2019): "'",
    }
)


def textos_del_paradiso(gold_dir: Path = GOLD_DIR) -> dict[str, str]:
    """Texto plano de cada documento del Paradiso, indexado por su url de cita."""
    corpus = gold_dir / "corpus.jsonl"
    if not corpus.is_file():
        return {}
    textos: dict[str, str] = {}
    for linea in corpus.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        registro = json.loads(linea)
        archivo = gold_dir / Path(str(registro.get("ruta_gold", ""))).name
        if archivo.is_file():
            textos[str(registro.get("url_cita", ""))] = plano(archivo.read_text(encoding="utf-8"))
    return textos


def plano(markdown: str) -> str:
    """Texto comparable: sin front matter, enlaces, negritas ni espacios de mas."""
    texto = re.sub(r"\A---\n.*?\n---\n", "", markdown, flags=re.S)
    texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texto)
    texto = re.sub(r"\*\*|__|^#+\s*", "", texto, flags=re.M)
    texto = unicodedata.normalize("NFC", texto).translate(_COMILLAS)
    return re.sub(r"\s+", " ", texto).strip().casefold()


def cargar_hallazgos(textos: Mapping[str, str], path: Path = HALLAZGOS_PATH) -> dict[str, Any]:
    """Lee los hallazgos y conserva solo los que tienen una cita comprobable."""
    data = _leer(path)
    validos: list[dict[str, str]] = []
    descartados: list[dict[str, str]] = []
    for numero, item in enumerate(data.get("hallazgos", []), start=1):
        hallazgo = {
            clave: str(item.get(clave, "")).strip()
            for clave in ("tema", "hallazgo", "cita", "url_cita")
        }
        hallazgo["id"] = str(item.get("id") or f"h{numero}").strip()
        motivo = _motivo_descarte(hallazgo, textos)
        if motivo:
            descartados.append({**hallazgo, "motivo": motivo})
        else:
            validos.append(hallazgo)
    vacios = [
        {clave: str(item.get(clave, "")).strip() for clave in ("tema", "por_que_importa")}
        for item in data.get("vacios", [])
        if str(item.get("tema", "")).strip()
    ]
    ids = {hallazgo["id"] for hallazgo in validos}
    insights = []
    for item in data.get("insights", []):
        sostenidos = [i for i in _lista(item.get("hallazgos")) if i in ids]
        titulo = str(item.get("titulo", "")).strip()
        if titulo and sostenidos:
            insights.append(
                {
                    "titulo": titulo,
                    "por_que_importa": str(item.get("por_que_importa", "")).strip(),
                    "hallazgos": sostenidos,
                }
            )
    return {
        "hallazgos": validos,
        "descartados": descartados,
        "vacios": vacios,
        "insights": insights,
    }


def cargar_relato(permitidas: set[str], path: Path = RISPOSTA_PATH) -> dict[str, Any]:
    """Lee la Gran Idea y la historia de tres minutos.

    Una frase con una cifra que no salio de los datos del viaje no llega a La Cronaca.
    """
    data = _leer(path)
    gran_idea = str(data.get("gran_idea", "")).strip()
    historia = [
        frase for frase in _lista(data.get("historia")) if cifras_sostenidas(frase, permitidas)
    ]
    descartadas = len(_lista(data.get("historia"))) - len(historia)
    if gran_idea and not cifras_sostenidas(gran_idea, permitidas):
        gran_idea, descartadas = "", descartadas + 1
    return {"gran_idea": gran_idea, "historia": historia[:3], "descartadas": descartadas}


def cifras(texto: str) -> set[str]:
    """Los numeros de un texto, sin separadores de miles ni ceros de mas."""
    hallados = set()
    for numero in re.findall(r"\d+(?:[.,]\d+)?", texto or ""):
        limpio = numero.replace(",", ".")
        hallados.add(limpio.rstrip("0").rstrip(".") if "." in limpio else limpio)
    return hallados


def cifras_sostenidas(texto: str, permitidas: set[str]) -> bool:
    """True si cada numero del texto aparece en los datos del viaje."""
    return cifras(texto) <= permitidas


def cargar_acciones(textos: Mapping[str, str], path: Path = RISPOSTA_PATH) -> list[dict[str, Any]]:
    """Lee La Risposta. Solo cuenta como evidencia una pagina que este en el Paradiso."""
    acciones = []
    for item in _leer(path).get("acciones", []):
        titulo = str(item.get("titulo", "")).strip()
        if not titulo:
            continue
        acciones.append(
            {
                "titulo": titulo,
                "prioridad": _entero(item.get("prioridad")),
                "responde_a": _lista(item.get("responde_a")),
                "que_debe_decir": _lista(item.get("que_debe_decir")),
                "evidencia": [
                    url for url in _lista(item.get("evidencia_disponible")) if url in textos
                ],
                "falta_confirmar": _lista(item.get("falta_confirmar")),
                "resultado": str(item.get("resultado", "")).strip(),
                "esfuerzo": _opcion(item.get("esfuerzo"), ESFUERZOS),
                "cuando": _opcion(item.get("cuando"), PLAZOS),
            }
        )
    acciones.sort(key=lambda accion: accion["prioridad"])
    return acciones


# --- utilidades ----------------------------------------------------------------------


def _motivo_descarte(hallazgo: Mapping[str, str], textos: Mapping[str, str]) -> str:
    if not (hallazgo["tema"] and hallazgo["hallazgo"]):
        return "falta tema o hallazgo"
    cita = plano(hallazgo["cita"])
    if not CITA_MINIMA <= len(cita) <= CITA_MAXIMA:
        return f"la cita debe tener entre {CITA_MINIMA} y {CITA_MAXIMA} caracteres"
    if "enmascarad" in cita:
        return "la cita contiene un dato enmascarado"
    texto = textos.get(hallazgo["url_cita"])
    if texto is None:
        return "la pagina citada no esta en el Paradiso"
    if cita not in texto:
        return "la cita no aparece en la pagina que nombra"
    return ""


def _leer(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _lista(valor: Any) -> list[str]:
    """Acepta una lista o un texto con una vineta por linea ("- punto")."""
    if isinstance(valor, str):
        valor = valor.splitlines()
    if not isinstance(valor, list):
        return []
    limpios = (re.sub(r"^\s*[-*•]\s*", "", str(item)).strip() for item in valor)
    return [item for item in limpios if item]


def _opcion(valor: Any, opciones: tuple[str, ...]) -> str:
    texto = str(valor or "").strip().lower()
    return texto if texto in opciones else ""


def _entero(valor: Any) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return 99
