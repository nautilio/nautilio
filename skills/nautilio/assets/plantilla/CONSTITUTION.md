# CONSTITUTION — Corpus de {{EMPRESA}}

> **Verdad central del proyecto.** Si algo aquí contradice al código, el código manda y este
> archivo se actualiza en el mismo cambio.

> «Per me si va ne la città dei dati.»

## 1. Propósito

Construir un corpus citable y reproducible con información pública de `{{DOMINIO}}`. Il
Viaggio cruza La Porta: respeta `robots.txt`, los términos de uso y la normativa de protección
de datos. Cada afirmación conserva su URL de origen y la fecha de captura.

### No-propósito

No es un crawler masivo. No atraviesa formularios, sesiones ni endpoints autenticados. No
recolecta datos de redes sociales ni datos de menores. No publica copias completas del sitio.

## 2. Alcance

- Semillas explícitas y acotadas en `src/paquete_plantilla/config.py`.
- Tres reinos: Inferno, Purgatorio y Paradiso.
- Fuera de alcance: páginas no listadas como semilla, áreas privadas, redes sociales y
  cualquier dato personal que no sea estrictamente necesario.

## 3. Il Viaggio: ética de captura

- **La Porta:** leer `robots.txt` y los términos de uso **antes** de capturar. Manda el
  criterio más restrictivo; ante la duda, no se entra.
- **Il Passo:** una solicitud a la vez y una pausa fija entre peticiones.
- `User-Agent` identificable con el correo real de quien captura, nunca uno de la empresa.
- **Caronte:** ante `403` o `429` el viaje se detiene de inmediato; el resto de semillas queda
  sin intentar.
- Sin formularios, sesiones, cookies de autenticación ni endpoints privados.
- Sin recolección automatizada en redes sociales.
- El cliente se identifica con honestidad y nunca suplanta un navegador. Sin herramientas
  sigilosas, proxies ni rotación de direcciones.
- **Limbo:** si una página solo carga con JavaScript, queda marcada para revisión humana. No se
  abre un navegador para sortearlo.
- Repositorio **privado por defecto**.
- Nunca publicar copias completas del sitio: solo fragmentos citables.
- Excluir datos de menores.

## 4. El Lete

- Borra correos de personas, números de identificación y **todos** los celulares.
- Solo sobreviven los correos del dominio institucional `{{DOMINIO}}` y los teléfonos fijos
  (`60x`); ambas excepciones se pueden apagar en `config.py`.
- Un celular de una tienda o sucursal se trata como personal salvo prueba escrita de que es
  corporativo.
- El Registro del Lete anota cuántos datos se enmascararon por archivo y por tipo. Revisarlo
  antes de publicar es obligatorio.

## 5. Los tres reinos

| Reino | Contenido | Se versiona |
|-------|-----------|-------------|
| Inferno | Payload crudo + manifiesto con fecha, hash, estado y marca de Limbo | Solo el manifiesto |
| Purgatorio | Markdown limpio, sin adornos de página, que cruzó el Lete | No |
| Paradiso | Markdown con front matter, `corpus.jsonl` y Registro del Lete | Sí |

## 6. Stack

- Python 3.13 y `uv`.
- Un cliente HTTP honesto, un parser de HTML y un lector de PDF, declarados en
  `pyproject.toml`.
- Un transcriptor local opcional, solo en el extra `audio`.
- El linter del proyecto y las pruebas automáticas.

## 7. Le Muse

- Lema: **«Inspírate, no copies»**.
- Solo se usan datos públicos de las bibliotecas públicas de anuncios de las plataformas,
  recolectados a mano o con un conector autorizado.
- No se descargan videos de forma automática ni se sortean términos de uso.
- Las cifras las calcula el código, no un modelo de lenguaje.
- Menores excluidos.

## 8. Il Giudizio

`make check` debe pasar antes de cada cambio y de cada publicación. Después se revisan a mano
el Registro del Lete, las páginas del Limbo y que no haya copias completas del sitio.

## 9. Historial de decisiones

| Fecha | Decisión | Motivo |
|-------|----------|--------|
| {{FECHA}} | Captura por semillas explícitas, no por crawling | Alcance acotado y auditable |
| {{FECHA}} | El Lete enmascara por defecto celulares, correos personales e identificaciones | Ley 1581 de 2012 y minimización de datos |
| {{FECHA}} | Cliente honesto: no suplanta un navegador, sin proxies y sin navegador para el Limbo | Consentimiento informado y uso ético |
| {{FECHA}} | Le Muse solo con datos públicos y reporte determinista | Transparencia y «Inspírate, no copies» |
