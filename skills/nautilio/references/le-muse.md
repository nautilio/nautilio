# Le Muse: inspiración a partir de anuncios públicos

> Lema: **«Inspírate, no copies»**. Un hook ajeno se estudia para entender su mecanismo; no
> se reutiliza su texto, su guion ni su visual.

Le Muse busca entender **qué prueba** una marca con su pauta pública. Trabaja solo
con datos de las bibliotecas públicas de anuncios de las plataformas, y todas las cifras las
calcula el código. El recorrido tiene cuatro pasos: **Raccolta**, **Conteggio**, **Lettura**
e **Ispirazione**.

## 1. Raccolta: la recolección permitida

1. Abre la biblioteca pública de anuncios de cada plataforma y busca la página o el
   anunciante de la marca. Toma solo anuncios **activos** del país y el idioma que interesan.
2. Registra una fila por anuncio en `data/raw/anuncios/<marca>.jsonl` (dentro del Inferno).
3. La recolección la hace una persona a mano en el navegador o un agente con un conector
   autorizado que respete los términos de la plataforma.
4. **Nunca descargues videos de forma automática.** Si necesitas la transcripción, usa un
   archivo local que tengas derecho a usar y el comando `transcribir` con el extra `audio`.

### Campos del JSONL

| Campo | Obligatorio | Notas |
|-------|-------------|-------|
| `id` | Sí | Único dentro del archivo. |
| `plataforma` | Sí | Uno de los valores admitidos (ver el bloque siguiente). |
| `pagina` | No | Nombre público de la página o del anunciante. |
| `fecha_inicio` | No | `YYYY-MM-DD` si la plataforma lo muestra. |
| `formato` | No | `imagen`, `video`, `carrusel`, etc. |
| `texto` | No | Texto principal del anuncio. |
| `titulo` | No | Titular o encabezado. |
| `cta` | No | Llamado a la acción tal como aparece. |
| `url_destino` | No | URL final del anuncio. |
| `url_ficha` | No | Enlace público a la ficha del anuncio. |
| `duracion_s` | No | Duración del video en segundos. |
| `transcripcion` | No | Texto hablado, si lo tienes de forma lícita. |

Valores admitidos de `plataforma`:

```text
meta | google
```

Ejemplo con datos ficticios (en el archivo, cada anuncio ocupa una sola línea):

| Campo | Ejemplo |
|---|---|
| `id` | `demo-001` |
| `plataforma` | `meta` |
| `pagina` | `Empresa Demo` |
| `fecha_inicio` | `2026-01-01` |
| `formato` | `video` |
| `texto` | `Tu rutina puede ser mas simple.` |
| `titulo` | `Empresa Demo` |
| `cta` | `Comprar` |
| `url_destino` | `https://ejemplo.com/producto` |
| `url_ficha` | `https://biblioteca-anuncios.example/ficha/demo-001` |
| `duracion_s` | `15` |
| `transcripcion` | `Tu rutina puede ser mas simple. Empieza hoy.` |

## 2. Conteggio: las cuentas las hace el código

```bash
make anuncios MARCA=<marca>
```

El comando lee el JSONL, resume la pauta en cifras y escribe
`data/gold/inteligencia-anuncios-<marca>.md` (en el Paradiso), con un enlace a cada
`url_ficha`. Ninguna cifra se pide a un modelo de lenguaje: si un número no sale del JSONL y
del reporte, no existe.

## 3. Lettura: la lectura de cada video

Para cada creativo de video, estudia:

| Dimensión | Pregunta |
|-----------|----------|
| **Hook** | ¿Qué dice o muestra al inicio para detener el scroll? |
| **Formato** | ¿Talking head, demo, UGC, testimonio, animación, pantalla dividida? |
| **Ángulo** | ¿Dolor, deseo, prueba social, precio, urgencia, curiosidad, comparación? |
| **Guion** | ¿Cómo encadena hook, problema, solución, prueba y cierre? |
| **CTA** | ¿Qué acción pide y en qué momento aparece? |
| **Visuales** | ¿Planos, texto en pantalla, ritmo, música, subtítulos, colores? |

### Plantilla de prompt para el agente

Úsala solo sobre el JSONL ya recolectado. El agente **no inventa** anuncios, cifras ni
fichas: si un dato falta, escribe `null` y lo señala.

Instrucción inicial:

```text
Eres analista de performance marketing. Trabaja SOLO con los anuncios del archivo
adjunto. No busques datos nuevos, no descargues videos y no inventes cifras.
Devuelve un objeto JSON por creativo único, con la forma del esquema.
```

Cada objeto de la respuesta lleva estos campos:

| Campo | Qué va |
|---|---|
| `id` | id representativo del grupo de anuncios |
| `url_ficha` | ficha pública del anuncio; obligatoria |
| `plataforma` | `meta` o `google` |
| `formato` | `imagen`, `video`, `carrusel` u otro |
| `hook` | lo que detiene el scroll, o `null` |
| `angulo` | dolor, deseo, prueba social, precio, urgencia, curiosidad, comparación u otro |
| `guion` | lista corta de pasos del anuncio |
| `cta` | llamado a la acción textual, o `null` |
| `visuales` | lista de planos o recursos visuales |
| `duracion_s` | número o `null` |
| `evidencia` | cita textual breve del anuncio que sustenta el análisis |

Reglas que acompañan la instrucción:

1. Un objeto por creativo único; no repitas el mismo texto.
2. Cita siempre `url_ficha`. Si no existe, usa `null` y explica por qué.
3. No completes datos faltantes con suposiciones.
4. No copies el anuncio: describe su mecanismo.
5. Excluye cualquier anuncio dirigido a menores o con datos de menores.
6. Devuelve solo el arreglo JSON, sin markdown ni comentarios.

## 4. Ispirazione: de la lectura a una idea propia

1. Elige un mecanismo, no una pieza: por ejemplo, «una demostración corta con texto en
   pantalla».
2. Escribe un hook original para tu marca y tu público.
3. Cambia el visual, el ángulo y el CTA; conserva solo la estructura que quieres probar.
4. Marca la idea como hipótesis y mídela con tus propios datos.
5. Nunca publiques una pieza que reproduzca texto, voz, imagen o guion de otra marca.

## 5. Reglas no negociables

- Solo datos públicos de las bibliotecas de anuncios.
- Sin descargas automáticas de videos de ninguna plataforma.
- Sin sortear muros de acceso, inicios de sesión ni términos de uso.
- Menores excluidos: si aparecen, se descartan y no se analizan.
- Inspírate, no copies: el reporte es para aprender, no para plagiar.
- Toda afirmación cuantitativa sale del JSONL y del reporte determinista.
