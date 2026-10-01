# ADR-229 — Los instantes de G8 se comparan en una sola forma canónica, sean cuales sean sus escrituras

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de su PR por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-01-los-instantes-de-g8-se-comparan-en-una-sola-forma.md`,
  confirmada en `285b0c77` antes del primer commit de arreglo, con las cuatro
  preguntas, las predicciones y el criterio de parada.

## Contexto y problema

La puerta `G8` del motor por etapas (`src/sirius/domain/staged_engine_gates.py`)
decide la aplicabilidad temporal de una candidata comparando **cadenas**:
`created_at > corte_de_registro`, `valid_from > tiempo_objetivo`,
`valid_to <= tiempo_objetivo`. El repositorio escribe los instantes de dos
maneras: `created_at` llega de SQLite como `str(datetime)`
—`2026-03-20 09:00:00.000000`, separador espacio, y sin fracción cuando los
microsegundos son cero— y el corpus, el intérprete (`_ahora_como_lo_declara_el_corpus`)
y el clasificador escriben `2026-03-20T00:00:00Z`. El espacio (0x20) ordena
antes que la `T` (0x54), y el `+` de `+00:00` antes que la `Z`: dos escrituras
del mismo instante admitían conjuntos distintos.

Hasta hoy funcionaba por convención de los **emisores**: el clasificador
reescribe el corte en la forma de `created_at` y el intérprete alinea el
«ahora» con la `Z` del corpus, porque los encargos que lo encontraron
(#570, #577, #581) tenían prohibido tocar la puerta. La bitácora lo registró
como deuda 20 y, a la tercera aparición (entrada 69), nombró la raíz: «el
repositorio tiene DOS formas canónicas de escribir un instante, las compara
por orden léxico en SQL crudo, y no hay ningún tipo que impida mezclarlas.
Cada comparación nueva es una tirada de dados». Dejó tres opciones para el
propietario: (a) `datetime` en el contrato con migración; (b) el contrato en
`str` con una forma canónica única garantizada y un guardián; (c) dejarlo.
El 01-10-2026 el propietario delegó («haz lo que me recomiendas»); la
recomendación era la (b).

El caso que ordenaba mal, en Python: `"2026-03-20 09:00:00.000000" >
"2026-03-20T00:00:00Z"` es `False`, así que un elemento registrado a las nueve
de la mañana pasaba un corte de registro de medianoche del mismo día.

## Criterio de parada (escrito ANTES de decidir)

Copiado de la nota de arranque:

- Si la forma canónica exigiera cambiar el tipo del contrato (`created_at:
  str`) o la escritura de `created_at` en SQLite, parar: eso es la opción (a).
- Si el banco se moviera en el motor por etapas, no se entrega sin explicar
  cada caso que cambia.
- Tres mutaciones tienen que caer: M1 `G8` vuelve a comparar las cadenas
  crudas; M2 la forma canónica deja de ser de ancho fijo; M3 un desfase
  distinto de cero se ignora en vez de convertirse a UTC.
- Dos rondas de revisión externa con defectos de la misma familia → raíz.

Ninguna de las dos primeras paró: el contrato y SQLite no se tocan, y el
banco no se movió en ninguna cifra.

## Opciones consideradas

1. Dejarlo (la opción c): cada emisor nuevo paga su ronda, y la frontera
   depende de la escritura.
2. **La opción b, en el comparador** (la elegida): un módulo de dominio sin
   E/S, `sirius.domain.instantes`, que lleva cualquier escritura reconocible a
   una forma canónica —UTC, ancho fijo, `AAAA-MM-DDTHH:MM:SS.ffffffZ`— en la
   que el orden léxico es el cronológico; `G8` compara eso. Un texto que no es
   un instante se compara tal cual, como antes.
3. La opción a: `datetime` en `ItemCanonico.created_at` y en la
   `VentanaTemporal`, con migración de todo lo que construye y lee esos
   campos. Más tipo, más trabajo, mismo efecto en la puerta; queda abierta
   para quien quiera cerrarla, y este ADR no la impide.
4. Normalizar en los emisores (lo que se venía haciendo): el puerto emite
   `created_at` en una forma y cada emisor se adapta. Descartada como
   solución: es exactamente el camino «sin final» que la entrada 69 describe.

## Decisión

1. `src/sirius/domain/instantes.py` (nuevo): `FORMA_CANONICA`
   (`%Y-%m-%dT%H:%M:%S.%fZ`), `en_forma_canonica(texto) -> str | None`
   (reconoce lo que `datetime.fromisoformat` reconoce más el sufijo `Z`: el
   `str(datetime)` de SQLite con y sin microsegundos, ISO con `T`, `Z` o
   desfase, y una fecha sola como su medianoche; sin zona se asume UTC, con
   zona se convierte a UTC) y `comparable(texto) -> str` (la forma canónica,
   o el texto si no es un instante).
2. `G8` lleva los dos lados de cada una de sus tres comparaciones por
   `comparable` antes de comparar. Nada más cambia: ni el contrato, ni el
   puerto SQL (`created_at <= :hasta` sigue con el extremo reescrito en la
   forma de la columna, que es cosa del almacenamiento), ni lo que escriben
   el clasificador y el intérprete.
3. Lo que no es un instante se compara como antes, a propósito: una
   excepción en la puerta tumbaría la consulta entera por un dato ilegible, y
   degradar a la comparación de hoy es lo peor que ya pasaba.

## Comprobación que la sostiene

- `tests/unit/test_instantes_en_una_sola_forma.py`, quince casos: seis
  escrituras del mismo instante dan la misma forma canónica; la forma es UTC,
  de 27 caracteres y ordena como el reloj; una fecha sola es su medianoche; un
  desfase se convierte; lo que no es un instante se compara tal cual; y `G8`
  en la frontera con las formas mezcladas (lo registrado a las nueve no pasa
  un corte de medianoche del mismo día; el corte sigue siendo inclusivo en su
  instante exacto; `+00:00` frente a `Z` son el mismo instante; un `valid_to`
  con desfase expira cuando llega su instante en UTC; con una sola forma el
  veredicto es el de siempre).
- Mutaciones, con los ficheros restaurados (`diff -q` limpio):

| | Mutación | Resultado |
|---|---|---|
| M1 | `G8` de `main` (cadenas crudas) | caen `lo_registrado_a_las_nueve_no_pasa_un_corte_de_medianoche_del_mismo_dia` y `un_valid_to_escrito_con_desfase_expira_cuando_su_instante_en_utc_llega` |
| M2 | la forma canónica sin microsegundos | caen 10 (las seis escrituras, el ancho fijo, la fecha sola, el desfase y lo ilegible) |
| M3 | el desfase se ignora | caen 3 (la escritura `+02:00`, la conversión y el `valid_to` con desfase) |

- Baterías del motor por etapas (`test_staged_engine.py`,
  `test_staged_engine_candidate_por_vigencia.py`, `test_staged_engine_port.py`,
  `test_ollama_query_intent_classifier.py`, `test_interpret_query_request.py`)
  más la nueva: 133 en verde. `ruff`, `mypy src tests` y el comprobador de
  documentos, sin avisos.
- **El banco de 47 casos, antes y después, idéntico**
  (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, las tres pruebas
  que reportan las cuatro métricas): motor por etapas 30/47, 51 de más, 0
  omisiones críticas, 68/81; pipeline M7 10/47, 218, 10, 57/81; paquete
  completo 0/47, 487, 0, 72/81. Era la predicción 2: los emisores ya
  alineaban las formas; lo que cambia es que ya no hace falta que lo hagan.

## Consecuencias

- `G8` deja de depender de cómo escriba el instante cada emisor; un emisor
  nuevo que escriba `+00:00`, omita los microsegundos o traiga un desfase no
  mueve la frontera.
- La deuda 20 queda pagada en el comparador. La reescritura del corte en el
  clasificador y la del extremo de la ventana en el puerto SQL siguen siendo
  correctas y no se tocan; quien las retire tendrá esta puerta detrás.
- La opción (a), tipar los instantes, sigue abierta como mejora de forma, no
  de corrección.
- H-229 en el registro de defectos.

## Alternativas descartadas y por qué

Las opciones 1, 3 y 4 de arriba: la 1 porque deja la tirada de dados; la 3
porque cuesta una migración para el mismo efecto en la puerta; la 4 porque
es el camino que no termina.

## La lección

- familia: `comparar-instantes-como-texto`
- sin esto se repetiría: comparar instantes por orden léxico de cadenas que distintos emisores escriben de distinta forma, y descubrirlo caso a caso en la frontera: tres veces en septiembre (entradas 52, 60 y 69), siempre parcheando al emisor porque el comparador estaba fuera del alcance.
- lo hace cumplir: `tests/unit/test_instantes_en_una_sola_forma.py`
