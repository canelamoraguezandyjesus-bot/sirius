# SIRIUS 0.2 — ADR-002 · Congelación de la proyección experimental v0.1

**Versión:** 1.0
**Estado:** **CONGELADA**
**Fecha:** 3 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** paso **4** del plan aprobado por `..._RESOLUCION_PREBENCHMARK_..._v1.0_APROBADA.md` §4 — «construir la proyección experimental» —, con el contenido que la resolución v0.4 fija en §4.5–§4.10, §5.1–§5.9, §7.2–§7.3 y §8.1.

---

## 1. Qué se congela

La familia v0.6 está congelada **como datos**: cuatro JSON y un canal lateral heredado por blob. Nada de eso se puede ejecutar. La proyección la convierte en **tres planos materializados**, uno por capacidad de la clasificación aprobada.

| Ruta | Blob |
|---|---|
| `experiments/adr002/projection/__init__.py` | `c55838e8abd153851879631c95c6c3fa69f0365a` |
| `experiments/adr002/projection/contracts.py` | `0b60d3db8ee77bde7f16be40ff9770c01af2cc36` |
| `experiments/adr002/projection/build.py` | `29a3217f031efdaaca3f58138e7265203c0b8bad` |
| `experiments/adr002/projection/conftest.py` | `cda0ec04196c5535e20f9905d233b2bad6fdf589` |
| `experiments/adr002/projection/projection_manifest_v0_1.json` | `308a4440fd20d4afce860ec8de1332afd02d47df` |
| `experiments/adr002/projection/test_adr002_proyeccion.py` | `f06931a5775ec5af7c1d1744250510fcf0b23d06` |

**Huella lógica total de los tres planos:** `755cbdfea35969dc570ac9a94a23581f8e433c3575220d344e85c6cb2c47e33d`

Se congela el **contenido lógico**, no el fichero SQLite: un fichero SQLite lleva páginas libres y contadores de cambio, de modo que hashearlo daría un falso negativo de determinismo sobre un contenido que ya está determinado por las tablas base.

### 1.1 Origen, verificado por blob

| Artefacto de la familia v0.6 | Blob observado |
|---|---|
| `conformance_corpus_v0_6.json` | `561d9dee8f215e4692d22f194c5972b09b5d3027` |
| `subject_keys_v0_2.json` | `f6c0f49b4f084d8b5d364d7ec6e1ba7562a5e302` |
| `property_keys_v0_2.json` | `321383be53dc65859000cf557b5b78e8dafc1901` |
| `applied_criticality_v0_1.json` | `7dcbba0031e76d4f0763e0d0b853e59584fe3077` |

**La familia v0.6 no se modifica.** Los cuatro blobs coinciden byte a byte con los que declara su acta de congelación, y una prueba los recomprueba con `git hash-object` en cada ejecución.

---

## 2. Los tres planos y por qué son tres

La resolución v0.4 §5.1 exige que `property_key` viva «en una **tabla lateral de la proyección experimental, indexada por identidad canónica**, que **solo `common` abrirá**. Un candidato no podrá leerla porque **no la recibirá**.»

La proyección cumple eso **con separación física**: un fichero por clase de capacidad, y la ruta del plano reservado no se entrega nunca a un candidato.

| Plano | Fichero | Capacidad | Quién lo abre |
|---|---|---|---|
| Entrada | `entrada.sqlite3` | `ENTRADA_DE_CANDIDATO`, `COMUN_Y_SENAL_DECLARADA_DE_A` | `common`, A, B, C, D, `T0-control` |
| Ejes P2 | `ejes_p2.sqlite3` | `ENTRADA_DE_CANDIDATO` | `common`, A, B, C, D |
| Reservado | `reservado.sqlite3` | `SOLO_CAPA_COMUN`, `HANDOFF_A_B05` | `common`, `B05` |

**`entrada.sqlite3` es el esquema canónico de Sirius 0.1 sin DDL adicional.** Una prueba compara su `sqlite_master` entero contra el de una base recién migrada: si la proyección añadiera una tabla, un índice o un trigger, falla. Ese es el motivo de que los ejes P2 vivan en un fichero aparte y no en columnas nuevas del primero: el puerto declara que lee el esquema canónico intacto, y esa garantía no se puede debilitar por comodidad.

**El plano reservado se abre en modo `ro`.** No es sólo que un candidato no reciba la ruta: `common` tampoco puede escribirla.

---

## 3. Independencia del oráculo — estructural, no prometida

`construir()` recibe **por firma** el corpus y los tres canales laterales. `cargar_familia()` lee exactamente los cuatro nombres de `ARTEFACTOS_FUENTE` y ninguno más.

No hay ruta por la que un artefacto de oráculo pueda entrar: el generador no conoce sus nombres. Una prueba lo comprueba sobre el texto de los dos módulos —`cases_v0_`, `references_v0_`, `resultado_esperado`, `elegibles`, `grupos_esperados`—, y otra recorre las columnas de los dos planos laterales exigiendo que ninguna se llame `nota`, `grupo_homonimo`, `traza` ni `fuente`.

**Lo que no se materializa, y por qué:**

| Campo del corpus | Por qué no cruza |
|---|---|
| `criticidad.fuente` bruta | porta identificadores de caso del banco; la tabla cerrada de §4.6 la traduce a `fuente_de_politica` y **solo el resultado cruza** |
| `entidades[].grupo_homonimo` | es la **respuesta** de `G5`: que dos homónimos no se fusionan. Entregarla sería dar el resultado |
| `entidades[].nota`, `relaciones[].nota` | oráculo declarado por §5.3 |
| `items[].traza`, `documentos[].traza`, `mensajes[].traza` | ídem |

Además, el validador preventivo del requisito 8 de §4.5 se recomprueba sobre lo materializado: ningún valor de `razon_segura` ni de `regla_de_politica` contiene un identificador de caso.

---

## 4. Identidad canónica: una biyección declarada

`MEM-007` → `MEMORIA:7`. `DEC-006` → `DECISION:6`. `MSG-030` → `MENSAJE:30`.

El número sale **del propio identificador**, nunca de un contador de inserción. Dos construcciones producen las mismas identidades aunque el generador recorriese los ítems en otro orden, y una colisión aborta la construcción.

**Entidades y proyectos devuelven `null`.** `ENT-ROTOR` y `PRJ-ALFA` son extremos legítimos de una relación y **no** elementos del canon de Sirius 0.1. Inventarles una identidad haría indistinguible «no existe en el canon» de «existe», que es exactamente el defecto que el paquete de corrección 02 eliminó para los identificadores ausentes.

---

## 5. Pérdidas declaradas, no disimuladas

El esquema canónico de Sirius 0.1 no puede sostener todo lo que el corpus declara. La proyección **colapsa donde debe colapsar y declara el colapso**, y el eje verdadero viaja intacto en `ejes_p2`.

| Pérdida | Qué se pierde | Dónde sobrevive |
|---|---|---|
| **Estado** | `memories.status` tiene tres valores y `decisions.status` cuatro; el corpus declara confirmación × validez × disponibilidad por separado | `ejes_del_item`, verbatim. `G3`, `G6`, `G7` y `G9` deben leerlos de ahí |
| **Ámbito multiproyecto** | `project_id` es una sola clave foránea y no puede expresar una lista cerrada | `proyectos` y `miembros_de_lista_cerrada`. `G4` debe leerlos de ahí |
| **Sujeto ausente** | `decisions.subject` es `NOT NULL` | cadena vacía, que el puerto y las consultas por clave y por prefijo **ya tratan como ausencia**. Fabricar un sujeto sería `P-SUJETO-01`, la proyección expresamente descartada por §6.1 |
| **Proyecto activo** | el corpus no declara ninguno | **ninguno lo es**: marcar uno decidiría a qué ítems favorece el desempate por proyecto activo de Sirius 0.1 |
| **Relaciones** | el canon materializa **una**: `decisions.supersedes_decision_id` | las diez en `relaciones`, con `materializada_en_el_canon` en 1 sólo para `REL-001` y `REL-008` |

Ninguna de estas pérdidas se resuelve aquí. Se **declaran** para que el paso 5 del plan —la corrección de `common`— sepa exactamente qué puertas tienen que dejar de leer el estado colapsado.

### 5.1 Dos campos que la clasificación autoriza y aun así no cruzan

`polaridad` y `condicion` están clasificados `ENTRADA_DE_CANDIDATO` por §5.7. La proyección los **materializa** en `ejes_reservados_al_arnes` y **no** los cablea a `ItemCanonico`.

No es una restricción nueva: el contrato común congelado ya asigna su derivación al candidato —«derivarlas es trabajo del candidato, y como las derive es justamente parte de la alternativa que se pone a prueba»—. Inyectarlas sustituiría por el dato la señal que `RF-19` mide, y el banco no mediría nada. Quien las quiera tendrá que pedirlas al plano y declarar para qué.

---

## 6. Deduplicación exacta y agrupación semántica, separadas por construcción

§7.2 distingue dos mecanismos. La proyección los mantiene **estructuralmente distintos** y no fusiona nada:

**A · Identidad exacta.** Es la clave primaria de los tres planos. Una identidad repetida aborta la construcción. `clases_por_identidad_exacta` no consulta sujeto ni propiedad: si lo hiciera, dejaría de ser identidad y sería equivalencia con otro nombre.

**B · Equivalencia candidata.** `clases_candidatas_de_equivalencia` agrupa identidades **distintas** por `(subject_key_experimental, property_key)`, ambas no nulas. Son **dos de los siete ejes** de `B04-Q13`: los otros cinco los adjudica la capa común, y por eso la función devuelve *candidatas*, no grupos.

Sobre la familia v0.6 hay **exactamente una** clase candidata:

```
plataformadedespliegue | PK-d291da76418f  ->  DECISION:6, DECISION:7, DECISION:8
```

Es `B04-CA-19`, el defecto que la v0.6 corrigió. La proyección lo confirma por ejecución, y los tres siguen siendo tres identidades distintas y citables.

**La ausencia no fusiona.** Un sujeto o una propiedad nulos excluyen de toda clase candidata. Y **no hacen inelegible al elemento**: los 85 ítems sin `property_key` siguen siendo recuperables por el puerto, comprobado por ejecución.

---

## 7. Totalidad de los canales laterales

`property_key` y `criticidad_aplicada` tienen fila para **los 97 ítems**, `null` incluido. Una fila que faltase sería indistinguible de un ítem que la proyección olvidó, y por eso su ausencia aborta la construcción.

- `property_key`: 12 con valor, **85 nulos declarados**.
- `criticidad_aplicada`: 19 con los cuatro campos seguros, 78 nulos.

---

## 8. Determinismo, comprobado

Dos construcciones sobre las mismas entradas producen el mismo contenido lógico, y una prueba lo verifica construyendo dos veces y comparando. Ningún identificador depende del orden de recorrido, ningún valor depende del reloj y toda la escritura ordena por identidad canónica.

El manifiesto congelado se recomputa en cada ejecución de la suite y se compara campo a campo con el fichero: si el generador cambiase, la prueba falla antes de que nadie pueda ejecutar un candidato contra una proyección distinta de la declarada.

---

## 9. La proyección es ejecutable de verdad

No es una declaración: se comprueba.

- El motor común recorre `E0-E5` completo sobre la proyección con `ADR002-A` y adjudica parada.
- `CA-19` es alcanzable por los **tres** caminos del puerto: término léxico, clave exacta y prefijo de sujeto.
- El historial llega como **evidencia atribuida**, no canónica (`MENSAJE:30`).
- El mensaje redactado tiene `content` nulo y `redacted_at` fijado, y deja de casar en el índice.
- El discriminante relacional `MEMORIA:950 → MEMORIA:951` sigue siendo una arista `DERIVA_DE` **no materializada en el canon**, que es la razón de ser de `ADR002-C`.

**Ninguna de estas comprobaciones es una medición.** No hay rendimiento, no hay tiempos, no hay candidatos evaluados.

---

## 10. Custodia

| | |
|---|---|
| `src/sirius` | **intacto**, árbol `6d8558ef1fe4994cb15a12967525bf3496b3c0b8` |
| `migrations/` | **intacto** |
| Familias v0.4, v0.5 y v0.6 | **intactas**, verificadas por blob |
| Fichas `T0-control v1`, `ADR002-A v3`, `ADR002-B v5` | **intactas** |
| `common/` | **sin tocar**: la corrección es el paso 5, no éste |
| Benchmark | **BLOQUEADO, NO AUTORIZADO y NO EJECUTADO** |

---

## 11. Lo que esta congelación no hace

- **No** corrige `common`. Las pérdidas de §5 son el encargo del paso siguiente, no su solución.
- **No** emite fichas sucesoras de `A` ni de `B`.
- **No** implementa `C` ni `D`.
- **No** satisface ninguna puerta de arranque.
- **No** autoriza el benchmark ni ninguna medición.
