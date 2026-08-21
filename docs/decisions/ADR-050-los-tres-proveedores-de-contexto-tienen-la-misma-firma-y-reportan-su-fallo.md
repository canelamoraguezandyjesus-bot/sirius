# ADR-050 — Los tres proveedores de `contexto.recuperar` tienen la misma firma y reportan su fallo

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR por el propietario
- Contexto: defecto **H-5**, incidencia [#216](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/216), §H-5 de `docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md`
- Relacionadas: ADR-034 (el espejo marca cada proyección y nunca confunde fallo con ausencia), ADR-036 (una lectura caída no es una ausencia y el llamador tiene que poder distinguirlas), ADR-001 (disciplina de evidencia)

## Contexto y problema

`contexto.recuperar` (bloque A3) responde «¿qué pasó con X?» combinando tres
proveedores deterministas. Su contrato, escrito en el propio módulo, dice:

> Un fallo de lectura en un proveedor NUNCA se convierte en "no hay
> referencias" [...]: se acumula en ``proveedores_fallidos``.

En `main` (`450df1b`) ese contrato se cumplía en **dos de los tres**:

```
$ git show origin/main:src/sirius_engine/context_recall.py | grep -n proveedores_fallidos
 58:    proveedores_fallidos: tuple[str, ...]
263:        proveedores_fallidos=fallidas_arbol + fallidas_incidencias,
```

Falta el historial de git, y **no era un olvido de una línea**: era lo único
que se podía escribir ahí. La asimetría real estaba en las firmas.

| proveedor | ¿lee dentro? | firma en `main` |
|---|---|---|
| 1 `buscar_en_arbol_repo` | sí (`read_text`) | `-> (referencias, fallidas)` |
| 2 `buscar_en_incidencias` | sí (mira `LecturaEstado`) | `-> (referencias, fallidas)` |
| 3 `buscar_en_historial_git` | **no**, la lectura está izada fuera | **`-> referencias`** |

El tercero recibía `entradas_git_log: Sequence[EntradaGitLog]`: un tipo que no
tiene manera de expresar «no pude leer». El fallo vivía antes, en
`leer_historial_git`, que lanza `EspejoIlegibleError` hacia quien construya las
entradas — y ahí se perdía, porque el único destino natural de esa excepción,
para un llamador que quiere seguir respondiendo con lo que sí tiene, es
traducirla a `()`.

Consecuencia medible: quien recibía un `ContextoRecuperado` **no podía
distinguir «git no tenía nada» de «git no se pudo leer»**. Es la familia de
ADR-036, cerrada en dos de tres proveedores: un tercio del mecanismo de memoria
de Sirius no sabía decir que se había quedado ciego.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la incidencia #216 ([comentario del 21-08 05:23
UTC](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/216#issuecomment-5365554193)),
antes de tocar código y antes de ver ningún resultado. Se para y se consulta al
propietario, en vez de seguir, si:

1. Cerrar la asimetría exige **tocar `GitHubMirrorPort`** o hacer que
   `sirius_engine` importe de `sirius` (frontera de `tests/engine/test_boundary.py`).
2. El arreglo obliga a que `recuperar_contexto` **deje de ser determinista**
   (requisito 5 de A3, fijado por `test_recuperar_contexto_es_determinista`).
3. La mutación «quitar el reporte del tercer proveedor» **no** hace caer la
   prueba nueva: entonces la prueba es vacua y se arregla antes de seguir.
4. Aparecen **dos defectos de la misma familia** durante el trabajo → regla de
   las dos rondas: parar de parchear y escribir el patrón.
5. Para conseguir verde hiciera falta relajar, saltar o marcar `xfail`
   cualquier prueba existente.

Ninguna se disparó. Punto 1: no se tocó `GitHubMirrorPort` (solo se **reutiliza**
su `LecturaEstado`) ni la frontera. Punto 2: `test_recuperar_contexto_es_determinista`
sigue en verde sin cambios de aserción. Punto 3: la mutación (a) mata la prueba
nueva, tabla abajo. Punto 5: ninguna prueba se relajó, se saltó ni se borró; dos
existentes se **adaptaron** a la firma nueva conservando todas sus aserciones y
ganando una.

En la misma nota se declaró qué NO garantiza esto, y se mantiene:

- **No** impide mentir: quien quiera puede construir a mano
  `LecturaHistorialGit(estado=OK, entradas=())` y disfrazar un fallo de
  ausencia. Lo que deja de ser posible es que eso ocurra **por defecto**, sin
  que nadie lo escriba.
- **No** distingue tipos de fallo de git (binario ausente, repo corrupto,
  timeout): un único identificador `"historial_git"`, igual de grueso que
  `"arbol:<ruta>"`.
- **No** reintenta ni degrada nada. Solo informa.

## Opciones consideradas

1. **Alargar la línea 263 con un parámetro `fallidas_git` nuevo.** Un
   `Sequence[str]` más en `recuperar_contexto`, rellenado por el llamador.
2. **Que `recuperar_contexto` reciba un lector `Callable[[], Sequence[EntradaGitLog]]`**
   y capture él mismo el `EspejoIlegibleError`.
3. **Igualar las tres firmas**: un tipo de lectura para el historial de git, con
   la misma forma que `LecturaCuerpo`/`LecturaComentarios`, y
   `buscar_en_historial_git` devolviendo `(referencias, fallidas)` como los
   otros dos.

## Decisión

**La opción 3.** Concretamente:

- `LecturaHistorialGit(estado, entradas, error)` — misma forma exacta que
  `LecturaCuerpo` y `LecturaComentarios`, y **reutiliza su mismo
  `LecturaEstado`**. No amplía `GitHubMirrorPort`: el historial de git no se lee
  por la vía GitHub, pero el problema que el tipo resuelve es idéntico, así que
  la forma también. `estado=OK` con `entradas=()` es «leí y no había»; solo
  `NO_DISPONIBLE` es «no pude leer».
- `leer_historial_git_como_lectura(...)`: el **único** punto donde el
  `EspejoIlegibleError` deja de ser una excepción y pasa a ser un dato
  transportable. `leer_historial_git` conserva intacto su contrato de lanzar —
  una excepción es lo que impide la confusión en quien la llame directamente
  (ADR-034), y su prueba no cambia.
- `buscar_en_historial_git(lectura, consulta) -> (referencias, fallidas)`: una
  lectura `NO_DISPONIBLE` da cero referencias **y** `("historial_git",)`.
- La orquestación queda `fallidas_arbol + fallidas_incidencias + fallidas_git`.
- `ContextoRecuperarConfig.entradas_git_log` pasa a `lectura_historial_git`, para
  que la sesión tampoco pueda transportar un historial sin decir si se pudo leer.

El identificador `"historial_git"` **no lleva el motivo del fallo**, y es
deliberado: el motivo de un `git log` caído es el `stderr` del binario, que
cambia entre versiones y máquinas, y `recuperar_contexto` tiene que dar la misma
salida para la misma entrada (requisito 5 de A3). El motivo se conserva en
`LecturaHistorialGit.error` para quien quiera diagnosticar; simplemente no entra
en el valor que se compara.

**Por qué la opción 3 y no las otras dos.** La pregunta de ADR-001 es qué hace
el fallo *imposible* en vez de improbable. Mientras dos proveedores de tres
tengan la firma `-> (referencias, fallidas)` y el tercero no, olvidar el tercero
en la concatenación es el resultado **natural** de leer el código: la línea 263
se lee correcta. Con las tres firmas iguales, el olvido se ve como una asimetría
en una sola línea, al lado de sus dos hermanas. Eso es lo que se compra
cambiando la firma en vez de alargando la línea.

## Comprobación que la sostiene

### 1. La prueba, vista fallar antes del arreglo

Con todo el andamiaje de tipos ya puesto pero la línea de orquestación **sin
tocar** (`fallidas_arbol + fallidas_incidencias`), para que el fallo fuera la
aserción y no un `ImportError`:

```
$ uv run pytest tests/engine/test_context_recall.py -q
>       assert "historial_git" in contexto.proveedores_fallidos
E       AssertionError: assert 'historial_git' in ()
E        +  where () = ContextoRecuperado(consulta='B12e', referencias=(Referencia(tipo='fichero',
E            identificador='PLAN.md:1', fragmento='B12e...rar:canelamoraguezandyjesus-bot/sirius',
E            leido_en=datetime.datetime(2026, 8, 18, 15, 0, tzinfo=datetime.timezone.utc))).proveedores_fallidos

tests/engine/test_context_recall.py:321: AssertionError
=========================== short test summary info ============================
FAILED tests/engine/test_context_recall.py::test_recuperar_contexto_reporta_el_fallo_del_tercer_proveedor
1 failed, 16 passed in 0.94s
```

Ese `assert 'historial_git' in ()` **es** el defecto H-5: el tercer proveedor
avisó de que no pudo leer y el aviso no llegó a ninguna parte.

Tras añadir `+ fallidas_git`:

```
$ uv run pytest tests/engine/test_context_recall.py tests/engine/test_session.py -q
22 passed in 0.11s
```

### 2. Pruebas por mutación

Cada mutación se sembró reescribiendo el fichero desde una copia del texto
original guardada en memoria, nunca con `git checkout --`, y se revirtió al
terminar. Comprobado que el árbol vuelve limpio: `22 passed` al final.

| # | Mutación sembrada | Resultado | Prueba(s) que caen |
|---|---|---|---|
| a | `proveedores_fallidos=fallidas_arbol + fallidas_incidencias` (quitar el tercer proveedor — la exigida) | **CAE** 1 | `test_recuperar_contexto_reporta_el_fallo_del_tercer_proveedor` |
| b | `if True:` en `buscar_en_historial_git` (reportar **siempre** el tercer proveedor — la exigida) | **CAE** 5 | `..._distingue_no_pude_leer_de_no_habia_nada`, `..._no_llama_fallo_a_un_historial_de_git_vacio`, `..._referencia_por_sha_corto`, `..._cita_el_cuerpo_...`, `..._responde_con_referencias_no_con_afirmaciones` |
| c | El adapter se traga `EspejoIlegibleError` y devuelve `OK, entradas=()` | **CAE** 1 | `test_leer_historial_git_como_lectura_convierte_el_fallo_en_no_disponible` |
| d | `return (), ()` ante `NO_DISPONIBLE` (el defecto original, sembrado dentro del proveedor) | **CAE** 2 | `..._distingue_no_pude_leer_de_no_habia_nada`, `..._reporta_el_fallo_del_tercer_proveedor` |

Ninguna resultó equivalente. La (b) es la que impide el arreglo tramposo
«reportar siempre», y la (d) confirma que la propiedad queda fijada también un
nivel por debajo de la orquestación, no solo en la línea que se cambió.

### 3. Validaciones

Las cuatro de `AGENTS.md`, con las rutas tocadas. **La batería completa no se
ejecuta aquí a propósito**: un intento anterior de esta tanda murió con
`exit 137` (OOM) por correr varias baterías completas en paralelo en el mismo
contenedor. La valida Quality en la PR.

## Consecuencias

- Quien reciba un `ContextoRecuperado` puede, por fin, distinguir las dos
  situaciones en los tres proveedores. La familia de ADR-036 queda cerrada en
  este módulo.
- **Cambio de firma público** en `buscar_en_historial_git` y en
  `recuperar_contexto`, y cambio de campo en `ContextoRecuperarConfig`. El único
  llamador de producción es `sirius_engine.session`, ya adaptado. Un llamador
  externo que pasara `entradas_git_log=` recibe un `TypeError` inmediato, no un
  silencio: es el modo de fallo que se prefiere.
- `leer_historial_git` sigue lanzando. Hay ahora **dos** adapters para el
  historial (el que lanza y el que devuelve la lectura), y eso es deliberado:
  quien lee git directamente quiere la excepción; quien orquesta quiere el dato.

### Hallazgo adyacente que este ADR NO arregla

`_resumir_contexto` (`src/sirius_engine/session.py`) construye el texto que ve
el humano en la CLI y **no menciona `proveedores_fallidos` en ningún caso**. Con
cero referencias dice «No encontré referencias para 'X'» aunque los tres
proveedores hayan fallado. Es el mismo agujero de familia ADR-036, pero **un
nivel más arriba y afectando por igual a los tres proveedores** — existía antes
de H-5 y no es lo que la incidencia #216 pide («que el fallo de lectura del
historial de git llegue a `proveedores_fallidos`»). Arreglarlo aquí sería
ampliar alcance por iniciativa propia; queda escrito para que el propietario
decida si abre incidencia.

## Alternativas descartadas y por qué

- **Opción 1 (parámetro `fallidas_git` suelto).** Deja el fallo *improbable*, no
  imposible: el llamador puede olvidarse de rellenarlo y el tipo no se queja.
  Además mantiene la asimetría que causó el defecto, así que el siguiente
  proveedor que se añada volverá a nacer torcido.
- **Opción 2 (`recuperar_contexto` recibe un lector y hace la lectura).** Cierra
  el agujero, pero mete E/S dentro del orquestador, que hoy es una función pura
  sobre datos ya leídos; complica el determinismo (requisito 5) y obliga a las
  pruebas a inyectar lectores donde antes bastaban datos. Se descartó por eso, no
  por incorrecta.
- **Un tipo suma que haga estructuralmente imposible construir una lectura `OK`
  vacía a partir de un fallo.** Sería rediseñar el patrón de lecturas del
  repositorio entero: `LecturaCuerpo`, `LecturaComentarios`, `LecturaMetadatos` y
  `LecturaRunActions` comparten la misma forma opcional. Esta incidencia es de
  gravedad baja y alcance A3; cambiar ese patrón es una decisión del propietario.
- **Meter el `stderr` de git en `proveedores_fallidos`.** Rompe el determinismo
  (requisito 5): el mismo fallo daría salidas distintas en máquinas distintas. El
  motivo vive en `LecturaHistorialGit.error`.
