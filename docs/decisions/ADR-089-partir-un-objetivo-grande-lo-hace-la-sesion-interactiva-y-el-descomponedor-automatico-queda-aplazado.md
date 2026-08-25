# ADR-089 — Partir un objetivo grande lo hace la sesión interactiva, y el descomponedor automático queda aplazado

- Estado: PROPUESTO
- Fecha: 2026-08-25
- Aprobación: decisión del propietario del 25-08-2026, registrada en la
  incidencia #341; la fusión de esta PR la deja escrita
- Relacionadas: ADR-082 (el motor no ejecuta modelos, e I4), ADR-063 (el
  despachador), ADR-079 (`MIXTA` es inalcanzable por construcción), ADR-087
  (el registro de bloques)

## Contexto y problema

`sirius-despachar` convierte **una frase en un encargo**. Pedirle algo del
tamaño de una versión entera produce un encargo de alcance imposible.

Y esto **no está en ningún plan**. Comprobado el 25-08-2026: ni «partir», ni
«descomponer», ni «planificador» aparecen en `docs/implementation/` ni en
`docs/decisions/`. Es alcance nuevo, nombrado ese día al inventariar lo que el
motor hace de verdad.

Lo que hay hoy, medido:

| | |
|---|---|
| Trabajo padre/hijo en el dominio | **no existe**: `WorkItem` no tiene padre |
| Clase `MIXTA` | existe en el enum y es **inalcanzable por construcción** (ADR-079) |
| El contrato sobre descomponer | **no dice nada** |

## Criterio de parada (escrito ANTES de decidir)

**(a)** Si la solución **exige ejecutar un modelo dentro del motor**, se para y
se sube a decisión del propietario. Esa premisa —el motor no ejecuta ninguno—
sostiene ADR-082 y la vigila
`tests/automation/test_el_motor_no_ejecuta_modelos.py`. Tocarla es reabrir una
decisión de seguridad, no añadir una tabla.

**(b)** Si no hay **ningún objetivo real esperando** que la vía manual no pueda
atender, se para. Construir maquinaria para un problema que aún no se tiene es
la forma más cara de equivocarse.

**(c)** Si la vía manual **no tiene guardián** —si un reparto mal hecho puede
colarse sin que nada lo note— no vale como respuesta, ni siquiera provisional.

## Opciones consideradas

1. **Incidencias padre e hijas de GitHub.** El objetivo grande es una incidencia
   padre; cada trozo, una hija que se despacha como cualquier encargo. Barato y
   nativo, pero da **dónde colgar** el reparto, no **quién lo piensa**.
2. **Un descomponedor automático** sobre la clase `MIXTA`, hoy inalcanzable.
   Es lo único que quita del todo la persona del bucle, y choca de frente con el
   criterio (a).
3. **El reparto lo hace la sesión interactiva.** Es la elegida.

## Decisión

**Opción 3, ahora.** El propietario dice el objetivo, la sesión interactiva lo
parte en encargos y los despacha uno a uno.

**La opción 1 se añade el día que haya varios objetivos vivos a la vez**, no
antes: es barata y no reabre nada, pero hoy no resuelve ningún problema que
exista.

**La opción 2 queda APLAZADA, no descartada.** Y con una condición del
propietario que es parte de la decisión, no una nota al margen:

> **Cuando llegue, el modelo que decida el reparto tiene que ser una vía local
> o una API gratuita. No una API de pago de Claude ni de ChatGPT.**

Esa restricción no es de gusto: es la misma regla de gasto que gobierna el resto
del proyecto —se paga por pregunta, pero no con esas dos APIs—, y llega a este
ADR porque es aquí donde se decidirá el primer modelo que el motor ejecute.

## Comprobación que la sostiene

**El criterio (a) muerde:** la opción 2 exige un modelo dentro del motor. Se
verificó que la premisa sigue viva y vigilada: `test_el_motor_no_ejecuta_modelos.py`
prohíbe todo SDK de modelo y toda biblioteca de red en `src/sirius_engine/`, y
sólo tolera `gh` y `git` como binarios. Activar `MIXTA` con un descomponedor
rompería esa prueba, que es exactamente lo que la prueba existe para hacer.

**El criterio (b) muerde:** no hay ningún objetivo pendiente que la vía manual
no pueda atender. Los cuatro bloques abiertos del registro —S2, B1, D1 y D2—
caben todos en un encargo cada uno.

**El criterio (c) NO muerde, y esto es lo que sostiene la decisión.** La vía
manual tiene guardián, y se vio funcionar el mismo día: C3 se partió a mano en
dos mitades, y cuando el implementador recibió el bloque entero **se negó a
entregar la mitad que sí podía hacer**:

> «Añadir únicamente las filas […] sin el cableado de los workflows no cierra el
> bloque C3 […]: el ciclo arrancaría pero ejecutaría el prompt de programación,
> no el documental, lo que sería **una vuelta completa falsa**.»
>
> «No se ha creado rama, código ni PR.»

Un reparto mal hecho no se coló: lo paró la propia máquina, sin que nadie se lo
pidiera. Eso convierte la opción 3 en algo más que un apaño provisional.

## Consecuencias

**El propietario sigue en el bucle para partir**, y eso es deliberado mientras
la alternativa cueste reabrir una decisión de seguridad.

**Queda un techo declarado**: la opción 3 no escala más allá de lo que una
persona aguante seguir, y depende de que la sesión esté delante. El día que ese
techo estorbe, esta decisión se relee — y el registro de bloques dirá qué
objetivo la hizo estorbar.

**Y queda escrita la restricción del modelo.** Sin ella, el día que alguien
retome la opción 2 la respuesta cómoda sería llamar a la API que ya se tiene a
mano. Esa puerta queda cerrada por decisión, no por olvido.

## Alternativas descartadas y por qué

- **Descomponedor automático ya (opción 2)**: criterios (a) y (b). Reabre
  ADR-082 para resolver un problema que hoy no existe.
- **Padre/hijas ya (opción 1)**: no lo descarta nada; simplemente no resuelve
  nada todavía. Se retoma cuando haya varios objetivos vivos.
- **Añadir `MIXTA` a la tabla del despachador sin descomponedor**: sería una
  clase que se despacha y que ningún agente sabe atender. Es la familia de
  defecto que este repositorio lleva seis veces encontrando —una pieza que
  nadie llama— y no se añade una séptima a propósito.
