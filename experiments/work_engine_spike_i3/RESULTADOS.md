# Resultados del spike I3 — patrón de escritura seguro del almacén (incidencia #182)

Código y evidencia desechables (ADR-020): esto **no fija** la representación
definitiva del almacén — depende de I3 **e I4** (ADR-019) y se fija en D2.
Decisión completa, con criterio de parada y límites, en
[`docs/decisions/ADR-026-spike-i3-diario-append-only-con-checksum-e-idempotencia.md`](../../docs/decisions/ADR-026-spike-i3-diario-append-only-con-checksum-e-idempotencia.md).

## Patrón elegido

**Diario append-only con `fsync`, checksum SHA-256 por registro y clave de
idempotencia**, reutilizando directamente el diseño de A1 (`Event` +
`rebuild_state`, `src/sirius_engine/domain/events.py`): el almacén durable no
es más que la MISMA idea de A1 -un diario de instantáneas- escrita a un
fichero en vez de a una lista en memoria, con la validación necesaria para
sobrevivir a un `kill -9` en cualquier punto.

## Matriz punto-de-muerte × resultado

Producida por `tests/engine/test_spike_i3_durability.py::test_matriz_punto_de_muerte_por_resultado`
(para una transición de `WorkItem`) y su réplica
`test_matriz_punto_de_muerte_por_resultado_run` (misma matriz, para la
transición representativa `run_prepared` de `Run` — ver «Cobertura de `Run`»,
abajo), ambas parametrizadas sobre los seis puntos nombrados de
`experiments/work_engine_spike_i3/durable_journal.KillPoint`. Cada punto mata
el proceso escritor **exactamente ahí** (autoterminación con
`os.kill(os.getpid(), signal.SIGKILL)` inyectada en el propio código de
escritura, no un temporizador externo) y comprueba, desde un proceso PADRE
que nunca muere, cuántos registros válidos quedan en el diario tras
reproducirlo. Los seis resultados de la tabla valen igual para ambos tipos
de agregado: el arnés (`writer_process`, `append_durably`, `replay`) es
agnóstico al contenido del registro.

| # | Punto nombrado | Qué se completó antes de morir | Resultado tras reiniciar | ¿Por qué? |
|---|---|---|---|---|
| 1 | `before_open` | Nada; ni siquiera se abrió el fichero | **No ocurrió** (0 registros) | El fichero no existe o queda igual que antes. |
| 2 | `after_open_before_write` | Fichero abierto/creado (0 bytes) | **No ocurrió** (0 registros) | Un fichero vacío no aporta ningún registro al reproducir. |
| 3 | `mid_write_torn` | Escritura truncada a mitad (torn write **inyectado**, no una interrupción real de la syscall — ver «Cómo se simuló», abajo) | **No ocurrió** (0 registros) | La cola no analiza como JSON válido (o, si analizara, el checksum no coincidiría): `replay` la descarta entera. |
| 4 | `after_write_before_fsync` | Registro completo escrito, `fsync` NO llamado | **Ocurrió una vez** (1 registro) | Límite conocido, confirmado empíricamente (ver más abajo): `kill -9` no vacía la caché de páginas del kernel. |
| 5 | `after_fsync_before_close` | Registro completo, `fsync` llamado, `close` NO llamado | **Ocurrió una vez** (1 registro) | `fsync` ya garantizó la durabilidad; `close` es irrelevante para ella. |
| 6 | `after_close` | Escritura completa | **Ocurrió una vez** (1 registro) | Camino de éxito normal. |

Además:

| Caso | Resultado | Prueba |
|---|---|---|
| Reintento de la misma petición lógica tras "reiniciar" (misma `idempotency_key`) | **Ocurrió una sola vez** (1 evento, no 2) | `test_reintento_tras_reinicio_no_duplica_por_idempotencia` |
| Ciclo de vida real encadenado (crear → activar → fallar a salvo) reabierto desde cero | El estado reconstruido coincide exactamente con el que produjo la ejecución en vivo | `test_almacen_durable_reproduce_un_ciclo_de_vida_real` |
| Kill en `mid_write_torn` → reapertura → reintento de la misma petición | **Ocurrió una sola vez** el reintento (1 evento nuevo), preservando cualquier prefijo válido previo | `test_kill_mid_write_torn_reapertura_reintento_preserva_prefijo_y_produce_un_evento` |

**En ningún punto de la matriz el estado quedó "a medias" ni "duplicado".**
Es exactamente uno de los dos resultados permitidos en los quince casos
probados (seis puntos × dos tipos de agregado, más los tres casos
adicionales de la tabla).

### Cobertura de `Run`

La definición aprobada de I3 (`docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md:808`)
exige un esqueleto desechable con `WorkItem` **y** `Run`. La matriz de arriba
se repite íntegra (los mismos seis puntos, el mismo arnés, `writer_process`)
sobre `run_prepared` -la primera transición del ciclo `PREPARED ->
DISPATCHED -> RUNNING -> FINISHED` (§3.3)- en
`test_matriz_punto_de_muerte_por_resultado_run`, con los mismos resultados
que la tabla de arriba (`entity_codec.run_to_dict`/`run_from_dict` codifican
`Run` igual que `work_item_to_dict`/`work_item_from_dict` codifican
`WorkItem`; `rebuild_state`, de A1, ya distinguía ambos tipos de agregado
sin cambios). Esto demuestra que el patrón de escritura durable no depende
del tipo de agregado -es el mismo diario, el mismo `append_durably`, el
mismo `replay`- sin implementar el resto del puerto de `Run` (ver límite
conocido 5, abajo): `DurableJsonlWorkItemStore` sigue sin tener métodos de
`Run`, eso es trabajo de A2.

### Cómo se simuló la escritura truncada (torn write)

Capturar un `kill -9` real a mitad de la syscall `write()` del kernel no es
observable ni reproducible desde el espacio de usuario — por eso el punto
`mid_write_torn` construye deliberadamente un prefijo truncado (la mitad de
los bytes del registro) y lo escribe (con `fsync`, el peor caso: incluso el
prefijo corrupto llega a disco) antes de autoterminarse. Es la forma honesta
de convertir "escritura interrumpida" en un punto NOMBRADO y determinista, en
vez de perseguir una condición de carrera contra el planificador del kernel.

### Recuperar la cola truncada antes de reintentar

La fila 3 de la matriz («No ocurrió») describe el estado justo tras el
`kill -9`, no lo que pasa al reintentar. Detectado en revisión: `replay()`
descarta la cola inválida pero no la elimina del fichero, y
`append_durably()` abre con `O_APPEND` — así que un reintento ingenuo
escribiría su registro nuevo **detrás** de la cola vieja, y ambos se
fundirían en una sola línea rota para `replay`, que seguiría descartándolo
todo, reintento incluido (el reintento nunca "aterrizaba"). Corregido: cada
llamada a `append_durably()` empieza recortando y sincronizando esa cola
inválida (`durable_journal.recover_invalid_tail`, sin intentar reparar
corrupción interna, solo el sufijo que `replay` ya descartaría) antes de
escribir. Probado en
`test_kill_mid_write_torn_reapertura_reintento_preserva_prefijo_y_produce_un_evento`:
kill en `mid_write_torn` → "reapertura" (proceso nuevo) → reintento de la
MISMA petición produce exactamente un evento nuevo, preservando cualquier
prefijo válido anterior al incidente.

### Completar escrituras cortas de `os.write` antes de confirmar el anexo

Detectado en revisión (CODEX-001, ronda 6): `append_durably()` ignoraba el
valor de retorno de `os.write()`. POSIX permite una escritura corta incluso
en ficheros regulares, y una escritura corta real dejaba en disco un
registro con JSON y checksum completos pero **sin** su delimitador `\n`
final -aunque `append_durably` ya hubiera dado el anexo por bueno-. `replay`
trataba esa línea como cola truncada (la misma clasificación que la fila 3
de la matriz) y `recover_invalid_tail` la borraba para siempre en el
siguiente anexo: un registro que el escritor creía confirmado, perdido sin
avisar. Corregido con `_write_all`, que reintenta `os.write()` hasta
completar todos los bytes del registro (o falla explícitamente, sin llamar
a `fsync` sobre una escritura incompleta) antes de seguir. Probado en
`test_escritura_corta_de_os_write_no_pierde_el_delimitador_final`, que
recorta de verdad la escritura de `os.write` (sustituyendo la primera
llamada por `real_write(fd, data[:-1])` vía `monkeypatch`), a diferencia de la
prueba de cola truncada (`test_registro_completo_sin_delimitador_final_se_trata_como_cola_truncada`),
que fabrica el fichero incompleto a mano para probar el lado de `replay`.

## Prueba por mutación (ADR-001 §3, requisito 4)

Dos mutaciones sembradas, cada una vista fallar en un caso concreto:

1. **Quitar la comprobación de checksum** (`test_mutacion_quitar_el_checksum_acepta_un_registro_corrupto`):
   se escribe un registro válido y se altera un byte de uno de sus campos
   (`objetivo normalizado` → `OBJETIVO_ALTERADO_`), manteniendo el JSON
   sintácticamente válido. La implementación real (`replay`) lo descarta: el
   checksum no coincide. Una variante mutada que solo exige `json.loads`
   válido -sin comparar el checksum- lo **acepta como si nada hubiera
   pasado**. Esto demuestra que el checksum cubre corrupción más allá de lo
   que el parseo JSON detecta por sí solo (bit-flips que preservan sintaxis
   válida, no solo truncamientos).
2. **Quitar la comprobación de idempotencia**
   (`test_mutacion_quitar_la_comprobacion_de_idempotencia_duplica`): anexar
   directamente con `append_durably`, saltándose el paso de
   `DurableJsonlWorkItemStore._append` que consulta `idempotency_key` antes
   de escribir, produce **dos registros** para el mismo reintento -exactamente
   la duplicación que el requisito 1 prohíbe-, frente al registro único que
   produce el almacén real con la comprobación puesta.

## Límites conocidos (escritos antes de declarar terminado)

1. **Este arnés NO demuestra que `fsync` sea necesario ante fallo real de
   alimentación o caída del SO.** Es el resultado más importante de la
   matriz: los puntos 4, 5 y 6 dan el MISMO resultado ("ocurrió una vez"),
   con y sin `fsync` de por medio. La razón: `kill -9` mata el proceso, pero
   el kernel **no vacía su caché de páginas** al hacerlo — los bytes que
   `os.write()` ya entregó siguen visibles al releer el fichero en la misma
   máquina, se haya llamado a `fsync` o no. Demostrar la necesidad de
   `fsync` de verdad exige inyección de fallos a nivel de sistema de
   ficheros (`dm-flakey`, ALICE, Jepsen) o un ciclo de alimentación real,
   fuera de alcance de un spike en un runner de CI. Lo que este arnés SÍ
   demuestra es orden y atomicidad de la escritura -registro completo o
   descartado entero, nunca a medias-, que es una propiedad distinta y
   también necesaria.
2. **`fsync` mentiroso.** Si el sistema de ficheros o el disco confirman
   `fsync` sin persistir de verdad, ningún patrón de escritura en espacio de
   usuario puede detectarlo. No cubierto.
3. **Corrupción del medio.** El checksum por registro detecta alteración de
   bytes ya escritos y truncamiento en la cola. `replay` solo descarta la
   línea inválida y todo lo que la sigue como cola truncada por una
   escritura interrumpida si, a la vez, (a) no hay ningún registro completo
   y válido después de ella, y (b) esa línea inválida no termina en su
   propio `\n` -es decir, es el sufijo SIN terminar al final del fichero-.
   Si se da al menos una de las dos señales contrarias -hay un registro
   completo y válido después de la línea inválida, o la propia línea
   inválida sí termina en su `\n` (una línea completa que se escribió
   entera pero cuyo contenido o checksum no cuadra)- no puede ser una cola
   truncada, porque una escritura interrumpida por este escritor solo deja
   basura SIN terminar al final, nunca una línea completa ni un registro
   bueno después de la basura; `replay` lanza `InternalCorruptionError` en
   vez de descartar y perder esos registros posteriores o esa línea
   completa. `recover_invalid_tail`/`append_durably` propagan el error y
   dejan el fichero intacto. No cubre reparación: no hay redundancia del
   medio para reconstruir el registro corrupto en sí, solo detección
   conservadora que evita perder lo que sí sigue íntegro.
4. **Concurrencia multiproceso.** El arnés asume un único escritor. Dos
   procesos anexando al mismo diario a la vez podrían intercalar escrituras
   de forma insegura; no probado ni protegido (sin bloqueo de fichero).
5. **Cobertura parcial del puerto.** El patrón de escritura (diario
   append-only + `fsync` + checksum + idempotencia) se demuestra también
   sobre una transición representativa de `Run` (`run_prepared`, misma
   matriz de seis puntos — ver «Cobertura de `Run`», abajo), pero
   `DurableJsonlWorkItemStore` solo implementa el CRUD de `WorkItem`
   (crear/activar/cancelar/fallar-a-salvo). No implementa el CRUD de `Run`
   (`prepare`/`dispatch`/`confirm_running`/... ni las fases del ciclo
   revisar-reparar). Basta para demostrar que el patrón de escritura vale
   para ambos tipos de agregado; no es una migración de A2.
6. **Rendimiento no evaluado.** `_next_sequence` y la comprobación de
   idempotencia releen el diario entero en cada anexo (O(n) por escritura).
   Aceptable para un spike con ficheros de prueba pequeños; un almacén de
   referencia (A2) necesitaría un índice o una cola en memoria reconstruida
   una sola vez al arrancar, no releer el fichero en cada llamada.

## Comparativa de los patrones considerados

| Patrón | ¿Se implementó y probó? | Encaje con A1 (diario + `rebuild_state`) | Decisión |
|---|---|---|---|
| **Diario append-only + `fsync` + checksum por registro + idempotencia por clave** | **Sí** — arnés completo, matriz de 6 puntos, 2 mutaciones | Directo: A1 YA modela el almacén como un diario append-only de `Event`; esto es esa misma idea escrita a fichero | **Adoptado** |
| Reemplazo atómico (temp + `fsync` + `rename` + `fsync` del directorio) | No | Mal encaje: A1 es un diario de MUCHOS eventos pequeños, no un snapshot único; reescribir el fichero entero en cada transición es O(n) por escritura y contradice el propio diseño append-only de A1 | Descartado sin probar. Candidato razonable para *checkpoints* periódicos de A2 (compactar el diario), no para el camino caliente de cada transición. |
| SQLite en modo WAL, `synchronous=FULL` | No (el contrato del spike lo autoriza explícitamente sin que sea decisión de arquitectura) | Cambia el modelo entero: de "diario de objetos de dominio" a filas relacionales, con mapeo objeto-relacional y un motor de base de datos completo dentro del proceso | Descartado sin probar por ahora: su garantía de durabilidad tiene previsiblemente el MISMO límite #1 de arriba (usa `fsync` por debajo, con la misma exposición a la caché de páginas), a cambio de mucha más complejidad de adopción que el diario que A1 ya tiene. Buen candidato a revisar en A2 si aparecen necesidades de consulta que un diario plano no cubra bien (ADR-019/I4). |
| Registro de intención antes de actuar + reconciliación al rearrancar | Parcialmente absorbido, no como patrón aparte | Para una transición **interna** del almacén (una función pura del dominio + un único anexo) no hay una "acción" separada del "desenlace": la única acción observable ES la escritura durable. Separar intención/acción/desenlace añadiría una segunda escritura donde una basta. | Descartado para el camino interno del almacén. Sigue siendo el patrón correcto para acciones **externas** con efecto en el mundo (p. ej. despachar un `Run` a un Worker remoto) — ahí sí hay una brecha real entre "decidir actuar" y "el mundo confirma"; el dominio de A1 ya modela una forma de esto con `cancellation_status=UNCONFIRMED` en `Run`, fuera del alcance de S1 (S1 es el almacén, no el despacho). |
| Idempotencia por identificador monótono de evento | Sí, como componente del patrón adoptado (no como patrón aparte) | Directo: A1 ya asigna `sequence` monótono en el diario | Adoptado como la mitad "sin duplicación al reproducir" del patrón elegido, vía `idempotency_key` + reproducción del diario. |

## Qué demuestra esto para A2 (sin decidirlo)

Si A2 reutiliza este patrón, hereda gratis: el `Event`/`rebuild_state` de A1
sin cambios, la detección de cola corrupta, y la idempotencia por clave. Lo
que A2 tendría que resolver que este spike deja fuera a propósito: el resto
del puerto (`Run` y las fases), un índice para no releer el fichero entero
por escritura, y el barrido de arranque (arquitectura §3.5) que reconcilia
cada `Run` abierto contra el mundo — ninguno de los dos forma parte de I3.
