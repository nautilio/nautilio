SHELL := /bin/bash

.DEFAULT_GOAL := help
.PHONY: help install demo capture status anuncios eco cronaca lint format-check test check clean

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Prepara el entorno del proyecto
	uv sync

demo: ## Viaje de prueba sin internet: el primer encuentro con Nautilio
	uv run paquete_plantilla demo

capture: ## Il Viaggio: captura las semillas y llena Inferno, Purgatorio y Paradiso
	uv run paquete_plantilla capture

status: ## Cuenta los documentos del Inferno, el Purgatorio y el Paradiso
	uv run paquete_plantilla status

anuncios: ## Le Muse: analiza los anuncios de una marca (MARCA=<marca>)
	uv run paquete_plantilla anuncios "$(MARCA)"

eco: ## L'Eco: lo que los motores dicen de la marca (MARCA=<marca> COMPETIDORES="a,b")
	uv run paquete_plantilla eco "$(MARCA)" --competidores "$(COMPETIDORES)"

cronaca: ## La Cronaca: el viaje contado para personas (MARCA= opcional para L'Eco)
	uv run paquete_plantilla cronaca --marca "$(MARCA)" --competidores "$(COMPETIDORES)"

lint: ## Ejecuta el linter del proyecto
	uv run ruff check .

format-check: ## Verifica el formato sin modificarlo
	uv run ruff format --check .

test: ## Ejecuta las pruebas
	uv run pytest

check: lint format-check test ## Il Giudizio: lint, formato y pruebas antes de publicar

clean: ## Limpia caches y artefactos
	rm -rf .pytest_cache .ruff_cache dist build
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
