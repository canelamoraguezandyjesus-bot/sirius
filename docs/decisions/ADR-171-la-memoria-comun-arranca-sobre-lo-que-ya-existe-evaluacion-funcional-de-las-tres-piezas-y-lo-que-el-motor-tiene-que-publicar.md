# ADR-171 — La memoria común arranca sobre lo que ya existe: evaluación funcional de las tres piezas (T-5) y lo que el motor tiene que publicar

- Estado: PROPUESTO
- Fecha: 2026-09-11
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Ejecuta: la decisión técnica pendiente **T-5** de
  `docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md` §7.2, que ADR-160 dejó
  abierta: *«la evaluación funcional —qué requisitos de 6.3 cumple ya cada pieza
  existente— no se ha hecho, y es trabajo previo a elegir nada»*
- Numeración: 171 y no 170. `main` llega a ADR-169 y la PR abierta #583 tiene
  tomado el 170. Mismo modo de fallo que ADR-069 documenta; se evitó mirando las
  PR abiertas
- Relacionadas: ADR-160 (las tres memorias con dueño distinto, EV-018), ADR-082 y
  ADR-083 (el diario del motor vive en su rama), ADR-161 y ADR-163 (los carriles
  retirados que dejaron la memoria común como decisión pendiente), ADR-001

> **Este ADR es también la nota de arranque de la rama**, publicada en su propio
> commit antes de leer una sola pieza. Las conclusiones se rellenan después, con
> evidencia marcada `[V]` (verificado en el repositorio) o `[H]` (hipótesis).

## Por qué ahora

El propietario lo ha dicho con estas palabras: *«cuando hablo en una sesión de
Claude Code, cuando tomo decisiones, cuando redacto documentos, cuando se trabaja
en el motor, todo quede en un mismo sitio»*, y *«siempre estáis leyendo las
conversaciones todo el rato y me gastáis muchos planes»*. Las dos cosas son la
misma: **nada publica el trabajo al hacerse en una forma barata de consultar**,
así que cada sesión y cada run reconstruye el contexto releyendo el repositorio.

Y la dirección ya está dada (ADR-160, EV-018): la memoria común es memoria **del
trabajo**, las IAs la actualizan, y el propietario **no escribe fichas** (R14).
Lo que falta no es una decisión nueva: es la evaluación que ADR-160 declaró
previa a cualquier elección, y que nadie ha hecho.

## Nota de arranque (publicada ANTES de evaluar)

**1. ¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en dos sitios y
el arreglo también. Primero, **nadie ha medido qué cumplen ya las tres piezas**
—el repositorio, el diario del motor, la memoria del producto— frente a los
catorce requisitos de la propuesta §6.3; sin eso, cualquier herramienta se elige
a ciegas y cualquier «mapa» se pudre. Segundo, **el motor no publica
desenlaces**: la propuesta §6.2 le asigna exactamente esa obligación —*«publicar
desenlaces (qué se encargó, qué salió, dónde está la evidencia); nunca ceder la
autoridad del estado en curso»*— y hoy sus desenlaces viven solo en su diario y
en etiquetas de GitHub. Este ADR hace la evaluación y decide, con ella, dónde
arranca la memoria común **sin comprar nada** y qué tiene que publicar el motor.

**2. ¿Qué NO va a garantizar esto?**

- **No elige la herramienta definitiva.** Graphiti, Obsidian, Basic Memory o
  cualquier otra siguen siendo candidatas para después; este ADR decide dónde
  arranca la memoria con lo que ya existe, que es lo que ADR-160 pide que se
  evalúe primero.
- **No toca la memoria propia de Sirius ni Sirius 0.2.** D6 y EV-018 las dejan
  aparte, y aparte siguen.
- **No resuelve T-6** (qué del repositorio privado puede salir hacia las IAs
  externas) más allá de declararla y de exigir que la protección sea mecánica.
- **No da permiso de escritura general a ninguna IA** (R10). El mecanismo de
  escritura es T-4 y se decide con la evaluación delante, no antes.
- **No promete por sí solo reducir el gasto de las sesiones interactivas**: eso
  exige que las sesiones lean la vista barata, y ese cambio de conducta se
  ordena en `AGENTS.md`, que es un acto aparte.

**3. Criterio de parada (escrito ANTES de ver resultados).**

- **(a)** Si el repositorio más el diario del motor cumplen R1–R14 salvo huecos
  que se cierran **generando** vistas con un guion y una prueba, la memoria común
  arranca sobre el repositorio y **no se propone nada nuevo**.
- **(b)** Si algún requisito de disponibilidad (R1), supervivencia (R3) o
  independencia de proveedor (R13) **no lo cumple ninguna pieza existente**, se
  para y se declara: ahí sí hace falta algo nuevo, y se lista qué, sin elegirlo.
- **(c)** Si publicar desenlaces del motor exigiera cambiar permisos o escribir
  en `.github/**` desde la automatización (ADR-002), se declara la mano humana
  necesaria en vez de sortearla.
- **(d)** Ninguna afirmación sobre una pieza sin `[V]` o `[H]`. Una búsqueda
  vacía por nombre **no** prueba ausencia funcional (lección de la propuesta
  §6.1).
- **(e)** Si la evaluación obligara a leer entero más de un documento por pieza
  para responder un requisito, ese requisito se responde con `[H]` y se dice:
  este ADR no puede ser él mismo un ejemplo del gasto que viene a reducir.

**4. ¿Qué haría imposible el error más probable, en vez de improbable?** El error
más probable ya ocurrió en esta misma sesión: proponer una vista **curada** —un
mapa escrito a mano— que se queda vieja con la siguiente decisión. Lo hace
imposible una regla, no un recordatorio: **toda vista de la memoria común se
genera con un guion que tiene prueba**, de modo que un ADR sin resumen, un
desenlace sin publicar o un índice desactualizado rompan CI. Lo que no se puede
hacer imposible desde aquí: que una IA externa lea la vista y decida releer el
corpus igualmente; eso es conducta, y se ordena en `AGENTS.md`.

## Evaluación funcional (T-5)

Se rellena con la evidencia, requisito a requisito y pieza a pieza.

## Decisión

Se rellena después de la evaluación.

## Lo que el propietario tiene que hacer

Se rellena después de la evaluación, como guía concreta.
