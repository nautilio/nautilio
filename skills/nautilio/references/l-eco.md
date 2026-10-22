# L'Eco

Lo que los motores de respuesta repiten de la marca. La búsqueda ya no entrega diez enlaces:
entrega una respuesta. En esa respuesta hay dos formas de estar presente:

- **Mención:** el motor nombra la marca como recomendación o alternativa. Genera demanda y
  pesa más cuando la persona compara y decide.
- **Cita:** el motor usa una página de la marca como fuente. Construye autoridad, sobre todo
  en preguntas informativas, y abre el camino a la mención.

L'Eco trabaja en cuatro pasos. Los dos primeros los escribe el agente con la persona; los
dos últimos los cuenta el código.

## 1. Il Ritratto

`make eco MARCA=<marca>` crea `data/eco/ritratto.csv` con tres bloques:

| Bloque | Componentes |
|---|---|
| 1. Contexto del negocio | Descripción, mercados e idiomas, canales actuales, objetivos, lo que los motores ya saben de la marca |
| 2. Foco | Productos o categorías prioritarios, personas, casos de uso, competidores y alternativas, transacción, etapa prioritaria |
| 3. Narrativa para los motores | Atributos y diferenciadores, pruebas y evidencia, cómo queremos ser descritos, claims a evitar |

Cada fila trae quién la responde, qué significa y las preguntas que ayudan a llenarla.

- El agente llena lo que el Paradiso permite sostener y **cita la `url_cita`** de cada dato.
- Lo que el Paradiso no responde queda como «por confirmar con <rol>».
- Nunca se inventa un dato de negocio.

## 2. Le Domande

`data/eco/domande.csv` es la matriz de preguntas, con estas columnas:

| Columna | Qué va |
|---|---|
| `id` | identificador corto: `c1`, `c2`… para el set conversacional y `m1`… para el de marca |
| `set` | `conversacional` (sin nombrar la marca) o `marca` (con la marca) |
| `etapa` | `decision`, `comparacion` o `descubrimiento` |
| `producto` | producto o categoría prioritaria del Ritratto |
| `persona` | quién pregunta, con sus palabras |
| `situacion` | la necesidad o el problema |
| `restricciones` | presupuesto, lugar, tiempo, tamaño, uso |
| `prompt` | la pregunta completa, como la haría una persona |
| `insumo` | de dónde salió: ventas, soporte, foros, buscadores, el propio Paradiso |
| `resultado_negocio` | qué venta, segmento o meta mueve; sin esto la pregunta es ruido |

Reglas:

- **Entre 20 y 40 preguntas conversacionales**, que no nombran la marca: miden si el motor la
  recomienda por su cuenta frente a sus competidores.
- **Un set de marca aparte**, que sí la nombra: audita qué dice el motor de ella. No mide
  visibilidad; controla la narrativa.
- **Fórmula:** situación + persona + restricciones. Sin restricciones, el motor responde con
  definiciones y no recomienda marcas.
- **De abajo hacia arriba:** primero las preguntas de decisión, luego comparación y al final
  descubrimiento.
- **Regla de oro:** cada pregunta se conecta con un resultado de negocio; si no, se descarta.

`make eco` revisa estas reglas y lista lo que falte.

## 3. L'Ascolto

Las respuestas se guardan en `data/raw/eco/<marca>.jsonl`, una línea por respuesta:

| Campo | Qué va |
|---|---|
| `prompt_id` | el `id` de Le Domande |
| `motor` | el motor consultado, con un nombre genérico que la persona elija |
| `fecha` | día de la consulta |
| `respuesta` | el texto completo de la respuesta |
| `fuentes` | lista de URL que el motor mostró como fuente |

Las recoge una persona en cada motor, o un agente con una API autorizada. **Nunca se
automatiza el acceso a un motor** ni se inventa una respuesta.

Con ese archivo, `make eco MARCA=<marca> COMPETIDORES="a,b"` calcula, sin modelo de
lenguaje:

- **Visibilidad:** preguntas conversacionales donde aparece la marca, sobre las que tienen
  respuesta.
- **Share of voice:** menciones de la marca sobre todas las menciones de la marca y sus
  competidores.
- **Posición promedio:** lugar en que aparece la marca cuando aparece.
- **Citas propias:** respuestas que usan el sitio de la marca como fuente.
- **Sitios citados:** los dominios que más usan los motores para la categoría.

## 4. La Risposta

Una **brecha** es una pregunta donde aparece un competidor y la marca no aparece ni como
mención ni como cita. Para cada brecha, el código busca en el Paradiso la página más
relacionada:

- Si existe, la brecha es de distribución: la página ya responde, pero el motor no la usa.
  Se refuerza esa página.
- Si no existe, falta contenido. Se escribe una página propia que responda la pregunta con
  pruebas públicas y sin los claims a evitar del Ritratto.

La relación entre pregunta y página es una coincidencia de palabras, no un juicio semántico:
una persona confirma cada caso antes de actuar.

## Qué entrega

- `data/eco/ritratto.csv`: el brief, con su fuente en cada dato.
- `data/eco/domande.csv`: la matriz de preguntas.
- `data/gold/eco-<marca>.md`: visibilidad, share of voice, posición, citas, sitios citados,
  brechas con su Risposta y lo que los motores dicen de la marca.
