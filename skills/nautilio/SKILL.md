---
name: nautilio
description: "Nautilio guía tres viajes sobre los datos públicos de cualquier empresa. Il Viaggio cruza La Porta (robots.txt y términos), avanza con Il Passo, se detiene ante Caronte y lleva pocas páginas públicas por Inferno, Purgatorio y Paradiso: el Lete borra los datos personales y queda un corpus citable. Le Muse lee los anuncios públicos de una marca para inspirarse sin copiar. L'Eco mide lo que los motores de respuesta dicen de la marca: brief, matriz de preguntas, visibilidad, share of voice, citas y brechas frente al Paradiso. Úsala para preparar un corpus citable para RAG, auditar el enmascarado, analizar la pauta pública de una competencia o mejorar la visibilidad de una marca en asistentes de IA. No sirve para crawling masivo, redes sociales, áreas autenticadas, datos de menores ni para automatizar consultas a los motores."
license: MIT
allowed-tools: Read Write Edit Glob Grep WebFetch Bash(python:*) Bash(uv:*) Bash(make:*) Bash(git init:*) Bash(git status:*)
compatibility: "Requiere Python 3 (el script de montaje usa solo la biblioteca estándar). El proyecto generado usa uv y Python 3.13, y funciona en macOS, Linux y Windows. El transcriptor local es opcional (extra audio)."
metadata:
  author: Christian Trujillo
  version: "2.1"
---

# Nautilio — tres viajes por los datos públicos

> «Per me si va ne la città dei dati.»

Nautilio guía tres viajes sobre un mismo proyecto reproducible:

1. **Il Viaggio** lleva un conjunto **acotado** de páginas públicas desde el Inferno hasta el
   Paradiso. Al final queda un corpus citable y los datos personales se pierden en el Lete.
   Regla de oro: **primero La Porta, después la petición**.
2. **Le Muse** estudia los anuncios públicos de una marca o competencia para entender qué
   prueba y por qué. Lema: **«Inspírate, no copies»**.
3. **L'Eco** escucha lo que los motores de respuesta dicen de la marca: si la recomiendan,
   si la usan como fuente y dónde la dejan por fuera. Cada brecha se cruza con el Paradiso.

## Mapa del viaje

Cada nombre corresponde a una pieza técnica. La ruta aparece aquí una sola vez; el resto del
documento usa el nombre.

| Nombre | Qué es | Pieza técnica |
|--------|--------|---------------|
| **La Porta** | Revisión de `robots.txt` y de los términos de uso antes de la primera petición | `fetching.py` y `CONSTITUTION.md` |
| **Il Passo** | Una petición a la vez, con una pausa fija entre una y otra | 4 s en `REQUEST_DELAY_SECONDS` (`config.py`) |
| **Caronte** | El barquero que niega el paso: el lote se detiene ante `403` o `429` | `STOP_STATUS_CODES` (`config.py`) |
| **Inferno** | Payload crudo y manifiesto de la captura | `data/raw` |
| **Purgatorio** | Markdown limpio, sin menús ni pies de página | `data/processed` |
| **Lete** | El río del olvido: enmascarado de datos personales | `extracting.py` |
| **Registro del Lete** | Máscaras por archivo, por tipo y en total | `data/gold/inventario_enmascarado.json` |
| **Paradiso** | Documentos citables con front matter y `corpus.jsonl` | `data/gold` |
| **Limbo** | Páginas que solo cargan con JavaScript y esperan revisión humana | `requiere_js` en el manifiesto |
| **Il Giudizio** | Verificación completa antes de publicar | `make check` |
| **Le Muse** | Análisis de anuncios públicos | `make anuncios MARCA=<marca>` |
| **L'Eco** | Lo que los motores de respuesta dicen de la marca | `make eco MARCA=<marca> COMPETIDORES="a,b"` |
| **Il Ritratto** | El brief: contexto, foco y narrativa | `data/eco/ritratto.csv` |
| **Le Domande** | La matriz de preguntas | `data/eco/domande.csv` |
| **L'Ascolto** | Respuestas recogidas en los motores | `data/raw/eco/<marca>.jsonl` |
| **La Risposta** | Brechas cruzadas con el Paradiso | `data/gold/eco-<marca>.md` |

## Invocación

```text
@nautilio

Empresa:           <nombre legible, sin datos reales en el repositorio>
Dominio:           <dominio.com>
Semillas:          <lista corta de URL públicas, una por línea>
Marca competidora: <marca o página pública cuyos anuncios estudiará Le Muse>
Destino:           <carpeta del proyecto nuevo>
Paquete:           <opcional; por defecto, slug snake_case de la empresa>
Contacto:          <correo real de quien captura, nunca uno de la empresa>
Competidores:      <marcas contra las que la comparan, separadas por comas>
Productos:         <productos o categorías prioritarios para L'Eco>
Alcance:           <qué entra y qué queda fuera>
```

Si falta el contacto real, pídelo antes del **primer viaje real**: sin un `User-Agent`
identificable no hay `make capture`. El primer encuentro no lo necesita. Si no hay marca
competidora, Il Viaggio puede hacerse solo.

## El primer encuentro

Lo primero que ve la persona es el viaje completo, no un formulario. Apenas montes el
proyecto (paso 1 de Il Viaggio), corre:

```bash
uv sync
make demo
```

`make demo` levanta una ciudad de prueba en `127.0.0.1`, sin internet ni configuración, y
recorre los círculos con el mismo código del viaje real. Muestra, con cifras que cuenta el
código, cómo La Porta cierra una página prohibida, cómo Caronte detiene el viaje, cuánto borra
el Lete y qué llega al Paradiso. Le Muse lee además unos anuncios de muestra. Tarda unos
segundos y escribe en `data/demo/`, que git ignora.

Muestra esa salida tal cual y termina con el siguiente paso que ella misma propone: poner el
contacto, cambiar las semillas y correr `make capture`. No inventes cifras ni resumas lo que
la demo ya dice.

## Il Viaggio

### 1. Preparar la nave

```bash
python <SKILL_DIR>/scripts/montar_pipeline.py \
  --empresa "Empresa Demo" \
  --dominio ejemplo.com \
  --path ./empresa-demo
```

El script copia `assets/plantilla/`, renombra `src/paquete_plantilla/` y sustituye
`{{EMPRESA}}`, `{{DOMINIO}}`, `paquete_plantilla` y `{{FECHA}}`. Opciones:

- `--paquete <nombre>`: nombre del paquete Python; por defecto, el slug de la empresa.
- `--dry-run`: muestra qué escribiría, sin escribir nada.
- `--force`: sobrescribe archivos existentes; sin esta opción, los omite.

Después, dentro del proyecto: `uv sync` y `make demo` (ver «El primer encuentro»).

### 2. Elegir las semillas

Edita `src/<paquete>/config.py`:

- Entre 5 y 15 URL públicas, cada una con `id`, `titulo` y `categoria`.
- Nada de sitemaps completos ni descubrimiento de enlaces.
- Cada semilla cruza La Porta por separado.
- `CONTACTO` lleva el correo de **quien captura**, nunca uno del dominio de la empresa. Sin
  él, `make capture` no arranca.

### 3. La Porta

Antes de la primera petición, lee `robots.txt` y los términos de uso. Si `robots.txt` lo
permite pero los términos lo prohíben, no se entra: manda siempre el criterio más
restrictivo. Ante la duda, tampoco. La decisión y su motivo quedan en `CONSTITUTION.md`.

El pipeline vuelve a consultar `robots.txt` en cada origen antes de pedir una página. Si el
sitio declara una pausa mayor que Il Passo, sube Il Passo en `config.py` antes de capturar.

### 4. Il Passo y Caronte

```bash
make capture
```

- **Il Passo:** una petición a la vez, sin paralelizar y con la pausa fija entre peticiones.
- **Caronte:** ante `403` o `429` el lote se detiene. Las semillas restantes quedan sin
  intentar y esperan otra ejecución.
- El cliente se identifica con honestidad y nunca suplanta un navegador. El `User-Agent`
  lleva el contacto real de quien captura.
- Quedan fuera del proyecto los modos sigilosos, los proxies, la rotación de direcciones y
  cualquier intento de sortear un desafío de acceso. Una prueba de guardia recorre `src/` y
  falla si aparecen.

### 5. Inferno

Cada semilla deja una fila en el manifiesto, incluso si falla: fecha, estado, código HTTP,
SHA-256 y marca de Limbo. El payload crudo se queda en el Inferno y **no se versiona**; el
manifiesto sí.

### 6. Purgatorio y el Lete

`src/<paquete>/extracting.py` convierte HTML o PDF en Markdown limpio y lo sumerge en el Lete,
que borra:

- correos de personas;
- números de identificación;
- **todos** los celulares, incluidos los de tiendas y sucursales.

Solo sobreviven los correos del dominio institucional y los teléfonos fijos (`60x`); ambas
excepciones se apagan en `config.py`. Un celular de tienda se trata como personal salvo
prueba escrita de que es corporativo. El Registro del Lete anota cuántas máscaras hubo por
archivo, por tipo y en total.

### 7. Paradiso

Cada documento llega con front matter: `url_cita`, `fecha_captura`, `sha256`, `confianza`,
`posible_inyeccion` y `requiere_js`. `corpus.jsonl` tiene una fila por documento. El Paradiso
se versiona: es el contrato con quien consume el corpus.

### 8. Limbo

Nautilio **no abre navegador**. Si el HTML solo trae scripts y un contenedor de aplicación
casi vacío, la página queda en el Limbo y espera revisión humana. No se intenta sortear la
carga diferida.

### 9. Il Giudizio

```bash
make check
```

Además, revisa a mano:

- el Registro del Lete y que no queden datos personales en el Paradiso;
- que no haya copias completas de páginas;
- que las URL citadas sigan siendo públicas;
- que el repositorio sea privado si no hay autorización expresa;
- las páginas del Limbo, para decidir si se excluyen o se revisan.

## Le Muse

Lema: **«Inspírate, no copies»**. Le Muse estudia la pauta pública de una marca para entender
su mecanismo; nunca reutiliza sus piezas. El recorrido tiene cuatro pasos.

### Raccolta

La entrada es `data/raw/anuncios/<marca>.jsonl`, una fila por anuncio con estos campos:
`id`, `plataforma`, `pagina`, `fecha_inicio`, `formato`, `texto`, `titulo`, `cta`,
`url_destino`, `url_ficha`, `duracion_s` y `transcripcion` (opcional). Valores admitidos de
`plataforma`:

```text
meta | google
```

Recolecta una persona a mano en las bibliotecas públicas de anuncios de las plataformas, o el
agente con un conector autorizado. Solo anuncios activos y públicos. **Nunca se descargan
videos de forma automática.**

### Conteggio

```bash
make anuncios MARCA=<marca>
```

El código hace todas las cuentas y escribe `data/gold/inteligencia-anuncios-<marca>.md`, con
un enlace a cada `url_ficha`. Ninguna cifra sale de un modelo de lenguaje.

### Lettura

En cada creativo de video se leen el hook, el formato, el ángulo, el guion, el llamado a la
acción y los visuales. La plantilla de prompt y el esquema de salida están en
`references/le-muse.md`.

La transcripción es opcional y solo se hace con archivos locales que la persona tenga
derecho a usar. Requiere el extra de audio:

```bash
uv sync --extra audio
uv run <paquete> transcribir ruta/al/video.mp4 --idioma es
```

Si el extra falta, el comando explica cómo instalarlo.

### Ispirazione

De lo leído se extrae un mecanismo, no una pieza. La idea propia se escribe para la marca y
el público de quien la usa, se marca como hipótesis y se mide con datos propios.

## L'Eco

Lo que los motores de respuesta repiten de la marca. Una **mención** es cuando el motor la
recomienda; una **cita**, cuando usa una página de la marca como fuente. Detalle del método en
[`references/l-eco.md`](references/l-eco.md).

### Il Ritratto

```bash
make eco MARCA="<marca>"
```

La primera vez crea `data/eco/ritratto.csv` (el brief) y `data/eco/domande.csv` (la matriz
vacía). Llena el brief con lo que el Paradiso sostiene y **cita la `url_cita`** de cada dato. Lo
que el Paradiso no responde queda «por confirmar con <rol>». Nunca inventes un dato de negocio.

### Le Domande

Escribe en `domande.csv` entre 20 y 40 preguntas conversacionales que **no nombran la marca**,
más un set de marca que sí la nombra.

- Fórmula: situación + persona + restricciones.
- Orden: primero las de decisión, luego comparación y al final descubrimiento.
- Cada pregunta se conecta con un resultado de negocio; si no, se descarta.

`make eco` revisa estas reglas y lista lo que falte.

### L'Ascolto

La persona hace cada pregunta en los motores y guarda las respuestas en
`data/raw/eco/<marca>.jsonl` (`prompt_id`, `motor`, `fecha`, `respuesta`, `fuentes`). Un agente
solo puede hacerlo con una API autorizada. **No automatices el acceso a un motor ni inventes
respuestas.**

### La Risposta

```bash
make eco MARCA="<marca>" COMPETIDORES="rival uno,rival dos"
```

El código calcula visibilidad, share of voice, posición promedio, citas propias y sitios
citados, y lista las brechas. Para cada brecha dice si el Paradiso ya tiene una página
relacionada o si falta contenido. El reporte queda en `data/gold/eco-<marca>.md`. Muestra sus
cifras tal cual y propone qué página reforzar o escribir, con pruebas públicas y sin los claims
a evitar del Ritratto.

## Reglas no negociables

1. **La Porta primero.** `robots.txt` y términos de uso antes de capturar; ante la duda, no
   se entra.
2. **Il Passo siempre.** Una petición a la vez, con la pausa fija y sin paralelizar.
3. **Un contacto real en el `User-Agent`.** Es el de quien captura, nunca el de la empresa.
4. **Caronte manda.** Ante `403` o `429` el viaje se detiene y se retoma en otra ejecución.
5. **Sin formularios, sesiones ni endpoints autenticados.** Solo GET públicos.
6. **Sin recolección automatizada en redes sociales.**
7. **Sin sigilo.** El cliente se identifica con honestidad y nunca suplanta un navegador; sin
   proxies, rotación de direcciones ni desafíos sorteados.
8. **El Limbo no se fuerza.** Sin navegador para JavaScript; decide una persona.
9. **Repositorio privado por defecto.**
10. **Sin copias completas del sitio.** Solo fragmentos citables con su URL.
11. **Menores fuera del viaje.** Sus datos se descartan; no se enmascaran.
12. **Le Muse solo con datos públicos**, sin descargas automáticas que violen términos.
13. **Inspírate, no copies.** No se reutiliza texto, guion, voz, imagen ni visual ajeno.
14. **L'Eco escucha, no automatiza.** Las respuestas las recoge una persona o una API
    autorizada; nunca se inventan ni se sacan con un robot.

## Lista de Il Giudizio

- [ ] La Porta cruzada: `robots.txt` y términos de uso revisados y documentados en
      `CONSTITUTION.md`.
- [ ] `CONTACTO` con el correo real de quien captura.
- [ ] Il Passo activo y una petición a la vez.
- [ ] Caronte verificado ante `403` y `429`.
- [ ] Cliente honesto: no suplanta un navegador; sin herramientas sigilosas, proxies ni
      navegador en `src/`.
- [ ] Sin formularios, sesiones, endpoints autenticados ni redes sociales.
- [ ] Semillas acotadas y justificadas (5–15).
- [ ] Manifiesto del Inferno con fecha, estado, SHA-256 y marca de Limbo por semilla.
- [ ] Celulares de tienda borrados en el Lete; correos institucionales y fijos `60x` según la
      configuración elegida.
- [ ] `corpus.jsonl` y Registro del Lete generados.
- [ ] Páginas del Limbo revisadas a mano.
- [ ] Le Muse con datos públicos y reporte sin cifras inventadas.
- [ ] Il Ritratto con la fuente de cada dato o «por confirmar».
- [ ] Le Domande sin avisos de `make eco` y cada pregunta con resultado de negocio.
- [ ] L'Ascolto con respuestas reales y el reporte de L'Eco generado por el código.
- [ ] `make check` en verde.
- [ ] Repositorio privado y sin copias completas del sitio.

## Referencias

| Archivo | Contenido |
|---------|-----------|
| [`references/etica-y-legal.md`](references/etica-y-legal.md) | La Porta: `robots.txt`, términos de uso, Ley 1581 de 2012, menores y redes sociales. |
| [`references/enmascarado.md`](references/enmascarado.md) | El Lete: qué borra, qué sobrevive y la lección de los celulares de tienda. |
| [`references/tre-regni.md`](references/tre-regni.md) | Inferno, Purgatorio y Paradiso: qué guarda cada reino y qué se versiona. |
| [`references/le-muse.md`](references/le-muse.md) | Raccolta, Conteggio, Lettura e Ispirazione: JSONL, prompt de análisis y reglas. |
| [`references/l-eco.md`](references/l-eco.md) | Il Ritratto, Le Domande, L'Ascolto y La Risposta: menciones, citas y brechas. |
