# Nota de arranque — una contradicción de etiquetas no es una divergencia

Fecha: 2026-08-27. Publicada ANTES del primer cambio de código, como exige
ADR-001.

## Lo que ya está medido, y de dónde sale

Leyendo el registro real de la racha en la rama de memoria
(`estado-del-motor:racha_siete_dias.jsonl`), las seis líneas de la única pasada
registrada dicen lo mismo:

```
{"clase": "programacion", "ejes": [
   {"eje": "fase",   "motivo": "motor=<WorkItemPhase.PREPARAR> incidencia=None", "resultado": "divergencia"},
   {"eje": "estado", "motivo": "motor=<WorkItemState.ACTIVE>   incidencia=None", "resultado": "divergencia"}],
 "instante": "2026-08-26T04:07:12Z", "work_id": "WI-20260825-225310"}
```

`WI-20260825-225310` es la incidencia #353, y #353 lleva **dos etiquetas de
estado a la vez**: `sirius:failed-safely` y `sirius:completed`.

`mirror_projection._estado_y_fase` trata eso como corresponde —no elige una
ganadora en silencio— y devuelve `(None, None, True)`: estado desconocido, fase
desconocida y **`etiquetas_contradictorias = True`**. El dominio lo documenta
con estas palabras: *«expone la contradicción en vez de que el espejo elija una
etiqueta ganadora»*.

Y entonces:

```
$ grep -rn etiquetas_contradictorias src/sirius_engine/projection_verifier.py \
                                     src/sirius_engine/seven_day_streak_cli.py \
                                     src/sirius_engine/authority_reversion.py
(sin resultados)
```

**Nadie lee el aviso.** El campo se calcula, se documenta y se prueba, y ningún
consumidor lo consulta. Es el séptimo caso de la enfermedad de esta casa, y por
primera vez no es una función sin llamante sino **un dato sin lector**.

## Por qué importa, y no es una cuestión de estilo

`projection_verifier._comparar` recibe `espejo=None` y, como `motor != None`,
escribe `DIVERGENCIA`. Río abajo, `authority_reversion` revierte la autoridad de
una clase **a la primera divergencia registrada tras la conmutación, sin
esperar a la segunda** (contrato §11.4).

O sea: en cuanto una clase esté conmutada, que alguien deje dos etiquetas
pegadas en una incidencia devolvería el mando a la vía GitHub, y el aviso diría
`motor=<ACTIVE> incidencia=None` —que se lee como «el motor está
desincronizado»— cuando lo que pasa es que **la incidencia lleva dos etiquetas
que se contradicen**.

Es un rojo que miente, la misma familia que el 503 de ayer, y con el mismo coste:
manda a arreglar lo que no está roto.

## Las cuatro preguntas

1. ¿La prueba nueva se ve **FALLAR antes** del cambio, y falla por el motivo
   correcto —registra `DIVERGENCIA` donde debería registrar `NO_COMPARABLE`— y
   no por cualquier otro?
2. ¿Sigue siendo `DIVERGENCIA` el caso distinto de «la incidencia no lleva
   NINGUNA etiqueta `sirius:*`»? Eso **no** puede cambiar: una incidencia sin
   etiquetas es un hecho observado, no una lectura fallida.
3. ¿El día sigue sin poder salir **verde**? Hay que verlo ejecutando, no
   suponerlo: si `NO_COMPARABLE` contara como verde, este arreglo cambiaría un
   rojo que miente por un verde que miente, que es peor.
4. ¿La reversión de autoridad deja de dispararse con una contradicción **y sigue
   disparándose con una divergencia real**? Las dos mitades, o no vale.

## Criterio de parada

- **(a)** Si al hacer `NO_COMPARABLE` la contradicción un día pudiera contar
  como verde, se para: el arreglo estaría mal planteado.
- **(b)** Si aparece algún consumidor de `etiquetas_contradictorias` que no vi,
  se para y se replantea sobre lo que ese consumidor espera.
- **(c)** Si arreglarlo exigiera tocar el contrato, la tabla de autoridad o
  conmutar cualquier clase, se para: eso es un acto del propietario (§11.3), no
  una decisión de implementación.
- **(d)** Si dos rondas seguidas dejan defectos de la misma familia, se para y
  se busca la raíz en vez de seguir parcheando (ADR-001, regla de las dos
  rondas).

## Lo que este trabajo NO toca

No conmuta ninguna clase, no cambia el contrato, no toca la tabla de activación
y no intenta arreglar el segundo hallazgo de esta lectura —que el motor no
aprende nunca el desenlace de lo que despacha—, que se registra aparte con su
evidencia.
