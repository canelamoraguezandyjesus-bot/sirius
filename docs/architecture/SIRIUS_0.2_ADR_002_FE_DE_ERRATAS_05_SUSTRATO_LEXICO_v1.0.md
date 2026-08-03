# SIRIUS 0.2 — ADR-002 · Fe de erratas 05: identidad del sustrato léxico FTS5

**Versión:** 1.0
**Estado:** **ERRATA RECONOCIDA · APPEND-ONLY**
**Fecha:** 3 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **HEAD de partida:** `1cb3a958dd86123bf2a21bcffe35d1f49a2bc655`
**PR:** #117, **abierto y sin fusionar**

**Autoridad:** paso **2** del plan aprobado por `SIRIUS_0.2_ADR_002_RESOLUCION_PREBENCHMARK_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v1.0_APROBADA.md` §4, con el alcance adjudicado en la resolución aprobada `..._v0.4_PROPUESTA.md` §9.4 y §9.5 (blob `191edb43df37a6cd9220212815ee52a1c4b0397e`).

**Ámbito exclusivo:** las descripciones documentales del sustrato léxico. **Este documento no modifica ningún fichero.**

---

## 0. Qué declara esta errata

Varias fichas de candidato y de control de ADR-002 **describen mal** el índice léxico sobre el que se midió y se va a medir. La descripción publicada no coincide con la identidad real del índice que crea la cadena de migraciones canónica.

**Las fichas no se reescriben.** Se conservan íntegras, con su contenido normativo y su huella, y esta fe de erratas registra la verdad observada **junto a** ellas, en régimen append-only.

**La discrepancia ya fue adjudicada como exclusivamente documental** para los corpus y las evidencias ya emitidos (resolución v0.4 §9.4, aprobada por el acta v1.0 §1 punto 14 y §2). Esta fe de erratas **ejecuta** ese remedio; no lo reabre ni lo revisa.

---

## 1. Identidad incorrecta publicada

Dos errores distintos, y conviene no mezclarlos:

| # | Error | Dónde aparece |
|---|---|---|
| **E-1** | **Nombre de la tabla.** Se declara `items_fts` | únicamente en la ficha de `T0-control v1` |
| **E-2** | **Parámetro del tokenizador.** Se declara `remove_diacritics 2` | en las **nueve** fichas de ADR-002 |

El tokenizador declarado, `unicode61`, **sí es correcto**: el error de `E-2` está en el valor del parámetro, no en la familia del tokenizador.

---

## 2. Identidad real observada

Verificada sobre este HEAD, en la cadena de migraciones canónica:

**`migrations/versions/61be4bb269bf_create_fts5_search_indexes.py`** — blob `5ae00f728778144e9ddf04def7cb08ed7b404c5f`

```
línea 116:  "CREATE VIRTUAL TABLE knowledge_fts USING fts5(kind UNINDEXED, item_id UNINDEXED, content)"
```

| Hecho | Comprobación |
|---|---|
| La tabla se llama **`knowledge_fts`** | `61be4bb269bf:116` |
| El `CREATE VIRTUAL TABLE` **no declara cláusula `tokenize=`** | la palabra `tokenize` aparece **una sola vez** en todo el fichero, en la línea **33**, dentro de un *docstring*; no aparece en ninguna sentencia DDL |
| Sin cláusula `tokenize=`, FTS5 aplica su tokenizador **predeterminado**: `unicode61` | documentación de SQLite, corroborada por sonda en la resolución v0.4 §9.3 |
| El valor **predeterminado** de `remove_diacritics` en `unicode61` es **`1`** | sonda de la resolución v0.4 §9.3: los términos indexados por la tabla real son **idénticos** a los de una tabla con `remove_diacritics 1` y **distintos** de una con `2` |

> **Identidad real, en una línea:**
> **`knowledge_fts` · `unicode61` · `remove_diacritics` efectivo = `1`, por configuración predeterminada.**

**Nota de alcance, para que no se sobreinterprete:** `message_fts` —creada en la misma migración, línea 84— tampoco declara `tokenize=` y por tanto también rige el predeterminado. Ninguna ficha describe `message_fts`, de modo que **no hay errata que corregir sobre ella**; se registra el hecho para que la identidad observada quede completa.

---

## 3. Artefactos afectados

### 3.1 Fichas que publican la descripción incorrecta

**Nueve fichas, diecisiete declaraciones.** Todas en `artifacts/adr002_cards/`.

| Ficha | Blob | Estado | Líneas | Qué declara |
|---|---|---|---|---|
| `ficha_T0-control_v1.json` | `c25a293c34644e2195d812ef8777246400e52c96` | **CONGELADA · vigente** | `27` | «FTS5 medido de Sirius 0.1 (**tabla items_fts** con unicode61 y **remove_diacritics 2**), sin alternativa ni indice adicional» |
| `ficha_ADR002-A_v1.json` | `4dcb53873de5ca58cf3e929e861511219430b6be` | SUSTITUIDA | `29`, `69` | `remove_diacritics 2` |
| `ficha_ADR002-A_v2.json` | `d8cdd35784437da1860dc4130c7d605ade695ab6` | SUSTITUIDA | `29`, `69` | `remove_diacritics 2` |
| `ficha_ADR002-A_v3.json` | `b3ce920e6dc0ee62a0358f8bfb9762dcac0d64d7` | **CONGELADA · vigente** | `29`, `69` | `remove_diacritics 2` |
| `ficha_ADR002-B_v1.json` | `8a3f1c434222fc86309466884c8b10a7bae2b600` | SUSTITUIDA | `29`, `69` | `remove_diacritics 2` |
| `ficha_ADR002-B_v2.json` | `4ab1b3e768da357ed94a792f82473ba4a5b67e99` | SUSTITUIDA | `29`, `69` | `remove_diacritics 2` |
| `ficha_ADR002-B_v3.json` | `2ec4e417f862b20c341d77bf61ce6de322c5a46a` | SUSTITUIDA | `29`, `69` | `remove_diacritics 2` |
| `ficha_ADR002-B_v4.json` | `5c028871f782024b02f555357697bb4b2162143d` | SUSTITUIDA | `29`, `69` | `remove_diacritics 2` |
| `ficha_ADR002-B_v5.json` | `b9ddf6de393e21bebdd3d0eab1e182aa069053e3` | **CONGELADA · vigente** | `29`, `69` | `remove_diacritics 2` |

Las dos declaraciones por ficha de `A` y de `B` son:

```
línea 29:  "sustrato_lexico": "FTS5 medido de Sirius 0.1 (unicode61, remove_diacritics 2), sin alternativa"
línea 69:  "nombre": "SQLite FTS5 (unicode61, remove_diacritics 2)"
```

**Identidad de las tres fichas vigentes**, para que la errata quede anclada a lo que hoy rige:

| Ficha | Versión | Huella declarada | Commit de congelación |
|---|---|---|---|
| `T0-control` | 1 | `d47a767e61b30729e15f48c9924413f6fddc9429` | `c881fce697009d294121c5b99d23ba6af5b8b173` |
| `ADR002-A` | 3 | `427905a06f6c12666a09c73b8720e229f17eeef3` | `13ffae552b76089fee7119264a2502d166ef97dd` |
| `ADR002-B` | 5 | `b27866b1278f37473fa6151ab7f26df7386bcd81` | `317ad5fc406012c5a8684b57f8e53d61ff9fd7c0` |

### 3.2 Código que asume explícitamente un valor

**Un solo fichero, dos líneas.** `experiments/adr002/rederivation/frozen_corpus.py` — blob `081366080b5c941194d1df2ff8b51d44ec54a2a6`:

```
línea 63:  #: ``remove_diacritics 2`` —se descomponen y descartan las marcas diacriticas—
línea 72:  """Pliegue de diacriticos equivalente a ``remove_diacritics 2`` en latin."""
```

**Precisión que esta errata debe hacer, porque cambia la gravedad:** esas dos líneas —un comentario y un *docstring*— **no describen el índice**: describen **el pliegue propio del módulo**, y afirman que es *equivalente* a `remove_diacritics 2`. Y el propio módulo **verifica esa coincidencia contra el índice real antes de medir** (resolución v0.4 §9.3 paso 5, anclado en `frozen_corpus.py:27`, `:66`, `:145`, `:388`), de modo que una divergencia habría **abortado la medición** en vez de contaminarla.

Es, por tanto, una **descripción imprecisa de una equivalencia**, no una declaración falsa de la identidad del índice. **El código no se modifica aquí** —esta fe de erratas es exclusivamente documental— y se deja registrado para que la futura corrección de esa capa lo recoja.

### 3.3 Lo que NO está afectado, verificado

| Ámbito | Resultado |
|---|---|
| Canon `.docx` (`docs/canonical/`, 8 documentos) | **ninguno** contiene `items_fts` ni `remove_diacritics`. El único que menciona el índice —`SIRIUS_ARQUITECTURA_TECNICA_0.1_v1.0_PROPUESTA.docx`— dice **`knowledge_fts`**, que es lo correcto |
| Informes de tolerancias, de rederivación y de spikes | **ninguna** declaración del sustrato: la búsqueda de «FTS5 medido», «tabla items_fts» y `remove_diacritics` sobre `artifacts/adr002_tolerances/` y `artifacts/adr001_spikes/` **no devuelve nada** |
| Corpus, casos, referencias y manifiestos de las familias v0.4, v0.5 y v0.6 | **ninguna** declaración incorrecta. La familia v0.5 y la v0.6 declaran expresamente `unicode61 remove_diacritics=1`, que **ya es la identidad correcta** |
| Paráfrasis sin nivel («pliegue de diacríticos», «minúscula sin diacríticos») en `lexical.py`, en las fichas de `A` y en las pruebas | **no son erratas**: describen el pliegue sin atribuirle un nivel |

### 3.4 Documentos que ya registran la discrepancia

No son objeto de corrección: **la citan para denunciarla**, y son la cadena documental que conduce hasta aquí.

| Documento | Dónde |
|---|---|
| `..._RESOLUCION_PREBENCHMARK_..._v0.2_PROPUESTA.md` | líneas 317, 427, 441 — primer registro de `items_fts` / `knowledge_fts` |
| `..._RESOLUCION_PREBENCHMARK_..._v0.3_PROPUESTA.md` | líneas 37, 550, 554, 555, 612 — amplía la discrepancia a **dos**: nombre de tabla **y** parámetro |
| `..._RESOLUCION_PREBENCHMARK_..._v0.4_PROPUESTA.md` | §9.1 a §9.5 — inventario, hechos, auditoría, adjudicación y remedio |
| `..._RESOLUCION_PREBENCHMARK_..._v1.0_APROBADA.md` | §2 — acepta la identidad real como hecho observado |
| `..._PAQUETE_RESOLUCION_05_..._v0.3.md` | líneas 40, 97 — exige tratarla como fe de erratas separada |
| `..._PAQUETE_RESOLUCION_05_..._v0.4.md` | líneas 69, 109, 111 — plan de la auditoría dirigida |
| `..._PAQUETE_TRABAJO_13_..._v0.1.md` | línea 309 — usa ya la identidad correcta |
| `..._CONGELACION_FAMILIA_SUCESORA_v0.5.md` | líneas 199, 201 — mide con la identidad correcta |

---

## 4. Inexistencia de impacto sobre resultados congelados

**Adjudicado en la resolución v0.4 §9.4 y aprobado por el acta v1.0 §1 punto 14.** Se reproduce aquí el fundamento, sin reabrirlo:

1. La **única** diferencia efectiva entre `remove_diacritics 1` y `2` está en los codepoints con **más de una marca diacrítica**. Con `1` se indexan sin plegar —`ǻ`, `ḗ`, `ṓ`, `ẳ`, `ế`, `ự`—; con `2` se pliegan. **Los acentos españoles de una sola marca —`á é í ó ú ñ ü`— se pliegan idénticamente en ambas configuraciones.**
2. El escaneo de todo el material congelado —corpus de conformidad, corpus de rendimiento, casos, referencias, *fixtures*, cargadores y la evidencia ya emitida de `T0`— halló una unión de **19 codepoints no ASCII**, y **ninguno** se comporta distinto entre `1` y `2`. Los **106** textos del corpus de conformidad se comprobaron uno a uno: **0 divergentes**.
3. El acta de congelación de la familia v0.5 midió además la condición léxica de su discriminante con `remove_diacritics` **0, 1 y 2** y por omisión: **vacía en las cuatro**.

> **Conclusión, ya adjudicada: no existe en el material congelado un solo codepoint cuyo tratamiento difiera entre la configuración declarada y la real.**
>
> **No hay impacto sobre resultados, comparabilidad, huellas, pruebas ni evidencia ya emitida.** La errata es **exclusivamente documental**.

---

## 5. Consecuencias declaradas

### 5.1 `T0-control v1`

- **No** necesita ficha nueva por esta errata.
- **No** necesita repetir la rederivación de `ADR002-TOL-208` por esta errata.
- Su ficha **no se reescribe**: conserva su contenido, su huella `d47a767e...` y su estado `CONGELADA`.
- **La identidad observada real que rige es la de §2**, y esta fe de erratas es el registro que prevalece sobre la descripción de la ficha **sin tocarla**.
- Cualquier cambio futuro de implementación o de protocolo de `T0` sigue sometido a las reglas normales de ficha sucesora. **Esta errata no es uno de esos cambios.**

### 5.2 `ADR002-A v3` y `ADR002-B v5`

- Sus fichas y sus actas históricas **no se reescriben**.
- **No se emiten ahora fichas intermedias** por esta errata. Emitir una versión de ficha solo para corregir una descripción documental multiplicaría identidades congeladas sin cambiar comportamiento alguno.
- Sus aprobaciones como **PREPARADO PARA BENCHMARK** permanecen **intactas** como decisiones históricas de sus identidades exactas.
- Esta fe de erratas **las cubre expresamente**: las diez declaraciones de §3.1 correspondientes a `A v1/v2/v3` y `B v1/…/v5` quedan corregidas por §2 a todos los efectos documentales.

### 5.3 Fichas sucesoras futuras

Las fichas sucesoras de `ADR002-A` y `ADR002-B` —**ya obligatorias** por la futura corrección de `common` (paso 6 del plan aprobado), no por esta errata— **deberán declarar la identidad correcta**:

```
knowledge_fts · unicode61 · remove_diacritics 1
```

y **deberán probarse y recibir reaprobación explícita**.

Lo mismo regirá para cualquier ficha futura de `ADR002-C`, `ADR002-D` o de una versión sucesora de `T0`.

### 5.4 El benchmark sigue bloqueado

> **Ningún benchmark podrá autorizarse mientras no existan las fichas sucesoras de §5.3 con la identidad correcta y sus reaprobaciones explícitas.**

Esta condición viene de la resolución v0.4 §9.5, aprobada por el acta v1.0 §2, y **esta fe de erratas no la levanta**. Emitirla **cierra el paso 2** del plan; **no** desbloquea el benchmark.

El benchmark permanece **BLOQUEADO, NO AUTORIZADO y NO EJECUTADO**. La ronda primaria sigue siendo `T0 + ADR002-A + ADR002-B + ADR002-C + ADR002-D`, **sin reducción**.

---

## 6. Régimen de este documento

1. **Append-only.** No modifica ningún fichero: ni fichas, ni actas, ni corpus, ni manifiestos, ni código, ni pruebas.
2. **No altera ningún estado.** Ninguna ficha cambia de versión ni de estado; ninguna aprobación se revoca ni se traslada.
3. **Prevalece sobre las descripciones enumeradas en §3.1** en cuanto a la identidad del sustrato léxico, **sin reescribirlas**. Es el mismo mecanismo que el acta de congelación del corpus v0.4 aplica a las etiquetas internas `PROPUESTO`: prevalecer sin reescribir, porque reescribir destruiría la identidad congelada.
4. **No reabre** la adjudicación de §4, que ya está aprobada.
5. Reverificación de la identidad real en cualquier momento:

```
git rev-parse HEAD:migrations/versions/61be4bb269bf_create_fts5_search_indexes.py
grep -n "tokenize\|CREATE VIRTUAL TABLE knowledge_fts" \
     migrations/versions/61be4bb269bf_create_fts5_search_indexes.py
```

---

## 7. Estado tras esta fe de erratas

| | |
|---|---|
| Fichas afectadas | **9**, ninguna modificada |
| Declaraciones corregidas documentalmente | **17** |
| Ficheros modificados por este documento | **0** |
| `T0-control v1` | intacto; **sin ficha nueva y sin nueva rederivación** por esta errata |
| `ADR002-A v3` | **PREPARADO PARA BENCHMARK**, intacto; **sin ficha intermedia** |
| `ADR002-B v5` | **PREPARADO PARA BENCHMARK**, intacto; **sin ficha intermedia** |
| `ADR002-C`, `ADR002-D` | no implementados |
| Familias v0.4, v0.5 y v0.6 | intactas |
| `ADR002-TOL-208` | íntegra |
| Benchmark | **BLOQUEADO, NO AUTORIZADO y NO EJECUTADO** |
| PR #117 | **abierto y sin fusionar** |

**El paso 2 del plan aprobado queda cerrado.** El paso 3 —la adjudicación separada del arnés de conformidad de `T0`— **no** se ejecuta ni se autoriza aquí.
