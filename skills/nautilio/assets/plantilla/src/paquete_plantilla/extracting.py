"""Purgatorio: extraccion de HTML/PDF a Markdown y paso por el Lete (enmascarado)."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag
from pypdf import PdfReader

from paquete_plantilla.config import (
    CONSERVAR_CORREOS_INSTITUCIONALES,
    CONSERVAR_TELEFONOS_FIJOS,
    DOMINIO,
    PREFIJOS_TELEFONO_FIJO,
)

MASK_CORREO = "[correo enmascarado]"
MASK_TELEFONO = "[telefono enmascarado]"
MASK_IDENTIFICACION = "[identificacion enmascarada]"

CHROME_TAGS = frozenset(
    {
        "script",
        "style",
        "noscript",
        "iframe",
        "svg",
        "form",
        "nav",
        "header",
        "footer",
        "aside",
        "button",
        "input",
        "select",
        "textarea",
        "canvas",
        "template",
    }
)
BLOCK_CONTAINERS = frozenset(
    {"div", "section", "article", "main", "figure", "figcaption", "dl", "dt", "dd"}
)
HEADING_LEVELS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
ID_RE = re.compile(
    r"(?i)\b(c\.?c\.?|c[eé]dula|nit|pasaporte)\s*(?:n[.º°o]*)?\s*[:#-]?\s*([\d.\-]{5,15})"
)
PHONE_RE = re.compile(
    r"(?i)"
    r"(?P<labeled>\b(?:tel[eé]fono|tel\.?|celular|m[oó]vil|whatsapp|fax)\b\s*:?\s*)"
    r"(?P<labeled_number>\+?\(?\d[\d\s().-]{3,18}\d)"
    r"|(?<!\d)(?P<international>(?:\+\s?57|\(\s*\+\s?57\s*\))[\s.-]?"
    r"(?:\(\s*\d{1,3}\s*\)[\s.-]?)?\d{3}[\s.-]?\d{3}[\s.-]?\d{4})(?!\d)"
    r"|(?<!\d)(?P<area>\(\s*60\d\s*\)\s*\d{3}[\s.-]?\d{4})(?!\d)"
    r"|(?<!\d)(?P<spaced_cell>3\d{2}[\s.-]\d{3}[\s.-]\d{4})(?!\d)"
    r"|(?<!\d)(?P<spaced_landline>60\d[\s.-]\d{3}[\s.-]\d{4})(?!\d)"
    r"|(?<!\w)(?P<bare_cell>3\d{9})(?![\d@])"
    r"|(?<!\w)(?P<bare_landline>60\d{8})(?![\d@])"
)
PHONE_GROUPS = (
    "labeled_number",
    "international",
    "area",
    "spaced_cell",
    "spaced_landline",
    "bare_cell",
    "bare_landline",
)

INJECTION_PATTERNS = (
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
    r"disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions",
    r"ignora\s+(?:todas\s+)?las\s+instrucciones",
    r"olvida\s+(?:todas\s+)?las\s+instrucciones",
    r"system\s+prompt",
    r"prompt\s+del\s+sistema",
    r"jailbreak",
    r"act[uú]a\s+como\s+(?:un|una)\s+(?:asistente|modelo)",
    r"revela\s+(?:tu|las)\s+instrucciones",
)
INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

MIN_CONTENT_CHARS = 200
JS_APP_ROOT_RE = re.compile(
    r"""id=["'](?:root|app|__next|__nuxt|svelte|ng-app)["']""",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """Texto extraido y senales de confianza."""

    titulo: str
    markdown: str
    posible_inyeccion: bool = False


def extract_html(html: str | bytes, url: str, fallback_title: str = "") -> ExtractedDocument:
    """Convierte HTML ya descargado en Markdown limpio y enmascarado."""
    soup = BeautifulSoup(html, "lxml")
    title = _extract_title(soup, fallback_title)

    for node in list(soup.find_all(CHROME_TAGS)):
        if not node.decomposed:
            node.decompose()

    root = _content_root(soup)
    for node in list(root.find_all(True)):
        if not node.decomposed and _is_hidden(node):
            node.decompose()

    blocks: list[str] = []
    _walk(root, url, blocks)
    body = mask_personal_data(_normalize_blocks(blocks))
    return ExtractedDocument(
        titulo=title,
        markdown=body,
        posible_inyeccion=detect_injection(body),
    )


def extract_pdf(data: bytes, fallback_title: str = "") -> ExtractedDocument:
    """Extrae texto de un PDF ya descargado, sin consultar la red."""
    reader = PdfReader(io.BytesIO(data))
    metadata_title = ""
    if reader.metadata is not None and reader.metadata.title:
        metadata_title = str(reader.metadata.title).strip()

    pages: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        normalized = _normalize_pdf_text(text)
        if normalized:
            pages.append(f"<!-- p. {index} -->\n\n{normalized}")

    body = mask_personal_data("\n\n".join(pages))
    return ExtractedDocument(
        titulo=metadata_title or fallback_title,
        markdown=body,
        posible_inyeccion=detect_injection(body),
    )


def mask_personal_data(
    text: str,
    *,
    keep_institutional_emails: bool | None = None,
    keep_landlines: bool | None = None,
) -> str:
    """El Lete: enmascara correos, identificaciones y telefonos.

    Los celulares se enmascaran siempre. Solo se conservan los correos del dominio
    institucional y los telefonos fijos (``60x``), y ambas excepciones se pueden
    desactivar desde ``config.py`` o con los argumentos de esta funcion.
    """
    keep_email = (
        CONSERVAR_CORREOS_INSTITUCIONALES
        if keep_institutional_emails is None
        else keep_institutional_emails
    )
    keep_fixed = CONSERVAR_TELEFONOS_FIJOS if keep_landlines is None else keep_landlines

    masked = EMAIL_RE.sub(
        _keep_institutional_email if keep_email else (lambda _match: MASK_CORREO), text
    )
    masked = ID_RE.sub(
        lambda match: f"{match.group(1)} {MASK_IDENTIFICACION}",
        masked,
    )
    return PHONE_RE.sub(lambda match: _mask_phone(match, keep_fixed), masked)


def count_masks(text: str) -> dict[str, int]:
    """Cuenta las mascaras presentes en un texto, por tipo."""
    return {
        "correo": text.count(MASK_CORREO),
        "telefono": text.count(MASK_TELEFONO),
        "identificacion": text.count(MASK_IDENTIFICACION),
    }


def detect_injection(text: str) -> bool:
    """Marca texto con instrucciones dirigidas a un modelo de lenguaje."""
    return bool(INJECTION_RE.search(text))


def detect_requires_js(html: str | bytes, markdown: str) -> bool:
    """Limbo: heuristica para paginas que solo muestran contenido con JavaScript.

    No se abre un navegador: si el HTML trae scripts y el texto extraido es casi
    vacio (o el documento solo contiene un contenedor de aplicacion), la pagina
    queda en el Limbo para revision humana.
    """
    visible = markdown.strip()
    if len(visible) >= MIN_CONTENT_CHARS:
        return False
    raw = html.decode("utf-8", errors="replace") if isinstance(html, bytes) else html
    if "<script" not in raw.lower():
        return False
    if len(visible) < 20:
        return True
    return bool(JS_APP_ROOT_RE.search(raw))


def _keep_institutional_email(match: re.Match[str]) -> str:
    domain = match.group(0).rsplit("@", 1)[-1].lower().strip(".")
    if domain == DOMINIO or domain.endswith(f".{DOMINIO}"):
        return match.group(0)
    return MASK_CORREO


def _mask_phone(match: re.Match[str], keep_landlines: bool) -> str:
    label = match.group("labeled")
    if keep_landlines and _is_landline(_phone_digits(match)):
        return match.group(0)
    if label:
        return label + MASK_TELEFONO
    return MASK_TELEFONO


def _phone_digits(match: re.Match[str]) -> str:
    for group in PHONE_GROUPS:
        value = match.group(group)
        if value:
            return re.sub(r"\D", "", value)
    return ""


def _is_landline(digits: str) -> bool:
    national = digits[2:] if len(digits) == 12 and digits.startswith("57") else digits
    if len(national) not in {7, 10}:
        return False
    return national.startswith(PREFIJOS_TELEFONO_FIJO)


def _extract_title(soup: BeautifulSoup, fallback: str) -> str:
    heading = soup.find("h1")
    if heading is not None:
        text = _clean_inline(heading.get_text(" ", strip=True))
        if text:
            return text
    if soup.title is not None:
        text = _clean_inline(soup.title.get_text(" ", strip=True))
        if text:
            return text
    return fallback


def _content_root(soup: BeautifulSoup) -> Tag:
    for candidate in (
        soup.find("main"),
        soup.find("article"),
        soup.select_one('[role="main"]'),
        soup.body,
    ):
        if isinstance(candidate, Tag):
            return candidate
    return soup


def _is_hidden(tag: Tag) -> bool:
    if tag.has_attr("hidden"):
        return True
    if str(tag.get("aria-hidden", "")).lower() == "true":
        return True
    style = str(tag.get("style", "")).replace(" ", "").lower()
    if "display:none" in style or "visibility:hidden" in style:
        return True
    raw_classes = tag.get("class")
    if isinstance(raw_classes, str):
        classes = raw_classes.lower()
    elif raw_classes is None:
        classes = ""
    else:
        classes = " ".join(str(item) for item in raw_classes).lower()
    return any(token in classes for token in ("cookie", "modal", "popup", "overlay"))


def _walk(node: Tag, base_url: str, blocks: list[str]) -> None:
    buffer: list[str] = []

    def flush() -> None:
        text = _clean_inline(" ".join(buffer))
        if text:
            blocks.append(text)
        buffer.clear()

    for child in node.children:
        if isinstance(child, NavigableString):
            buffer.append(str(child))
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name.lower()
        if name in CHROME_TAGS or _is_hidden(child):
            continue

        if name in HEADING_LEVELS:
            flush()
            text = _inline(child, base_url)
            if text:
                blocks.append(f"{'#' * HEADING_LEVELS[name]} {text}")
        elif name == "p":
            flush()
            text = _inline(child, base_url)
            if text:
                blocks.append(text)
        elif name in {"ul", "ol"}:
            flush()
            _list_block(child, base_url, blocks, ordered=name == "ol")
        elif name == "table":
            flush()
            blocks.extend(_table_block(child, base_url))
        elif name == "blockquote":
            flush()
            text = _inline(child, base_url)
            if text:
                blocks.append(f"> {text}")
        elif name == "pre":
            flush()
            text = child.get_text("\n", strip=True)
            if text:
                blocks.append(f"```\n{text}\n```")
        elif name in BLOCK_CONTAINERS:
            flush()
            _walk(child, base_url, blocks)
        else:
            buffer.append(_inline(child, base_url))

    flush()


def _inline(node: Tag, base_url: str) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name.lower()
        if name in CHROME_TAGS or _is_hidden(child):
            continue
        if name == "br":
            parts.append("\n")
        elif name == "a":
            label = _inline(child, base_url)
            href = str(child.get("href", "")).strip()
            if not label:
                continue
            lowered = href.lower()
            if href and not lowered.startswith(("javascript:", "#", "data:")):
                parts.append(f"[{label}]({urljoin(base_url, href)})")
            else:
                parts.append(label)
        elif name in {"strong", "b"}:
            parts.append(f"**{_inline(child, base_url)}**")
        elif name in {"em", "i"}:
            parts.append(f"*{_inline(child, base_url)}*")
        elif name == "code":
            parts.append(f"`{_inline(child, base_url)}`")
        else:
            parts.append(_inline(child, base_url))
    return _clean_inline("".join(parts))


def _list_block(node: Tag, base_url: str, blocks: list[str], ordered: bool) -> None:
    for index, item in enumerate(node.find_all("li", recursive=False), start=1):
        marker = f"{index}." if ordered else "-"
        text = _clean_inline(_inline(_without_nested_lists(item), base_url))
        if text:
            blocks.append(f"{marker} {text}")
        for nested in item.find_all(["ul", "ol"], recursive=False):
            _list_block(nested, base_url, blocks, ordered=nested.name == "ol")


def _without_nested_lists(item: Tag) -> Tag:
    clone = BeautifulSoup(str(item), "lxml")
    for nested in clone.find_all(["ul", "ol"]):
        nested.decompose()
    body = clone.body
    return body if isinstance(body, Tag) else clone


def _table_block(table: Tag, base_url: str) -> list[str]:
    rows: list[list[str]] = []
    for row in table.find_all("tr"):
        cells = [
            _inline(cell, base_url).replace("|", "\\|")
            for cell in row.find_all(["th", "td"], recursive=False)
        ]
        if any(cells):
            rows.append(cells)
    if not rows:
        return []

    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(normalized[0]) + " |"]
    lines.append("| " + " | ".join(["---"] * width) + " |")
    for row in normalized[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return ["\n".join(lines)]


def _clean_inline(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def _normalize_blocks(blocks: list[str]) -> str:
    cleaned: list[str] = []
    for block in blocks:
        text = block.strip()
        if not text:
            continue
        if cleaned and cleaned[-1] == text:
            continue
        cleaned.append(text)
    return "\n\n".join(cleaned)


def _normalize_pdf_text(text: str) -> str:
    paragraphs: list[str] = []
    buffer: list[str] = []
    for raw_line in text.replace("\xa0", " ").splitlines():
        line = raw_line.strip()
        if not line:
            if buffer:
                paragraphs.append(" ".join(buffer))
                buffer.clear()
            continue
        buffer.append(line)
    if buffer:
        paragraphs.append(" ".join(buffer))
    return "\n\n".join(paragraphs)
