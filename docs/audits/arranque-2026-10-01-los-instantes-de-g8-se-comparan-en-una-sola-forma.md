# Nota de arranque — los instantes de G8 se comparan en una sola forma

Rama `claude/los-instantes-se-comparan-en-una-sola-forma`, 01-10-2026,
15:50 UTC. Mejora 5 de la lista de la mina de septiembre
(`SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09-30.md`, §10): deuda 20 de la
bitácora (entradas 52, 60 y 69). El propietario la delegó hoy («haz lo que me
recomiendas»); la recomendación era la opción (b) de la bitácora: el contrato
sigue en `str`, pero el comparador trabaja sobre una forma canónica única.
Escrita antes de tocar la puerta.

## La cifra de partida

- La puerta `G8` (`src/sirius/domain/staged_engine_gates.py`) decide la
  aplicabilidad temporal comparando **cadenas**: `created_at > corte`,
  `valid_from > tiempo_objetivo`, `valid_to <= tiempo_objetivo`. El
  repositorio escribe los instantes de dos formas: `created_at` llega de
  SQLite como `str(datetime)` —`2026-03-20 09:00:00.000000`, separador
  espacio, y sin fracción cuando los microsegundos son cero— y el corpus, el
  intérprete y el clasificador escriben `2026-03-20T00:00:00Z`. El espacio
  (0x20) ordena antes que la `T` (0x54) y el `+` de `+00:00` antes que la `Z`.
- Hoy funciona por convención de los emisores: el clasificador reescribe el
  corte en la forma de `created_at` y el intérprete alinea el «ahora» con la
  `Z` del corpus. La bitácora (entrada 69) nombró la raíz: «el repositorio
  tiene DOS formas canónicas de escribir un instante, las compara por orden
  léxico y no hay ningún tipo que impida mezclarlas. Cada comparación nueva
  es una tirada de dados». Tres apariciones de la familia en septiembre.
- El caso que hoy ordena mal, reproducible en Python:
  `"2026-03-20 09:00:00.000000" > "2026-03-20T00:00:00Z"` es `False`, así
  que un elemento registrado a las nueve de la mañana pasa un corte de
  registro de medianoche del mismo día como si fuera anterior.
- Banco de 47 casos sobre `main` (`ee12e27f`), medido antes de tocar nada
  (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, las tres
  pruebas que reportan las cuatro métricas): motor por etapas
  **30/47, 51 de más, 0 omisiones críticas, 68/81**; pipeline M7 10/47, 218,
  10, 57/81; paquete completo 0/47, 487, 0, 72/81.

## Las cuatro preguntas y la predicción

1. ¿`G8` compara dos escrituras cualesquiera del mismo instante como el mismo
   instante, y dos instantes distintos en su orden cronológico, sean cuales
   sean sus formas? Predicción: sí, llevando ambos lados a una forma canónica
   única (UTC, ancho fijo, `AAAA-MM-DDTHH:MM:SS.ffffffZ`) justo antes de
   comparar; un texto que no sea un instante se compara como hoy, para que un
   dato ilegible no tumbe la puerta.
2. ¿El banco se mueve? Predicción: **no cambia ninguna de las cuatro cifras**
   del motor por etapas (30/47, 51, 0, 68/81), porque hoy los emisores ya
   alinean las formas por convención; si se mueve, la convención tenía un
   hueco que la medida enseñará, y se escribe.
3. ¿Queda un guardián? Predicción: una prueba con las formas mezcladas en la
   frontera exacta (espacio frente a `T`, `+00:00` frente a `Z`, un desfase
   distinto de cero, sin microsegundos, fecha sola) que hoy falla y después
   pasa, más la prueba de ancho fijo de la forma canónica.
4. ¿Cuánto cuesta? Predicción: un módulo nuevo de dominio sin E/S, tres
   comparaciones de `G8` y las pruebas; ni el puerto SQL ni los emisores
   cambian lo que escriben.

## Criterio de parada (antes de medir)

- Si la forma canónica exigiera cambiar el tipo del contrato (`created_at:
  str`) o la escritura de `created_at` en SQLite, parar: eso es la opción (a)
  de la bitácora, con migración, y no es lo recomendado.
- Si el banco se moviera en el motor por etapas, no se entrega sin explicar
  cada caso que cambia; si la explicación es que la comparación de hoy
  incluía de más, se entrega con la cifra nueva y el caso escrito.
- Tres mutaciones tienen que caer: M1 `G8` vuelve a comparar las cadenas
  crudas; M2 la forma canónica deja de ser de ancho fijo (sin microsegundos);
  M3 un desfase distinto de cero se ignora en vez de convertirse a UTC.
- Dos rondas de revisión externa con defectos de la misma familia → raíz.
