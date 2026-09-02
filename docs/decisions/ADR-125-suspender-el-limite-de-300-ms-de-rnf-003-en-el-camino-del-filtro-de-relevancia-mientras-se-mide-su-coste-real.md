# ADR-125 — Suspender el limite de 300 ms de RNF-003 en el camino del filtro de relevancia mientras se mide su coste real

- Estado: APROBADO
- Fecha: 2026-09-02
- Aprobación: decisión del propietario en sesión interactiva (02-09-2026) y
  fusión de la PR por el propietario

Este ADR registra una decisión ya tomada por el propietario y el porte que la
hace efectiva. La evidencia completa —diagnóstico, nota de arranque, cada
medición con su criterio de parada escrito antes— vive en
`docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md`; aquí se
cita, no se repite. Lo que este ADR **no** registra: cómo se marca lo crítico
en producción (dos señales, índice y rescate por criticidad, siembra). Eso es
una decisión distinta y tendrá su propio ADR con el encargo M18b.

## Contexto y problema

RNF-003 fija 300 ms P95 para construir el contexto
(`docs/implementation/V8_EXECUTION.md:47`;
`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md` §6.4). Para
caber en ese presupuesto, el filtro de relevancia con modelo local se cableó
con una espera de **50 ms** (`_RELEVANCE_FILTER_TIMEOUT_SECONDS = 0.05` en
`src/sirius/composition_root.py`, ADR-117). Un modelo local no contesta en
50 ms: el adaptador fallaba abierto en todas las llamadas y el filtro
**nunca filtraba**. La memoria que el propietario probó en casa por primera
vez (02-09-2026) llevaba el filtro cableado y, en la práctica, apagado.

Además, el adaptador de producción no hacía la misma llamada que el
laboratorio que midió 29/47 sobre el banco de 47 casos (rama
`evidence/adr001-spikes`, ficheros `experiments/adr002/modelo_local/puerto.py`
y `experiments/adr002/modelo_local/filtro.py`, que nunca se copian a `main`).
Seis diferencias, comprobadas leyendo los dos ficheros (tabla completa y citas
en la evidencia, sección «Por qué existe esta rama»):

| | Laboratorio (`puerto.py`, `filtro.py`) | `main` antes de esta PR |
|---|---|---|
| Modelo | `qwen3:4b-instruct` (`puerto.py:73`) | `llama3.2` (`composition_root.py:136`) |
| Espera | `10.0 s` (`puerto.py:91`) | `0.05 s` (`composition_root.py:157`) |
| Extremo | `/api/chat` (`puerto.py:319`) | `/api/generate` |
| Formato | esquema JSON impuesto al generar (`filtro.py:139`) | pedido por escrito en el prompt |
| Modo razonador | `think: False` (`puerto.py:316`) | no se envía |
| `temperature` / `num_ctx` | `0.1` / `8192` (`puerto.py:78-86`) | no se envían |

El laboratorio declara que el formato impuesto no es cosmético («con un modelo
pequeño eso falla») y que sin `think: False` un modelo Qwen3 «pasa de segundos
a minutos». Con esas diferencias, ninguna prueba en casa medía la memoria que
produjo la cifra que se quería reproducir.

El intento de portar esto mediante el motor de trabajo falló dos veces de
forma segura sin subir rama ni veredicto (#507: 262 turnos; #508: tope de 60
minutos). Por la regla de las dos rondas (ADR-001) no se insiste: el porte,
ya hecho y verificado en la rama `experimento/filtro-fiel-al-laboratorio`,
entra por PR directa y el motor solo revisa.

## Criterio de parada (escrito ANTES de decidir)

El criterio que ató el experimento se publicó en su nota de arranque antes de
medir nada (evidencia, «Nota de arranque», punto 3): *si con la llamada fiel
el registro seguía mostrando «Filtro de relevancia no disponible, se falla
abierto», las seis diferencias no eran la causa y no había nada que suspender;
si el filtro se ejecutaba y descartaba, el experimento cumplía sea cual fuera
la cifra de aciertos*. Se cumplió lo segundo: 47 llamadas, 0 rendiciones.

Para la suspensión misma, lo que la hará revisar, fijado ahora:

1. Si en la máquina del propietario el filtro vuelve a rendirse con Ollama
   levantado (contador de rendiciones > 0 en
   `scripts/medir_banco_con_ollama_real.py`), la espera de 30 s es corta o
   hay otra causa: se investiga antes de tocar nada más.
2. Si el coste por consulta medido supera los **20 s** que el propietario
   dio como tolerancia («diez, veinte segundos»), la suspensión deja de estar
   cubierta por su decisión y vuelve a él.
3. La suspensión es temporal: se cierra o se convierte en un límite nuevo
   cuando termine M21 (última pieza del plan de la evidencia) y se mida el
   coste real con los recuerdos del propietario, no solo con el banco.

## Opciones consideradas

- **(a) Mantener RNF-003 y la espera de 50 ms.** Es el estado que se probó en
  casa: el filtro no se ejecuta nunca. Cumple el límite porque no hace nada.
- **(b) Suspender el límite en el camino del filtro, poner la espera a 30 s y
  medir el coste real** con el adaptador fiel al laboratorio. Elegida.
- **(c) Buscar una espera que quepa en 300 ms.** ADR-117 (sección
  «Alternativas descartadas») y ADR-119 (misma sección) ya descartaron bajar
  la espera para forzar RNF-003: el coste dominante no es el transporte, y una
  espera corta maquilla la cifra. Con un modelo local que tarda ~0,5 s por
  consulta, cualquier espera dentro de 300 ms es la opción (a) con otro
  nombre.
- **(d) Quitar el filtro.** Perdería lo único que baja el ruido: con el
  filtro vivo los elementos de más pasan de 285 a 39 (medición del
  propietario).

## Decisión

1. **RNF-003 queda suspendido en el camino del filtro de relevancia** mientras
   se mide su coste real: cuando `ContextBuilder` ejecuta el filtro con modelo
   local (puerta `category_matching_enabled` abierta), el P95 de 300 ms no se
   afirma ni se exige. En el resto del camino —puerta cerrada, o Ollama
   ausente— RNF-003 sigue tal cual. Palabras del propietario, 02-09-2026: «me
   da igual que tarde diez, veinte segundos, mientras lo haga bien».
2. **El adaptador hace la llamada del laboratorio**, punto por punto
   (`src/sirius/adapters/ollama_relevance_filter.py`): `/api/chat` con
   mensajes `system` + `user`, esquema JSON `{responden: [int]}` impuesto al
   generar, `think: False`, `keep_alive: 15m`, `temperature: 0.1`,
   `num_ctx: 8192`, lectura de `message.content`. La instrucción y el esquema
   se portan **literales** de `filtro.py:139-180` y llevan su cita en el
   código. Sigue siendo solo-`localhost` y falla abierto.
3. **La espera pasa de 0,05 s a 30 s** (`composition_root.py:166`). Es la
   cifra que llevaba la orden aprobada por el propietario; está por encima
   del laboratorio (10 s) a propósito, para observar la calidad separada de la
   velocidad, y muy por encima del coste medido (~0,5 s por consulta).
4. **El modelo local deja de ser una constante:** clave nueva `ollama_model`
   en `settings.json`, por defecto `qwen3:4b-instruct`, leída una sola vez y
   entregada al filtro **y** al clasificador de categoría
   (`composition_root.py:143-180` y punto de construcción en `:502`), porque
   el comentario de `_RELEVANCE_FILTER_MODEL` ya exigía que ambos usaran el
   mismo modelo. Valores vacíos o de otro tipo caen al valor por defecto.
5. **El banco de latencia deja de dormir la espera.** Su escenario (c)
   («Ollama acepta la conexión y agota el timeout») construía el adaptador con
   la espera real y un doble que duerme esa espera entera: con 30 s serían
   15 minutos para medir una constante y el guardarraíl de 1.500 ms lo pondría
   en rojo por construcción. Mientras la espera de producción supere el
   guardarraíl, (c) no se ejecuta ni se afirma y la tabla lo publica como «no
   medido: = espera de producción por construcción»; (a) y (b) se miden y
   afirman como siempre; si la espera vuelve a bajar del guardarraíl, (c) se
   mide de nuevo sin tocar la prueba
   (`tests/integration/test_local_performance.py`). La prueba
   `xfail(strict=True)` del suelo de RNF-003 no cambia.
6. **Nada más.** La puerta `category_matching_enabled` sigue cerrada por
   defecto; `category` y su semántica D7 no cambian; el banco, el corpus y sus
   adjudicaciones no se tocan; `criticidad.razon_segura` no se lee; no entra
   ninguna señal de criticidad.

## Comprobación que la sostiene

Medición del propietario en su máquina (02-09-2026, Ollama real,
`qwen3:4b-instruct`, espera 30 s), `uv run python
scripts/medir_banco_con_ollama_real.py --diagnostico`:

| | Sin filtro (doble que conserva todo) | Con el filtro fiel (propietario) |
|---|---|---|
| Llamadas / rendiciones / duración | — | **47 / 0 / 0,4 min** |
| Aciertos exactos | 7/47 | **22/47** |
| Elementos de más | 285 | **39** |
| Críticas perdidas | 9 | 10 |
| Cobertura | 62/81 | 59/81 |

La medición es válida por su propio criterio (0 rendiciones). El coste real es
~0,5 s por consulta: la suspensión es formal, no práctica. Las 10 críticas
perdidas (9 antes del filtro, 1 tirada por él) tienen causa localizada en la
evidencia y son objeto de M18b-M20, no de este ADR.

En la rama de esta PR (`experimento/filtro-fiel-al-laboratorio`), antes de la
PR: `uv run ruff format --check` y `uv run ruff check` en verde; `uv run mypy
src tests` sin incidencias; `uv run pytest tests/unit/test_ollama_relevance_filter.py`
12 pasan (1 se vio fallar antes de acomodar el sobre, ADR-001);
`uv run pytest tests/unit/test_composition_root_ollama_model.py` 4 pasan;
`uv run pytest tests/unit tests/integration` (sin el banco de latencia) 1475 +
512 pasan.

Comprobación del punto 5, en el runner donde se preparó la PR, tras el ajuste:
ver la sección «Corrección tras preparar la PR» al final de este ADR.

En un runner sin Ollama, `uv run python scripts/medir_banco_con_ollama_real.py
--espera 0.2` informa 47 llamadas y 40 rendiciones con `ConnectError` y declara
las cifras no válidas: el contador funciona y el porte no cambia lo recuperado
con el doble (7/47, 285, 9, 62/81).

## Consecuencias

- Positivas: el filtro se ejecuta por primera vez en producción; el ruido baja
  de 285 a 39 y los aciertos exactos suben de 7 a 22 sobre el banco. El modelo
  local es configurable sin tocar código. Existe por primera vez un
  instrumento que mide el camino real con Ollama puesto.
- Negativas y riesgos: con la puerta abierta, construir el contexto puede
  tardar hasta 30 s si Ollama acepta la conexión y no contesta; RNF-003 no se
  afirma en ese camino; el banco de latencia deja de cubrir el escenario (c)
  mientras dure la suspensión. Las tres cosas están dichas aquí y en la prueba,
  no escondidas.
- Deuda declarada (evidencia, «Nota de arranque», punto 4): nada impide que
  las dos implementaciones del filtro vuelvan a divergir. Cerrarlo exige una
  prueba compartida entre la corrida congelada del laboratorio y el adaptador
  que falle cuando dejen de coincidir. No se hace aquí.
- Siguiente paso del plan (evidencia, «Decisión del propietario y plan»):
  M18b, la señal de criticidad, con su propio ADR.

## Alternativas descartadas y por qué

- Bajar la espera hasta caber en 300 ms: ya descartado por ADR-117 y ADR-119
  y, con un modelo local, equivale a apagar el filtro.
- Mantener `llama3.2` y solo subir la espera: habría medido un filtro distinto
  del que produjo 29/47; el modelo es una de las seis diferencias, no un
  detalle.
- Pedir el formato JSON por escrito en el prompt en vez de imponerlo al
  generar: el laboratorio lo probó y lo descartó con un modelo pequeño.
- Dormir la espera de 30 s en el banco de latencia para «medir de verdad» el
  escenario (c): mediría una constante durante 15 minutos y pondría en rojo
  una prueba por construcción; no aporta información que la constante no dé.

## Corrección tras preparar la PR

El hallazgo del punto 5 apareció al preparar la PR, no antes: la rama del
experimento había declarado que no ejecutaba el banco de latencia («mediría
peor a propósito») y al abrir la PR eso deja de valer. Comprobación del
ajuste, en el runner donde se preparó la PR (02-09-2026, sin Ollama, dobles
deterministas del transporte como siempre):

```
uv run pytest tests/integration/test_local_performance.py -k "tres_escenarios or suelo_de_rnf_003" -s

  M11 — RNF-003, paquete completo activo, timeout=30000 ms:
  | Escenario | P95 | Límite |
  | Ollama disponible dentro del presupuesto | 577.3 ms | 300 ms |
  | Ollama ausente (conexión rechazada) | 556.5 ms | 300 ms |
  | Ollama acepta la conexión y agota el timeout | no medido: = espera de producción (30000 ms) por construcción, ADR-125 | 300 ms |
1 passed, 1 xfailed in 65.19s
```

Antes del ajuste, con la misma espera, la prueba habría dormido 30 s por
repetición en (c) y fallado el guardarraíl por construcción. (a) y (b) siguen
midiéndose y afirmándose contra el guardarraíl; siguen por encima de 300 ms,
como ya registró ADR-117 en otro runner, y la prueba `xfail(strict=True)` del
suelo sigue fallando-como-se-espera sin llegar a (c). `uv run mypy src tests`:
sin incidencias en 550 archivos. `uv run ruff format --check` y `uv run ruff
check` sobre los archivos tocados: en verde. `git diff --check`: limpio.
