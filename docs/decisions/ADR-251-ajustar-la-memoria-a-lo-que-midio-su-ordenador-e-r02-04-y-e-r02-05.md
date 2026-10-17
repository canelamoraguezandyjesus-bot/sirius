# ADR-251 — Ajustar la memoria a lo que midió su ordenador: E-R02-04 y E-R02-05

- Estado: APROBADO
- Fecha: 2026-10-17
- Aprobación: la fusión de la PR que lo lleva a `main`.

## Nota de arranque

Publicada antes del primer commit en la incidencia #693, y copiada aquí sin cambiar lo
que dice.

1. **Dónde vive el fallo y dónde va el arreglo.**
   - Buscar por significado: el umbral de parecido, 0,5
     (`src/sirius/application/memory_search.py`), se fijó sin sus datos (ADR-238) y deja
     fuera lo que el modelo sí relaciona; las huellas se pedían sin el formato que
     recomienda cada modelo para buscar.
   - Buscar por palabras: «tiene» no era palabra vacía, y a «¿Cuántos metros tiene el
     salón?» le traía «Tiene dos gatos.» (MB-071).
   - El orden: lo más nuevo solo desempataba con parecidos exactamente iguales, y en
     «cosas que cambian» lo de antes suele parecerse más a la pregunta que lo de ahora.
   - El tiempo: con 10.000 huellas, casi toda la búsqueda era calcular 10.000 cosenos
     en sqlite-vec: 35 de 40 ms aquí, y en su máquina unas 3,4 veces más.
   - El arreglo: EmbeddingGemma por defecto, con su formato en la pregunta y en los
     recuerdos y el formato en la clave de las huellas; umbral 0,26 para ese formato;
     «tener» y «cuánto» vacías; desempate por lo más nuevo; y buscar en dos pasos.
   - **¿Puede el sitio del arreglo observar el fallo?** Sí: con los cosenos que midió su
     ordenador se rehacen unas huellas que los cumplen, y el banco pasa por el camino
     real. Reproduce sus 100 casos uno a uno, 70 y 77, sin ningún caso distinto.
2. **Qué NO garantiza.**
   - Que pase en su ordenador: lo dicen E-R02-04 y E-R02-05 cuando las repita.
   - El umbral, las palabras vacías y el desempate se ajustan con los mismos 100 casos;
     con frases nuevas puede acertar menos.
   - El desempate está a 0,01 o 0,02 de romper «quién dijo qué» en su propio banco
     (MB-086).
   - «Cosas que cambian» no se arregla de raíz: ADR-239 lo deja a los hechos con persona
     y tema, y el banco guarda recuerdos sin tema.
   - Los bits son aproximados cuando hay más de 200 candidatas; su acierto con huellas de
     verdad por encima de 1.000 recuerdos no se mide aquí.
   - La cifra de su máquina se estima con dos medidas suyas.
3. **Criterio de parada.**
   - Con sus cosenos, por el camino real y con el código nuevo, el banco tiene que dar 90
     o más, con 14 de 14 en «olvida eso» y en «quién dijo qué»; si no, no se entrega y
     se le pregunta, porque cambiar de enfoque es producto (ADR-238).
   - La búsqueda con 10.000 huellas, escalada a su máquina, por debajo de 150 ms en el
     P95 con al menos un 30 % de margen; si no, no se entrega.
   - Su base de hoy, con 1 recuerdo con huella de qwen3, se abre con el modelo nuevo
     sin mezclar huellas.
   - Cada regla nueva, con una prueba vista fallar.
   - Dos rondas con defectos de la misma familia: se para y se busca la raíz.
   - Lo que solo se puede ver en su ordenador se escribe con esas palabras.
4. **Qué lo haría imposible en vez de improbable.**
   - Mezclar huellas de dos modelos o dos formatos: imposible; la clave lleva el modelo
     y el formato, la búsqueda solo compara las de su clave, y la huella nueva de un
     recuerdo sustituye a la vieja.
   - Que dos pasos pierdan algo que traería un paso: con 1.000 huellas o menos,
     imposible, porque va en uno. Por encima, se mide.
   - Que el resultado dependa de algo nuestro en su ordenador: las dos órdenes solo
     necesitan Ollama con embeddinggemma, que ya tiene.

## Contexto y problema

El 16-10-2026 pasó en su ordenador las dos evaluaciones de la memoria de la 0.2:

- **E-R02-04**: 70 de 100 con qwen3-embedding:0.6b y 77 con embeddinggemma; hacen falta
  90, con todos los de «olvida eso» y «quién dijo qué», que sí dieron 14 de 14.
- **E-R02-05**: con 10.000 recuerdos de prueba, P95 de 170 ms; el límite es 150. Con su
  memoria, de 1 recuerdo, 61 ms.

Con la orden de diagnóstico de la PR #692 pasó otra vez el banco con los dos modelos y
pegó, caso a caso, lo que trajo y los parecidos de la pregunta con cada recuerdo y de
cada par de recuerdos, como se piden hoy y con el formato que recomienda cada modelo.
Con esos cosenos se rehicieron aquí unas huellas que los cumplen, y el banco pasó por el
camino real: reproduce los 100 casos de cada modelo uno a uno. Lo que sale de ahí:

- **Personas y gustos**: el umbral 0,5 deja fuera recuerdos que el modelo sí relaciona.
  Solo por palabras el banco da 64; la búsqueda por significado de hoy le añadía 6.
- **No lo sé**: MB-071, por la palabra «tiene».
- **Cosas que cambian**, 2 de 14: el orden. Con lo de antes 0,01 o 0,02 más parecido que
  lo de ahora, 0 de 14; con lo de ahora más parecido, 14 de 14. Las huellas de mentira
  de la nube hacían que lo de antes no se pareciera a nada, y por eso nunca se vio.
- **El tiempo**: de los 40 ms de la búsqueda con 10.000 huellas aquí, 35 son los cosenos;
  leer las huellas, 4.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, publicado en la incidencia #693 antes del primer commit.

## Opciones consideradas

1. **Umbral, formato, palabras vacías, desempate por lo más nuevo y dos pasos.** Esta.
2. **Solo umbral, formato y palabras vacías.** Da 89: a uno de 90.
3. **«Cosas que cambian» como hechos**, como dice ADR-239: lo nuevo cierra lo viejo de la
   misma persona y el mismo tema. Es cambiar de enfoque: hay que decidir quién pone el
   tema, el sueño o él, y que el banco lea también los hechos. Es producto, y se le
   pregunta aparte.
4. **Para el tiempo, la búsqueda exacta más rápida**: vec0 de sqlite-vec con mmap, 19 ms
   aquí; en su máquina, unos 140 ms de P95. Demasiado justo.
5. **Desempatar por palabras de cambio** («ahora», «ya», «ha» y participio): 99, pero
   escrita sobre cómo se redactó el banco.

## Decisión

La opción 1. Las decisiones son técnicas y caben en lo que permite ADR-238, que dejó el
umbral para que lo moviera lo que dijera E-R02-04; las toma la sesión (ADR-204).

- **EmbeddingGemma por defecto**, con el formato de su ficha: la pregunta como
  `task: search result | query: …` y cada recuerdo como `title: none | text: …`. El
  formato va en la clave de las huellas, `embeddinggemma#busqueda-1`: las de antes se
  vuelven a calcular y ninguna se compara con las de otra clave. Un modelo sin formato
  conocido se pide tal cual, con el umbral de siempre.
- **Umbral 0,26** para ese formato: el centro del tramo, de 0,24 a 0,28, en el que el
  banco da lo mismo.
- **«tener» y «cuánto», vacías** solo en la búsqueda de recuerdos de cada turno
  (`VACIAS_DE_LOS_RECUERDOS`). La lista del laboratorio no cambia: la usan el motor por
  etapas y el banco de 47 casos.
- **Lo más nuevo que dice casi lo mismo, delante**: si un recuerdo más nuevo que el
  primero, traído también por significado, se le parece 0,70 o más y a la pregunta como
  mucho 0,05 menos, pasa delante. Solo uno, y solo delante del primero.
- **Dos pasos con muchas huellas**: cada huella guarda un bit por número, en un índice
  con su clave. Con más de 1.000 huellas, todas con bits, la búsqueda lee los bits del
  índice, se queda con las 200 más cercanas y calcula el coseno exacto de esas. Con
  1.000 o menos, o si a alguna le faltan bits, en un paso, como antes. Migración
  `43d72bb058bd`.
- **Las dos órdenes de su ordenador.** La de E-R02-04 con `--diagnostico` escribe el
  umbral del modelo, 0,26 con EmbeddingGemma, y «hoy» pide las huellas como las pide
  Sirius, con su formato. La de E-R02-05 escribe cada cuenta con su plural: «Tu memoria,
  1 recuerdo», no «1 recuerdos», como salió en su ordenador el 16-10-2026.
- **La vista de `MEMORIA.md`**: el resumen de cada ADR pasa de 240 a 160 caracteres
  (`LONGITUD_RESUMEN`). Con el árbol de la PR #692, en `f695f251` y en `dedb2cf6`, la vista ya ocupaba 119.993 de los
  120.000 bytes de una sola lectura, y detrás de este ADR va el de la voz, ADR-252. Medido
  sobre ese árbol con ADR-251 y ADR-252 de prueba, cada uno con su lección y su entrada en
  el registro, cada ADR así suma de 585 a 630 bytes; con otros dos después, la vista
  ocuparía 122.515 bytes con 240 caracteres, 121.091 con 200, 120.204 con 180, 119.717
  con 170 y 119.297 con 160. 160 es el recorte más pequeño que aguanta esos cuatro con
  holgura para un título largo: con 170 quedarían 283 bytes, menos de medio ADR. A 160 se
  cortan 22 de los 51 resúmenes desde ADR-200, y cada uno conserva su primera frase. Es la
  opción 3 que dejó ADR-218, que no toca lo que crece: cuando vuelva a no caber, hará
  falta otro corte.

## Comprobación que la sostiene

Todo aquí, en la nube. Lo que solo se ve en su ordenador va al final.

- **El banco de su ordenador, rehecho.** Con la matriz de cosenos de cada caso que pegó
  el 16-10-2026, sacada con la orden de diagnóstico de la PR #692, se sacan vectores que
  la cumplen (Cholesky) y el caso pasa por `pasa_un_caso`, el camino real. Con el código
  de antes reproduce sus 100 casos uno a uno: 70 con qwen3 y 77 con embeddinggemma, y
  ningún caso con otro resultado ni con otros recuerdos traídos.
- **El umbral y el formato, barridos por ese camino** (antes de este código):
  | Modelo y forma | Mejor | Umbral |
  |---|---|---|
  | qwen3, tal cual | 82 | 0,32 |
  | qwen3, con su formato | 83, y 84 con las vacías | 0,38 a 0,40 |
  | embeddinggemma, tal cual | 81 | 0,36 y 0,40 a 0,42 |
  | embeddinggemma, con su formato | 88, y 89 con las vacías | 0,24 a 0,28 |

  Con 0,29, 88. En ese tramo se cambia MB-022, de gustos, parecido 0,2504, por un
  recuerdo de «no lo sé» que entra entre 0,25 y 0,26.
- **El desempate, en rejilla** (embeddinggemma con formato, 0,26 y las vacías): con
  δ de 0,03 o 0,05 y τ de 0,66 a 0,76, de 90 a 93, con «quién dijo qué» 14 de 14. Con τ
  de 0,68 o menos y δ de 0,08 o más, «quién dijo qué» baja a 13: lo rompe MB-086, que se
  parece al primero 0,68 y a la pregunta 0,06 menos. La regla ingenua, τ 0,58 y δ 0,25,
  da 88 con «quién dijo qué» 10, gustos 10 y fechas 11. Con qwen3, como mucho 86.
- **El código nuevo, por el mismo camino**: embeddinggemma, 93 de 100: personas 15 de
  15, gustos 14 de 15, cosas que cambian 8 de 14, fechas 14, no lo sé 14, quién dijo qué
  14 y olvida eso 14. Fallan MB-022 y seis de cosas que cambian. qwen3 tal cual, 70.
- **La búsqueda con 10.000 recuerdos**, con la orden de E-R02-05 y unas huellas al azar
  que no tardan, alternando cuatro veces el código de `main` (qwen3, 1.024 números, un
  paso) con el nuevo (embeddinggemma, 768, dos pasos) en la misma máquina:
  - antes: P50 de 36,8 a 38,0 ms y P95 de 45,0 a 47,3;
  - ahora: P50 de 9,4 a 10,2 ms y P95 de 17,0 a 19,1.
  Del nuevo, en SQL: leer los bits del índice, 2,8 ms; sus distancias, 1,3; quedarse con
  las 200, 0,6; los dos pasos enteros, 6,0 de P50.
- **Escalado a su máquina** con sus dos medidas del 16-10-2026, 61 ms de P95 con 1
  recuerdo, que es sobre todo la huella de la pregunta, y 170 con 10.000: su búsqueda era
  unas 2,5 veces la de aquí en el P95 y 3,4 en el P50. Con el código nuevo, P95 de unos
  99 ms, un 34 % por debajo de 150, y P50 de unos 58.
- **Su base del 16-10-2026**, migrada desde `b0f472943480` con 1 recuerdo y su huella de
  qwen3: con embeddinggemma, la de qwen3 no se compara con la pregunta, se vuelve a
  calcular, y queda una sola huella, de 768 números, con sus bits y su clave
  (`tests/integration/test_memoria_en_su_ordenador.py`).
- **Mutación**: 21 mutaciones, una por regla nueva; caen las 21. Dos sobrevivían en la
  primera pasada, «dos pasos con pocas huellas» y «desempatar con lo que solo traen las
  palabras», y sus pruebas se reforzaron.
- **La batería entera**: pendiente. Se pasa sobre el árbol completo de la PR, y su cifra
  se anota aquí antes de fusionar.
- **Lo que solo se ve en su ordenador**: lo que dan E-R02-04 y E-R02-05 al repetirlas;
  lo que tarda la huella de la pregunta con embeddinggemma, que aquí se supone igual que
  con qwen3; y que la búsqueda en dos pasos, por encima de 1.000 recuerdos de verdad,
  traiga lo mismo que en uno.

## Consecuencias

- La primera vez que abra la ventana, Sirius vuelve a calcular las huellas de todos sus
  recuerdos con EmbeddingGemma. Él tiene 1.
- Con qwen3 en los ajustes todo sigue como antes, salvo las palabras vacías y el
  desempate: con su banco, 70.
- Con más de 1.000 recuerdos la búsqueda es aproximada: lo que no esté entre las 200 más
  cercanas por bits no llega al coseno.

## Alternativas descartadas y por qué

Las opciones 2 a 5, por lo que dice cada una.

## La lección

- familia: doble-mas-permisivo-que-la-herramienta-que-dobla
- sin esto se repetiría: el banco de memoria pasaba en la nube con unas huellas de
  mentira en las que solo lo esperado se parecía a la pregunta; con un modelo de verdad
  lo de antes también se parece, y «cosas que cambian» cayó a 2 de 14 en su ordenador
- lo hace cumplir: tests/integration/test_memoria_en_su_ordenador.py
