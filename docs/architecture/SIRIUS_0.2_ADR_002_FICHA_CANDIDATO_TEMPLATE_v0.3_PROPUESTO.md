# SIRIUS 0.2 — ADR-002 · Ficha de candidato · plantilla

**Versión:** 0.3
**Estado:** **PROPUESTO** · plantilla, **no está aprobada** y no autoriza nada por sí misma
**Fecha:** 31 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.2_PROPUESTO.md`, que se conserva **sin modificar** (igual que la v0.1). Las anteriores **no se editan** porque sus blobs los citan el Registro, el paquete 02D y la Resolución de la partición de candidatos: alterarlas haría incomprobable esa cadena
**Cambio de esta versión:** (1) la ficha pasa a tener una **forma JSON normativa** y auditable por máquina, con esta plantilla como su lectura humana; (2) el **§2.12** se reescribe conforme al acta de `ADR002-TOL-209` —**exactamente once sesiones**, dos reglas por percentil, `SM` y `U50` citados, sin umbral relativo para P95—; (3) el **§2.11** cita el presupuesto aprobado por el acta de `ADR002-TOL-207`; (4) el **§2.5** fija el protocolo **v0.2**; (5) las referencias pasan al **Registro v0.5**; (6) se añaden la **huella canónica** y la regla de **anterioridad comprobable**. **Todo lo demás de la v0.2 se conserva**: el universo `ADR002-A/B/C/D` + `T0-control`, el papel, la señal tardía del §2.2 bis y la restricción propia de `ADR002-D` del §2.2 ter
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_09_TOL210_FICHA_CANDIDATO_v0.1.md`
**Autoridad del universo de candidatos:** `SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md` y `SIRIUS_0.2_ADR_002_NOTA_SUPERACION_02_PARTICION_CANDIDATOS_v1.0_APROBADA.md`
**Exigida por:** `ADR002-TOL-210` del `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.5_PROPUESTO.md`
**No autoriza:** ejecutar el benchmark, ejecutar T0, implementar prototipos, elegir alternativa ni merge.

---

## 0. Por qué existe esta versión

La v0.1 puso la ficha en el contenedor correcto. La v0.2 corrigió el universo de candidatos. Ninguna de las dos hizo —ni podía hacer— lo que faltaba: volver **auditable** su cumplimiento.

`ADR002-TOL-210` dice dos cosas con consecuencia:

> Un candidato sin ficha confirmada **no es ejecutable**.
> Una ejecución que no referencie una ficha previa **no es utilizable como evidencia**.

Ambas son comprobables por máquina, y hasta el paquete 09 no las comprobaba nadie: la ficha era prosa, y su corrección dependía de la buena fe de quien la rellenase. **Es exactamente el defecto que la propia fila del Registro denuncia de la v0.3**, donde la regla «señalaba a un contenedor que no podía alojarla, y su cumplimiento no era auditable». Repetirlo un nivel más arriba habría sido el mismo error con mejor letra.

Por eso la ficha pasa a tener una **forma JSON normativa** validada por contrato, y la anterioridad de su congelación deja de ser una fecha escrita para ser una **relación de ancestro en el grafo de Git**. Una fecha se escribe; un ancestro, no.

### 0.1 Qué cambia y qué no

| Punto | v0.2 | **v0.3** |
|---|---|---|
| Forma normativa | Markdown rellenado a mano | **JSON** validado por `schema_card_v0_1`; esta plantilla es su lectura humana |
| Congelación | «commit de confirmación» y «fecha», escritos | **Huella canónica** + fichero confirmado en su commit + **ancestro estricto** del commit que ejecuta |
| §2.5 protocolo | `PROTOCOLO_MEDICION_v‹›` | **v0.2**, el aprobado, sin alternativa |
| §2.11 presupuesto | `‹›` a rellenar | **`1610612736 B`**, citado del acta de TOL-207 |
| §2.12 sesiones | «`‹≥5›`» | **`11`, exactamente** |
| §2.12 régimen | «umbral de conmutación» único | **Dos reglas por percentil**, `SM` y `U50` citados, **sin umbral relativo para P95** |
| Universo de fichas | `ADR002-A/B/C/D` + `T0-control` | **sin cambio** |
| §2.2 bis y §2.2 ter | señal tardía y restricción de `D` | **sin cambio de fondo**, ahora con campos |

---

## 1. Reglas de uso

1. **Una ficha por candidato.** `ADR002-A`, `ADR002-B`, `ADR002-C` y `ADR002-D` tienen fichas distintas. **`T0` tiene la suya**, marcada como control de falsación, y no es candidato.
2. **Confirmada antes de la primera ejecución.** No basta declararlo: el commit que confirma la ficha debe ser **ancestro estricto** del commit que ejecuta. Aparecer en el mismo commit **no** es haber congelado antes.
3. **Completa o inexistente.** Un campo vacío o «pendiente» invalida la ficha. Si un valor no puede declararse, se declara **por qué**, y esa imposibilidad se congela igual.
4. **Versionada, y de una en una.** Las versiones crecen `1 → 2 → 3`, nunca saltan ni retroceden. Una sucesora declara **a quién sustituye y por qué**, y obliga a **repetir** las ejecuciones hechas bajo la anterior (Registro v0.5 §9 reglas 2 y 10).
5. **Una sola ficha `CONGELADA` por candidato.** Publicar una sucesora obliga a marcar `SUSTITUIDA` la anterior.
6. **Referenciada desde cada ejecución** por `candidato · versión · huella`. Una ejecución que no referencie una ficha previa **no es utilizable como evidencia**.
7. **No sustituye a la ficha del caso.** Ambas coexisten: la del caso describe qué se prueba, esta describe contra qué límites se juzga al candidato.
8. **No contiene resultados.** Límites y declaraciones, jamás mediciones del propio candidato. El contrato lo hace cumplir **cerrando** todos los conjuntos de campos: lo que el esquema no prevé, no entra.
9. **Ninguna alternativa mínima puede fichar como control.** `ADR002-A`, `ADR002-B`, `ADR002-C` y `ADR002-D` son candidatos completos y se juzgan con las mismas puertas. **Marcar `ADR002-A` o `ADR002-C` como control invalida la ficha** (Resolución v1.0 §2.1 y §2.2).

### 1.1 La huella

La huella de una ficha es el **blob Git de su forma canónica excluido el propio campo de huella**.

Se excluye por necesidad aritmética, no por comodidad: una huella que se incluyese a sí misma **no tendría punto fijo**, porque escribirla cambia el contenido que la produce. Excluirla no debilita nada, porque el campo excluido es justo el que se comprueba.

La huella dice **qué** se congeló. **Cuándo** lo dice otra comprobación distinta: que el fichero coincida con su versión confirmada en el commit declarado, y que ese commit preceda a la ejecución. Ninguna de las dos sustituye a la otra.

---

## 2. Contenido mínimo

La forma normativa es el JSON descrito por `experiments/adr002/cards/schema_card_v0_1.py`. Cada apartado corresponde a una **sección obligatoria** del contrato y ninguno puede omitirse.

### 2.1 Identidad · `identidad`

| Campo | Valor |
|---|---|
| **Candidato** | `‹ADR002-A · ADR002-B · ADR002-C · ADR002-D · T0-control›` |
| **Papel** | `CANDIDATO` · `CONTROL_DE_FALSACION` — **solo `T0-control`** puede ser control |
| **Versión de ficha** | entero, crece de una en una |
| **Sustituye a** | `null` en la primera; la versión inmediatamente anterior en las sucesoras |
| **Motivo de sustitución** | `null` en la primera; obligatorio y con fundamento en las sucesoras |

### 2.2 Congelación · `congelacion`

| Campo | Valor |
|---|---|
| **Commit** | sha del commit que confirma esta ficha |
| **Huella** | huella canónica, §1.1 |
| **Ruta** | `artifacts/adr002_cards/ficha_‹ID›_v‹N›.json` |

### 2.3 Arquitectura declarada · `arquitectura`

| Campo | Valor |
|---|---|
| **Alternativa mínima** | `‹ADR002-A · ADR002-B · ADR002-C · ADR002-D›` según **ARQ-00 §23**; **`null` para `T0-control`**, que no representa ninguna |
| **Definición canónica que asume** | transcribir literalmente la fila correspondiente de ARQ-00 §23 |
| **Sustrato léxico** | `‹FTS5 medido · alternativo: nombre y versión›` |
| **Materialización de relaciones** | `‹desde el canon · índice relacional derivado›` |
| **Puerto de acceso** | equivalente a `KnowledgeSearchRepository`; obligatorio por RF-31 y la puerta 6 |
| **Etapas E0–E5** | una declaración por etapa: qué ocurre y qué condición de insuficiencia autoriza la transición |

**Puertas previas comunes.** No son ventaja de ningún candidato y ninguno puede omitirlas. **Las seis son obligatorias**, una declaración cada una:

`aislamiento_de_ambito` · `expansion_escalonada_sin_salto` · `validacion_de_sujeto_polaridad_condicion_y_tiempo` · `borrado_y_regeneracion_desde_el_canon` · `peticion_completa_y_operacion_activa` · `plan_reproducible_y_explicacion_por_resultado`

### 2.4 Señal tardía y orden de etapas · `senal_tardia` — **obligatorio**

**Es lo que distingue a cada alternativa mínima.** La etapa `E3` es obligatoria para **todos** los candidatos, incluido `ADR002-A`, con validación explícita de sujeto, polaridad, condición y tiempo (`B04-RF-17`). **Una señal semántica vectorial NO es obligatoria**: `B04-RF-31` prohíbe convertir una obligación de comportamiento en una realización predeterminada, y no declararla **no es un déficit**, es la alternativa que se pone a prueba.

| Campo | Valor |
|---|---|
| **Habilitada** | `ninguna_adicional` (A) · `semantica_vectorial` (B) · `relacional_explicita` (C) · `ambas_en_etapas_distintas` (D) · `null` para `T0-control` |
| **Coherente con la alternativa** | `true` — el contrato comprueba que coincide exactamente con §2.3; una discrepancia invalida la ficha |
| **Cómo satisface E3** | obligatorio **también para `ADR002-A`**: por qué medios léxico-estructurados se buscan paráfrasis, dependencias, apoyo/refutación y relaciones |
| **Validación en E3** | mecanismo concreto; **no se hereda de la señal** |
| **Orden de las etapas tardías** | secuencia exacta y congelada; para `A`, «no aplica: sin señal tardía adicional» |
| **Condición de insuficiencia por transición** | una por transición |

### 2.5 Restricción propia de `ADR002-D` · `restriccion_d` — **obligatorio para D**

`ADR002-D` **no es `B` más `C`**. Sus tres restricciones son acumulativas y su anclaje es `B04-D15`, que prohíbe adelantar espacios posteriores y sustituir la política escalonada.

| Campo | Valor |
|---|---|
| **Aplica** | `true` solo si la alternativa es `ADR002-D`; el contrato lo recomputa |
| **Motivo de no aplicación** | obligatorio cuando `aplica` es `false`; `null` cuando es `true` |
| **Señales en etapas distintas** | qué señal en qué etapa |
| **Orden predefinido** | orden exacto y su fundamento, congelado antes de ejecutar |
| **Sin coordinación simultánea** | cómo se impide **técnicamente**, no solo por convención |
| **Cómo se demuestra en cada ejecución** | traza que evidencia la etapa de cada señal y la ausencia de coordinación simultánea |
| **Traza a `B04-D15`** | cómo se garantiza que la coordinación solo combina señales del mismo espacio y familia de la etapa activa |

**Consecuencia:** un `ADR002-D` que coordine ambas señales simultáneamente, o que no respete el orden aquí congelado, **incumple `B04-D15` y la puerta 9** aunque sus resultados sean perfectos.

### 2.6 Componentes y versiones · `componentes`

Una entrada por componente, con `papel`, `nombre`, `version`, `origen`, `acopla_a_proveedor` y `ruta_de_sustitucion`.

> Un candidato que no declara representación semántica o índice relacional lo dice expresamente. **No declararlo no es un déficit**: es la alternativa que se está poniendo a prueba.

**Puerta 6 de ADR-002 (RF-31):** un componente que acople a un proveedor o formato no portable **debe** declarar su ruta de sustitución. Sin ella, descarta.

### 2.7 Corpus y entorno · `corpus` — `ADR002-TOL-208`

Versión de corpus, mensajes / recuerdos / decisiones / proyectos, longitud media y distribución, commit, head de esquema, si **T0 se rederivó sobre este mismo corpus** y la referencia que lo acredita —o por qué todavía no existe—.

**Prohibido** reutilizar cifras del corpus 5.000/500 sobre otro volumen sin rederivar.

### 2.8 Protocolo aplicado · `protocolo_aplicado` — `ADR002-TOL-209`

| Campo | Valor |
|---|---|
| **Protocolo** | `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md` — **el aprobado, sin alternativa** |
| **Desviaciones** | `ninguna` o lista con fundamento, declarada **antes** de ejecutar |
| **Entorno** | máquina, SO, carga controlada o no |
| **Semilla** | fija |
| **Repeticiones por magnitud** | **≥30**; 100 cuando el coste sea bajo |

### 2.9 Sustrato léxico · `sustrato_lexico` — `ADR002-TOL-101A`

Si el sustrato **es** el FTS5 medido, `magnitudes` queda **vacía**: rigen TOL-101L, TOL-104L y los tiempos de TOL-105. Si **no** lo es, congela sus seis magnitudes propias con objetivo, límite duro y fundamento. **Ningún objetivo puede superar a su propio límite duro.**

**Neutralidad (Registro §5.6):** la desviación respecto de FTS5 se informa como **comparación**, no como déficit automático. Lo que descarta es incumplir el límite que el candidato **mismo** congeló.

### 2.10 Índices no léxicos · `indices_no_lexicos` — `ADR002-TOL-104A`

Una entrada por índice, con los trece campos, más `escala_comun` a 500 / 5.000 / 50.000 unidades y `limites_por_magnitud` para tamaño, construcción, reconstrucción y borrado.

### 2.11 Ciclo de todo índice adicional · `ciclo_de_indice` — `ADR002-TOL-203`

Las cuatro operaciones —`tamano`, `construccion`, `reconstruccion`, `borrado`— con límite y fundamento, más las cuatro obligaciones de comportamiento.

**No ejecutabilidad.** Si una operación no es ejecutable ≥30 veces, se declara **con motivo técnico y evidencia alternativa**, antes de ejecutar (§3.6 del protocolo). Invocarlo después equivale a no haber declarado el límite. A la inversa: una operación ejecutable **no** declara exención.

### 2.12 Coste por etapa · `coste_por_etapa` — `ADR002-TOL-202`

Las seis etapas E0–E5 en orden, cada una con objetivo y límite locales en nanosegundos, operaciones locales y **coste externo declarado aparte**.

**Regla de coherencia:** la suma de los límites locales por etapa debe **explicar** el `coste_local_total_ns`. Una discrepancia no explicada invalida ambas declaraciones.

**El coste externo nunca se suma al local.** Por eso se declara en texto y no como entero: para que no pueda entrar en la aritmética.

### 2.13 Límite extremo a extremo · `extremo_a_extremo` — `ADR002-TOL-102C`

Objetivo P95 y límite duro P99 en nanosegundos —el segundo debe coincidir con `coste_extremo_a_extremo_ns`—, percentil y n, fundamento, y dos campos obligatorios en `true`: **no deriva de TOL-102B** y **no invoca el barrido de T0**.

No son advertencias, son campos: **ningún** candidato puede invocar el barrido prohibido de T0 como justificación de un coste alto propio. Superar el tiempo de T0 no descarta; incumplir el límite congelado aquí, sí.

### 2.14 Almacenamiento absoluto · `almacenamiento` — `ADR002-TOL-207`

| Campo | Valor |
|---|---|
| **Presupuesto absoluto (B)** | `1610612736` — **citado del acta de TOL-207, no elegido** |
| **Consumo declarado (B)** | entero |
| **Porcentaje (‰)** | recomputado: `1000 · consumo / presupuesto`, truncado |
| **Proyección a 50.000 (B)** | entero |
| **¿Cabe?** | recomputado: `0 ≤ consumo ≤ presupuesto` |

Si no cabe, el candidato queda descartado por la puerta 7.

### 2.15 Estabilidad · `estabilidad` — `ADR002-TOL-107`

**Reescrito conforme al acta de `ADR002-TOL-209`.** La ficha **cita** el perfil aprobado; no propone uno propio.

| Campo | Valor |
|---|---|
| **Sesiones previstas** | `11` — **exactamente**, no «al menos» |
| **`SM` (ns)** | `17405` — citado del perfil aprobado |
| **`U50` (ns)** | `2685` — citado del perfil aprobado |
| **Régimen P50** | relativo `≤ 20 %` por encima de `U50`; `B50(M)` por debajo; **sin afirmación de latencia bajo `SM`** |
| **Régimen P95** | absoluto contra `B95(M)` en **todo el rango cubierto**; `NO_EVALUABLE` bajo `SM` o por encima de la mayor escala medida |
| **Sin umbral relativo para P95** | `true` |
| **Consulta de la banda** | `M` es el **mínimo entre sesiones del mismo percentil** que se evalúa |
| **Repetición única y `NO EVALUABLE`** | declaración |

**Por qué exactamente once.** `(máx − mín)` es un **rango**, y la esperanza de un rango crece con el tamaño de la muestra. Una magnitud medida con otro número es **`NO_COMPARABLE`** frente a las bandas de TOL-107 y **no recibe veredicto**. La v0.2 de esta plantilla pedía «≥5»: era justo la fórmula que la decisión prohíbe.

### 2.16 Banda temporal e indistinguibilidad · `banda_temporal` — `ADR002-TOL-201` y `TOL-002`

Las cuatro condiciones, el modelo de amenaza declarado, y un campo obligatorio en `true`: **no hereda la indistinguibilidad de la línea base**.

**No es un formalismo.** La indistinguibilidad observada en la línea base es en buena medida **accidental**: un barrido constante de 122,5 ms enmascara una diferencia de trabajo ~31.000 veces menor. Un candidato que elimine el barrido, como RF-14 exige, **pierde ese enmascaramiento**. El resultado no se hereda, y la ficha tiene que reconocerlo por escrito.

### 2.17 Purga física · `purga` — `ADR002-TOL-206`

Secuencia declarada, los cuatro ficheros cubiertos —`.db`, `-wal`, `-shm`, `-journal`—, qué payload literal o representación reversible contiene el derivado, modelo de amenaza **no más débil que el de ADR-001**, y comprobación propuesta.

### 2.18 Huella del candidato · `huella_candidato`

Commit del prototipo, hash del árbol de fuentes, migraciones o DDL aplicados, artefactos generados con su hash, y comandos exactos de reproducción.

### 2.19 Declaración de congelación · `declaracion_de_congelacion`

> Declaro que los valores de esta ficha se han fijado **antes** de la primera ejecución de este candidato, que no proceden de ningún resultado observado del propio candidato, y que cualquier modificación posterior obligará a nueva versión de ficha y a repetir las ejecuciones ya realizadas.

Con responsable, fecha y `valores_anteriores_a_la_primera_ejecucion: true`.

---

## 3. Verificación antes de ejecutar

No es una lista para marcar a mano. La ejecuta:

```text
uv run python -m experiments.adr002.cards.verify_cards --check \
    --execution <SHA> --candidate <ID> --version <N> --fingerprint <huella>
```

Y comprueba, fallando cerrado:

1. las **plantillas anteriores** siguen intactas;
2. cada ficha cumple el **contenido mínimo**, con los conjuntos de campos cerrados;
3. la **huella declarada** recomputa sobre el contenido normativo;
4. el fichero coincide con su versión **confirmada** en el commit que declara;
5. ese commit es **ancestro estricto** del commit que ejecuta;
6. hay **una sola** ficha `CONGELADA` por candidato;
7. las **cinco puertas de arranque** están satisfechas: `SRC-ADR002-01`, TOL-207, TOL-208, TOL-209, TOL-210.

Cualquier fallo deja la ejecución **no utilizable como evidencia**, o al candidato **no ejecutable**, según el caso.

---

## 4. Lo que esta plantilla no hace

- No aprueba ningún candidato ni autoriza ejecutarlo.
- **No emite ninguna ficha.** `ADR002-TOL-210` sigue **NO SATISFECHA**.
- No fija ningún valor: los valores los declara y congela cada candidato bajo su responsabilidad. Lo único que el contrato impone es que los declare **antes**, **completos** y **sin contradecir** lo ya aprobado.
- **No declara obligatoria ninguna señal tardía concreta.** Obligatoria es la etapa `E3`; qué señal la satisface es lo que el benchmark mide.
- **No convierte `ADR002-A` ni `ADR002-C` en controles.** Solo `T0` puede fichar como control de falsación.
- No sustituye a la ficha del caso de la Especificación de benchmark §5.
- No sustituye al Registro de Tolerancias: lo instrumenta.
- **No declara satisfecha `ADR002-TOL-208`** ni autoriza ejecutar T0 ni sus pasos 2 y 3.
- No abre `EJE-1` ni `EJE-2`: en la primera ronda todos los candidatos comparten el sustrato léxico FTS5 medido.
- No modifica `src/`, `tests/`, `migrations/` ni configuración productiva.

---

**Siguiente movimiento único:** que el usuario apruebe o corrija esta plantilla v0.3 junto al Registro v0.5. Hasta entonces no se instancia ninguna ficha, y aunque se apruebe, **no habrá ficha que emitir mientras no exista un candidato autorizado** y `ADR002-TOL-208` no esté satisfecha en sus tres pasos.
