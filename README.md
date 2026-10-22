<p align="center">
    <img alt="Nautilio: per me si va ne la città dei dati" src="docs/assets/portada.svg">
</p>

<p align="center">
    <img alt="Agent Skill" src="https://img.shields.io/badge/Agent-Skill-15110D?style=flat">
    <img alt="Licencia MIT" src="https://img.shields.io/badge/licencia-MIT-5E554A?style=flat">
</p>

<p align="center">
    <a href="#el-viaje"><strong>El viaje</strong></a>
    &middot;
    <a href="#el-mapa"><strong>El mapa</strong></a>
    &middot;
    <a href="#instalación"><strong>Instalación</strong></a>
    &middot;
    <a href="#uso"><strong>Uso</strong></a>
    &middot;
    <a href="#le-leggi"><strong>Le leggi</strong></a>
</p>

> *Per me si va ne la città dei dati.*

**Nautilio** es una skill de agente. Le das una empresa, su dominio, unas pocas páginas
y la marca que quieres leer, y arma un proyecto que recorre los datos públicos círculo por
círculo: entra por la puerta, baja sin prisa, deja lo personal en el río del
olvido y sale con lo que se puede citar.

## El viaje

Nautilio tiene dos brazos.

- **Il Viaggio** (`make capture`): baja del sitio público solo lo que tiene permiso de
  bajar, lo limpia y lo deja citable, página por página y con su fuente.
- **Le Muse** (`make anuncios`): lee los anuncios públicos de una marca para aprender de
  sus ganchos, ángulos y guiones. *Inspírate, no copies.*

<p align="center">
    <img alt="El mapa del viaje: Il Viaggio y Le Muse" src="docs/assets/flujo.svg">
</p>

## El mapa

| Nombre | Qué hace |
|---|---|
| **La Porta** | Pide permiso antes de entrar. Si el sitio no lo da, no entra. |
| **Il Passo** | Avanza sin prisa, una página a la vez. |
| **Caronte** | Sabe cuándo parar: si el sitio niega el paso, el viaje termina. |
| **Inferno** | Lo crudo, tal como llegó. |
| **Purgatorio** | Lo limpio. Aquí corre el **Lete**, el río del olvido, que borra los datos personales. |
| **Registro del Lete** | Cuenta cuánto borró el Lete y dónde. |
| **Paradiso** | Lo citable: cada línea con su fuente. |
| **Limbo** | Lo que no se puede leer sin un navegador espera revisión humana. |
| **Raccolta · Conteggio · Lettura · Ispirazione** | Los cuatro pasos de Le Muse: recoger, contar, leer e inventar algo propio. |
| **Il Giudizio** | La revisión final antes de publicar nada (`make check`). |

## Instalación

Copia la carpeta `skills/nautilio/` dentro de la carpeta de skills de tu agente. No necesita
dependencias de Node.

```bash
cp -r skills/nautilio <carpeta-de-skills-de-tu-agente>/nautilio
```

En Windows, copia la carpeta con el Explorador o con `Copy-Item` de PowerShell.

## Uso

Invoca la skill y describe el viaje:

```text
@nautilio

Empresa:   Empresa Demo
Dominio:   ejemplo.com
Semillas:  https://ejemplo.com/
           https://ejemplo.com/quienes-somos
Marca:     competidor-demo
Destino:   ./empresa-demo
Contacto:  tu-correo@tu-dominio.edu   (el tuyo, nunca uno de la empresa)
```

Nautilio arma el proyecto y, antes de pedirte nada más, te muestra el viaje completo.

### El primer encuentro

```bash
make demo
```

En unos segundos, sin internet ni configuración, Nautilio recorre una ciudad de prueba en tu
propia máquina y te cuenta lo que pasó:

```text
La Porta     dejó pasar 2 páginas y cerró 1 que el sitio prohíbe
Caronte      negó el paso y detuvo el viaje; 1 página quedó sin visitar
Purgatorio   el Lete borró 4 datos personales: 2 correos, 1 teléfono y 1 identificación
Paradiso     2 documentos citables en data/demo/gold, con su fuente
Le Muse      6 anuncios: 4 creativos únicos y 2 repetidos
```

Después es tu turno: pon tu correo, elige páginas reales que den permiso y corre
`make capture`.

## Le leggi

- Se pide permiso antes de entrar y se respeta el «no».
- Quien viaja se identifica con su propio nombre y nunca se disfraza.
- Nada de formularios, sesiones, áreas privadas ni recolección automática en redes sociales.
- Lo personal pasa siempre por el Lete; los datos de menores no entran.
- El proyecto nace privado y nunca publica copias completas de un sitio.
- Las cifras las cuenta el código, no el modelo de lenguaje.
- *Inspírate, no copies.*

## Licencia

MIT © 2026 Christian Trujillo. Ver [`LICENSE`](LICENSE). Créditos de las imágenes en
[`docs/assets/CREDITOS.md`](docs/assets/CREDITOS.md).
