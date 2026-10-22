"""Orquestacion de Il Viaggio: del Inferno al Purgatorio y de ahi al Paradiso."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paquete_plantilla import config
from paquete_plantilla.config import (
    CONFIANZA,
    CORPUS_PATH,
    DOMINIO,
    GOLD_DIR,
    INVENTORY_PATH,
    MANIFEST_PATH,
    PROCESSED_DIR,
    RAW_DIR,
    REQUEST_DELAY_SECONDS,
    Seed,
)
from paquete_plantilla.extracting import detect_requires_js, extract_html, extract_pdf
from paquete_plantilla.fetching import FetchResult, PoliteFetcher
from paquete_plantilla.gold import write_corpus, write_gold, write_inventory


@dataclass(frozen=True, slots=True)
class LayerCounts:
    """Documentos presentes en el Inferno, el Purgatorio y el Paradiso."""

    bronze: int = 0
    silver: int = 0
    gold: int = 0


@dataclass(slots=True)
class ManifestEntry:
    """Fila del manifiesto del Inferno."""

    id: str
    url: str
    titulo: str
    categoria: str
    prioridad: str
    status: str
    http_status: int | None = None
    content_type: str = ""
    size_bytes: int = 0
    sha256: str = ""
    robots_allowed: bool | None = None
    bronze_path: str | None = None
    silver_path: str | None = None
    gold_path: str | None = None
    fetched_at: str | None = None
    requiere_js: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serializa la entrada a un diccionario JSON-compatible."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CorpusRecord:
    """Fila de ``corpus.jsonl`` (Paradiso)."""

    id: str
    titulo: str
    url_cita: str
    categoria: str
    prioridad: str
    fecha_captura: str
    confianza: str
    posible_inyeccion: bool
    sha256: str
    content_type: str
    ruta_gold: str
    caracteres: int
    requiere_js: bool

    def to_dict(self) -> dict[str, Any]:
        """Serializa el registro a un diccionario JSON-compatible."""
        return asdict(self)


@dataclass(slots=True)
class CaptureReport:
    """Resultado agregado de una captura."""

    entries: list[ManifestEntry] = field(default_factory=list)
    counts: LayerCounts = field(default_factory=LayerCounts)
    statuses: Counter[str] = field(default_factory=Counter)
    requiere_js: int = 0
    manifest_path: Path = MANIFEST_PATH
    corpus_path: Path = CORPUS_PATH
    inventory_path: Path = INVENTORY_PATH
    inventory: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StatusReport:
    """Estado leido desde el manifiesto y el disco."""

    manifest_exists: bool
    seeds: int
    counts: LayerCounts
    statuses: Counter[str] = field(default_factory=Counter)
    requiere_js: int = 0


def capture(
    seeds: Sequence[Seed] = config.SEEDS,
    fetcher: PoliteFetcher | None = None,
    raw_dir: Path = RAW_DIR,
    processed_dir: Path = PROCESSED_DIR,
    gold_dir: Path = GOLD_DIR,
    manifest_path: Path = MANIFEST_PATH,
    corpus_path: Path = CORPUS_PATH,
    inventory_path: Path = INVENTORY_PATH,
    now: Callable[[], datetime] | None = None,
) -> CaptureReport:
    """Captura las semillas y llena los tres reinos, el corpus y el Registro del Lete."""
    for directory in (raw_dir, processed_dir, gold_dir):
        directory.mkdir(parents=True, exist_ok=True)

    clock = now or (lambda: datetime.now(UTC))
    client = fetcher or PoliteFetcher()
    entries: list[ManifestEntry] = []
    records: list[CorpusRecord] = []
    documents: dict[str, str] = {}

    for seed in seeds:
        entry = ManifestEntry(
            id=seed.id,
            url=seed.url,
            titulo=seed.titulo,
            categoria=seed.categoria,
            prioridad=seed.prioridad,
            status="not_attempted",
        )
        if client.stopped:
            entry.error = client.stop_reason
            entries.append(entry)
            continue

        result = client.fetch(seed)
        _apply_result(entry, result)

        if result.content is None:
            entries.append(entry)
            continue

        fetched_at = clock().isoformat(timespec="seconds")
        entry.fetched_at = fetched_at
        digest = hashlib.sha256(result.content).hexdigest()
        entry.sha256 = digest
        entry.size_bytes = len(result.content)

        extension = "pdf" if result.content_kind == "pdf" else "html"
        bronze_path = raw_dir / f"{seed.id}.{extension}"
        _write_bytes(bronze_path, result.content)
        entry.bronze_path = _relative(bronze_path)

        try:
            if result.content_kind == "pdf":
                document = extract_pdf(result.content, fallback_title=seed.titulo)
            else:
                document = extract_html(
                    result.content,
                    seed.url,
                    fallback_title=seed.titulo,
                )
        except Exception as exc:
            entry.status = "extract_error"
            entry.error = f"{type(exc).__name__}: {exc}"
            entries.append(entry)
            continue

        entry.requiere_js = result.content_kind == "html" and detect_requires_js(
            result.content, document.markdown
        )

        silver_path = processed_dir / f"{seed.id}.md"
        _write_text(silver_path, document.markdown + "\n")
        entry.silver_path = _relative(silver_path)

        gold_path = gold_dir / f"{seed.id}.md"
        metadata: dict[str, Any] = {
            "id": seed.id,
            "titulo": seed.titulo,
            "url_cita": seed.url,
            "categoria": seed.categoria,
            "prioridad": seed.prioridad,
            "fuente": DOMINIO,
            "fecha_captura": fetched_at,
            "content_type": result.content_type,
            "sha256": digest,
            "confianza": CONFIANZA,
            "posible_inyeccion": document.posible_inyeccion,
            "requiere_js": entry.requiere_js,
            "ruta_bronze": entry.bronze_path,
            "ruta_silver": entry.silver_path,
            "ruta_gold": _relative(gold_path),
        }
        write_gold(gold_path, metadata, document.markdown)
        entry.gold_path = _relative(gold_path)

        documents[f"{seed.id}.md"] = document.markdown
        records.append(
            CorpusRecord(
                id=seed.id,
                titulo=seed.titulo,
                url_cita=seed.url,
                categoria=seed.categoria,
                prioridad=seed.prioridad,
                fecha_captura=fetched_at,
                confianza=CONFIANZA,
                posible_inyeccion=document.posible_inyeccion,
                sha256=digest,
                content_type=result.content_type,
                ruta_gold=_relative(gold_path),
                caracteres=len(document.markdown),
                requiere_js=entry.requiere_js,
            )
        )
        entries.append(entry)

    write_corpus(corpus_path, (record.to_dict() for record in records))
    _write_manifest(manifest_path, entries, len(seeds), clock)
    inventory = write_inventory(inventory_path, documents)

    return CaptureReport(
        entries=entries,
        counts=LayerCounts(
            bronze=sum(1 for entry in entries if entry.bronze_path),
            silver=sum(1 for entry in entries if entry.silver_path),
            gold=sum(1 for entry in entries if entry.gold_path),
        ),
        statuses=Counter(entry.status for entry in entries),
        requiere_js=sum(1 for entry in entries if entry.requiere_js),
        manifest_path=manifest_path,
        corpus_path=corpus_path,
        inventory_path=inventory_path,
        inventory=inventory,
    )


def collect_status(
    raw_dir: Path = RAW_DIR,
    processed_dir: Path = PROCESSED_DIR,
    gold_dir: Path = GOLD_DIR,
    manifest_path: Path = MANIFEST_PATH,
) -> StatusReport:
    """Cuenta documentos en disco y estados del manifiesto."""
    manifest = _read_manifest(manifest_path)
    entries = manifest.get("entradas", []) if manifest else []
    statuses = Counter(str(entry.get("status", "")) for entry in entries)
    return StatusReport(
        manifest_exists=manifest is not None,
        seeds=int(manifest.get("semillas", len(entries))) if manifest else 0,
        counts=LayerCounts(
            bronze=_count_files(raw_dir, exclude={"manifest.json"}),
            silver=_count_files(processed_dir),
            gold=_count_files(gold_dir, exclude={"corpus.jsonl", "inventario_enmascarado.json"}),
        ),
        statuses=statuses,
        requiere_js=sum(1 for entry in entries if entry.get("requiere_js")),
    )


def read_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any] | None:
    """Lee el manifiesto del Inferno, si existe."""
    return _read_manifest(path)


def _apply_result(entry: ManifestEntry, result: FetchResult) -> None:
    entry.status = result.status
    entry.http_status = result.http_status
    entry.content_type = result.content_type
    entry.robots_allowed = result.robots_allowed
    entry.error = result.error


def _write_manifest(
    path: Path,
    entries: Iterable[ManifestEntry],
    seeds: int,
    clock: Callable[[], datetime],
) -> None:
    payload = {
        "generado_en": clock().isoformat(timespec="seconds"),
        "semillas": seeds,
        "politica": {
            "user_agent": config.USER_AGENT,
            "retardo_segundos": REQUEST_DELAY_SECONDS,
            "respeta_robots": True,
            "parada_http": sorted(config.STOP_STATUS_CODES),
            "scrapling_impersonate": None,
            "scrapling_stealthy_headers": False,
            "sin_navegador": True,
            "requiere_js_revision_humana": True,
        },
        "entradas": [entry.to_dict() for entry in entries],
    }
    _write_json(path, payload)


def _read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def _count_files(directory: Path, exclude: set[str] | None = None) -> int:
    if not directory.exists():
        return 0
    skipped = exclude or set()
    return sum(1 for path in directory.iterdir() if path.is_file() and path.name not in skipped)


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(config.PROJECT_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()
