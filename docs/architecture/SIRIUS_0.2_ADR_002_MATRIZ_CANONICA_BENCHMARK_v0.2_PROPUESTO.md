# SIRIUS 0.2 — ADR-002 · Matriz canónica del benchmark

**Versión:** 0.2
**Estado:** **PROPUESTO · NO CONGELADO** · no aprueba, no decide y no autoriza ejecutar nada
**Fecha:** 26 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_MATRIZ_CANONICA_BENCHMARK_v0.1_PROPUESTO.md`, que **se conserva sin modificar**
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_03B_CORRECCION_CORPUS_CANONICO_v0.1.md`
**Entrada adicional:** auditoría adversarial independiente del corpus v0.1 (B-01–B-04, M-01–M-07)
**Fuentes canónicas:** `docs/architecture/canonical_sources/` · huellas verificadas por el validador en cada ejecución
**Materialización ejecutable:** `experiments/adr002/benchmark/cases_v0_2.json`, `references_v0_2.json`, `pdp_cases_v0_1.json`
**No autoriza:** congelar `ADR002-TOL-208`, ejecutar T0, implementar o ejecutar `ADR002-A/B/C/D`, aprobar `ADR002-TOL-207`, satisfacer `ADR002-TOL-209` o `ADR002-TOL-210`, ni merge.

---

## 0. Qué corrige esta versión

La v0.1 fue **NO APROBABLE** en auditoría adversarial independiente. Esta versión corrige los defectos **sin rehacer el trabajo válido**: los cincuenta casos, el corpus sintético, los cinco casos arquitectónicos y las siete ablaciones se conservan y se reutilizan.

| # | Defecto de la v0.1 | Corrección en la v0.2 |
|---|---|---|
| **B-01** | Cuatro asignaciones canónicas del Anexo B perdidas y métricas canónicas ausentes | El **Anexo B se lee del DOCX**, no de una tabla escrita a mano. Lo añadido por el arnés se etiqueta `..._adicional_derivada` y **no sustituye** al canon |
| **B-02** | `congelada_por: "B04 §17/§17.1"` sobre campos que §17 no fija | Bloques `canonico` e `instanciacion` separados, con **fuente individual por campo** |
| **B-03** | Clasificación frente a T0 presentada como resultado sin haber ejecutado T0 | `estado_t0: NO_MEDIDO` en los cincuenta, más previsión con fundamento y `no_es_veredicto: true` |
| **M-01** | Ningún caso en modo `M4`; media obligación canónica sin instanciar | Ramas `M4` en `CA-09`, `CA-10`, `CA-24` y `CA-49` —**y en `CA-35`, que detectó el propio validador** |
| **M-02** | `CA-36`, `CA-47` y `CA-48` aplanados: el fallo canónico era indetectable | Tres ramas cada uno, con resultado esperado **distinto y falsable** |
| **M-03** | Ficha de caso incompleta frente al PDP §7 | Los **catorce campos** del PDP §7, leídos del DOCX, más la condición de insuficiencia por transición |
| **M-04** | Ningún `PDP-CA` instanciado | Ocho `PDP-CA` aplicables instanciados; los veinte restantes en **matriz de exclusión** con su responsable |
| **M-05** | Un solo corpus para dos objetivos incompatibles | **Dos corpus**: conformidad y rendimiento a escala `5.000 / 500 / 50` |
| **M-07** | `EXHAUSTIVA` y `S5` atribuidas al canon | Atribución retirada; solo se marca `CANONICO` lo que el texto canónico del propio caso nombra |
| menores | Comillas tipográficas sustituidas; `20/25` como cobertura | Literalidad **carácter a carácter** desde el DOCX; **cuatro denominadores** de familias, sin agregarlos |

**Lo que esta versión NO hace:** no congela nada, no ejecuta T0, no aprueba `TOL-207` —**M-06 sigue abierto**— y no satisface ninguna puerta de arranque.

---

## 1. Regla de separación: canon frente a instanciación

**El defecto B-02 era de fondo.** B04 §17 y §17.1 tienen **cinco columnas**: ID, riesgo, entrada, resultado esperado y fallo observable. La v0.1 congelaba con esa autoridad también la cardinalidad, la etapa, la parada, el orden y las listas de ids — que §17 no contiene.

Desde la v0.2, cada caso tiene dos bloques y **solo uno es canónico**:

```json
"canonico": {
  "fuente": "B04 v1.0 APROBADO §17/§17.1",
  "seccion_exacta": "B04 v1.0 APROBADO §17.1",
  "riesgo": "…", "entrada": "…",
  "resultado_esperado": "…", "fallo_observable": "…",
  "modificable": false
},
"instanciacion": {
  "fuente": "Matriz/corpus ADR-002 v0.2 PROPUESTO",
  "estado": "PROPUESTO_NO_CONGELADO",
  "cardinalidad": {"valor": "…", "fuente": "…", "estado": "DERIVADO_PROPUESTO"},
  "…": "un campo por línea, cada uno con su fuente y su estado",
  "ramas": []
}
```

**Regla de marcado**, comprobada automáticamente contra el DOCX: un campo de instanciación solo se marca `CANONICO` cuando **el texto canónico de ese mismo caso nombra literalmente el valor**. El recuento resultante es deliberadamente pequeño:

| Campo | Marcados `CANONICO` | Cuáles |
|---|---|---|
| `modo` | **6** | CA-04, CA-06, CA-09, CA-15, CA-24, CA-35 |
| `etapa` | **6** | CA-40, CA-41, CA-42, CA-43, CA-45, CA-49 |
| `parada` | **2** | CA-18 («parada S7»), CA-40 («se detiene en E1 con S1») |
| `cardinalidad` | **1** | CA-40 («Consulta EXACTA») |

Todo lo demás es **instanciación arquitectónica declarada como tal**. El bloque de instanciación es `modificable: true` mientras no se haya observado ninguna salida; después, cambiarlo está prohibido igual que el canónico (RED-004, PDP-CA-02, Registro v0.4 §9 regla 1).

---

## 2. Cardinalidad y parada: la única regla canónica que existe

B04 **no asigna cardinalidad a ningún caso** salvo CA-40, cuya entrada dice literalmente «Consulta EXACTA». Lo único que el canon fija sobre la relación cardinalidad→parada es esto, leído del DOCX en cada ejecución:

> **B04 §15.2 · EXHAUSTIVA** — Busca todos los elementos que cumplen una condición. **S1 deshabilitado.** Deben agotarse los espacios autorizados o terminar por S2–S7 con estado parcial/explicado.

**Se conserva esa regla y solo esa.** La v0.1 la aplicó bien —retiró S1 de CA-02, CA-22, CA-39 y CA-47— pero **conservó la premisa no canónica**: que esos cuatro casos fueran `EXHAUSTIVA`, que el canon nunca dice. La v0.2:

| Caso | v0.1 | **v0.2** |
|---|---|---|
| CA-02 | `EXHAUSTIVA` · `S5`, congeladas por §17 | `EXHAUSTIVA` · `S5`, **`DERIVADO_PROPUESTO`**, con la regla canónica citada como único anclaje |
| CA-22 | ídem | ídem |
| CA-47 | ídem | ídem, y ahora con **tres ramas temporales** |
| **CA-39** | `EXHAUSTIVA` · `S5` | **`null` · `null`.** Es un arnés de equivalencia entre dos realizaciones, no una consulta de recuperación: no se le impone vocabulario de parada |

Una prueba de contrato y una comprobación del validador impiden reintroducir la atribución.

---

## 3. Anexo B · las asignaciones canónicas restituidas

El Anexo B del Plan de Pruebas asigna a cada fila RED **casos y métricas exactos**. El validador lo extrae del DOCX y compara. Las cinco filas que la auditoría señaló quedan restituidas:

| Fila RED | Casos que el Anexo B le asigna | Métrica canónica | Estado en la v0.1 | **Estado en la v0.2** |
|---|---|---|---|---|
| `RED-027` | CA-01, **CA-05**, **CA-08**, CA-15 | `B04-M13`, `B04-M15` | CA-05 y CA-08 desasignadas; métricas ausentes | **Restituidas las cuatro y las dos métricas** |
| `RED-028` | CA-06, CA-07, CA-32, CA-47 | `B04-M11` | familias F02/F03 ausentes en CA-06 y CA-07 | **Restituidas** |
| `RED-029` | CA-40, **CA-44** | `B04-M15` | CA-44 desasignada; `M15` ausente | **Restituidas** |
| `RED-030` | CA-19, CA-31, CA-38 | `B04-M10` | `M10` ausente en CA-31 y CA-38 | **Restituida** |
| `RED-034` | CA-18, **CA-24** | `B04-M21` | CA-24 desasignada; `M21` ausente | **Restituidas** |
| `RED-031`, `RED-032`, `RED-033`, `RED-017` | CA-17/36 · CA-37/48 · CA-39 · CA-39 | `M09` · `M20` · `M16` · `M16` | correctas | **Sin cambios** |

**Veinte de los cincuenta CA** están nombrados por el Anexo B. Para esos veinte, la asignación canónica es obligatoria y el validador la exige. Para los treinta restantes, el Anexo B no dice nada y la traza es **enteramente del arnés**, declarada como tal.

**Lo adicional se conserva, no se borra.** Ejemplo real:

| Caso | `traza_red_canonica_anexo_b` | `metrica_canonica_anexo_b` | `traza_red_adicional_derivada` | `metrica_adicional_derivada` |
|---|---|---|---|---|
| CA-01 | `RED-027` | `B04-M13`, `B04-M15` | — | `B04-M02`, `B04-M03`, `B04-M14` |
| CA-24 | `RED-034` | `B04-M21` | `RED-015` | `B04-M04` |
| CA-44 | `RED-029` | `B04-M15` | `RED-030` | `B04-M21` |
| CA-02 | — | — | `RED-010` | `B04-M04`, `B04-M06` |

Una comprobación verifica que los dos conjuntos **no se solapan**: nada canónico puede disfrazarse de derivado ni al revés.

**Cobertura resultante:** `B04-RF-01–32` **32/32** · `B04-M01–M21` **21/21** · `RED-027–034` **8/8** · `RED-040` **nunca** como requisito propio.

---

## 4. Ramas canónicas · M-01 y M-02

Las ramas viven **dentro del mismo identificador canónico**: no se ha creado ningún CA nuevo. Diecisiete ramas en ocho casos.

### 4.1 Ramas `M4` — la mitad de la obligación que faltaba

| Caso | Rama `R1` | Rama `R2` | Cláusula canónica de `R2` |
|---|---|---|---|
| **CA-09** | `M1`: la candidata no aparece | `M4`: la candidata **sí** es visible con su estado | «Fuera de M1; **visible en M4**» |
| **CA-10** | `M1`: no se recupera como conocimiento | `M4`: muestra el estado `RECHAZADA` | «**M4 muestra estado si se pide**» |
| **CA-24** | `M1`: el resumen sin soporte queda fuera | `M4`: visible con validez `SIN_SOPORTE` | «visible en auditoría» + B04 §5 M4, que lista «**sin soporte**» |
| **CA-49** | `M3`/`E4`: evidencia atribuida con enlace | `M4`: la candidata pendiente y su origen | «candidata pendiente **visible en M4**» |
| **CA-35** | `M1`: el fallback excluye «no usar» | `M3`: inspección autorizada del fragmento | «**M3 puede inspeccionarlo si se pide**» |

**CA-35 no estaba en la lista del paquete.** La detectó el validador al comparar los modos que el canon nombra con los que el artefacto instancia. Es la prueba de que validar contra el DOCX encuentra lo que una lista escrita a mano no ve.

**Resultado:** los cinco modos `M1`–`M5` aparecen ahora al menos una vez. `M4` pasa de **0** a **4** apariciones.

### 4.2 Casos multirrama — el fallo canónico vuelve a ser detectable

**CA-47** exige que las consultas por los tres ejes temporales devuelvan resultados **distintos**, y su fallo observable es «colapsa las tres fechas en "más reciente"». Con un solo elemento eso era indetectable por construcción. Se añaden dos anclajes —`DEC-014` y `DEC-015`, declarados con su motivo— para que los tres ejes den tres conjuntos distintos:

| | `occurred_at` | tiempo válido | `recorded_at` |
|---|---|---|---|
| `DEC-011` | 2026-01-12 | desde 2026-02-01 | 2026-03-08 |
| `DEC-014` | 2026-03-05 | 2026-01-15 → 2026-01-31 | 2026-01-20 |
| `DEC-015` | 2026-01-20 | desde 2026-03-01 | 2026-01-25 |
| **Rama** | `R1` ocurrido en enero → **{011, 015}** | `R2` válido el 20-01 → **{014}** | `R3` corte 15-02 → **{014, 015}** |

Tres conjuntos distintos: **ningún sistema que colapse los tres ejes puede producirlos.**

**CA-36** pasa a tres ramas con estado seguro interno distinto —`SOLO_HISTORICO`, `SOLO_CANDIDATA`, `FUERA_DE_AMBITO`—, de modo que devolver «no hay nada» a las tres, que era exactamente el fallo canónico, ya no pasa.

**CA-48** pasa a tres ramas: autorizada (el contenido restringido existe), no autorizada (`NO_REPORTABLE`) y **ausencia real** (`NINGUNO_EN_AMBITO`). Las dos últimas comparten la **misma tolerancia pendiente** declarada, porque la banda de indistinguibilidad de `RF-26`/`RED-032` **no está congelada**: se registra la dependencia, no se inventa la banda.

---

## 5. Ficha obligatoria del caso · PDP §7

El PDP §7 fija **catorce campos**, y la v0.1 no instanciaba cuatro: `Objetivo`, `Unidad de trabajo`, `Tolerancias` y `Señales observables`. La Especificación §5 campo 12 exigía además la **condición de insuficiencia por transición**, que tampoco estaba.

Los catorce se leen del DOCX y se comparan con el esquema. Cada campo declara **fuente** y **estado**:

| Estado | Significado | Ejemplo |
|---|---|---|
| `CANONICO` | Tomado literalmente del canon | `entrada`, `fallo` |
| `DERIVADO_PROPUESTO` | Decisión del arnés, declarada | `objetivo`, `unidad_de_trabajo`, `senales_observables` |
| `PENDIENTE_TOL209` | **Falta un valor que solo puede congelar el entorno** | `tolerancias` de CA-37, CA-39 y CA-48 |

**No se inventa ninguna banda.** Las tres tolerancias pendientes citan su dependencia exacta:

| Caso | Tolerancia | Dependencia declarada |
|---|---|---|
| CA-37, CA-48 | Banda de texto, estado, conteo y tiempo entre ausencia real y no reportable | `RED-032` · `B04-RF-26` · `ADR002-TOL-209` |
| CA-39 | Clase de equivalencia de orden entre implementaciones | `RED-033` · `ADR002-TOL-209` |

La condición de insuficiencia se declara **por transición**, no en bloque: un caso que resuelve en `E4` declara las cuatro transiciones `E0→E1 … E3→E4` con la condición que autoriza cada una. Es lo que la puerta 9 —salto a recuperación amplia— necesita para adjudicarse.

---

## 6. Clasificación frente a T0 · B-03

**Desaparece todo veredicto.** La v0.1 declaraba «3 pasan / 6 fallo esperado / 5 fallo duro / 36 no expresables» sin haber ejecutado T0, y aplicaba el criterio de expresabilidad de forma incompatible entre casos que comparten RF.

Cada caso lleva ahora:

```json
"t0": {
  "estado_t0": "NO_MEDIDO",
  "expresabilidad_prevista": "…",
  "fundamento_de_prevision": "…",
  "estado_por_requisito": {"B04-RF-12": "AUSENTE"},
  "ejes_inseguros_medidos": [],
  "no_es_veredicto": true
}
```

**Criterio único**, aplicado sin excepción: si **alguna** dimensión requerida está `AUSENTE` en la línea base, el caso es `NO_EXPRESABLE_PREVISTO` —un resultado coincidente no demostraría conformidad—; si alguna es `PARCIAL`, `PARCIALMENTE_EXPRESABLE_PREVISTO`; si todas existen, `EXPRESABLE_PREVISTO`. Los ejes `INSEGURO` medidos se registran aparte, sin alterar la previsión.

| Previsión | Casos | Cambio respecto de la v0.1 |
|---|---|---|
| `EXPRESABLE_PREVISTO` | **5** — CA-03, CA-20, CA-21, CA-25, CA-43 | La v0.1 decía «pasan 3»: CA-04, CA-11 y CA-39 |
| `PARCIALMENTE_EXPRESABLE_PREVISTO` | **14** — incluye CA-02, CA-11, CA-24, CA-38, CA-45 | CA-11 baja de «debería pasar» a parcial: purgado y «no guardado» **no existen** en 0.1 |
| `NO_EXPRESABLE_PREVISTO` | **30** — incluye CA-01, CA-04, CA-09, CA-10 | CA-04 baja de «debería pasar»: `RF-12` está `AUSENTE`, igual que en CA-09 y CA-10 |
| `NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION` | **1** — **CA-39** | Deja de figurar como «debería pasar»: exige **dos** realizaciones |

**Ninguna de estas cifras es un resultado.** La clasificación real solo se crea tras ejecutar T0 sobre el corpus congelado, y `ADR002-TOL-208` sigue **NO SATISFECHA**.

---

## 7. PDP-CA · M-04

Los veintiocho casos transversales del Plan se extraen del DOCX y se clasifican **sin hueco ni solapamiento**. Dos criterios, ambos citables:

| Criterio | Definición |
|---|---|
`ANEXO_B_RED_CON_CASO_O_METRICA_DE_B04` | El Anexo B lo asigna en una fila que cita un caso `B04-CA` o una métrica `B04-M`
`DISCIPLINA_DE_CONGELACION_IMPORTADA_POR_ADR002` | Un artefacto **aprobado** de ADR-002 importa su regla de forma expresa

### 7.1 Los ocho aplicables, instanciados como nivel 1

| PDP-CA | Criterio | Anclaje |
|---|---|---|
| **PDP-CA-09** | Anexo B | `RED-017` → `B04-CA-39` · `B04-M16` · F22 |
| **PDP-CA-22** | Anexo B | `RED-017` → `B04-CA-39` · `B04-M16` · F22 |
| **PDP-CA-02** | Disciplina | Registro v0.4 §9 regla 1 · Especificación §3 principio 2 |
| **PDP-CA-03** | Disciplina | Protocolo de medición §6.5, §6.6 y prohibición 8 |
| **PDP-CA-06** | Disciplina | `ADR002-TOL-210` · congelación antes de la primera ejecución |
| **PDP-CA-16** | Disciplina | Protocolo de medición §7 · registro obligatorio |
| **PDP-CA-17** | Disciplina | Registro v0.4 §9 reglas 1 y 10 |
| **PDP-CA-18** | Disciplina | `ADR002-TOL-107` · `NO EVALUABLE` permanece en el denominador |

Su texto canónico se reproduce **carácter a carácter** y se verifica contra el DOCX.

### 7.2 Los veinte excluidos, con responsable

`PDP-CA-01`, `04`, `05`, `07`, `08`, `10`, `11`, `12`, `13`, `14`, `15`, `19`, `20`, `21`, `23`, `24`, `25`, `26`, `27`, `28`. Cada uno registra las filas RED que lo asignan, sus familias, el destino expandido desde ARQ-00 §20 y el motivo de la exclusión.

**No se afirma cobertura de los 304 casos del Plan** (276 heredados + 28 transversales). El artefacto lo declara expresamente.

---

## 8. Familias PDP · cuatro denominadores, ninguno agregado

La v0.1 declaraba «20/25 con los tres niveles» como cobertura. **No existe una sola cifra de cobertura de familias de ADR-002.** Se reportan cuatro y no se suman:

| # | Denominador | Familias | Fuente |
|---|---|---|---|
| **1** | **Destino directo de ADR-002** | **7** — F01, F02, F03, F10, F15, F22, F23 | ARQ-00 §20, columna Destino, leída del DOCX |
| **2** | Entradas obligatorias declaradas | **13** — F01–F06, F10, F11, F14, F15, F22, F23, F24 | ADR-002 v0.3 §2 |
| **3** | Tocadas por casos, **sin atribuir cierre** | **20** | Instanciación del arnés |
| **4** | Fuera del alcance de ADR-002 | **18**, con su responsable expandido | ARQ-00 §20 |

El denominador **1** es el canónico. El **3** es el que la v0.1 presentaba como cobertura: incluye siete familias que ARQ-00 asigna a ADR-001, ADR-003A, ADR-003C o ADR-004. Que un caso canónico toque una familia **no la cierra ni la atribuye a ADR-002**: el mínimo canónico del PDP §8 exige ejecutar todos sus casos asignados del banco de 304, más un caso positivo, uno negativo y uno adversarial distintos.

Una comprobación impide que reaparezca la cifra `20/25` como cobertura.

---

## 9. Los tres niveles y los dos corpus

| Nivel | Contenido | Recuento | Corpus |
|---|---|---|---|
| **1 · canónicos B04** | `B04-CA-01`–`CA-50`, exactamente una vez cada uno | **50**, con **17 ramas** | conformidad |
| **1 · canónicos PDP** | Los ocho `PDP-CA` aplicables | **8** | conformidad |
| **2 · arquitectónicos** | `ARQ-CA-01`–`05`, conservados de la v0.1 sin cambios | **5** | conformidad |
| **3 · ablaciones** | `AB-0`–`AB-6`, conservadas de la v0.1 sin cambios | **7** | ambos |

Las ablaciones **no llevan ficha de caso del PDP §7**: el canon dice que nunca producen veredicto de conformidad, y por tanto no son unidades de caso.

**Nota sobre `AB-3` y `AB-4`:** no son aplicables a `ADR002-A`, que no tiene señal tardía adicional que desactivar. Esa no aplicabilidad **no penaliza** al candidato.

---

## 10. Lo que esta matriz no hace

- No congela nada. Los seis artefactos declaran `PROPUESTO_NO_CONGELADO`.
- **No ejecuta T0** ni `ADR002-A/B/C/D`. No mide nada.
- **No aprueba `ADR002-TOL-207`.** El hallazgo **M-06** sigue abierto.
- **No declara satisfechas `ADR002-TOL-208`, `ADR002-TOL-209` ni `ADR002-TOL-210`.**
- No modifica los artefactos v0.1, `docs/architecture/canonical_sources/`, `src/`, `tests/`, `migrations/` ni configuración productiva.
- No sustituye `B04-CA-01–50` ni el PDP, y no crea referencias que los contradigan.
- No reabre B04-B, `E0–E5`, `G1–G12` ni `S1–S7`, ni la partición `ADR002-A/B/C/D`.
- No elige entre candidatos ni propone modelos, extensiones ni fórmulas de fusión.

---

**Siguiente movimiento único:** que el usuario revise esta corrección y decida si el corpus de conformidad puede congelarse. Congelarlo es el primer paso de `ADR002-TOL-208`; los dos siguientes —ejecutar T0 sobre él y rederivar la comparación— siguen sin autorización.
