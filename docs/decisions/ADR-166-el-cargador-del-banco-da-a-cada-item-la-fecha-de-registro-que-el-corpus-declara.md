# ADR-166 — El cargador del banco da a cada ítem la fecha de registro que el corpus declara

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de esta PR por el propietario.

## Nota de arranque (publicada ANTES del primer commit de código)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en el
   cargador del banco —`_load_canon_item`,
   `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`—, que crea los 97
   ítems del canon llamando a los casos de uso reales y deja, por tanto, el
   `created_at` que el reloj de la máquina pone: **todos con la fecha del día
   en que se mide**. El arreglo va **en el mismo sitio**, y por eso hay que
   decir por qué puede funcionar: el sitio del arreglo SÍ puede observar el
   fallo, porque `created_at` no es un estado interno del cargador sino una
   columna de la base que el puerto real lee
   (`src/sirius/adapters/persistence/staged_engine_port.py:138` y `:158`); una
   prueba puede abrir la base cargada y comparar columna a columna con lo que
   el corpus declara, y hoy sale la fecha de la ejecución. El arreglo **no**
   va en `G8` ni en el puerto: la puerta compara bien, lo que estaba mal era
   el dato que se le daba (ADR-148, hueco H2).
2. **¿Qué NO va a garantizar esto?** No garantiza que `ejes_p2.valid_from`
   sea la fecha de registro «verdadera» de cada ítem: es la única fecha que el
   corpus congelado declara por ítem, y el corpus no separa registro de
   vigencia. No cierra H1, H3 ni H4. No adelanta ni corrige la derivación de
   ejes en el puerto (incidencia #572), que sigue parada. No abre
   `category_matching_enabled`. No cambia nada del producto: en producción
   `created_at` ya es la fecha real de registro, así que ningún usuario ve
   diferencia — esto corrige el **arnés**, no el producto. Y no garantiza que
   ninguna otra métrica del banco se mueva: si se mueve, se transcribe y se
   explica caso a caso, no se ajusta ninguna cota.
3. **Criterio de parada (decidido ANTES de ver ningún resultado).**
   - Si el motivo del descarte de `DEC-012` en `B04-CA-32` **antes** del
     cambio NO es `G8` «posterior al corte de registro», la premisa de
     ADR-148 H2 es falsa: se para y se registra, no se sigue.
   - Si el suelo sin ejes derivados —`--peticion`: `16/47; 162; 73/81; 0`—
     **empeora** en cualquiera de las cuatro métricas, se para y se registra
     el número tal cual.
   - Si `B04-CA-32` no pasa de fallar a acertar, o pasa por un motivo
     distinto de `G8`/corte de registro, se para y se registra.
   - Si cerrar el hueco exigiera tocar `G8`, el puerto, el corpus o
     `resultado_esperado`, se para y se pide decisión: está fuera de alcance.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Que ningún ítem del
   banco pueda nacer con la fecha del reloj. Se hace de la única forma que lo
   consigue por construcción: la fecha se fija **dentro del propio cargador**,
   en el mismo punto donde se crea el ítem y antes de devolverlo, y la prueba
   recorre **los 97 ítems del canon**, no una muestra, comparando `created_at`
   con lo que el corpus declara para cada uno. Lo que NO queda imposible, y se
   dice: que alguien escriba un cuarto arnés que llame a los casos de uso sin
   pasar por el cargador. Reunir en un único bucle las tres cargas que hoy
   existen (`_ejecutar_banco`, `_ejecutar_banco_motor_portado`,
   `_ejecutar_banco_paquete_completo`) es un refactor que esta incidencia no
   autoriza; queda dicho aquí en vez de simulado con una garantía que el
   alcance no puede dar.

## Contexto y problema

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

## Decisión

## Comprobación que la sostiene

## Consecuencias

## Alternativas descartadas y por qué
