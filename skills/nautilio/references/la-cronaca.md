# La Cronaca

El informe que la persona abre al final del viaje: `data/gold/cronaca.html`, en tinta sobre
papel, que se lee en cualquier navegador y se imprime como PDF. `make cronaca MARCA=<marca>`
lo arma con lo que hay en el proyecto.

## La regla de oro: primero la idea

La Cronaca no es un inventario. Abre con **la idea en una frase**, una conclusión con punto de
vista que dice qué está en juego, y con **la historia en tres minutos**: tres frases que alguien
podría decir de pie en una reunión. Después vienen la tensión (lo que dicen los asistentes), la
evidencia (sitio, vista al compartir, anuncios) y la resolución (qué hacer, en orden).

- Cada sección abre con un **titular que concluye**; el nombre italiano queda como etiqueta.
- Un **hecho** es un dato; un **hallazgo**, un patrón; un **insight** dice por qué importa y
  qué decisión obliga. Le Scoperte agrupa los hallazgos bajo 3 a 5 insights: arriba la idea,
  debajo la cita que la sostiene.
- Un solo color de acento, reservado para la marca y lo urgente. Nada escondido tras un clic.
- **Urgencia honesta:** solo con hechos del viaje (una fecha vencida, un proceso que ya abrió).
  Ninguna cifra de pérdida que no se haya medido. El código descarta la frase de la idea o de
  la historia que trae un número que no aparece en los datos.

## Qué cuenta y en qué orden

| Sección | De dónde sale | Quién la escribe |
|---|---|---|
| En una frase | manifiesto, Registro del Lete y L'Ascolto | el código |
| Lo esencial | hallazgos, perfiles, visibilidad y acciones | el código |
| Con sus propias palabras | el primer párrafo con sustancia de cada página | el código |
| Le Scoperte | `data/gold/hallazgos.json` | el agente; el código comprueba las citas |
| Lo Specchio | el HTML del Inferno | el código |
| Le Muse | `data/raw/anuncios/*.jsonl` o `data/gold/muse-sin-anuncios.json` | el código |
| L'Eco | L'Ascolto, Le Domande y `data/eco/competidores.json` | el código |
| La Risposta | `data/gold/risposta.json` | el agente; el código filtra la evidencia |
| Para completar el viaje | lo que falta en el proyecto | el código; desaparece cuando no falta nada |
| Cómo se hizo | los círculos de Il Viaggio | el código |

## Le Scoperte: `data/gold/hallazgos.json`

Un objeto con dos listas, `hallazgos` y `vacios`.

| Campo de un hallazgo | Qué va |
|---|---|
| `tema` | grupo legible: «Admisiones», «Instalaciones y entorno», «Actualidad del sitio» |
| `hallazgo` | una o dos frases propias que dicen **solo** lo que la cita sostiene |
| `cita` | la frase del documento del Paradiso, letra por letra, entre 20 y 280 caracteres |
| `url_cita` | la `url_cita` del front matter de ese documento |

| Campo de un vacío | Qué va |
|---|---|
| `tema` | lo que falta: «Costos», «Horario y jornada» |
| `por_que_importa` | una frase humana de por qué pesa en la decisión, sin notas técnicas |

Cada hallazgo puede llevar un `id` (por defecto `h1`, `h2`… en orden). La lista `insights`
agrupa: `titulo` (la idea, como conclusión), `por_que_importa` (una frase) y `hallazgos` (los
`id` que la sostienen). Un insight sin ningún hallazgo válido no llega a La Cronaca.

El código normaliza espacios, comillas y negritas antes de comparar, y descarta el hallazgo
cuya cita no aparece en la página que nombra, la que viene de una página que no está en el
Paradiso o la que trae un dato enmascarado. La Cronaca dice cuántos descartó.

Buenos hallazgos:

- Un dato que el cliente usa para decidir: fechas, requisitos, servicios, lugar.
- Una contradicción o un error del propio sitio, como dos rangos de fechas que se cruzan.
- Algo vencido: un evento del año anterior todavía anunciado en la portada.

Un vacío vale solo para las páginas leídas. Antes de declararlo, búscalo en todo el
Paradiso; si el dato está en el pie de página o en los datos estructurados, no es un vacío.

## Lo Specchio

No se redacta. `specchio.py` lee los `.html` del Inferno, pie de página incluido, y cuenta:

- la vista previa al compartir (título, descripción e imagen) y si está completa;
- los perfiles sociales enlazados y en cuántas páginas aparecen;
- los enlaces de mensajería directa y los botones para compartir;
- lo que conviene corregir: descripciones repetidas o que parecen un nombre de archivo,
  imágenes sin tamaño, perfiles que faltan en los datos estructurados.

Nunca visita un perfil ni hace una petición: todo sale de lo ya capturado.

## Le Muse sin anuncios: `data/gold/muse-sin-anuncios.json`

Cuando la búsqueda no encuentra anuncios de la marca, se guarda la búsqueda:

| Campo | Qué va |
|---|---|
| `consultas` | cada búsqueda hecha (término, país y estado) |
| `resultado` | «sin anuncios de la marca» |
| `fecha` | cuándo se buscó |

La Cronaca lo cuenta y recuerda el límite: un anuncio que no nombra la marca en el texto
puede escaparse de la búsqueda.

## La Risposta: `data/gold/risposta.json`

Un objeto con la lista `acciones`, de 4 a 6, en orden de impacto en la decisión del cliente.

| Campo | Qué va |
|---|---|
| `titulo` | qué crear o reforzar, en 12 palabras como máximo, sin URL |
| `prioridad` | 1, 2, 3… |
| `responde_a` | las preguntas, vacíos o hallazgos que atiende (interno, no se muestra) |
| `que_debe_decir` | de 2 a 4 puntos cortos; también se acepta un texto con un punto por línea |
| `evidencia_disponible` | `url_cita` del Paradiso que ya sostienen algo; el código quita las demás |
| `falta_confirmar` | de 1 a 4 datos que solo la empresa puede dar |
| `resultado` | lo que se logra si se hace, en una frase |
| `esfuerzo` | `bajo`, `medio` o `alto` |
| `cuando` | `hoy`, `este mes` o `este semestre`; lo de hoy sale en una franja aparte |

El mismo archivo lleva arriba `gran_idea` (una frase) e `historia` (tres frases). Si se
configura `CONTACTO_INFORME` en `config.py`, La Cronaca cierra con un siguiente paso; vacío,
no se muestra.

Cada acción nace de algo encontrado: una brecha de L'Eco, un vacío, un hallazgo o un error de
los asistentes al describir la marca. Si no se puede señalar de dónde nace, sobra.

## Estilo

- Escribe para quien decide en la empresa: frases cortas y concretas.
- Sin códigos de pregunta, rutas, nombres de archivos ni nombres de herramientas o motores.
- De la competencia, solo nombres; nunca atributos que dijo un motor.
- Nada sin fuente. Lo que no está en el Paradiso va en `falta_confirmar`.
- Antes de compartirla, léela completa de principio a fin.
