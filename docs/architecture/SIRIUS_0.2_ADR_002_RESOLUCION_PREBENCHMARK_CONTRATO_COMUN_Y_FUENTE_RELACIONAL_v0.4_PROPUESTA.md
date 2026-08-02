# SIRIUS 0.2 · ADR-002 · Resolución pre-benchmark · v0.4

## Contrato común experimental y fuente relacional admisible de ADR002-C

**Estado:** **PROPUESTA · PENDIENTE DE APROBACIÓN EXPLÍCITA DEL USUARIO**
**Versión:** v0.4
**Sustituye documentalmente a:** `..._v0.1_PROPUESTA.md` (blob `727e02ed6b7f0e750d4877a8d10bd171afbf4d5a`), `..._v0.2_PROPUESTA.md` (`82c2bcc06bbee2f39ca58f0f921fcf9e1ee49eb6`) y `..._v0.3_PROPUESTA.md` (`e649a7f8719c4da5d576002b14b1f8d80618c613`). **Las tres se conservan íntegras.**
**Preinscrita por:** `..._PAQUETE_RESOLUCION_05_..._v0.4.md`
**Rama de trabajo:** `claude/adr002-tol209-forensic-audit-i0ui8k` · **HEAD de partida:** `71e759b19ceb00d5e7c22f609ded974e86d08bc5`

> **No está aprobada.** No autoriza implementación, fichas sucesoras, corpus, fe de erratas, benchmark, fast-forward ni fusión.

---

## 0. Convención de tiempo verbal, que esta versión respeta sin excepción

La v0.3 mezclaba hechos y requisitos. Aquí se separan siempre:

| Marca | Significado |
|---|---|
| **HOY** | Comportamiento **actual verificado** sobre el árbol de `71e759b`, con su anclaje |
| **DEBERÁ** | **Requisito aprobado para la futura corrección**. No describe nada que exista |

Ninguna afirmación en presente sin anclaje. Ningún requisito futuro escrito como hecho.

---

## 1. Materia que esta versión no reabre

**`ADR002-C` · fuente relacional: ADMISIBLE PERO FUNCIONALMENTE INSUFICIENTE sobre el corpus v0.4.**

Se conserva **provisionalmente**. No se han repetido las sondas generales de suficiencia relacional.

**Única vía de condicionamiento admitida:** el cambio futuro de `subject_key_experimental`, registrado en la v0.3 y conservado en §6. La justificación que la v0.2 dio a su proyección de sonda era falsa —ver §6.1—, de modo que la conclusión **no está reforzada «a fortiori» por la proyección, sino condicionada a ella**. Eso no la reabre aquí: la deja condicionada, y §12 lo lleva a decisión.

---

## 2. Qué corrige esta versión

| # | Defecto de la v0.3 | Corrección |
|---|---|---|
| **B1** | La tabla de auditoría certificaba «el grupo es atómico», regla que el cuerpo retiraba | §7.7 regla 5 y §11.2 tesis 21 **coherentes**: el grupo **no** es atómico; y §7.8 separa lo que `G12` hace HOY de lo que **deberá** hacer |
| **B2** | La tabla de la familia reintroducía «por ítem agrupable» y la custodia por ítem | §8.1: solo el **valor lateral** por ítem, custodia en el manifiesto, sin conjunto circular |
| **M1** | La lista negra remitía en bloque a la v0.2 §9.2, reimportando una prohibición ya levantada | §5.3: lista **efectiva y autocontenida**, sin remisiones históricas |
| **M2** | Publicaba el rango inexistente `MEM-001…MEM-079` | §6.1: censo real, con la conclusión limitada que sí resiste |
| **M3** | Atribuía a la v0.2 un control fallo-abierto que la v0.2 no contiene | §5.8: atribución corregida a su origen real |
| **M4** | Confinaba la discrepancia del sustrato léxico a `T0` | §9: inventario completo, auditoría ejecutada y adjudicación |
| **H1** | `subject_key_experimental` clasificado como «solo `common`» pese a que `A` lo consume | §5.7: categorías por **(campo, consumidor, uso)** |
| **H2** | Los campos de criticidad segura clasificados como «solo `common`» pese a ir a B05 | §5.7: capacidad **`HANDOFF_A_B05`** |
| **H3** | El mapeo de `fuente_de_politica` descrito como derivado de la razón | §4.6: dominio y evaluación descritos con honestidad |
| **H4** | Numeración huérfana en la tabla de tesis resistentes | §11.2: cada tesis cita su hallazgo |
| **H5** | «19 razones de política» sin distinguir instancias de valores | §4.3 y §4.9: 19 instancias, **8 valores distintos** |
| **H6** | Un control negativo lógicamente redundante | §3.2: declarado, con su alcance real |
| **H7** | Sin declarar si el verificador acumula o aborta | §3.2: **acumula**, y §3.3 lo usa con esa semántica |
| **H8** | Citas «literales» con elisiones no marcadas | Toda elisión lleva `[…]` |
| **H9** | El paquete presuponía un arnés de conformidad de `T0` | §8.3 y el paquete §6 `P-I3`: no se presupone |

Todo lo demás de la v0.3 se conserva y se reproduce aquí de forma autocontenida.

---

## 3. Recuento exacto de criticidad

### 3.1 Cifras sobre el blob congelado `c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48`

| | |
|---|---|
| Ítems totales | **95** |
| `criticidad: null` | **76** |
| `criticidad` no nula | **19** |
| de ellos, `nivel: CRITICO` | **18** |
| de ellos, `nivel: IMPORTANTE` | **1** |

### 3.2 El verificador del corpus v0.4: semántica declarada

**Acumula todos los fallos y no aborta en el primero.** Comprueba el blob del corpus y, con independencia del resultado de esa comprobación, evalúa los cuatro predicados y emite todos los que fallen.

| # | Predicado | ¿Independiente? |
|---|---|---|
| a | la suma es 95 | **sí** |
| b | los no nulos son 19 | **sí** |
| c | la distribución es `{CRITICO: 18, IMPORTANTE: 1}` | **sí** |
| d | ningún nivel fuera del inventario | **NO — redundante** |

**El predicado (d) está lógicamente implicado por (b) ∧ (c)**: si los no nulos son 19 y hay 18 más 1, el conjunto queda agotado y no cabe un nivel ajeno. **No puede fallar solo.**

Se **conserva** como defensa en profundidad, con su alcance declarado: dejará de ser redundante en la familia sucesora, donde las constantes se rederivan y (b) y (c) tomarán otros valores. **No se presenta como un cuarto predicado independiente.**

**Alcance de las constantes:** `95 / 76 / 19 / 18 / 1` y el blob son **específicos de la v0.4**. La familia sucesora **deberá** llevar **su propio censo, con sus propias constantes recomputadas y congeladas en su acta**.

### 3.3 Controles negativos, con la semántica de §3.2

Ejecutados sobre copias mutadas **fuera del repositorio**; **el corpus congelado no se tocó**. Toda mutación cambia el blob, de modo que **cada control dispara además el fallo de blob**; se listan los fallos de recuento, que son los que aíslan el poder discriminante:

| Mutación | Fallos de recuento emitidos |
|---|---|
| quitar un ítem | «la suma no es 95: 94» **y** «nulos + no nulos no suma el total» |
| anular la criticidad de los `CRITICO` | «los no nulos no son 19» **y** «la distribución no es 18/1» |
| mover un `CRITICO` a `IMPORTANTE` | «la distribución no es 18/1: {IMPORTANTE: 2, CRITICO: 17}» |
| introducir un nivel `URGENTE` | «la distribución no es 18/1» **y** «nivel no inventariado: ['URGENTE']» — **nunca el segundo solo**, conforme a §3.2 |

Los tres predicados independientes fallan cuando deben. El verificador **no es vacuo**.

---

## 4. Contrato de criticidad de extremo a extremo

### 4.1 Requisito canónico

> **`B04-RF-23` (línea 441):** «Propagar **nivel, razón, fuente y regla aprobada** de criticidad **hasta B05**; prohibir auto-marcado libre y exclusión por presupuesto ordinario.»
>
> **`B04-M19` (línea 525):** «Criticidad controlada y propagada | Marcas con **fuente/regla aprobada y razón intactas B04→B05**. | 100%; 0 auto-marcados sin regla y 0 exclusiones por presupuesto ordinario.»
>
> **`B04-D05` (línea 535, APROBADA):** «La criticidad exige **fuente o regla aprobada** y cruza a B05; B05 no puede excluirla por presupuesto ordinario, solo por límite duro o elección explícita por petición con estado parcial.»
>
> **`B04-Q21` (línea 414):** «La criticidad procede de **requisito/decisión aprobada, acto explícito, etiqueta de escenario o regla operativa aprobada con ID y evidencia**. […]»
>
> **`B04` §7 (línea 230):** «Criticidad | Nivel, razón y fuente de clasificación para cada resultado; **debe sobrevivir intacta al handoff a B05**.»

**Propagar solo el nivel incumple el contrato.**

### 4.2 Divergencia interna de B04, declarada

| Lugar | Enumeración | ¿Etiqueta del corpus? |
|---|---|---|
| Glosario, línea 186 | «instrucción explícita, requisito/decisión aprobada o clasificación operativa trazable» — tres | **no** |
| §6, líneas 215-219 | explícito del usuario · documento o decisión aprobada · clasificación operativa · **adjudicación de prueba** — cuatro | **sí** |
| `Q21`, línea 414 | requisito/decisión aprobada · acto explícito · **etiqueta de escenario** · regla operativa aprobada — cuatro | **sí** |

**Se adopta la de `Q21`**, por ser la respuesta aprobada a la pregunta que gobierna directamente esta materia («¿Quién clasifica la criticidad en ejecución, con qué evidencia y cómo se corrige?», línea 273), por coincidir con §6 y por ser la única que fija el requisito de **ID y evidencia**.

### 4.3 Qué porta el oráculo — HOY, verificado campo a campo

| Campo bruto | Valores observados sobre el blob | ¿Identificador de caso? |
|---|---|---|
| `criticidad.nivel` | `CRITICO` ×18, `IMPORTANTE` ×1 | **no** |
| `criticidad.razon` | **19 instancias, 8 valores distintos** (12 comparten «Restricción esencial etiquetada por el corpus antes de ejecutar.»); **0 contienen identificador** de caso ni de ítem | **no** |
| `criticidad.regla` | `CRIT-01`…`CRIT-07` (12× `CRIT-06`, 2× `CRIT-07`) | **no** — identificadores de **regla de política** |
| `criticidad.fuente` | 8 valores: `B04-CA-01`, `B04-CA-02`, `B04-CA-20`, `B04-CA-21`, `B04-CA-42`, `B04-CA-45`, `REGLA-CRIT-07`, y ×12 «Instanciación compartida por B04-CA-26, B04-CA-38 y B04-CA-44» | **SÍ — el único** |

### 4.4 Plano A · Metadato bruto del arnés — PROHIBIDO

**`criticidad.fuente` en bruto no viaja.** No puede ser consumido por `ADR002-A`, `B`, `C` ni `D`, ni por el motor **como señal**, ni por índices, ranking, expansión o construcción de candidatas. Permanece privado del arnés.

### 4.5 Plano B · Criticidad aplicada segura

```
CriticidadAplicada(
    nivel,                 # conforme al vocabulario de niveles P2
    razon_segura,          # = criticidad.razon, verbatim
    fuente_de_politica,    # producida por la regla cerrada de §4.6
    regla_de_politica,     # = criticidad.regla, verbatim (CRIT-0x)
)
```

| # | Requisito |
|---|---|
| 1 | No contiene identificadores de casos |
| 2 | No contiene resultados esperados |
| 3 | No contiene referencias a `A`/`B`/`C`/`D` |
| **4a** | **No procede de la adjudicación de resultados del banco** — elegibles, prohibidos, resultados esperados ni grupos esperados |
| **4b** | **Sí puede proceder de una etiqueta de escenario** en el sentido de `Q21` y `§6`. `4a` y `4b` no se contradicen: prohíben la adjudicación del **resultado**, no la etiqueta del **escenario** |
| 5 | Su asignación **deberá** quedar congelada antes de ejecutar candidatos |
| 6 | Se construye por la regla cerrada de §4.6 |
| 7 | Un nivel **no podrá** autoasignarse durante la recuperación |
| 8 | Un validador **deberá** fallar cerrado si algún valor de `razon_segura` o `regla_de_politica` coincidiera con un patrón de identificador de caso. HOY ninguno coincide; el control es **preventivo** para familias sucesoras |

**Usos permitidos:** `G12`; tratamiento previo al límite; **desempate estable y registrado, y razón de orden por resultado**; estado `PARCIAL` por desbordamiento crítico; explicación autorizada; traspaso a B05.

> El desempate no es concesión: `B04` M-05 (línea 46) lo fija «[…] por **criticidad**, autoridad, ajuste temporal, apoyo directo y ID estable […]»; `RF-28` (línea 446) exige explicar «[…] **criticidad y razón de orden**»; `M21` (línea 527) lo mide. **HOY** el motor común ya lo implementa en `engine.py:66-75`.

**Usos prohibidos:** generar candidatas; aumentar similitud; alterar `E0-E4`; saltar etapas; **rescatar un elemento que no haya pasado las puertas** —`B04` §11, línea 307: «[…] **Ninguna señal blanda puede rescatar un elemento excluido**»—; favorecer a un candidato.

### 4.6 Regla cerrada de `fuente_de_politica` — descrita con honestidad

**Dominio:** `criticidad.fuente` **bruta**, que es campo prohibido de viajar (§4.4).
**Evaluación:** **dentro del arnés**, y **deberá** quedar congelada antes de ejecutar candidatos (§4.5 requisito 5).
**Codominio:** el vocabulario de `B04-Q21`.
**Qué cruza al canal común:** **solo el resultado seguro**, nunca el dominio.

La razón de política de cada ítem se cita como **justificación** de cada asignación, no como su dominio:

| `criticidad.fuente` bruta | n | `fuente_de_politica` | Justificación (razón del ítem) |
|---|---|---|---|
| `B04-CA-01`, `B04-CA-02`, `B04-CA-20`, `B04-CA-21` | 4 | `ACTO_EXPLICITO` | requisitos y restricciones declarados por el usuario |
| `B04-CA-42`, `B04-CA-45` | 2 | `REQUISITO_O_DECISION_APROBADA` | restricción tecnológica aprobada; límite de gasto vigente |
| «Instanciación compartida por B04-CA-26, B04-CA-38 y B04-CA-44» | 12 | `ETIQUETA_DE_ESCENARIO` | «Restricción esencial etiquetada por el corpus antes de ejecutar.» |
| `REGLA-CRIT-07` | 1 | `REGLA_OPERATIVA_APROBADA` | detectada por regla operativa aprobada |

**Requiere aprobación explícita** (§12) y **deberá** congelarse en el acta de la familia sucesora.

### 4.7 Plano C · Handoff a B05

El contrato entregado a B05 conserva **íntegramente** `nivel`, `razon_segura`, `fuente_de_politica` y `regla_de_politica`.

### 4.8 Cómo se satisfacen `RF-23`, `M19`, `D05` y `Q21`

| Exigencia | Cómo se satisface | Cómo se evita el oráculo |
|---|---|---|
| **nivel** hasta B05 | Se transporta conforme al vocabulario de niveles P2 de §8.1, sin reinterpretación semántica | No identifica ningún caso |
| **razón** intacta | `criticidad.razon` **verbatim** | 0 de 19 contienen identificador |
| **fuente** | `fuente_de_politica`, del vocabulario de `Q21` | El identificador de caso no viaja |
| **regla aprobada** | `criticidad.regla` **verbatim** (`CRIT-0x`) | Es identificador de **política** |
| **«con ID y evidencia»** (`Q21`) | **ID** = `regla_de_politica`; **evidencia** = `razon_segura` | Ninguno es etiqueta de banco |
| «0 auto-marcados sin regla» | Asignación congelada antes de ejecutar; ninguna etapa podrá crear un nivel | Requisitos 5 y 7 |
| «0 exclusiones por presupuesto ordinario» | Un crítico solo caerá por puerta o por límite duro declarado | `RF-24` y §7 |

### 4.9 Lo que se pierde, declarado

1. **La trazabilidad hasta el caso del banco no llega a B05.** Deliberado: `RF-23` pide procedencia de política, y `Q21` satisface su ID con `CRIT-0x`. Queda en la traza privada del arnés.
2. **`fuente_de_politica` es un enum de cuatro valores** donde **12 de los 19** ítems comparten uno.
3. **`razon_segura` tiene 8 valores distintos sobre 19 instancias**, y 12 comparten el mismo. La «evidencia» que `Q21` pide es **idéntica para 12 de los 19 ítems**, de modo que su poder de auditoría es menor de lo que la literalidad de `M19` sugiere.
4. **Ningún otro campo se transforma.** `razon` y `regla` viajan verbatim: «intacta» es literal.

### 4.10 Consecuencia para la implementación

**HOY** el contrato común define `Criticidad` con **dos** valores, `ORDINARIA` y `CRITICA` (`contracts.py:99-104`), y sus consumidores comparan solo contra `CRITICA` (`gates.py:216-222`, `stops.py:59`). **El nivel `IMPORTANTE` sería indistinguible de `ORDINARIA`.**

El paso de corrección de `common/` **deberá** ampliar el vocabulario de niveles y revisar `G12` y la parada por críticos pendientes.

---

## 5. Fuente y custodia de `property_key`

### 5.1 Dónde vive

**`property_key` NO será campo del registro de ítem, ni de `ItemCanonico`, ni de ninguna estructura que el puerto entregue a un candidato.** Vivirá en una **tabla lateral de la proyección experimental, indexada por identidad canónica**, que **solo `common` abrirá**. Un candidato no podrá leerla porque **no la recibirá**.

### 5.2 Custodia: manifiesto de familia

| Campo de custodia | Dónde vive |
|---|---|
| `fuente_de_asignacion` | manifiesto de la familia, **una sola vez** |
| `version_del_vocabulario` | manifiesto de la familia, **una sola vez** |
| `regla_de_validacion` | manifiesto de la familia, **una sola vez** |

**Por ítem existirá únicamente el valor lateral de `property_key`, `null` incluido.** Los metadatos de custodia por ítem estarían correlacionados con la partición que la clave induce y darían esa partición por una puerta trasera.

### 5.3 Lista negra efectiva y autocontenida

**No se remite en bloque a ninguna clasificación anterior.** Esta es la lista vigente, y refleja la clasificación de §4.3:

**PROHIBIDO como origen de `property_key` y como entrada de cualquier candidato:**

- `criticidad.fuente` **bruta**;
- `items[].traza`;
- `relaciones[].nota`;
- `entidades[].nota` y `entidades[].grupo_homonimo`;
- `documentos[].traza` y `mensajes[].traza`;
- `cases_v0_4.json` y `references_v0_4.json` **completos**;
- adjudicaciones, resultados esperados, elegibles, prohibidos, grupos esperados, etapas esperadas y paradas esperadas;
- etiquetas `A`/`B`/`C`/`D` de candidato;
- cualquier proyección de `T0`.

**NO prohibido, conforme a la inspección de §4.3:** `criticidad.razon` y `criticidad.regla` **no son oráculo por sí mismos**. Su tratamiento es el de §4.5: viajan verbatim dentro de `CriticidadAplicada`, bajo el validador preventivo del requisito 8.

**Regla positiva, que es la que cierra de verdad:** `property_key` solo podrá derivarse del **contenido y las dimensiones declaradas del propio ítem** —texto, sujeto, clase y ámbito— y de nada más. Cualquier campo no clasificado aquí **deberá** clasificarse por su **contenido real**, nunca por remisión histórica.

**La prohibición alcanza también al generador de la familia sucesora**, que no podrá leer los artefactos de oráculo al asignar la clave.

### 5.4 Independencia del oráculo

**`property_key` se asignará antes de generar casos y referencias.** Si por construcción no fuese posible, la regla cerrada **deberá ser demostrablemente independiente de los artefactos de oráculo**, no meramente de orden registrado.

### 5.5 Ausencia

`null` o desconocido **impedirá agrupar**, pero **no hará al elemento inelegible**.

### 5.6 Naturaleza

Vocabulario **local P2**, **no productivo**.

### 5.7 Clasificación por (campo, consumidor, uso)

Una categoría global por campo no puede expresar que un mismo valor sea legible por `common` para una cosa y por `A` para otra. La constante única **deberá** clasificar por **terna**:

| Capacidad | Quién | Uso autorizado | Campos |
|---|---|---|---|
| **`ENTRADA_DE_CANDIDATO`** | candidatos y `common` | recuperación | `id`, `kind`, `project_id`, `text`, `polaridad`, `condicion`, `confirmacion`, `validez`, `disponibilidad`, `sensibilidad`, `temporalidad.*`, `ambito`, `autoridad`, `no_usar_como_memoria`, `no_consolidable`, `procedencia`, `entity_ids` |
| **`SOLO_CAPA_COMUN`** | únicamente `common` | decidir equivalencia | `property_key` |
| **`COMUN_Y_SENAL_DECLARADA_DE_A`** | `common` (agrupación y desempate de orden) **y** `A` (los tres usos que su ficha declara, §6.4) | según consumidor | `subject_key_experimental` |
| **`HANDOFF_A_B05`** | `common` **y B05**; **nunca** un candidato | `G12`, límite, explicación y traspaso | `criticidad.nivel`, `razon_segura`, `fuente_de_politica`, `regla_de_politica` |
| **`ORACULO_PROHIBIDO`** | nadie del canal de recuperación | ninguno | todo lo de §5.3 |

La constante seguirá siendo **una** y **fallará cerrada**: un campo sin terna asignada aborta la construcción de la proyección.

### 5.8 Control de inaccesibilidad — con la atribución correcta

**Atribución, que la v0.3 daba mal:**

- la **v0.2** pidió controles estáticos de prohibición, **sin especificar el mecanismo**;
- el **borrador inicial de la v0.3** formuló incorrectamente una búsqueda de cadena **fallo-abierta**;
- la **v0.3 publicada** ya sustituyó ese borrador por una **lista blanca por contención**.

La v0.3 publicada, sin embargo, seguía atribuyendo el defecto a la v0.2 en tres puntos. **Aquí se corrige: el defecto fue del borrador de la v0.3, no de la v0.2.**

**Mecanismo que se adopta:** **lista blanca por contención** sobre los atributos que un candidato puede leer de las estructuras que recibe —`atributos_leidos <= ATRIBUTOS_PERMITIDOS`—, que es el mecanismo del precedente real de `ADR002-B` (`test_adr002_b_corrupcion_static.py:118-133`, `assert nombres <= _NOMBRES_PERMITIDOS`). **No** una búsqueda de ausencia de una cadena literal, que sería fallo-abierta.

### 5.9 Validadores que la familia sucesora deberá incluir

| Validador | Qué comprueba | Polaridad |
|---|---|---|
| **Cobertura del canal lateral** | **Todo** ítem tiene entrada en el canal lateral, aunque su valor sea `null`. Falla si alguno carece de entrada | fallo-cerrado |
| **Frontera estructural del valor** | Los ítems con `property_key` no nula son exactamente aquellos cuya clase y forma admiten predicado sobre sujeto, según una **propiedad estructural declarada**. Nunca según su destino en el banco | fallo-cerrado |
| **Formato cerrado** | Pertenencia al vocabulario y versión declarados en el manifiesto | fallo-cerrado |
| **Independencia del oráculo** | El generador no leyó ningún artefacto de §5.3 y la asignación cumple §5.4 | fallo-cerrado |
| **Inaccesibilidad estructural** | Lista blanca por contención (§5.8) | fallo-cerrado |

La cobertura **no es circular**: exige el campo en **todos** los ítems, y la corrección semántica del valor **no se valida contra los grupos esperados**.

---

## 6. Sujeto de sonda frente a sujeto definitivo

### 6.1 Qué fue realmente `P-SUJETO-01`

Fue **únicamente** la proyección utilizada en las sondas de suficiencia de `C`: `subject_key := id del ítem`, la regla que aplica el único cargador congelado (`frozen_corpus.py:301`, `:319`).

**Se retira la caracterización de la v0.2**, que la llamaba «la más conservadora» y afirmaba que no creaba familias de sujeto artificiales. **Censo real del corpus de conformidad congelado** (`conformance_corpus_v0_4.json`, blob `c21b702c…`):

```
memorias  (79): MEM-001..MEM-027, MEM-101..MEM-112, MEM-901..MEM-940
decisiones(16): DEC-001..DEC-016
```

**No existe `MEM-028`…`MEM-078`.** El rango `MEM-001…MEM-079` que la v0.3 publicó **no existe** y queda retirado.

**Conclusión limitada que sí resiste**, y es la que importa:

- `_familias_de_sujeto` calcula `prefijo = plegar(subject_key).split("-")[0]` (`adr002_a/candidate.py:269`);
- con identificadores de la forma `<CLASE>-<n>` eso produce exactamente **`mem`** y **`dec`**;
- ambos superan `PREFIJO_MINIMO = 3` (`candidate.py:53`, `:270`);
- el puerto los traduce en `LIKE 'mem%'` y `LIKE 'dec%'` (`port.py:342`, `:349`);
- **los dos prefijos cubren el corpus de la sonda.**

Por tanto `P-SUJETO-01` **no es conservadora**: es la más permisiva para la expansión por familia de `E3`. **No es, en ningún caso, la proyección definitiva del benchmark.**

### 6.2 `subject_key_experimental`

| # | Requisito |
|---|---|
| 1 | Fuente explícita y congelada |
| 2 | Asignación independiente de casos, referencias y resultados |
| 3 | No derivada durante la consulta |
| 4 | Permitirá que identidades distintas con el mismo sujeto real se comparen por equivalencia |
| 5 | Conservará `null` como ausencia |
| 6 | La ausencia no eliminará el ítem |
| 7 | La ausencia impedirá la agrupación |
| 8 | No podrá usarse por un candidato como señal adicional no declarada |
| 9 | Todo uso estructural de `A` **deberá** ser exactamente el declarado en su ficha sucesora |

### 6.3 Los requisitos 5, 6 y 7 están invertidos HOY

| Requisito | Comportamiento **actual verificado** | Anclaje |
|---|---|---|
| 5 · `null` como ausencia | **Se pierde**: `subject_key=str(fila[1] or "")` hace indistinguibles `NULL` y cadena vacía | `port.py:193` |
| 6 · la ausencia no elimina | **La ausencia fuerza la agrupación y elimina miembros**: `_agrupar` agrupa por la clave cruda y devuelve solo representantes | `engine.py:88-92`, `:99` |
| 7 · la ausencia impide agrupar | **Lo contrario**: `A` **fabrica** un sujeto desde el texto cuando la clave está vacía, y `G11` pasa | `adr002_a/lexical.py`, `sujeto_estructural` |

**Deberá** corregirse en el paso 6 del plan: representar la ausencia sin colapsarla; que `_agrupar` no agrupe con clave ausente; y declarar si `A` conserva la fabricación de sujeto, que HOY enmascara la ausencia ante `G11` y ante `S6`.

### 6.4 Los tres usos que la ficha de `A` declara

| Uso | Cita de `ficha_ADR002-A_v3.json` |
|---|---|
| `E1` | «estructurada exacta por clave de sujeto normalizada […]» |
| `E3` | «[…] familias de sujeto por **prefijo concreto**» |
| Validación semántica | `arquitectura.puertas_previas_comunes`: «lectura semantica por item con marcadores lexicos de negacion y condicion, **clave de sujeto del canon** y marca temporal (B04-RF-17, RF-19)»; y `senal_tardia.validacion_en_e3`: «[…] **clave de sujeto del canon** y marca temporal del item» |

El tercero gobierna `G11` y la adjudicación de `S6`.

Definición canónica, literal: «expansion escalonada solo lexica/estructurada en todas las etapas E0-E5.»

### 6.5 HOY es un solo valor con cinco consumidores

`ItemCanonico.subject_key` (`contracts.py:187`), materializado desde `memories.subject_key` y `decisions.subject` (`port.py:44`, `:51`, `:193`):

| # | Consumidor | Dónde |
|---|---|---|
| 1 | `A` en `E1`, clave exacta | `candidate.py:149` |
| 2 | `A` en `E3`, prefijo de familia | `candidate.py:269` → `port.py:342`, `:349` |
| 3 | `A` en `leer()`, sujeto validado | `candidate.py:92` |
| 4 | `common` en `_agrupar` | `engine.py:88-92` |
| 5 | `common` en el desempate de orden | `engine.py:66-75` |

**La separación de §5.7 es de gobierno.** Fijar `subject_key_experimental` será **una sola decisión con cinco efectos**.

### 6.6 El riesgo incluye el orden

`engine._clave_de_orden` (`engine.py:66-75`) devuelve `(critica, autoridad, item.subject_key, item.id)`: la clave de sujeto es la **tercera clave de ordenación**, y `G12` aplica el límite duro sobre esa lista ya ordenada (`engine.py:190`). **Cambiar la proyección reordena la salida de los cuatro candidatos** y cambia qué cae fuera del límite, sin cambiar necesariamente el alcance.

**Salvaguarda:** si la proyección definitiva alterase, respecto de la ficha vigente, el **alcance**, la **validación**, la **adjudicación de parada** o el **orden** de `A`, **deberá declararse en su ficha sucesora antes de ejecutar**.

---

## 7. Deduplicación, agrupación y las dos cardinalidades

### 7.1 Anclaje canónico

> **`EXACTA` (línea 380):** «Busca uno o varios objetivos identificados o una respuesta cerrada.» · «S1 permitido solo cuando todos los objetivos están resueltos **y** el control interno confirma que no quedan críticos elegibles pendientes […]»
>
> **`ACOTADA` (línea 381):** «Busca N resultados, una lista definida o exploración con límite/criterio explícito.»
>
> **`EXHAUSTIVA` (línea 382):** *Definición:* «Busca todos los elementos que cumplen una condición.» · *Regla de parada:* «S1 deshabilitado. Deben agotarse los espacios autorizados o terminar por S2–S7 con estado parcial/explicado.»
>
> **`S1` (línea 385):** «Solo para EXACTA o ACOTADA: objetivos/cuota y soporte satisfechos, **y control interno de críticos pendientes = cero** […]»
>
> **`S4` (línea 388):** «[…] Se declara incompletitud y críticos pendientes sin revelar contenido protegido.»
>
> **`Q10` (línea 403):** «Solo se expande cuando falta suficiencia **o críticos** y el siguiente espacio está autorizado. […]»
>
> **`Q17` (línea 410):** «El límite objetivo puede ampliarse visiblemente para críticos; el límite duro nunca se supera. **Si quedan críticos fuera, se declara incompleto y se solicita ampliación.**»
>
> **`RF-24` (línea 442), íntegra:** «Respetar límite objetivo y límite duro; nunca ampliar el segundo ni ocultar desbordamiento crítico.»
>
> **`G12` (línea 306):** «Todos los críticos elegibles se preservan o se declara desbordamiento bajo límite duro; nunca se ocultan.»
>
> **`CA-44` (línea 498):** «[…] Límite duro 5, seis críticos elegibles con empate en el corte. | Aplica desempate estable registrado; **entrega 5, parcial y crítico pendiente**. Si el empate material persiste, no inventa preferencia. […]»
>
> **Contrato de salida (línea 233):** «Grupos de duplicados | Representante justificado, procedencias adicionales y diferencias preservadas.»

### 7.2 Dos mecanismos distintos

**A · Deduplicación exacta por identidad.** El mismo identificador canónico aportado por varias etapas o procedencias. Una sola entrada lógica. Fusiona señales y procedencias. No pierde ninguna explicación. **No selecciona representante entre identidades diferentes**, porque no las hay.

**B · Agrupación de equivalentes.** Identificadores canónicos **distintos**, solo cuando los siete ejes de `B04-Q13` (línea 406) están determinados y coinciden. Conserva todos los miembros, sus relaciones, procedencias y diferencias. Representante justificado. **No elimina las identidades de la salida.**

### 7.3 Qué impide agrupar

Sujeto ausente o indeterminado; sustituida frente a sucesora; apoyo frente a refutación; condiciones, tiempos, ámbitos o posturas distintas; vigencia o disponibilidad distintas; `property_key` distinta, `null` o desconocida; **cualquier eje indeterminado**. Fallo cerrado: la duda no fusiona.

### 7.4 Regla de representante

Cascada registrada: **confirmación → autoridad → vigencia → procedencia → identidad estable**. **«Primero en llegar» queda prohibido.** `B04:196` prohíbe elegir representante si hay diferencias materiales, de modo que solo se aplica a grupos que ya pasaron §7.3.

### 7.5 Reparto por contador

| Concepto | Contador |
|---|---|
| Suficiencia — **primer conjunto de `S1`**: objetivos y cuota | **semántica** |
| Suficiencia — **segundo conjunto de `S1`**: críticos pendientes = cero | **documental** |
| `EXACTA`: objetivos identificados | **semántica** |
| `ACOTADA`: la cuota `N` | **semántica** — reinterpretación declarada en §7.6 |
| Avanzar de etapa (`Q10`: «falta suficiencia **o críticos**») | **semántica** para la suficiencia; **documental** para los críticos |
| Parada `S1` (solo `EXACTA`/`ACOTADA`) | **semántica**, con la condición documental |
| `EXHAUSTIVA` y su parada por agotamiento (`S5`) | **documental** |
| Límite objetivo y límite duro (`RF-24`, `Q17`) | **documental**: se aplican sobre **resultados entregables** |
| Recall, auditoría, procedencia, trazabilidad, inspección de criticidad, explicación, handoff | **documental** |

### 7.6 La reinterpretación de `ACOTADA`, declarada

`B04` línea 381 dice «**N resultados**», unidad documental. Asignar la cuota al contador semántico **es una reinterpretación**, apoyada en que `B04-Q13` hace que los miembros de un grupo sirvan a **una única necesidad**. **Requiere aprobación explícita.** Si se prefiere la lectura literal, `ACOTADA` pasa al contador documental y la regla 7 de §7.7 se limita a `EXACTA`.

### 7.7 Reglas

1. Todos los miembros permanecerán citables.
2. El representante no reemplazará ni eliminará a los miembros.
3. **`G12` deberá inspeccionar todos los miembros**, no solo representantes.
4. Un crítico no quedará oculto por pertenecer a un grupo.
5. **Bajo límite duro, los miembros se entregarán hasta agotar el límite**, aplicando el desempate estable de `M-05`; **los omitidos se contarán y se declararán como desbordamiento visible** (`G12`, `RF-24`). **Nunca se omitirán en silencio ni se ampliará el límite duro.**
   > **El grupo NO es atómico frente al límite.** Esa regla no se deriva de ninguna fuente y choca con `CA-44`, que ante seis críticos y límite 5 ordena «entrega 5, parcial y crítico pendiente». **B04 sí trunca; lo que prohíbe es ocultarlo.**
6. Si el límite impide entregar íntegro un grupo, el estado será `PARCIAL` y la razón quedará trazada (`S4`, `Q17`).
7. Equivalentes repetidos no podrán satisfacer artificialmente una cardinalidad que pide necesidades semánticas distintas.
8. En `EXHAUSTIVA`, `S1` seguirá deshabilitado y la salida contará por `cardinalidad_documental`.
9. **Precedencia:** `S1` **no podrá** adjudicarse si el límite impide entregar íntegro un grupo que compute en la cuota, o si quedan críticos elegibles pendientes. Prevalecerá `S4` con estado `PARCIAL`.

### 7.8 Comportamiento actual, que estas reglas NO describen

**HOY**, y esto es lo que la corrección deberá cambiar:

| Hecho actual verificado | Anclaje |
|---|---|
| `_agrupar` devuelve **solo representantes**; los demás miembros desaparecen del resultado | `engine.py:88-92`, `:99` |
| `G12` se aplica **después** de agrupar y por tanto **solo ve representantes**, no miembros | `engine.py:188`, `:190` |
| La suficiencia se adjudica **antes** de agrupar | `engine.py:162-168` frente a `:188` |
| La clave de agrupación tiene **tres** de los siete ejes | `engine.py:88-92` |

**Ninguna de las reglas de §7.7 describe el árbol vigente.** Todas son requisitos del paso 6 del plan.

### 7.9 Estructura de salida

Agregado `GrupoDeEquivalentes`, campo propio del contrato de salida y **distinto de la traza**: `representante`, `miembros`, `procedencias_adicionales`, `diferencias_materiales`, `relaciones_entre_miembros`, `razon_del_representante`, `estado_historico_por_miembro`.

**Invariante comprobable:** elegibles antes de agrupar = unión de los `miembros` de todos los grupos + los no agrupados.

---

## 8. Familia sucesora de conformidad

Procede porque el veredicto de `C` es **B**. **La v0.4 del corpus permanece íntegra**; la familia se materializará **junto a** ella, conforme al **acta de congelación del corpus v0.4, §7 punto 2**: «Una versión posterior del corpus se materializa **junto a** la v0.4, con nueva acta y nuevos blobs; **no se sobrescribe** ningún congelado.»

### 8.1 Lo que la familia deberá cerrar

| # | Artefacto o dato | Contenido |
|---|---|---|
| 1 | **`property_key`** | **Por ítem: solo el valor**, en el canal lateral de §5.1, `null` incluido y presente en **todos** los ítems. `fuente_de_asignacion`, `version_del_vocabulario` y `regla_de_validacion` **una sola vez en el manifiesto** (§5.2) |
| 2 | **`subject_key_experimental`** | Fuente congelada y custodia de §6.2 |
| 3 | **`CriticidadAplicada`** o la regla cerrada que la produce | Con la asignación congelada antes de ejecutar (§4.5 requisito 5) y la tabla de §4.6 |
| 4 | **Vocabularios P2** | `CONFIRMACION`, `VALIDEZ`, `DISPONIBILIDAD`, `SENSIBILIDAD`, `AUTORIDAD`, `AMBITO`, niveles de criticidad y el vocabulario de `property_key` |
| 5 | **Arista discriminante de `C`** | Tipo distinto de supersesión y conflicto |
| 6 | **Extremos del discriminante** | Dos ítems sintéticos, con **cero** tokens de contenido compartidos bajo la regla de tokenización real del índice, verificado mecánicamente; sujetos distintos; **mismo proyecto** |
| 7 | **Caso funcional** | Semilla alcanzable por `A`; destino no alcanzable por `A` completo `E0-E5` |
| 8 | **Referencia independiente** | Derivada **después**, por regla cerrada, con orden auditable |
| 9 | **Validadores** | Los de v0.4 más: **censo de criticidad propio, con constantes recomputadas y congeladas** —no las de §3.1—; los cinco de §5.9; el patrón de identificador de caso de §4.5 requisito 8; y cero solapamiento léxico del discriminante |
| 10 | **Manifiesto sucesor** | Cierra **inequívocamente la familia completa**, incluidos los artefactos que no cambian, y aloja la custodia de §5.2 |
| 11 | **Auditoría independiente** | Con las mismas puertas que la v0.4 |
| 12 | **Acta de congelación propia** | Blobs nuevos; los siete de v0.4 **intactos** |
| 13 | **Proyección `T0`** | `t0_preexecution_projection_v0_2.json` (blob observado `3a241839b7eba84f12a3bbb3c643a17f7b0d0f91`) está declarado `NO_NORMATIVO_NO_CONGELABLE` por el acta v0.4, cuyo §6 prohíbe modificarlo. La familia **deberá declarar expresamente** si lo regenera —como artefacto no congelable, con su blob y `version_contrato` nuevos— o si no lo regenera, justificando cómo cumple entonces la regla del manifiesto |

### 8.2 Lo que permanece intacto

- **Corpus v0.4** íntegro. **`performance_corpus_v0_2.json`** íntegro.
- **Rederivación T0 de `TOL-208`** íntegra **mientras no cambie ninguna de las guardas que su arnés verifica realmente**: `rederivation_protocol.fallos_de_corpus` recorre **todos** los blobs de `CORPUS_CONGELADO` —los siete de v0.4, no solo el de rendimiento—, `fallos_de_linea_base` verifica la línea base histórica, y `fallos_de_ficha` exige ficha de `T0` en estado `CONGELADA`. Como §8.1 punto 12 mantiene intactos los siete blobs, en la práctica nada se rompe; la condición se enuncia como el arnés la implementa.

### 8.3 El arnés de conformidad de `T0` — no se presupone

Hay que distinguir cuatro cosas que la v0.3 confundía:

| Plano | Estado **actual verificado** |
|---|---|
| **Control productivo real** | `KnowledgeSearchRepository` de Sirius 0.1 vía `build_sqlite_knowledge_search_repository` y `RankRelevantKnowledgeUseCase`, según `ficha_T0-control_v1.json` |
| **Arnés de rendimiento existente** | `run_rederivation --check`, **bloqueado por blob** al corpus de rendimiento (`frozen_corpus.py:51-52`, falla cerrado ante otro blob) y con **tres** escenarios derivados |
| **Arnés o adaptador de conformidad** | **NO EXISTE** |
| **Cambio que requeriría** | Construirlo **es un cambio de implementación de `T0`** |

**Efecto sobre ficha y evidencia:** la ficha congelada declara que «cualquier modificación posterior obligará a nueva versión de ficha **y a repetir las ejecuciones ya realizadas**» —es decir, `rederivacion_t0_v0.1` y `v0.2`—. Por tanto, **construir un arnés de conformidad para `T0` obligaría a ficha sucesora de `T0` y a repetir sus ejecuciones.**

**No se decide aquí.** El paso 4 del plan lo trata como adjudicación separada, con el coste a la vista.

### 8.4 Fichas de los candidatos

Las fichas sucesoras de `A`, `B`, `C` y `D` **deberán citar la familia efectiva utilizada**, no «la v0.4» genéricamente.

---

## 9. Discrepancia del sustrato léxico declarado

### 9.1 Inventario completo de apariciones

| Artefacto | Estado | Qué declara |
|---|---|---|
| `ficha_T0-control_v1.json` | **CONGELADA, vigente** | «FTS5 medido de Sirius 0.1 (**tabla `items_fts`** con **unicode61 y remove_diacritics 2**), sin alternativa ni índice adicional» |
| `ficha_ADR002-A_v3.json` (líneas 29 y 69) | **CONGELADA, APROBADA** | «FTS5 medido de Sirius 0.1 (**unicode61, remove_diacritics 2**), sin alternativa» y «SQLite FTS5 (**unicode61, remove_diacritics 2**)» |
| `ficha_ADR002-B_v5.json` (líneas 29 y 69) | **CONGELADA, APROBADA** | idéntico |
| `ficha_ADR002-A_v2.json`, `ficha_ADR002-B_v3.json` | **SUSTITUIDAS** | repiten la declaración |
| `frozen_corpus.py:63` y `:72` | código | comentario y docstring: pliegue «equivalente a `remove_diacritics 2`» |

**`items_fts` no aparece en ningún otro punto del repositorio:** la ficha de `T0` es su única ocurrencia.

### 9.2 Hechos verificados directamente sobre la migración

| # | Hecho | Cómo se verificó |
|---|---|---|
| 1 | La migración crea **`knowledge_fts`** | `61be4bb269bf:116` |
| 2 | El `CREATE VIRTUAL TABLE` **no declara `tokenize=`** | La única aparición de «tokenize» en el fichero está en una cadena de documentación (`:33`) |
| 3 | El tokenizador predeterminado es **`unicode61`** | Documentación de SQLite y sonda |
| 4 | `remove_diacritics` predeterminado es **`1`** | Sonda: los términos indexados por la tabla real son **idénticos** a los de una tabla con `remove_diacritics 1` y **distintos** de una con `2` |
| 5 | Las fichas citadas declaran **`remove_diacritics 2`** | §9.1 |
| 6 | La ficha de `T0` dice además **`items_fts`** en vez de `knowledge_fts` | §9.1 |

### 9.3 Auditoría dirigida del impacto — ejecutada

Sin modificar el repositorio, sin ejecutar el benchmark y sin medir rendimiento.

**Paso 1-2 · SQL efectivo.** Base mínima con el DDL real; `sqlite_master` devuelve, literal:

```
CREATE VIRTUAL TABLE knowledge_fts USING fts5(kind UNINDEXED, item_id UNINDEXED, content)
```

**Paso 3 · Sonda discriminante** (SQLite 3.45.1). Términos indexados de una muestra con acentos españoles, caracteres multi-diacríticos, griego, cirílico y latín extendido:

| Configuración | ¿Idéntica a la tabla real? |
|---|---|
| `remove_diacritics 0` | **no** |
| **`remove_diacritics 1`** | **SÍ** |
| `remove_diacritics 2` | **no** |

**Diferencia efectiva entre 1 y 2**, y es la única: los codepoints con **más de una marca diacrítica**. Con `1` se indexan sin plegar —`ǻ`, `ḗ`, `ṓ`, `ẳ`, `ế`, `ự`—; con `2` se pliegan a `a`, `e`, `o`, `u`. **Los acentos españoles de una sola marca —`á é í ó ú ñ ü`— se pliegan idénticamente en ambas.**

**Paso 4 · Escaneo del material congelado.** Codepoints no ASCII presentes y su comportamiento:

| Fuente | Codepoints no ASCII | ¿Alguno diverge entre 1 y 2? |
|---|---|---|
| `conformance_corpus_v0_4.json` | 8 | **no** |
| `performance_corpus_v0_2.json` | 8 | **no** |
| `cases_v0_4.json` | 19 | **no** |
| `references_v0_4.json` | 15 | **no** |
| `fixtures.py`, `fixtures_b.py` | 3, 1 | **no** |
| `frozen_corpus.py`, `tolerances/corpus.py` | 2, 1 | **no** |
| Evidencia emitida de `T0` (`rederivacion_t0_v0.1/v0.2` y muestras) | 2 (`§`, `·`) | **no** |

Unión de todos los codepoints no ASCII del material: **19** — `§ « · » ¿ Á Í á é í ñ ó ú — " " … € →`. **Ninguno diverge.**
Los **106** textos del corpus de conformidad —ítems, mensajes y documentos— comprobados uno a uno: **0 divergentes**.

**Paso 5 · Suposiciones explícitas en el código.** Única aparición de `remove_diacritics` en `experiments/` y `src/`: `frozen_corpus.py:63` y `:72`, un comentario y un docstring que describen el pliegue propio como «equivalente a `remove_diacritics 2`». Ese mismo módulo declara además que la coincidencia «se **VERIFICA** contra el índice real antes de medir» (`:27`, `:66`, `:145`, `:388`), de modo que una divergencia habría abortado la medición.

### 9.4 Adjudicación

# **A · LA DISCREPANCIA ES EXCLUSIVAMENTE DOCUMENTAL**

No hay efecto sobre resultados, comparabilidad, huellas, pruebas ni evidencia ya emitida: **no existe en el material congelado un solo codepoint cuyo tratamiento difiera** entre la configuración declarada y la real.

**No procede la regla de parada.**

### 9.5 Remedio propuesto

**`T0-control v1`:**

- **fe de erratas append-only**;
- **no modificar la ficha original**;
- **no emitir `T0 v2` ni repetir `TOL-208`** únicamente por una descripción documental falsa;
- **declarar como identidad observada real**: `knowledge_fts`, `unicode61`, `remove_diacritics 1`;
- cualquier cambio futuro de implementación o protocolo sigue sometido a las reglas normales de ficha sucesora.

**`ADR002-A v3` y `ADR002-B v5`:**

- sus fichas y actas históricas **no se reescriben**;
- **no se emiten ahora versiones intermedias** exclusivamente por esta errata;
- la fe de erratas **deberá cubrirlas expresamente**;
- las **fichas sucesoras ya obligatorias** por la futura corrección de `common` **deberán declarar correctamente** `knowledge_fts`, `unicode61` y `remove_diacritics 1`;
- esas sucesoras **deberán probarse y recibir reaprobación explícita**;
- **ningún benchmark podrá autorizarse usando las fichas actuales sin haber cerrado la discrepancia.**

**No se emite todavía la fe de erratas ni ninguna ficha.**

---

## 10. Plan propuesto, sin autorizar

| Paso | Contenido |
|---|---|
| **1** | Aprobación explícita de la resolución v0.4 |
| **2** | Materialización y congelación de la familia sucesora |
| **3** | **Fe de erratas amplia del sustrato léxico**, con el alcance adjudicado en §9.5 |
| **4** | **Construcción o adjudicación separada del arnés de conformidad de `T0`** (§8.3) |
| **5** | Construcción de la proyección experimental |
| **6** | **Corrección completa y única de `common`** — incluye §4.10, §6.3 y §7.7 |
| **7** | Fichas sucesoras de `A` y `B`, incorporando **tanto `common` como la identidad FTS5 correcta** |
| **8** | Pruebas completas y **reaprobación explícita** de `A` y `B` |
| **9** | Implementación, congelación, prueba y aprobación de `C` |
| **10** | Implementación, congelación, prueba y aprobación de `D` |
| **11** | **Solicitud separada** de autorización del benchmark |

**Ningún paso queda autorizado por esta resolución.**

---

## 11. Auditoría adversarial

### 11.1 Lo que la refutación tumbó de la v0.3, y su corrección

| # | Afirmación de la v0.3 | Por qué caía | Corrección en la v0.4 |
|---|---|---|---|
| **B1** | La tabla de tesis resistentes certificaba «el grupo es atómico» | Contradecía §7.6 y la propia tabla de refutaciones de la v0.3 | §7.7 regla 5 y §11.2 tesis 21, coherentes |
| **B2** | «Valor, fuente de asignación, versión de vocabulario y regla de validación **por ítem agrupable**» | Reintroducía la custodia por ítem y el conjunto circular que §5 eliminaba | §8.1 punto 1 |
| **M1** | Cierre de la lista negra por remisión a la v0.2 §9.2 | Reimportaba la prohibición de `razon` y `regla` que §4.3 levantaba | §5.3, autocontenida |
| **M2** | «`MEM-001`…`MEM-079`» | Rango inexistente | §6.1, censo real |
| **M3** | «la v0.2 tenía un control fallo-abierto» | La v0.2 no lo contiene; fue el borrador de la v0.3 | §5.8 |
| **M4** | La discrepancia confinada a `T0` | Alcanza a fichas **aprobadas** de `A` y `B` | §9.1 |
| **H1** | `subject_key_experimental` «solo `common`» | `A` lo consume en tres usos declarados | §5.7, por terna |
| **H2** | Criticidad segura «solo `common`» | Debe salir en el handoff a B05 | §5.7, `HANDOFF_A_B05` |
| **H3** | Mapeo «derivado de la razón de política» | Su dominio es `criticidad.fuente` bruta | §4.6 |
| **H4** | Numeración huérfana en la tabla de tesis | No correspondía con la lista del paquete | §11.2 |
| **H5** | «19 razones de política» | 19 instancias, **8 valores distintos** | §4.3 y §4.9 punto 3 |
| **H6** | Cuatro controles negativos presentados como independientes | El cuarto es redundante | §3.2 |
| **H7** | Semántica del verificador sin declarar | — | §3.2 |
| **H8** | Citas «literales» con elisiones no marcadas | — | Toda elisión con `[…]` |
| **H9** | El paquete presuponía un arnés de conformidad de `T0` | No existe | §8.3 y paquete §6 `P-I3` |

### 11.2 Tesis que resisten, numeradas contra el §11 del paquete v0.4

| Punto del paquete | Tesis | Resultado |
|---|---|---|
| 15 | Recuento exacto y verificador no vacuo | **Resiste**, con la redundancia del cuarto control declarada (§3.2) |
| 16 | La criticidad aplicada satisface `RF-23`, `M19`, `D05` y `Q21` | **Resiste** con `razon` y `regla` verbatim y el ID de política |
| 17 | La prohibición no es más amplia que la evidencia | **Resiste**: §4.3 y §5.3 |
| 18 | `property_key` no derivable del oráculo, con control fallo-cerrado | **Resiste**: §5.3, §5.4, §5.8, §5.9 |
| 19 | La caracterización de la proyección de sonda es verdadera | **Resiste tras corregirse**: §6.1 |
| 20 | Los requisitos sobre ausencia de sujeto se contrastan contra el árbol | **Resiste**: §6.3 |
| 21 | Las dos cardinalidades no ocultan un crítico | **Resiste tras corregirse**: el grupo **no** es atómico y **deberá** truncarse con desbordamiento declarado (§7.7 reglas 3-6). **HOY el motor no lo hace** (§7.8) |
| 22 | Existe regla de precedencia entre `S1` y `PARCIAL` | **Resiste**: §7.7 regla 9 |
| 23 | Toda cita es literal o marcada, y las secciones existen | **Resiste**: `[…]` en toda elisión; el acta se cita por **§7 punto 2** |
| 24 | La familia sucesora cierra todo lo nuevo, incluida la proyección `T0` | **Resiste**: §8.1, trece puntos |
| 25 | Ninguna afirmación presupone un arnés que no existe | **Resiste**: §8.3 |
| 26 | Ninguna regla retirada reaparece | **Resiste**: la atomicidad no aparece afirmada en ningún punto |
| 27 | La adjudicación del sustrato léxico se sostiene en la sonda | **Resiste**: §9.3 |
| 28 | El inventario de artefactos afectados es completo | **Resiste**: §9.1, incluidas las sustituidas |
| 29 | Ninguna categoría contradice a sus consumidores | **Resiste**: §5.7 |
| 30 | Paquete y resolución no discrepan | **Resiste** |

---

## 12. Cuestiones que requieren aprobación explícita

1. El contrato de criticidad de tres planos y el handoff completo a B05 (§4), incluida la adopción del vocabulario de `Q21` (§4.2).
2. La tabla de mapeo de `fuente_de_politica` (§4.6).
3. Que la trazabilidad hasta el caso del banco no viaje a B05 (§4.9).
4. La ampliación del vocabulario de niveles de criticidad (§4.10, paso 6).
5. El origen, la custodia y los cinco validadores de `property_key` (§5).
6. La clasificación por **(campo, consumidor, uso)** y la capacidad `HANDOFF_A_B05` (§5.7).
7. `subject_key_experimental` (§6.2), sabiendo que **HOY** es un único campo con cinco consumidores (§6.5).
8. Que su elección **es también una decisión de ordenación** (§6.6).
9. **Que la conclusión de `C` se recompruebe bajo la proyección definitiva** antes de autorizar la ronda primaria (§1, §6.1).
10. Los tres cambios de `common/` sobre la ausencia de sujeto (§6.3).
11. Las dos cardinalidades y las nueve reglas de §7.7.
12. La reinterpretación de `ACOTADA` (§7.6).
13. El alcance de la familia sucesora (§8.1) y el tratamiento de la proyección `T0` (§8.1 punto 13).
14. **La adjudicación del sustrato léxico como exclusivamente documental** (§9.4) y el remedio de §9.5.
15. La adjudicación separada del arnés de conformidad de `T0`, con su coste (§8.3).
16. El plan de once pasos (§10).

---

## 13. Estado

**PROPUESTA. NO APROBADA.**

- El contrato común **no se modifica**.
- `ADR002-A v3` y `ADR002-B v5` permanecen **aprobadas e intactas**; ninguna aprobación anterior se borra ni se reescribe. **Pero ningún benchmark podrá autorizarse con las fichas actuales mientras la discrepancia de identidad del sustrato léxico siga abierta** (§9.5).
- `T0-control v1` intacto. Corpus v0.4 intacto. Toda la implementación intacta.
- **El benchmark permanece bloqueado.** La ronda primaria sigue siendo `T0 + A + B + C + D`, **sin reducción**.
- Las **v0.1, v0.2 y v0.3 se conservan**; esta versión las sustituye **únicamente en el plano documental de propuesta**.
- **No autoriza** implementación, fichas sucesoras, corpus, fe de erratas, benchmark, fast-forward ni fusión.
- `evidence/adr001-spikes` **no se ha movido**; PR #117 sigue abierto, sin fusionar y con cabeza en `a074eb5`.
