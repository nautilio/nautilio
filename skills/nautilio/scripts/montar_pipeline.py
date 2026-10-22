#!/usr/bin/env python3
"""Monta el proyecto plantilla de nautilio en una carpeta destino.

Solo usa la biblioteca estandar. Copia ``assets/plantilla``, renombra la carpeta
del paquete y sustituye los marcadores ``{{EMPRESA}}``, ``{{DOMINIO}}``,
``paquete_plantilla`` y ``{{FECHA}}``. Sin ``--force`` nunca sobrescribe un archivo
que ya exista.
"""

from __future__ import annotations

import argparse
import keyword
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = SKILL_DIR / "assets" / "plantilla"
PACKAGE_MARKER = "paquete_plantilla"  # identificador valido: la plantilla es Python analizable
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".venv"}


@dataclass(frozen=True, slots=True)
class Summary:
    """Resultado de montar el proyecto."""

    destination: Path
    package: str
    written: list[str]
    skipped: list[str]
    dry_run: bool


def slugify(text: str) -> str:
    """Convierte un nombre legible en un identificador snake_case."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")
    if not slug:
        slug = "corpus"
    if slug[0].isdigit():
        slug = f"_{slug}"
    return slug


def normalize_domain(value: str) -> str:
    """Quita esquema, ruta y barra final de un dominio."""
    domain = value.strip().lower()
    domain = re.sub(r"^[a-z]+://", "", domain)
    domain = domain.split("/", 1)[0]
    if not domain or " " in domain:
        raise ValueError(f"dominio invalido: {value!r}")
    return domain


def render(text: str, values: dict[str, str]) -> str:
    """Sustituye los marcadores de la plantilla."""
    for marker, value in values.items():
        text = text.replace(marker, value)
    return text


def montar(
    empresa: str,
    dominio: str,
    destination: Path,
    package: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    today: str | None = None,
) -> Summary:
    """Copia la plantilla y devuelve el resumen de lo escrito y lo omitido."""
    if not TEMPLATE_DIR.is_dir():
        raise FileNotFoundError(f"no existe la plantilla: {TEMPLATE_DIR}")

    package = package or slugify(empresa)
    if not package.isidentifier() or keyword.iskeyword(package):
        raise ValueError(f"paquete invalido: {package!r}")

    values = {
        "{{EMPRESA}}": empresa.strip(),
        "{{DOMINIO}}": normalize_domain(dominio),
        "paquete_plantilla": package,
        "{{FECHA}}": today or date.today().isoformat(),
    }

    written: list[str] = []
    skipped: list[str] = []
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)

    for source in sorted(TEMPLATE_DIR.rglob("*")):
        if source.is_dir() or any(part in SKIP_DIRS for part in source.parts):
            continue
        relative = source.relative_to(TEMPLATE_DIR)
        target_relative = Path(*(render(part, values) for part in relative.parts))
        target = destination / target_relative
        relative_label = target_relative.as_posix()

        if target.exists() and not force:
            skipped.append(relative_label)
            continue

        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            _write(source, target, values)
        written.append(relative_label)

    return Summary(
        destination=destination,
        package=package,
        written=written,
        skipped=skipped,
        dry_run=dry_run,
    )


def _write(source: Path, target: Path, values: dict[str, str]) -> None:
    payload = source.read_bytes()
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        target.write_bytes(payload)
        return
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render(text, values))


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos."""
    parser = argparse.ArgumentParser(
        prog="montar_pipeline.py",
        description="Monta el proyecto de captura y anuncios de nautilio.",
    )
    parser.add_argument("--empresa", required=True, help="Nombre legible de la empresa.")
    parser.add_argument("--dominio", required=True, help="Dominio del sitio (sin esquema).")
    parser.add_argument("--path", required=True, help="Carpeta destino del proyecto.")
    parser.add_argument(
        "--paquete",
        default=None,
        help="Nombre del paquete Python (por defecto, slug snake_case de la empresa).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Muestra que haria sin escribir.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribe archivos existentes (por defecto se omiten).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada del script."""
    args = build_parser().parse_args(argv)
    try:
        summary = montar(
            empresa=args.empresa,
            dominio=args.dominio,
            destination=Path(args.path).expanduser(),
            package=args.paquete,
            force=args.force,
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    prefix = "[dry-run] " if summary.dry_run else ""
    print(f"{prefix}Destino: {summary.destination}")
    print(f"{prefix}Paquete: {summary.package}")
    print(f"{prefix}Archivos escritos: {len(summary.written)}")
    for item in summary.written:
        print(f"  + {item}")
    if summary.skipped:
        print(f"Archivos omitidos (ya existian): {len(summary.skipped)}")
        for item in summary.skipped:
            print(f"  = {item}")
    if summary.dry_run:
        print("No se escribio nada. Repite sin --dry-run para aplicar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
