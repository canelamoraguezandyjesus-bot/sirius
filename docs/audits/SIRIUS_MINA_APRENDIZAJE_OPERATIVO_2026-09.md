# La mina, segunda edición: cuánta razón tiene el detector de familia repetida

- Fecha: 2026-09-14
- Ventana medida: del 01-09-2026 al 14-09-2026, ambos inclusive
- Incidencia: #627 (Work ID WI-20260914-073945)
- Alcance: solo lectura de la API de GitHub sobre este mismo repositorio
  (`canelamoraguezandyjesus-bot/sirius`); ningún cambio de comportamiento en
  código, workflows ni prompts
- Primera edición (plantilla de método y estructura):
  `docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md`
- Autor: documentalista genérico de Sirius (encargo autónomo)

> **Aviso de colisión de ruta, que hay que leer antes que nada.** Este
> documento ocupa una ruta que tres ADR ya citaban para referirse a **otro**
> informe: la «mina v2» del 04-09-2026, que vive en la rama
> `claude/adr002-tol209-forensic-audit-i0ui8k` y que a propósito nunca se
> fusiona entera a `main`. La citan
> `docs/decisions/ADR-132-el-guardian-del-contrato-local-de-ollama-convierte-adr-125-en-prueba-y-corrige-ollama-category-classifier.md:7-10`
> («la propuesta 1 de … sección 8»),
> `docs/decisions/ADR-134-el-guardian-del-suelo-de-prueba-muerto-retira-las-dos-cotas-tautologicas-del-banco-de-evidencia.md:7-10`
> y
> `docs/decisions/ADR-135-el-corrector-actualiza-en-el-mismo-commit-el-papel-que-depende-de-su-correccion.md:40-42`
> («§4»). Sus §4 y §8 no son los de este documento. El objetivo de la
> incidencia #627 fija esta ruta literalmente, así que aquí se escribe donde
> se pidió y la colisión se declara en vez de resolverse: **quién decide qué
> se hace con esas tres citas es el propietario**, no este informe (§7, hueco
> primero).

## Nota de método (antes de los resultados)

Cinco decisiones se tomaron antes de mirar las cifras finales, siguiendo la
disciplina de evidencia de ADR-001. Las tres primeras replican las de la
primera edición; la cuarta y la quinta son propias de esta.

1. **Dónde vive el dato y dónde vive el análisis.** El dato vive en los
   comentarios de las incidencias de GitHub (bloques `RONDA_HALLAZGOS` y
   `OBSERVACIONES_ESTRUCTURADAS`, avisos `AVISO_FAMILIA_REPETIDA`, marcas
   `⚠️ Guardián de goteo:`) y en `docs/decisions/ADR-*.md`; el análisis vive
   únicamente en este documento nuevo.
2. **Qué NO garantiza este informe.** No es una auditoría exhaustiva del
   repositorio ni de septiembre entero: mide las **30 incidencias** que
   publicaron al menos un registro de ronda dentro de la ventana, y solo las
   rondas publicadas dentro de ella. No verifica de forma independiente
   ninguna de las declaraciones de goteo de §3 —las cuenta, que es otra
   cosa—. No implementa, no cablea, no decide y no da de alta ningún defecto.
   Ninguna de las propuestas de §8 se toca aquí.
3. **Criterio de pertenencia a la ventana, decidido antes de contar nada:**
   una incidencia entra si alguno de sus marcadores `<!-- sirius-round:N -->`
   fue publicado por un autor de confianza (`OWNER` o `github-actions[bot]`)
   entre el `2026-09-01T00:00:00Z` y el `2026-09-14T23:59:59Z`; y una ronda
   entra en las cifras si el comentario que la publicó cae en ese intervalo.
   Se elige la fecha de **publicación de la ronda**, no la de creación de la
   incidencia, porque lo que se mide es actividad de revisión de septiembre,
   no incidencias nacidas en septiembre.
4. **Criterio de clasificación de los avisos del detector (§4), escrito
   ANTES de clasificar ninguno.** Se reproduce literal, porque es la pieza
   que sostiene la respuesta a la pregunta de esta edición:

   > Un aviso nombra un par (archivo A, tramo de rondas consecutivas
   > r..r+k).
   >
   > - **ACERTADO**: leyendo el campo `problema` de las
   >   `OBSERVACIONES_ESTRUCTURADAS` sobre A en al menos dos rondas del
   >   tramo, esas observaciones son la misma familia: comparten el
   >   mecanismo de fondo (misma función, mismo invariante o mismo
   >   acoplamiento) de forma que la corrección de una ronda no cerró el
   >   problema sino que dejó otra variante del mismo problema abierta
   >   —incluida la variante que esa misma corrección introdujo—. Es el
   >   criterio con el que ADR-078 verificó a mano sus 4 aciertos.
   > - **FALSO**: las observaciones sobre A en el tramo son defectos
   >   independientes que solo comparten el fichero: distinta función o
   >   sección, distinto invariante, sin relación causal entre la corrección
   >   de una ronda y el hallazgo de la siguiente.
   > - **INDETERMINADO**: las observaciones publicadas no bastan para
   >   decidir.
   > - **Ante duda razonable se clasifica FALSO.** La pregunta que motiva el
   >   informe es si el detector merece autoridad para detener un ciclo; en
   >   esa dirección el error caro es sobrestimar su acierto.
   >
   > Para los avisos **no** emitidos (falsos negativos), el patrón de
   > referencia es la misma familia de defecto recurriendo en 3 o más rondas
   > consecutivas, **independientemente de cómo esté escrito el campo
   > `archivo`**. Los casos con solo 2 rondas consecutivas NO cuentan como
   > falso negativo: el umbral de 3 es una decisión ya medida (ADR-078), no
   > un fallo de implementación —ADR-078 declara exactamente esto para la
   > incidencia #268—.

5. **Criterio de parada, escrito antes de ver cuántos avisos había:** si el
   número de avisos emitidos en la ventana es **menor que 10**, la tasa
   resultante se declara *demasiado pequeña para sostener una tasa* con esas
   palabras, se da el número, y no se publica ningún porcentaje como si fuera
   una tasa estable. Se disparó: ver §4.3.

**Qué haría el fallo imposible, no solo improbable.** No aplica de forma
directa: este informe no corrige nada. Lo más cercano es §4.4, que sí nombra
la línea exacta cuyo comportamiento explica todos los falsos negativos
medidos —`src/sirius_engine/round_history.py:79`— y §8, que se detiene antes
de tocarla.

Fuentes leídas: `gh issue list --state all` sobre
`canelamoraguezandyjesus-bot/sirius` (206 incidencias visibles; 125 con
actividad desde el 25-08-2026, que son las que se descargaron enteras), los
comentarios de autor de confianza de esas 125
(`gh api repos/.../issues/N/comments --paginate`, filtrando
`author_association=="OWNER"` o `user.login=="github-actions[bot]"`, el mismo
filtro que `scripts/automation/sirius_issue.sh:337-354` usa en producción),
`src/sirius_engine/round_history.py`, `src/sirius_engine/round_family_detector.py`,
`src/sirius_engine/drip_guard.py`, `scripts/automation/sirius_apply_verdict.sh`,
`AGENTS.md` y los ADR citados. El detector se ejecutó con su propio CLI
instalado, `uv run sirius-familia-repetida`, sin reimplementar nada.

Comando reproducible del volcado (con `GH_TOKEN` exportado):

```bash
gh issue list --repo canelamoraguezandyjesus-bot/sirius --state all --limit 1000 \
  --json number,title,createdAt,updatedAt,state,url
# para cada número candidato N:
gh api "repos/canelamoraguezandyjesus-bot/sirius/issues/$N/comments" --paginate
# los cuerpos de confianza, del más antiguo al más reciente, a un fichero por
# incidencia; sobre ese fichero:
uv run sirius-familia-repetida --historial historial_$N.txt
```

## 1. Distribución de hallazgos por fuente, gravedad y tipo de fichero

Datos: los **301 hallazgos** publicados en los bloques `RONDA_HALLAZGOS` de
las **122 rondas** que las 30 incidencias de la ventana publicaron dentro de
ella.

### 1.1 Por fuente

| Fuente | Hallazgos | % |
|---|---|---|
| CLAUDE | 195 | 64.8% |
| CODEX | 106 | 35.2% |
| **Total** | **301** | 100% |

**El reparto se ha dado la vuelta.** En agosto CODEX firmaba el 71.3% de los
324 hallazgos y CLAUDE el 28.7%
(`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md:99-105`); en
septiembre es CLAUDE quien firma el 64.8%. Este informe **no explica** el
vuelco: no distingue si CLAUDE reporta más, si CODEX reporta menos, o si la
mezcla de trabajo de septiembre (más documentación de ADR, ver §1.3) favorece
al revisor que más citas de prosa levanta. Es un dato, no una conclusión.

### 1.2 Por gravedad (dentro de cada fuente, porque usan escalas distintas)

| Fuente | Gravedad | Hallazgos |
|---|---|---|
| CLAUDE | baja | 72 |
| CLAUDE | media | 57 |
| CLAUDE | alta | 14 |
| CLAUDE | menor | 14 |
| CLAUDE | p3 | 14 |
| CLAUDE | p2 | 11 |
| CLAUDE | p1 | 8 |
| CLAUDE | mayor | 2 |
| CLAUDE | media-baja | 2 |
| CLAUDE | moderada | 1 |
| CODEX | p2 | 71 |
| CODEX | p1 | 26 |
| CODEX | p3 | 9 |

La taxonomía de CLAUDE sigue sin normalizar y en septiembre ha crecido: a las
palabras que ya usaba en agosto (`alta`, `media`, `baja`, `menor`) se suman
`mayor`, `media-baja` y `moderada`, ninguna de las cuales está en
`SEVERITY_WEIGHTS` (`src/sirius_engine/round_history.py:55-68`), así que las
tres pesan como `DEFAULT_SEVERITY_WEIGHT = 2` al medir progreso. CODEX se
mantiene íntegramente en P1–P3.

### 1.3 Por tipo de fichero

Extensión de la ruta que encabeza el campo `archivo` del hallazgo, extraída
con `sirius_engine.drip_guard.parse_archivo_location`
(`src/sirius_engine/drip_guard.py:127`) —reutilizada, no reescrita— porque el
campo trae con frecuencia prosa detrás de la ruta.

| Extensión | Hallazgos | % |
|---|---|---|
| `.py` | 168 | 55.8% |
| `.md` | 111 | 36.9% |
| `.sh` | 13 | 4.3% |
| (sin extensión) | 6 | 2.0% |
| `.yml` | 3 | 1.0% |

En agosto documentación y código empataban (157 `.md` frente a 156 `.py`); en
septiembre el código se despega. Aun así, **más de un tercio de todo lo que
la revisión encuentra sigue siendo texto**, y §5 muestra que es ahí donde
vive la familia dominante del mes.

## 2. Rondas por incidencia

Datos: las mismas 30 incidencias, contando solo las rondas publicadas dentro
de la ventana.

- Media: **4.07 rondas** por incidencia.
- Mediana: **4 rondas**.
- Distribución (rondas → nº de incidencias): 1→4, 2→3, 3→7, 4→10, 5→3, 7→1,
  14→1, 15→1.
- Con **más de una** ronda en la ventana: **26 de 30**.

Las 5 peores, con su coste en ciclos:

| Incidencia | Rondas en la ventana |
|---|---|
| #545 | 15 |
| #581 | 14 |
| #574 | 7 |
| #508 | 5 |
| #529 | 5 |

La media de agosto era 2.93 y la mediana 2, medidas sobre todas las rondas
jamás publicadas de 55 incidencias
(`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md:159-162`). Las dos
poblaciones no son comparables directamente —aquella cubría toda la historia,
esta una ventana de catorce días— así que el salto de 2.93 a 4.07 **no se
afirma como un empeoramiento**: se publica junto a su base para que una
tercera edición, ya con dos ventanas del mismo tipo, pueda comparar de verdad.

## 3. Goteo: lo que el guardián marca y lo que el revisor declara

En agosto la tasa de goteo se midió a mano, clasificando 89 hallazgos con la
API de comparación de GitHub. En septiembre hay dos fuentes nuevas que en
agosto no existían, y este informe las cuenta en vez de repetir aquel
trabajo:

1. **El guardián de goteo en vivo** (ADR-123, cableado en
   `scripts/automation/sirius_apply_verdict.sh:764-782`), que anota cada
   observación cuyo fichero y línea ya estaban idénticos en la ronda 1.
2. **La declaración del propio revisor**, que `AGENTS.md:98-101` exige:
   «un hallazgo sobre líneas ya idénticas en la ronda previa se reporta
   igualmente, declarando que llega tarde por goteo del revisor».

Base: los **203 hallazgos de ronda N>1** publicados en la ventana (CLAUDE
133, CODEX 70).

### 3.1 Lo que el revisor declara

| Fuente | Hallazgos N>1 | Se declaran goteo | % |
|---|---|---|---|
| CLAUDE | 133 | 56 | **42.1%** |
| CODEX | 70 | 1 | **1.4%** |
| **Total** | **203** | **57** | 28.1% |

Otros 6 hallazgos nombran el goteo **para negarlo** («no es goteo del
revisor: el corrector lo dejó expresamente sin corregir», #545 rondas 3 y 4;
«no visible en la ronda anterior», #523 ronda 2) y no se cuentan; uno más
(#501 ronda 6) habla del guardián, no de sí mismo, y tampoco se cuenta.

La forma coincide con agosto —CLAUDE gotea mucho más que CODEX— pero **el
instrumento es distinto y hay que decirlo**: agosto verificaba cada hallazgo
contra el diff real; septiembre cuenta autodeclaraciones. Por eso la cifra de
CLAUDE es un **suelo** (solo cuenta lo que el revisor admitió) y la de CODEX
**no mide casi nada**: CODEX no sigue el convenio de declaración de
`AGENTS.md:98-101`, así que su 1.4% dice más sobre su formato de salida que
sobre su disciplina. Los dos números no son comparables entre sí.

### 3.2 Lo que el guardián marca

El guardián marcó **37 observaciones** en 15 incidencias de la ventana
(#508, #545, #570, #574, #577, #579, #581, #582, #592, #594, #597, #599,
#601, #612, #615). **Las 37 son de CLAUDE; ninguna de CODEX.** No es una
sorpresa: el guardián solo puede evaluar un hallazgo que cite fichero **y**
línea de forma que `parse_archivo_location` la reconozca
(`src/sirius_engine/drip_guard.py:127`), y CODEX cita la ruta desnuda, sin
línea, en la práctica totalidad de sus hallazgos (§4.4 muestra el mismo
efecto sobre el detector de familia).

Cruce de las dos señales, sobre las 37 marcas:

| | Hallazgos |
|---|---|
| Marcados por el guardián **y** declarados por el revisor | 18 (48.6% de las marcas) |
| Marcados por el guardián **sin** declaración del revisor | 19 |
| Declarados por el revisor **sin** marca del guardián | 39 |

Esto es **concordancia entre dos señales, no precisión**: ninguna de las dos
es la verdad. Una marca sin declaración puede ser un falso positivo del
guardián (la línea citada es contexto sin tocar dentro de un hunk modificado,
la limitación que ADR-123 declara en el docstring del módulo,
`src/sirius_engine/drip_guard.py:18-28`) o un goteo que el revisor no
reconoció. Una declaración sin marca es, casi siempre, un hallazgo cuya cita
el guardián no puede resolver. Verificar cada uno contra el diff —el método
de agosto— queda fuera del presupuesto de esta edición y se declara como
hueco (§7).

### 3.3 Un dato de forma que conviene no perder

La marca del guardián **solo sobrevive en la prosa**. `sirius_apply_verdict.sh`
publica el bloque `## OBSERVACIONES_ESTRUCTURADAS` con `$observations`, la
lista **sin anotar**, mientras que la anotada (`$readable_observations`) solo
se usa para renderizar las viñetas legibles
(`scripts/automation/sirius_apply_verdict.sh:781-784` y `:835`). Consecuencia
medida: de los 203 hallazgos de ronda N>1 de la ventana, **cero** traen la
clave `posible_goteo` en el JSON publicado, pese a las 37 marcas visibles en
el texto. Cualquier medición futura del guardián tendrá que leer la prosa,
como ha hecho esta. Se declara como observación; **no se propone ni se
implementa nada** (§8 lo recoge como candidata para un encargo aparte).

## 4. La pregunta de esta edición: cuánta razón tiene el detector de familia repetida

Hoy `sirius-familia-repetida` (ADR-078, cableado por ADR-121) **solo avisa**:
`scripts/automation/sirius_apply_verdict.sh:799-819` añade una sección
`## AVISO_FAMILIA_REPETIDA` al comentario de `CHANGES_REQUESTED` y nada más
—«no bloquea ni cambia esta transición» (`:837`)—. Está pendiente decidir si
se le da autoridad para detener un ciclo. Esa decisión necesita su tasa de
acierto sobre datos reales, y la primera edición de la mina no pudo darla:
se limitó a reutilizar la medición de ADR-078 (4 aciertos, 0 falsos sobre 14
incidencias de agosto) y lo declaró como hueco
(`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md:458-462`). Esta
sección la mide.

### 4.1 Qué se ejecutó, exactamente

Sobre las **26 incidencias de la ventana con más de una ronda** (§2) se
ejecutó el CLI real del detector sobre el historial real de cada una:

```bash
uv run sirius-familia-repetida --historial historial_<N>.txt --salida familia_<N>.json
```

El CLI corta el historial por la última orden de continuar
(`history_after_last_resume`) antes de analizarlo, igual que en producción
(`src/sirius_engine/round_family_detector_cli.py:61-62`), así que lo que ve
es exactamente lo que vería el ciclo.

Además se recogieron los avisos **realmente publicados** en septiembre,
buscando el bloque `## AVISO_FAMILIA_REPETIDA` en los comentarios de
confianza. Las dos lecturas no coinciden, y la diferencia es en sí un
resultado: hoy el detector solo avisa en 4 de las 7 incidencias en las que
avisó durante el mes (#520, #526, #539, #597), porque #529, #545 y #581
publicaron después una orden de continuar que reinició su historial vigente.
**El aviso de producción es el dato bueno** —es el que el ciclo vio, cuando
lo vio— y es el que se clasifica.

### 4.2 Los avisos emitidos en septiembre

**11 comentarios** con `AVISO_FAMILIA_REPETIDA`, que nombran **8 casos**
distintos (incidencia, archivo) en **7 incidencias**. Los 11 comentarios son
solo 8 casos porque el detector vuelve a avisar del mismo tramo cuando este
crece (#520 avisó en las rondas 3 y 4 del mismo fichero; ídem #526, #581,
#597).

| # | Incidencia | Archivo señalado | Tramo | Veredicto | Evidencia |
|---|---|---|---|---|---|
| 1 | #520 | `src/sirius/presentation/knowledge_widget.py` | rondas 1-3 y 1-4 | **ACERTADO** | Cadena completa sobre el acoplamiento `CriticalityProposalWorker` ↔ estado «ocupado externo»: r1 `CODEX-001` (el worker arranca con `set_external_busy(True)`), r2 `CODEX-001` (el retorno nuevo descarta la solicitud y nadie la reanuda), r3 `CODEX-001` (el bucle de reanudación que corrigió r2 arranca workers en rutas terminales), r4 `CODEX-001`/`-002` (la opción `resume_proposals=False` que corrigió r3 no cubre cierre ni copia/exportación). Cada corrección abre el siguiente hueco del mismo mecanismo. |
| 2 | #526 | `docs/decisions/ADR-134-…-banco-de-evidencia.md` | rondas 1-3 y 1-4 | **ACERTADO** | Dos eslabones de la misma familia («la evidencia que el ADR cita no sostiene lo que afirma»): r1 `CODEX-001` (la nota de arranque se declara previa y el comando citado demuestra lo contrario) → r2 `CODEX-001` (el comando que corrigió r1 usa una ruta abreviada y sigue sin demostrar la cronología); r3 `CLAUDE-OBS-1` (la cifra de pytest del ADR no cuadra con la de la PR) → r4 `CLAUDE-REVISOR-001` (al fijar la cifra queda expuesto que la duración adjunta nunca se actualizó). |
| 3 | #529 | `src/sirius_engine/reflect.py` | rondas 1-3 | **ACERTADO** | La reactivación de un `WorkItem` detenido desde el espejo, tres rondas seguidas: r1 `CODEX-002` (la rama rechaza el espejo `ACTIVE` si el motor quedó en `NEEDS_DECISION`/`FAILED_SAFELY`), r2 `CODEX-001` (el bloque nuevo nunca se alcanza y la rama `DELIVERED` sigue rechazando), r3 `CODEX-001` (la condición que corrigió r2 ahora interpreta cualquier estado distinto como autorización). |
| 4 | #539 | `src/sirius_engine/reflect.py` | rondas 1-3 | **ACERTADO** | Lo dice el propio revisor en la ronda 3, textualmente: «Es, por tanto, la TERCERA aparicion de la misma familia de defecto (ronda 1: CLAUDE-REV-001; ronda 2: CLAUDE-R2-001…)» — medir la coincidencia con la foto en vez del salto, en `_objetivos_acreditados` y su sucesora `_salida_de_parada_acreditada`. |
| 5 | #545 | `src/sirius_engine/mirror_projection.py` | rondas 1-3 | **ACERTADO** | r1 `CODEX-001` (el orden de publicación se usa como orden de estados), r2 `CODEX-001` (`_diagnostico_hasta` atribuye a una parada el diagnóstico que no es suyo), r3 `CLAUDE-R4-002` («El defecto de base sigue vivo: `_diagnostico_hasta` … atribuye a cada marcador de parada el ultimo diagnostico publicado ANTES»). |
| 6 | #545 | `src/sirius_engine/reflect.py` | rondas 1-3 | **ACERTADO** | El anclaje del recorrido acreditado: r1 `CODEX-002` (asignar siempre la última coincidencia no demuestra que sea la ocurrencia almacenada), r2 `CODEX-002` (el fallback elige el marcador de la primera parada aunque su diagnóstico contradiga al guardado), r3 `CLAUDE-R4-001` (el corrector declara sin corregir los dos anteriores y la revisión los vuelve a levantar sobre el mismo fichero). |
| 7 | #581 | `docs/decisions/ADR-177-…-la-subcadena-contexto.md` | rondas 1-3 y 1-4 | **ACERTADO** | El revisor lo nombra dos veces: r2 `CLAUDE-H4R2-001` («es de la MISMA FAMILIA que CLAUDE-H4-002 —un desglose que no sumaba— y CLAUDE-H4-003 —cifras traídas del cuerpo de la incidencia sin re-medir—») y r3 `CLAUDE-H4R3-003` («es la MISMA familia que CLAUDE-H4-005»). |
| 8 | #597 | `docs/decisions/ADR-182-…-que-declaran-leccion.md` | rondas 1-3 (dos veces) | **ACERTADO** | La tabla de mutaciones del propio ADR, tres rondas seguidas: r1 `CLAUDE-REV-597-002` (dos afirmaciones que el código no sostiene, fila M8), r2 `CLAUDE-REV-597-003` (al añadir la fila M9 se actualizó el encabezado pero no el recuento), r3 `CLAUDE-REV-597-004` («REGRESION DE LA CORRECCION DE LA RONDA ANTERIOR») y `-006` (la aritmética de M8 sigue sin cuadrar). |

**8 casos, 8 ACERTADO, 0 FALSO, 0 INDETERMINADO.** Ninguno necesitó la
cláusula de duda razonable: en cinco de los ocho (#526, #539, #545 ×1, #581,
#597) la propia revisión escribe la relación con la ronda anterior, y en los
tres restantes la cadena corrección → hueco siguiente del mismo mecanismo
está en el texto de los hallazgos.

### 4.3 Y aquí es donde el criterio de parada muerde

**El número de casos es demasiado pequeño para sostener una tasa: son ocho.**
Ocho casos, en siete incidencias, en catorce días. Que los ocho hayan
resultado acertados es un resultado real y es información —el detector no
falló ni una vez en septiembre— pero **no es una tasa de acierto**: con ocho
observaciones y cero fallos, cualquier porcentaje que se publique («100%»)
proyecta una confianza que los datos no tienen. Sumando la medición de
ADR-078 (4 aciertos, 0 falsos sobre las 14 incidencias multi-ronda de
agosto,
`docs/decisions/ADR-078-tres-rondas-consecutivas-sobre-el-mismo-archivo-son-la-familia-repetida-medido-antes-de-fijarlo.md:94-105`)
el acumulado son **12 aciertos y 0 falsos positivos conocidos**, sobre dos
mediciones independientes y dos poblaciones distintas. Eso es lo que hay, y
lo que hay se dice entero: doce casos siguen siendo doce casos.

### 4.4 Cuántas veces NO avisó y debería haber avisado

Aquí está el resultado incómodo, y es mucho más grande que el anterior.

Método, decidido con el criterio (B) de la nota de método: sobre las mismas
26 incidencias se recalculó el tramo consecutivo por fichero usando, en vez
del campo `archivo` tal cual, **la ruta que lo encabeza**, extraída con
`parse_archivo_location`. Cada tramo de 3+ rondas que aparece con la ruta y
no con el campo crudo es un candidato a falso negativo; cada candidato se
clasificó leyendo el texto de sus hallazgos con el mismo criterio de familia.

| Incidencia | Ruta real | Tramo | ¿Familia real? | Evidencia |
|---|---|---|---|---|
| #570 | `src/sirius/adapters/ollama_query_intent_classifier.py` | 1-3 | **Sí** | r1 `CLAUDE-R1-001` (la fecha declarada no se normaliza) → r2 `CLAUDE-R2-001`/`CODEX-001`/`-002` (la normalización que corrige r1 rompe la comparabilidad con los ejes de G8 y pierde el día declarado) → r3 `CLAUDE-R3-003` (la corrección de r2 descarta el desfase declarado por completo). |
| #570 | `docs/decisions/ADR-164-…-la-politica-uniforme-de-hoy.md` | 2-4 | **Sí** | r2 `CLAUDE-R2-002` (la sección de validación sigue anclada a los árboles de la ronda 1) → r3 `CLAUDE-R3-001` (la reescritura que la corrige deja intacto el párrafo contiguo) → r4 `CLAUDE-R4-001` (los dos guardianes nuevos vuelven a dejarla desfasada). |
| #574 | `docs/decisions/ADR-166-…-que-el-corpus-declara.md` | 1-7 | **Sí** | r1 `CLAUDE-REV-575-001` (el ADR no declara la limitación que el propietario pidió) → r2 `CLAUDE-REV2-575-001`/`-002` (el párrafo que la corrección añade es él mismo falso, y el re-anclaje es una regresión) → r3 (dos goteos sobre la misma elección y su justificación escrita) → r4 `CLAUDE-REV4-575-001`/`-002` (texto nuevo de la corrección de r3, otra vez incorrecto). |
| #599 | `scripts/automation/sirius_apply_verdict.sh` | 1-4 | **Sí** | r1 `CLAUDE-REV-600-002` (el aviso de la fase nueva afirma dos cosas falsas) → r2 `CLAUDE-REV-600-R2-001`/`-002` (la reescritura a `case` fija `run_line` pero hereda el `desbloquea` genérico, y su comentario nuevo dice «dos fases» donde hay cuatro) → r3 `CLAUDE-REV-600-R3-001`/`-002` (el mismo comentario publicado afirma dos cosas incompatibles) → r4 (el commit que reescribe los `::error::` deja otra afirmación sin sostén). |
| #523 | `docs/decisions/ADR-133-…-los-revisores-las-escriben-de-verdad.md` | 2-4 | **Sí** | r2 `CLAUDE-ADR133-001` (tras la corrección, el ADR deja de describir fielmente el código que documenta) → r3 `CODEX-001` (el recuento de la suite queda desfasado) → r4 `CODEX-001` (vuelve a quedar desfasado tras el merge). La misma familia: la afirmación del ADR que su propio árbol deja de sostener. |
| #601 | `src/sirius_engine/intent_interpreter.py` | 1-3 | **Sí, el más débil** | r1 `CLAUDE-R-001`/`CODEX-002` (los negadores de `_va_negado` no gobiernan de verdad el marcador) → r2 `CLAUDE-R2-001`/`-002`, `CODEX-002`/`-003` (la corrección añade `duda` y `falta` a `_CORTES_DE_ORACION` y con eso rompe la salvaguarda habitual) → r3 `CLAUDE-REV4-002` (regresión de esa corrección, sobre el mismo bloque de constantes). El eslabón de r3 es un defecto de documentación del mismo bloque, no el mismo defecto semántico: se cuenta, y se declara como el más discutible de los seis. |
| #566 | `docs/decisions/ADR-162-…-en-cuanto-aparece-el-texto.md` | 1-3 | **No** | La familia real («afirmaciones falsas sobre ADR-153») ocupa las rondas 1 y 2, no tres: el hallazgo de la ronda 3 es un goteo declarado sobre otra sección (validaciones obligatorias). Dos rondas consecutivas no son familia repetida por el criterio ya medido de ADR-078. |
| #579 | `docs/decisions/ADR-169-…-que-la-peticion-declara.md` | 2-4 | **No** | Los tres hallazgos de la ronda 3 (`CODEX-001`/`-002`/`-003`) sí son una familia entre sí —la evidencia de validación no se sostiene— pero ocupan **una sola** ronda; los de las rondas 2 y 4 son goteos declarados sobre secciones distintas y sin relación causal. Defectos independientes que comparten fichero. |

**Resultado: 6 falsos negativos confirmados, en 5 incidencias** (#523, #570
×2, #574, #599, #601) — cinco de ellos sin la menor duda y el sexto (#601)
declarado como el más débil. Frente a 8 avisos acertados, el detector **dejó
pasar casi tantas familias repetidas como las que señaló**.

**Y todas por la misma causa, que es una sola línea.** El detector agrupa por
`_normalize_location` (`src/sirius_engine/round_family_detector.py:127-131`),
que recorta el sufijo de línea con
`LOCATION_LINE_RE = re.compile(r":\d+(?:-\d+)?$")`
(`src/sirius_engine/round_history.py:79`): solo recorta cuando la cadena
**termina** en `:N`. Pero los revisores no escriben así. En la incidencia
#601, el mismo fichero aparece como:

- ronda 1: `src/sirius_engine/intent_interpreter.py` y
  `src/sirius_engine/intent_interpreter.py:148 (_NEGADORES 148-182, _va_negado 226-243)`
- ronda 2: `src/sirius_engine/intent_interpreter.py` y
  `src/sirius_engine/intent_interpreter.py:153 y :181 (_NEGADORES 156-184)`
- ronda 3: **solo** `src/sirius_engine/intent_interpreter.py:185-205 y :230`

La tercera forma no termina en `:N`, así que no se recorta nada y cuenta como
un archivo distinto: el tramo se rompe en la ronda 2 y el aviso nunca sale.
Lo mismo, exactamente, en #599 (la ruta desnuda aparece en las rondas 1 y 4,
y las rondas 2 y 3 solo la citan con paréntesis detrás), en #523, en #570 y
en #574.

Esto es notable por dos motivos. El primero es que **la solución ya está
construida en este árbol y el detector no la usa**: `parse_archivo_location`
existe desde ADR-133 precisamente porque el guardián de goteo se topó con el
mismo problema —su título es «el guardián de goteo entiende las citas tal
como los revisores las escriben de verdad»— y el detector de familia siguió
con el recorte estrecho. Es una variante del patrón F3 de la primera edición
(«pieza correcta sin llamante»): aquí la pieza sí tiene llamante, pero no el
que la necesita.

El segundo es que **el cambio se puede medir antes de hacerlo, y está medido
aquí**: la variante laxa produjo 8 tramos nuevos, de los que 6 son familias
reales y 2 no (#566 y #579). Por el criterio de entrada de la incidencia
#267 —una comprobación entra si caza más defectos reales que falsos
positivos— el neto es **+4** (o +3 si se descuenta el caso débil de #601).
Esa medición está hecha; lo que este informe **no** hace es aplicarla.

### 4.5 Qué significa esto para la decisión pendiente

La pregunta era si el detector merece autoridad para detener un ciclo. Lo que
los datos de septiembre permiten decir, y nada más:

- **Cuando avisa, acierta.** 8 de 8 en septiembre; 12 de 12 sumando ADR-078.
  Cero falsos positivos conocidos en dos mediciones independientes.
- **Ocho casos no son una tasa.** El criterio de parada de §5 de la nota de
  método se escribió antes de contarlos y se respeta aquí.
- **Avisa poco: se le escapan tantas familias como las que ve**, y por un
  motivo mecánico, identificado, medido y arreglable sin tocar el umbral de
  3 rondas que ADR-078 fijó.
- **La decisión no se toma en este informe.** El objetivo de la incidencia
  #627 lo prohíbe expresamente, y §8 se detiene antes de proponer ninguna
  implementación.

## 5. Familias de defecto más repetidas entre incidencias distintas

### F1 — La ficha afirma algo que su propio árbol deja de sostener

**La familia dominante de septiembre, con diferencia**: aparece en 8 de las
30 incidencias de la ventana (#523, #526, #566, #570, #574, #579, #581,
#597), y es la que produce 6 de los 8 avisos del detector (§4.2) y 4 de los 6
falsos negativos (§4.4). Es la F2 de la primera edición («cita o cifra que
deja de sostenerse tras la propia corrección»), ahora con un patrón interno
más concreto: casi siempre es la sección de validación o la tabla de
evidencia del propio ADR, y casi siempre la rompe la corrección anterior.

- #597 `CLAUDE-REV-597-003`: al añadir la fila M9 a la tabla de mutaciones se
  actualizó el encabezado («Nueve.») y no el recuento de la sección «Criterio
  de parada», que siguió diciendo ocho.
- #570 `CLAUDE-R2-002`: el commit que añade 81 líneas a la ficha no toca la
  sección de validación, que sigue anclada a dos árboles de la ronda 1.
- #526 `CLAUDE-REVISOR-001`: al corregir el recuento de pytest (4697 → 4698)
  queda a la vista que la duración adjunta nunca se actualizó, ni en esa
  ronda ni en las dos anteriores.

Que esta familia siga siendo la primera **en septiembre** merece una nota:
ADR-135 (`docs/decisions/ADR-135-el-corrector-actualiza-en-el-mismo-commit-el-papel-que-depende-de-su-correccion.md`)
atacó exactamente este patrón por el prompt del corrector el 04-09-2026. Este
informe **no mide si ADR-135 ha servido**: para eso haría falta comparar
antes y después con la misma población, y la ventana de este informe empieza
tres días antes del ADR y no está partida por esa fecha. Se declara como
hueco (§7) y como la primera candidata a medición de la tercera edición.

### F2 — La corrección de una ronda abre el siguiente hueco del mismo mecanismo

6 incidencias: #520, #529, #539, #545, #570, #601. Es exactamente lo que el
detector de familia repetida existe para ver, y §4 la mide de cerca. La
variante más pura es #539, donde el revisor la nombra en voz alta en la
ronda 3 («la TERCERA aparicion de la misma familia de defecto»), y la más
cara es #545, que acumuló 15 rondas en la ventana.

### F3 — El texto que el motor publica describe mal lo que el motor hace

**Familia candidata, con solo 2 incidencias** (#599 y #615): no llega al
listón de «3 o más incidencias distintas» que la primera edición usó para
declarar una familia, y se publica igualmente porque el patrón es nítido y
ninguna comprobación del repositorio puede verlo hoy.

- #599: cuatro rondas seguidas sobre
  `scripts/automation/sirius_apply_verdict.sh` corrigiendo lo que el aviso de
  Quality **dice** que va a pasar y no pasa —el `que_pasa` y el `desbloquea`
  de dos fases nuevas afirman cosas incompatibles entre sí en el mismo
  comentario publicado (`CLAUDE-REV-600-R3-001`)—.
- #615 `CLAUDE-R1-001` y, dos rondas después, `CLAUDE-R2-002`: el bloque que
  el despachador publica para explicar cómo se sale de una parada contiene
  una orden (`sirius-decidir … --continuar`) que no hace lo que el texto
  promete.

Es hermana de F1 —una afirmación sin sostén— pero el texto no vive en un ADR
sino en el comentario que la automatización publica en la incidencia, así que
ninguna guarda documental puede verla.

### F4 — Pieza correcta a la que no llama quien la necesita

Familia ya reconocida por el propio repositorio (`AGENTS.md:17-20`: «seis
veces una pieza correcta a la que no llamaba nadie») y con guarda propia
desde ADR-179
(`docs/decisions/ADR-179-la-guarda-de-piezas-sin-llamante-deriva-su-inventario-del-codigo-del-motor.md`).
§4.4 documenta una variante que esa guarda **no** puede ver: aquí
`parse_archivo_location` sí tiene llamantes —el guardián de goteo la usa—,
pero no la llama el módulo que la necesitaría. Un inventario de piezas sin
llamante no detecta una pieza con el llamante equivocado.

## 6. Guardián mecánico simple por familia: aciertos y falsos medidos

Mismo criterio de entrada que en la primera edición y que la incidencia #267:
**una comprobación entra solo si caza más defectos reales que falsos
positivos.** Ninguna de las siguientes se implementa aquí.

| Familia | Guardián candidato | Aciertos reales | Falsos positivos | Evidencia |
|---|---|---|---|---|
| F2 (familia repetida) | Ampliar el agrupamiento del detector para que use la ruta que encabeza el campo `archivo` (`parse_archivo_location`) en vez del recorte de `:N` final | +6 familias reales que hoy no ve | 2 (#566 y #579: tramos de 3 rondas sobre el mismo fichero que **no** son la misma familia) | §4.4 de este informe, medido caso por caso. Neto **+4**. |
| F2 (familia repetida) | Mantener el detector como está | 8 avisos, 8 acertados en septiembre; 12 de 12 con ADR-078 | 0 conocidos | §4.2 y `docs/decisions/ADR-078-…-medido-antes-de-fijarlo.md:94-105`. |
| §3 (goteo) | El guardián de goteo ya en producción (ADR-123/ADR-133) | 37 marcas en 15 incidencias, 18 concordantes con la declaración del propio revisor | No medido aquí: haría falta verificar cada marca contra el diff, el método de agosto | §3.2. **No es una precisión medida**, es concordancia entre dos señales. |
| F1 (ficha sin sostén) | Ampliar la guarda de citas de `docs/decisions/` a todo `docs/**` | **0** | **23** | Ya medido y **descartado** en `docs/decisions/ADR-190-la-guarda-de-citas-no-sale-de-docs-decisions-medidos-590-citas-y-23-rotas-fuera-del-registro-cero-son-defectos-de-este-arbol.md`: 590 citas, 23 rotas fuera del registro, cero son defectos de este árbol. Era la propuesta 4 de la primera edición; la medición la rechazó. |
| F3 (texto del motor) | Ninguno con evidencia suficiente | — | — | El texto vive en cadenas de shell dentro de `sirius_apply_verdict.sh`; comprobar que describe el comportamiento real exige razonar sobre el comportamiento, no sobre el texto. Se declara sin candidato. |

## 7. Huecos declarados

- **La colisión de ruta de la cabecera es un hueco abierto, no un detalle de
  forma.** ADR-132, ADR-134 y ADR-135 citan
  `docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09.md` para referirse a
  la mina v2 del 04-09-2026, que vive en una rama que nunca se fusiona; desde
  que este documento existe, esa ruta resuelve a **otro** texto, cuyos §4 y
  §8 dicen cosas distintas. La guarda de citas solo comprueba existencia de
  ruta (`tests/automation/test_citas_de_los_adr.py`), así que **pasará en
  verde sin que el problema se haya resuelto**: es, literalmente, un caso
  nuevo de la familia F1 de §5, creado por este informe. Las tres salidas
  —renombrar esta edición, re-anclar las tres citas a la ruta cualificada por
  rama, o aceptar la colisión— son decisión del propietario. Aquí se declara;
  no se elige.
- **Ninguna declaración de goteo de §3 se verificó contra el diff.** Agosto
  clasificó 89 hallazgos con `gh api compare`; septiembre cuenta
  autodeclaraciones y marcas. Las dos cifras miden cosas distintas y no deben
  compararse como si fueran la misma serie.
- **La concordancia del 48.6% de §3.2 no es la precisión del guardián.** Para
  eso haría falta un árbitro independiente de las dos señales, que este
  informe no tiene.
- **Los 8 avisos de §4.2 los clasificó un solo lector, sin segunda opinión.**
  El criterio se escribió antes (§nota de método, punto 4) y la cláusula de
  duda razonable estaba puesta en contra del detector, pero ninguna
  clasificación se contrastó con nadie. La excepción parcial son los cinco
  casos en los que el propio revisor declara la familia por escrito, donde la
  clasificación se apoya en una cita y no en un juicio.
- **La búsqueda de falsos negativos de §4.4 es mecánica y solo mira la misma
  ruta.** Una familia que se mueve de fichero entre rondas —#545 la tiene,
  entre `mirror_projection.py` y `reflect.py`— no la encuentra este método.
  El número de falsos negativos publicado (6) es, por construcción, un suelo.
- **El texto de los hallazgos de la incidencia #520 se leyó antes de escribir
  el criterio de §4**, al comprobar que el bloque
  `OBSERVACIONES_ESTRUCTURADAS` contenía el campo `problema` que la
  clasificación necesita. El criterio quedó escrito antes de emitir ninguna
  clasificación, incluida la de #520, pero no antes de haber visto ese texto:
  se declara en vez de dejarlo implícito.
- **No se mide si ADR-135 ha reducido la familia F1.** La ventana empieza el
  01-09 y el ADR es del 04-09; partirla en dos dejaría tres días a un lado y
  once al otro, con poblaciones demasiado desiguales para comparar. Queda
  para la tercera edición, que podrá comparar septiembre completo contra
  octubre.
- **La ventana excluye por construcción las incidencias cerradas antes del
  01-09 que aún tuvieran rondas pendientes de publicar**, y excluye las
  rondas de septiembre de incidencias cuyo historial no se descargó (solo se
  descargaron las 125 con actividad desde el 25-08-2026). Una incidencia sin
  actividad registrada en GitHub desde antes de esa fecha pero con una ronda
  publicada en septiembre sería invisible a esta medición; no se encontró
  ninguna, pero tampoco se buscó fuera de ese corte.

## 8. Propuestas

Ordenadas por (defectos reales cazados − falsos positivos medidos),
descendente. **Ninguna se implementa en esta incidencia**: son candidatas
para encargos aparte, sujetas a la aprobación del propietario, tal como exige
el objetivo de la incidencia #627.

1. **Que el detector de familia repetida agrupe por la ruta que encabeza la
   cita, no por el recorte de `:N` final.** Es el único cambio que este
   informe puede respaldar con una medición completa: +6 familias reales
   cazadas, 2 falsos positivos, neto +4 sobre las 26 incidencias de la
   ventana (§4.4). No toca el umbral de 3 rondas consecutivas que ADR-078
   midió, no toca `.github/**`, y la pieza que hace falta ya existe y ya está
   probada en el árbol (`src/sirius_engine/drip_guard.py:127`). El coste
   conocido es que los dos falsos positivos medidos se publicarían como
   avisos informativos —que es lo que el detector hace hoy: informar—.
2. **Decidir qué se hace con la colisión de ruta** (§7, hueco primero).
   No es una propuesta de ingeniería sino una decisión pendiente, y se lista
   aquí porque hasta que se tome hay tres ADR aprobados citando un documento
   que no es el que creen citar.
3. **Medir el guardián de goteo con el método de agosto, ahora que hay datos
   de producción.** Las 37 marcas de §3.2 son una muestra manejable y
   verificable una por una con `gh api compare`, que es exactamente lo que
   ADR-123 dejó pendiente al declarar que la marca sirve «para medir la tasa
   real en producción antes de darle cualquier autoridad»
   (`src/sirius_engine/drip_guard.py:12-16`). Sin esa medición, la marca
   lleva un mes acumulando datos que nadie ha leído.
4. **Que la marca del guardián sobreviva al JSON** (§3.3). Hoy solo vive en
   la prosa, así que cualquier medición futura tiene que reparsear texto. Es
   un cambio pequeño y de bajo riesgo en
   `scripts/automation/sirius_apply_verdict.sh:835`, pero **toca el formato
   del bloque que la puerta del corrector vuelve a leer**, así que no se
   propone sin que alguien compruebe antes qué más consume ese bloque.
5. **Una tercera edición de la mina sobre octubre, partida por ADR-135**,
   para medir si la familia F1 —dominante en septiembre, con 8 de 30
   incidencias— cede tras el cambio del prompt del corrector. Es la única
   forma de saber si aquella decisión funcionó, y hoy no se sabe.
