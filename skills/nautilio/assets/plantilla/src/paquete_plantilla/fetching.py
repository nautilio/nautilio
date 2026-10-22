"""Cliente HTTP etico: La Porta (robots.txt), Il Passo y Caronte (parada ante 403/429)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from curl_cffi.requests.exceptions import RequestException
from scrapling.fetchers import FetcherSession

from paquete_plantilla.config import (
    MAX_BYTES,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    STOP_STATUS_CODES,
    USER_AGENT,
    Seed,
)


class SessionLike(Protocol):
    """Minimo de una sesion HTTP que el cliente necesita."""

    def get(self, url: str, **kwargs: Any) -> Any:
        """Hace un GET y devuelve una respuesta con ``status``, ``body`` y ``headers``."""


@dataclass(frozen=True, slots=True)
class FetchResult:
    """Resultado de una solicitud HTTP a una semilla."""

    seed: Seed
    status: str
    http_status: int | None = None
    content: bytes | None = None
    content_type: str = ""
    content_kind: str = ""
    robots_allowed: bool | None = None
    error: str = ""


def opciones_sesion() -> dict[str, Any]:
    """Opciones de la sesion HTTP.

    El cliente se identifica con honestidad, con el contacto real de quien captura, y
    nunca suplanta un navegador. No se configuran intermediarios ni rotacion de
    direcciones.
    """
    return {
        "impersonate": None,
        "stealthy_headers": False,
        "headers": {"User-Agent": USER_AGENT},
        "timeout": REQUEST_TIMEOUT_SECONDS,
        "retries": 1,
    }


class PoliteFetcher:
    """Descarga semillas tras cruzar La Porta (robots.txt) y con Il Passo entre peticiones."""

    def __init__(
        self,
        session: SessionLike | None = None,
        delay_seconds: float = REQUEST_DELAY_SECONDS,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._session = session
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: float | None = None
        self._robots: dict[str, RobotFileParser | None] = {}
        self.stopped = False
        self.stop_reason = ""

    def fetch(self, seed: Seed) -> FetchResult:
        """Descarga una semilla y devuelve un resultado sin lanzar excepciones."""
        if self.stopped:
            return FetchResult(seed=seed, status="not_attempted", error=self.stop_reason)

        allowed, robots_reason = self._robots_allows(seed.url)
        if self.stopped:
            return FetchResult(
                seed=seed, status="stopped", robots_allowed=False, error=robots_reason
            )
        if not allowed:
            return FetchResult(
                seed=seed, status="robots_blocked", robots_allowed=False, error=robots_reason
            )

        self._wait()
        try:
            response = self._get(
                seed.url,
                accept="text/html,application/pdf,*/*",
            )
        except RequestException as exc:
            self._last_request_at = self._clock()
            return FetchResult(
                seed=seed,
                status="network_error",
                robots_allowed=True,
                error=f"{type(exc).__name__}: {exc}",
            )
        finally:
            self._last_request_at = self._clock()

        status = int(response.status)
        # Caronte niega el paso: el lote se detiene y el resto de semillas espera.
        if status in STOP_STATUS_CODES:
            self.stopped = True
            self.stop_reason = f"HTTP {status} en {seed.url}"
            return FetchResult(
                seed=seed,
                status="stopped",
                http_status=status,
                robots_allowed=True,
                error=self.stop_reason,
            )
        if status in {404, 410}:
            return FetchResult(seed=seed, status="missing", http_status=status, robots_allowed=True)
        if status >= 400:
            return FetchResult(
                seed=seed,
                status="http_error",
                http_status=status,
                robots_allowed=True,
                error=f"HTTP {status}",
            )

        content = _response_body(response)
        if len(content) > MAX_BYTES:
            return FetchResult(
                seed=seed,
                status="too_large",
                http_status=status,
                robots_allowed=True,
                error=f"{len(content)} bytes supera el limite de {MAX_BYTES}",
            )

        content_type = str(response.headers.get("Content-Type", ""))
        return FetchResult(
            seed=seed,
            status="ok",
            http_status=status,
            content=content,
            content_type=content_type,
            content_kind=_detect_kind(seed.url, content_type, content),
            robots_allowed=True,
        )

    def _get(self, url: str, accept: str) -> Any:
        headers = {"User-Agent": USER_AGENT, "Accept": accept}
        if self._session is not None:
            return self._session.get(url, timeout=self.timeout_seconds, headers=headers)
        with FetcherSession(**opciones_sesion()) as session:
            return session.get(url, timeout=self.timeout_seconds, headers=headers)

    def _robots_allows(self, url: str) -> tuple[bool, str]:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = self._load_robots(origin)
        parser = self._robots[origin]
        if parser is None:
            return False, f"robots.txt inaccesible para {origin}"
        return parser.can_fetch(USER_AGENT, url), f"robots.txt de {origin}"

    def _load_robots(self, origin: str) -> RobotFileParser | None:
        robots_url = f"{origin}/robots.txt"
        self._wait()
        try:
            response = self._get(robots_url, accept="text/plain,*/*")
        except RequestException:
            return None
        finally:
            self._last_request_at = self._clock()

        status = int(response.status)
        if status in STOP_STATUS_CODES:
            self.stopped = True
            self.stop_reason = f"HTTP {status} en {robots_url}"
            return None
        if status in {401, 403}:
            return None
        if status in {404, 410}:
            parser = RobotFileParser()
            parser.parse([])
            return parser
        if status >= 400:
            return None

        parser = RobotFileParser()
        parser.parse(_response_text(response).splitlines())
        return parser

    def _wait(self) -> None:
        if self._last_request_at is None or self.delay_seconds <= 0:
            return
        elapsed = self._clock() - self._last_request_at
        remaining = self.delay_seconds - elapsed
        if remaining > 0:
            self._sleep(remaining)


def _response_body(response: Any) -> bytes:
    body = getattr(response, "body", None)
    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        return body.encode("utf-8")
    content = getattr(response, "content", None)
    if isinstance(content, bytes):
        return content
    if isinstance(content, str):
        return content.encode("utf-8")
    return b""


def _response_text(response: Any) -> str:
    # En el cliente HTTP de la plantilla, `.text` es el texto visible del DOM y llega vacio
    # en un robots.txt; por eso primero se decodifica el cuerpo crudo.
    body = _response_body(response)
    if body:
        return body.decode("utf-8", errors="replace")
    text = getattr(response, "text", None)
    return text if isinstance(text, str) else ""


def _detect_kind(url: str, content_type: str, content: bytes) -> str:
    lowered_type = content_type.lower()
    lowered_url = url.lower()
    if "pdf" in lowered_type or lowered_url.split("?")[0].endswith(".pdf"):
        return "pdf"
    if "html" in lowered_type or content.lstrip().startswith((b"<!doctype", b"<html")):
        return "html"
    return "unsupported"
