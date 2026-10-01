# ADR-224 — Quality no muere por un `uv sync` sin caché: los dos pasos largos llevan plazo propio y el job sube de 20 a 50 minutos

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR #669 por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-01-quality-no-muere-por-un-sync-lento.md`,
  confirmada en `bbd7e38d` antes del primer commit de arreglo, con las
  predicciones y el criterio de parada.

## Contexto y problema

Quality (`.github/workflows/quality.yml`) tenía `timeout-minutes: 20` en el job
y ningún plazo por paso. El 01-10-2026 tres ejecuciones murieron **canceladas**
a los 20 minutos, sobre dos PR de la Fase 2 (#666 dos veces, #667 una), con el
paso «Sync environment» entre 11 y 16,5 minutos. Leído de la API de Actions
(pasos de cada job):

| Hora (UTC) | Rama (PR) | Sync environment | Pytest | Desenlace |
|---|---|---|---|---|
| 07:52 | `claude/el-motor-dice-lo-que-hace` (#666) | 15 m 46 s | cancelado a los 3 m 57 s | cancelled |
| 08:10 | `claude/la-cola-regenera-la-memoria` (#667) | 16 m 30 s | cancelado a los 3 m 12 s | cancelled |
| 08:15 | `claude/el-motor-dice-lo-que-hace` (#666) | 11 m 47 s | cancelado a los 7 m 54 s | cancelled |
| 08:01 | `claude/mina-de-septiembre-entero` (#665) | 8 m 0 s | 10 m 28 s | success, 19 min en total |
| 08:29 | `claude/la-referencia-de-cierre-se-sigue-desde-main` (#668) | 8 m 28 s | no llegó: falló antes `ruff format` | failure |

Con la caché de `setup-uv` restaurada, el mismo paso tarda **2-4 s** (las otras
ocho ejecuciones del día). El registro de la ejecución de las 08:29 dice qué
hace el paso sin caché: descarga 58 paquetes, 243 MiB solo de PySide6
(`pyside6-addons` 167 MiB, `pyside6-essentials` 76 MiB), «Prepared 58 packages
in 8m 26s». Ese día PyPI servía a menos de 1 MB/s.

La cadena que convierte una lentitud en un bucle:

1. La caché de Actions solo se restaura desde la misma rama o desde `main`, y
   la entrada de `main` dejó de restaurarse de forma fiable: a las 08:28 una
   ejecución la restauró en 3 s y a las 08:29 otra, en la misma rama, no.
2. `setup-uv` (v8.3.2, la versión fijada) solo **guarda** la caché si el job
   termina bien (`post-if: success()`).
3. Una rama cuya primera ejecución se cancela por tiempo no tiene caché propia
   nunca, y la siguiente vuelve a descargar y a cancelarse. #666 lo demostró
   dos veces seguidas (07:52 y 08:15).

Coste medido: **60 minutos de runner tirados** y dos PR paradas (la fusión del
motor exige Quality verde, ADR-205). Desde el 01-09 hay 12 ejecuciones
canceladas de Quality: las 3 de hoy; 3 más (08-09 en `main`, 20-09, 21-09) en
las que Pytest solo rozó el tope (19 m 20 s a 19 m 37 s); y 6 del 13-09 que son
otra familia (`sync` de 3 s y Pytest cortado entre 0 y 4 min: canceladas por un
push nuevo o a mano).

Y una cancelación no dice nada. El propio `quality.yml` ya lo aprendió con
`apt` el 19-08 (#202, #206) y le puso plazo propio a ese paso para que fallara
con `failure`, diagnosticable, en vez de llevarse el job entero a `cancelled`.
Los dos pasos largos no tenían ese plazo.

## Criterio de parada (escrito ANTES de decidir)

Copiado de la nota de arranque:

- El cambio se queda si la primera ejecución de Quality de la propia rama, que
  no tiene caché propia, termina (verde, o roja por algo que no sea el tiempo)
  y la siguiente restaura la caché en menos de 10 s.
- Si con los topes nuevos vuelve a cancelarse, la causa es otra y se para a
  buscarla en vez de subir más el número.
- No se toca la lista de dependencias ni la batería: eso sería otra decisión,
  con su propia nota.

## Opciones consideradas

1. Subir solo el tope del job. Barato, pero una descarga colgada seguiría
   muriendo como `cancelled`, sin diagnóstico: justo lo que el paso de `apt`
   enseñó que no se hace.
2. **Plazo propio en los dos pasos largos y un tope del job que los cubra a los
   dos** (la elegida).
3. Quitar `pyside6-addons` (167 MiB) de las dependencias: toca la lista de
   dependencias y la GUI; otra decisión, fuera del criterio de parada.
4. Reintentar la descarga o cambiar de índice: la velocidad de PyPI no está en
   nuestra mano y un reintento dentro del mismo tope no compra tiempo.
5. Guardar la caché aunque el job no termine bien: `setup-uv` no ejecuta su
   `post` en un job cancelado, y guardar cachés de ramas rojas llenaría antes el
   límite de 10 GB que ya expulsa la de `main`.

## Decisión

En `.github/workflows/quality.yml`:

- el job pasa de `timeout-minutes: 20` a **50**;
- «Sync environment» lleva `timeout-minutes: 20` (peor medido sin caché:
  16 m 30 s);
- «Pytest» lleva `timeout-minutes: 25` (peor medido: 19 m 37 s; hoy tarda
  9-10,5 min);
- el resto del job (checkout, Qt, uv, ruff, mypy) tarda menos de 3 min:
  20 + 25 + 5 cabe en 50.

Los tres números llevan al lado, en el YAML, la razón y la fecha, como el paso
de `apt`. Nada más cambia.

## Comprobación que la sostiene

- `tests/automation/test_quality_no_muere_por_un_sync_lento.py`, dos pruebas
  que leen el YAML real: los dos pasos largos tienen plazo propio por encima de
  lo medido (17 y 20 min), y el tope del job cubre la suma de los dos más 5 min
  del resto. Las dos en verde.
- Mutaciones sobre el YAML, con la prueba ejecutada y el fichero restaurado:

| | Mutación | Resultado |
|---|---|---|
| M1 | el job vuelve a 20 min | cae `el_tope_del_job_de_quality_cubre_los_dos_pasos_largos_y_el_resto` |
| M2 | «Sync environment» pierde su plazo propio | caen las dos |
| M3 | el plazo de «Pytest» baja a 15 min, por debajo de lo medido | cae `los_dos_pasos_largos_de_quality_tienen_plazo_propio_por_encima_de_lo_medido` |

- Las pruebas que leen los `timeout-minutes` reales de todos los workflows
  siguen en verde (`tests/automation/test_contador_de_siete_dias.py`,
  `tests/automation/test_sirius_reconcile.py`,
  `tests/automation/test_automatizacion_congelada_de_main.py`: 76 passed). La
  tolerancia del contador de los siete días (`max(timeout-minutes) × 2`) no
  cambia, porque el máximo sigue siendo 85.
- El YAML carga; `ruff` y `mypy` sobre la prueba, sin avisos.
- La medida del criterio de parada es la primera ejecución de Quality de la PR
  #669, sin caché propia. La fusión por aprobación dual exige Quality en verde
  sobre la cabeza fusionada, así que este ADR no puede entrar en `main` sin
  haberla superado; el resultado queda en la PR.

## Consecuencias

- Una ejecución sin caché termina (unos 25-30 min con PyPI lento) en vez de
  morir a los 20; al terminar bien guarda la caché de su rama y la siguiente
  vuelve a 3 s.
- Solo pagan más las ejecuciones lentas: una normal sigue en 12 min. Un run de
  30 min que termina vale más que uno de 20 que no.
- Un paso que se cuelga falla con `failure` y diagnóstico, no con `cancelled`:
  lo primero el motor sabe tratarlo (ADR-183); lo segundo le para el bloque.
- La causa de fondo (la caché de `main` que se expulsa y PyPI lento) no está en
  nuestra mano; si con estos topes vuelve a cancelarse, el criterio de parada
  manda buscar la causa, no subir el número.
- H-224 en el registro de defectos.

## Alternativas descartadas y por qué

Las opciones 1, 3, 4 y 5 de arriba: la 1 porque repite el error de la
cancelación muda; la 3 porque es otra decisión; la 4 porque no compra tiempo;
la 5 porque la acción no lo ofrece y empeoraría la expulsión.

## La lección

- familia: `paso-largo-sin-plazo-propio`
- sin esto se repetiría: dejar que el tope del job sea el único plazo de un paso que depende de la red, y descubrirlo en una cancelación muda que no guarda caché y se repite sola; es la misma lección que el paso de `apt` dejó escrita el 19-08, aplicada esta vez a los dos pasos que quedaban.
- lo hace cumplir: `tests/automation/test_quality_no_muere_por_un_sync_lento.py`
