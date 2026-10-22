"""Interfaz de linea de comandos: Il Viaggio (captura), estado y Le Muse (anuncios)."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from paquete_plantilla import config, eco
from paquete_plantilla.anuncios import cargar_anuncios, reporte_markdown, resumen
from paquete_plantilla.demo import narrar, recorrer
from paquete_plantilla.pipeline import capture, collect_status
from paquete_plantilla.transcribir import transcribir_archivo


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada de la CLI."""
    parser = argparse.ArgumentParser(
        prog="paquete_plantilla",
        description="Il Viaggio y Le Muse para {{EMPRESA}}: captura etica y anuncios.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "demo",
        help="Viaje de prueba sin internet en una ciudad local: el primer encuentro",
    )
    subparsers.add_parser(
        "capture",
        help="Il Viaggio: captura las semillas y llena Inferno, Purgatorio y Paradiso",
    )
    subparsers.add_parser(
        "status", help="Cuenta los documentos del Inferno, el Purgatorio y el Paradiso"
    )

    anuncios_parser = subparsers.add_parser(
        "anuncios",
        help="Le Muse: genera el reporte de anuncios de una marca desde data/raw/anuncios/",
    )
    anuncios_parser.add_argument("marca", help="Marca o competidor con JSONL en data/raw/anuncios/")

    eco_parser = subparsers.add_parser(
        "eco",
        help="L'Eco: brief, preguntas y escucha de lo que los motores dicen de la marca",
    )
    eco_parser.add_argument("marca", help="Nombre de la marca tal como la nombran los clientes")
    eco_parser.add_argument("--competidores", default="", help="Competidores separados por comas")

    transcribir_parser = subparsers.add_parser(
        "transcribir",
        help="Transcribe un archivo local con el transcriptor opcional (extra audio)",
    )
    transcribir_parser.add_argument("archivo", help="Ruta a un archivo de audio o video local")
    transcribir_parser.add_argument("--modelo", default="small", help="Modelo del transcriptor")
    transcribir_parser.add_argument(
        "--idioma", default=None, help="Codigo de idioma, por ejemplo es"
    )

    args = parser.parse_args(argv)
    if args.command == "demo":
        narrar(recorrer())
        return 0
    if args.command == "capture":
        return _capture()
    if args.command == "anuncios":
        return _anuncios(args.marca)
    if args.command == "eco":
        return _eco(args.marca, args.competidores)
    if args.command == "transcribir":
        return _transcribir(Path(args.archivo), args.modelo, args.idioma)
    return _status()


def _capture() -> int:
    if not config.CONTACTO:
        print("Falta CONTACTO en config.py: pon tu correo antes de capturar.")
        print("Para ver el viaje completo sin configurar nada, corre: make demo")
        return 2
    delay = config.REQUEST_DELAY_SECONDS
    print(f"Il Viaggio: {len(config.SEEDS)} semillas, Il Passo de {delay:.0f} s por solicitud...")
    report = capture()
    counts = report.counts
    print(f"Inferno: {counts.bronze}  Purgatorio: {counts.silver}  Paradiso: {counts.gold}")
    for status, total in sorted(report.statuses.items()):
        print(f"  {status}: {total}")
    if report.requiere_js:
        print(
            f"Limbo: {report.requiere_js} pagina(s) requieren JavaScript y esperan "
            "revision humana. La skill no abre navegador."
        )
    print(f"Manifiesto: {report.manifest_path}")
    print(f"Corpus: {report.corpus_path}")
    print(f"Registro del Lete: {report.inventory_path}")
    print(f"  mascaras totales: {report.inventory.get('total', 0)}")
    return 0


def _status() -> int:
    report = collect_status()
    if not report.manifest_exists:
        print("No hay manifiesto. Ejecuta `make capture` primero.")
        return 1

    print(f"Semillas en el manifiesto: {report.seeds}")
    counts = report.counts
    print(f"Inferno: {counts.bronze}  Purgatorio: {counts.silver}  Paradiso: {counts.gold}")
    for status, total in sorted(report.statuses.items()):
        print(f"  {status}: {total}")
    if report.requiere_js:
        print(f"En el Limbo (requieren JavaScript y revision humana): {report.requiere_js}")
    return 0


def _anuncios(marca: str) -> int:
    if not marca:
        print("Falta MARCA. Usa: make anuncios MARCA=<marca>.")
        return 2
    if Path(marca).name != marca or marca in {".", ".."}:
        print("Marca invalida: usa un nombre simple, sin rutas.")
        return 2
    entrada = config.ANUNCIOS_DIR / f"{marca}.jsonl"
    if not entrada.is_file():
        print(f"No existe {entrada}. Agrega el JSONL publico de la marca antes de continuar.")
        return 1

    try:
        anuncios = cargar_anuncios(entrada)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2
    destino = config.GOLD_DIR / f"inteligencia-anuncios-{marca}.md"
    reporte_markdown(anuncios, marca, destino)
    datos = resumen(anuncios)
    print(f"Anuncios: {datos['total']}  unicos: {datos['unicos']}")
    print(f"Repetidos: {datos['porcentaje_repetido']:.2f} %")
    for formato, total in datos["por_formato"].items():
        print(f"  formato {formato}: {total}")
    for dominio, total in datos["por_dominio"].items():
        print(f"  destino {dominio}: {total}")
    for cta, total in datos["por_cta"].items():
        print(f"  CTA {cta}: {total}")
    print(f"Reporte: {destino}")
    return 0


def _transcribir(archivo: Path, modelo: str, idioma: str | None) -> int:
    try:
        texto = transcribir_archivo(archivo, modelo=modelo, idioma=idioma)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}")
        return 2
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def _eco(marca: str, competidores: str) -> int:
    if not marca.strip():
        print('Falta la marca: make eco MARCA=<marca> COMPETIDORES="rival uno,rival dos"')
        return 2
    if eco.escribir_ritratto():
        print(f"Il Ritratto: plantilla del brief en {eco.RITRATTO_PATH}")
    if eco.escribir_domande():
        print(f"Le Domande: matriz vacia en {eco.DOMANDE_PATH}")
    pendientes = eco.ritratto_pendiente()
    if pendientes:
        print(f"Il Ritratto: faltan {len(pendientes)} componentes por responder.")

    preguntas = eco.cargar_domande()
    validacion = eco.validar_domande(preguntas, marca)
    print(f"Le Domande: {validacion['total']} preguntas {validacion['por_set']}")
    for problema in validacion["problemas"]:
        print(f"  - {problema}")

    ruta = eco.ruta_respuestas(marca)
    if not ruta.exists():
        print(f"L'Ascolto: aun no hay respuestas. Recogelas en {ruta} (una linea por respuesta).")
        return 0
    rivales = [c.strip() for c in competidores.split(",") if c.strip()]
    escucha = eco.escuchar(
        preguntas,
        eco.cargar_respuestas(ruta),
        marca,
        config.DOMINIO,
        rivales,
        eco.leer_corpus(config.CORPUS_PATH),
    )
    reporte = eco.reporte_markdown(
        marca,
        escucha,
        validacion,
        eco.respuestas_de_marca(preguntas, eco.cargar_respuestas(ruta)),
    )
    print(
        f"L'Ascolto: la marca aparece en {escucha['visibles']} de {escucha['con_respuesta']} "
        f"preguntas ({escucha['visibilidad']} %); share of voice {escucha['share_of_voice']} %"
    )
    print(
        f"La Risposta: {len(escucha['brechas'])} brechas; el Paradiso ya responde "
        f"{escucha['cubiertas']}"
    )
    print(f"Reporte: {reporte}")
    return 0
