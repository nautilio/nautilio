# I tre regni: Inferno, Purgatorio y Paradiso

Il Viaggio atraviesa tres reinos. Cada uno responde una pregunta distinta y tiene su propia
política de versionado. La regla es simple: **se versiona lo que se puede auditar sin exponer
el crudo ni los datos personales**.

| Reino | Ruta |
|-------|------|
| Inferno | `data/raw` |
| Purgatorio | `data/processed` |
| Paradiso | `data/gold` |

## Inferno: la evidencia

**Pregunta:** ¿qué se descargó exactamente y cuándo?

- Payload original tal como llegó: HTML, PDF o JSON.
- `manifest.json` con una fila por semilla, incluso si falló.
- Cada fila: `id`, `url`, `titulo`, `categoria`, `prioridad`, `status`, `http_status`,
  `content_type`, `size_bytes`, `sha256`, `robots_allowed`, `requiere_js`, `fetched_at`, la
  ruta del documento en cada reino y `error` si aplica.
- `politica`: `User-Agent`, Il Passo, respeto a La Porta, códigos de Caronte y la constancia
  de que el cliente no suplanta un navegador ni abre uno.
- Si el HTML solo muestra un contenedor de aplicación y el texto extraído es casi vacío, la
  página entra al Limbo (`requiere_js: true`) para revisión humana. No se abre un navegador.

**Se versiona:** solo el manifiesto. El crudo puede contener datos personales, pesar mucho y
cambiar sin control. Se guarda en local y se puede reconstruir.

## Purgatorio: el texto que se purifica

**Pregunta:** ¿cuál es el texto útil, sin adornos de página y sin datos personales?

- Markdown limpio: encabezados, párrafos, listas, tablas y enlaces.
- Se eliminan scripts, estilos, navegación, encabezado, pie, formularios, modales, avisos de
  cookies y texto oculto.
- El texto cruza el Lete: se borran correos de personas, identificaciones y todos los
  celulares.
- Solo sobreviven las excepciones configuradas: correos institucionales y fijos `60x`.
- Se marca `posible_inyeccion` si el texto contiene instrucciones dirigidas a un modelo.

**Se versiona:** no. Es intermedio y se regenera desde el Inferno.

## Paradiso: el contrato de consumo

**Pregunta:** ¿qué documento citable consume el buscador o el RAG?

- Un Markdown por semilla con front matter YAML: `id`, `titulo`, `url_cita`, `categoria`,
  `prioridad`, `fuente`, `fecha_captura`, `content_type`, `sha256`, `confianza`,
  `posible_inyeccion`, `requiere_js` y rutas.
- `corpus.jsonl`: una fila JSON por documento con los mismos campos y el conteo de caracteres.
- Registro del Lete (`inventario_enmascarado.json`): máscaras por archivo, por tipo y total.

**Se versiona:** sí. Es el contrato con quien consume el corpus. Cambiar su forma es un cambio
incompatible y se documenta en `CONSTITUTION.md`.

## El recorrido

```text
semilla pública
   │  La Porta + Il Passo (Caronte vigila)
   ▼
Inferno: payload + manifiesto (fecha, estado, hash)
   │  extracción sin red
   ▼
Purgatorio: Markdown limpio que cruzó el Lete
   │  front matter + índice
   ▼
Paradiso: documentos citables + corpus.jsonl + Registro del Lete
```

## Por qué no todo sube al Paradiso

- **Privacidad:** el Inferno y el Purgatorio pueden contener datos personales antes o después
  del Lete; el crudo nunca se publica.
- **Peso:** los payloads crecen rápido y no aportan valor a quien consume el corpus.
- **Reproducibilidad:** el manifiesto conserva URL, fecha y SHA-256; con la misma política se
  puede repetir la captura y verificar si el contenido cambió.
- **Auditoría:** el Registro del Lete demuestra qué se tapó y cuánto, sin exponer el dato
  original.

## Il Giudizio antes de publicar

1. `make check` en verde.
2. Registro del Lete revisado: totales coherentes y sin archivos faltantes.
3. Ninguna copia completa de una página.
4. Repositorio privado si no hay autorización expresa del titular del sitio.
