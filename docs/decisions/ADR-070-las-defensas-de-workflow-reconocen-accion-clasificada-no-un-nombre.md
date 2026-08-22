# ADR-070 — Las defensas de workflow reconocen «acción clasificada», no un nombre

- Estado: PROPUESTO
- Fecha: 2026-08-22
- Aprobación: la fusión de la PR de esta rama por el propietario
- Nota de arranque de esta rama: este ADR. Publicado antes del primer commit.

## Contexto y problema

`tests/automation/test_auditor_workflow.py` sostiene las defensas de ADR-016: lo
que ejecuta un modelo no puede escribir, y el trabajo del modelo no recibe más
secreto que su credencial. Las dos se apoyaban en esta línea:

```python
ACCIONES_CON_MODELO = ("anthropics/claude-code-action",)
```

**Una tupla escrita a mano con un nombre.** Toda la defensa reconocía
*ese nombre*, no la categoría «acción que ejecuta un modelo». Un runtime nuevo
—otra acción, otro proveedor, un contenedor— entraba sin que el barrido de
permisos ni la regla de secretos lo miraran siquiera: su nombre no estaba en la
tupla, así que `_ejecuta_modelo()` devolvía `False` y el job quedaba fuera de
todas las comprobaciones.

Es exactamente la familia que ADR-033 nombró y que este repositorio ya ha pagado
varias veces: **una lista escrita a mano siempre tiene un hueco más**. Aquí el
hueco no era teórico: era «cualquier acción que todavía no exista».

## De dónde sale la solución

De la PR #171, que se cerró sin fusionar el 22-08-2026. Su **ADR-018** —«el arnés
ejecuta y el modelo interpreta; runbooks neutrales al motor»— traía un
`registro_de_acciones.yml`: un registro **cerrado** donde toda acción `uses:` de
todo workflow tiene que estar clasificada.

El plan del Work Engine señaló ese registro entre las piezas «compatibles y
valiosas» a extraer. En `main` se había heredado **el patrón** —así lo dicen
`registro_capacidades.yml` y `capability_registry.py`, que se declaran «heredero
directo del patrón de `registro_de_acciones.yml` (PR #171)»— pero **no el
fichero ni su guarda**. La idea estaba, la defensa no.

Número nuevo y no ADR-018 porque el 017 y el 018 siguen tomados mientras exista
la rama `feat/investigador-por-etiqueta`, y la convención de numeración cuenta
todas las ramas remotas.

## Criterio de parada (escrito ANTES de decidir)

Si extraer el registro exigiera **tocar `.github/**`**, se para: la
automatización lo tiene prohibido (ADR-002) y la sesión interactiva lo tiene
denegado por permisos. No se activó — el registro y su guarda viven enteros en
`tests/automation/`, y los workflows solo se **leen**.

Y si al derivar `ACCIONES_CON_MODELO` del registro alguna defensa existente
dejara de mirar lo que miraba, se para: sustituir una guarda por otra más
elegante que cubre menos es un retroceso disfrazado. Tampoco se activó, y hay
mutación que lo demuestra.

## Decisión

`ACCIONES_CON_MODELO` **se deriva** de la clave `con_modelo` del registro. La
pregunta que se hace la defensa deja de ser «¿es esta acción?» y pasa a ser
«¿está clasificada?».

Y se añade la guarda que cierra el círculo: **toda `uses:` de todo workflow debe
estar en el registro**, o la suite se pone roja. Se recorren las de paso **y las
de nivel job** —los workflows reutilizables—, porque un barrido solo de pasos
dejaría entrar un workflow entero sin clasificar, que es una puerta más ancha
que la que se cierra.

Consecuencia buscada: meter un motor nuevo obliga a pasar por el registro, y
entrar en `con_modelo` le aplica **de golpe** el barrido de permisos y la regla
de secretos que ya existen. La defensa se amplía sola.

## Consecuencias

- Aceptada: añadir una acción legítima exige una línea en el registro. Es el
  coste, y es el que se quiere pagar — esa línea es la decisión, visible.
- El registro también rechaza `./ruta` y `docker://`: no son nombres
  clasificables y caen en «desconocida» mientras nadie las declare.

## Lo que esto NO hace

- **No detecta un modelo ejecutado sin acción**, por ejemplo con un `run:` que
  invoque un binario. La guarda cubre `uses:`, que es como entran hoy los
  runtimes; un `run:` que descargue y ejecute un modelo pasaría.
- **No clasifica bien por sí sola.** Si alguien mete una acción con modelo en
  `sin_modelo`, la guarda de clasificación pasa y las defensas no la miran. Lo
  que impide es la entrada *silenciosa*, no la mal declarada.
- **No toca los workflows.** Solo los lee.

## Comprobación que la sostiene

- **Mutación, vista fallar:** vaciada la clave `con_modelo` del registro, caen
  **cuatro** pruebas — incluidas dos que ya existían antes de este cambio. Eso
  demuestra que la derivación es real y no decorativa: el registro gobierna las
  defensas de verdad.
- Defecto sembrado sobre definiciones **sintéticas** (no sobre `.github/`, para
  no dejar basura en el árbol): una acción desconocida en un paso se detecta;
  un workflow reutilizable sin clasificar también; `./ruta` y `docker://` caen
  en desconocida; y la versión (`@v4` frente a `@v6`) no cuenta para clasificar.
- Guarda contra excepciones muertas: una acción clasificada que ya no usa ningún
  workflow pone la prueba en rojo, para que la lista no crezca sola.
