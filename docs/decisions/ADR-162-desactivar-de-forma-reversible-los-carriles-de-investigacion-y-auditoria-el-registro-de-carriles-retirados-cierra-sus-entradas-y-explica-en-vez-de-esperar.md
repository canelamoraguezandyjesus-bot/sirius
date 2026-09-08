# ADR-162 — Desactivar de forma reversible los carriles de investigación y auditoría: el registro de carriles retirados cierra sus entradas y explica en vez de esperar

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Ejecuta: la recomendación de **ADR-161**, ordenada por el propietario
- Relacionadas: ADR-160 (el reparto), ADR-161 (la retirada acordada), contrato
  operativo §13 (v1.10), ADR-099 y ADR-016 (los carriles que se desactivan),
  ADR-088 (la tabla cerrada de clases), ADR-136 y ADR-101 (por qué el diario
  del motor tiene WorkItems parados en `active`), ADR-002 (la automatización no
  escribe en `.github/**`), ADR-001

> **Este ADR es también la nota de arranque de la rama**, publicado en su propio
> commit antes del primer cambio de código.

## Nota de arranque (publicada ANTES del primer cambio)

**1. ¿Dónde vive el fallo y dónde va el arreglo?** No hay un fallo: hay una
decisión que ejecutar. Lo que sí hay es una **trampa de diseño**, y el arreglo
tiene que vivir donde la evita. Los dos carriles no comparten forma de entrada:

- La **auditoría** tiene etiqueta propia (`auditoria:solicitada`) y un workflow
  que solo reacciona a ella. Quitar la reacción deja la etiqueta sin efecto y sin
  respuesta: la incidencia se queda esperando en silencio.
- La **investigación** comparte la etiqueta de programación
  (`sirius:implement-requested`) y se reparte por el campo `Perfil:`
  (ADR-099). El workflow del implementador **declina** el perfil `investigador`
  antes de consumir el evento, para que lo atienda `investigar-orden.yml`.

De ahí sale la trampa, y es la que decide el diseño: si solo se desactiva
`investigar-orden.yml`, una activación con perfil `investigador` **no la atiende
nadie** y se queda colgada; si en cambio se quita la puerta del implementador,
esa misma activación **se implementa como programación**. Las dos cosas están
prohibidas por el encargo, y ninguna se descubre leyendo un solo fichero.

El arreglo, por tanto, no vive en «quitar un disparador». Vive en un **registro
versionado de carriles retirados** que leen las tres piezas —el despachador, el
workflow del auditor y el de investigación—, y en que cada entrada retirada
**responda y termine** en vez de esperar.

¿Puede el sitio del arreglo observar el fallo que arregla? Sí: una prueba puede
poner una activación de cada carril y comprobar que ninguna queda esperando y que
ninguna acaba en el carril de programación.

**2. ¿Qué NO va a garantizar esto?**

- **No borra nada.** Ni código, ni perfiles, ni prompts, ni informes, ni
  investigaciones, ni ADR, ni el historial del diario.
- **No cancela ni toca los seis WorkItems** que el diario tiene parados (ver el
  inventario): no se cancelan órdenes ni se borra estado.
- **No cambia la configuración de GitHub**: ni variables, ni secretos, ni
  protecciones, ni etiquetas existentes.
- **No garantiza que un run histórico no pueda relanzarse a mano.** Ver
  «Limitaciones declaradas».
- **No toca Sirius**, ni su roadmap, ni sus funciones de ingeniería.
- **No elige herramienta de memoria** ni reabre nada sobre las rondas del motor.

**3. Criterio de parada (escrito ANTES de implementar).**

- **(a)** Si el inventario encuentra **una orden pendiente o una ejecución en
  curso** en cualquiera de los dos carriles, se para y se propone su tratamiento
  antes de desactivar nada. *No se disparó*: el inventario no encontró ninguna.
- **(b)** Si desactivar exigiera cambiar permisos, variables de repositorio o
  reglas de protección, se para. Sortear un permiso no es desactivar un carril.
- **(c)** Si una entrada retirada pudiera quedarse **esperando** o **caer en
  programación**, el diseño se rechaza aunque pase las pruebas.
- **(d)** Si hiciera falta tocar los revisores, el corrector, la convergencia o
  Quality, se para: el encargo los conserva.

**4. ¿Qué haría imposible el error más probable, en vez de improbable?** El error
más probable es dejar una entrada abierta que nadie mire — la trampa del punto 1.
Lo hace imposible una prueba que **enumera las entradas desde el árbol** y exige
que cada una esté cubierta: si mañana alguien añade un disparador nuevo a
cualquiera de los dos carriles y no lo cierra, la prueba cae. Una lista escrita a
mano en un ADR no lo haría: se queda vieja el día que alguien añade un workflow.
Lo que **no** se puede hacer imposible desde el repositorio: que una persona con
permisos relance a mano un run antiguo desde la pestaña Actions.

## Inventario de entradas (paso 0 de ADR-161), medido el 08-09-2026

| Entrada | Carril | Mecanismo comprobado | Tratamiento |
|---|---|---|---|
| `sirius-despachar` / `despachar-orden.yml` | ambos | `dispatch_work_item` acepta la clase si está en `TABLA_ACTIVACION` | **Se cierra**: el despachador rechaza la clase retirada con un error propio y explicado |
| Intérprete de intención | ambos | clasifica «investiga…» y «audita…» a esas clases (ADR-043) | Se conserva: clasificar no es despachar; el rechazo llega después, con explicación |
| Etiqueta `auditoria:solicitada` | auditoría | `audit-sirius-repository.yml`, `if: github.event.label.name == 'auditoria:solicitada'` | **Se cierra**: el workflow no ejecuta el modelo; publica la explicación |
| Etiqueta `sirius:implement-requested` con `Perfil: investigador@N` | investigación | `investigar-orden.yml`, `if: github.event.label.name == 'sirius:implement-requested'` + reparto por perfil | **Se cierra**: no investiga; publica la explicación y deja la incidencia en un estado terminal |
| Puerta del implementador | investigación | `implement-sirius-work.yml` declina el perfil ANTES de consumir el evento | **Se conserva, con su motivo reescrito**: sin ella la activación caería en programación. Es la decisión que ADR-161 dejó pendiente, resuelta aquí con esta evidencia |
| Supervisión y reintento del motor | investigación | `INVESTIGACION` tiene autoridad `MOTOR` (`domain/authority.py:61`), así que `supervise_runs` la vigila y `_reactivar_o_sustituir` puede reactivar un Run | **Se cierra en el origen**: sin despacho nuevo no nacen Runs nuevos. Los Runs históricos siguen legibles |
| Reconciliador (`sirius_reconcile.sh`) | ninguno | no menciona `auditoria` ni `investigador`; solo actúa sobre estados `sirius:*` del ciclo de programación | Sin cambios |
| `preflight-investigador.yml`, `medir-investigador.yml` | investigación (instrumento) | solo `workflow_dispatch` / `workflow_call`; **no aceptan encargos** | Se conservan, y se declaran como entrada manual que sigue existiendo |

**Órdenes pendientes y ejecuciones en curso: ninguna.** El diario del motor tiene
seis WorkItems de estos carriles parados en `active`/`preparar`
—`WI-20260828-054330`, `WI-20260828-112416`, `WI-20260828-122242`,
`WI-20260831-130547`, `WI-20260831-130914` y `WI-20260831-131457`—, pero sus seis
incidencias (386, 389, 392, 481, 482, 483) **están cerradas**: ninguna figura
entre las 17 incidencias abiertas del repositorio, y ninguna abierta lleva
`auditoria:solicitada` ni un perfil `investigador`. No son trabajo vivo: son el
hueco que ADR-136 y ADR-101 describen —el motor despachaba y no volvía a
enterarse del desenlace—. **No se tocan**: ni se cancelan ni se borran.

## Decisión

1. **Un registro versionado, `docs/implementation/work_engine/carriles_retirados.yml`**,
   es la única fuente de verdad de qué carril está retirado y con qué mensaje.
   Dato, no código, como `registro_capacidades.yml` y `manifiesto.json`.
2. **El despachador rechaza la clase retirada** con `CarrilRetiradoError`, que
   lleva el motivo y a dónde va ese trabajo ahora. No nace ningún WorkItem nuevo.
3. **`TABLA_ACTIVACION` no pierde ninguna fila**, y el contrato §11.1 tampoco.
   La clase sigue existiendo y descrita; lo que cambia es que está retirada. Así
   el registro sigue siendo verdad y la reactivación es quitar una línea.
4. **Los dos workflows responden y terminan.** Ninguna activación queda
   esperando: el auditor publica la explicación sin ejecutar el modelo, y el de
   investigación publica la explicación y deja la incidencia en
   `sirius:failed-safely`, que es terminal y no reentra en el ciclo.
5. **La puerta del implementador se conserva**, con el comentario reescrito: ya
   no dice «lo atiende investigar-orden.yml», dice que el perfil está retirado y
   que por eso este workflow sigue sin consumir el evento. Quitarla haría que la
   activación cayera en programación.
6. **Nada se borra.** Perfiles, prompts, scripts, workflows, informes,
   `docs/investigaciones/`, ADR y diario se conservan enteros.

## Limitaciones declaradas

- **Relanzar ejecuciones históricas.** Una persona con permisos puede volver a
  lanzar desde Actions un run antiguo de `investigar-orden.yml` o de
  `audit-sirius-repository.yml`. Esta desactivación **no lo impide**: un re-run
  reejecuta el YAML del commit de aquel run, no el de `main`. Impedirlo exigiría
  borrar los workflows —que no es reversible— o cambiar permisos, que el encargo
  prohíbe. Queda dicho, no resuelto.
- **`preflight-investigador.yml` y `medir-investigador.yml`** siguen lanzables a
  mano y gastan cuota de APIs del propietario. No aceptan encargos, así que no
  son un carril; su retirada, si se quiere, es decisión aparte.
- **La etiqueta `auditoria:solicitada` no se borra.** Aplicarla seguirá
  disparando el workflow, que ahora responde que el carril está retirado. Borrar
  la etiqueta es configuración de GitHub y queda fuera.

## Cómo se revierte

Quitar del registro la entrada del carril —una línea— y fusionar. No hay que
tocar código, ni workflows, ni pruebas: el despachador vuelve a despachar esa
clase y los dos workflows vuelven a atenderla. Es la propiedad que ADR-161 pedía.

## Comprobación que la sostiene

Se rellena en el commit que la produce, con las cifras reales.

## Consecuencias

- El contrato operativo describe en §13 el resultado previsto al fusionar.
- Los bloques S2, B1 y C4 pasan de «retirada acordada» a «retirada ejecutada al
  fusionar», sin cambiar de estado ni perder su evidencia.
- Queda pendiente y sin fecha cualquier borrado definitivo, que sería otro ADR.
