# La Porta: ética y marco legal de la captura

> «Per me si va ne la città dei dati.»

Este documento fija el criterio para decidir **si** se cruza La Porta. La respuesta por defecto
es no: se entra solo cuando hay permiso técnico y legal claro.

## 1. `robots.txt`

`robots.txt` es una declaración del sitio sobre qué agentes pueden recorrerlo. Se lee siempre
antes de la primera petición y se respeta por agente y por ruta.

- Si `Disallow` bloquea la ruta, no se captura.
- Si `robots.txt` no existe (`404`), se asume permitido, pero se revisan igual los términos de
  uso.
- Si `robots.txt` responde `403` o `429`, Caronte detiene el lote. Si responde `401` o es
  inaccesible por red, no se adivina: ese origen queda cerrado.
- Si el sitio declara un `Crawl-delay` mayor que Il Passo (4 s, `REQUEST_DELAY_SECONDS`), se
  sube Il Passo en `config.py` antes de capturar.
- `robots.txt` no autoriza el uso de los datos: solo el recorrido.

## 2. Términos de uso

Los términos de uso son un contrato entre el sitio y quien lo consulta. Se leen antes de
capturar y se busca, como mínimo:

- prohibición de recolección automatizada, crawling o scraping;
- prohibición de reproducción o redistribución del contenido;
- límites de uso comercial o de creación de bases de datos;
- exigencia de autorización escrita.

Si los términos prohíben la captura, no se captura aunque `robots.txt` lo permita. Cuando
`robots.txt` y los términos difieren, se aplica el criterio **más restrictivo**. La decisión y
su justificación se registran en `CONSTITUTION.md`.

## 3. Ley 1581 de 2012 (Colombia)

La Ley 1581 de 2012 protege los datos personales. Aplica a datos de personas naturales,
incluidos los que están publicados en internet.

Principios que gobiernan la captura:

- **Finalidad:** se recoge solo lo necesario para el corpus declarado.
- **Minimización:** nada de datos personales que no aporten al propósito.
- **Veracidad y calidad:** se conserva la fuente y la fecha; no se inventan datos.
- **Seguridad:** el repositorio es privado por defecto y el acceso se limita.
- **Transparencia:** el `User-Agent` identifica al responsable y deja un contacto.
- **Confidencialidad:** los datos personales cruzan el Lete antes de llegar al Paradiso.

Los datos personales **públicos** no quedan libres por estar publicados: siguen protegidos y
su tratamiento requiere una base legal. Los datos sensibles (salud, orientación sexual,
convicciones religiosas, datos biométricos, etc.) no se capturan. Los datos de niños, niñas y
adolescentes tienen protección reforzada.

El Lete es una medida técnica de minimización; **no** sustituye la autorización del titular
ni el análisis jurídico del caso.

## 4. Menores de edad

- No se capturan páginas dirigidas a menores ni datos de menores.
- Si un documento contiene nombres, imágenes o contactos de menores, se descarta el fragmento.
  No basta con enmascararlo: se elimina.
- Los programas, concursos o contenidos escolares se tratan como sensibles y quedan fuera del
  alcance por defecto.

## 5. Redes sociales

- No se recolecta de forma automatizada en redes sociales: sus términos suelen prohibirlo y
  sus datos personales tienen protección reforzada.
- Se permite usar una API oficial si el titular autorizó el acceso, el uso está dentro de los
  términos y se respetan los límites de la plataforma.
- Los enlaces a redes sociales dentro de una página capturada se conservan como enlaces, no
  como contenido descargado.

## 6. Un cliente honesto

El cliente HTTP de la plantilla se identifica con honestidad y nunca suplanta un navegador. El
`User-Agent` lleva el contacto de quien captura. No hay modos sigilosos, proxies ni rotación de
direcciones.

El pipeline consulta La Porta en cada origen antes de pedir una página, y Caronte vive en el
propio cliente: ante `403` o `429`, el lote se detiene.

Si una página depende de JavaScript, no se abre un navegador ni se sortea la protección: la
página queda en el Limbo y espera revisión humana.

## 7. Lo que nunca se hace

- Sortear un bloqueo con proxies, rotación de IP o un `User-Agent` alternativo.
- Usar modos sigilosos o resolver desafíos contra robots.
- Atravesar formularios, inicios de sesión o endpoints autenticados.
- Descargar copias completas del sitio o de sus bases de datos.
- Publicar el corpus sin revisar el Registro del Lete.
- Capturar datos de menores o datos sensibles.
