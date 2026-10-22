"""Pruebas de la orquestacion medallon con un fetcher falso (sin red)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from paquete_plantilla.config import Seed
from paquete_plantilla.fetching import FetchResult, PoliteFetcher
from paquete_plantilla.pipeline import capture, collect_status

HTML = """
<html><head><title>Quienes somos</title></head>
<body><main>
  <h1>Quienes somos</h1>
  <p>Somos una empresa de ejemplo.</p>
  <p>Contacto: ventas@{{DOMINIO}}, persona@gmail.com.</p>
  <p>Celular: +57 313 424 5231.</p>
</main></body>
</html>
"""


class FakeFetcher:
    """Fetcher determinista que sirve contenido fijo por semilla."""

    def __init__(self, results: dict[str, FetchResult]) -> None:
        self.results = results
        self.stopped = False
        self.stop_reason = ""

    def fetch(self, seed: Seed) -> FetchResult:
        return self.results[seed.id]


def _seed(seed_id: str, url: str) -> Seed:
    return Seed(id=seed_id, url=url, titulo=seed_id, categoria="prueba")


def _fixed_now() -> datetime:
    return datetime(2026, 10, 22, 12, 0, tzinfo=UTC)


def test_captura_escribe_las_tres_capas_el_corpus_y_el_inventario(tmp_path: Path) -> None:
    # Arrange
    ok_seed = _seed("quienes-somos", "https://{{DOMINIO}}/quienes-somos")
    missing_seed = _seed("blog", "https://{{DOMINIO}}/blog")
    results = {
        "quienes-somos": FetchResult(
            seed=ok_seed,
            status="ok",
            http_status=200,
            content=HTML.encode(),
            content_type="text/html; charset=UTF-8",
            content_kind="html",
            robots_allowed=True,
        ),
        "blog": FetchResult(
            seed=missing_seed,
            status="missing",
            http_status=404,
            robots_allowed=True,
        ),
    }
    fetcher = cast(PoliteFetcher, FakeFetcher(results))

    # Act
    report = capture(
        seeds=[ok_seed, missing_seed],
        fetcher=fetcher,
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
        gold_dir=tmp_path / "gold",
        manifest_path=tmp_path / "raw" / "manifest.json",
        corpus_path=tmp_path / "gold" / "corpus.jsonl",
        inventory_path=tmp_path / "gold" / "inventario_enmascarado.json",
        now=_fixed_now,
    )

    # Assert
    assert report.counts.bronze == 1
    assert report.counts.silver == 1
    assert report.counts.gold == 1
    assert report.statuses["ok"] == 1
    assert report.statuses["missing"] == 1

    bronze = tmp_path / "raw" / "quienes-somos.html"
    assert bronze.is_file()
    silver = (tmp_path / "processed" / "quienes-somos.md").read_text(encoding="utf-8")
    assert "ventas@{{DOMINIO}}" in silver
    assert "persona@gmail.com" not in silver
    assert "313 424 5231" not in silver
    assert "[correo enmascarado]" in silver
    assert "[telefono enmascarado]" in silver

    gold = (tmp_path / "gold" / "quienes-somos.md").read_text(encoding="utf-8")
    assert gold.startswith("---\n")
    assert 'url_cita: "https://{{DOMINIO}}/quienes-somos"' in gold
    assert 'confianza: "no_confiable"' in gold
    assert "posible_inyeccion: false" in gold

    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["semillas"] == 2
    assert manifest["politica"]["retardo_segundos"] == 4.0
    assert len(manifest["entradas"]) == 2
    assert manifest["entradas"][0]["fetched_at"] == "2026-10-22T12:00:00+00:00"
    assert len(manifest["entradas"][0]["sha256"]) == 64
    assert manifest["entradas"][1]["status"] == "missing"

    lines = (tmp_path / "gold" / "corpus.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["id"] == "quienes-somos"
    assert record["confianza"] == "no_confiable"
    assert record["posible_inyeccion"] is False

    inventory = json.loads(
        (tmp_path / "gold" / "inventario_enmascarado.json").read_text(encoding="utf-8")
    )
    assert inventory["por_tipo"] == {"correo": 1, "telefono": 1, "identificacion": 0}
    assert inventory["por_archivo"]["quienes-somos.md"]["correo"] == 1
    assert inventory["total"] == 2


def test_marca_requiere_js_en_el_manifiesto(tmp_path: Path) -> None:
    # Arrange
    seed = _seed("panel", "https://{{DOMINIO}}/panel")
    shell = '<html><body><div id="root"></div><script src="/app.js"></script></body></html>'
    results = {
        "panel": FetchResult(
            seed=seed,
            status="ok",
            http_status=200,
            content=shell.encode(),
            content_type="text/html",
            content_kind="html",
            robots_allowed=True,
        )
    }
    fetcher = cast(PoliteFetcher, FakeFetcher(results))

    # Act
    report = capture(
        seeds=[seed],
        fetcher=fetcher,
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
        gold_dir=tmp_path / "gold",
        manifest_path=tmp_path / "raw" / "manifest.json",
        corpus_path=tmp_path / "gold" / "corpus.jsonl",
        inventory_path=tmp_path / "gold" / "inventario_enmascarado.json",
        now=_fixed_now,
    )

    # Assert
    assert report.requiere_js == 1
    assert report.entries[0].requiere_js is True
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["entradas"][0]["requiere_js"] is True
    assert manifest["politica"]["scrapling_impersonate"] is None
    assert manifest["politica"]["scrapling_stealthy_headers"] is False


def test_status_cuenta_los_archivos_de_cada_capa(tmp_path: Path) -> None:
    # Arrange
    seed = _seed("quienes-somos", "https://{{DOMINIO}}/quienes-somos")
    results = {
        "quienes-somos": FetchResult(
            seed=seed,
            status="ok",
            content=HTML.encode(),
            content_type="text/html",
            content_kind="html",
            robots_allowed=True,
        )
    }
    fetcher = cast(PoliteFetcher, FakeFetcher(results))
    dirs = {
        "raw_dir": tmp_path / "raw",
        "processed_dir": tmp_path / "processed",
        "gold_dir": tmp_path / "gold",
        "manifest_path": tmp_path / "raw" / "manifest.json",
        "corpus_path": tmp_path / "gold" / "corpus.jsonl",
        "inventory_path": tmp_path / "gold" / "inventario_enmascarado.json",
    }
    capture(seeds=[seed], fetcher=fetcher, now=_fixed_now, **dirs)

    # Act
    status = collect_status(
        raw_dir=dirs["raw_dir"],
        processed_dir=dirs["processed_dir"],
        gold_dir=dirs["gold_dir"],
        manifest_path=dirs["manifest_path"],
    )

    # Assert
    assert status.manifest_exists is True
    assert status.counts.bronze == 1
    assert status.counts.silver == 1
    assert status.counts.gold == 1
    assert status.statuses["ok"] == 1
