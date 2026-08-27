# ADR-096 — Una contradicción de etiquetas no es una divergencia, y confundirlas gasta la salida de emergencia

- Estado: PROPUESTO
- Fecha: 2026-08-27
- Aprobación: la fusión de la PR por el propietario
- Contexto: D1a/D1c, contrato §11.2 y §11.4. Nace de leer el registro real de la
  racha, no de una revisión de código
- Relacionadas: ADR-001 (disciplina de evidencia), ADR-036 (una lectura caída no
  es una ausencia), ADR-077 (la reversión no espera a la segunda divergencia),
  ADR-093 (el registro de la racha vive en la rama de memoria)

## Contexto y problema

El contador de los siete días lleva una sola pasada registrada. Sus seis líneas
—rama `estado-del-motor`, 2026-08-26— dicen todas lo mismo:

```json
{"eje": "estado", "motivo": "motor=<WorkItemState.ACTIVE> incidencia=None",
 "resultado": "divergencia"}
```

`incidencia=None` se lee como «la incidencia no dice nada». Pero una de esas seis
es la **#353**, que lleva `sirius:failed-safely` **y** `sirius:completed` a la
vez.

El espejo hace exactamente lo que debe. `mirror_projection._estado_y_fase`
detecta que hay más de una etiqueta de estado, **se niega a elegir una
ganadora** y devuelve `(None, None, True)`, marcando
`etiquetas_contradictorias`. El dominio lo documenta con estas palabras:
*«expone la contradicción en vez de que el espejo elija una etiqueta ganadora
en silencio»*.

Y entonces:

```
$ grep -rn etiquetas_contradictorias src/sirius_engine/projection_verifier.py \
                                     src/sirius_engine/seven_day_streak_cli.py \
                                     src/sirius_engine/authority_reversion.py
(sin resultados)
```

**Nadie lee el aviso.** El campo se calcula, se documenta y se prueba, y ningún
consumidor lo consulta.

### Por qué esto no es una cuestión de estilo

`projection_verifier._comparar` recibe `espejo=None`, ve que no coincide con el
motor, y escribe `DIVERGENCIA`. Río abajo,
`authority_reversion.evaluar_reversion` revierte la autoridad de una clase **a
la primera divergencia registrada tras la conmutación, sin esperar a la
segunda** (ADR-077, contrato §11.4).

Encadenado: en cuanto una clase esté conmutada al motor —que es justo lo que D1
persigue—, que alguien deje dos etiquetas pegadas en una incidencia **devuelve
el mando a la vía GitHub**, y el aviso que lo justifica dice
`motor=<ACTIVE> incidencia=None`, o sea *«el motor está desincronizado»*.

Es un rojo que miente. Misma familia que el 503 de ayer —el preflight llamó
`NO RESPONDE` a un modelo vivo que estaba ocupado— y mismo coste: **manda a
arreglar lo que no está roto**, y en este caso gasta la salida de emergencia del
contrato en el sitio equivocado.

### La familia, contada

Es el **séptimo** caso de la enfermedad de esta casa, y el primero de una
variante nueva:

| # | pieza | forma |
|---|---|---|
| 1–6 | despachador, H-13, supervisor, `sirius-racha`, `authority_reversion`, el guardián del atestado | **función sin llamante** |
| 7 | `etiquetas_contradictorias` | **dato sin lector** |

Vale la pena separarlas porque se buscan distinto. Una función sin llamante se
encuentra con `grep` del nombre. Un dato sin lector no: el campo *se usa* —se
construye, se serializa, se prueba— y aun así ninguna decisión lo consulta.

## Decisión

**Ante una incidencia cuyas etiquetas se contradicen, el verificador no
compara: declara `NO_COMPARABLE` en los dos ejes y nombra las etiquetas que
chocan.**

Se implementa como **ventana 0** —antes que las cuatro ventanas de tolerancia ya
existentes— porque no es una tolerancia de tiempo ni un caso del ciclo: es que
no hay dato contra el que comparar.

Tres consecuencias, y las tres son deliberadas:

1. **El día sigue sin poder salir verde.** `LineaRegistro.es_verde` exige que
   TODOS los ejes `COINCIDAN`, y un `NO_COMPARABLE` no lo hace. Esto era el
   criterio de parada (a) de la nota de arranque: si `NO_COMPARABLE` contara
   como verde, este arreglo cambiaría un rojo que miente por un verde que
   miente, que es peor, y habría que tirarlo.
2. **La reversión de autoridad deja de dispararse** por un defecto de
   etiquetado, y **sigue disparándose** con una divergencia real. Las dos
   mitades tienen prueba; sin la segunda, el arreglo habría apagado la alarma
   que venía a proteger.
3. **Una incidencia SIN ninguna etiqueta `sirius:*` sigue siendo
   `DIVERGENCIA`.** No es lo mismo. El dominio ya lo dice: una incidencia sin
   etiquetas es *«un hecho observado, no una ausencia de lectura»*. Silenciar
   también ese caso taparía el que de verdad hay que ver.

## Alternativas descartadas

**Elegir una etiqueta ganadora por prioridad.** El espejo ya tiene
`_LABEL_PRIORITY` y podría desempatar. Se descarta: desempatar es inventarse un
estado que la incidencia no tiene, y el resultado sería una comparación que
parece concluyente. La contradicción es información, no ruido.

**Que el contador arregle las etiquetas.** Fuera de su jurisdicción: el contador
no escribe en GitHub (§11.2), y darle permiso de escritura para esto abriría una
puerta mucho mayor que el problema que cierra.

**Dejarlo como estaba y avisar en la documentación.** Es lo que ya había: el
dominio lo documenta desde que se escribió, y aun así el registro real acusó al
motor seis veces. Un aviso que nadie lee no es un aviso.

## Qué no decide este ADR

No conmuta ninguna clase, no cambia el contrato y no toca la tabla de
activación. Tampoco resuelve el **segundo hallazgo** de la misma lectura, que se
registra aparte con su evidencia: el motor no aprende nunca el desenlace de lo
que despacha —cada `WorkItem` tiene exactamente dos sucesos, `creado` y
`activado`, y ninguno más— así que la racha de siete días verdes **no puede
avanzar hoy por construcción**. Eso es alcance nuevo y decisión del propietario.

## Cómo se comprueba

- `tests/engine/test_projection_verifier.py`:
  `test_etiquetas_contradictorias_no_se_registran_como_divergencia`,
  `test_una_incidencia_sin_etiquetas_sigue_siendo_divergencia`,
  `test_una_contradiccion_tampoco_pinta_el_dia_de_verde`.
- `tests/engine/test_authority_reversion.py`:
  `test_una_incidencia_contradictoria_no_revierte_la_autoridad` y
  `test_pero_una_divergencia_real_sigue_revirtiendo`. La primera **no se fía de
  la constante**: construye la línea con `verificar_dia` real a partir de un
  espejo contradictorio y se la da a `evaluar_reversion`. Comprobar que
  `NO_COMPARABLE` está excluido en el código de la reversión no demuestra que la
  línea que llega sea `NO_COMPARABLE`.
- Tres mutaciones vistas caer: quitar la ventana 0, dispararla siempre —que se
  lleva por delante nueve pruebas de las otras cuatro ventanas— y dejar de
  nombrar las etiquetas en el motivo.
