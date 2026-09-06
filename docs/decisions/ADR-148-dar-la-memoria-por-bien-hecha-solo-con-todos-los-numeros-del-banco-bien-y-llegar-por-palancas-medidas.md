# ADR-148 — Dar la memoria por bien hecha solo con todos los números del banco bien, y llegar por palancas medidas

- Estado: PROPUESTO
- Fecha: 2026-09-05
- Aprobación: la fusión de esta PR por el propietario. El criterio de fondo es
  suyo y consta en la sesión de esta noche; lo que la fusión aprueba es su
  registro y el plan para alcanzarlo.

## Contexto y problema

Sirius 0.2 «Memoria útil» tiene los cinco bloques construidos en `main`
(ADR-126 a ADR-131 cierran la ola de criticidad M18–M21). Tres hechos,
verificados el 05-09-2026:

1. **La recuperación mejorada está apagada en el uso diario.**
   `category_matching_enabled` es `False` por defecto y se lee de
   `settings.json` (`src/sirius/composition_root.py:514`); con la puerta
   cerrada, `RankRelevantKnowledgeUseCase` y `ContextBuilder` se construyen
   sin vocabularios, sin filtro de relevancia y sin categoría de máxima
   criticidad (`src/sirius/composition_root.py:516-547`).
   `docs/evolution/STATUS.md` («Decisión de rumbo», 31-08) ató la apertura a
   dos condiciones: el umbral de D7 punto 6, nunca medido en la máquina del
   propietario (ADR-117), y que la ola de paridad alcanzara 29/47 exactas.
2. **Los números del camino con la puerta abierta, con Ollama real en la
   máquina del propietario** (05-09, `scripts/medir_banco_con_ollama_real.py
   --diagnostico`, `qwen3:4b-instruct`, 47 llamadas, 0 rendiciones; ADR-128,
   ADR-129 y la PR #547): 8/47 exactas, 218 elementos de más, 0 críticas
   perdidas, 70/81 hallados. El 02-09, antes de M19b/M20: 22/47, 39, 10 y
   59/81.
3. **El criterio del propietario**, en la sesión del 05/06-09 (hacia las
   00:30 hora local): «tenemos que sacar todos los números bien… no me vale
   a medias». Sustituye la frase «el ruido es tolerable» que el registro del
   02-09 le atribuía
   (`docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md`,
   «Decisión del propietario y plan») y confirma su «si recuerda 29 cosas de
   47 a mí no me vale» del 31-08 (`docs/evolution/STATUS.md`): el suelo no es
   29/47, es todo.

El problema: ni la decisión del 31-08 (abrir con 29/47) ni la del 02-09
(ruido tolerable) coinciden ya con lo que el propietario exige, y el plan del
02-09 se eligió sin medir qué palanca movía qué número. Este ADR registra el
criterio y el plan para alcanzarlo, con el techo de cada palanca medido antes
de encargar nada.

## Criterio de parada (escrito ANTES de decidir)

- **De la línea entera:** la memoria se da por bien hecha solo cuando el
  banco de 47 casos, con Ollama real en la máquina del propietario y 0
  rendiciones, mide **47/47 exactas, 81/81 hallados, 0 críticas perdidas y 0
  elementos de más**. La puerta `category_matching_enabled` no se abre por
  defecto antes de eso, y la criticidad la sigue confirmando el propietario
  (ADR-131) hasta entonces.
- **De cada encargo del plan:** su predicción numérica se escribe en la orden
  antes de construir (abajo). Si al medir no se cumple, o si dos rondas
  seguidas traen defectos de la misma familia, se para y se busca la raíz
  (ADR-001); no se pasa al siguiente encargo.
- **De este ADR:** si la primera medición del intérprete de peticiones
  (palanca 1) no reproduce la petición del banco en al menos 45 de los 47
  casos, la palanca 1 no se da por buena y el plan se revisa aquí, no dentro
  de la orden.

## Opciones consideradas

1. **Abrir la puerta ahora, con el criterio del 02-09** (0 críticas perdidas
   alcanzado). Descartada por el propietario: 8/47 exactas y 218 de más no es
   una memoria bien hecha.
2. **Cambiar solo el modelo del filtro por uno mayor.** Insuficiente como
   única palanca: sin filtro, la etapa de búsqueda ya da 0/47 exactas y 487
   de más con la petición fija, así que el modelo hereda un problema que no
   es suyo. Se conserva como medición de la palanca 3 (un comando,
   `--modelo`), no como plan.
3. **Palancas en orden, cada una con su techo medido** (elegida): interpretar
   la petición, derivar los ejes, filtrar con la cardinalidad conocida, y
   cerrar los cuatro huecos que quedan.

## Decisión

**El criterio de parada de arriba es el criterio de aceptación de la memoria
de Sirius.** El camino, con el techo de cada palanca medido el 05-09 sobre la
etapa de búsqueda sin Ollama (doble que no descarta; ver «Comprobación»):

| Configuración de la búsqueda | Exactas | De más | Hallados | Críticas perdidas |
|---|---|---|---|---|
| Hoy: petición fija, ítems sin ejes | 0/47 | 487 | 72/81 | 0 |
| Solo ejes de los ítems | 0/47 | 421 | 71/81 | 0 |
| Solo petición real del caso | 16/47 | 162 | 73/81 | 0 |
| Ejes y petición real | 20/47 | 144 | 73/81 | 0 |

**Palanca 1 — la petición real (el mayor salto).** Producción interroga al
motor con una política uniforme para toda pregunta (`_peticion_ordinaria`,
`src/sirius/application/rank_relevant_knowledge.py:103-149`: modo M1,
cardinalidad EXHAUSTIVA, tiempo objetivo «ahora», sin corte, propósito fijo).
El banco y el laboratorio llevan por caso el modo (M1 responder, M2 revisar
historial), el permiso, la cardinalidad (EXACTA, EXHAUSTIVA, ACOTADA), el
tiempo objetivo o intervalo y el corte de registro
(`tests/acceptance/staged_engine_case_translation.py:120-155`); el motor ya
honra esos campos (`src/sirius/domain/staged_engine_gates.py`), como prueba
la medición: inyectar la petición del caso mueve las exactas de 0 a 16 sin
tocar nada más. Encargo: un intérprete de la pregunta que produzca esa
`Peticion` —el modelo local para el modo, la cardinalidad y el tiempo; reglas
del producto para el permiso—, medido primero contra las 47 `peticion_p2` del
banco (la coincidencia campo a campo es su prueba de aceptación, vista fallar
antes). Predicción sobre el banco sin filtro: ≥16/47 exactas, ≤162 de más, 0
críticas perdidas, ≥73/81 hallados.

**Palanca 2 — los ejes de cada ítem, derivados de datos que el producto ya
tiene.** `build_staged_engine_port` entrega todo ítem real con
`ejes=SIN_EJES` (`src/sirius/adapters/persistence/staged_engine_port.py:24-33`).
La vigencia desde/hasta se deriva de la aprobación y la sustitución de las
decisiones y de las revisiones de los recuerdos; el registro, de
`created_at`; la autoridad, del origen (guardado explícito, sugerencia,
fuente externa). Sin migración nueva salvo que la medición lo exija.
Predicción, con la palanca 1 puesta: 20/47, 144 de más, 0, 73/81.

**Palanca 3 — el filtro con la cardinalidad conocida.** Con EXACTA n el
filtro recorta a n; con EXHAUSTIVA poda por relevancia. Se mide con
`qwen3:4b-instruct` y con un modelo mayor (`--modelo`, un comando en la
máquina del propietario). Predicción: de más 144 → ≤ 20 con el 4B; el
objetivo es 0, y si el 4B no llega, el modelo se decide con número.

**Los cuatro huecos que las palancas no cierran (8 ocurrencias de 81):**

- **H1, enumerar por ventana temporal sin tema** (B04-CA-22, cinco
  decisiones «válidas entre enero y marzo»): la búsqueda parte de palabras;
  hace falta un camino que liste por vigencia cuando la petición trae
  intervalo y no tema.
- **H2, el corte de registro** (B04-CA-32, «qué sabía el 1 de marzo»): G8
  compara con el `created_at` real
  (`src/sirius/domain/staged_engine_gates.py:214-216`) y el cargador del
  banco crea todos los ítems el día de la medición — artefacto del arnés; en
  el producto la fecha es real. Se corrige en el cargador, sin tocar el
  corpus ni `resultado_esperado`.
- **H3, lo candidato de fuente externa** (B04-CA-29, MEM-020 `CANDIDATA`):
  el cargador lo archiva y en el producto sería una sugerencia pendiente.
  **Decisión de producto del propietario, pendiente:** si lo no confirmado se
  recupera, marcado como tal.
- **H4, la derivación léxica de D3 bajo cardinalidad acotada** (B04-CA-30,
  MEM-001): entra en EXHAUSTIVA y queda fuera del límite en ACOTADA; es de
  ranking (coincidencia semántica o expansión), no de búsqueda.

**Orden:** P1 → P2 → P3 → H2 (barato) → H1 → H4 → H3 (tras la decisión). Un
encargo cada vez; medición en CI con el doble (búsqueda) y del propietario
con Ollama real al cerrar cada palanca. La siembra de M20 se mantiene hasta
que la palanca 1 mida y se revisa entonces.

## Comprobación que la sostiene

- Puerta: `src/sirius/composition_root.py:513-547`; el arnés del banco la
  abre a mano (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:2195`
  y `:2218`).
- Petición fija: `src/sirius/application/rank_relevant_knowledge.py:103-149`;
  petición por caso: `tests/acceptance/staged_engine_case_translation.py:120-155`;
  ítems sin ejes: `src/sirius/adapters/persistence/staged_engine_port.py:24-33`
  y `:169-173`.
- Techo de la búsqueda: `scripts/diagnosticar_busqueda_del_banco.py`
  (añadido en esta PR), que reutiliza `_ejecutar_banco_paquete_completo` sin
  reimplementarlo e inyecta, por parches sobre nombres de módulo, los ejes
  del corpus (`_ejes_declarados`) y la petición del caso
  (`peticion_desde_caso`). Ejecutado el 05-09 sobre `a07c5d5` en el
  contenedor del operador, sin Ollama:
  - sin banderas: `0/47 exactos; 487 de mas; 72/81 hallados; omisiones
    criticas=0`;
  - `--ejes`: `0/47; 421; 71/81; 0`;
  - `--peticion`: `16/47; 162; 73/81; 0` (47 llamadas a la petición, 0 sin
    caso);
  - `--ejes --peticion`: `20/47; 144; 73/81; 0`;
  - los 8 huecos con ambas palancas, tal como los imprime el guion:
    B04-CA-22 (DEC-001, DEC-005, DEC-009, DEC-011, DEC-015), B04-CA-29
    (MEM-020), B04-CA-30 (MEM-001), B04-CA-32 (DEC-012).
- Ollama real en la máquina del propietario (05-09): ADR-128, ADR-129 y la
  sección «Resultado en la máquina del propietario (Ollama real,
  05-09-2026)» de la evidencia del experimento (PR #547).
- **Lo que NO se ha medido:** el intérprete de peticiones no existe; la cifra
  de la palanca 1 es el techo con la petición del banco inyectada, no la de
  un intérprete. Tampoco se ha medido ningún modelo distinto del 4B.
- Cadena de comprobación de esta rama: ver el cuerpo de la PR (se ejecuta
  como una sola invocación antes de abrirla y se transcribe allí con su
  código de salida).

## Consecuencias

- Sustituye, para la activación de la memoria, tanto el criterio del 31-08
  (29/47) como la frase «el ruido es tolerable» del 02-09: la puerta no se
  abre por defecto hasta el criterio de parada de arriba.
  `docs/evolution/STATUS.md` se actualiza al fusionar el primer encargo del
  plan, no aquí.
- La siembra en contexto (M20) deja de ser el mecanismo principal contra las
  críticas perdidas: con la petición real, las críticas perdidas siguen en 0
  aunque la siembra solo actúe en los dos casos cuyo propósito la pide.
- ADR-131 (confirmación manual de la criticidad) sigue vigente; el marcado
  automático queda aparcado por el propietario.
- Deuda declarada: el umbral de D7 punto 6 sigue sin medir en la máquina del
  propietario; se mide al cerrar la palanca 2.

## Alternativas descartadas y por qué

Ver «Opciones consideradas»: abrir con el criterio del 02-09 (números
insuficientes, por decisión del propietario) y el modelo mayor como única
palanca (la búsqueda da 0/47 antes de cualquier filtro).
