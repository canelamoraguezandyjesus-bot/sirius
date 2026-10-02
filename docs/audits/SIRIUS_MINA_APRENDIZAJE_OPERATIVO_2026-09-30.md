# La mina, tercera edición: septiembre entero, y la bitácora puesta contra `main` entrada a entrada

- Fecha: 2026-10-01 (ventana medida: 2026-09-01T00:00:00Z → 2026-09-30T23:59:59Z).
- Ediciones anteriores: agosto (`SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md`),
  la mina v2 de la ola de criticidad del 02-03-09
  (`SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09.md`, que tres ADR citan por ese
  nombre y por eso lo conserva) y la segunda edición, ventana 01→14-09
  (`SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09-14.md`). Esta se nombra por el
  último día de su ventana, como aquella.
- La pidió el propietario el 01-10-2026: «que la mina revise todo» y, después,
  «todos los problemas que se han salido este mes se mejoren […] Todo lo que
  está apuntado en la bitácora. Todo, uno a uno, se mide y se crean mejoras».
  Por eso esta edición añade a las secciones de siempre una lista nueva: las
  146 entradas de la bitácora del ciclo, cada una con su estado real contra
  `main` (§6).
- Quién la escribe: la sesión que cerró el ciclo el 24-09 (ADR-216), no un
  encargo del motor. Lo dice para que se lea con ese sesgo: §5 mide, entre
  otras, las rondas de sus propias PR.

## Nota de método (escrita ANTES de los resultados)

La nota de arranque se escribió en el contenedor el 2026-10-01 a las 04:45 UTC
(hora de creación del fichero), antes de ejecutar ningún análisis y antes de
que ningún agente clasificara una sola entrada; la muestra de verificación se
fijó a las 04:56 UTC, antes de que ningún agente terminara. Se reproduce lo que
decidía, y al lado lo que pasó.

**Cuatro preguntas y su predicción.**

1. *Rondas y goteo en el mes entero.* Predicción: la mediana sube de 4 a entre
   5 y 6 por la segunda quincena (#653 con 5, H4 con 14); el goteo declarado
   sigue siendo casi todo de CLAUDE. **Falló la mitad**: la mediana se queda en
   4 (§2), porque la segunda quincena casi no tiene rondas del motor; el goteo
   sí es casi todo de CLAUDE (§3).
2. *Familias.* Predicción: F1 («la ficha afirma algo que su propio árbol deja
   de sostener») sigue primera, y aparece como segunda «afirmar lo que hace un
   mecanismo sin ejecutarlo ni leer su regla de rechazo». **Acertó** (§7).
3. *La bitácora contra `main`.* Predicción: un tercio resuelto, un tercio
   abierto, un tercio narración; de las 48 deudas, la mitad abiertas y cinco
   del propietario. **Falló en la narración** (12 %, no 33 %) y en no prever
   la categoría grande, «parcial» (36 %); y se quedó corta en las deudas:
   **35 de 48 no están cerradas** (18 abiertas, 7 parciales y 10 que esperan
   una decisión del propietario), no la mitad (§6.3).
4. *Guardianes.* Predicción: el que más defectos reales habría cazado es el
   detector de familia repetida ya arreglado el 14-09, por delante de cualquier
   guardián nuevo. **Acertó, con un coste**: 9 familias reales (10 tramos sin
   aviso en 8 incidencias, uno de ellos el falso positivo) que el detector de
   entonces dejó pasar y el de hoy ve en alguna ronda, y **1 falso positivo
   nuevo** (#566, por el criterio de la edición anterior): neto +8 (§4.3, §8).

**Criterio de parada, escrito antes de contar nada.** Menos de 10 avisos del
detector en la ventana → no se publica tasa. Dos agentes en desacuerdo sobre la
misma entrada → gana `abierta`. Ninguna entrada es `resuelta` sin evidencia en
`main` (ADR `APROBADO` que la implemente, o código y prueba presentes); un ADR
que solo la propone es `parcial`. Dos rondas de revisión externa con la misma
familia sobre esta edición → parar y buscar la raíz.

**Muestra de verificación propia, fijada antes de leer ningún triaje:**
entradas 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140 y 146. Si
el sentido dominante de las correcciones fuera hacia «más abierto», la lista se
publica con esa advertencia y las `resuelta` sin ADR citado bajan a `parcial`.
**Se disparó** (§6.2): una corrección, hacia «más abierto», y la regla se aplicó
tal como estaba escrita.

**Qué NO garantiza esta edición.** No es una auditoría del repositorio. Cuenta
las rondas y hallazgos que los revisores publicaron; no verifica cada hallazgo.
No implementa, no cablea, no decide: las mejoras van en ADR propios, después
(§10 las ordena). La lista de §6 la produjeron siete agentes leyendo `main`; se
publica con la evidencia que cada uno cita y con el resultado del muestreo.

**Criterio de pertenencia a la ventana.** El de la edición del 14-09: una
incidencia entra si alguno de sus `<!-- sirius-round:N -->` lo publicó un autor
de confianza (`OWNER` o `github-actions[bot]`, el filtro de
`scripts/automation/sirius_issue.sh`) dentro de la ventana; una ronda entra si
su comentario cae dentro. Se descargaron todas las incidencias con actividad
desde el 25-08-2026.

**Una decisión tomada después de ver el primer resultado, y se dice.** Al
contar, la segunda quincena tenía **2** incidencias con rondas del motor (§2).
El trabajo no había desaparecido: había cambiado de cauce, a PR de sesión
revisadas por Codex sin pasar por el ciclo del motor. Por eso esta edición
añade una segunda población (§5), cuyo criterio se escribió en el guion que la
cuenta antes de ejecutarlo: una ronda es una *review* de
`chatgpt-codex-connector[bot]` o su comentario de conversación «Didn't find any
major issues» (así publica las limpias), y un hallazgo es un comentario en
línea suyo con insignia `P0..P4` que no sea respuesta. Es una población distinta
de la del motor y se compara con cuidado: las rondas del motor agregan a los
dos revisores; estas son solo Codex.

**Fuentes y reproducción.** La API de GitHub (solo lectura, 376 incidencias y
3 036 comentarios, 233 PR con sus reviews y comentarios en línea), los
analizadores del propio motor (`sirius_engine.round_history.parse_round_records`,
`history_after_last_resume`, `sirius_engine.drip_guard.parse_archivo_location`)
y el detector instalado (`uv run sirius-familia-repetida`), sin reimplementar
nada. Los guiones están en `scripts/mina/` (`descargar.py`, `descargar_pr.py`,
`analizar.py`, `analizar_pr.py`, `reproducir_avisos.py`, `falsos_negativos.py`,
`cerrado_por_inalcanzable.py`). Leen y escriben en el directorio que diga
`MINA_DATOS` (por defecto `scripts/mina/datos/`, fuera del repositorio), en
ese orden, y no dependen de dónde viva el clon ni desde dónde se invoquen;
cada cifra de este informe que no sea una lectura a mano sale de su salida, y la
clasificación de falsos negativos tiene sus pruebas en
`tests/automation/test_mina_falsos_negativos.py`.
Repetir la cadena sobre el mismo `MINA_DATOS` refresca el volcado entero: los
guiones de descarga escriben en un directorio aparte (`raw.parcial`,
`raw_pr.parcial`) y lo publican entero al terminar con un selector
(`raw.actual`, el nombre de la foto publicada) sustituido de forma atómica, así
que una descarga que se interrumpa no mezcla un índice nuevo con historiales
viejos ni retira la foto visible (el volcado anterior sigue siendo la última
foto completa hasta que la nueva está seleccionada, y los dos analizadores
avisan de un parcial o de una foto sin seleccionar en cualquiera de los dos
volcados, lean el que lean, y de que `raw` y `raw_pr` no sean de la misma
captura: `descargar.py` escribe una marca de captura y `descargar_pr.py` la
copia; los dos volcados de esta edición son una sola captura, la del 01-10 de
04:45 a 04:58 UTC, y la marca se les escribió a posteriori); los analizadores se
detienen si el volcado que leen no existe o está vacío (un `MINA_DATOS` nuevo
no es «cero PR y cero hallazgos»); un comentario creado en la ventana y editado
después del 30-09 queda fuera de la evidencia, porque la API devuelve el cuerpo
vigente con la fecha de creación original y el de septiembre no se puede
reconstruir (en esta captura, 0 de los 1 545 comentarios de confianza de la
ventana, cifra que `analizar.py` imprime y guarda en `resumen.json`; los
comentarios de Codex en las PR de esta captura no guardan la fecha de edición,
así que para ellos no se puede saber y el analizador lo avisa; las descargas
posteriores la guardan, y una captura de `raw` empareja un solo volcado de PR,
así que renovarla es repetir la cadena entera); y cada `sirius-round:N` cuenta una vez por incidencia aunque GitHub
lo hubiera publicado dos veces. Y la reconstrucción ronda a ronda solo cuenta rondas y avisos
publicados dentro de la ventana 01→30-09: lo anterior al 01-09 es contexto del
detector, no medición; y un tramo que el detector ya marcaba entero con lo
publicado antes del 01-09 no se atribuye a septiembre salvo que crezca dentro
de la ventana (y entonces lo cubre también el aviso anterior que ya lo cubría:
la familia estaba avisada).
**Comprobación del instrumento**: sobre la subventana 01→14-09 el guion devuelve
exactamente lo que la edición anterior publicó —30 incidencias, 122 rondas,
301 hallazgos—, así que las dos ediciones son comparables fila a fila.

## 1. Distribución de hallazgos (el ciclo del motor)

Datos: los **314 hallazgos** de los bloques `RONDA_HALLAZGOS` de las **130
rondas** que **32 incidencias** publicaron dentro de la ventana. De ellos, 301
hallazgos / 122 rondas / 30 incidencias son del 01→14 (la edición anterior) y
**13 hallazgos / 8 rondas / 2 incidencias** (#650 y #653) del 15→30.

### 1.1 Por fuente

| Fuente | Hallazgos | % |
|---|---|---|
| CLAUDE | 202 | 64,3 % |
| CODEX | 112 | 35,7 % |
| **Total** | **314** | 100 % |

El reparto de la primera quincena (64,8 / 35,2) no se mueve: la segunda
quincena aporta 13 hallazgos y no cambia nada.

### 1.2 Por gravedad, dentro de cada fuente

| Fuente | Gravedad | Hallazgos |
|---|---|---|
| CLAUDE | baja | 73 |
| CLAUDE | media | 58 |
| CLAUDE | p3 | 17 |
| CLAUDE | alta | 15 |
| CLAUDE | menor | 14 |
| CLAUDE | p2 | 12 |
| CLAUDE | p1 | 8 |
| CLAUDE | mayor | 2 |
| CLAUDE | media-baja | 2 |
| CLAUDE | moderada | 1 |
| CODEX | p2 | 77 |
| CODEX | p1 | 26 |
| CODEX | p3 | 9 |

La taxonomía de CLAUDE sigue sin normalizar (diez etiquetas, tres fuera de
`SEVERITY_WEIGHTS`); la de CODEX sigue íntegra en P1–P3. Nada cambió desde el
14-09.

### 1.3 Por tipo de fichero

| Tipo | Hallazgos | % |
|---|---|---|
| código (`.py`) | 164 | 52,2 % |
| documentos (`.md`) | 115 | 36,6 % |
| otros | 18 | 5,7 % |
| guiones (`.sh`/`.ps1`) | 13 | 4,1 % |
| workflows (`.yml`) | 4 | 1,3 % |

Los 13 hallazgos de la segunda quincena: 7 sobre `.md`, 2 sobre `.py`, 4 otros.

## 2. Rondas por incidencia

Datos: las 32 incidencias, contando solo las rondas publicadas dentro de la
ventana.

- Media **4,06**, mediana **4**, máximo 15.
- Distribución (rondas → incidencias): 1→4, 2→3, 3→8, 4→10, 5→4, 7→1, 14→1,
  15→1. Con más de una ronda: **28 de 32**.
- Por quincena: 01→14, 30 incidencias, media 4,07, mediana 4; **15→30, 2
  incidencias** (#650: rondas 1-3; #653: rondas 1-5), media 4,0.

| Incidencia | Rondas en la ventana |
|---|---|
| #545 | 15 |
| #581 | 14 |
| #574 | 7 |
| #508, #529, #541, #653 | 5 |

**El dato del mes no está en la media: está en el 2.** Del 15 al 30 de
septiembre el ciclo del motor —despachar, implementar, revisar con dos
revisores, corregir, fusionar— se usó dos veces. Todo lo demás que entró en
`main` en esa quincena (ADR-204 a ADR-217, cinco PR de sesión) no pasó por él.
§5 mide ese otro cauce.

## 3. Goteo: lo que el revisor declara y lo que el guardián marca

Base: las **213 observaciones** de rondas N>1 publicadas en la ventana (CLAUDE
137, CODEX 76). Mismo instrumento que la edición del 14-09: se cuentan
autodeclaraciones, no se verifica contra el diff.

| Fuente | Observaciones N>1 | Se declaran goteo | % |
|---|---|---|---|
| CLAUDE | 137 | 57 | **41,6 %** |
| CODEX | 76 | 2 | **2,6 %** |

El guardián de goteo (ADR-123/ADR-133) marcó **37 observaciones en 15
incidencias**, las mismas 37 del 14-09: la segunda quincena no añadió ninguna.
Y la clave `posible_goteo` sigue apareciendo en **cero** de los 213 JSON
publicados: `scripts/automation/sirius_apply_verdict.sh:716-784` la retira
como clave reservada antes de publicar y solo la vuelve a pintar en la prosa.
Es el mismo hueco que §3.3 de la edición anterior declaró; no se ha movido.

**Un dato nuevo, el alcance del guardián.** El guardián solo puede juzgar una
observación cuyo campo `archivo` lleve una línea que
`parse_archivo_location` reconozca. Medido sobre los 314 hallazgos del mes
con esa misma función, la del guardián en producción (`analizar.py`, §3.4 de
su salida):

| Fuente | Con `fichero:línea` reconocible | % |
|---|---|---|
| CLAUDE | 118 de 202 | 58,4 % |
| CODEX | 3 de 112 | **2,7 %** |

El guardián no ve a CODEX: no por su lógica, sino porque CODEX cita la ruta
desnuda. Cualquier medición de goteo de CODEX con este instrumento mide el
formato de salida de CODEX, no su disciplina.

## 4. El detector de familia repetida, mes entero

### 4.1 Lo que avisó

**13 comentarios** `AVISO_FAMILIA_REPETIDA` en la ventana, en **8
incidencias**: #520 (2), #526 (2), #529, #539, #545, #581 (2), #597 (2) y
#653 (2). Un aviso se reconoce por su cabecera (`## AVISO_FAMILIA_REPETIDA` al
principio de línea), no por la subcadena: la primera versión de este informe
contaba 14 porque sumaba el comentario del propietario en #520 (03-09, 17:12
UTC: «Sobre el `AVISO_FAMILIA_REPETIDA`: es exacto…»), que es una mención, no
un aviso. Los 11 primeros son los de la edición anterior, que los clasificó
uno a uno: 8 casos, 8 ACERTADO. Los dos de #653 se clasifican aquí con el
mismo criterio:

| Incidencia | Fichero | Tramo | Veredicto | Evidencia |
|---|---|---|---|---|
| #653 | `docs/decisions/ADR-212-…` | rondas 2-4 y 2-5 | **ACERTADO** | La misma afirmación cuatro rondas seguidas: lo que la ficha declara validado no coincide con el head. r2 `CODEX-001` («el head final añade a `d8cf2756` solo este párrafo» es falso: añade una sección entera), r3 `CODEX-001` (la enumeración de lo no validado sigue incompleta: falta la tabla y la rectificación), r4 `CLAUDE-R5-001` (la sección «Comprobación» ancla la validación a un árbol y dos commits nuevos la falsean), r5 `CLAUDE-R7-001`/`-002` y `CODEX-001` (regresión incompleta de la corrección anterior; atribución residual a Quality). Es F1, y la propia bitácora lo cuenta en sus entradas 130, 131 y 141. |

**Acumulado: 9 casos en septiembre, 9 ACERTADO; 13 de 13 con ADR-078.** Trece
comentarios superan el umbral de 10 que el criterio de parada fijó, así que
esta vez sí se puede decir con esas palabras: sobre lo que avisa, el detector
no ha fallado ninguna vez en dos meses.

### 4.2 Todos los avisos se reproducen con el detector de hoy

Para separar «el detector cambió» de «el historial cambió», se reconstruyó
para cada aviso el historial que el motor veía en ese instante (comentarios de
confianza hasta el que llevó el aviso, tras el último marcador de reanudación)
y se pasó el detector instalado hoy (`reproducir_avisos.py`, que llama al
mismo código que `sirius-familia-repetida`) y se compararon las evidencias del
aviso con las de hoy, fichero a fichero: **13 de 13 avisan** sobre el mismo
fichero y con un tramo que contiene entero el publicado (no basta con que el
detector vea alguna familia en la incidencia, ni con que los tramos se
solapen). El detector de hoy es un superconjunto del de entonces, no otro
detector.

### 4.3 Cuántas veces no avisó, y desde cuándo ya no pasa

La edición del 14-09 encontró 6 falsos negativos por una sola línea
(`LOCATION_LINE_RE` recortaba solo cuando la cita terminaba en `:N`) y lo
propuso arreglar; las incidencias #638 y #642 lo cerraron el 14-09. Esta
edición lo mide con `falsos_negativos.py`, que recorre las 32 incidencias de
`resumen.json` y, para cada una, reconstruye **ronda a ronda** lo que el motor
veía en ese instante (los comentarios de confianza hasta esa ronda, incluida, y
nunca más allá del 30-09) y le pasa el detector de hoy, el mismo código que
`sirius-familia-repetida`. Mirar solo el historial final no vale: un
`continua` posterior saca del tramo vigente una familia que sí habría avisado
antes (lo cazó Codex en la revisión de este informe; la clasificación es una
función pura con sus pruebas en `tests/automation/test_mina_falsos_negativos.py`).

La unidad es el **tramo** —un fichero con hallazgos en tres o más rondas
consecutivas—, no la incidencia: #570 tiene dos tramos reales distintos (1-3 y
2-4), como ya contaba la edición del 14-09 («6 falsos negativos en 5
incidencias»); contar incidencias los fundía en uno (lo cazó Codex en la ronda
3 de la revisión de este informe). La identidad de un tramo es el fichero **y
la racha**: el mismo fichero en las rondas 1-4 y, tras un `continua`, en las
5-9, son dos tramos (#581 tiene tres); una evidencia que solapa con un tramo ya
visto es ese mismo tramo, que crece. Y un aviso cubre exactamente lo que
publicó —sus líneas «fichero … (rondas a-b)»—: un tramo está cubierto si algún
aviso de su incidencia, dentro de la ventana, lista ese fichero con una racha
que solapa con la suya. Comparar solo instantes no valía: tras un `continua`,
un aviso por otra familia no pudo contener la anterior. Las dos cosas las cazó
Codex en la ronda 4 de la revisión de este informe, y las dos cambiaban la
cifra: con la identidad por fichero solo, el segundo tramo de #545 y los dos
últimos de #581 quedaban fundidos con el primero, que sí tuvo aviso.

Resultado: el detector de hoy marca **19 tramos en 14 incidencias** (#520,
#523, #526, #529, #539, #545, #566, #570, #574, #581, #597, #599, #601 y
#653); **9** tramos los cubrió un aviso de la ventana, y **10 no recibieron
ninguno**, en 8 incidencias:

| Incidencia | Tramo (fichero, rondas) | Primera ronda en la que marca el detector de hoy |
|---|---|---|
| #523 | `ADR-133-g3-el-guardian-de-goteo-entiende…` (2-4) | ronda 4, 04-09 15:52 UTC |
| #545 | `reflect.py` (8-10; el tramo 1-3 sí tuvo aviso) | ronda 10, 07-09 19:11 UTC |
| #566 | `ADR-162-la-altura-de-una-fila-del-chat…` (1-3) | ronda 3, 08-09 03:43 UTC |
| #570 | `ollama_query_intent_classifier.py` (1-3) | ronda 3, 08-09 10:39 UTC |
| #570 | `ADR-164-la-pregunta-se-convierte-en-una…` (2-4) | ronda 4, 08-09 11:12 UTC |
| #574 | `ADR-166-el-cargador-del-banco…` (1-6; en la 7 el tramo se corta) | ronda 3, 08-09 14:14 UTC |
| #581 | `ADR-177-la-ampliacion-por-categoria…` (5-9; el tramo 1-4 tuvo dos avisos) | ronda 7, 13-09 00:48 UTC |
| #581 | `ADR-177-la-ampliacion-por-categoria…` (10-14) | ronda 12, 13-09 05:00 UTC |
| #599 | `sirius_apply_verdict.sh` (1-4) | ronda 3, 13-09 02:21 UTC |
| #601 | `intent_interpreter.py` (1-3) | ronda 3, 13-09 12:10 UTC |

Los diez son **anteriores al 14-09**. #545 y #581 enseñan la forma más cara
del falso negativo: la incidencia tuvo aviso en su primer tramo, el
propietario escribió `continua`, y el mismo fichero volvió a recibir hallazgos
tres, cinco y hasta cinco rondas seguidas (en #581, de la 5 a la 14 sobre el
mismo ADR) sin que nadie volviera a avisar. Después del arreglo solo dos incidencias
tuvieron rondas (#650, sin familia; #653, avisada en r4 y r5): **0 falsos
negativos conocidos tras el 14-09**.

Tres rondas sobre el mismo fichero no demuestran por sí solas una familia
(#566 lo prueba), así que los tramos sin aviso se clasifican **caso a caso**.
Seis los validó la edición del 14-09 (su §4.4: #523, los dos de #570, #574,
#599 y #601); #566 es el falso positivo; y los tres que esta edición añade se
validan aquí, leyendo las observaciones estructuradas de cada ronda en el
volcado (lo cazó Codex en la ronda 7 de la revisión de este informe: la
primera versión se los atribuía a la edición del 14-09, que no los vio):

| Tramo | Lo que dicen las rondas (observaciones estructuradas del volcado) | Veredicto |
|---|---|---|
| #545 `reflect.py` (8-10) | r8 `CLAUDE-R9-001`: «Código NUEVO de la ronda 8 (commit d8553d7, corrección de CLAUDE-R8-002)», las afirmaciones nuevas sobre `_hay_una_parada_posterior_sin_aviso` no se sostienen; r9 `CLAUDE-R10-001` (P2): `_recorrer_historial_acreditado` pasa mal las paradas al ancla, y el revisor lo declara «LLEGA TARDE POR GOTEO DEL REVISOR… idénticas a las de la ronda 7»; r10 `CLAUDE-R11-001` (P1): «Código NUEVO de la corrección de la ronda 10 (commit 1b7c815…)», `_paradas_que_el_recorrido_debe_recrear` filtra con el predicado equivocado. Tres rondas sobre el mismo mecanismo —qué paradas recrea el recorrido acreditado tras ADR-157—; dos nacen de la corrección anterior y una es goteo declarado. | **familia real (F2)** |
| #581 `ADR-177` (5-9) | r5 `CLAUDE-H4R6-001` (mayor): la sección «Validación obligatoria» la dejan falsa «dos commits NUEVOS» (traer main y regenerar MEMORIA); r6 `CLAUDE-H4R7-001` (mayor): el texto de la corrección anterior «lo falsificaron los dos commits que vinieron después»; r7 `CLAUDE-H4R8-001`: dos frases de la corrección de la r7, ciertas sobre su árbol, falsas tras «la TERCERA fusión»; r8 `CLAUDE-H4R9-002` y `CODEX-001`: las cifras de la sección 6 y un sha del `compare` que «nace de la evidencia añadida en esta corrección»; r9 `CODEX-001/002`: «Esta corrección vuelve falsa la clasificación…». Cada corrección ancla la prosa a un árbol que la fusión o la corrección siguiente cambian. | **familia real (F2)** |
| #581 `ADR-177` (10-14) | r10 `CLAUDE-H4R10-003`: «en la misma familia que las rondas 6, 7 y 8 —`prosa-que-el-cambio-deja-falsa` sobre anclas caducadas»; `CLAUDE-H4R10-004`: «la familia de defecto de las rondas 9 y 10»; r11 `CODEX-001`: «nace de las líneas nuevas de esta corrección»; r12 `CLAUDE-H4R12-001`: «código NUEVO de la corrección de la ronda 12»; r13 `CLAUDE-H4R13-001` y `CODEX-001/002`: «nace de la prosa añadida en esta corrección», y el `compare` termina en el padre del commit revisado; r14 `CODEX-001/002`: «el compare vuelve a excluir el commit actual». El propio revisor nombra la familia y cada corrección repite el mecanismo: un ancla que se excluye a sí misma. | **familia real (F2)** |

Nueve tramos reales y uno falso: las cifras de §8 (+9 familias reales, 1 falso
positivo, neto +8) salen de esta clasificación y de la del 14-09, no de la
señal estructural sola.

Una diferencia con la edición anterior, y conviene decirla: aquella clasificó
#566 como «no familia» (su tramo real eran dos rondas) y el detector de hoy
sí la marca en 1-3 por el fichero del ADR. Con el criterio de aquella edición
—que sigue siendo el de esta— #566 es un **falso positivo del detector de
hoy**, el primero conocido. Y #574, que aquella contó a mano con tramo 1-7,
hoy se marca desde la ronda 3 (no sobre el historial final, porque un
`continua` lo corta antes de la 7): la primera versión de este informe decía
que «hoy no se marca», y era verdad solo del historial final. Así que el
arreglo del 14-09 no es gratis: **+9 familias reales que antes se perdían
(#523, el segundo tramo de #545, los dos tramos de #570, #574, los dos tramos
tardíos de #581, #599, #601), 1 falso positivo nuevo (#566)**, neto +8, medido
sobre el mes entero y por tramos, que es la unidad que aquella edición ya
usaba.

## 5. La segunda población: Codex sobre las PR

Datos: **43 PR** con al menos una ronda de Codex dentro de la ventana. Se
separan por el nombre de la rama: las de `claude/*` son PR de sesión
(ADR-205: dos revisores sobre la PR, sin ciclo del motor); el resto son las PR
del motor, cuyas rondas de Codex ya entran agregadas en §1-§3.

| Población | PR | Rondas de Codex | …limpias | Hallazgos en línea | P1 / P2 / P3 |
|---|---|---|---|---|---|
| PR del motor | 38 | 185 | 98 | 122 | 27 / 83 / 12 |
| PR de sesión (`claude/*`) | 5 | 19 | 4 | 41 | 20 / 21 / 0 |

Las cinco PR de sesión, todas de la segunda quincena:

| PR | Qué era | Rondas (limpias) | Hallazgos | Gravedad | Fusionada |
|---|---|---|---|---|---|
| #658 | la auditoría de la forma de trabajar, paso 5 | 3 (1) | 4 | P2 ×4 | 21-09 |
| #659 | siete skills de flujo (ADR-214) | 6 (1) | 10 | P1 ×1, P2 ×9 | 21-09 |
| #660 | reconstrucción de #659 | 4 (1) | 9 | P1 ×7, P2 ×2 | no (sustituida) |
| #661 | cinco skills (ADR-215) | 1 (0) | 2 | P1 ×1, P2 ×1 | 24-09 |
| #663 | el cierre del ciclo (ADR-216) | 5 (1) | 16 | **P1 ×11**, P2 ×5 | 24-09 |

Tres lecturas, y ninguna es cómoda:

- **37 de los 41 hallazgos de sesión caen sobre `.md`.** Las PR de sesión del
  mes fueron documentos y skills; lo que Codex encontró en ellas es casi todo
  F1: afirmaciones que el árbol no sostenía.
- **#663 es la peor PR del mes por hallazgos de primera gravedad** (11 P1 en 5
  rondas), y es de quien firma esta mina. ADR-216 deja escritas sus dos
  familias: afirmar lo que hace un mecanismo sin leer su regla de rechazo (el
  reflector, dos veces), y salvaguardas escritas en prosa debajo de un bloque
  de comandos que se ejecuta entero (tres defectos en dos rondas, más un cuarto
  que ninguna ronda vio).
- **Codex no limpia a la primera casi nunca**: 4 rondas limpias de 19 en las PR
  de sesión; en las del motor, 98 de 185, pero muchas de esas son re-peticiones
  automáticas tras cada corrección (#546: 21 rondas, 13 limpias).

## 6. La bitácora del ciclo contra `main`, entrada a entrada

La lista completa, con una fila por entrada y por deuda, está en
`docs/audits/mina-2026-09-30-bitacora-contra-main.md`; el dato crudo con el
que se generó, en `docs/audits/mina-2026-09-30-triaje.yml`.

### 6.1 Cómo se hizo

Siete agentes de lectura, cada uno con un tramo (1-25, 26-50, 51-75, 76-100,
101-125, 126-146, y las 48 deudas), leyeron cada entrada entera, extrajeron
qué falló y qué «mejor manera» proponía, buscaron en el árbol (ADR con `Estado:
APROBADO` que lo implemente, código, pruebas, workflows, skills, `AGENTS.md`) y
clasificaron con el criterio de la nota de método. Ninguno tocó el
repositorio. Cada fila lleva la evidencia que citó o los patrones con los que
buscó sin encontrar.

### 6.2 El muestreo propio

Las 15 entradas fijadas de antemano se verificaron a mano, leyendo la entrada
y comprobando la evidencia con `grep` sobre el árbol:

| Resultado | Entradas |
|---|---|
| Confirmadas | 10, 20, 30, 40, 50, 60, 70, 90, 100, 110, 120, 130, 140, 146 (**14**) |
| Corregidas | **80**: de `resuelta` a `parcial`. La parte (1) sí está (ADR-169); la parte (2), la regla sobre los patrones de los guiones de vigía, solo vive en un `.sh` archivado de `docs/audits/`, no en ninguna skill viva |

Una corrección de quince, hacia «más abierto». La regla preregistrada se
dispara con una, y se aplicó: la única `resuelta` cuya evidencia no citaba
ningún ADR (la entrada **77**) baja a `parcial`. El recuento de abajo ya la
lleva. Fuera de la muestra, al preparar §10 apareció una segunda: la **deuda
13** (C2, la cadena del contador de los siete días) estaba como `parcial` del
motor y es una decisión del propietario ya tomada el 13-09 (§6.4); la tabla
de deudas conserva la lectura del agente y esta nota la corrige.

### 6.3 El recuento

| Estado en `main` | Entradas | % |
|---|---|---|
| `resuelta` | 38 | 26 % |
| `parcial` | 52 | 36 % |
| `abierta` | 38 | 26 % |
| `no_aplica` (narra o mide, no propone) | 18 | 12 % |

De las 48 deudas del cierre del 21-09: **13 resueltas, 7 parciales, 18
abiertas, 10 que solo el propietario puede decidir**. De esas diez, cinco son
las D-1…D-5 de `docs/audits/decisiones-abiertas-del-propietario.md` (deudas
38, 39, 40, 42/43, 44); las otras cinco (6, 16, 27, 31 y la mitad de la 2) el
agente las clasificó así porque la propia deuda dice que necesitan su visto
bueno.

### 6.4 Lo que está abierto, agrupado por mecanismo

De las 90 entradas `abierta` o `parcial` y las 35 deudas no cerradas (18
abiertas, 7 parciales y 10 que esperan una decisión del propietario), la mayor
parte converge en pocos mecanismos. Se listan con la entrada o deuda que los
sostiene; §10 los ordena por lo que valen.

**Del motor (código, guiones, workflows):**

- El validador de encargos (`scripts/automation/validate_issue_body.py`) no
  comprueba `Perfil: rol@N`: #653 murió a los 6 s por una línea que faltaba
  (deuda 34; entradas 123, 138) ni avisa de un `rol@N` no vigente (deuda 35;
  entrada 124). Hoy el guion no contiene la palabra «Perfil».
- `continua` no puede reanudar una parada anterior a la PR: repone
  `implement-requested` pero no `planned`, y anuncia en verde un reinicio que
  se rechaza solo, dejando la incidencia sin etiqueta (deuda 36; entradas 126,
  139). Y un `continua` malformado sale en silencio con `exit 0`
  (`sirius_resume_on_command.sh:87-90`; entrada 29).
- La salida de una parada por familia repetida choca con el precheck de
  convergencia (deuda 46; entrada 145).
- El aviso de `ready-for-merge` sigue pidiendo «escribe **fusiona**» cuando
  desde ADR-205 el motor fusiona por aprobación dual
  (`.github/workflows/notify-sirius-state.yml:105`,
  `sirius_apply_verdict.sh:690`; deuda 47; entrada 146).
- La cola de ADR-200 trae `main` a la rama sin regenerar `MEMORIA.md` y Quality
  cae por la memoria: una vuelta del corrector, 25 minutos
  (`advance-sirius-after-quality.yml:426`; deuda 48; entrada 146).
- `printf '- PR: %s\n'` en `sirius_apply_verdict.sh:850` falla con `printf: - :
  invalid option` (entrada 100; reproducido hoy en bash).
- El motor ordena instantes como texto: `created_at: str` y G8 compara
  lexicográficamente, así que cada formato nuevo es un riesgo (deuda 20;
  entradas 52, 69).
- La contradicción de etiquetas que el reflector aparta a propósito
  (`WI-20260828-122242`, #392) no la ve nadie: H-216 (entrada 38; #662).
- El implementador muere en silencio al tope del job, sin reloj (deuda 30;
  entrada 92); una cuota de Codex agotada se descubre gastando la ronda
  (deudas 12, 16; entrada 106).
- Un cliente único de Ollama para los cuatro adaptadores (deuda 4; entradas 7,
  8): sigue habiendo cuatro copias del contrato HTTP, con el guardián de
  ADR-132 vigilándolas.
- El guardián de citas juzga las que van dentro de un `>` (entrada 84); el
  freno de convergencia no distingue hallazgos nacidos de convenios posteriores
  (entrada 102).
- **El `cerrado_por` de los defectos cerrados no se puede seguir desde
  `main`.** La skill `registro-de-defectos` manda dos commits (el arreglo, y
  la entrada con el sha del arreglo) y el repositorio fusiona aplastado desde
  ADR-205, así que el sha citado nunca es ancestro de `main`. Medido el 01-10
  con `scripts/mina/cerrado_por_inalcanzable.py` (clon entero, no superficial;
  `git cat-file -e` y `git merge-base --is-ancestor` contra `origin/main`)
  sobre los 68 defectos cerrados: **29 citan un commit que `main` no
  contiene**: los 14 cerrados desde el 20-09 (H-204 a H-215, H-217 y H-218,
  todos; los ocho de la PR #652 ni siquiera existen en un clon fresco), 13
  anteriores que viven solo en su rama de origen aplastada (H-1, H-2, H-4,
  H-5, H-6, H-8, H-10, H-12, H-14, H-18, H-20, H-23, H-24) y 2 con un sha
  corto que la skill no admite (H-7, H-9). Una primera cuenta a mano de esta
  misma edición dio 19 de 49; la del guion es la que vale, porque se puede
  volver a ejecutar. Lo cazó Codex en la PR #664, sobre H-217. No viene de la
  bitácora: viene de esta edición.

**Del método de las sesiones (skills, plantillas, `AGENTS.md`):**

- Las cinco «lecciones de encargos» (verificar cada premisa en el dato
  primario; escribir los casos de parada y vuelta; afirmación factual con su
  comando; el modelo de qué acredita qué; auditar la orden contra el árbol
  antes de lanzarla) solo viven en la bitácora (entradas 26, 31, 37, 39, 41,
  51, 54, 67, 78). No hay plantilla ni skill de encargo.
- En `cadena-de-comprobacion`: los pasos sueltos no son `check.ps1`; el código
  de salida se lee del registro, no del envoltorio (entradas 140, 142; deuda
  25, con `git diff --check` sin argumentos en la plantilla).
- En `medir-con-linea-base`: predecir el mecanismo y contar las consultas que
  activan una palanca antes de predecir la cifra (10); el jitter ±2 (114);
  comprobar que no hay una cifra más reciente en el mismo documento (116);
  predecir una invariante cuando no hay línea base (83); leer el veredicto ítem
  a ítem (66).

**Del propietario:** D-1…D-5 (deudas 38, 39, 40, 42/43, 44), B04 en `main` o
no (entrada 121; decisión D1), la opción 4 de ADR-150 (`check.ps1` como paso
determinista del workflow; deuda 8), el vigía barato (deuda 5), persistir el
rechazo de una propuesta de criticidad (deuda 6) y **la cadena del contador de
los siete días** (deuda 13, C2 de ADR-101): `CLASES_CON_ESTADO_PROPIO` sigue
vacío y `seven_day_streak_cli.py:66` dice que eso bloquea D1, pero el
propietario decidió el 13-09 que esa línea **no es necesaria**: la fuente es su
comentario en la incidencia #610 (13-09-2026, 13:25 UTC, «Cancelado por el
propietario, a los dos minutos de despacharse… la línea del contador de los
siete días **no es necesaria**»), que cerró el encargo como `not_planned` antes
de que produjera rama ni PR. Ningún ADR lo recoge y ADR-101 sigue teniendo C2
como bloque: la decisión está tomada y sin registrar (familia
`decision-que-solo-vive-en-una-conversacion`). El agente del triaje la dio por
`parcial`; aquí se corrige a decisión tomada, y la propuesta 11 pide el ADR que
la deje escrita.

## 7. Familias de defecto del mes

- **F1 — La ficha afirma algo que su propio árbol deja de sostener.** Sigue
  primera: 8 de 30 incidencias en la primera quincena, el aviso de #653 en la
  segunda (§4.1) y 37 de los 41 hallazgos de las PR de sesión (§5). Es la
  familia que ADR-135 intentó cortar con el prompt del corrector el 04-09; a
  final de mes sigue siendo la dominante en los dos cauces. **Este dato
  responde a la propuesta 5 de la edición anterior: F1 no cedió.**
- **F2 — La corrección de una ronda abre el siguiente hueco del mismo
  mecanismo.** Son F2 las familias que §4 da por reales: los 9 casos avisados
  (§4.1, 9 ACERTADO) y los 9 tramos sin aviso de §4.3 que no son el falso
  positivo #566 (seis validados por la edición del 14-09 y tres en la tabla
  de §4.3). En incidencias, 13 de las 14 que el detector marca (#566 fuera):
  12 en la primera quincena, #653 en la segunda. Marcar tres rondas sobre el
  mismo fichero no demuestra por sí solo que cada corrección abriera el
  siguiente hueco; lo demuestra la clasificación caso a caso.
- **F5 — Afirmar lo que hace un mecanismo sin ejecutarlo ni leer su regla de
  rechazo.** Nueva como nombre, no como hecho: la bitácora la cuenta desde el
  08-09 (entradas 54, 59, 80, 83, 98: «premisas falsas escritas de memoria»)
  y ADR-216 la repitió el 24-09 dos veces sobre el reflector. Es la variante
  de F1 que ocurre antes de escribir la ficha: la afirmación nace falsa, no se
  queda falsa.
- **F6 — La salvaguarda escrita en prosa.** Tres defectos en dos rondas sobre
  el lote de ADR-216 y un cuarto que ninguna ronda vio; antes, en la bitácora,
  el `vigila_653.sh` que nunca leía la PR (entrada 140) y el `continua` que
  anuncia en verde lo que va a rechazarse (entrada 126). La regla existe; lo
  que falta es que esté en el código que se ejecuta.
- F3 (el texto que el motor publica describe mal lo que hace) y F4 (pieza
  correcta sin el llamante que la necesita) siguen con los mismos casos de la
  edición anterior más uno cada una: deuda 47 para F3 (el aviso que pide
  «fusiona») y `CLASES_CON_ESTADO_PROPIO` vacío para F4.

## 8. Guardianes mecánicos: aciertos y falsos medidos

Mismo criterio de entrada que las ediciones anteriores y que la incidencia
#267: entra lo que caza más defectos reales que falsos positivos.

| Guardián | Aciertos reales | Falsos | Evidencia |
|---|---|---|---|
| El detector de familia repetida ya arreglado (14-09) | +9 familias reales sin aviso en su día (#523, #545, #570 ×2, #574, #581 ×2, #599, #601; seis validadas el 14-09 y tres en la tabla de §4.3) y 13/13 avisos reproducidos | 1 (#566, por el criterio de la edición anterior) | §4.2, §4.3. Neto **+8**, medido tramo a tramo sobre el mes |
| Comprobar `Perfil: rol@N` en `validate_issue_body.py` | 1 ciclo muerto a los 6 s (#653) y los encargos lanzados con `@2` no vigente | 0 por construcción: solo rechaza lo que el workflow iba a rechazar después | entradas 123, 124, 138; deudas 34, 35 |
| Regenerar `MEMORIA.md` en la cola antes de empujar la combinación | 1 vuelta del corrector (25 min) en #653 | 0 | entrada 146; deuda 48 |
| El guardián de goteo tal como está | 37 marcas en 15 incidencias | no medido: haría falta verificar cada marca contra el diff, el método de agosto | §3 |
| Que la marca del guardián sobreviva en el JSON | medición futura posible | 0 | §3; `sirius_apply_verdict.sh:716-784` |

\* #566 cuenta como acierto del detector (tramo 1-3 sobre el mismo fichero) y
como falso por el criterio de familia de la edición anterior; se publica en
las dos columnas a propósito.

## 9. Huecos declarados

- **La segunda quincena del ciclo del motor son dos incidencias.** Cualquier
  cifra de esa quincena sobre el motor describe dos casos, y así se ha escrito.
- **Las dos poblaciones no se suman.** Las rondas del motor agregan a los dos
  revisores; las de las PR son solo Codex. Se publican lado a lado y no se
  mezclan.
- **La clasificación de las 146 entradas la hicieron agentes.** El muestreo
  propio midió 14 de 15 confirmadas; la lista se publica con esa cifra al
  lado, no como verdad.
- **Las entradas 147 en adelante no existen.** La bitácora se detuvo el 21-09;
  lo que pasó del 22 al 30 (ADR-204 a ADR-217, las cinco PR de sesión) está
  medido en §5 y escrito en los ADR, no en la bitácora. Añadirlo a la bitácora
  es trabajo de quien la retome, con la forma de siempre.
- **El goteo de CODEX no se puede medir con este instrumento** (§3): 2,7 % de
  sus citas llevan línea.

## 10. Propuestas, ordenadas por lo que cazan menos lo que cuestan

Ninguna se implementa en este documento. Cada una lleva cómo se mide antes y
después, que es la condición que el propietario puso el 01-10: «mejoras
reales, nada de fusiones a lo tonto».

1. **El validador de encargos comprueba `Perfil: rol@N`** (existencia,
   pertenencia al carril del manifiesto y aviso si la versión no es la
   vigente). Medida: un cuerpo sin `Perfil` se rechaza al escribirlo (prueba
   que hoy falla y después pasa); 0 falsos por construcción.
2. **La cola regenera `MEMORIA.md` antes de empujar la combinación** y el
   aviso de `ready-for-merge` dice lo que el motor hace desde ADR-205. Medida:
   la guarda que lee el workflow y el texto; el caso de #653 (25 min) deja de
   poder repetirse.
3. **`continua` sobre una parada anterior a la PR**: comprobar `planned`, no
   anunciar en verde lo que se rechazará, no consumir la parada; y un
   `continua` malformado que diga por qué no actúa. Medida: las pruebas de
   `tests/automation/test_reanudar_una_parada.py` con el caso de la entrada
   126, que hoy no existe.
4. **Las divergencias que el reflector aparta a propósito, visibles en
   `DESENLACES.md` con su edad.** Es el mecanismo que H-216 no tiene: el diseño
   dice «esto lo mira un humano» y nada se lo pone delante. Medida: hoy 0
   sitios lo muestran; después, la vista lista `WI-20260828-122242` con sus
   días.
5. **El comparador de instantes de G8 tipado o con forma canónica** (deuda
   20). Medida: una prueba con `Z` y `+00:00` mezclados que hoy ordena mal.
6. **`printf -- '- PR: %s\n'`** en `sirius_apply_verdict.sh:850`. Medida: el
   fallo reproducido hoy deja de reproducirse. Es una línea; va con la 2.
7. **Que `cerrado_por` sea una referencia que se pueda seguir desde
   `main`** (la PR que lo cerró, que el aplastado lleva en el título, o el
   commit de `main` resultante), y la guarda que lo compruebe con `git`.
   Medida: hoy 29 de 68 defectos cerrados citan un commit que `main` no
   contiene (los 14 cerrados desde el 20-09, todos), según
   `scripts/mina/cerrado_por_inalcanzable.py`; después, 0.
8. **Una skill de encargos** con las cinco lecciones de la bitácora y las
   cuatro preguntas de auditoría previa (entradas 26, 31, 37, 39, 41, 51, 54,
   67, 78), más las líneas que faltan en `cadena-de-comprobacion` y
   `medir-con-linea-base` (§6.4). Medida: no mecánica; se medirá en la mina de
   octubre por rondas que ya no ocurren.
9. **El reloj del implementador** (deuda 30) y **leer la cuota de Codex antes
   de disparar** (deudas 12, 16). Medida: las muertes silenciosas de las
   entradas 92 y 94 y las rondas tiradas de la 106 dejan de serlo.
10. **Las decisiones del propietario** D-1…D-5, que mueven el banco de 29/47 a
    36/47 según cómo se resuelva D-1 y que ningún encargo puede tomar por él.
11. **Un ADR que recoja la cancelación de C2** (#610, 13-09) y supere esa parte
    de ADR-101, para que `seven_day_streak_cli.py:66` y el bloque dejen de
    decir que algo bloquea D1 cuando el propietario ya dijo que no hace falta.
    Medida: hoy la decisión vive en un comentario; después, en el registro.
