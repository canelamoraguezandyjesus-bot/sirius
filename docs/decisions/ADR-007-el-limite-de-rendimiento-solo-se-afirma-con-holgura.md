# ADR-007 — Afirmar el límite de rendimiento en CI solo si hay un orden de magnitud de holgura

- Estado: PROPUESTO
- Fecha: 2026-08-10
- Aprobación: la fusión de la PR por el propietario

## Contexto y problema

PA-025 exige «inicio ≤3 s P95 y operaciones locales ≤300 ms P95» sobre un
conjunto de datos de referencia que el Plan de Pruebas especifica con
precisión: 5.000 mensajes, 500 recuerdos, 100 decisiones versionadas y 10
proyectos históricos con uno solo activo, con un mínimo de 30 repeticiones e
informe de P50 y P95.

Hoy no se mide nada. B12a lo dejó como el único hueco automatizable de todo
V8.1.

El problema no es medir: es **qué se afirma con la medida**. Una prueba de
rendimiento en CI mide el runner compartido de GitHub, no el Windows del
usuario, y ese runner varía entre ejecuciones. Hay dos formas conocidas de
hacerlo mal:

- **Afirmar el límite cuando la medida vive cerca de él.** La prueba pasa a
  fallar de forma intermitente por la carga del runner. Una prueba de
  rendimiento intermitente se acaba silenciando o borrando, y entonces no
  queda ni la medida.
- **Aflojar el umbral hasta que no moleste.** Entonces pasa siempre y no
  demuestra nada; es una prueba vacua con aspecto de garantía.

## Criterio de parada (escrito ANTES de medir)

Publicado antes de ejecutar ninguna medición, que es lo único que lo hace
valer:

1. **Si el P95 medido en el runner es ≤ 10 % del límite del plan**, se afirma
   el límite del plan directamente. Con un orden de magnitud de holgura, un
   fallo significa una regresión real y no un runner lento.
2. **Si el P95 medido queda entre el 10 % y el 100 % del límite**, *no* se
   afirma el límite en CI. Se registra la medida como evidencia, se afirma un
   umbral de regresión declarado como tal —no como el requisito— y PA-025
   queda dependiendo de la máquina real.
3. **Si el P95 medido supera el límite**, es un hallazgo sobre Sirius, no
   sobre la prueba. Se informa y se detiene. **No se afloja el umbral para
   conseguir verde**, que es una de las prohibiciones explícitas del contrato
   operativo §3.2.

Y en cualquiera de los tres casos: la prueba automática **no declara PA-025
superada**. PA-025 se ejecuta formalmente en la máquina del usuario dentro de
V8.4.

## Decisión

Medido, se aplica el criterio sin retocarlo:

- **Inicio → caso 1.** 30,3 ms P95 frente a 3.000 ms es el 1 %. Se afirma el
  límite del plan. `tests/integration/test_local_performance.py` comprueba
  además que la holgura de 10× siga existiendo: si desaparece, el criterio que
  sostiene esta aserción deja de valer y hay que revisarla antes de seguir.
- **Listar decisiones vigentes → caso 1.** 25,8 ms P95 frente a 300 ms es el
  9 %. Se afirma el límite del plan.
- **El resto de operaciones locales → caso 2.** Se miden, se registran y se
  vigilan con un guardarraíl de 1.500 ms **declarado como tal**: caza una
  regresión de orden de magnitud sin volverse intermitente, y no es el
  requisito. Los 300 ms los comprueba PA-025 en la máquina del usuario.

PA-025 **no** queda superada. Queda medida.

## Comprobación que la sostiene

Conjunto de referencia del plan: 5.000 mensajes, 500 recuerdos, 100 decisiones
versionadas y 10 proyectos, uno activo. 30 repeticiones por operación. Tres
pasadas del mismo código sobre la misma máquina, el 10 de agosto de 2026:

| Operación | P95 pasada 1 | pasada 2 | pasada 3 | Límite |
|---|---|---|---|---|
| inicio | 30,3 ms | — | — | 3.000 ms |
| listar decisiones vigentes | 25,4 ms | 22,8 ms | 25,8 ms | 300 ms |
| cargar historial completo | 99,1 ms | 123,1 ms | 120,1 ms | 300 ms |
| listar recuerdos vigentes | 117,4 ms | 122,5 ms | 115,3 ms | 300 ms |
| resumen de conocimiento | 154,5 ms | 132,0 ms | 136,3 ms | 300 ms |
| **construir contexto** | **266,4 ms** | **286,6 ms** | **298,6 ms** | **300 ms** |

La fila que decide es la última: **89 %, 96 % y 100 % del presupuesto en tres
pasadas del mismo código.** No hace falta argumentar que afirmar 300 ms sería
intermitente; está medido que lo sería.

**Hallazgo sobre el producto, no sobre la prueba.** El término dominante está
localizado en el código: `SqliteMemoryRepository.list_current_memories()`
recorre los modelos y llama a `_load_memory()` por cada uno, que a su vez
consulta `_get_current_revision_model()`. Son 501 consultas para 500 recuerdos.
Explica los ~117 ms de esa operación y la mayor parte de los ~221 ms de
construir el contexto, que la invoca a través del ranking de relevancia.

Corregirlo es un cambio de código productivo y no se hace en B12c: se registra
como decisión pendiente del propietario.

Cinco mutaciones verificadas, con el resultado predicho antes de ejecutarlas:
conjunto sembrado a medias, operación local +2 s, inicio +1 s, decisiones
+0,4 s y aislamiento de rutas roto. Las cinco fallan; restaurado, pasan las
cuatro pruebas.

### Un defecto propio, encontrado por la última mutación

La primera versión de la fixture llamaba a `resolve_paths()` confiando en el
`_isolate_platform_dirs` de `tests/conftest.py`. Ese es de ámbito función y la
fixture es de ámbito módulo: pytest construye primero las de mayor ámbito, así
que el aislamiento **todavía no estaba activo** y la siembra escribió 5.000
mensajes en el directorio de datos real (`/root/.local/share/sirius`, 1,6 MB).
Se detectó porque la segunda ejecución falló con «An active, configured project
already exists»: la base persistía entre ejecuciones.

La fixture aísla ahora sus propias rutas y **verifica antes de sembrar** que
`resolve_paths()` cae dentro del temporal. Esa comprobación es la respuesta a
«qué haría el fallo imposible en vez de improbable»: sin ella, la próxima
fixture de ámbito módulo repetiría el error en la máquina de quien la ejecute.

## Lo que esto NO garantiza

- **No sustituye a PA-025.** El runner es Linux en hardware compartido; el
  requisito habla del portátil del usuario con Windows. La prueba automática
  es un guardarraíl de regresión, no la prueba de aceptación.
- **No mide el arranque de la interfaz.** Mide el arranque determinista y sin
  GUI —resolución de rutas, migraciones y composición—, porque el tiempo de
  pintado de PySide6 en un runner sin pantalla no dice nada del arranque real.
  Esa parte queda para B14.
- **No cubre el rendimiento con proveedor real**, que depende de la red y no
  de Sirius.
