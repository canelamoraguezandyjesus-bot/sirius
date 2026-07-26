# SIRIUS 0.2 — Registro de Tolerancias

**Versión:** 0.4
**Estado:** **PROPUESTO** · este Registro **no está aprobado** y no autoriza nada por sí mismo
**Fecha:** 26 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.3_PROPUESTO.md`, que se conserva sin modificar (igual que la v0.2 y la v0.1)
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02D_CORRECCION_AUDITORIA_v0.1.md`
**Entrada correctiva:** auditoría adversarial de la v0.3 · veredicto **NO APROBABLE**, con B-01, B-02 y B-03 bloqueantes
**Evidencia:** `artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json` · `INFORME_MEDICION_TOLERANCIAS_v0.2_PROPUESTO.md`
**Artefactos obligatorios asociados:** `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.1_PROPUESTO.md` · `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md`
**Alcance de toda cifra medida:** **LAB-LINUX** · `ACEPTACIÓN-WINDOWS` **pendiente**
**No autoriza:** benchmark T1–T4, ejecución de T0, prototipos, remedición, implementación productiva, elección de alternativa ni merge.

---

## 0. Qué corrige esta versión

Corrección **exclusivamente documental**. **No se ha ejecutado ninguna medición nueva, ninguna cifra medida ha cambiado y ningún umbral canónico se ha modificado ni rebajado.**

Esta versión hace tres cosas: **restaura** la integridad documental que la v0.3 perdió, **corrige** dos filas cuyo fundamento la evidencia refutaba, y **cierra** las lagunas que impedían ejecutar el benchmark de forma justa.

### 0.1 Regla de honestidad documental de esta versión

> **Prohibido declarar «sin cambios» para una fila cuyo texto difiera del de la versión anterior.**

La v0.3 declaró «Sin cambios respecto de la v0.2» en once filas; ocho de ellas tenían el texto alterado, y tres perdían contenido normativo o de neutralidad. Esa es la causa del veredicto NO APROBABLE. El §0.3 de esta versión enumera **todos** los cambios v0.3 → v0.4, uno por uno. Si una fila no aparece en esa lista, su texto es idéntico al de la fuente que se declara.

### 0.2 Cierre de B-01 · Integridad restaurada desde la v0.2

Se ha restaurado **literalmente desde la v0.2** el contenido completo de las ocho filas alteradas, y solo después se han aplicado los cambios explícitos de este paquete. Contenido concreto que la v0.3 había suprimido y que vuelve a estar presente:

| Fila | Texto restaurado |
|---|---|
| **TOL-101** → 101L | «Amplio porque **un candidato con vocabulario o índice distinto puede ser legítimamente más lento**» · «obliga a **justificar el coste frente a la aportación medida**» |
| **TOL-102** → 102B | Las anclas numéricas del margen · «Uno que apenas alcance el techo **probablemente reproduce el mismo defecto**» · la *Nota de corrección* v0.1 → v0.2 |
| **TOL-103** | «**La línea base ya alcanza el 100 %**» · «caso **estrictamente más exigente**» |
| **TOL-105** | El `rebuild` interno «**no puede usarse como evidencia**» · «Límite duro anclado a la peor cola observada **del ciclo** (122,9 ms, **borrado**)» · la *Nota de corrección* v0.1 → v0.2 |
| **TOL-106** | «Esta fila cubre la desaparición lógica del derivado, **no la purga del medio**» |
| **TOL-107** | «**A esa escala la comparación debe hacerse en valor absoluto**» · «Acotan la variación intra-proceso, **no la variación entre procesos, entre máquinas ni entre sistemas operativos**» · «**el §4 del paquete 02B lo prohíbe expresamente**» · la *Nota de corrección* v0.1 → v0.2 |
| **TOL-201** | La fila «**Corrección del 02B**: la fracción de signo… **nunca como única protección**. Las condiciones **(3) y (4) son nuevas y obligatorias**» · los Δ observados **+15,4 ms y +21,5 ms** |
| **TOL-204** | «**descarta el candidato**» · «La v0.1 la clasificó como pendiente de congelar por candidato, y **eso contradecía B04**» |

**B-01 queda cerrado.** Ninguna de esas frases vuelve a desaparecer sin declaración.

### 0.3 Historial completo de cambios v0.3 → v0.4

**Restauraciones (B-01).** Ocho filas restauradas desde la v0.2 antes de cualquier otro cambio: TOL-101, 102, 103, 105, 106, 107, 201 y 204. Tres *Notas de corrección* v0.1 → v0.2 restauradas: las de TOL-102, TOL-105 y TOL-107.

**Filas retiradas y sustituidas.**

| Retirada | Sustituida por | Motivo |
|---|---|---|
| `ADR002-TOL-101` | **`TOL-101L`** (FTS5 medido) + **`TOL-101A`** (sustrato léxico alternativo) | B-03 y neutralidad del eje léxico |
| `ADR002-TOL-102` | **`TOL-102B`** (comparativa de línea base) + **`TOL-102C`** (límite del candidato) | B-02 y neutralidad del coste semántico |

**No existen `TOL-101B` ni `TOL-102A`.** Los identificadores retirados no se reutilizan.

**Cifras corregidas contra el JSON (B-03).**

| Magnitud | v0.3 declaraba | v0.4 declara | Origen exacto |
|---|---|---|---|
| FTS5 P50 | 0,172–0,576 ms | **0,1407–0,6759 ms** | S2 `cero_resultados` / S4 `muchos_candidatos` |
| FTS5 P95 | 0,209–0,730 ms | **0,1884–1,0038 ms** | S2 `cero_resultados` / S4 `muchos_candidatos` |
| FTS5 P99 | 0,251–1,415 ms | **0,2099–1,4145 ms** | S2 `cero_resultados` / `E-LAT-N` del paquete 02 |
| FTS5 muestra máxima | no declarada | **2,3934 ms** | S2 `muchos_candidatos` |
| Margen del objetivo | ×2,05 | **×1,49** | 1,5 ÷ 1,0038 |
| `rank()` P95 | 125,1–147,2 ms | **125,0519–173,1957 ms** | `E-LAT-1` / `E-TOL002` rama `no_reportable` |
| `rank()` P99 | 129,0–154,4 ms | **127,9717–181,8166 ms** | S5 `muchos_candidatos` / `E-TOL002` rama `no_reportable` |

El valor «0,209» de la v0.2 y la v0.3 no existía como P95 en la evidencia: `0.2099` aparece una sola vez en el JSON y es un **P99** (sesión 2, `cero_resultados`). Queda corregido.

**Umbrales retirados.** El **objetivo P95 ≤ 150 ms** y el **límite duro P99 ≤ 250 ms** del antiguo TOL-102 dejan de existir como umbrales universales congelados. No es una rebaja de umbral canónico —nunca fueron canónicos, eran `PROPUESTA`— sino la retirada de un fundamento que la propia evidencia refutaba: la línea base **supera** los 150 ms de P95 en dos escenarios medidos. Ver TOL-102B.

**Reglas de consecuencia eliminadas por no ser medibles.** «Combinada con TOL-102, descarta» (TOL-101) y «combinada con la puerta 5, descarta» (TOL-104L). Ninguna definía la combinación, y la segunda era vacua porque la puerta 5 descarta por sí sola. Cada fila aplica ahora su consecuencia propia.

**Filas nuevas.**

| ID | Objeto | Origen |
|---|---|---|
| `ADR002-TOL-101A` | Sustrato léxico alternativo de T3/T4: latencia, tamaño y ciclo por candidato | 02D §3.3, §4.1 |
| `ADR002-TOL-102B` | Línea base extremo a extremo como dato comparativo | 02D §3.2 |
| `ADR002-TOL-102C` | Límite extremo a extremo del candidato | 02D §3.2 |
| `ADR002-TOL-206` | Purga física del derivado | 02D §6 |
| `ADR002-TOL-207` | Presupuesto absoluto de almacenamiento del entorno de laboratorio | 02D §5.5 |
| `ADR002-TOL-208` | Corpus, escala y rederivación de la línea base | 02D §5.2 |
| `ADR002-TOL-209` | Protocolo común de medición | 02D §5.4 |
| `ADR002-TOL-210` | Ficha de candidato obligatoria | 02D §5.3 |
| `SRC-ADR002-01` | Puerta de arranque por fuentes canónicas completas | 02D §5.1 |

**Filas ampliadas.**

| Fila | Ampliación |
|---|---|
| `TOL-104A` | Escala común obligatoria de reporte y porcentaje del presupuesto de TOL-207; límite duro **por cada magnitud declarada**, no solo tamaño |
| `TOL-104L` | Restituido «**por índice**»; consecuencia de fallo propia; ámbito remitido a TOL-101A para sustratos no medidos |
| `TOL-105` | Campo «Ámbito» (ya anunciado en la v0.3) y remisión explícita a TOL-101A / TOL-203; resolución del P99 con n=30 declarada en la fila |
| `TOL-106` | Remisión a la nueva TOL-206 para la purga física |
| `TOL-107` | Dos regímenes —relativo y absoluto— con umbral de conmutación congelado; estado `NO EVALUABLE` tras una única repetición controlada |
| `TOL-202` | Coste de inferencia o generación de señal de consulta; objetivo y límite duro **por etapa** congelados; coste extremo a extremo resultante |
| `TOL-203` | Límite congelado para **cada** magnitud (tamaño, construcción, reconstrucción, borrado); el ≥30 repeticiones aplica también a las tasas del 100 %; la no ejecutabilidad se declara **antes** |
| `TOL-205` | Se le añaden TOL-206 y TOL-207 como reverificaciones obligatorias en Windows |

**Estados nuevos.** `REGLA_CONFIRMADA_VALOR_CANDIDATO_Y_ENTORNO` y `PUERTA_DE_ARRANQUE`.

**Notas de dependencia añadidas —declaradas, no silenciosas.** Tres textos nuevos que no modifican ninguna cifra ni ningún umbral:

| Dónde | Qué añade |
|---|---|
| §3, bajo la tabla de M01–M21 | La regla de muestreo de **M14** no consta en ninguna fuente del repositorio; sin ella M14 no es ejecutable. Dependencia de `SRC-ADR002-01`. **Las veintiuna filas de la tabla siguen siendo literalmente idénticas a las de la v0.2 y la v0.3** |
| TOL-204, última fila | El umbral **está cerrado** pero **no es medible** sin casos con criticidad de origen trazable. La falta de medibilidad **no reabre el umbral**: bloquea el benchmark |
| TOL-201, última fila | RF-26 habla de tolerancias de texto, estado, conteo y tiempo; la condición (1) impone equivalencia exacta, que es el lado seguro. Si B04/PDP fijan una tolerancia no nula, **prevalece la canónica** |

**Corrección aritmética declarada.** En la advertencia de TOL-105, «el P99 del `rebuild` interno es seis veces su P95» pasa a «**más de ocho veces**»: 269,912 ÷ 32,951 = 8,19. El enunciado erróneo procede de la v0.2 y del Informe §3.2. **Se corrige el Registro; no se modifica el Informe ni ninguna medición.**

**Conservado sin cambios desde la v0.3:** TOL-104L en su métrica, dato observado, objetivo, límite duro, margen y advertencia de alcance · TOL-104A en su regla, ficha de trece campos y punto de congelación · §5.1 · §5.2 · la corrección de TOL-203 sobre qué **no** hereda · la nota de la v0.3 en TOL-205 · la declaración de neutralidad tecnológica.

**Conservado sin cambios desde la v0.2, verificado por comparación literal:** las seis filas `CANÓNICA` de TOL-001 a TOL-006 y las veintiuna de B04-M01 a M21. Idénticas en v0.2, v0.3 y v0.4.

### 0.4 Qué sigue sin resolverse aquí, y por qué

- **Las fuentes canónicas completas no están en el repositorio.** No se afirma lo contrario en ningún punto de este Registro. Su materialización es ahora una puerta de arranque explícita: `SRC-ADR002-01`.
- **Las tolerancias de texto, estado, conteo y tiempo de RF-26** pueden estar ya fijadas en B04/PDP con valor no nulo. Este Registro impone equivalencia exacta en TOL-201 condición (1), que es el lado seguro, y **registra la comprobación como pendiente** de `SRC-ADR002-01`. No se inventa ninguna tolerancia.
- **La regla de muestreo de B04-M14** («100 % de muestra auditada») no está disponible. Registrada como dependencia de `SRC-ADR002-01`.

---

## 1. Cómo leer este Registro

### 1.1 Estados

| Estado | Significado |
|---|---|
| `CANÓNICA` | Ya aprobada en B04/PDP. Se reproduce literalmente. **No se toca.** |
| `DERIVADA_CANÓNICA` | Su valor **se deduce sin margen** de una regla canónica. No es una propuesta y no admite negociación por candidato. |
| `PROPUESTA` | Cifra nueva con medición, margen y consecuencia declarados. Requiere aprobación explícita. |
| `COMPARATIVA_LINEA_BASE` | Dato medido sobre T0 que se publica para comparar. **No es umbral y no descarta a ningún candidato.** |
| `REGLA_CONFIRMADA_VALOR_CANDIDATO` | La regla es firme; el valor solo puede fijarse frente a un candidato concreto, antes de ejecutarlo. |
| `REGLA_CONFIRMADA_VALOR_ENTORNO` | La regla es firme; el valor depende del entorno de ejecución y **la evidencia disponible no basta** para fijarlo. **No se inventa.** |
| `REGLA_CONFIRMADA_VALOR_CANDIDATO_Y_ENTORNO` | **Nuevo en la v0.4.** La regla es firme; el valor depende a la vez del candidato y del entorno, y ambos se congelan juntos antes de ejecutar. |
| `PUERTA_DE_ARRANQUE` | **Nuevo en la v0.4.** No es una tolerancia: es una condición sin la cual el benchmark no puede comenzar. No admite margen ni excepción por candidato. |
| `NO_APLICA_ADR002` | Pertenece a otro ADR. Se registra la dependencia. |

### 1.2 Alcance de toda cifra medida

**`LAB-LINUX`** — umbral del laboratorio comparativo Linux. Sirve para comparar T1–T4 entre sí en el mismo entorno, y solo para eso.

**`ACEPTACIÓN-WINDOWS`** — **PENDIENTE**. Ninguna cifra absoluta de latencia, tamaño o ciclo se traslada automáticamente a Windows. Aceptar la implementación exige confirmar el comportamiento sobre el ejecutable o entorno de referencia Windows, incluidos el tokenizador, `secure_delete` y la secuencia de purga que ADR-001 dejó pendientes.

**Sí es trasladable** lo booleano: restitución idéntica, `integrity-check`, desaparición completa del derivado, purga física sin fragmento recuperable y estabilidad de orden y conjunto. Son propiedades de comportamiento, no cifras de rendimiento.

### 1.3 Regla de propuesta

Toda fila `PROPUESTA` declara **dato observado**, **margen elegido** y **consecuencia de fallo**. Ninguna cifra se ha inventado: o es canónica, o procede de una medición reproducible.

**Añadido en la v0.4:** toda fila que publique una cifra medida declara además su **procedencia exacta dentro del JSON de evidencia**, de modo que el dato observado sea verificable sin releer el informe.

### 1.4 Vinculación de toda cifra al corpus que la produjo — nuevo en la v0.4

Ninguna cifra `LAB-LINUX` de latencia, tamaño o ciclo significa nada fuera del corpus sobre el que se midió. Todas las de este Registro proceden del **corpus de referencia de la remedición 02B**: 5.000 mensajes, 500 recuerdos (499 memorias vigentes), 50 decisiones aprobadas, 2 proyectos, head de Alembic `61be4bb269bf`, commit `610d10c5410438ad6251ebf0f813832539a6daef`.

Latencia extremo a extremo, tiempo de ciclo y tamaño del índice son magnitudes que **escalan con el corpus**. Aplicarlas sin más a un corpus distinto no es congelar una tolerancia: es cambiarla en silencio. La regla de arranque está en **ADR002-TOL-208**.

### 1.5 Tratamiento uniforme de los percentiles con muestras pequeñas — nuevo en la v0.4

Regla única, aplicable a **todas** las filas de este Registro:

- Con **n=30**, el P99 por rango más cercano **coincide con el máximo observado**: acota la cola, **no la caracteriza**. Un P95 con n=30 es la segunda peor muestra.
- Con **n=100**, el P99 es la peor muestra observada.
- En consecuencia: **ninguna cola de n=30 puede usarse en una fila y descartarse en otra según convenga.** O las colas de n=30 son evidencia utilizable para todas las filas que las publiquen, o para ninguna.

Esta regla es la que obliga a corregir el antiguo TOL-102: no era admisible anclar su límite duro en un P99 de n=30 y a la vez excluir del «peor observado» los P95 y P99 de n=30 del escenario TOL-002.

---

## 2. Valores ya canónicos — TOL-001 a TOL-006

Reproducidos literalmente. **Estado: `CANÓNICA` en las seis. Texto idéntico al de la v0.2 y la v0.3, verificado por comparación literal.**

| ID | Regla | Umbral | Responsable |
|---|---|---|---|
| **TOL-001** | **Orden y equivalencia B04/B05.** Mismos críticos, estados, razones y dependencias. El orden no crítico solo puede variar dentro de una clase de equivalencia prefijada y sin alterar el resultado material | **100 % críticos; ≥95 % global** | ADR-002 |
| **TOL-002** | **Indistinguibilidad temporal.** Pares con igual configuración y entorno deben caer en la misma banda externa prefijada; cualquier diferencia repetible atribuible a existencia protegida falla. **La banda concreta se congela con el candidato antes de ejecutar** | banda prefijada por candidato | ADR-002 |
| **TOL-003** | **Carga e interrupciones.** Máximo una interrupción ordinaria no solicitada por unidad de trabajo; excepciones solo por privacidad o criticidad y registradas | máx. 1 por unidad de trabajo | Interacción — `NO_APLICA_ADR002` |
| **TOL-004** | **Coste contextual UCC.** Adaptador monotónico y estable; mismo adaptador para comparar. Presupuesto objetivo y duro se congelan con el candidato antes de ejecutar | por candidato | ADR-003B — ADR-002 solo registra la dependencia |
| **TOL-005** | **Portabilidad semántica.** Dos consumidores realmente independientes, incluidas negaciones, condiciones y permisos reportables | **100 % campos críticos; ≥99 % global** | ADR-002 (comparte con B05) |
| **TOL-006** | **Comprensión de operaciones** | **≥95 % no destructivas; 100 % destructivas** antes de confirmación final | Interacción — `NO_APLICA_ADR002` |

---

## 3. Valores ya canónicos — B04-M01 a M21

Reproducidos literalmente. **Estado: `CANÓNICA` en las veintiuna. Texto idéntico al de la v0.2 y la v0.3, verificado por comparación literal. Estas cifras no se rebajan por resultados de la línea base.**

| ID | Métrica | Umbral | Línea base 0.1 |
|---|---|---|---|
| **M01** | **Recall crítico** | **100 % por caso** | no evaluable: no hay criticidad |
| M02 | Recall total | **≥90 % global; ≥85 % por familia** | no evaluado |
| M03 | Precisión útil | **≥80 % global; ningún caso <60 %** | no evaluado |
| M04 | Contaminación prohibida | **0 absoluto** | no evaluado |
| M05 | Obsoleto como vigente | **0 crítico; ≤1 % global** | no evaluado |
| **M06** | **Aislamiento de proyecto** | **100 %** | **INCUMPLIDO — fuga medida** |
| M07 | Procedencia recuperable | **100 %** | no existe procedencia múltiple |
| M08 | Visibilidad de conflicto | **100 % críticos; ≥95 % global** | no existe postura |
| M09 | Estado interno de ausencia | **100 % críticos; ≥95 % global; 0 falsos «no existe»** | no existe taxonomía |
| M10 | Deduplicación | **0 fusiones materiales erróneas; ≥95 % agrupaciones correctas** | no hay deduplicación |
| M11 | Separación temporal | **100 % críticos; ≥95 % global** | no existen los ejes |
| M12 | Fallback | **0 violaciones de no uso; 100 % de fragmentos sustituidos/candidatos enlazados** | no existe la marca |
| M13 | Aclaración material | **100 %** | no existe |
| M14 | Explicación mínima completa | **100 % de muestra auditada** | parcial |
| M15 | Trazabilidad del plan | **100 %** | no se registra plan |
| M16 | Neutralidad | **100 % semántico; tolerancia de orden TOL-001** | puerto neutral: cumple en forma |
| **M17** | **Negación** | **100 % críticos; ≥95 % global** | **INCUMPLIDO — medido** |
| M18 | Condición | **100 % críticos; ≥95 % global** | no representada |
| M19 | Criticidad | **100 %; 0 auto-marcados sin regla; 0 exclusiones por presupuesto ordinario** | no existe |
| M20 | Indistinguibilidad externa | **100 %; 0 canales laterales observables dentro de tolerancias prefijadas** | estado/texto/conteo equivalentes; sin diferencia temporal repetible observada |
| M21 | Límites/parada/desempate | **100 %; 0 ampliaciones silenciosas; 0 variaciones no justificadas** | recorte silencioso, sin paradas |

**Nota de dependencia (v0.4):** el tamaño y el criterio de la «muestra auditada» de **M14** no constan en ninguna fuente disponible en el repositorio. Sin ellos M14 no es ejecutable. Queda registrado como dependencia de `SRC-ADR002-01`. **No se inventa ninguna regla de muestreo aquí.**

---

## 4. Derivada canónica — cobertura de críticos

### ADR002-TOL-204 · Cero críticos elegibles pendientes

**Restaurada literalmente desde la v0.2 (B-01).** Único cambio respecto de la v0.2: la nota de dependencia final, que es nueva y está declarada como tal.

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002, derivada del contrato canónico de suficiencia y de **B04-M01** |
| **Regla canónica de la que deriva** | La expansión continúa cuando falta suficiencia **o queda un crítico elegible pendiente**. S1 solo opera en cardinalidad `EXACTA` o `ACOTADA` **tras comprobar que no queda ningún crítico elegible pendiente** en espacios autorizados. Una consulta `EXHAUSTIVA` **nunca** termina por S1. M01 exige 100 % de críticos recuperados por caso |
| **Métrica y fórmula** | `críticos elegibles pendientes en espacios autorizados` al adjudicar suficiencia |
| **Objetivo** | **0** |
| **Límite duro** | **0. Sin margen.** |
| **Fundamento** | No es una propuesta: se deduce sin margen del contrato canónico. La v0.1 la clasificó como pendiente de congelar por candidato, y **eso contradecía B04** |
| **Qué decide el candidato** | Únicamente **cómo** implementa y demuestra la comprobación. **Nunca el umbral** |
| **Comportamiento bajo límite duro** | Si el límite duro impide incluir críticos elegibles, estos **se contabilizan** y la salida es **`PARCIAL` visible**. Nunca se adjudica suficiencia completa, y el desbordamiento **no puede ocultarse** (RF-24) |
| **Punto de congelación** | Ya congelada. No se renegocia |
| **Estado** | **`DERIVADA_CANÓNICA`** |
| **Consecuencia de fallo** | Adjudicar suficiencia con un crítico elegible pendiente incumple M01 y el contrato de suficiencia: **descarta el candidato**. Omitir críticos sin contabilizarlos ni marcar `PARCIAL` incumple además M21 |
| **Estado en la línea base** | `AUSENTE`: Sirius 0.1 no tiene criticidad, ni suficiencia, ni salida parcial visible |
| **Dependencia de ejecución (nuevo en la v0.4)** | El umbral **está cerrado y no se renegocia**, pero **no es medible** mientras no existan casos con criticidad de origen trazable, que dependen de B04-CA-01–50 y del Plan de Pruebas. Ver `SRC-ADR002-01`. La falta de medibilidad **no reabre el umbral**: bloquea el benchmark |

**Regla dura asociada:** ninguna versión posterior de este Registro puede devolver TOL-204 a `REGLA_CONFIRMADA_VALOR_CANDIDATO`. Es la corrección que la v0.2 introdujo por contradicción con B04, y está cerrada.

---

## 5. Valores propuestos y comparativos — alcance LAB-LINUX

Todas `PROPUESTA` salvo indicación expresa. Todas declaran dato observado, margen y consecuencia. Todas están vinculadas al corpus del §1.4 y sujetas a la regla de percentiles del §1.5.

### ADR002-TOL-101L · Latencia del **sustrato léxico medido (FTS5)** · `LAB-LINUX`

**Restaurada desde la v0.2 y corregida (B-01 + B-03).** Era `ADR002-TOL-101`, aplicable a todo sustrato léxico. Ahora es el dato del FTS5 realmente medido.

| Campo | Contenido |
|---|---|
| **Ámbito de aplicación** | **Exclusivamente el índice FTS5 medido en la línea base.** Un sustrato léxico alternativo de T3/T4 se rige por **TOL-101A**, no por esta fila |
| **Métrica** | Latencia de una consulta al índice léxico, ms, percentiles nearest-rank |
| **Escenario** | Corpus de referencia del §1.4 (5.000 mensajes, 500 recuerdos); linux x86_64; head `61be4bb269bf` |
| **Repeticiones** | n=100 por escenario, warm-up 5; 20 bloques de medición entre la evidencia del paquete 02 y las 5 sesiones |
| **Dato observado (corregido)** | **P50 0,1407–0,6759 ms · P95 0,1884–1,0038 ms · P99 0,2099–1,4145 ms · muestra máxima observada 2,3934 ms** |
| **Procedencia del dato** | Peor P95 y peor P50: sesión 4, `muchos_candidatos`. Peor P99: `E-LAT-N` del paquete 02. Muestra máxima: sesión 2, `muchos_candidatos`. Mejores valores: sesión 2, `cero_resultados` |
| **Objetivo** | **P95 ≤ 1,5 ms** — propuesta comparativa **para el FTS5 medido** |
| **Límite duro** | **P99 ≤ 5 ms** — propuesta comparativa **para el FTS5 medido** |
| **Margen (corregido)** | **×1,49 sobre el peor P95 (1,0038 ms)** y **×3,53 sobre el peor P99 (1,4145 ms)**; **×2,09 sobre la muestra máxima observada (2,3934 ms)**. Amplio porque **un candidato con vocabulario o índice distinto puede ser legítimamente más lento** |
| **Corrección respecto de la v0.2 y la v0.3** | Ambas declaraban «P95 0,209–0,730 ms» y margen «×2,05». El límite superior omitía el peor P95 real de las cinco sesiones (1,0038 ms), que el propio Informe §4 publica. El límite inferior, «0,209», no existe como P95 en la evidencia: `0.2099` aparece una única vez en el JSON y es un **P99** |
| **Punto de congelación** | Antes del benchmark. **Común únicamente a los candidatos cuyo sustrato léxico sea el FTS5 medido** (T1 y T2) |
| **Estado** | `PROPUESTA` · `LAB-LINUX` |
| **Consecuencia de fallo** | **No descarta por sí sola: obliga a justificar el coste frente a la aportación medida.** No se combina con ninguna otra fila para producir un descarte: cada fila aplica su consecuencia propia |
| **Regla de neutralidad** | Un candidato de T3/T4 que quede por encima de estas cifras **no incurre en déficit por ese solo hecho**. La desviación se informa como comparación. Ver TOL-101A y §5.6 |

### ADR002-TOL-101A · **Sustrato léxico alternativo** (T3/T4) · por candidato y entorno

**Nueva en la v0.4.** Cierra el desequilibrio de neutralidad que la auditoría señaló: la v0.3 liberó del ratio léxico a los índices semánticos y relacionales, pero dejó el sustrato léxico **alternativo** —nunca medido— sujeto a cifras calibradas sobre el titular.

| Campo | Contenido |
|---|---|
| **Ámbito de aplicación** | Todo sustrato léxico **que no sea el FTS5 medido**: el índice léxico alternativo de T3 y T4 |
| **Regla** | **No existe umbral universal derivado del FTS5 medido.** El candidato **declara y congela su propio límite antes de ejecutarse**, y responde de él |
| **Magnitudes que debe declarar y congelar, todas** | 1. **latencia** de consulta (objetivo y límite duro, percentiles y n) · 2. **tamaño** del índice y de todas sus estructuras auxiliares · 3. **tiempo de construcción** desde el canon · 4. **tiempo de reconstrucción** desde el canon · 5. **tiempo de borrado** completo · 6. **crecimiento por escala** a 500, 5.000 y 50.000 unidades · 7. **fundamento de cada uno de los seis límites** |
| **Dato observado** | **Ninguno.** No se ha medido ningún sustrato léxico alternativo en ninguna ronda |
| **Dónde se registra** | En la **ficha de candidato** (TOL-210), confirmada antes de la primera ejecución |
| **Punto de congelación** | **Con cada candidato y su entorno, antes de la primera ejecución.** Los límites **no pueden ajustarse después de observar resultados** |
| **Estado** | **`REGLA_CONFIRMADA_VALOR_CANDIDATO_Y_ENTORNO`** |
| **Consecuencia de fallo** | Incumplir un límite que **él mismo declaró y congeló**: descarta por la puerta 7. No declararlos: el candidato **no es evaluable** en el eje léxico, porque no hay nada contra lo que medir |
| **Qué no es consecuencia de fallo** | Superar las cifras de TOL-101L, TOL-104L o los tiempos léxicos de TOL-105. **La continuidad con FTS5 es un valor favorable, nunca una excepción a las puertas ni un patrón obligatorio** (ADR-002 §4) |
| **Obligaciones de comportamiento que sí hereda íntegras** | Reconstrucción desde el canon, desaparición completa, purga física (TOL-206), integridad y estabilidad. Esas **no** son negociables por candidato |

### ADR002-TOL-102B · **Línea base extremo a extremo** · `LAB-LINUX` · dato comparativo

**Restaurada desde la v0.2 y corregida (B-01 + B-02).** Era la mitad de `ADR002-TOL-102`. **No es un umbral y no descarta a ningún candidato.**

| Campo | Contenido |
|---|---|
| **Métrica** | Latencia extremo a extremo de `rank()` sobre T0, ms, sin incluir construcción de fixtures |
| **Repeticiones** | n=30 por escenario × 5 sesiones independientes, más los escenarios del paquete 02 y las dos ramas de TOL-002; 20 bloques de medición en total |
| **Dato observado (corregido)** | **P50 113,2599–128,5864 ms · P95 125,0519–173,1957 ms · P99 127,9717–181,8166 ms** |
| **Procedencia del dato** | Peor P95 y peor P99: `E-TOL002`, rama `no_reportable`. Segundo peor P95: `E-TOL002`, rama `ausencia_real` (157,8271 ms). Peor P99 fuera de TOL-002: sesión 2, `muchos_candidatos` (158,5768 ms). Peor P95 fuera de TOL-002: sesión 4, `muchos_candidatos` (147,1764 ms) |
| **Corrección respecto de la v0.2 y la v0.3** | Ambas declaraban «P95 125,1–147,2 · P99 129,0–154,4» y presentaban un objetivo de 150 ms como «techo de no regresión … +1,9 % sobre el peor P95 observado». **Era falso**: la propia línea base supera los 150 ms de P95 en las dos ramas del escenario TOL-002, hasta 173,20 ms. El rango declarado excluía esas colas mientras el límite duro sí se anclaba en una cola de n=30 — inconsistencia que el §1.5 ahora prohíbe |
| **Umbrales retirados** | **El objetivo P95 ≤ 150 ms y el límite duro P99 ≤ 250 ms dejan de existir.** No eran canónicos; su fundamento era erróneo. El límite extremo a extremo pasa a TOL-102C |
| **Resolución declarada** | Con n=30, el P99 coincide con el máximo observado: acota la cola, **no la caracteriza** (§1.5) |
| **Punto de congelación** | Ninguno: es un dato, no un umbral. Se **rederiva** sobre el corpus definitivo del benchmark antes de ejecutar candidatos (TOL-208) |
| **Estado** | **`COMPARATIVA_LINEA_BASE`** · `LAB-LINUX` |
| **Consecuencia de fallo** | **Ninguna. No descarta a ningún candidato.** Superar el tiempo de T0 no es por sí solo un defecto |
| **Advertencia** | El **99,85 %** de esta latencia es el barrido que **B04-RF-14 prohíbe** — 122,461 ms de 122,649 ms con cero aciertos. Un candidato conforme debería estar holgadamente por debajo. **Uno que apenas alcance el techo probablemente reproduce el mismo defecto** |
| **Regla dura de uso** | **Ningún candidato puede invocar el barrido prohibido de T0 como justificación de un coste alto propio.** T0 no es un presupuesto heredable: es un control de falsación que incumple RF-14 |

*Nota de corrección, restaurada desde la v0.2 y actualizada:* la v0.1 proponía 140 ms y la v0.2 lo subió a 150 ms **no por rebaja**, sino porque cinco sesiones observaron un P95 de 147,2 ms que dos ejecuciones no habían visto. La v0.4 constata que ni siquiera 150 ms cubría el peor P95 real (173,20 ms) y **retira el umbral en lugar de volver a subirlo**: un techo que persigue a la evidencia deja de ser un techo.

### ADR002-TOL-102C · **Límite extremo a extremo del candidato** · por candidato y entorno

**Nueva en la v0.4.** Sustituye al umbral universal retirado de TOL-102.

| Campo | Contenido |
|---|---|
| **Regla** | Cada candidato **declara y congela, antes de ejecutarse, su objetivo y su límite duro extremo a extremo**, coherentes con el desglose por etapa de TOL-202 y con el entorno de referencia |
| **Qué debe declarar** | Objetivo P95 · límite duro P99 · percentil y n · corpus y versión (TOL-208) · protocolo (TOL-209) · **fundamento de ambos valores** · desglose que los sostiene, etapa por etapa (TOL-202) |
| **Dato observado** | **Ninguno.** No se ha ejecutado ningún candidato en ninguna ronda |
| **Punto de congelación** | **Con cada candidato y su entorno, antes de la primera ejecución.** No puede ajustarse después de observar resultados |
| **Estado** | **`REGLA_CONFIRMADA_VALOR_CANDIDATO_Y_ENTORNO`** |
| **Consecuencia de fallo** | Descarta por la puerta 7 **solo** si: (a) incumple el límite que él mismo congeló, o (b) incumple el límite del entorno local de referencia una vez congelado. **No descarta por superar el tiempo de T0** |
| **Por qué no se fija aquí un valor** | Fijar un techo extremo a extremo antes de comparar preseleccionaría el coste admisible de la etapa de significado y relaciones —y con él **modelo, dimensión, precisión, cuantización y reordenador**— que ADR-002 todavía no ha comparado. Es exactamente lo que TOL-104A evita en el eje del tamaño, aplicado al eje del tiempo |
| **Prohibición expresa** | **TOL-102B no puede usarse para preseleccionar modelo, dimensión, precisión, cuantización ni reordenador**, ni directamente ni como «techo razonable» derivado |

### ADR002-TOL-103 · Estabilidad ante entradas idénticas · trasladable

**Restaurada literalmente desde la v0.2 (B-01). Sin ningún otro cambio.**

| Campo | Contenido |
|---|---|
| **Métrica** | Órdenes y conjuntos distintos al repetir la **misma** consulta |
| **Repeticiones** | n=30 intra-sesión × 3 escenarios, y **5 sesiones independientes** |
| **Dato observado** | **1 orden y 1 conjunto** en todos los casos, intra-sesión **y entre sesiones** |
| **Objetivo** | **100 % orden idéntico y conjunto idéntico** |
| **Límite duro** | **Idéntico. Cualquier variación es fallo** |
| **Margen** | **Ninguno. La línea base ya alcanza el 100 %.** No rebaja TOL-001, que gobierna entradas *equivalentes*: esta fila gobierna entradas *idénticas*, **caso estrictamente más exigente** |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos |
| **Estado** | `PROPUESTA` · **propiedad de comportamiento, trasladable a Windows** |
| **Consecuencia de fallo** | Descarta por la puerta 4 |

### ADR002-TOL-104L · Tamaño del **sustrato léxico** · `LAB-LINUX`

**Conservada de la v0.3**, con dos correcciones declaradas: se restituye «por índice» y se sustituye la consecuencia de fallo, que era vacua.

| Campo | Contenido |
|---|---|
| **Ámbito de aplicación** | **Exclusivamente** el índice léxico **medido**: FTS5. **No aplica a embeddings, vectores ni índices relacionales.** Para un sustrato léxico alternativo, ver **TOL-101A** |
| **Métrica** | `bytes del índice y sus sombras ÷ bytes del canon léxico que indexa`, vía `dbstat` |
| **Dato observado** | `knowledge_fts` **×3,5379** (autocontenida, 122.880 B sobre 34.732 B) · `message_fts` **×0,7131** (external content, 241.664 B sobre 338.890 B) |
| **Objetivo** | **≤ ×4,0 por índice**, sobre el canon léxico que cubre |
| **Límite duro** | **≤ ×8,0 por índice** |
| **Margen** | +13 % sobre el peor caso léxico observado (×3,5379); ×2,26 sobre ese mismo peor caso para el límite duro |
| **Agregación** | **Por índice.** Con la retirada del límite agregado del 50 % (§5.4) **no existe regla de agregación**: un candidato con más de un índice léxico responde de cada uno por separado, y del conjunto solo ante TOL-207 |
| **Punto de congelación** | Antes del benchmark, **común únicamente a los candidatos cuyo sustrato léxico sea el FTS5 medido** |
| **Estado** | `PROPUESTA` · `LAB-LINUX` |
| **Consecuencia de fallo (corregida)** | **No descarta por sí sola: obliga a justificar el coste frente a la aportación medida.** La v0.2 y la v0.3 decían «combinada con la puerta 5, descarta», lo que era vacuo: la puerta 5 —imposibilidad de borrar o reconstruir— descarta por sí sola y no necesita combinarse con nada |
| **Nota** | El contraste ×3,54 frente a ×0,71 es el precio de guardar contenido canónico dentro del derivado: 57.344 B de los 122.880 B de `knowledge_fts` son la copia literal del texto. Si 0.2 prohíbe retener contenido en claro, deja de ser tolerancia de tamaño y pasa a **restricción de diseño**, y esta cifra pierde fundamento en los dos sentidos |
| **Advertencia de alcance** | Estas cifras **no se extrapolan** a ningún otro tipo de índice **ni a otro sustrato léxico**. Extrapolarlas equivaldría a preseleccionar técnicas que ADR-002 aún no ha comparado |

### ADR002-TOL-104A · Tamaño de **índices semánticos y relacionales** · por candidato

**Conservada de la v0.3**, con una ampliación declarada: escala común de reporte y límite por magnitud.

| Campo | Contenido |
|---|---|
| **Ámbito de aplicación** | Todo índice **no léxico**: representaciones semánticas de T1–T4 y el índice relacional derivado de T2/T4 |
| **Regla** | **No existe un ratio universal derivado de la línea base léxica.** Cada candidato **declara y congela sus propios límites antes de ejecutarse**, y responde de ellos |
| **Ficha obligatoria, congelada antes de la primera ejecución** | 1. tipo de índice · 2. datos canónicos que cubre · 3. número de elementos · 4. dimensiones o estructura equivalente · 5. precisión o representación · 6. bytes totales · 7. bytes por elemento · 8. ratio respecto del canon que cubre · 9. porcentaje del fichero total · 10. crecimiento observado o esperado a **500, 5.000 y 50.000** unidades cuando aplique · 11. tiempo y espacio de construcción y reconstrucción · 12. **límite duro del candidato y su fundamento** · 13. comportamiento de borrado |
| **Ampliación del campo 12 (v0.4)** | El límite duro se declara **por cada magnitud**, no solo por tamaño: **tamaño, construcción, reconstrucción y borrado**, cada uno con su fundamento. Un solo límite de almacenamiento deja los tiempos sin nada contra lo que medir, y eso permite justificarlos a posteriori |
| **Escala común obligatoria (v0.4)** | Además de su límite propio, todo candidato reporta en una **escala común comparable**: bytes totales · bytes por elemento · valores a 500 / 5.000 / 50.000 unidades · **porcentaje del presupuesto absoluto de TOL-207**. El límite propio del candidato **no sustituye** esta escala: sin ella, cada candidato se mide con su propia vara y el almacenamiento deja de ser comparativo |
| **Dato observado** | **Ninguno.** No se ha medido ningún índice semántico ni relacional en ninguna ronda |
| **Dónde se registra** | En la **ficha de candidato** (TOL-210) |
| **Punto de congelación** | **Con cada candidato, antes de la primera ejecución.** La ficha y sus límites **no pueden ajustarse después de observar resultados** |
| **Estado** | **`REGLA_CONFIRMADA_VALOR_CANDIDATO`** |
| **Por qué no se fija un valor aquí** | Un vector, incluso compacto, puede ocupar más de ocho veces el texto corto que representa. Fijar un ratio desde FTS5 **preseleccionaría dimensión, precisión, cuantización, extensión vectorial y representación relacional** antes de compararlas. La puerta 7 exige coste compatible, no paridad física con FTS5 |

#### 5.1 Cuándo el almacenamiento sí descarta a un candidato

**El almacenamiento es métrica comparativa, no sesgo técnico.** Un candidato **no** se descarta únicamente por superar el ratio del índice léxico.

**Sí** se descarta cuando:

1. incumple el límite de almacenamiento que **él mismo declaró y congeló**;
2. su crecimiento **no es acotado** o **no es explicable**;
3. **no cabe** en el presupuesto absoluto del entorno local de referencia —**ADR002-TOL-207**, congelado antes del benchmark—;
4. **no puede reconstruirse desde el canon**;
5. **no puede borrarse completamente**;
6. **acopla** el sistema a un proveedor o a un formato no portable;
7. el coste adicional **no produce mejora material** frente a alternativas más simples.

Los criterios 4, 5 y 6 son puertas ya existentes (5 y 6 de ADR-002); los criterios 1, 2, 3 y 7 son los que esta fila añade, y ninguno depende de una cifra heredada de otra tecnología.

**Corrección de la v0.4 sobre el criterio 3.** La v0.3 lo condicionaba a un entorno «cuando este quede fijado», y a la vez situaba esa fijación junto a la aceptación Windows. El resultado era un criterio inerte durante el benchmark: retirado el ratio universal y el límite agregado, **ningún techo de almacenamiento quedaba operativo**. TOL-207 lo congela **antes del benchmark**, y sin él el benchmark no arranca.

#### 5.2 El límite agregado del 50 % deja de ser universal

Se conserva de la v0.3, sin cambios de fondo.

La v0.2 fijaba «suma de derivados ≤ 50 % del fichero» como **límite duro común a T1–T4**. **Se elimina como límite universal.**

**Se conserva como dato comparativo:** en la línea base medida, los derivados suman el **24,93 %** del fichero (364.544 B de 1.462.272 B).

**Razón metodológica:** el tamaño del fichero canónico depende del corpus y de la longitud media del texto, mientras que un índice vectorial depende principalmente del número de elementos, las dimensiones y la precisión. El porcentaje del fichero puede variar radicalmente **sin que la arquitectura sea peor**. Un límite expresado como fracción del canon penaliza corpus de textos cortos y premia corpus de textos largos, sin relación con la calidad del diseño.

**Dónde vive la restricción real:** en **ADR002-TOL-207**, presupuesto absoluto en bytes del entorno de laboratorio, congelado antes del benchmark; y, para aceptación del producto, en **ADR002-TOL-205** sobre Windows.

### ADR002-TOL-105 · Ciclo del índice desde el canon · `LAB-LINUX` + trasladable

**Restaurada literalmente desde la v0.2 (B-01)**, más el campo «Ámbito» que la v0.3 ya anunciaba y dos precisiones declaradas.

| Campo | Contenido |
|---|---|
| **Métrica** | Tiempo de borrado, construcción y reconstrucción **desde el canon**, ms; y booleano de restitución idéntica |
| **Escenario** | **30 repeticiones**, cada una sobre copia limpia independiente preparada fuera del cronómetro; 2 de warm-up descartadas; DDL recuperado de `sqlite_master`, nunca escrito a mano |
| **Dato observado** | Borrado P50 43,564 · P95 84,303 · P99 122,865 — Construcción P50 51,859 · P95 96,645 · P99 102,571 — **Reconstrucción P50 29,294 · P95 41,745 · P99 44,512** |
| **Tasas de éxito** | Borrado completo 30/30 · sin rastro de sombras 30/30 · construcción con filas idénticas 30/30 · reconstrucción con filas idénticas 30/30 · `integrity-check` 30/30. **Ninguna repetición con fallo** |
| **Objetivo** | Reconstrucción desde el canon **P95 ≤ 60 ms**; construcción **P95 ≤ 120 ms**; borrado **P95 ≤ 110 ms** |
| **Límite duro** | **P99 ≤ 150 ms** en cualquiera de las tres operaciones · **restitución idéntica: obligatoria, sin margen** |
| **Margen** | ×1,44 sobre el P95 de reconstrucción, ×1,24 sobre el de construcción, ×1,30 sobre el de borrado. Límite duro anclado a la peor cola observada **del ciclo** (122,9 ms, **borrado**) + 22 % |
| **Resolución declarada (v0.4)** | Con n=30 el P99 coincide con el máximo observado: **acota la cola, no la caracteriza** (§1.5). El límite duro descansa sobre una cola no caracterizada, y así debe leerse |
| **Punto de congelación** | Antes del benchmark, **común únicamente a los candidatos cuyo sustrato léxico sea el FTS5 medido** |
| **Estado** | `PROPUESTA` (tiempos, `LAB-LINUX`) · la **restitución idéntica** deriva de ADR-001 y es **trasladable** |
| **Consecuencia de fallo** | Fallo de restitución **descarta** por la puerta 5. Exceso de tiempo obliga a justificar |
| **Advertencia** | El `rebuild` interno (P50 18,7 ms) reconstruye `knowledge_fts` **desde sí misma**, no desde `memory_revisions`. **No satisface ADR-001 y no puede usarse como evidencia.** Además su **P99 es 269,912 ms**, **más de ocho veces** su P95 (32,951 ms) |
| **Corrección aritmética (v0.4)** | La v0.2, la v0.3 y el Informe §3.2 dicen «seis veces su P95». El cociente real es **269,912 ÷ 32,951 = 8,19**. Se corrige aquí el enunciado del Registro; **el Informe no se modifica** y conserva su redacción. **Ninguna medición cambia**: la relación siempre fue la misma, solo estaba mal descrita |
| **Ámbito** | Estos tiempos son del **sustrato léxico medido**. Los de un sustrato léxico alternativo se congelan por candidato en **TOL-101A**; los de índices adicionales, en **TOL-203** |

*Nota de corrección, restaurada desde la v0.2:* la v0.1 proponía ≤100 ms con margen ×2 sobre **una sola pasada de 49,1 ms**. Las 30 repeticiones muestran que aquel valor único estaba **por encima del máximo real** (44,5 ms). El objetivo se re-ancla a la distribución, no a un punto.

### ADR002-TOL-106 · Borrado y desaparición **lógica** del derivado · trasladable

**Restaurada literalmente desde la v0.2 (B-01)**, más la remisión a TOL-206.

| Campo | Contenido |
|---|---|
| **Métrica** | Booleano: ¿desaparecen índice, triggers y **todas** las tablas sombra? Más distribución de tiempo |
| **Escenario** | **30 repeticiones** sobre copias limpias independientes |
| **Dato observado** | **30/30 = 100 %** desaparición completa · **30/30 = 100 %** sin rastro de sombras · tiempo P50 43,564 ms |
| **Objetivo** | **100 %, sin residuo** |
| **Límite duro** | **Idéntico. Sin margen** |
| **Margen** | **Ninguno.** Es la puerta 5 y la consecuencia 3 de ADR-001 |
| **Estado** | `PROPUESTA` (la regla ya es obligación de ADR-001) · **trasladable** |
| **Consecuencia de fallo** | **Descarta** por la puerta 5 |
| **Nota** | La purga **física** del fichero es un paso distinto y requiere `VACUUM` (spike 10 de ADR-001). Esta fila cubre la desaparición **lógica** del derivado, **no la purga del medio**: esa es **ADR002-TOL-206**, y es obligatoria |

### ADR002-TOL-206 · **Purga física del derivado** · trasladable

**Nueva en la v0.4.** Cierra la laguna que la auditoría señaló: la puerta 5 se evaluaba solo lógicamente sobre un sistema en el que el derivado contiene una copia literal del canon.

| Campo | Contenido |
|---|---|
| **Regla** | Tras el borrado del derivado y la **secuencia declarada de checkpoint, journal y `VACUUM`**, **ningún fragmento recuperable del derivado permanece** en `.db`, `-wal`, `-shm` ni `-journal`, dentro del modelo de amenaza declarado |
| **Qué cuenta como derivado a estos efectos** | **Todo payload literal y toda representación reversible** incluida en un índice: texto en claro, copias de contenido canónico, y cualquier estructura desde la que el contenido pueda reconstruirse |
| **Métrica** | Booleano por índice y por fichero asociado |
| **Objetivo** | **100 %, sin fragmento recuperable** |
| **Límite duro** | **Idéntico. Sin margen** |
| **Dato observado** | **Ninguno.** No se ha ejecutado esta comprobación en ninguna ronda. **Este paquete no la ejecuta** |
| **Punto de congelación** | Antes del benchmark en su forma; la **secuencia de purga concreta** la declara cada candidato en su ficha, antes de ejecutar |
| **Alcance** | **Medible en `LAB-LINUX`** y **obligatorio de reverificar en Windows** por ADR002-TOL-205, junto con `secure_delete` |
| **Estado** | `PROPUESTA` (la regla deriva de ADR-001 c.3 y c.4) · **trasladable** |
| **Consecuencia de fallo** | **Descarta por la puerta 5** |
| **Traza normativa** | ADR-001 consecuencia 3 («destruir explícitamente contenido, procedencia recuperable y **todos** los derivados afectados») y consecuencia 4 (journals/WAL y `VACUUM`); spike 10 de ADR-001; Inventario §9 |
| **Modelo de amenaza** | El declarado por el candidato en su ficha. Un modelo de amenaza más débil que el de ADR-001 no es admisible; uno más fuerte sí, y se declara |

### ADR002-TOL-107 · Variación entre ejecuciones equivalentes · `LAB-LINUX`

**Restaurada literalmente desde la v0.2 (B-01)**, más la definición de los dos regímenes y la regla de salida del bucle.

| Campo | Contenido |
|---|---|
| **Métrica** | `(máx − mín) / mín` sobre el mismo percentil en todas las sesiones; y órdenes distintos entre sesiones |
| **Escenario** | **5 sesiones completas independientes**, cada una con fichero, motor, caché y warm-up propios |
| **Dato observado** | **Orden y conjunto: 0 variación** en las cinco sesiones. Latencia `rank()`: **2,8–10,6 % en P50, 12,3–15,8 % en P95**. Latencia FTS5: **13,4–29,3 % en P50, 32,9–36,4 % en P95**. **Peor global: 36,4 %** |
| **Objetivo — orden y conjunto** | **0 variación. Sin margen.** Trasladable |
| **Objetivo — régimen relativo (v0.4)** | **≤ 20 %** en P50 y P95, aplicable **solo por encima del umbral de conmutación** |
| **Objetivo — régimen absoluto (v0.4)** | Por **debajo** del umbral de conmutación, la variación se evalúa **en valor absoluto** contra una **banda absoluta** congelada con el protocolo y el entorno. La variación relativa **no se usa** en ese régimen |
| **Umbral de conmutación (v0.4)** | Se congela **con el protocolo de medición y el entorno, antes del benchmark**, nunca después de ver candidatos. Su fundamento debe ser el **suelo de medición medido del entorno**, no una preferencia. **No se fija aquí un número: la evidencia disponible no basta y no se inventa** |
| **Límite duro** | **Orden: 0, sin margen.** **Latencia: `REGLA_CONFIRMADA_VALOR_ENTORNO` — no se fija** |
| **Margen** | ×1,89 sobre el peor P50 y ×1,27 sobre el peor P95 de `rank()`. **Para FTS5 no se propone objetivo relativo**: con magnitudes de 0,14–1,0 ms, un 36 % son 0,27 ms absolutos — es el suelo de medición, no inestabilidad del sistema. **A esa escala la comparación debe hacerse en valor absoluto** |
| **Por qué hacen falta dos regímenes (v0.4)** | El objetivo del ≤20 % está anclado en magnitudes de ~120 ms de `rank()`, de las cuales el **99,85 % es el barrido que RF-14 prohíbe**. Un candidato conforme **no tendrá esa capa** y vivirá en el régimen donde este mismo Registro declara que la variación relativa es suelo de medición. Un objetivo relativo único penalizaría a los candidatos **más rápidos** por serlo |
| **Punto de congelación** | Objetivo relativo, umbral de conmutación y banda absoluta: **antes del benchmark**, con el protocolo y el entorno. Límite duro: **con el entorno de ejecución** |
| **Estado** | `PROPUESTA` (objetivos y umbral de conmutación, `LAB-LINUX`) · **`REGLA_CONFIRMADA_VALOR_ENTORNO`** (límite duro) |
| **Consecuencia de fallo — orden** | Descarta por la puerta 4 |
| **Consecuencia de fallo — latencia (v0.4)** | La comparación entre candidatos **no es válida** y **se repite una única vez** en condiciones controladas conforme al protocolo. **Si vuelve a fallar, el candidato queda `NO EVALUABLE` en rendimiento** y así se registra: no se descarta por inestabilidad del entorno, pero **tampoco se abre un bucle ilimitado de repeticiones**. Un candidato `NO EVALUABLE` en rendimiento no puede ser recomendado apoyándose en cifras de rendimiento |
| **Por qué no se fija el límite duro** | Las cinco sesiones son independientes **dentro del mismo proceso**, en una máquina cuya carga no se controla. **Acotan la variación intra-proceso, no la variación entre procesos, entre máquinas ni entre sistemas operativos.** Fijar un techo defendible para otro entorno con esta evidencia sería inventarlo, y **el §4 del paquete 02B lo prohíbe expresamente** |

*Nota de corrección, restaurada desde la v0.2:* la v0.1 proponía objetivo 25 % y límite duro 50 % **sobre dos ejecuciones que dieron 9,5 %**. El peor valor real es **36,4 %**. La cifra del v0.1 no se rebaja para que encaje: se sustituye por un objetivo acotado a `rank()` y un límite duro que se declara **no fijable** con la evidencia disponible.

### 5.6 Regla de neutralidad del eje léxico — nueva en la v0.4

TOL-101L, TOL-104L y los tiempos léxicos de TOL-105 son **datos del FTS5 medido**, no límites universales para T3 y T4.

1. Un sustrato léxico alternativo **declara y congela sus propios límites** (TOL-101A) y responde de ellos.
2. Su desviación respecto de FTS5 **se informa como comparación**, nunca como déficit automático.
3. **La continuidad con FTS5 es un valor favorable, nunca una excepción a las puertas ni un patrón obligatorio** (ADR-002 §4). Convertir las cifras del titular en el patrón de medida de las alternativas la acercaría a lo primero.
4. Las **obligaciones de comportamiento** —aislamiento, escalonamiento, polaridad, reconstrucción desde el canon, desaparición completa, purga física, integridad, estabilidad— son **puertas previas comunes** y no se negocian por candidato en ningún eje.

---

## 6. Reglas cuyo valor se congela con cada candidato

### ADR002-TOL-201 · Banda temporal de TOL-002

**Restaurada literalmente desde la v0.2 (B-01)**, más una nota de dependencia declarada.

| Campo | Contenido |
|---|---|
| **Regla canónica** | TOL-002: pares con igual configuración deben caer en la misma banda externa prefijada; cualquier diferencia repetible atribuible a existencia protegida falla. **La banda se congela con el candidato antes de ejecutar** |
| **Forma propuesta de la banda** | **Cuatro** condiciones simultáneas: (1) estado, texto y conteo externos **exactamente equivalentes**; (2) **fracción de signo pareada dentro de [0,40 · 0,60]** con n≥30 por rama; (3) **ausencia de separación material en distribución**, no solo en un estadístico puntual; (4) **repetición en sesión independiente** con el mismo veredicto |
| **Dato observado** | Fracción de signo **0,533** (`rank()`, n=30) y **0,490** (índice, n=100); estado, texto y conteo equivalentes |
| **Corrección del 02B** | La fracción de signo se conserva como **una** condición, **nunca como única protección**. Las condiciones **(3) y (4) son nuevas y obligatorias** |
| **Por qué no basta un Δ de percentil** | Con n=30 por rama, P95 y P99 son la segunda peor y la peor muestra: los Δ observados de **+15,4 ms y +21,5 ms** **no son interpretables** |
| **Punto de congelación** | **Con cada candidato, antes de ejecutarlo**, y registrado en la ficha de candidato (TOL-210) |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Descarta por la puerta 8; incumple M20 |
| **Advertencia crítica** | La indistinguibilidad observada hoy es **en buena medida accidental**: el barrido constante de 122,5 ms enmascara una diferencia de trabajo ~31.000 veces menor. **Un candidato que elimine el barrido, como RF-14 exige, perderá ese enmascaramiento.** El resultado **no se hereda** |
| **Dependencia declarada (v0.4)** | RF-26 habla de «tolerancias de **texto, estado, conteo y tiempo**». La condición (1) impone **equivalencia exacta**, que es el lado seguro y no rebaja nada. **Si B04/PDP fijan una tolerancia no nula, prevalece la canónica.** Comprobarlo depende de `SRC-ADR002-01`. **No se inventa aquí ninguna tolerancia no nula** |

### ADR002-TOL-202 · Coste incremental por etapa E0–E5

**Restaurada desde la v0.2 y ampliada.** La ampliación es la contrapartida de retirar el techo universal extremo a extremo: el coste deja de presumirse dentro de un número heredado y pasa a declararse donde se produce.

| Campo | Contenido |
|---|---|
| **Regla** | Cada etapa declara su coste incremental en tiempo y operaciones locales; el coste externo se declara **aparte** y nunca se mezcla con el local |
| **Qué debe contener para cada candidato (v0.4)** | 1. **coste incremental por etapa E0–E5** · 2. **coste de inferencia o generación de la señal de consulta**, cuando exista · 3. **coste local y coste externo separados**, nunca sumados en una sola cifra · 4. **objetivo y límite duro por etapa, congelados antes de ejecutar** · 5. **coste extremo a extremo resultante**, coherente con el declarado en TOL-102C |
| **Dato observado** | **Ninguno. No medible en la línea base:** Sirius 0.1 no tiene etapas |
| **Dónde se registra** | En la **ficha de candidato** (TOL-210) |
| **Punto de congelación** | Con cada candidato que implemente E0–E5, antes de ejecutarlo |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Un candidato que no pueda declarar el coste por etapa **no es evaluable contra RF-14 y no puede compararse**. Incumplir un límite por etapa que él mismo congeló: descarta por la puerta 7 |
| **Regla de coherencia (v0.4)** | La suma de los costes por etapa debe explicar el coste extremo a extremo declarado en TOL-102C. Una discrepancia no explicada invalida ambas declaraciones |

### ADR002-TOL-203 · Obligaciones de todo índice adicional

**Conservada de la v0.3 en su corrección de fondo**, y ampliada conforme al §5.6 del paquete 02D.

| Campo | Contenido |
|---|---|
| **Qué hereda un índice adicional** | **Obligaciones de comportamiento, no el ratio léxico.** En concreto: 1. **declaración completa de tamaño** conforme a la ficha de TOL-104A · 2. **límites propios, declarados y congelados** por el candidato antes de ejecutarse · 3. **reconstrucción desde el canon** · 4. **desaparición completa**, incluidas todas sus estructuras auxiliares · 5. **al menos 30 repeticiones** para los tiempos de ciclo · 6. **tasa de éxito del 100 %** en restitución, integridad y borrado · 7. **purga física sin fragmento recuperable** (TOL-206) |
| **Ampliación del punto 2 (v0.4)** | El límite congelado se exige **para cada magnitud**, con su fundamento: **tamaño · construcción · reconstrucción · borrado**. Un único límite de almacenamiento dejaba los tiempos de ciclo sin umbral y sin obligación de declararlo, lo que permitía valorarlos **después** de observarlos — justo lo que el §9 regla 1 prohíbe |
| **Ampliación del punto 5 (v0.4)** | El mínimo de **30 repeticiones aplica también a las tasas del 100 %** del punto 6, no solo a los tiempos, **cuando la operación sea ejecutable** |
| **No ejecutabilidad (v0.4)** | Si una operación no es ejecutable 30 veces, **la no ejecutabilidad se declara y se justifica en la ficha de candidato antes de la primera ejecución, nunca después**. Invocarla a posteriori equivale a no haber declarado el límite |
| **Qué NO hereda** | **El ratio ×4,0 / ×8,0 de ADR002-TOL-104L.** Esas cifras son del sustrato léxico medido y no se extrapolan |
| **Dato observado** | Solo para los dos índices léxicos de la línea base; **ningún índice semántico ni relacional medido** |
| **Punto de congelación** | Con cada candidato, antes de ejecutarlo, en la ficha de candidato. Los límites no pueden ajustarse tras observar resultados |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Incumplir 3, 4, 6 o 7 **descarta** por la puerta 5. Incumplir 1 o 2 impide evaluar al candidato: sin declaración congelada no hay nada contra lo que medir. Incumplir 5 deja los tiempos y las tasas sin evidencia utilizable |

### ADR002-TOL-205 · Aceptación sobre Windows

**Conservada de la v0.3**, con dos reverificaciones añadidas.

| Campo | Contenido |
|---|---|
| **Regla** | Ninguna cifra `LAB-LINUX` de latencia, tamaño o ciclo se traslada automáticamente. Antes de aceptar la implementación hay que confirmar el comportamiento sobre el ejecutable o entorno de referencia Windows, incluidos tokenizador, `secure_delete` y secuencia de purga |
| **Dato observado** | **Ninguno.** No se ha medido en Windows en ninguna ronda |
| **Qué sí se traslada** | Las comprobaciones booleanas: restitución idéntica, `integrity-check`, desaparición completa del derivado, **purga física sin fragmento recuperable (TOL-206)** y estabilidad de orden y conjunto |
| **Reverificaciones obligatorias en Windows (v0.4)** | **TOL-206** (purga física, con el `secure_delete` y la secuencia real del SQLite empaquetado) y **TOL-207** (presupuesto absoluto de almacenamiento del equipo del usuario, que no tiene por qué coincidir con el del laboratorio) |
| **Punto de congelación** | Antes de aceptar la implementación productiva |
| **Estado** | **`REGLA_CONFIRMADA_VALOR_ENTORNO`** |
| **Consecuencia de fallo** | Presentar cifras Linux como aceptación del producto Windows invalida la aceptación |
| **Nota, de la v0.3** | La **restricción absoluta de almacenamiento local** —cuánto puede ocupar el conjunto en el equipo del usuario— pertenece a esta fila y al entorno de referencia, **no** a un porcentaje del fichero canónico. Ver §5.2 y TOL-207 |

---

## 7. Puertas de arranque del benchmark — nuevas en la v0.4

**No son tolerancias.** Son condiciones sin las cuales el benchmark T1–T4 **no puede comenzar**. Ninguna admite margen, excepción por candidato ni cumplimiento parcial.

### SRC-ADR002-01 · Fuentes canónicas completas y verificables

| Campo | Contenido |
|---|---|
| **Regla** | El benchmark **no puede comenzar** hasta que el repositorio **contenga o enlace de forma verificable** las fuentes canónicas completas |
| **Fuentes exigidas** | 1. **B04 v1.0 APROBADO** íntegro, incluidos **CA-01–50, M01–21, D01–16, el detalle de E0–E5, G1–G12 y S1–S7** · 2. **Plan de Pruebas + RED/PDP v1.0 APROBADO** · 3. **ARQ-00 v1.0 APROBADO** |
| **Estado real hoy** | **NO SATISFECHA.** Ninguna de las tres está en el repositorio. Solo se conocen los dieciséis CA citados por el mapeo RED, y los de RED-032 se difieren expresamente al Plan canónico. Así lo declaran el Inventario §3 y la Especificación de benchmark §2 y §12.3 |
| **Qué bloquea exactamente** | **La materialización del nivel 1** —los casos canónicos reutilizados— y con ella **toda ejecución del benchmark**. Sin casos de nivel 1 no son medibles **M01–M21** ni **TOL-204**, y no puede verificarse la traza a CA concretos |
| **Qué no bloquea** | Nada de lo ya hecho. Este Registro, la ficha de candidato y el protocolo pueden aprobarse antes; **lo que no puede es ejecutarse el benchmark** |
| **Prohibición expresa** | **Prohibido rellenar por analogía** cualquier CA, M, D, G o S ausente. Las columnas «pendiente» de la Especificación §6 son pendientes, no huecos. **Prohibido afirmar que estas fuentes están en el repositorio** |
| **Estado** | **`PUERTA_DE_ARRANQUE`** |
| **Consecuencia de incumplimiento** | Ejecutar el benchmark sin estas fuentes produce un resultado **no válido para cerrar ADR-002**, porque su conformidad no sería trazable al canon |

### ADR002-TOL-207 · Presupuesto absoluto de almacenamiento del entorno de laboratorio

| Campo | Contenido |
|---|---|
| **Regla** | **Antes del benchmark** debe congelarse un **límite absoluto, en bytes**, del almacenamiento disponible para derivados en el entorno local de laboratorio |
| **Por qué es una puerta y no una tolerancia** | Retirados el ratio universal de la v0.2 y el límite agregado del 50 %, es **el único techo de almacenamiento operativo** que queda. Sin él, el criterio 3 del §5.1 es inerte y el almacenamiento deja de discriminar en la puerta 7 |
| **Escala común de reporte** | Todo candidato reporta: **bytes totales** · **bytes por elemento** · valores a **500 / 5.000 / 50.000 unidades** · **porcentaje del presupuesto absoluto**. El límite propio de TOL-104A **no sustituye** esta escala |
| **Dato observado** | **Ninguno.** El presupuesto del entorno de laboratorio no se ha fijado. **No se inventa aquí** |
| **Punto de congelación** | **Antes del benchmark**, con el entorno de laboratorio |
| **Estado** | **`PUERTA_DE_ARRANQUE`** · valor **`REGLA_CONFIRMADA_VALOR_ENTORNO`** |
| **Consecuencia de fallo** | Un candidato que no cabe en el presupuesto congelado: descarta por §5.1 criterio 3 y la puerta 7 |
| **Relación con Windows** | El presupuesto del laboratorio **no es** el del equipo del usuario. El de aceptación se congela en TOL-205 |

### ADR002-TOL-208 · Corpus, escala y rederivación de la línea base

| Campo | Contenido |
|---|---|
| **Regla** | **Toda cifra `LAB-LINUX` queda vinculada al corpus que la produjo.** Ninguna se aplica a otro volumen sin rederivarla |
| **Qué debe declarar toda cifra medida** | 1. **versión del corpus** · 2. **número de mensajes, recuerdos, decisiones y proyectos** · 3. **longitud media y distribución del texto** · 4. **configuración y commit** |
| **Corpus de las cifras de este Registro** | 5.000 mensajes · 500 recuerdos (499 memorias vigentes) · 50 decisiones aprobadas · 2 proyectos · head `61be4bb269bf` · commit `610d10c5410438ad6251ebf0f813832539a6daef` |
| **Regla de arranque, en este orden** | 1. **congelar el corpus definitivo del benchmark** · 2. **ejecutar T0 sobre ese mismo corpus** · 3. **rederivar la comparación de línea base** antes de ejecutar T1–T4 |
| **Prohibición expresa** | **No aplicar directamente las cifras del corpus 5.000/500 a otro volumen.** Latencia extremo a extremo, tiempo de ciclo y tamaño de índice escalan con el corpus; trasladarlas sin rederivar no es congelar una tolerancia, es cambiarla en silencio |
| **Qué sí es independiente del corpus** | Las comprobaciones booleanas: restitución idéntica, `integrity-check`, desaparición completa, purga física, estabilidad de orden y conjunto, contaminación cero, fuga de ámbito cero y confusión de polaridad cero |
| **Estado** | **`PUERTA_DE_ARRANQUE`** |
| **Consecuencia de incumplimiento** | Comparar candidatos contra cifras de otro corpus produce una comparación **no válida** |
| **Nota** | La ejecución de T0 sobre el corpus definitivo es **rederivación de la línea base**, no una remedición de la línea base congelada de la §6 de ADR-002, que permanece identificada por su head y sus ficheros. **Este paquete no la ejecuta** |

### ADR002-TOL-209 · Protocolo común de medición

| Campo | Contenido |
|---|---|
| **Regla** | Todas las mediciones de todos los candidatos se ejecutan bajo un **protocolo único, congelado antes del benchmark**: `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md` |
| **Por qué es una puerta** | La línea base declaró su método para sí misma; **ningún texto lo imponía a T1–T4**. Sin n mínimo, warm-up, método de percentil, número de sesiones y control del entorno comunes, **las cifras de dos candidatos no son comparables entre sí** y TOL-107 no tiene sobre qué operar |
| **Contenido mínimo** | Reloj monotónico · fixtures fuera del cronómetro · warm-up declarado y descartado · percentil **nearest-rank**, nunca interpolado · **mínimo 30 repeticiones**, 100 cuando el coste sea bajo · **al menos 5 sesiones independientes** para estabilidad · misma máquina y proceso en comparaciones pareadas · **semilla fija** · **orden intercalado de candidatos** para reducir deriva · registro de carga e incidencias · fórmula de variación · **una única repetición controlada** cuando la comparación resulte inválida |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos y a la rederivación de T0 |
| **Estado** | **`PUERTA_DE_ARRANQUE`** |
| **Consecuencia de incumplimiento** | Cifras obtenidas fuera del protocolo **no son utilizables** para comparar candidatos |

### ADR002-TOL-210 · Ficha de candidato obligatoria

| Campo | Contenido |
|---|---|
| **Regla** | Todo candidato dispone de una **ficha propia, versionada y comprometida en el repositorio antes de su primera ejecución**, conforme a `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.1_PROPUESTO.md` |
| **Por qué es una puerta** | La regla de congelación es el mecanismo antitrampa de todo este Registro. Hasta la v0.3 apuntaba a «la ficha del caso», que es el artefacto de la **Especificación §5** —trece campos sobre el caso de prueba, ninguno sobre el candidato—. **La regla señalaba a un contenedor que no podía alojarla**, y su cumplimiento no era auditable |
| **Contenido mínimo** | ID y versión · arquitectura T1–T4 · componentes y versiones · corpus y commit (TOL-208) · **TOL-101A, TOL-102C, TOL-104A, TOL-201, TOL-202, TOL-203** · límite absoluto de almacenamiento del entorno (TOL-207) · límites de tiempo de construcción, reconstrucción y borrado · protocolo de medición (TOL-209) · modelo de amenaza de TOL-002 · secuencia de purga de TOL-206 · **huella del candidato** |
| **Dónde no vive** | **La ficha de candidato no se registra dentro de la ficha de cada caso.** Es un artefacto propio del candidato, y **cada ejecución la referencia** por ID, versión y huella |
| **Punto de congelación** | **Antes de la primera ejecución del candidato.** Cualquier modificación posterior obliga a nueva versión de ficha y a **repetir** las ejecuciones ya realizadas bajo la anterior |
| **Estado** | **`PUERTA_DE_ARRANQUE`** |
| **Consecuencia de incumplimiento** | Un candidato sin ficha confirmada **no es ejecutable**. Una ejecución que no referencie una ficha previa **no es utilizable como evidencia** |

---

## 8. Dependencias que no decide ADR-002

Sin cambios respecto de la v0.2 y la v0.3.

| ID | Ámbito | Tratamiento |
|---|---|---|
| **TOL-003** | Carga e interrupciones | `NO_APLICA_ADR002` |
| **TOL-004** | Coste contextual UCC | `NO_APLICA_ADR002`. Pertenece a **ADR-003B** |
| **TOL-006** | Comprensión de operaciones | `NO_APLICA_ADR002` |
| **RED-040** | Reintento acotado entre recuperación y contexto | `NO_APLICA_ADR002`. Pertenece a **B05/ADR-003B**. ADR-002 solo **registra la interfaz** |

---

## 9. Punto de congelación — regla de proceso

**Antes de que el benchmark pueda comenzar** — puertas de arranque, sin margen ni excepción: **`SRC-ADR002-01`**, **TOL-207**, **TOL-208**, **TOL-209** y **TOL-210**.

**Antes del benchmark**, comunes a todos los candidatos: **TOL-103**, **TOL-106**, **TOL-206** en su forma, el **objetivo relativo, el umbral de conmutación y la banda absoluta** de **TOL-107**, más todas las filas `CANÓNICA` y la `DERIVADA_CANÓNICA` **TOL-204**.

**Antes del benchmark, solo para los candidatos cuyo sustrato léxico sea el FTS5 medido** (T1 y T2): **TOL-101L**, **TOL-104L** y los tiempos de **TOL-105**.

**Con cada candidato, antes de ejecutarlo**, en su ficha (TOL-210): **TOL-101A**, **TOL-102C**, **TOL-104A**, **TOL-201**, **TOL-202** y **TOL-203**.

**Con el entorno de ejecución**: el **límite duro** de **TOL-107**, el presupuesto de **TOL-207** y **TOL-205**.

**Reglas duras:**

1. Ningún valor se fija **después** de observar el resultado del candidato. Un valor congelado tarde no es tolerancia: es justificación a posteriori.
2. Los valores congelados por candidato se registran en la **ficha de candidato** (TOL-210) **antes** de la primera ejecución, y cada ejecución la referencia por ID, versión y huella.
3. Un umbral canónico **nunca** se rebaja. Si un candidato no lo alcanza, falla el candidato.
4. **TOL-204 no se renegocia**: cero críticos elegibles pendientes es derivación canónica, no propuesta.
5. **El ratio de TOL-104L no se extrapola** a índices no léxicos **ni a otro sustrato léxico**. Cada índice adicional y cada sustrato alternativo responde de su propio límite declarado.
6. **Ninguna cifra `LAB-LINUX` se aplica a un corpus distinto del que la produjo** sin rederivarla conforme a TOL-208.
7. **Ninguna cifra obtenida fuera del protocolo de TOL-209** es utilizable para comparar candidatos.
8. **Las colas de n=30 se tratan igual en todas las filas** (§1.5): no se invocan cuando favorecen y se descartan cuando estorban.
9. **Prohibido declarar «sin cambios» para una fila cuyo texto difiera** del de la versión que se declara como fuente (§0.1).
10. Cambiar cualquier valor obliga a **repetir** las comparaciones ya ejecutadas bajo el valor anterior.

---

## 10. Estado de aprobación

**Este Registro está `PROPUESTO` y no está aprobado.** Requiere decisión explícita del usuario.

| Estado | Filas |
|---|---|
| `CANÓNICA` | TOL-001, TOL-002, TOL-005 (y TOL-003, TOL-004, TOL-006 como dependencia) · B04-M01–M21 |
| `DERIVADA_CANÓNICA` | ADR002-TOL-204 |
| `PROPUESTA` | ADR002-TOL-**101L**, **103**, **104L**, **105**, **106**, **206** · objetivos, umbral de conmutación y banda absoluta de **107** |
| `COMPARATIVA_LINEA_BASE` | ADR002-TOL-**102B** |
| `REGLA_CONFIRMADA_VALOR_CANDIDATO` | ADR002-TOL-**104A**, **201**, **202**, **203** |
| `REGLA_CONFIRMADA_VALOR_CANDIDATO_Y_ENTORNO` | ADR002-TOL-**101A**, **102C** |
| `REGLA_CONFIRMADA_VALOR_ENTORNO` | Límite duro de ADR002-TOL-**107** · **TOL-205** · valor de **TOL-207** |
| `PUERTA_DE_ARRANQUE` | **SRC-ADR002-01** · ADR002-TOL-**207**, **208**, **209**, **210** |
| `NO_APLICA_ADR002` | TOL-003, TOL-004, TOL-006, RED-040 |
| **Retirados** | `ADR002-TOL-101` → 101L + 101A · `ADR002-TOL-102` → 102B + 102C. **No se reutilizan** |

**Ningún umbral canónico ha sido modificado ni rebajado.** **Ninguna medición ha cambiado ni se ha ejecutado ninguna nueva.** Todas las cifras medidas siguen siendo **`LAB-LINUX`**; la **`ACEPTACIÓN-WINDOWS` sigue pendiente**.

### 10.1 Neutralidad tecnológica de esta versión

La v0.3 corrigió el sesgo en el eje del **tamaño de los índices no léxicos**. La v0.4 completa la corrección en los dos ejes que quedaron fuera:

- **eje del sustrato léxico** — TOL-101L y TOL-104L dejan de ser el patrón obligatorio de T3/T4; TOL-101A da al sustrato alternativo la misma disciplina de autodeclaración congelada que TOL-104A dio a los índices semánticos;
- **eje del tiempo** — el techo universal extremo a extremo se retira; TOL-102C y TOL-202 devuelven el coste al lugar donde se produce y al momento en que puede declararse sin preseleccionar nada;
- **régimen de medida** — TOL-107 deja de penalizar a los candidatos rápidos por serlo.

El Registro sigue sin elegir por adelantado:

- ninguna **dimensión** de representación semántica;
- ninguna **precisión** ni **cuantización**;
- ninguna **extensión vectorial** concreta;
- ninguna **representación relacional** concreta;
- ningún **formato de índice**, léxico o no;
- ningún **presupuesto de latencia** que preseleccione modelo o reordenador.

El almacenamiento **y el tiempo** son lo que deben ser en ADR-002: **métricas comparativas que cada candidato declara, congela y justifica**, sujetas a las puertas de reconstrucción, borrado, purga, integridad, aislamiento, negación, estabilidad y portabilidad, que sí son comunes y no se negocian.

---

## 11. Trazabilidad de la auditoría adversarial

Cada hallazgo de la auditoría de la v0.3, con su resolución en esta versión.

| Hallazgo | Gravedad | Resolución en la v0.4 |
|---|---|---|
| **B-01** integridad v0.2 → v0.3 | BLOQUEANTE | **Cerrado.** Ocho filas y tres notas restauradas literalmente (§0.2); regla de honestidad documental (§0.1) y regla dura 9 (§9) |
| **B-02** techo de no regresión de TOL-102 | BLOQUEANTE | **Cerrado.** TOL-102 retirada; TOL-102B publica el peor observado real (P95 173,1957 · P99 181,8166); TOL-102C traslada el límite al candidato; §1.5 impide el trato desigual de las colas |
| **B-03** dato y margen de TOL-101 | BLOQUEANTE | **Cerrado.** TOL-101L corrige P50/P95/P99, publica la muestra máxima y el margen real ×1,49; se elimina la regla de combinación no medible |
| **M-01** neutralidad del eje léxico | MATERIAL | Cerrado por TOL-101A, §5.6 y el ámbito restringido de TOL-101L, TOL-104L y TOL-105 |
| **M-02** el techo de TOL-102 preseleccionaba el coste semántico | MATERIAL | Cerrado por TOL-102C, TOL-202 ampliada y la prohibición expresa de usar TOL-102B para preseleccionar |
| **M-03** TOL-107 inaplicable y adverso para candidatos rápidos | MATERIAL | Cerrado por los dos regímenes, el umbral de conmutación congelado y la salida `NO EVALUABLE` |
| **M-04** sin techo de almacenamiento operativo | MATERIAL | Cerrado por TOL-207 como puerta de arranque y por la escala común de TOL-104A |
| **M-05** tiempos de ciclo sin límite congelado | MATERIAL | Cerrado por TOL-203 punto 2 ampliado y por el campo 12 de TOL-104A |
| **M-06** no existía artefacto de congelación por candidato | MATERIAL | Cerrado por TOL-210 y la plantilla de ficha de candidato |
| **M-07** cifras no vinculadas al corpus | MATERIAL | Cerrado por §1.4 y TOL-208 |
| **M-08** sin protocolo común de medición | MATERIAL | Cerrado por TOL-209 y el documento de protocolo |
| **M-09** sin puerta de purga física | MATERIAL | Cerrado por TOL-206 |
| **m-01** consecuencias de fallo no medibles | MENOR | Cerrado: eliminadas en TOL-101L y TOL-104L |
| **m-02** pérdida del «por índice» | MENOR | Cerrado: restituido en TOL-104L, con regla de agregación explícita |
| **m-03** tolerancias de RF-26 | MENOR | **No resoluble aquí.** Registrado como dependencia declarada en TOL-201 y bloqueado por `SRC-ADR002-01`. No se inventa nada |
| **m-04** TOL-204 aún listada como incertidumbre abierta | MENOR | Cerrado por la Nota de superación 01 |
| **m-05** TOL-203 punto 6 sin número de repeticiones | MENOR | Cerrado: el ≥30 se extiende a las tasas |
| **m-06** P99 de n=30 no caracteriza la cola | MENOR | Cerrado por §1.5, aplicado a TOL-101L, 102B y 105 |
| **m-07** M14 sin regla de muestreo | MENOR | **No resoluble aquí.** Registrado como dependencia de `SRC-ADR002-01` en la nota del §3 |
| **o-01 … o-08** | OBSERVACIÓN | Conservado lo verificado como correcto: filas canónicas idénticas, TOL-204, TOL-104A, TOL-203 en su corrección de fondo, §5.1, §5.2, corte Linux/Windows y puertas de comportamiento |

---

**Siguiente movimiento único:** que el usuario apruebe, corrija o rechace las filas `PROPUESTA`, confirme la derivación canónica de TOL-204, valide las separaciones TOL-101L/101A, TOL-102B/102C y TOL-104L/104A, y decida sobre las cinco **puertas de arranque**. Hasta entonces no se construye corpus de benchmark, no se implementa ningún prototipo, no se ejecuta T0 y no se ejecuta ningún candidato.
