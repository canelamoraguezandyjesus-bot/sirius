# Evidencia — Experimento: el filtro de relevancia, fiel a la corrida del laboratorio

**Rama:** `experimento/filtro-fiel-al-laboratorio` · **Fecha:** 2026-09-01
**Estatuto: EXPERIMENTO. No es una propuesta de fusión.** Existe para que el
propietario pueda ejecutar en su máquina, por primera vez, la memoria de Sirius
con el filtro tal y como se midió, y decidir con lo que vea.

## Por qué existe esta rama

El propietario pidió probar la memoria en casa. Antes de que lo hiciera, se
comprobó qué llamada hace hoy `OllamaRelevanceFilterAdapter` y qué llamada hizo
el laboratorio que midió `29/47` (rama `evidence/adr001-spikes`,
`experiments/adr002/modelo_local/`). **No son la misma llamada.** Seis
diferencias, comprobadas leyendo los dos ficheros:

| | Laboratorio (`puerto.py`, `filtro.py`) | `main` antes de esta rama |
|---|---|---|
| Modelo | `qwen3:4b-instruct` (`puerto.py:73`) | `llama3.2` (`composition_root.py:136`) |
| Espera | `10.0 s` (`puerto.py:91`) | `0.05 s` (`composition_root.py:157`) |
| Extremo | `/api/chat` (`puerto.py:320`) | `/api/generate` |
| Formato | esquema JSON impuesto al generar (`filtro.py:139`) | pedido por escrito en el prompt |
| Modo razonador | `think: False` (`puerto.py:316`) | no se envía |
| `temperature` / `num_ctx` | `0.1` / `8192` (`puerto.py:78-86`) | no se envían |

El propio laboratorio declara que el formato impuesto **no es cosmético**:

> «La versión anterior pedía el formato por escrito en la instrucción y confiaba
> en que el modelo obedeciera. **Con un modelo pequeño eso falla.**»

Y sobre el modo razonador:

> «Sin esto, un modelo de la familia Qwen3 escribe su pensamiento antes de
> contestar y estas tareas pasan de segundos a minutos.»

Con esas seis diferencias, una prueba en casa no habría medido la memoria: habría
medido un filtro distinto del que produjo la cifra que se quiere reproducir.

## Nota de arranque

**Escrita antes de tocar el código, tras el diagnóstico de arriba y antes de
ver ningún resultado de ejecución.**

1. **¿Dónde vive el fallo y dónde va el arreglo?** No hay fallo que arreglar: hay
   una divergencia entre dos implementaciones del mismo filtro. El arreglo va en
   `src/sirius/adapters/ollama_relevance_filter.py` (la llamada) y en las dos
   constantes de `src/sirius/composition_root.py` (modelo y espera).
2. **¿Qué NO garantiza esto?** No garantiza que Sirius alcance `29/47`. El
   laboratorio midió sobre su propio corpus con su propio arnés; aquí se ejecuta
   el camino de producción, con el ámbito real de M16 y sin la siembra. Tampoco
   garantiza latencia: se sube la espera a 30 s **a propósito**, sacrificando
   RNF-003 para poder observar la calidad por separado de la velocidad.
3. **Criterio de parada, fijado antes de medir:** el experimento responde una
   sola pregunta — *¿el filtro llega a ejecutarse y descarta algo?*. Si con este
   cambio el registro sigue mostrando «Filtro de relevancia no disponible, se
   falla abierto», el experimento ha fracasado y la causa no eran estas seis
   diferencias. Si el filtro se ejecuta y descarta, el experimento cumple su
   objetivo **sea cual sea la cifra de aciertos**: esa cifra es un dato para el
   propietario, no un aprobado ni un suspenso de esta rama.
4. **¿Qué haría imposible el fallo, en vez de improbable?** Nada de lo que hay
   aquí. La divergencia volverá a abrirse en cuanto alguien toque una de las dos
   implementaciones sin mirar la otra. Cerrarla de verdad exigiría que la corrida
   congelada del laboratorio y el adaptador de producción compartan una prueba
   que falle cuando dejen de coincidir. **Eso no se hace en esta rama** y queda
   escrito aquí como deuda declarada.

## Qué se cambió

- `ollama_relevance_filter.py`: `/api/chat` con `system` + `user`, esquema JSON
  impuesto (`responden`), `think: False`, `keep_alive: 15m`, `temperature: 0.1`,
  `num_ctx: 8192`, y lectura de `message.content`. La instrucción y el esquema se
  portan **literales** del laboratorio, con su cita en el código.
- `composition_root.py`: modelo `qwen3:4b-instruct`, espera `30.0 s`.
- `tests/unit/test_ollama_relevance_filter.py`: los dobles pasan del sobre
  `{"response": ...}` al `{"message": {"content": ...}}` y de la clave `keep` a
  `responden`. **Ninguna prueba cambia de intención**; solo de protocolo.

## Comprobación

- `uv run ruff format --check` y `uv run ruff check` sobre los ficheros tocados: en verde.
- `uv run mypy` sobre el adaptador: sin incidencias.
- `uv run pytest tests/unit`: **1475 pasan**.
- `uv run pytest tests/integration` (sin `test_local_performance.py`): **512 pasan**.
- `uv run pytest tests/unit/test_ollama_relevance_filter.py`: **12 pasan**. Antes
  de acomodar los dobles fallaba **1**, exactamente la que afirmaba el sobre
  viejo — el cambio de protocolo se vio fallar antes de acomodarlo, que es la
  prueba por mutación que ADR-001 pide.

**Lo que NO se ejecutó, y por qué se dice:** `tests/integration/test_local_performance.py`
(el banco de latencia de RNF-003) y `tests/acceptance/` completo no caben en el
límite de tiempo de la máquina donde se preparó esta rama. El de latencia
**mediría peor a propósito**: subir la espera de `0.05 s` a `30.0 s` sacrifica
RNF-003 deliberadamente, que es justo el objeto del experimento. Ninguna de las
dos se declara verde aquí.

## Lo que esta rama NO hace

- No toca `.github/**` (ADR-002 intacto).
- No toca el banco de 47 casos, el corpus, `resultado_esperado` ni ninguna
  adjudicación.
- No abre la puerta `category_matching_enabled`: sigue cerrada por defecto y solo
  abre con el JSON exacto `true` en la configuración local.
- No propone fusionar nada a `main`. Si el experimento resulta útil, el cambio
  entra por el ciclo normal del motor, con su ADR y su revisión.

---
_Generated by [Claude Code](https://claude.ai/code)_

## Añadido: el medidor con Ollama real (`scripts/medir_banco_con_ollama_real.py`)

**Pregunta que responde, y que nunca se había respondido:** ¿cuánto acierta el
camino real de producción sobre el banco de 47 casos **con el modelo puesto**?

Ninguno de los tres arneses del repositorio la responde: el de examen usa la
grabación congelada, `_ejecutar_banco_paquete_completo` usa un doble que
conserva todo, y el de latencia mide tiempos. El guion reutiliza el arnés de
producción **sin reimplementarlo** —única forma de no medir otra cosa por
accidente— y solo le inyecta el adaptador real. Para permitirlo,
`_ejecutar_banco_paquete_completo` gana un parámetro opcional que por defecto
conserva el doble de siempre: ninguna prueba existente cambia de comportamiento.

**Criterio de parada, escrito antes de medir:** una cifra solo vale si el
contador de rendiciones es **cero**. Con una sola rendición, la medición mezcla
consultas filtradas con consultas sin filtrar y no significa nada.

**Defecto encontrado y corregido durante la construcción, declarado porque
importa:** la primera versión contaba las rendiciones leyendo el registro, y
devolvía **cero** aunque el filtro se rindiera en todas las consultas —
`alembic` reconfigura `logging` al migrar y desactiva los `logger` existentes.
Un cero falso ahí es peor que no tener la cifra: haría pasar por válida una
medición inválida, que es exactamente el error que este experimento existe para
evitar. Se sustituyó por un envoltorio que cuenta por identidad del objeto
devuelto, que es exacta: el adaptador devuelve la MISMA tupla al fallar abierto
y una tupla NUEVA cuando el modelo contesta.

**Comprobación:** ejecutado en una máquina sin Ollama, informa `47 llamadas,
40 rendiciones` y declara las cifras no válidas. Antes del arreglo informaba
`0 rendiciones` sobre esa misma ejecución.

## Medición: por qué producción pierde el doble de críticas que el laboratorio

**Pregunta (del propietario, 01-09-2026):** con la misma receta —filtro + categoría,
sin siembra—, el laboratorio (fila 4) pierde 4 críticas del banco y producción
pierde 10. ¿Por qué?

**Instrumento:** `scripts/medir_banco_con_ollama_real.py --diagnostico`. El arnés
de producción ahora devuelve `obtenido_por_caso` y el mapa `real_a_canonico`
(campos opcionales de `_EjecucionDelBanco`, vacíos para todo llamador
anterior); el envoltorio del filtro recuerda qué entró y qué salió en cada
llamada, y cada crítica perdida se clasifica en la etapa donde se perdió:
`NO_ENTRO` (la búsqueda nunca la puso delante del filtro),
`TIRADO_POR_EL_FILTRO` (el modelo la descartó y ninguna regla la rescató) o
`PERDIDO_TRAS_FILTRO`. La correlación llamada↔caso exige exactamente una
llamada por caso, que es el contrato de `_apply_relevance_filter`; el
instrumento se niega a diagnosticar si no se cumple.

**Criterio de parada, escrito antes de ejecutar:** si la mayoría de las pérdidas
adicionales de producción son `TIRADO_POR_EL_FILTRO`, la causa está en la regla
de rescate; si son `NO_ENTRO`, la causa está antes del filtro y el filtro es
inocente.

**Resultado (ejecución en seco, sin Ollama: el filtro falla abierto en todas las
llamadas, así que NADA se tira — solo puede aparecer `NO_ENTRO`):**

| caso | crítica | laboratorio (fila 4) | producción |
|---|---|---|---|
| B04-CA-02 | MEM-002 | OK | **NO_ENTRO** |
| B04-CA-31 | DEC-003, DEC-010, MEM-014, MEM-016, MEM-025 | OK | **NO_ENTRO** (las cinco) |
| B04-CA-33 | DEC-003 | NO_ENTRO | OK |
| B04-CA-34 | DEC-003, MEM-014, MEM-016 | NO_ENTRO | NO_ENTRO |

Laboratorio: 4 perdidas, todas `NO_ENTRO`. Producción: **9 perdidas, todas
`NO_ENTRO`** — sin que el filtro haya descartado ni una. El filtro es inocente:
la diferencia está en la búsqueda. Con Ollama real el propietario midió 10; la
décima es la única que puede atribuirse al filtro y su ejecución con
`--diagnostico` lo dirá.

**La causa, comprobada en el código:** las consultas que producción pierde piden
literalmente *restricciones*:

- B04-CA-31: «Dame todas las **restricciones** esenciales que debo respetar.»
- B04-CA-02: «¿Qué **restricciones** de transporte tengo?»

En el laboratorio, la búsqueda por texto no encuentra nada para ellas (fila 1,
`obtenido = []`); quien las encuentra es el **índice de categoría** (fila 2). Ese
índice guarda, para todo item no ordinario, las palabras con las que alguien
pediría lo crítico —`esencial`, `restriccion`, `critica`, `obligatoria`,
`imprescindible`
(`tests/acceptance/staged_engine_category_and_relevance.py:240-251`, portado
literal de `experiments/adr002/lateral/categoria.py:72-78`)— y la categoría se
**deriva de la criticidad** (`categoria_del_item`, `:268-276`).

Producción activa el índice con la misma regla —alguna palabra del vocabulario
dentro de la consulta (`src/sirius/domain/relevance.py:204-221`)— pero con
**otro vocabulario**: `trabajo`, `personal`, `salud`, `finanzas`, `proyecto`,
`aprendizaje`, `otros` (`src/sirius/composition_root.py:133-135`, fijado por
ADR-116 como etiquetas *provisionales* para M11). Ninguna de esas palabras
aparece en «restricciones esenciales» ni en «restricciones de transporte»: el
índice **no se activa**, solo corre FTS5, y FTS5 no las encuentra, igual que en
la fila 1 del laboratorio.

Es decir: el laboratorio etiquetaba por **criticidad** y producción etiqueta
por **tema**. La palabra con la que el usuario pide lo importante dejó de estar
en el vocabulario, y con ella se fue la pieza que hacía subir la cobertura de
64 a 70 (filas 1→2 del laboratorio).

**Segunda consecuencia de la misma decisión, también comprobada:** la regla de
las críticas RF-25/RF-26 rescata por `category == max_criticality_category`
(`src/sirius/domain/relevance.py:328-372`), y esa categoría en producción es
`"salud"` (`composition_root.py:144`, ADR-116:80). Las 18 críticas del banco
están etiquetadas `personal`, `finanzas`, `proyecto` o `trabajo`; el único item
`salud` (MEM-010) no es crítico. La regla, tal como está cableada, **no protege
ninguna crítica del banco**. En la ejecución en seco esto no pesa (nada se
tira); con el filtro trabajando, es lo que impide rescatar lo que el modelo
descarte.

**Lo que este resultado NO afirma:** no dice qué vocabulario debe tener
producción, ni que ADR-116 estuviera mal en su momento (era provisional y para
otro hito). Dice que, con el vocabulario actual, la receta medida en #117 no
puede reproducirse por construcción, y señala exactamente dónde.

### Resultado en la máquina del propietario (Ollama real, 02-09-2026)

`uv run python scripts/medir_banco_con_ollama_real.py --diagnostico`, modelo
`qwen3:4b-instruct`, espera 30 s: **47 llamadas, 0 rendiciones, 0,4 min** —
medición válida por su propio criterio.

Métricas: 22/47 aciertos exactos, 39 de más, **10 críticas perdidas**, 59/81.

| caso | crítica | laboratorio (fila 4) | producción (propietario) |
|---|---|---|---|
| B04-CA-02 | MEM-002 | OK | NO_ENTRO |
| B04-CA-23 | DEC-003 | OK | **TIRADO_POR_EL_FILTRO** |
| B04-CA-31 | DEC-003, DEC-010, MEM-014, MEM-016, MEM-025 | OK | NO_ENTRO (las cinco) |
| B04-CA-33 | DEC-003 | NO_ENTRO | OK |
| B04-CA-34 | DEC-003, MEM-014, MEM-016 | NO_ENTRO | NO_ENTRO |

**Reparto de las 10: 9 `NO_ENTRO` + 1 `TIRADO_POR_EL_FILTRO`.** Coincide con la
ejecución en seco en las 9 de búsqueda; la décima solo podía verse con el
filtro vivo y es exactamente la que la regla de rescate debería haber salvado:
DEC-003 (crítica, categoría `finanzas`) en B04-CA-23, descartada por el modelo
y no rescatada porque la regla solo rescata `"salud"`.

**Conclusión de la medición pedida («por qué perdemos el doble»):** las dos
mitades del doble salen de la misma decisión — el vocabulario temático y la
categoría de máxima criticidad `"salud"` de ADR-116 sustituyeron a la categoría
derivada de la criticidad del laboratorio. Sin la palabra `restriccion` en el
vocabulario, el índice de categoría no se activa para las consultas que piden
lo crítico (5 pérdidas extra en B04-CA-31 y 1 en B04-CA-02); sin una categoría
de máxima criticidad que alguna crítica del banco lleve, la regla RF-25/RF-26
no rescata nada (1 pérdida en B04-CA-23). El filtro en sí funciona: baja el
ruido de 285 a 39 y sube los aciertos exactos de 7 a 22.

**Nota sobre una ejecución anterior contaminada:** una corrida intermedia del
propietario dio 40 rendiciones en 2,8 min con el mismo código; la siguiente,
idéntica, dio 0. No se investigó la causa (transitoria, probablemente el modelo
descargándose o recargándose); el medidor ahora publica el motivo de cada
rendición para que, si se repite, quede registrado en vez de adivinado.

### Resultado en la máquina del propietario (Ollama real, 05-09-2026)

Tras la ola de criticidad entera (M18b → M21b: ADR-126 a ADR-131) más los
guardianes G1-G3. `uv run python scripts/medir_banco_con_ollama_real.py
--diagnostico`, modelo `qwen3:4b-instruct`, espera 30 s, sobre main
`a07c5d5`: **47 llamadas, 0 rendiciones, 0,8 min** — medición válida por su
propio criterio.

Métricas: 8/47 aciertos exactos (suelo D1 29/47: por debajo), 218 de más
(ruido tolerable), **0 críticas perdidas** (suelo D1 ≤ 1: alcanza), **70/81**
de cobertura (suelo D1 63: alcanza).

| caso | crítica | laboratorio (fila 4) | producción (propietario, 05-09) |
|---|---|---|---|
| B04-CA-33 | DEC-003 | NO_ENTRO | OK |
| B04-CA-34 | DEC-003, MEM-014, MEM-016 | NO_ENTRO | OK |

Laboratorio, fila 4: 4 críticas perdidas (`NO_ENTRO`: 4). Producción, hoy: 0.

**Comparado con el 02-09 (misma máquina, mismo modelo, antes de M19b y
M20):** críticas perdidas **10 → 0**, cobertura **59 → 70/81**, aciertos
exactos 22 → 8, elementos de más 39 → 218. Las nueve pérdidas por `NO_ENTRO`
del 02-09 (B04-CA-02, B04-CA-31 y B04-CA-34) y la única
`TIRADO_POR_EL_FILTRO` (DEC-003 en B04-CA-23) han desaparecido todas: la
siembra (M20, ADR-129) pone lo crítico delante del filtro y el rescate por
criticidad (M19b, ADR-128) impide que el modelo lo tire. El precio, aceptado
por escrito en ADR-129 antes de medirlo: la siembra mete en cada consulta
todo lo no ordinario del ámbito y el filtro solo lo poda hasta 218 de más;
los aciertos exactos bajan porque la respuesta trae más de lo pedido, no
menos. La métrica que la Decisión 1 protege —ninguna crítica perdida— pasa de
incumplida por diez a cumplida.

Nota operativa de la ejecución: una corrida previa del mismo comando falló
antes de medir nada, con `uv` incapaz de reinstalar el paquete del proyecto
(«Acceso denegado» al borrar el `dist-info` del `.venv`, que vive dentro de
una carpeta sincronizada por OneDrive); la siguiente corrida reinstaló con un
aviso de `RECORD` ausente y midió entera. El aviso no afectó al resultado —el
banco corrió los 47 casos— y el `.venv` bajo OneDrive queda anotado como
riesgo de la máquina, no del código.

**Disciplina de esta medición (ADR-001).** Criterio de parada: los suelos de
la Decisión 1 de este documento (29/47 exactos, ≤ 1 crítica perdida, 63/81 de
cobertura), escritos antes de medir; las filas que ADR-128 y ADR-129 dejaron
pendientes fijaban qué se mediría y contra qué. Afirmación: M19b + M20
alcanzan los dos suelos que la Decisión 1 protege (críticas perdidas y
cobertura) y no el de aciertos exactos. Comprobación: la ejecución transcrita
arriba, con su diagnóstico por caso y la comparación contra el 02-09 en la
misma máquina y con el mismo modelo. No hay decisión nueva: esta sección
rellena las filas pendientes de los dos ADR y deja escrito el precio medido.

## Medición previa a la decisión: qué haría cada forma de marcar lo crítico

**Pregunta:** antes de decidir cómo se marca lo crítico en producción, ¿qué
haría cada opción sobre el camino real? **Instrumento:**
`scripts/medir_variantes_de_criticidad.py`, que inyecta al arnés de producción
otro vocabulario, otra asignación de categoría y otra categoría de máxima
criticidad (tres parámetros opcionales nuevos de
`_ejecutar_banco_paquete_completo`, con el comportamiento de hoy por defecto),
con el doble que nunca descarta: sin Ollama, solo la etapa de búsqueda
(`NO_ENTRO`), que es la mitad grande del problema (9 de 10).

**Predicción, escrita en el guion antes de ejecutar:** `hoy` = 9; `A` (porte
fiel: `restriccion` solo en lo no ordinario, vocabulario del laboratorio) baja a
**4**; `B` (etiquetas de tema para todo + las cinco palabras) baja también pero
**dispara** los elementos de más.

**Resultado (02-09-2026, sin Ollama, mypy y ruff en verde):**

| variante | exactos | de más | críticas `NO_ENTRO` | cobertura |
|---|---|---|---|---|
| `hoy` | 7/47 | 285 | **9** | 62/81 |
| `A_porte_fiel` | 7/47 | **260** | **3** | **68/81** |
| `B_arreglo_ingenuo` | 7/47 | **354** | 3 | 68/81 |

- `hoy` = 9: el control reproduce lo medido.
- `A` = **3**, una mejor que la predicción: B04-CA-33 `DEC-003` la encuentra
  producción aunque el laboratorio no. Las tres que quedan son las de
  B04-CA-34 («Prepara el **contexto** de planificación de Alfa»), que el
  laboratorio también pierde en la fila 4 y solo recupera con la **siembra**
  (fila 5): esa consulta no nombra ninguna palabra del vocabulario; declara que
  ensambla contexto, y la siembra es precisamente lo que responde a eso.
- `B` = 3 también, pero **354** elementos de más frente a 260: la predicción
  se cumple en dirección y tamaño (+94 sobre `A`, +69 sobre `hoy`). En
  producción todo item lleva etiqueta de tema; activar el índice con palabras
  nuevas trae todo lo del ámbito, ordinario incluido. **Añadir palabras al
  vocabulario queda descartado con datos.**
- `A` baja además el ruido respecto a `hoy` (285 → 260): al llevar categoría
  solo lo no ordinario, el índice deja de traer todo lo etiquetado
  `proyecto`/`trabajo` cuando la consulta nombra esos temas.

**Conclusión de la medición:** de las 9 críticas que la búsqueda de producción
no ve, **6 son la etiqueta** (se recuperan derivando la categoría de la
criticidad, como el laboratorio) y **3 son la siembra** (no se recuperan con
ninguna etiqueta; hace falta la pieza que ADR-119 dejó fuera). La décima, la
que tira el filtro, es la regla de rescate apuntando a `salud`; con `A` apunta
a `restriccion` y tendría a quién rescatar — eso se mide con Ollama, no aquí.

**Lo que NO afirma:** no decide qué etiqueta debe usar producción ni cómo
convive con las etiquetas de tema (que también sirven para otra cosa: D7). Mide
qué recupera cada opción y qué le cuesta. Decidir es del propietario.

## Decisión del propietario y plan (02-09-2026)

Con la medición de variantes delante, el propietario decide (sesión
interactiva) y entrega las riendas de la ejecución con dos condiciones:
«necesito acabar la memoria y hacerla bien» y «no te olvides del objetivo de
Sirius» — una memoria que no pierde lo importante; el ruido es tolerable.

**Decisión 1 — dos señales, no una.** `category` sigue siendo *de qué va* un
item (tema; D7 la necesita). Cada `Memory` y `Decision` gana `criticality:
CRITICO | IMPORTANTE | None`, el concepto del propio canon
(`criticidad.nivel`). El índice de categoría, la regla de rescate RF-25/RF-26
y la siembra pasan a mirar la criticidad, no el tema.

**Decisión 2 — la siembra entra.** Su precondición documentada (ampliar el
banco o retirarla) se resuelve así: el propietario la porta **sabiendo** que el
banco no puede validarla de forma independiente (solo B04-CA-34 y otro caso la
ejercitan); su aceptación es la medición de críticas perdidas (3 → 0) y el uso
real del propietario, no una prueba del banco. Queda escrito para que nadie lo
lea después como un olvido.

**Decisión 3 — RNF-003 suspendido para el camino del filtro** mientras se mide
su coste real («me da igual que tarde diez, veinte segundos, mientras lo haga
bien»). Medido en su máquina: 47 consultas en 0,4 min con `qwen3:4b-instruct`.

**Plan, un encargo detrás de otro (sin paralelo), con la predicción escrita
antes de construir:**

| Encargo | Qué | Predicción sobre el banco de 47 (Ollama real) |
|---|---|---|
| M18 | Señal de criticidad en dominio/persistencia/caso de uso + filtro fiel al laboratorio portado a `main` | Sin cambio en lo recuperado: 7/47, 285, 9 NO_ENTRO, 62/81 con el doble |
| M19 | Índice y rescate por criticidad | Críticas perdidas **10 → 3**; TIRADO **1 → 0** |
| M20 | Siembra en contexto | Críticas perdidas **3 → 0** |
| M21 | Sirius propone la criticidad, el usuario confirma | Que funcione con los recuerdos reales del propietario, no solo con el banco |

Si tras M19 no salen 3, o tras M20 no sale 0, se para y se busca la raíz
(regla de las dos rondas, ADR-001). M18 despachado el 02-09-2026 con esta
decisión embebida en la orden; su ADR la registra.

### Corrección del plan (02-09-2026, 17:44 UTC): M18 se parte en M18a y M18b

M18 (#507) se despachó como un solo encargo con las dos partes y falló de forma
segura a los 36 minutos: el implementador hizo **262 turnos**, gastó **~15 USD**,
terminó con `is_error: true` y **no subió ninguna rama ni escribió veredicto**
(run 33633342725, job 100257963608). No fue el límite de 60 minutos ni el de
300 turnos: la orden no cabía en una ejecución. Es el mismo defecto de
proporción que registra #503, esta vez del lado de quien ordena, y queda
declarado aquí como tal.

Se cierra #507 y se despachan dos encargos en serie:

| Encargo | Qué | Estado |
|---|---|---|
| M18a | Porte mecánico del filtro fiel (commits de esta rama hasta 877d11f) + clave `ollama_model` + ADR de la suspensión de RNF-003 | despachado 17:44 UTC (#508); falló de forma segura 18:44 UTC |
| M18b | La señal de criticidad (dominio, migración, repositorios, puertos, caso de uso, cargador del banco) + ADR de las dos señales y el plan | tras M18a |

El resto del plan (M19, M20, M21) y sus predicciones no cambian.

(La primera redacción de esta sección decía «16:55 UTC»; la hora real del
despacho de #508 es 17:44:18 UTC. Se corrige sin borrar el error.)

### Segundo fallo seguro (02-09-2026, 18:44 UTC): M18a entra por plan B

M18a (#508) agotó el tope de 60 minutos del implementador (run 33662923270,
17:44:22 → 18:44:50 UTC) sin sustituir el veredicto provisional y **sin subir
ninguna rama**, igual que #507. Ya no es la orden juntando dos encargos: es que
leer esta evidencia, portar siete archivos y escribir un ADR con seis citas
fichero:línea no cabe en una ejecución del motor. Dos intentos seguidos con el
mismo desenlace activan la regla de las dos rondas (ADR-001): se para de
insistir por ese camino.

El plan B, decidido antes de despachar #508: esta misma rama, que ya contiene
el porte verificado (`bd79d88`: ruff, mypy `src tests` y las pruebas unitarias
afectadas en verde; 8 archivos frente a `main`, ninguno tocado en `main`
desde la base), gana el ADR de la suspensión de RNF-003 y se abre como PR
contra `main`. El motor solo revisa y fusiona; no vuelve a implementar nada.
M18b se despacha después, como estaba previsto.

**Hallazgo al preparar la PR, declarado porque cambia una prueba:** el banco
de latencia (`tests/integration/test_local_performance.py`, encargo M11)
construye el adaptador real con `_RELEVANCE_FILTER_TIMEOUT_SECONDS` y, en su
escenario (c), un doble que **duerme la espera entera** antes de fallar. Con
la espera en 30 s, ese escenario dormiría 30 s por repetición (15 minutos en
total) para acabar midiendo la constante, y el guardarraíl de 1.500 ms lo
pondría en rojo por construcción. Esta rama no lo ejecutó antes (declarado en
«Comprobación»: «mediría peor a propósito»); al abrir la PR ya no vale
declararlo, hay que resolverlo.

**Cómo se resolvió, y por qué hizo falta ir a la raíz (rondas 1-3 de la PR
#509):** la primera versión saltaba (c) en una prueba mientras la espera
superara el guardarraíl; la ronda 1 señaló que la prueba hermana (`xfail`) no
tenía la guardia; la ronda 2, que el fallo rápido añadido ya no verificaba que
el filtro se invocara; la ronda 3, que los documentos no describían la
verificación. Tres rondas con la misma familia de defecto es la señal de
ADR-001 de que se estaba parcheando alrededor de la raíz. La raíz era que el
doble de (c) **dormía** la espera. Se quitó el sueño (ADR-125, punto 5): el
doble lanza `ReadTimeout` al instante y cuenta las invocaciones; las dos
pruebas miden (c) como (a) y (b) y publican `coste medido + espera`; el
guardarraíl afirma la invocación real y el coste medido; la prueba `xfail`
afirma el total y solo suma la espera si el filtro se invocó, con lo que
conserva el XPASS de alerta si una regresión desconectara el filtro. Sin
guardias, sin fallos sintéticos, sin dependencia de qué escenario falla
primero.
