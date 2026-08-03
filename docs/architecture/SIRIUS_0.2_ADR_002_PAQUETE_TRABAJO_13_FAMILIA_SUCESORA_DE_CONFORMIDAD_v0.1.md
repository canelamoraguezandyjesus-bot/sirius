# SIRIUS 0.2 · ADR-002 · Paquete de trabajo 13

## Preinscripción de la familia sucesora de conformidad `v0.5`

**Estado:** PREINSCRITO · **Versión:** v0.1
**Rama:** `evidence/adr001-spikes` · **HEAD de partida verificado:** `e3e143605a1a79572dae1b8fe115937c63e44fce`
**HEAD tras la corrección de Quality:** `e4fa2901efc940d4fb1509da576f3ed01a80411a`
**PR:** #117, **abierto y sin fusionar**

**Autoridad que ejecuta este paquete:**

| Documento | Blob verificado en este HEAD |
|---|---|
| `SIRIUS_0.2_ADR_002_RESOLUCION_PREBENCHMARK_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v1.0_APROBADA.md` | acta de aprobación |
| `SIRIUS_0.2_ADR_002_RESOLUCION_PREBENCHMARK_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v0.4_PROPUESTA.md` | `191edb43df37a6cd9220212815ee52a1c4b0397e` |
| `SIRIUS_0.2_ADR_002_PAQUETE_RESOLUCION_05_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v0.4.md` | `8e583876aac9f40144ec2a7db2c2270008bf4320` |

Este paquete ejecuta **exclusivamente el paso 1** del plan aprobado (acta v1.0 §4): «materializar y congelar la familia sucesora de conformidad».

> **No autoriza** la fe de erratas léxica, el arnés de conformidad de `T0`, la proyección experimental ejecutable, la corrección de `common`, fichas sucesoras de `A` o `B`, la implementación de `C` o `D`, el benchmark, ninguna medida de rendimiento, la elección de ganador, tocar Sirius 0.1 productivo ni fusionar el PR #117.

---

## 0. Convención de tiempo verbal

Se conserva la de la resolución v0.4 §0 y se aplica sin excepción:

| Marca | Significado |
|---|---|
| **HOY** | comportamiento **actual verificado** sobre este árbol, con su anclaje |
| **DEBERÁ** | **requisito** de la familia sucesora. No describe nada que exista todavía |

---

## 1. Identidad de la familia sucesora

| | |
|---|---|
| **Versión de contrato** | **`0.5`** |
| **Hereda de** | familia v0.4, congelada por `SIRIUS_0.2_ADR_002_CONGELACION_CORPUS_v0.4_APROBADA.md` |
| **Semilla compartida** | `20260726` — la misma de v0.4 (`schema_v0_4.SEMILLA`); un cambio de semilla regeneraría material congelado y está prohibido |
| **Ahora declarado** | `2026-06-15T00:00:00Z` — sin cambios |
| **Custodia** | **append-only**: la familia se materializa **junto a** la v0.4 |
| **Estado al preinscribirse** | `PROPUESTO_NO_CONGELADO` hasta su acta propia |

### 1.1 Por qué `v0.5` y no otra numeración

La convención real del repositorio, verificada sobre el árbol, es de **dos planos**:

1. **Versión de contrato de familia** — un único número que nombra a la familia entera: `version_contrato` vale `"0.4"` en `conformance_corpus_v0_4.json`, en `benchmark_manifest_v0_4.json` y en `schema_v0_4.VERSION_CONTRATO`.
2. **Versión propia de cada artefacto** — cada fichero lleva su número y **solo lo incrementa cuando su contenido cambia**. La familia v0.4 lo demuestra: contiene `pdp_cases_v0_3.json`, `pdp_harness_rules_v0_2.json` y `performance_corpus_v0_2.json` sin renumerarlos.

La sucesora de `0.4` es por tanto **`0.5`**, y **ningún artefacto se renumera por simpatía**: solo cambia de número el que cambia de bytes.

---

## 2. Inventario heredado, verificado por blob

Los siete congelables de la v0.4, comprobados sobre este HEAD con `git rev-parse HEAD:<ruta>`:

| # | Artefacto (`experiments/adr002/benchmark/`) | Blob | Destino en la v0.5 |
|---|---|---|---|
| 1 | `conformance_corpus_v0_4.json` | `c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48` | **origen** del sucesor; intacto |
| 2 | `cases_v0_4.json` | `072753b96f4162fe88ce9c96660296349225c7be` | **origen** del sucesor; intacto |
| 3 | `references_v0_4.json` | `3fc9a63705144bf543266de129e17a17ab31c568` | **origen** del sucesor; intacto |
| 4 | `pdp_cases_v0_3.json` | `2eee45a04dee3d72f52ad00dfd46023d7c5e2199` | **heredado sin cambio** |
| 5 | `pdp_harness_rules_v0_2.json` | `86e4f4ea6b4af3d445ec0f71c9772b46751a202b` | **heredado sin cambio** |
| 6 | `performance_corpus_v0_2.json` | `4e9e2746e49b158a43eda7826b47c78c41b36e90` | **heredado sin cambio** |
| 7 | `benchmark_manifest_v0_4.json` | `fa9a2f2b5d8d65aed811f039b2b279c5350d2132` | **origen** del sucesor; intacto |

**Excluido de la congelación v0.4 y observado aquí:**

| Artefacto | Blob observado | Estado |
|---|---|---|
| `t0_preexecution_projection_v0_2.json` | `3a241839b7eba84f12a3bbb3c643a17f7b0d0f91` | `NO_NORMATIVO_NO_CONGELABLE` |

**Código heredado sin versionar de nuevo:** `canonical_source_v0_4.py` —el canon `.docx` no cambia—, `schema.py`, `schema_v0_2.py`, `schema_v0_3.py`, `validate_corpus.py` y los validadores y pruebas históricos.

---

## 3. Artefactos sucesores y orden de generación

### 3.1 Los siete artefactos nuevos o versionados

| # | Artefacto | Versión | Qué añade sobre la v0.4 |
|---|---|---|---|
| 1 | `conformance_corpus_v0_5.json` | **0.5** | el delta relacional discriminante de §8: **2 ítems, 2 entidades, 1 proyecto y 1 relación** |
| 2 | `subject_keys_v0_1.json` | **0.1** | canal lateral de `subject_key_experimental` (§6) |
| 3 | `property_keys_v0_1.json` | **0.1** | canal lateral de `property_key` (§5) |
| 4 | `applied_criticality_v0_1.json` | **0.1** | plano común seguro de criticidad (§7) |
| 5 | `cases_v0_5.json` | **0.5** | el caso funcional del discriminante (§9) |
| 6 | `references_v0_5.json` | **0.5** | la referencia independiente del discriminante (§9) |
| 7 | `benchmark_manifest_v0_5.json` | **0.5** | manifiesto sucesor que cierra la familia entera (§4) |

### 3.2 Código de la familia

| Módulo | Papel |
|---|---|
| `schema_v0_5.py` | vocabularios P2, clasificación por terna, constantes y censos congelados |
| `build_corpus_v0_5.py` | **generador determinista** de los siete artefactos sucesores |
| `validate_corpus_v0_5.py` | validadores, con oráculo independiente del generador |
| `test_corpus_contract_v0_5.py` | pruebas positivas y **negativas por mutación** |

### 3.3 Orden de generación, que es la prueba de anterioridad

El orden **no es una preferencia de estilo**: es el mecanismo por el que §5.4 de la resolución («`property_key` se asignará **antes** de generar casos y referencias») queda demostrado y no meramente declarado.

```
1. conformance_corpus_v0_5.json     (corpus + delta)
2. subject_keys_v0_1.json           (desde dimensiones declaradas del propio ítem)
3. property_keys_v0_1.json          (desde contenido y sujeto del propio ítem)
4. applied_criticality_v0_1.json    (desde el plano privado, dentro del arnés)
5. cases_v0_5.json                  (adjudicación recalculada)
6. references_v0_5.json             (camino independiente)
7. benchmark_manifest_v0_5.json     (cierre de la familia)
```

**Regla estructural que lo hace verificable:** las funciones generadoras de los pasos 2, 3 y 4 **DEBERÁN** recibir por firma **únicamente el corpus**, y nunca los casos ni las referencias. Un validador comprobará que el paso 5 no puede preceder al 3, porque el 5 consume el resultado del 3 y no al revés.

---

## 4. Manifiesto sucesor · qué DEBERÁ cerrar

Conforme a la resolución v0.4 §8.1 punto 10, el manifiesto **cierra la familia completa, incluidos los artefactos que no cambian**:

1. **Artefactos heredados por blob** — los cuatro de §2 que no cambian, con su blob exacto.
2. **Artefactos sucesores por blob** — los siete de §3.1.
3. **Reglas de generación** — generador, semilla, orden de §3.3 y determinismo.
4. **Versión de contrato** — `0.5`.
5. **Dependencias** — de qué artefacto depende cada uno.
6. **Semilla** — `20260726`.
7. **Orden de materialización** — el de §3.3, literal.
8. **Frontera de custodia** — la de §10, con las cinco capacidades.
9. **Custodia de los canales laterales** — `fuente_de_asignacion`, `version_del_vocabulario` y `regla_de_validacion` **una sola vez aquí**, nunca por ítem (resolución §5.2).
10. **Censos recomputados** — los de §7.4.
11. **Proyección `T0`** — la adjudicación de §11.

---

## 5. `property_key` · canal lateral

### 5.1 Dónde vive

**No es campo del registro de ítem, ni de `ItemCanonico`, ni de ninguna estructura que el puerto entregue a un candidato.** Vive en `property_keys_v0_1.json`, **indexado por identidad canónica**, y **solo `common` lo abrirá**. Un candidato no puede leerlo porque **no lo recibe**.

### 5.2 Contenido por ítem

Exactamente **dos** campos: el identificador canónico y el valor, `null` incluido. **Nada más.** Los tres metadatos de custodia viven una sola vez en el manifiesto (§4 punto 9): repetirlos por ítem correlacionaría la custodia con la partición que la clave induce y entregaría esa partición por una puerta trasera.

### 5.3 Regla cerrada de asignación

**Frontera estructural declarada** — un ítem admite predicado sobre sujeto **si y solo si**:

1. declara **exactamente una** entidad en `entity_ids`; **y**
2. su texto conserva al menos una raíz discriminante tras retirar las palabras funcionales y los tokens del propio sujeto.

Si falla cualquiera de las dos, `property_key` es **`null`**. La frontera es estructural, **nunca el destino del ítem en el banco**.

**Valor** — para los que la superan:

```
raices  = { token[:LONGITUD_RAIZ] : token ∈ tokens(text),
                                    len(token) >= LONGITUD_TOKEN_INFORMATIVO,
                                    token ∉ VACIAS,
                                    token ∉ tokens(nombre canónico y alias del sujeto) }
property_key = "PK-" + sha256("|".join(sorted(raices)))[:12]
```

**Es opaco** —un hash, no texto legible—, **estable** —determinista sobre el contenido congelado—, **no se calcula durante la consulta** —se congela en el canal lateral—, **no genera candidatas** y **no interviene en el ranking**.

### 5.4 Origen admitido y prohibido

**Admitido, y nada más:** el texto del propio ítem, su sujeto declarado, su clase y su ámbito.

**Prohibido como origen** —lista efectiva y autocontenida, sin remisión histórica—: `criticidad.fuente` bruta; `items[].traza`; `relaciones[].nota`; `entidades[].nota` y `entidades[].grupo_homonimo`; `documentos[].traza` y `mensajes[].traza`; `cases_*.json` y `references_*.json` completos; adjudicaciones, resultados esperados, elegibles, prohibidos, grupos esperados, etapas y paradas esperadas; etiquetas `A`/`B`/`C`/`D`; cualquier proyección de `T0`.

**La prohibición alcanza al generador**: la función que asigna la clave **DEBERÁ** recibir el corpus y nada más.

### 5.5 Ausencia

`null` **impide agrupar** pero **no hace inelegible** al elemento. Se registra como ausencia real, nunca como cadena vacía.

### 5.6 Limitación declarada

La regla **no reconoce paráfrasis**: dos ítems que digan lo mismo con palabras distintas recibirán claves distintas y **no se agruparán**. Es una limitación deliberada y **fallo-cerrado**: la duda no fusiona (resolución §7.3). Se declara aquí para que no se descubra como sorpresa.

---

## 6. `subject_key_experimental` · proyección definitiva

### 6.1 Lo que NO se reutiliza

**`P-SUJETO-01` (`subject_key := id del ítem`) queda expresamente descartada** como proyección definitiva. Fue la proyección de las sondas, y la resolución v0.4 §6.1 ya retiró su caracterización como «la más conservadora»: con identificadores de la forma `<CLASE>-<n>` produce los prefijos `mem` y `dec`, ambos por encima de `PREFIJO_MINIMO = 3`, que el puerto traduce en `LIKE 'mem%'` y `LIKE 'dec%'` y **cubren el corpus entero**. Es la **más permisiva** para la expansión por familia de `E3`.

### 6.2 Regla cerrada de la proyección definitiva

**Fuente explícita:** las entidades que el propio ítem declara en `entity_ids`, resueltas contra el bloque `entidades` del corpus.

```
0 entidades declaradas  -> null      (ausencia real)
1 entidad  declarada    -> slug(nombre_canonico de la entidad)
2 o más    declaradas   -> null      (fallo cerrado: dos sujetos no son un sujeto)

slug(s) = caracteres alfanuméricos de NFKD(s.lower()) sin marcas combinantes
```

**El slug no contiene separador.** Es deliberado y es la garantía estructural que impide familias artificiales: `A` calcula su familia de `E3` como `plegar(subject_key).split("-")[0]`, de modo que **sin guion la familia es la clave entera y coincide exactamente con la entidad**. `LIKE 'rotor%'` alcanza al sujeto `rotor` y a nadie más.

### 6.3 Cómo satisface cada requisito de la resolución §6.2

| # | Requisito | Cómo se satisface |
|---|---|---|
| 1 | fuente explícita y congelada | `entity_ids` del corpus congelado; el canal se congela en su acta |
| 2 | independiente de casos, referencias y resultados | la función generadora recibe el corpus y nada más (§3.3) |
| 3 | no derivada durante la consulta | se congela en `subject_keys_v0_1.json` |
| 4 | identidades distintas con el mismo sujeto real comparten clave | tres ítems declaran `ENT-VEHICULO` y reciben `vehiculo` |
| 5 | `null` como ausencia | `null` explícito, nunca cadena vacía |
| 6 | la ausencia no elimina el ítem | el canal cubre **todos** los ítems; la ausencia no filtra |
| 7 | la ausencia impide agrupar | declarado en el contrato del canal |
| 8 | no usable por un candidato como señal adicional no declarada | clasificación por terna de §10 y control por lista blanca |
| 9 | todo uso estructural de `A` **DEBERÁ** ser el declarado en su ficha sucesora | §6.5 |

### 6.4 Cobertura real, declarada sin adorno

**HOY** solo **7 de 95** ítems del corpus v0.4 declaran entidad. La proyección definitiva deja por tanto **la inmensa mayoría de los ítems con sujeto ausente**. Eso **no es un defecto de la proyección**: es lo que el corpus declara, y la alternativa —fabricar un sujeto desde el identificador— es exactamente lo que §6.1 retira.

El censo exacto sobre la familia v0.5 se recomputa y se congela en su acta; **no se copia de aquí**.

### 6.5 Efectos sobre `A`, que se declaran y NO se corrigen aquí

**HOY**, verificado sobre este árbol:

| Hecho actual | Anclaje |
|---|---|
| `port.py` colapsa `NULL` y cadena vacía: `subject_key=str(fila[1] or "")` | `port.py:193` |
| `_agrupar` agrupa por la clave cruda y devuelve **solo representantes** | `engine.py:88-92`, `:99` |
| `A` **fabrica** un sujeto desde el texto cuando la clave está vacía | `lexical.sujeto_estructural` |
| la clave de sujeto es la **tercera** clave de ordenación, y `G12` aplica el límite sobre esa lista ya ordenada | `engine.py:66-75`, `:190` |

Los cuatro son requisitos del **paso 6** del plan aprobado —la corrección única de `common`—, **no de esta misión**. Aquí se **declaran** para que la ficha sucesora de `A` pueda recogerlos, y **no se toca ni una línea** de `common`, `A` ni `B`.

---

## 7. Criticidad aplicada segura · tres planos

### 7.1 Plano privado del arnés — PROHIBIDO cruzar

`criticidad.fuente` **bruta** permanece privada del arnés. Es el único campo del bloque que porta identificadores de caso (`B04-CA-01`, `B04-CA-02`, `B04-CA-20`, `B04-CA-21`, `B04-CA-42`, `B04-CA-45`, `REGLA-CRIT-07` y la instanciación compartida). **No la consume el motor, ni `A`, ni `B`, ni `C`, ni `D`, ni índices, ranking, expansión o construcción de candidatas.**

### 7.2 Plano común seguro

```
CriticidadAplicada(
    nivel,                 # vocabulario de niveles P2
    razon_segura,          # = criticidad.razon, verbatim
    fuente_de_politica,    # producida por la tabla cerrada de §7.3
    regla_de_politica,     # = criticidad.regla, verbatim (CRIT-0x)
)
```

Se materializa en `applied_criticality_v0_1.json`, **indexado por identidad canónica y con cobertura total**, `null` incluido.

### 7.3 Tabla cerrada de `fuente_de_politica`, aprobada

**Dominio:** `criticidad.fuente` bruta. **Evaluación:** dentro del arnés. **Codominio:** el vocabulario de `B04-Q21`. **Qué cruza:** solo el resultado seguro, nunca el dominio.

| `criticidad.fuente` bruta | `fuente_de_politica` |
|---|---|
| `B04-CA-01`, `B04-CA-02`, `B04-CA-20`, `B04-CA-21` | `ACTO_EXPLICITO` |
| `B04-CA-42`, `B04-CA-45` | `REQUISITO_O_DECISION_APROBADA` |
| «Instanciación compartida por B04-CA-26, B04-CA-38 y B04-CA-44» | `ETIQUETA_DE_ESCENARIO` |
| `REGLA-CRIT-07` | `REGLA_OPERATIVA_APROBADA` |

**Fallo cerrado:** una fuente bruta que no esté en la tabla **aborta la construcción**. No hay valor por defecto.

### 7.4 Censo propio, recomputado

Las constantes `95 / 76 / 19 / 18 / 1` son **específicas de la v0.4**. La familia v0.5 lleva **su propio censo, recomputado sobre su propio corpus y congelado en su acta**. Este paquete **no las copia** y **no anticipa sus valores**.

### 7.5 Usos permitidos y prohibidos

**Permitidos:** `G12`; tratamiento previo al límite; desempate estable y registrado; explicación autorizada; estado `PARCIAL` por desbordamiento crítico; **handoff íntegro de los cuatro campos a B05**.

**Prohibidos:** generar candidatas; alterar similitud; saltar etapas; rescatar un elemento que no pasó las puertas; favorecer a un candidato.

### 7.6 Validador preventivo

Un validador **DEBERÁ** fallar cerrado si algún valor de `razon_segura` o `regla_de_politica` coincidiera con un patrón de identificador de caso. **HOY ninguno coincide**; el control es preventivo para familias posteriores.

---

## 8. Delta relacional discriminante para `ADR002-C`

### 8.1 Composición mínima

| Elemento | Contenido |
|---|---|
| Proyecto | **uno nuevo**, de tipo `PROYECTO`, no `GLOBAL` y no miembro de ninguna lista cerrada |
| Entidades | **dos nuevas**, con `grupo_homonimo: null` |
| Ítems | **dos**, mismo proyecto, sujetos distintos, todas las dimensiones P2 declaradas, `criticidad: null` |
| Relación | **una**, explícita, tipada y dirigida |

**Tipo de la relación: `DERIVA_DE`.** Pertenece al vocabulario aprobado (`TIPOS_RELACION`) y es **distinto de la supersesión y del conflicto**, como exige la resolución §8.1 punto 5. Expresa **dependencia**, que es exactamente el fenómeno que `B04 §15.1` asigna a `E3`.

**Ninguna nota revela el caso esperado.** Las notas del delta describen el tipo de relación, nunca su destino en el banco.

### 8.2 Condición léxica, verificada con el tokenizador real

**Origen y destino comparten exactamente cero tokens**, medido con **FTS5 · `unicode61` · `remove_diacritics=1`** —la identidad real del índice, no la declarada por las fichas— mediante una tabla `fts5vocab` sobre los dos textos.

La comprobación ya está ejecutada sobre el vocabulario preinscrito y da **intersección vacía, incluidas las palabras funcionales**. El validador de la familia **DEBERÁ** repetirla mecánicamente; **no se comprueba a ojo**.

Además, y como refuerzo verificado: **todos los tokens de contenido del delta están ausentes del corpus v0.4**. Los únicos tokens que el delta comparte con el corpus son cinco palabras funcionales —`al`, `cada`, `del`, `el`, `una`—, presentes en la lista cerrada `VACIAS` del esquema.

### 8.3 Condición funcional

Con la proyección definitiva ya materializada, el caso **DEBERÁ** demostrar por ejecución real sobre una base con el esquema canónico de Sirius 0.1:

1. una consulta legítima **alcanza la semilla** mediante `ADR002-A`;
2. `ADR002-A` **completo `E0-E5`** —sin recortar el recorrido— **no alcanza el destino**;
3. el destino **supera las puertas comunes** `G1-G10` y `G11`;
4. el destino es **recuperable** por una consulta legítima propia: no es inalcanzable, es inalcanzable **para `A` desde esa semilla**;
5. un **recorrido relacional explícito de un salto** sí aportaría su identificador;
6. **desactivar o borrar la arista elimina ese alcance**;
7. **ningún campo de oráculo participa**.

### 8.4 Lo que el discriminante NO puede ser

- **No** un cambio de orden disfrazado de cambio de alcance: la cardinalidad del caso será `EXHAUSTIVA`, de modo que la escalera se recorre entera y no hay parada por cuota que enmascare el resultado.
- **No** un límite artificialmente estrecho: los límites del caso **no** podrán ser la causa de que el destino falte.
- **No** una alteración de `A`: si la proyección definitiva hiciera que `A` alcanzase el destino, se corrige **el delta**, nunca `A`, sus señales ni sus límites.

### 8.5 Impacto nulo sobre la adjudicación heredada

El delta **DEBERÁ** dejar **byte a byte idénticas** las adjudicaciones de todos los casos y ramas heredados. El generador incluirá un **barrido de impacto** que recalcula los **66** dominios —`DOMINIOS` más `DOMINIOS_RAMA`— con y sin delta y **exige cero cambios**, con el mismo patrón que el `barrido_impacto_dec016` de la v0.4.

El barrido ya está ejecutado sobre el diseño preinscrito: **66 dominios recalculados, cero cambios**. Hay además una razón estructural que lo explica y que el paquete deja escrita: de los 66 dominios, **64 están acotados a proyectos existentes** y no pueden ver un proyecto nuevo; los **dos** que usan `GLOBAL_TODOS` son `B04-CA-01`, anclado al prefijo `redact` —que el delta no contiene—, y `B04-CA-14`, restringido a `grupo_homonimo: JUAN` —que las entidades del delta no declaran—.

---

## 9. Caso funcional y referencia independiente

**El caso se crea DESPUÉS de congelar los datos de entrada que lo sustentan.** Mide **comportamiento observable**; no codifica cómo implementarlo.

**La referencia se calcula por un camino independiente del generador del corpus**, con la misma regla de independencia que la matriz de aceptación de la v0.4 impone al validador: el oráculo de la referencia **no importa ni reutiliza** las funciones de cierre del generador.

**Separación estricta, que el candidato nunca puede cruzar:**

| ENTRADA | ORÁCULO |
|---|---|
| ítems | resultado esperado |
| dimensiones | elegibles |
| claves laterales | prohibidos |
| relación `tipo`/`origen`/`destino` | etapa y parada esperadas |
| petición | explicación esperada |
| | grupos esperados |
| | notas que nombran casos |
| | referencias |

---

## 10. Vocabularios P2 y clasificación por (campo, consumidor, uso)

### 10.1 Naturaleza

Los vocabularios P2 se congelan como **convenciones locales experimentales del banco**. **No se atribuyen a ADR-001 como vocabularios productivos** y **no deciden el vocabulario productivo de Sirius**.

Se congelan: `CONFIRMACION`, `VALIDEZ`, `DISPONIBILIDAD`, `SENSIBILIDAD`, `AUTORIDAD`, `AMBITO`, `POLARIDAD`, `TIPOS_RELACION`, niveles de criticidad y el vocabulario de `property_key`.

### 10.2 Las cinco capacidades

| Capacidad | Quién | Uso autorizado | Uso prohibido |
|---|---|---|---|
| **`ENTRADA_DE_CANDIDATO`** | candidatos y `common` | recuperación | — |
| **`SOLO_CAPA_COMUN`** | únicamente `common` | decidir equivalencia | cualquier lectura por un candidato |
| **`COMUN_Y_SENAL_DECLARADA_DE_A`** | `common` (agrupación y desempate) **y** `A` (los tres usos que su ficha declara) | según consumidor | cualquier uso de `A` no declarado en su ficha |
| **`HANDOFF_A_B05`** | `common` **y B05** | `G12`, límite, explicación y traspaso | lectura por un candidato |
| **`ORACULO_PROHIBIDO`** | nadie del canal de recuperación | ninguno | todos |

### 10.3 La clasificación es estructural y falla cerrada

**No se usa búsqueda de cadenas como control principal.** El mecanismo es **lista blanca por contención** sobre los atributos que un candidato puede leer de las estructuras que recibe —`atributos_leidos <= ATRIBUTOS_PERMITIDOS`—, que es el mecanismo del precedente real de `ADR002-B` (`test_adr002_b_corrupcion_static.py:118-133`). Una búsqueda de ausencia de una cadena literal sería **fallo-abierta** y queda excluida.

**Un campo sin terna asignada aborta la construcción.** La constante sigue siendo **una**.

---

## 11. Tratamiento de `t0_preexecution_projection_v0_2.json`

**Decisión: la familia v0.5 NO regenera la proyección `T0`.**

**Fundamento:**

1. La proyección es `NO_NORMATIVO_NO_CONGELABLE` y el acta de congelación v0.4 §6 **prohíbe modificarla**. No se toca.
2. Regenerarla bajo la v0.5 exigiría proyectar el caso discriminante nuevo sobre `T0`, y esa proyección **presupondría el arnés de conformidad de `T0`, que NO EXISTE** y cuya construcción es un **paso separado** del plan aprobado.
3. La resolución v0.4 §8.3 declara además el coste: construir ese arnés obligaría a **ficha sucesora de `T0`** y a **repetir sus ejecuciones**.

**Cómo se cumple entonces la regla del manifiesto** —cerrar inequívocamente la familia completa—: el manifiesto sucesor **declara expresamente** que la familia v0.5 **no lleva proyección `T0`**, registra el blob observado `3a241839b7eba84f12a3bbb3c643a17f7b0d0f91` de la v0.2 como **observación sin valor vinculante**, y deja constancia de que la futura adjudicación del arnés de `T0` **podrá** usar esta familia **sin que nada aquí presuponga que dicho arnés existe**.

**Ningún artefacto de la v0.5 contiene previsiones sobre `T0`.** El escaneo anti-`T0` sobre la lista de congelables se hereda y se aplica a los sucesores.

---

## 12. Impacto sobre rendimiento y sobre `ADR002-TOL-208`

### 12.1 Rendimiento

`performance_corpus_v0_2.json` se **hereda byte a byte**, con su blob `4e9e2746e49b158a43eda7826b47c78c41b36e90` y su SHA-256 `c5a161cbdaa7ee150c08e663fa72663324375aa6654f3216a73e90d6b182666b`. **La familia v0.5 no mide latencia, memoria ni rendimiento**, y no introduce artefacto alguno que lo permita.

### 12.2 `TOL-208`

El arnés de rederivación verifica, sobre `rederivation_protocol.CORPUS_CONGELADO`, los blobs de los artefactos que allí se declaran; comprueba además la línea base histórica y exige ficha de `T0` en estado `CONGELADA`.

**Corrección de un dato de la resolución v0.4 §8.2.** Aquella afirma que `fallos_de_corpus` «recorre **todos** los blobs de `CORPUS_CONGELADO` —los siete de v0.4, no solo el de rendimiento—». Verificado sobre este árbol, `rederivation_protocol.py:77-84` declara **dos** rutas, no siete: `conformance_corpus_v0_4.json` y `performance_corpus_v0_2.json`.

**La conclusión de la resolución no cambia, y se refuerza:** como la familia sucesora es **append-only** y **ninguno de los dos ficheros cambia de bytes**, `TOL-208` permanece íntegra. La corrección se registra aquí porque el expediente no puede sostener una cifra falsa, aunque su consecuencia sea nula.

---

## 13. Validadores que la familia DEBERÁ incluir

| # | Validador | Polaridad |
|---|---|---|
| 1 | **Cobertura del canal lateral** de `property_key`: **todo** ítem tiene entrada, `null` incluido | fallo-cerrado |
| 2 | **Frontera estructural** de `property_key`: los no nulos son exactamente los que cumplen §5.3 | fallo-cerrado |
| 3 | **Formato cerrado**: pertenencia al vocabulario y versión declarados en el manifiesto | fallo-cerrado |
| 4 | **Independencia del oráculo**: el generador no leyó ningún artefacto prohibido y la asignación cumple el orden de §3.3 | fallo-cerrado |
| 5 | **Inaccesibilidad estructural**: lista blanca por contención (§10.3) | fallo-cerrado |
| 6 | **Cobertura y contrato** de `subject_key_experimental`, con `null` como ausencia real | fallo-cerrado |
| 7 | **Criticidad aplicada segura** completa, con su tabla cerrada y sin identificadores de caso | fallo-cerrado |
| 8 | **Censo de criticidad propio**, con constantes recomputadas y congeladas | fallo-cerrado |
| 9 | **Cero tokens compartidos** del discriminante, con el tokenizador real | fallo-cerrado |
| 10 | **Barrido de impacto**: 66 dominios, cero cambios | fallo-cerrado |
| 11 | **Manifiesto**: cierre completo, heredados y sucesores, por blob | fallo-cerrado |
| 12 | **v0.4 intacta**: los siete blobs congelados, byte a byte | fallo-cerrado |
| 13 | **Frontera entrada/oráculo**: ningún campo de oráculo alcanza el canal común | fallo-cerrado |
| 14 | **Determinismo**: regeneración en directorio temporal, idéntica | fallo-cerrado |

**Semántica declarada:** el informe **acumula** todos los fallos y **no aborta en el primero**, igual que el validador v0.4. Los puntos en los que un validador **aborta** en vez de acumular —fuente bruta fuera de la tabla cerrada (§7.3) y campo sin terna asignada (§10.3)— se declaran **expresamente** como abortos, porque construir una proyección incoherente y después listar sus defectos sería peor que no construirla.

---

## 14. Auditoría independiente · los quince puntos

Antes de congelar, una auditoría adversarial **intentará refutar**:

1. append-only real; 2. independencia del oráculo; 3. cobertura total de canales laterales; 4. ausencia de identificadores de caso en campos comunes; 5. imposibilidad de leer `property_key` desde candidatos; 6. uso autorizado de `subject_key_experimental`; 7. discriminante honesto de `C`; 8. cero tokens compartidos; 9. paso de puertas del destino; 10. reproducibilidad; 11. consistencia del manifiesto; 12. criticidad segura completa; 13. ausencia de benchmark; 14. integridad de `TOL-208`; 15. inexistencia presumida del arnés `T0`.

**Todos los defectos se corrigen antes de congelar.**

---

## 15. Reglas de congelación

1. La familia se congela por **acta propia**, con todos sus blobs.
2. Después del commit de congelación **no se modifica ningún artefacto incluido**.
3. **Cualquier defecto material obliga a una versión sucesora.** No se arregla en silencio.
4. Los siete artefactos de la v0.4 **permanecen idénticos**; la v0.5 se materializa **junto a** ellos.
5. Ninguna acta anterior se reescribe.
6. `common`, `A`, `B`, `src/`, `migrations/` y las pruebas productivas **no cambian**.

---

## 16. Prohibición de benchmark

**El benchmark permanece BLOQUEADO, NO AUTORIZADO y NO EJECUTADO.** La ronda primaria sigue siendo `T0 + ADR002-A + ADR002-B + ADR002-C + ADR002-D`, **sin reducción**.

Materializar esta familia **no** satisface ninguna puerta de arranque, **no** mide nada, **no** compara candidatos y **no** elige ganador. La validación funcional del discriminante (§8.3) es **una comprobación técnica del diseño de la familia, sin métricas**.

Sigue además vigente la condición de la resolución v0.4 §9.5: **ningún benchmark podrá autorizarse con las fichas actuales mientras la discrepancia de identidad del sustrato léxico siga abierta**, y esa fe de erratas **no** se emite en esta misión.

---

## 17. Estado

**PREINSCRITO.** Este paquete no congela nada por sí mismo: fija de antemano qué se va a materializar, en qué orden y bajo qué reglas, de modo que lo que venga después pueda contrastarse contra algo escrito **antes**.
