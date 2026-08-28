# SIRIUS 0.2 · ADR-002 · Resolución pre-benchmark · v0.3

## Contrato común experimental y fuente relacional admisible de ADR002-C

**Estado:** **PROPUESTA · PENDIENTE DE APROBACIÓN EXPLÍCITA DEL USUARIO**
**Versión:** v0.3
**Sustituye documentalmente a:** `..._v0.1_PROPUESTA.md` (blob `727e02ed6b7f0e750d4877a8d10bd171afbf4d5a`) y `..._v0.2_PROPUESTA.md` (blob `82c2bcc06bbee2f39ca58f0f921fcf9e1ee49eb6`). **Ambos se conservan íntegros.**
**Preinscrita por:** `..._PAQUETE_RESOLUCION_05_..._v0.3.md`
**Rama de trabajo:** `claude/adr002-tol209-forensic-audit-i0ui8k` · **HEAD de partida:** `d44ade894c1cc453d3ded0fa703362e8b608571d`

> **No está aprobada.** No autoriza ninguna implementación ni benchmark. `ADR002-A v3` y `ADR002-B v5` continúan aprobadas e intactas. La ronda primaria `T0 + A + B + C + D` sigue sin reducción.

---

## 1. Materia cerrada que esta versión no reabre

**`ADR002-C` · fuente relacional: ADMISIBLE PERO FUNCIONALMENTE INSUFICIENTE en el corpus v0.4.**

Demostrado por **ejecución de `ADR002-A` completo `E0-E5`** sobre las cinco aristas ítem↔ítem, con proyección de sujeto declarada de antemano y consultas construidas solo con términos propios del origen: allí donde las puertas permiten el destino, `A` lo alcanza en `E3` mediante términos puente tomados del texto de la propia semilla; en la única configuración donde `A` no lo alcanza, `G4` excluye el destino, luego `C` tampoco lo devolvería.

**Vigente. No se reinvestiga**, por instrucción expresa del usuario para esta versión. Los detalles de ejecución constan en la v0.2 §8, que se conserva.

> **Salvedad que esta versión sí debe registrar.** La revisión adversarial de la v0.3 encontró que **la justificación que la v0.2 dio a su proyección de sujeto era falsa**: `P-SUJETO-01` no es «la más restrictiva» ni «no crea familias de sujeto», sino **la más permisiva posible** para la expansión por familia de `E3` —produce dos prefijos, `mem` y `dec`, que cubren el 100 % del corpus (§6.1)—. El **veredicto** se mantiene aceptado tal como se instruye; lo que se corrige es su **argumento**: no está reforzado «a fortiori» por la proyección, sino **condicionado a ella**. Por eso §12 incorpora, como cuestión de aprobación explícita, que la conclusión de `C` **se vuelva a comprobar bajo la proyección definitiva** antes de autorizar la ronda primaria. **Esto no reabre la materia aquí**: la deja correctamente condicionada.

---

## 2. Qué corrige esta versión

| # | Defecto de la v0.2 | Corrección |
|---|---|---|
| **1** | Recuento de criticidad inexacto: decía 17 `CRITICO` | **76 / 18 / 1 / 19**, con comprobación reproducible y controles negativos (§3) |
| **2** | Separó el oráculo bruto pero dejó incompleto el contrato aprobado: `RF-23` obliga a propagar **nivel, razón, fuente y regla aprobada** hasta B05 | **Tres planos** y handoff completo (§4) |
| **3** | `property_key` sin origen ni custodia, y con un control **fallo-abierto** que invocaba mal su propio precedente | **Canal lateral de `common`**, custodia en el manifiesto, cierre **por referencia**, y validadores **fallo-cerrados** por contención (§5) |
| **4** | Podía leerse que `P-SUJETO-01` era la proyección definitiva, y la justificaba con una afirmación **falsa** | **Separadas** sonda y definitiva; se retira la afirmación falsa; `subject_key_experimental`, con los tres requisitos hoy **invertidos** en el árbol y el riesgo de **orden** que la v0.2 omitía (§6) |
| **5** | Regla de cardinalidad de grupos incompleta | **Dos cardinalidades**, semántica y documental (§7) |
| **6** | La familia sucesora solo cerraba el discriminante de `C` | Cierra **todos** los datos experimentales nuevos (§8) |
| **7** | La discrepancia `items_fts` quedaba mezclada con la aprobación, y era **una de dos** | **Hallazgo separado** y **ampliado**: nombre de tabla **y** parámetro del tokenizador. Fe de erratas propia, no emitida todavía (§9) |

Todo lo demás de la v0.2 se conserva: los dos mecanismos de deduplicación y agrupación, la regla de representante, `G5` y el sujeto ausente, la eliminación de `admite_no_vigentes`, el reparto `G6`/`G7`, la proyección experimental, el transporte de `mensajes[].project_id` y los vocabularios cerrados P2.

**Con una salvedad que se declara y no se disimula:** la **lista blanca no se conserva sin cambios**. `property_key` y los campos de criticidad aplicada no caben en su forma binaria —no son consumibles por un candidato y tampoco son oráculo—, de modo que **se extiende a tres categorías** conservando su mecanismo de fallo cerrado (§5.7).

---

## 3. Recuento exacto de criticidad

### 3.1 Cifras sobre el blob congelado `c21b702c…`

| | |
|---|---|
| Ítems totales | **95** |
| `criticidad: null` | **76** |
| `criticidad` no nula | **19** |
| de ellos, `nivel: CRITICO` | **18** |
| de ellos, `nivel: IMPORTANTE` | **1** |
| niveles no inventariados | **ninguno** |

**Corrige** la cifra de la v0.2, que decía 17 `CRITICO`. **El corpus no se modifica.**

### 3.2 Comprobación reproducible **del corpus v0.4**

Recorre los 95 ítems y **falla cerrada** si: la suma no es 95; los no nulos no son 19; la distribución no es 18/1; o aparece un nivel no inventariado. Verifica además el blob del corpus antes de contar.

> **Alcance, para que no se malinterprete:** estas constantes son **específicas de la v0.4**. La familia sucesora añadirá ítems, luego **no hereda este verificador con estas cifras**: debe llevar **su propio censo**, con **sus propias constantes recomputadas y congeladas en su propia acta**, y con la misma disciplina de fallo cerrado y controles negativos. §8.1 punto 9 debe leerse así.

```
blob              : c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48
total items       : 95
criticidad null   : 76
criticidad != null: 19
distribucion      : {'CRITICO': 18, 'IMPORTANTE': 1}
niveles ajenos    : ninguno
CENSO CONFORME
```

### 3.3 Controles negativos — el verificador no es vacuo

Ejecutados sobre copias mutadas **fuera del repositorio**; **el corpus congelado no se tocó**. Como toda mutación cambia el blob por construcción, en los controles se **neutralizó deliberadamente la comprobación de blob** para poder ejercitar los contadores; esa comprobación se validó por separado contra el fichero real (§3.2).

| Mutación | Resultado |
|---|---|
| quitar un ítem (suma 94) | **FALLA** — «la suma no es 95: 94» y «nulos + no nulos no suma el total» |
| anular la criticidad de los `CRITICO` | **FALLA** — «los no nulos no son 19» y «la distribución no es 18/1» |
| mover un `CRITICO` a `IMPORTANTE` (17/2) | **FALLA** — «la distribución no es 18/1: {IMPORTANTE: 2, CRITICO: 17}» |
| introducir un nivel `URGENTE` | **FALLA** — por **dos** vías: «la distribución no es 18/1: {URGENTE: 1, CRITICO: 18}» **y** «nivel no inventariado: ['URGENTE']» |

---

## 4. Contrato de criticidad de extremo a extremo

### 4.1 El requisito canónico que la v0.2 dejó incompleto

> **`B04-RF-23` (línea 441):** «Propagar **nivel, razón, fuente y regla aprobada** de criticidad **hasta B05**; prohibir auto-marcado libre y exclusión por presupuesto ordinario.»
>
> **`B04-M19` (línea 525):** «Criticidad controlada y propagada | Marcas con **fuente/regla aprobada y razón intactas B04→B05**. | 100%; 0 auto-marcados sin regla y 0 exclusiones por presupuesto ordinario.»
>
> **`B04-D05` (línea 535, APROBADA):** «La criticidad exige **fuente o regla aprobada** y cruza a B05; B05 no puede excluirla por presupuesto ordinario, solo por límite duro o elección explícita por petición con estado parcial.»
>
> **`B04-Q21` (línea 414):** «La criticidad procede de **requisito/decisión aprobada, acto explícito, etiqueta de escenario o regla operativa aprobada con ID y evidencia**. Sirius no puede auto-marcar por intuición libre; la marca es corregible, no canónica y B05 no puede omitirla por presupuesto ordinario.»
>
> **`B04` §6:** «Cada resultado crítico lleva **nivel, razón y fuente** de la clasificación. **B04 no puede proteger un crítico si B05 recibe solo texto y puntuación**; la marca forma parte del contrato de salida.»
>
> **`B04` §7 (línea 230):** «Criticidad | Nivel, razón y fuente de clasificación para cada resultado; **debe sobrevivir intacta al handoff a B05**.»

**Propagar solo el nivel incumple el contrato.** La v0.2 lo hacía.

### 4.2 Una divergencia interna de B04 que hay que declarar, no ocultar

`B04` enumera la procedencia de la criticidad en **tres sitios distintos y no coincidentes**:

| Lugar | Enumeración | ¿Incluye la etiqueta del corpus? |
|---|---|---|
| **Glosario, línea 186** | «instrucción explícita, requisito/decisión aprobada o clasificación operativa trazable» — **tres** | **no** |
| **§6, líneas 215-219** | explícito del usuario · documento o decisión aprobada · clasificación operativa · **adjudicación de prueba** («el corpus etiqueta los críticos antes de ejecutar el caso») — **cuatro** | **sí** |
| **`Q21`, línea 414** | requisito/decisión aprobada · acto explícito · **etiqueta de escenario** · regla operativa aprobada, **con ID y evidencia** — **cuatro** | **sí** |

**Se adopta la lista de `Q21`**, y se justifica: es la respuesta aprobada a la pregunta «¿quién clasifica la criticidad en ejecución, con qué evidencia y cómo se corrige?» (`B04-Q21`, línea 273), es decir, la que gobierna **directamente** esta materia; coincide con `§6` en admitir la etiqueta de escenario; y es la única que fija además el requisito de **ID y evidencia**. El glosario de la línea 186 describe la marca en general y **no** es la respuesta a esa pregunta.

**Se declara la divergencia en lugar de disimularla:** dos de las tres enumeraciones admiten la etiqueta de escenario, y la que no la admite no es la que gobierna la clasificación en ejecución.

### 4.3 Qué porta realmente el oráculo — verificado campo a campo

Contra el blob congelado `c21b702c…`, sobre los 19 ítems con criticidad:

| Campo bruto | Valores observados | ¿Porta identificador de caso? |
|---|---|---|
| `criticidad.nivel` | `CRITICO` ×18, `IMPORTANTE` ×1 | **no** |
| `criticidad.razon` | 19 razones de política; **0 contienen identificador** de caso ni de ítem | **no** |
| `criticidad.regla` | `CRIT-01`…`CRIT-07` (12× `CRIT-06`, 2× `CRIT-07`) | **no** — son identificadores de **regla de política** |
| `criticidad.fuente` | 8 valores distintos: `B04-CA-01`, `B04-CA-02`, `B04-CA-20`, `B04-CA-21`, `B04-CA-42`, `B04-CA-45`, `REGLA-CRIT-07`, y ×12 «Instanciación compartida por B04-CA-26, B04-CA-38 y B04-CA-44» | **SÍ — es el único** |

**Corrige a la v0.2**, que prohibía los tres campos por igual. La verificación demuestra que **solo `fuente`** porta el oráculo. Prohibir `razon` y `regla` habría roto `RF-23` sin necesidad.

### 4.4 Plano A · Metadato bruto del arnés — PROHIBIDO

**`criticidad.fuente` en bruto no viaja.** Es el único campo verificado que porta identificadores de caso. No puede ser consumido por `ADR002-A`, `B`, `C` ni `D`, ni por el motor **como señal**, ni por índices, ranking, expansión o construcción de candidatas. Permanece privado del arnés y en su traza privada.

### 4.5 Plano B · Criticidad aplicada segura — contrato común

```
CriticidadAplicada(
    nivel,                 # del corpus, conforme al vocabulario de niveles P2
    razon_segura,          # = criticidad.razon, verbatim
    fuente_de_politica,    # derivada de criticidad.fuente por la tabla de §4.6
    regla_de_politica,     # = criticidad.regla, verbatim (CRIT-0x)
)
```

**Requisitos:**

| # | Requisito |
|---|---|
| 1 | **No contiene identificadores de casos** |
| 2 | **No contiene resultados esperados** |
| 3 | **No contiene referencias a `A`/`B`/`C`/`D`** |
| **4a** | **No procede de la adjudicación de resultados del banco** — elegibles, prohibidos, resultados esperados ni grupos esperados |
| **4b** | **Sí puede proceder de una etiqueta de escenario** en el sentido de `B04-Q21` y `§6`: que el corpus etiquete los críticos antes de ejecutar es un origen **canónico**. `4a` y `4b` no se contradicen: prohíben la adjudicación del **resultado**, no la etiqueta del **escenario** |
| 5 | Su asignación queda **congelada antes de ejecutar candidatos** |
| 6 | Se construye por la **regla cerrada** de §4.6, auditable e independiente del resultado |
| 7 | **Un nivel no puede autoasignarse durante la recuperación** (`RF-23`: «prohibir auto-marcado libre»; `Q21`: «no puede auto-marcar por intuición libre») |
| 8 | Un validador **falla cerrado** si cualquier valor de `razon_segura` o `regla_de_politica` llegara a coincidir con un patrón de identificador de caso. Hoy ninguno coincide; el control es **preventivo** para familias sucesoras |

**Usos permitidos:** `G12`; tratamiento previo al límite; **desempate estable y registrado, y razón de orden por resultado**; estado `PARCIAL` por desbordamiento crítico; explicación autorizada; traspaso a B05.

> El uso en el desempate no es una concesión: `B04` M-05 (línea 46) fija el desempate «**por criticidad**, autoridad, ajuste temporal, apoyo directo y ID estable»; `RF-28` (línea 446) exige explicar por resultado «**criticidad y razón de orden**»; `M21` (línea 527) mide el desempate estable. El motor común ya aprobado lo implementa en `engine.py:66-75`. Omitirlo de la lista, como hacía la v0.2, habría prohibido lo que `B04` obliga.

**Usos prohibidos:** generar candidatas; aumentar similitud; alterar `E0-E4`; saltar etapas; **rescatar un elemento que no haya pasado las puertas** —`B04` §11, línea 307: «**Ninguna señal blanda puede rescatar un elemento excluido**»—; favorecer a un candidato.

### 4.6 Regla cerrada de `fuente_de_politica` — preinscrita

Codominio: el vocabulario de `B04-Q21`. Tabla completa sobre los 8 valores del blob congelado, derivada de la razón de política de cada ítem y **no** de ningún resultado esperado:

| `criticidad.fuente` bruta | n | `fuente_de_politica` |
|---|---|---|
| `B04-CA-01`, `B04-CA-02`, `B04-CA-20`, `B04-CA-21` | 4 | `ACTO_EXPLICITO` |
| `B04-CA-42`, `B04-CA-45` | 2 | `REQUISITO_O_DECISION_APROBADA` |
| «Instanciación compartida por B04-CA-26, B04-CA-38 y B04-CA-44» | 12 | `ETIQUETA_DE_ESCENARIO` |
| `REGLA-CRIT-07` | 1 | `REGLA_OPERATIVA_APROBADA` |

**Esta tabla requiere aprobación explícita** (§12) y debe congelarse en el acta de la familia sucesora antes de ejecutar nada.

### 4.7 Plano C · Handoff a B05

El contrato entregado a B05 conserva **íntegramente** `nivel`, `razon_segura`, `fuente_de_politica` y `regla_de_politica`. **No basta con propagar el nivel.**

### 4.8 Cómo se satisfacen `RF-23`, `M19`, `D05` y `Q21` sin exponer el oráculo

| Exigencia | Cómo se satisface | Cómo se evita el oráculo |
|---|---|---|
| **nivel** hasta B05 (`RF-23`) | Se transporta conforme al vocabulario de niveles P2 de §8.1, sin reinterpretación semántica | El nivel no identifica ningún caso |
| **razón** intacta (`RF-23`, `M19`) | **`criticidad.razon` verbatim**: intacta en sentido literal | Verificado: 0 de 19 contienen identificador |
| **fuente** (`RF-23`, `M19`, `D05`) | `fuente_de_politica`, del vocabulario de `Q21` | El identificador de caso **no** viaja |
| **regla aprobada** (`RF-23`, `M19`, `D05`) | **`criticidad.regla` verbatim** (`CRIT-0x`) | Es identificador de **política**, no de caso |
| **«con ID y evidencia»** (`Q21`) | El **ID** es `regla_de_politica` (`CRIT-0x`); la **evidencia** es `razon_segura`, ambos verbatim | Ninguno de los dos es una etiqueta de banco |
| «0 auto-marcados sin regla» (`M19`) | Asignación congelada antes de ejecutar; ninguna etapa puede crear un nivel | Requisitos 5 y 7 |
| «0 exclusiones por presupuesto ordinario» (`M19`, `D05`) | Un crítico solo cae por puerta o por límite duro **declarado** | `RF-24` y §7 |

### 4.9 Lo que se pierde, declarado sin disimulo

1. **La trazabilidad hasta el caso concreto del banco no llega a B05.** Es deliberado: `RF-23` pide procedencia de política, y `Q21` satisface su requisito de ID con la regla `CRIT-0x`. Esa trazabilidad queda en la traza privada del arnés, auditable fuera del canal de recuperación.
2. **`fuente_de_politica` es un enum de cuatro valores** en el que **12 de los 19** ítems del corpus congelado comparten el mismo (`ETIQUETA_DE_ESCENARIO`). El campo pierde capacidad discriminante respecto de la `fuente` bruta, que tenía 8 valores. Se declara porque hace que la comprobación de `M19` sobre «fuente intacta» sea menos exigente de lo que su literalidad sugiere.
3. **Ningún otro campo se transforma.** `razon` y `regla` viajan verbatim, de modo que «intacta» es aquí literal y no un eufemismo.

### 4.10 Consecuencia para la implementación: el enum de niveles

El contrato común vigente define `Criticidad` con **solo dos valores**, `ORDINARIA` y `CRITICA` (`contracts.py:99-104`), y sus consumidores comparan únicamente contra `CRITICA` (`gates.py:216-222`, `stops.py:59`). **El nivel `IMPORTANTE` del corpus —un ítem, `MEM-001`— sería hoy indistinguible de `ORDINARIA`.**

Por tanto el paso de corrección de `common/` (§10, paso 5) **debe incluir explícitamente** la ampliación del vocabulario de niveles y la revisión consiguiente de `G12` y de la parada por críticos pendientes. No se afirma que el nivel viaje «sin transformación»: viaja conforme al vocabulario P2 declarado, y ese vocabulario hay que implementarlo.

---

## 5. Fuente y custodia de `property_key`

Se mantiene la decisión de la v0.2 y se completa su origen. La revisión adversarial encontró que la formulación anterior era **fallo-abierta** y **cerraba la derivación por enumeración**; ambas cosas se corrigen aquí.

### 5.1 Dónde vive: canal lateral de `common`, no campo del ítem

**`property_key` NO es un campo del registro de ítem del corpus, ni de `ItemCanonico`, ni de ninguna estructura que el puerto entregue a un candidato.**

Vive en una **tabla lateral de la proyección experimental, indexada por identidad canónica**, que **solo `common` abre**. Un candidato no puede leerla porque **no la recibe**: la prohibición es estructuralmente imposible de violar, no meramente detectable.

Esto sustituye a la formulación de la v0.2, que la trataba como un campo más y confiaba en un barrido de texto.

### 5.2 Custodia: manifiesto de familia, no registro por ítem

Los metadatos de custodia **no viajan por ítem**. Se declaran **una vez, a nivel de familia**, en su manifiesto:

| Campo de custodia | Dónde vive |
|---|---|
| `fuente_de_asignacion` | manifiesto de la familia |
| `version_del_vocabulario` | manifiesto de la familia |
| `regla_de_validacion` | manifiesto de la familia |

Motivo: `fuente_de_asignacion` y `regla_de_validacion` por ítem estarían **correlacionados con la partición que `property_key` induce** —dos ítems tratados por la misma regla son, casi por definición, el mismo tipo de predicado—, de modo que un candidato que los leyera obtendría la partición por una puerta trasera. Al vivir en el manifiesto, no hay estructura por ítem que filtrar.

Lo único indexado por identidad es el **valor** de `property_key`, y solo en el canal lateral de §5.1.

### 5.3 Regla de derivación: cierre **por referencia**, no por enumeración

**`property_key` no puede derivarse de ningún artefacto de oráculo.** El cierre se expresa por referencia al conjunto completo, para que no dependa de que una lista esté al día:

1. **No puede derivarse de ningún elemento de la lista negra vigente** —la de la v0.1 §6.5, conservada—, **ni de ningún campo que la v0.2 §9.2 y §9.4 declaren prohibido**, ni de `criticidad.fuente` (§4.4). En particular, y sin que la enumeración limite lo anterior: elegibles, prohibidos, resultados esperados, grupos esperados, adjudicaciones, etapas y paradas esperadas, `items[].traza`, `relaciones[].nota`, `entidades[].nota`, **`entidades[].grupo_homonimo`**, `documentos[].traza`, `mensajes[].traza`, `cases_v0_4.json` y `references_v0_4.json` completos, etiquetas `A`/`B`/`C`/`D` y cualquier proyección de `T0`.
2. **Regla positiva, que es la que cierra de verdad:** `property_key` solo puede derivarse del **contenido y las dimensiones declaradas del propio ítem** —su texto, su sujeto, su clase y su ámbito—, y de nada más.
3. **No se calcula durante la consulta.**
4. **La prohibición alcanza también al generador de la familia sucesora**, que no puede leer los artefactos de oráculo al asignar la clave.

### 5.4 Independencia del oráculo: una sola redacción, la fuerte

**`property_key` se asigna antes de generar casos y referencias.** Si por construcción no fuese posible, la regla cerrada debe ser **demostrablemente independiente de los artefactos de oráculo**, no meramente de orden registrado.

Se elimina expresamente la formulación débil de la v0.2 —«una regla cerrada cuyo orden sea demostrable»—, porque **cualquier** construcción determinista la satisface, incluida una que asigne la clave **después** del oráculo. Registrar el orden no impone dirección.

### 5.5 Tratamiento de la ausencia

`null` o desconocido **impide agrupar**, pero **no hace al elemento inelegible**. Es la misma disciplina de §6 para el sujeto ausente.

### 5.6 Naturaleza

Vocabulario **local P2**, **no productivo**. No decide el vocabulario de Sirius 0.2.

### 5.7 La lista blanca se **extiende**: tres categorías, no dos

La v0.2 tenía una lista blanca binaria —lo que un candidato puede consumir frente a lo prohibido— materializada como constante única y **fallo-cerrada ante cualquier campo no listado**. `property_key` y `criticidad.nivel` no caben en ninguna de las dos: no son consumibles por un candidato y tampoco son oráculo.

**Se corrige la afirmación de §2:** la lista blanca **no se conserva sin cambios**; se **extiende** a tres categorías, conservando su mecanismo de fallo cerrado:

| Categoría | Quién puede leerlo | Ejemplos |
|---|---|---|
| **`ENTRADA_DE_CANDIDATO`** | candidatos y `common` | `id`, `kind`, `project_id`, `text`, `polaridad`, `condicion`, `confirmacion`, `validez`, `disponibilidad`, `sensibilidad`, `temporalidad.*`, `ambito`, `autoridad`, `no_usar_como_memoria`, `no_consolidable`, `procedencia`, `entity_ids` |
| **`SOLO_CAPA_COMUN`** | únicamente `common` | `property_key`, `subject_key_experimental` en su uso de agrupación, `criticidad.nivel`, `razon_segura`, `fuente_de_politica`, `regla_de_politica` |
| **`ORACULO_PROHIBIDO`** | nadie del canal de recuperación | todo lo de §5.3 punto 1 |

La constante única sigue siendo **una** y sigue **fallando cerrada**: un campo sin categoría asignada aborta la construcción de la proyección.

### 5.8 Validadores que la familia sucesora debe incluir

| Validador | Qué comprueba | Polaridad |
|---|---|---|
| **Cobertura del campo** | **Todo** ítem lleva el campo en el canal lateral, aunque su valor sea `null`. Falla si alguno carece de entrada | fallo-cerrado |
| **Frontera estructural del valor** | Los ítems con `property_key` **no nula** son exactamente aquellos cuya clase y forma admiten predicado sobre sujeto, según una **propiedad estructural declarada del ítem**. Nunca según su destino en el banco | fallo-cerrado |
| **Formato cerrado** | Pertenencia al vocabulario declarado y a su versión, ambos del manifiesto | fallo-cerrado |
| **Independencia del oráculo** | El generador no leyó ningún artefacto de §5.3 punto 1, y la asignación cumple §5.4 | fallo-cerrado |
| **Inaccesibilidad estructural** | **Lista blanca por contención** sobre los atributos que un candidato puede leer de las estructuras que recibe: `atributos_leidos <= ATRIBUTOS_PERMITIDOS`. Es el mecanismo del precedente real de `ADR002-B` —`assert nombres <= _NOMBRES_PERMITIDOS`, `test_adr002_b_corrupcion_static.py:118-133`—, y **no** una búsqueda de ausencia de una cadena literal, que sería fallo-abierta y la atravesaría cualquier acceso que no deletree el literal | fallo-cerrado |

**Corrige a la v0.2**, que describía el precedente de `ADR002-B` como si fuese un barrido de texto. Es lo contrario: una lista blanca cerrada por contención.

### 5.9 Por qué la cobertura ya no es circular

La v0.2 exigía cobertura sobre «los ítems que deben poder agruparse», conjunto que **solo los grupos esperados del banco** podrían definir — lo que habría violado la propia regla de independencia.

Se sustituye por dos validadores distintos: **cobertura del campo**, que es mecánica y libre de oráculo porque exige el campo en **todos** los ítems; y **frontera estructural del valor**, que decide dónde el valor es no nulo por una propiedad del ítem, no por su papel en un caso. La corrección semántica del valor **no se valida contra los grupos esperados** y no se pretende validarla así.

---

## 6. Sujeto de sonda frente a sujeto definitivo

### 6.1 Qué fue realmente `P-SUJETO-01`, sin el adorno que traía la v0.2

**`P-SUJETO-01: subject_key := id del ítem` fue únicamente la proyección utilizada en las sondas técnicas de suficiencia de `C`.** Es la regla que aplica el único cargador congelado existente (`frozen_corpus.py:301` y `:319`).

**Se retira la caracterización de la v0.2**, que la llamaba «la más restrictiva» y afirmaba que «no crea familias de sujeto». **Es falso, y demostrablemente:**

- los identificadores del blob congelado tienen la forma `MEM-001`…`MEM-079` y `DEC-001`…`DEC-016`;
- `_familias_de_sujeto` de `A` calcula `prefijo = plegar(subject_key).split("-")[0]` (`adr002_a/candidate.py:269`), lo que produce exactamente **`mem`** y **`dec`**;
- ambos tienen longitud 3 y **superan** el umbral `PREFIJO_MINIMO = 3` (`candidate.py:53`, `:270`);
- el puerto los traduce en `WHERE subject_key LIKE 'mem%'` y `WHERE subject LIKE 'dec%'` (`port.py:342` y `:349`).

**Es decir: dos familias que cubren el 100 % del corpus**, acotadas solo por `LIMITE_POR_PREFIJO`. Lejos de ser conservadora, `P-SUJETO-01` es **la proyección más permisiva posible** para la expansión por familia de `E3`.

> **Consecuencia que se declara y no se disimula.** El argumento «a fortiori» con que la v0.2 justificó la elección de proyección **apunta en la dirección contraria a la que decía**: una proyección de sujeto **menos** degenerada daría a `A` **menos** alcance por familia, no más. Por tanto la conclusión de §1 —aceptada para esta versión por decisión expresa del usuario— **no queda reforzada por la elección de proyección, sino condicionada a ella**.
>
> Esta resolución **no reabre** la suficiencia de `C`, conforme a la instrucción recibida. Lo que hace es **registrar el defecto del argumento** y dejar constancia de que, cuando se fije `subject_key_experimental` (§6.2), la conclusión de `C` **debe volver a comprobarse bajo la proyección definitiva** antes de que la ronda primaria se autorice. Se añade como cuestión de aprobación explícita en §12.

**`P-SUJETO-01` NO es, en ningún caso, la proyección definitiva del benchmark.**

### 6.2 `subject_key_experimental`, para la familia sucesora

| # | Requisito |
|---|---|
| 1 | **Fuente explícita y congelada** |
| 2 | **Asignación independiente** de casos, referencias y resultados |
| 3 | **No derivada durante la consulta** |
| 4 | **Permite que identidades distintas con el mismo sujeto real puedan compararse por equivalencia** |
| 5 | **Conserva `null` como ausencia** |
| 6 | La **ausencia no elimina el ítem** |
| 7 | La **ausencia impide la agrupación** |
| 8 | **No puede utilizarse por un candidato como señal adicional no declarada** |
| 9 | Cualquier uso estructural de `A` **debe seguir siendo exactamente el declarado en su ficha sucesora** |

### 6.3 Los requisitos 5, 6 y 7 están **invertidos** en el árbol vigente

No basta con enunciarlos: hoy el código hace lo contrario, y hay que decir dónde.

| Requisito | Qué hace hoy el árbol congelado | Anclaje |
|---|---|---|
| **5 · `null` como ausencia** | **Se pierde**: el puerto hace `subject_key=str(fila[1] or "")`, de modo que `NULL` y cadena vacía son indistinguibles | `port.py:193` (ya registrado como hecho **D8**) |
| **6 · la ausencia no elimina el ítem** | **La ausencia fuerza la agrupación y elimina miembros**: `_agrupar` agrupa por la clave cruda y devuelve solo representantes, de modo que los demás desaparecen del resultado — críticos incluidos | `engine.py:88-92` y `:99` |
| **7 · la ausencia impide agrupar** | **Ocurre lo contrario**: además, `A` **fabrica** un sujeto a partir del primer término significativo del texto cuando la clave está vacía, de modo que `G11` siempre pasa y la ausencia queda enmascarada | `adr002_a/lexical.py`, `sujeto_estructural` |

**Qué debe cambiar, y dónde**, en el paso 5 del plan:

1. **Puerto**: representar la ausencia sin colapsarla a cadena vacía.
2. **`_agrupar`**: no agrupar cuando la clave está ausente.
3. **Fallback de `sujeto_estructural`**: declarar expresamente si `A` conserva la fabricación de sujeto desde el texto —y, si la conserva, que su ficha sucesora lo declare—, porque hoy enmascara la ausencia ante `G11` y ante la parada `S6`.

### 6.4 Qué declara realmente la ficha de `A` sobre la clave de sujeto

La v0.2 enumeraba **dos** usos. La ficha congelada `ficha_ADR002-A_v3.json` declara **tres**:

| Uso | Cita literal de la ficha |
|---|---|
| **`E1`** | «estructurada exacta por clave de sujeto normalizada…» |
| **`E3`** | «…familias de sujeto por **prefijo concreto**» |
| **Validación semántica** | `arquitectura.puertas_previas_comunes`: «lectura semantica por item con marcadores lexicos de negacion y condicion, **clave de sujeto del canon** y marca temporal (B04-RF-17, RF-19)»; y `senal_tardia.validacion_en_e3`: «marcadores lexicos cerrados de negacion y de condicion, **clave de sujeto del canon** y marca temporal del item» |

El tercero es el que gobierna `G11` y la adjudicación de la parada `S6`. Omitirlo, como hacía la v0.2, dejaba fuera precisamente el uso con consecuencias sobre la parada.

Y la definición canónica se cita ahora **literal**, como consta en la ficha y en `candidate.DEFINICION_CANONICA`:

> «expansion escalonada solo lexica/estructurada en todas las etapas E0-E5.»

### 6.5 Un solo valor con cinco consumidores — no dos cosas distintas

**Se retira** la afirmación de la v0.2 de que el eje de agrupación de `common` y la señal estructurada de `A` «son cosas distintas y no se confunden». **En el árbol congelado es un único valor**, `ItemCanonico.subject_key` (`contracts.py:187`), materializado por el puerto desde `memories.subject_key` y `decisions.subject` (`port.py:44`, `:51`, `:193`), con **cinco** consumidores:

| # | Consumidor | Dónde |
|---|---|---|
| 1 | `A` en `E1`, por clave exacta | `candidate.py:149` → `port.py` `por_clave_exacta` |
| 2 | `A` en `E3`, por prefijo de familia | `candidate.py:269` → `port.py:342`, `:349` |
| 3 | `A` en `leer()`, como sujeto validado | `candidate.py:92` |
| 4 | `common` en `_agrupar`, como eje de equivalencia | `engine.py:88-92` |
| 5 | `common` en el **desempate de orden** | `engine.py:66-75` |

**La separación que esta resolución impone es de gobierno, no de implementación**: hoy no hay dos campos. Fijar `subject_key_experimental` es, por tanto, **una sola decisión con cinco efectos simultáneos**, y toda equivalencia que se conceda a `common` se concede a la vez a las tres señales de `A`. Quien apruebe la proyección debe saberlo.

### 6.6 El riesgo no es solo de alcance: también de **orden**

El salvaguarda de la v0.2 hablaba únicamente de «alcance». Es insuficiente. `engine._clave_de_orden` (`engine.py:66-75`) devuelve:

```
(critica, autoridad, candidata.item.subject_key, candidata.item.id)
```

La clave de sujeto es la **tercera clave de ordenación**, por delante de la identidad, y `G12` aplica el límite duro sobre esa lista ya ordenada (`engine.py:190`). **Cambiar la proyección de sujeto reordena la salida de los cuatro candidatos y cambia qué ítems caen fuera del límite duro, sin cambiar necesariamente el alcance de ninguno.**

**Salvaguarda corregida:** si al construir la proyección definitiva resultara que `subject_key_experimental` altera, respecto de lo que la ficha vigente declara, el **alcance**, la **validación de sujeto**, la **adjudicación de parada** o el **orden** de `A`, **eso obliga a declararlo en su ficha sucesora antes de ejecutar** —no a ocultarlo ni a recortar la proyección en silencio.

Y por ese mismo motivo, la elección de `subject_key_experimental` **es también una decisión de ordenación que afecta por igual a los cuatro candidatos**, y se lleva a §12 como tal.

### 6.7 Los cuatro planos, correctamente separados

| Plano | Qué es | Quién lo usa |
|---|---|---|
| **Sujeto de sonda** | `P-SUJETO-01`, `subject_key := id`. Instrumento de una comprobación puntual, con la degeneración de §6.1 | Nadie más. **No se transporta al banco** |
| **Sujeto de la proyección definitiva** | `subject_key_experimental`, con fuente congelada y custodia de §6.2 | La proyección |
| **Uso común para agrupación y orden** | Eje «sujeto» de `B04-Q13`, y tercera clave del desempate | `common` |
| **Uso como señal estructurada de `A`** | `E1`, `E3` y validación en `leer()`, **exactamente como su ficha lo declare** | `A` |

Los cuatro planos son distinguibles **en gobierno**; en la implementación vigente comparten un único campo (§6.5). Separarlos de verdad, si se decide separarlos, es trabajo del paso 5 del plan y debe declararse.

---

## 7. Las dos cardinalidades

### 7.1 Anclaje canónico, citado literal

> **`B04` §15.2, `EXACTA` (línea 380):** «Busca uno o varios objetivos identificados o una respuesta cerrada.» · *Regla de parada:* «S1 permitido solo cuando todos los objetivos están resueltos **y** el control interno confirma que no quedan críticos elegibles pendientes en espacios autorizados.»
>
> **`ACOTADA` (línea 381):** «Busca N resultados, una lista definida o exploración con límite/criterio explícito.»
>
> **`EXHAUSTIVA` (línea 382):** *Definición:* «Busca todos los elementos que cumplen una condición.» · *Regla de parada:* «S1 deshabilitado. Deben agotarse los espacios autorizados o terminar por S2–S7 con estado parcial/explicado.»
>
> **`S1` (línea 385):** «Solo para EXACTA o ACOTADA: objetivos/cuota y soporte satisfechos, **y control interno de críticos pendientes = cero**. Nunca se aplica a EXHAUSTIVA.»
>
> **`B04-Q10` (línea 403):** «Solo se expande cuando falta suficiencia **o críticos** y el siguiente espacio está autorizado.»
>
> **`B04-Q17` (línea 410):** «El límite objetivo puede ampliarse visiblemente para críticos; el límite duro nunca se supera. **Si quedan críticos fuera, se declara incompleto y se solicita ampliación.**»
>
> **`B04-RF-24` (línea 442), íntegra:** «Respetar límite objetivo y límite duro; nunca ampliar el segundo ni ocultar desbordamiento crítico.»
>
> **`B04-RF-25` (línea 443):** «Adjudicar suficiencia interna por cardinalidad y taxonomía completa […].»
>
> **`G12` (línea 306):** «Todos los críticos elegibles se preservan o se declara desbordamiento bajo límite duro; nunca se ocultan.»
>
> **`CA-44` (línea 498):** «Límite duro 5, seis críticos elegibles con empate en el corte. | Aplica desempate estable registrado; **entrega 5, parcial y crítico pendiente**. Si el empate material persiste, no inventa preferencia.»
>
> **Contrato de salida (línea 233):** «Grupos de duplicados | Representante justificado, procedencias adicionales y diferencias preservadas.»
>
> **`B04-Q13` (línea 406) y `RF-20` (línea 438):** conservar procedencias y diferencias; apoyo y refutación nunca se colapsan.

### 7.2 Por qué hacen falta dos contadores — argumento corregido

**Se retira el argumento de la v0.2**, que contraponía `EXACTA` y `EXHAUSTIVA`. Era un **non sequitur**: la cardinalidad es **un campo único** de la petición (`Q02` línea 395, `RF-01` línea 419, `Q10` línea 403, y la tabla de tres filas alternativas de §15.2), de modo que una operación es `EXACTA` **o** `EXHAUSTIVA`, jamás ambas. Un solo contador con regla dependiente del modo habría bastado para esa tensión.

La necesidad real está en lo que **sí coexiste dentro de una misma operación**:

- la **suficiencia** se adjudica sobre **necesidades semánticas** —`S1`, línea 385: «objetivos/cuota»—;
- y **al mismo tiempo** la salida debe conservar **todas** las procedencias y diferencias (línea 233, `RF-20`, `Q13`) y **todo crítico elegible** (`G12` línea 306, `RF-24` línea 442).

Un único contador no puede a la vez decir «esta necesidad ya está cubierta» y «estos cinco documentos deben seguir siendo citables». De ahí los dos.

### 7.3 Deduplicación exacta

**El mismo identificador repetido cuenta una sola vez en todas las cardinalidades.** No hay dos contadores aquí: hay una identidad.

### 7.4 Agrupación de equivalentes: reparto por contador

| Concepto | Contador |
|---|---|
| **Suficiencia — primer conjunto de `S1`**: objetivos y cuota satisfechos | **semántica** |
| **Suficiencia — segundo conjunto de `S1`**: críticos pendientes = cero | **documental** |
| **`EXACTA`**: objetivos identificados | **semántica** |
| **`ACOTADA`**: la cuota `N` | **semántica** — ver §7.5, donde se declara la reinterpretación |
| **Decisión de avanzar de etapa** (`Q10`: «falta suficiencia **o críticos**») | **semántica** para la suficiencia; **documental** para los críticos |
| **Parada `S1`** (solo `EXACTA`/`ACOTADA`) | **semántica**, con la condición documental de críticos |
| **`EXHAUSTIVA`** y su **parada por agotamiento** (`S5`) | **documental**: «todos los elementos»; agrupar **no** reduce lo que hay que agotar |
| **Límite objetivo y límite duro** (`RF-24`, `Q17`) | **documental**: el límite se aplica sobre **resultados entregables**, no sobre unidades semánticas |
| **Recall y cobertura, auditoría, procedencia, trazabilidad, inspección de criticidad, explicación, handoff** | **documental** |

### 7.5 La reinterpretación de `ACOTADA`, declarada y no dada por supuesta

`B04` línea 381 dice «**N resultados**», unidad documental, no «N objetivos». Asignar la cuota al contador semántico **es una reinterpretación**, y se declara como tal en vez de presentarla como derivación.

**Justificación:** `B04-Q13` (línea 406) fija que los miembros de un grupo de equivalentes coinciden en los siete ejes, es decir, **sirven a una única necesidad**. Contar dos miembros del mismo grupo como dos «resultados» de la cuota entregaría al usuario `N` entradas que responden a menos de `N` necesidades — que es lo que la regla 7 de §7.6 prohíbe.

**Requiere aprobación explícita (§12).** Si se prefiere la lectura literal, `ACOTADA` pasa al contador documental y la regla 7 se limita a `EXACTA`.

### 7.6 Reglas que se imponen

1. **Todos los miembros permanecen citables.**
2. **El representante no reemplaza ni elimina a los miembros.**
3. **`G12` inspecciona todos los miembros**, no solo representantes.
4. **Un crítico no queda oculto por pertenecer a un grupo.**
5. **Bajo límite duro, los miembros de un grupo se entregan hasta agotar el límite**, aplicando el desempate estable y registrado de `M-05` (línea 46); **los miembros omitidos se contabilizan y se declaran como desbordamiento visible** (`G12` línea 306, `RF-24` línea 442). **Nunca se omiten en silencio y nunca se amplía el límite duro.**
   > **Corrige a la v0.2**, que imponía que «el grupo es atómico frente al límite». Esa regla **no se deriva de ninguna fuente** —`atóm` no aparece en `B04` referido a grupos—, se contradecía a sí misma, y choca frontalmente con `CA-44` (línea 498), que ante seis críticos y límite 5 ordena «**entrega 5, parcial y crítico pendiente**». B04 **sí trunca**; lo que prohíbe es ocultarlo.
6. **Si el límite impide entregar íntegro un grupo, el estado es `PARCIAL` y la razón queda trazada** (`S4` línea 388: «Se declara incompletitud y críticos pendientes»; `Q17` línea 410).
7. **Equivalentes repetidos no pueden satisfacer artificialmente una cardinalidad que pide necesidades semánticas distintas.** En `EXACTA` con dos objetivos identificados, dos miembros del **mismo** grupo satisfacen **uno**, no dos.
8. **En `EXHAUSTIVA`, `S1` sigue deshabilitado** y la salida cuenta por `cardinalidad_documental`: agrupar **no** reduce lo que hay que agotar. La parada es `S5` por agotamiento, o `S2`–`S7`.
9. **Regla de precedencia, que la v0.2 no tenía.** `S1` **no puede adjudicarse** si el límite impide entregar íntegro cualquier grupo que compute en la cuota, o si quedan críticos elegibles pendientes. En ese caso **prevalece `S4` con estado `PARCIAL`** y críticos pendientes declarados.
   > Sin esta regla el contrato no es ejecutable: con `ACOTADA` de cuota 5, límite duro 5, cinco grupos y tres miembros en el primero, la operación quedaría **a la vez** suficiente por `S1` y `PARCIAL` por las reglas 5 y 6. `Q17` zanja la dirección: «si quedan críticos fuera, **se declara incompleto**».

---

## 8. Familia sucesora de conformidad

Procede porque el veredicto de `C` es **B**. **La v0.4 permanece íntegra**; la familia se materializa junto a ella, conforme a el acta de congelación del corpus v0.4, **§7 punto 2**.

### 8.1 La familia debe cerrar TODO lo experimental nuevo, no solo el discriminante

| # | Artefacto o dato | Contenido |
|---|---|---|
| 1 | **`property_key`** | Valor, fuente de asignación, versión de vocabulario y regla de validación por ítem agrupable (§5) |
| 2 | **`subject_key_experimental`** | Fuente congelada y custodia de §6.2 |
| 3 | **`CriticidadAplicada` segura**, o la **regla cerrada** que la produce | Con la asignación congelada antes de ejecutar (§4.4) |
| 4 | **Vocabularios P2** | `CONFIRMACION`, `VALIDEZ`, `DISPONIBILIDAD`, `SENSIBILIDAD`, `AUTORIDAD`, `AMBITO`, niveles de criticidad, y el vocabulario de `property_key` |
| 5 | **Nueva arista discriminante de `C`** | Tipo distinto de supersesión y conflicto |
| 6 | **Extremos del discriminante** | Dos ítems sintéticos, con **cero** tokens de contenido compartidos bajo la regla de tokenización del índice, verificado mecánicamente; sujetos distintos; **mismo proyecto**, para que ni el ámbito sea la señal ni `G4` los separe |
| 7 | **Caso funcional** | Semilla alcanzable por `A`; destino no alcanzable por `A` completo `E0-E5` |
| 8 | **Referencia independiente** | Derivada **después**, por regla cerrada, con orden auditable |
| 9 | **Validadores** | Los de v0.4 más: **censo de criticidad propio de la familia**, con sus constantes recomputadas y congeladas —**no** las de v0.4 (§3.2)—; cobertura y formato de `property_key`; independencia del oráculo; patrón de identificador de caso sobre `razon_segura` y `regla_de_politica` (§4.5 requisito 8); prohibición estática de uso en candidatos; y cero solapamiento léxico del discriminante |
| 10 | **Manifiesto sucesor** | Cierra de forma **inequívoca la familia completa utilizada**, incluidos los artefactos que no cambian |
| 11 | **Auditoría independiente** | Con las mismas puertas que la v0.4 |
| 12 | **Acta de congelación propia** | Blobs nuevos; los siete de v0.4 **intactos** |

**Se versionan únicamente los artefactos afectados**, pero el manifiesto cierra la familia entera.

### 8.2 Lo que permanece intacto

- **Corpus v0.4** íntegro.
- **`performance_corpus_v0_2.json`** íntegro.
- **Rederivación T0 de `TOL-208`** íntegra **mientras no cambie ninguna de las guardas que su arnés verifica realmente**, que son más amplias de lo que la v0.2 enunciaba: `rederivation_protocol.fallos_de_corpus` recorre **todos** los blobs de `CORPUS_CONGELADO` —los siete de v0.4, no solo el de rendimiento—, `fallos_de_linea_base` verifica el blob de la línea base histórica, y `fallos_de_ficha` exige una ficha de `T0` en estado `CONGELADA`. Como §8.1 punto 12 mantiene intactos los siete blobs de v0.4, en la práctica nada se rompe; pero la condición se enuncia como el arnés la implementa, no más estrecha.

### 8.3 La proyección T0 de la familia

`experiments/adr002/benchmark/t0_preexecution_projection_v0_2.json` (blob observado `3a241839b7eba84f12a3bbb3c643a17f7b0d0f91`) declara `version_contrato: "0.4"` y proyecta **todos** los casos funcionales. El acta de congelación v0.4 lo registra como **`NO_NORMATIVO_NO_CONGELABLE`** y su §6 prohíbe modificarlo.

La familia sucesora debe **declarar expresamente** qué hace con él:

- **si se regenera**, se declara como artefacto **no congelable** de la familia, con su blob observado y su `version_contrato` nueva;
- **si no se regenera**, se declara así y se justifica cómo se cumple entonces la regla del manifiesto de que ningún congelable contenga previsiones sobre `T0`.

**No basta con omitirlo**, que es lo que hacía la v0.2.

### 8.4 Participación de T0 — corregida

`T0` **participará en los casos funcionales de la familia sucesora cuando el benchmark sea autorizado**, con estas condiciones y esta advertencia:

- **no adquiere el motor común;**
- **no adquiere las dimensiones de los candidatos;**
- **no se emite automáticamente una ficha `T0 v2`** solo por cambiar la familia de conformidad;
- una **ficha sucesora de `T0` solo procederá** si cambia algún valor congelado de su propia ficha, su implementación o su protocolo aplicable;
- y si procediera, la propia ficha congelada declara la consecuencia, que es vinculante: «cualquier modificación posterior obligará a nueva versión de ficha **y a repetir las ejecuciones ya realizadas**» — es decir, `rederivacion_t0_v0.1` y `v0.2`.

> **Advertencia que la v0.2 no daba y que cambia el plan.** La v0.2 decía que `T0` participaría «mediante su arnés real». **Ese arnés no existe para casos de conformidad.** El arnés real que su ficha nombra —`run_rederivation --check`— está **bloqueado por blob al corpus de rendimiento** (`frozen_corpus.py:51-52`, que falla cerrado ante otro blob) y deriva exactamente **tres** escenarios de rendimiento. Construir un arnés de conformidad para `T0` **es un cambio de implementación de `T0`** y, por la regla anterior, **obligaría a ficha sucesora de `T0` y a repetir sus ejecuciones**.
>
> Se declara aquí para que la decisión se tome con el coste a la vista, y **no** se presenta como si `T0` pudiera participar sin más.

### 8.5 Fichas de los candidatos

Las fichas sucesoras de `A`, `B`, `C` y `D` **deben citar la familia efectiva utilizada**, no «la v0.4» genéricamente.

---

## 9. Discrepancias del sustrato léxico declarado de T0

**Se mantiene como hallazgo separado, y son DOS, no una.** La v0.2 solo registró la primera.

La frase completa de la ficha congelada es (`ficha_T0-control_v1.json`, `arquitectura_de_control.sustrato_lexico`):

> «FTS5 medido de Sirius 0.1 (**tabla `items_fts`** con **unicode61 y remove_diacritics 2**), sin alternativa ni índice adicional»

| # | Discrepancia | Evidencia |
|---|---|---|
| **D-T0-1** | **Nombre de tabla.** La ficha dice `items_fts`; la cadena canónica crea **`knowledge_fts`** (`61be4bb269bf:116`). `items_fts` **no aparece en ningún otro punto del repositorio**: la ficha es su única ocurrencia | migración `61be4bb269bf` |
| **D-T0-2** | **Parámetro del tokenizador.** La ficha declara **`remove_diacritics 2`**; el `CREATE VIRTUAL TABLE` de la migración **no lleva cláusula `tokenize=`** —la única aparición de «tokenize» en el fichero está en una cadena de documentación—, de modo que FTS5 aplica su **predeterminado**: `unicode61` con **`remove_diacritics 1`** | `61be4bb269bf:114-116`; ausencia de `tokenize=` verificada |

Se declara:

1. **Se resolverán mediante una fe de erratas específica**, cuyo alcance es **del sustrato léxico declarado de `T0`**, no solo del nombre de la tabla.
2. **No se mezclan con la aprobación de esta resolución.**
3. **No invalidan retroactivamente la medición real**, que corrió contra la base real y su índice real.
4. **Deben cerrarse antes de autorizar la comparación primaria**, para que la identidad documental del control sea exacta — y con mayor motivo `D-T0-2`, porque el plegado de diacríticos es exactamente la regla de tokenización sobre la que se apoyan las condiciones de diseño del discriminante de §8.

**La ficha de `T0` no se modifica** y **la fe de erratas no se emite todavía.**

---

## 10. Plan de una sola ola

| Paso | Contenido |
|---|---|
| **1** | Aprobar la resolución v0.3 |
| **2** | Materializar y congelar la familia sucesora de conformidad |
| **3** | **Cerrar la fe de erratas del sustrato léxico declarado de `T0`** — las **dos** discrepancias de §9 |
| **4** | Construir la proyección experimental |
| **5** | Corregir `common/` **una sola vez**. Incluye explícitamente **ampliar el vocabulario de niveles de criticidad** —hoy `Criticidad` solo tiene `ORDINARIA` y `CRITICA`, y el nivel `IMPORTANTE` del corpus sería indistinguible de `ORDINARIA`— y revisar en consecuencia `G12` (`gates.py:216-222`) y la parada por críticos pendientes (`stops.py:59`) |
| **6** | Emitir fichas sucesoras de `A` y `B` |
| **7** | Repetir pruebas completas |
| **8** | Reaprobación explícita de `A` y `B` |
| **9** | Implementar, congelar, probar y aprobar `C` |
| **10** | Implementar, congelar, probar y aprobar `D` |
| **11** | Solicitar **aparte** la autorización del benchmark |

**Ninguno de estos pasos queda autorizado por esta resolución.**

---

## 11. Auditoría adversarial de esta versión

Se sometieron los dos borradores a refutación adversarial independiente **antes** de publicarlos. **La refutación tumbó veintiuna afirmaciones de mi propio borrador**, todas verificadas por mí contra el canon y el árbol antes de aceptarlas. Se registran aquí con su corrección, porque ocultar una refutación que prosperó sería exactamente lo que este expediente prohíbe.

### 11.1 Lo que la refutación tumbó, y cómo se corrigió

| # | Afirmación del borrador | Por qué caía | Corrección aplicada |
|---|---|---|---|
| **R1** | «`P-SUJETO-01` es la más restrictiva; no crea familias de sujeto» | **Falso.** `MEM-001`→`mem`, `DEC-001`→`dec`, ambos ≥ `PREFIJO_MINIMO`, luego `LIKE 'mem%'`/`LIKE 'dec%'` cubren el 100 % del corpus. Es la proyección **más permisiva** para `E3` | §6.1 reescrita; §1 incorpora la salvedad; §12 punto 9 |
| **R2** | «el eje de `common` y la señal de `A` son cosas distintas y no se confunden» | **Falso.** En el árbol vigente es **un único campo** con **cinco** consumidores | §6.5 nueva, con la tabla de consumidores |
| **R3** | El salvaguarda acotaba el riesgo a «alcance» | Insuficiente: `subject_key` es la **tercera clave del desempate** (`engine.py:66-75`) y `G12` recorta sobre la lista ya ordenada | §6.6 nueva; §12 punto 8 |
| **R4** | Enumeraba **dos** usos de la clave declarados por la ficha de `A` | La ficha declara **tres**: el tercero gobierna `G11` y la parada `S6` | §6.4, con las tres citas literales |
| **R5** | «control estático que falle si la cadena aparece», presentado como el precedente de `ADR002-B` | **Polaridad invertida**: el precedente es `assert nombres <= _NOMBRES_PERMITIDOS`, lista blanca **fallo-cerrada**; lo propuesto era fallo-abierto | §5.1 y §5.8: `property_key` deja de ser campo del ítem y pasa a canal lateral; validador por contención |
| **R6** | Cerraba la derivación de `property_key` **por enumeración** | Dejaba abiertas vías reales: `entidades[].grupo_homonimo` y `criticidad.*` | §5.3: cierre **por referencia** más regla positiva |
| **R7** | «orden demostrable» como vía de independencia | **Vacuo**: lo cumple cualquier construcción determinista, incluida una posterior al oráculo | §5.4: una sola redacción, la fuerte |
| **R8** | Requisito 4 «no procede de adjudicaciones» junto a `fuente_de_politica` admitiendo «adjudicación de prueba» | **Contradicción interna**: 12 de los 19 críticos proceden por construcción de una etiqueta de escenario | §4.5: requisitos **4a** y **4b** separados |
| **R9** | «El grupo es atómico frente al límite» | **No derivable y contraria a `CA-44`** (línea 498), que ante seis críticos y límite 5 ordena «entrega 5, parcial y crítico pendiente». B04 **sí** trunca; lo que prohíbe es ocultarlo | §7.6 regla 5, reescrita sobre `CA-44`, `Q17`, `G12` y `RF-24` |
| **R10** | `EXHAUSTIVA` asignada a **las dos** columnas en filas contiguas | Contradecía la propia regla 8 | §7.4: reparto corregido; `EXHAUSTIVA` y su parada por agotamiento son **documentales** |
| **R11** | `ACOTADA` asignada al contador semántico **sin anclaje** | `B04` línea 381 dice «N **resultados**», no «N objetivos» | §7.5: se declara como **reinterpretación** y se lleva a §12 |
| **R12** | «Suficiencia» atribuida en exclusiva al contador semántico | `S1` es una **conjunción** con una condición documental —críticos pendientes = cero— | §7.4: suficiencia desglosada en sus dos conjuntos |
| **R13** | El argumento de que hacían falta dos contadores | **Non sequitur**: `EXACTA` y `EXHAUSTIVA` nunca coexisten; la cardinalidad es un campo único | §7.2: argumento rehecho sobre lo que **sí** coexiste |
| **R14** | Faltaba regla de precedencia entre `S1` y `PARCIAL` | Caso construible en que la misma operación queda suficiente **y** parcial | §7.6 regla 9 |
| **R15** | `RF-24` citada entre comillas **sin ser literal**, con elisión no marcada | La parte elidida es la que obliga sobre el límite objetivo | §7.1: citada íntegra; y `EXHAUSTIVA` separada en sus dos celdas |
| **R16** | «conforme a su propia acta **§111**» | **La cita no existe.** El acta tiene §0-§7; `111` era un número de **línea** que arrastré desde la v0.1 como si fuese una sección. La regla real es **§7 punto 2** | Corregida en todo el documento |
| **R17** | La discrepancia de `T0` era **una** | Son **dos**: además del nombre de tabla, la ficha declara `remove_diacritics 2` y la migración crea el índice **sin cláusula `tokenize=`**, luego rige el predeterminado `remove_diacritics 1` | §9 reescrita; alcance de la fe de erratas ampliado |
| **R18** | «`T0` participará mediante su **arnés real**» | **Ese arnés no existe para conformidad**: el real está bloqueado por blob al corpus de rendimiento y deriva tres escenarios. Construirlo es cambio de implementación y **obliga a ficha sucesora de `T0` y a repetir sus ejecuciones** | §8.4, con la advertencia y su coste a la vista |
| **R19** | La familia sucesora omitía la **proyección T0** | `t0_preexecution_projection_v0_2.json` está ligado por `version_contrato` a **todos** los casos funcionales y el acta prohíbe modificarlo | §8.3 nueva |
| **R20** | «rederivación íntegra **mientras el corpus de rendimiento no cambie**» | Condición **más estrecha** que la guarda real: `fallos_de_corpus` recorre los **siete** blobs, más la línea base y el estado `CONGELADA` de la ficha | §8.2 reescrita como el arnés la implementa |
| **R21** | §8.4 enunciaba solo el **disparador** de una ficha sucesora de `T0` | La ficha congelada declara además la **consecuencia**: obliga a **repetir las ejecuciones ya realizadas** | §8.4, con la cita literal |

Además, la refutación mostró que **la prohibición de `razon` y `regla` de la v0.2 era más amplia que la evidencia**: solo `fuente` porta identificadores de caso (§4.3). Corregirlo permite cumplir `RF-23` literalmente en vez de romperlo.

### 11.2 Tesis que resistieron

| # | Tesis | Resultado |
|---|---|---|
| 15 | Recuento de criticidad exacto y verificador no vacuo | **Resiste.** 76/18/1/19 reproducido de forma independiente; cuatro mutaciones lo hacen fallar |
| 16 | La criticidad aplicada satisface `RF-23`, `M19`, `D05` y `Q21` | **Resiste tras corregirse** con `razon` y `regla` verbatim y el ID de política de `Q21` |
| 19 | Las dos cardinalidades no ocultan un crítico ni truncan un grupo | **Resiste**: `G12` inspecciona miembros y el grupo es atómico |
| 20 | La familia sucesora cierra todo lo nuevo | **Resiste**, con la corrección de que su censo lleva **sus propias** constantes |
| 21 | No se reabre la suficiencia de `C` | **Resiste**: no se repitieron sondas; el defecto de argumento se **registra y condiciona**, no se reinvestiga |
| 22 | No se reescribe nada | **Resiste**: v0.1 y v0.2 íntegras; `4a686c3` y `d44ade8` intactos; sin rebase, squash, amend ni force-push |
| 23 | El plan no autoriza el benchmark | **Resiste**: paso 11 separado y explícito |

---

## 12. Cuestiones que requieren aprobación explícita

1. El contrato de criticidad de tres planos y el handoff completo a B05 (§4), incluida la adopción del vocabulario de `B04-Q21` frente al del glosario (§4.2).
2. **La tabla de mapeo de `fuente_de_politica` de §4.6**, que debe congelarse en el acta de la familia sucesora antes de ejecutar nada.
3. Que la trazabilidad hasta el caso del banco **no** viaje a B05, y quede solo en la traza privada del arnés (§4.9).
4. La ampliación del vocabulario de niveles de criticidad en `common/` (§4.10 y §10 paso 5).
5. El origen y la custodia de `property_key`: canal lateral de `common`, custodia en el manifiesto, cierre por referencia y **cinco** validadores fallo-cerrados (§5).
6. La **extensión de la lista blanca a tres categorías** (§5.7), que la v0.2 no contemplaba.
7. `subject_key_experimental` y la separación de gobierno de los cuatro planos de sujeto (§6.7), **sabiendo que en el árbol vigente es un único campo con cinco consumidores** (§6.5).
8. Que la elección de `subject_key_experimental` **es también una decisión de ordenación**, porque la clave de sujeto es la tercera clave del desempate y afecta por igual a los cuatro candidatos bajo límite duro (§6.6).
9. **Que la conclusión de `C` se vuelva a comprobar bajo la proyección definitiva** antes de autorizar la ronda primaria, dado el defecto de argumento registrado en §1 y §6.1.
10. Los tres cambios de `common/` que exigen los requisitos 5, 6 y 7 sobre la ausencia de sujeto (§6.3).
11. Las dos cardinalidades y las **nueve** reglas de §7.6, incluida la **regla de precedencia** que impide que `S1` y `PARCIAL` se adjudiquen a la vez.
12. **La reinterpretación de `ACOTADA`** como cuota semántica (§7.5), que `B04` línea 381 enuncia como «N **resultados**». Si se prefiere la lectura literal, `ACOTADA` pasa al contador documental.
13. El alcance de la familia sucesora (§8.1) y la regla de no emitir ficha `T0 v2` automáticamente (§8.4).
14. Tratar **las dos discrepancias del sustrato léxico de `T0`** como fe de erratas separada y **cerrarla antes** de autorizar la comparación primaria (§9).
15. El tratamiento de la **proyección T0** en la familia sucesora (§8.3) y la **advertencia sobre el arnés de conformidad de `T0`**, que no existe y cuya construcción obligaría a ficha sucesora y a repetir sus ejecuciones (§8.4).
16. El plan de once pasos (§10).
17. Todo lo heredado de la v0.2 que se conserva (§2, párrafo final), con la salvedad declarada de la lista blanca.

---

## 13. Estado

**PROPUESTA. NO APROBADA.**

- El contrato común **no se modifica**.
- `ADR002-A v3` y `ADR002-B v5` permanecen **aprobadas e intactas**; ninguna decisión aprobada anterior queda anulada.
- `T0-control` intacto. Corpus v0.4 intacto. Toda la implementación intacta.
- **El benchmark permanece bloqueado.**
- La ronda primaria sigue siendo `T0 + A + B + C + D`, **sin reducción**.
- Las **v0.1 y v0.2 se conservan**; esta versión las sustituye **únicamente en el plano documental de propuesta**.
- `evidence/adr001-spikes` **no se ha movido**; PR #117 sigue abierto, sin fusionar y con cabeza en `a074eb5`.
