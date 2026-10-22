"""Pruebas del cliente HTTP educado, sin tocar la red."""

from __future__ import annotations

from typing import Any

from paquete_plantilla.config import Seed
from paquete_plantilla.fetching import PoliteFetcher, opciones_sesion

DOMINIO = "{{DOMINIO}}"
BASE = f"https://{DOMINIO}"

ROBOTS_ALLOW = "User-agent: *\nDisallow:\n"
ROBOTS_BLOCK = "User-agent: *\nDisallow: /privado\n"


class FakeResponse:
    """Respuesta HTTP minima para las pruebas."""

    def __init__(
        self,
        status: int = 200,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self.body = body
        self.headers = headers or {}

    @property
    def text(self) -> str:
        """Texto decodificado de la respuesta."""
        return self.body.decode("utf-8", errors="replace")


class FakeSession:
    """Sesion HTTP falsa: devuelve respuestas por URL y registra las llamadas."""

    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Devuelve la respuesta preparada para ``url``."""
        self.calls.append(url)
        return self.responses[url]


def _seed(url: str) -> Seed:
    return Seed(id="prueba", url=url, titulo="Prueba", categoria="prueba")


def test_permite_la_descarga_cuando_robots_la_autoriza() -> None:
    # Arrange
    url = f"{BASE}/quienes-somos"
    session = FakeSession(
        {
            f"{BASE}/robots.txt": FakeResponse(body=ROBOTS_ALLOW.encode()),
            url: FakeResponse(body=b"<html>ok</html>", headers={"Content-Type": "text/html"}),
        }
    )
    fetcher = PoliteFetcher(session=session, delay_seconds=0, sleep=lambda _: None)

    # Act
    result = fetcher.fetch(_seed(url))

    # Assert
    assert result.status == "ok"
    assert result.content_kind == "html"
    assert result.robots_allowed is True
    assert session.calls == [f"{BASE}/robots.txt", url]


def test_bloquea_la_descarga_cuando_robots_lo_prohibe() -> None:
    # Arrange
    url = f"{BASE}/privado/interno"
    session = FakeSession(
        {
            f"{BASE}/robots.txt": FakeResponse(body=ROBOTS_BLOCK.encode()),
        },
    )
    fetcher = PoliteFetcher(session=session, delay_seconds=0, sleep=lambda _: None)

    # Act
    result = fetcher.fetch(_seed(url))

    # Assert
    assert result.status == "robots_blocked"
    assert result.robots_allowed is False
    assert session.calls == [f"{BASE}/robots.txt"]


class RespuestaDelClienteHTTP(FakeResponse):
    """Como el cliente real: `.text` es el texto visible y llega vacio en un robots.txt."""

    @property
    def text(self) -> str:
        """Texto visible del DOM (vacio para texto plano)."""
        return ""


def test_bloquea_con_robots_aunque_text_llegue_vacio_como_en_el_cliente_real() -> None:
    # Arrange
    url = f"{BASE}/privado/interno"
    session = FakeSession(
        {
            f"{BASE}/robots.txt": RespuestaDelClienteHTTP(
                body=ROBOTS_BLOCK.encode(),
            ),
        }
    )
    fetcher = PoliteFetcher(session=session, delay_seconds=0, sleep=lambda _: None)

    # Act
    result = fetcher.fetch(_seed(url))

    # Assert
    assert result.status == "robots_blocked"
    assert session.calls == [f"{BASE}/robots.txt"]


def test_lee_content_type_sin_distinguir_mayusculas() -> None:
    # Arrange: el cliente HTTP real entrega las cabeceras en minuscula.
    url = f"{BASE}/quienes-somos"
    session = FakeSession(
        {
            f"{BASE}/robots.txt": FakeResponse(body=ROBOTS_ALLOW.encode()),
            url: FakeResponse(
                body=b"<html>ok</html>", headers={"content-type": "text/html; charset=utf-8"}
            ),
        }
    )
    fetcher = PoliteFetcher(session=session, delay_seconds=0, sleep=lambda _: None)

    # Act
    result = fetcher.fetch(_seed(url))

    # Assert
    assert result.content_type == "text/html; charset=utf-8"
    assert result.content_kind == "html"


def test_para_el_lote_ante_403_o_429() -> None:
    # Arrange
    url = f"{BASE}/blog"
    session = FakeSession(
        {
            f"{BASE}/robots.txt": FakeResponse(body=ROBOTS_ALLOW.encode()),
            url: FakeResponse(status=429),
        }
    )
    fetcher = PoliteFetcher(session=session, delay_seconds=0, sleep=lambda _: None)

    # Act
    first = fetcher.fetch(_seed(url))
    second = fetcher.fetch(_seed(f"{BASE}/sostenibilidad"))

    # Assert
    assert first.status == "stopped"
    assert first.http_status == 429
    assert fetcher.stopped is True
    assert second.status == "not_attempted"
    assert session.calls == [f"{BASE}/robots.txt", url]


def test_registra_url_inexistente_y_continua() -> None:
    # Arrange
    missing = f"{BASE}/no-existe"
    working = f"{BASE}/quienes-somos"
    session = FakeSession(
        {
            f"{BASE}/robots.txt": FakeResponse(body=ROBOTS_ALLOW.encode()),
            missing: FakeResponse(status=404),
            working: FakeResponse(body=b"<html>ok</html>", headers={"Content-Type": "text/html"}),
        }
    )
    fetcher = PoliteFetcher(session=session, delay_seconds=0, sleep=lambda _: None)

    # Act
    first = fetcher.fetch(_seed(missing))
    second = fetcher.fetch(_seed(working))

    # Assert
    assert first.status == "missing"
    assert second.status == "ok"
    assert fetcher.stopped is False


def test_respeta_el_intervalo_minimo_entre_solicitudes() -> None:
    # Arrange
    url = f"{BASE}/quienes-somos"
    session = FakeSession(
        {
            f"{BASE}/robots.txt": FakeResponse(body=ROBOTS_ALLOW.encode()),
            url: FakeResponse(body=b"<html>ok</html>", headers={"Content-Type": "text/html"}),
        }
    )
    instants = iter([100.0, 100.5, 100.5, 100.5])
    slept: list[float] = []
    fetcher = PoliteFetcher(
        session=session,
        delay_seconds=4,
        sleep=slept.append,
        clock=lambda: next(instants),
    )

    # Act
    fetcher.fetch(_seed(url))

    # Assert
    assert slept == [3.5]


def test_opciones_de_sesion_no_suplantan_ni_son_sigilosas() -> None:
    # Arrange
    opciones = opciones_sesion()

    # Act
    impersonate = opciones["impersonate"]
    stealthy_headers = opciones["stealthy_headers"]

    # Assert
    assert impersonate is None
    assert stealthy_headers is False
    assert "User-Agent" in opciones["headers"]
    assert opciones["retries"] == 1
