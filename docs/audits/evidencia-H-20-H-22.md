# Evidencia — H-20, H-21 y H-22

Tres defectos de la misma cacería, agrupados aquí porque comparten el mismo
desenlace: **confirmados y no despachados**, cada uno por una razón distinta.

## Las cuatro preguntas, decididas ANTES de medir

1. ¿Sobreviven a una refutación adversarial hecha ejecutando?
2. ¿Cabe cada uno en una sola incidencia?
3. ¿Puede el implementador arreglarlo sin decidir producto?
4. Si la respuesta a (3) es no, ¿qué pregunta concreta hay que responder antes?

## Criterio de parada, escrito antes de ver resultados

- Un hallazgo que **no sobreviva** a los dos refutadores no se registra. Un
  defecto plausible y falso hace más daño que ninguno.
- Un hallazgo que sobreviva pero **exija decidir producto** se registra y **no
  se despacha**: despacharlo sería que el implementador decidiera por el
  propietario, con el agravante de que llegaría envuelto en una PR verde.
- Un hallazgo que sobreviva y **no quepa en una incidencia** tampoco se
  despacha: partirlo es en sí una decisión.
- Y ninguno se queda sin registrar. El registro existe porque el 21-08 cuatro
  defectos encontrados seguían vivos en `main` sin incidencia que los siguiera.

## H-20 — el estado cambia al reabrir

**Afirmación.** El mismo guion da un estado distinto según se lea del almacén
en memoria o del durable reabierto, y la fecha retrocede.

**Comprobación:**

```
MEMORIA:
   registrar_gasto -> cortado=True escalada=None estado=paused
   estado final: active            updated_at: 2026-01-02 00:00:00+00:00
DURABLE (mismo guion):
   estado final en el mismo proceso: active            updated_at: 2026-01-02
   estado tras REABRIR el diario:    needs_decision    updated_at: 2026-01-01
```

**Causa medida.** `cancel_all_live_runs_and_escalate_work_item` anexa el
marcador de corte **antes** de comprobar nada; si el WorkItem no está en
curso, sale por el `return` sin escalar y el marcador queda pendiente para
siempre, porque sólo lo limpia un evento de escalada que ya no llegará.

**Por qué no se despacha (pregunta 3 → no).** El arreglo toca a la vez la
reconciliación de marcadores, la divergencia entre las dos implementaciones del
mismo puerto y la semántica de `now`. **Partirlo es la decisión**, y es del
propietario.

## H-21 — el docstring presume de algo que no hace

**Afirmación.** `store.py` presume, **frente al spike de S1**, de no releer el
fichero por escritura. Lo relee entero en cada anexo.

**Comprobación:**

```
anexos=200  lecturas_completas_del_fichero=199  bytes_leidos=6470505  tamano_final=65090

--- prueba que se ve FALLAR ---
E  AssertionError: releyo el diario entero 49 veces
```

**Por qué no se despacha (pregunta 3 → no).** La frase no es adorno: es la
**justificación de un diseño frente a una alternativa ya medida**. Corregir la
frase obliga a releer esa comparación; corregir el comportamiento es rediseñar
el índice incremental. Elegir cuál de las dos es una decisión, no una tarea.

## H-22 — trabajo nuevo sobre trabajo terminado

**Afirmación.** `_reactivar_o_sustituir()` no comprueba el estado del WorkItem;
`_escalar()`, en el mismo módulo, sí.

**Comprobación:**

```
el supervisor creo ['RUN-1-S2'] sobre un WorkItem en cancelled
el supervisor creo ['RUN-1-S2'] sobre un WorkItem en delivered
```

**Por qué no se despacha (pregunta 3 → no).** Qué debe hacer el supervisor en
cada estado —aplazar, ignorar, informar— es política. La asimetría con
`_escalar()` sugiere la respuesta («ante la duda, informa y no toca»), pero
sugerir no es decidir.

## Lo que este documento NO afirma

Que los tres sean arreglables tal cual. Ninguno se ha intentado arreglar: lo
que está medido es **que ocurren**, no cuánto cuesta que dejen de ocurrir.
Confundir esas dos cosas es cómo nace una estimación falsa.
