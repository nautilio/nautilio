"""Paradiso: front matter, indice ``corpus.jsonl`` y Registro del Lete."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from paquete_plantilla.extracting import count_masks


def render_gold(metadata: Mapping[str, Any], body: str) -> str:
    """Compone el documento del Paradiso con front matter YAML y cuerpo Markdown."""
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.rstrip() + "\n"


def write_gold(path: Path, metadata: Mapping[str, Any], body: str) -> None:
    """Escribe un documento del Paradiso de forma atomica."""
    _write_text(path, render_gold(metadata, body))


def write_corpus(path: Path, records: Iterable[Mapping[str, Any]]) -> int:
    """Reescribe ``corpus.jsonl`` y devuelve cuantos registros escribio."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(dict(record), ensure_ascii=False) + "\n")
            count += 1
    temporary.replace(path)
    return count


def read_corpus(path: Path) -> list[dict[str, Any]]:
    """Lee ``corpus.jsonl``; devuelve una lista vacia si no existe."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_inventory(documents: Mapping[str, str]) -> dict[str, Any]:
    """Arma el Registro del Lete: mascaras por archivo, por tipo y en total."""
    por_tipo: dict[str, int] = {"correo": 0, "telefono": 0, "identificacion": 0}
    por_archivo: dict[str, dict[str, int]] = {}
    for name in sorted(documents):
        counts = count_masks(documents[name])
        por_archivo[name] = counts
        for kind, total in counts.items():
            por_tipo[kind] += total
    return {
        "por_tipo": por_tipo,
        "por_archivo": por_archivo,
        "total": sum(por_tipo.values()),
    }


def write_inventory(path: Path, documents: Mapping[str, str]) -> dict[str, Any]:
    """Escribe el Registro del Lete (``inventario_enmascarado.json``) y lo devuelve."""
    inventory = build_inventory(documents)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return inventory


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "null"
    return json.dumps(str(value), ensure_ascii=False)
