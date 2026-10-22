# El Lete: enmascarado de datos personales

El Lete es el río del olvido que se cruza antes de subir al Paradiso.
Aquí cumple la misma función: el texto cruza el Lete en el Purgatorio, antes de llegar al
Paradiso. La regla base es minimizar: si un dato no es imprescindible para el corpus, se
tapa.

## Marcas

| Tipo | Marca |
|------|-------|
| Correo | `[correo enmascarado]` |
| Teléfono | `[telefono enmascarado]` |
| Identificación | `[identificacion enmascarada]` |

Las marcas son estables y sin acentos para que los conteos del Registro del Lete sean exactos.

## Qué borra siempre el Lete

### Correos de personas

Cualquier correo cuyo dominio no sea el institucional de la empresa. También se borran los
correos del dominio institucional que corresponden a una persona: por ejemplo, el correo de un
directivo en un informe anual.

### Números de identificación

Cédula, NIT, pasaporte y variantes con prefijos como `C.C.`, `CC`, `NIT` o `Pasaporte`.

### Celulares

**Todos** los celulares, incluidos los de tiendas, sucursales y líneas de atención. Ejemplos
ficticios:

```text
+57 313 424 5231
313 424 5231
Celular: 3134245231
```

### Lo que el Lete no salva

Los datos de menores no se enmascaran: se descartan. El Lete no los reconoce por sí solo; si
aparecen en la revisión, quien revisa saca el fragmento del corpus.

## Qué sobrevive (configurable)

| Excepción | Condición | Interruptor en `config.py` |
|-----------|-----------|----------------------------|
| Correos institucionales | Dominio igual o subdominio del dominio de la empresa | `CONSERVAR_CORREOS_INSTITUCIONALES` |
| Teléfonos fijos | Prefijo nacional `60x` (601–608) | `CONSERVAR_TELEFONOS_FIJOS` |

Ambas excepciones se pueden apagar. Si el proyecto trabaja con datos de personas y no solo con
información corporativa, apágalas.

## La lección de los celulares de tienda

Un celular publicado en la ficha de una tienda **parece** corporativo, pero muchas veces es la
línea personal de quien atiende. No hay forma de probarlo desde la página. Por eso:

> Los celulares de tiendas y sucursales se tratan como **personales** salvo que exista
> **prueba escrita** de que son corporativos (un contrato, una política publicada o una
> autorización del titular).

En la práctica, el Lete los borra siempre. Si más adelante aparece la prueba, se puede evaluar
una excepción concreta, documentada en `CONSTITUTION.md`.

Esta regla corrige el error común de conservar el teléfono del local porque «es de la
empresa». El costo de enmascarar de más es bajo; el de exponer una línea personal es alto.

## Falsos positivos

- Las cifras financieras no se tocan: no tienen forma de teléfono ni etiqueta.
- Un correo institucional dentro de una ficha de tienda sobrevive; uno de dominio externo en la
  misma ficha se borra.
- No se intenta adivinar identidades ni completar datos faltantes.

## Registro del Lete

El Registro del Lete (`data/gold/inventario_enmascarado.json`) tiene esta forma:

```json
{
  "por_tipo": {"correo": 3, "telefono": 2, "identificacion": 1},
  "por_archivo": {
    "contacto.md": {"correo": 2, "telefono": 1, "identificacion": 0},
    "quienes-somos.md": {"correo": 1, "telefono": 1, "identificacion": 1}
  },
  "total": 6
}
```

Se revisa en Il Giudizio, antes de publicar. Un total inesperadamente bajo puede indicar que
una regla dejó de aplicarse; uno inesperadamente alto, que el Lete borra texto legítimo.
