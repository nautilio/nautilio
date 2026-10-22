"""Prueba de guardia: el codigo no incorpora herramientas sigilosas."""

from __future__ import annotations

from pathlib import Path

FORBIDDEN = (
    "StealthyFetcher",
    "StealthySession",
    "solve_cloudflare",
    "proxy",
    "proxies",
)


def test_src_no_contiene_herramientas_sigilosas() -> None:
    # Arrange
    root = Path(__file__).resolve().parents[1] / "src"
    offenders: list[str] = []

    # Act
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN:
            if token.lower() in text:
                offenders.append(f"{path.relative_to(root).as_posix()}: {token}")

    # Assert
    assert offenders == []
