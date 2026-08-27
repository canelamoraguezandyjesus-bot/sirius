# Investigaciones

Aquí se guardan **enteras** las investigaciones que informaron una decisión, con
su fecha y con de qué dependen para caducar.

El propietario lo pidió así, con estas palabras:

> «Las investigaciones no se pueden perder, porque siempre investigamos, y ya sé
> que las cosas cambian más adelante. Pero hay que tener las investigaciones de
> por qué se tomaron las decisiones.»

## La regla, y por qué no basta con archivar

Guardar el documento no basta. **Una investigación sobre algo que cambia es una
foto con fecha**, y tratarla como fuente es exactamente lo que costó la noche del
26 al 27 de agosto de 2026: cuatro rondas configurando modelos que ya no existían,
tres de ellos sacados de documentos que **eran correctos el día que se
escribieron** (ADR-095).

Por eso cada investigación de esta carpeta lleva, en su cabecera:

| campo | para qué |
|---|---|
| `fecha` | cuándo se hizo. Sin esto no se puede juzgar si sigue valiendo |
| `pregunta` | qué se le encargó responder, en una frase |
| `caduca_con` | **de qué depende para envejecer**. Es el campo que importa |
| `estado` | VIGENTE, PARCIALMENTE CADUCADA o CADUCADA |

Y si ya caducó, **un aviso arriba del todo** que diga qué acertó, qué falló y qué
se aprendió. Un documento caducado sin aviso es peor que no tenerlo: se lee y se
cree.

## Lo que va aquí y lo que no

| | dónde |
|---|---|
| La investigación entera, tal como llegó | **aquí** |
| La decisión que se tomó con ella, y por qué | `docs/decisions/ADR-*.md` |
| La medición que sostiene una afirmación | `docs/audits/evidencia-*.md` |
| Qué modelo funciona **hoy** | `scripts/investigacion/modelos_atestiguados.yml` |

Esa última fila es la lección entera: **el estado de algo vivo no se guarda en un
documento**, se le pregunta a quien lo sabe. El documento guarda por qué se
preguntó.
