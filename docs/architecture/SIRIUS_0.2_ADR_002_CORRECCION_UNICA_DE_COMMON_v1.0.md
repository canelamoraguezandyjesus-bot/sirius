# SIRIUS 0.2 — ADR-002 · Corrección única de `common`

**Versión:** 1.1
**Estado:** **APLICADA** · ampliada en la v1.1 con las cinco puertas, por orden expresa del usuario en la solicitud de reaprobación
**Fecha:** 3 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** paso **5** del plan aprobado por `..._RESOLUCION_PREBENCHMARK_..._v1.0_APROBADA.md` §4 — «corregir `common` una sola vez» —, con el contenido que la resolución v0.4 fija en §4.5, §4.10, §5.1, §5.5, §5.7, §7.2, §7.3, §7.4, §7.5, §7.6, §7.7 y §7.9.

**Es una sola corrección.** No hay parches sucesivos por síntoma: los dieciocho puntos son un mismo cambio de diseño y se aplican juntos porque dependen unos de otros. Separarlos habría dejado estados intermedios en los que, por ejemplo, la agrupación conserva miembros pero `G12` sigue viendo sólo representantes.

---

## 1. Lo que cambia, punto por punto

| # | Requisito aprobado | Qué hacía antes | Qué hace ahora |
|---|---|---|---|
| 1 | Ausencia real de sujeto como `null` | `str(fila[1] or "")`: ausencia y cadena vacía colapsaban | `subject_key: str \| None`; el puerto devuelve `None` |
| 2 | Prohibición de fabricar sujeto | el historial recibía `mensaje-<n>`, un sujeto sintético que el canon nunca declaró | `subject_key=None` para toda evidencia atribuida |
| 3 | Agrupar sólo con todos los ejes determinados | clave de tres ejes: sujeto, proyecto y polaridad | **diez ejes**, y cualquiera indeterminado excluye |
| 4 | Identidad exacta ≠ equivalencia semántica | una sola función que borraba miembros | `grouping.py`: dos mecanismos separados que no se llaman entre sí |
| 5 | `property_key` exclusiva de `common` | no existía en el motor | protocolo `PlanoComun`, parámetro propio de `recuperar`, **nunca** dentro de `ContextoDeEtapa` |
| 6 | Cardinalidad semántica y documental | un solo contador | `Cardinalidades`; la cuota cuenta necesidades, el límite cuenta entregables |
| 7 | Grupo **no** atómico frente al límite | los miembros absorbidos ya no existían | se entregan hasta agotar el límite |
| 8 | Miembros omitidos declarados | desaparecían en silencio | `omitidos_por_limite` y `traza.miembros_omitidos` |
| 9 | Estado `PARCIAL` cuando corresponde | `COMPLETA` aunque el límite partiera un grupo | `PARCIAL` ante desbordamiento crítico o grupo truncado |
| 10 | `G12` sobre **todos** los miembros | se aplicaba después de agrupar y sólo veía representantes | recibe la lista completa y `criticos_omitidos` puede nombrar lo absorbido |
| 11 | Criticidad aplicada segura | dos niveles y siempre `ORDINARIA` desde el puerto | `CriticidadAplicada` de cuatro campos, del plano común |
| 12 | Precedencia de criticidad | `hay_criticos_pendientes` era código muerto | se pasa `pendientes` y la criticidad viene del plano |
| 13 | Handoff íntegro a `B05` | inexistente | `Recuperacion.handoff_a_b05`, verbatim |
| 14 | Explicación y trazabilidad | procedencia en singular; «del canon» también para lo atribuido; razón de orden distinta de la clave real | procedencias plurales, origen correcto, ejes de desempate citados |
| 15 | Reinterpretación aprobada de `ACOTADA` | la cuota contaba documentos | la cuota cuenta **necesidades semánticas** (§7.6) |
| 16 | Clasificación estructural fallo-cerrado | `capacidad_de` ya fallaba cerrado; `common` no la usaba | `ItemCanonico` pierde `criticidad`; el plano reservado no llega al candidato |
| 17 | Prohibición de acceso a oráculo | — | el motor no recibe ninguna estructura de oráculo y el plano se abre en `ro` |
| 18 | Compatibilidad con la familia v0.6 | `IMPORTANTE` era indistinguible de `ORDINARIA` | tres niveles; la traducción `CRITICO → CRITICA` vive en la proyección |

---

## 2. Los dos mecanismos, y por qué viven separados

`grouping.py` es un módulo nuevo, y no por orden cosmético. Mientras deduplicación y agrupación compartieron función:

- la deduplicación **por sujeto** borraba miembros —`_agrupar` devolvía sólo `vistos.values()`—, de modo que un elegible desaparecía del resultado sin declararse;
- `G12` se aplicaba **después**, sobre esa lista ya recortada, y por tanto no podía nombrar a un crítico absorbido;
- la suficiencia se adjudicaba **antes** de agrupar, contando lo que luego se reducía.

Ahora:

**A · Identidad exacta.** Misma identidad canónica aportada por varias etapas. Fusiona señales, conserva la etapa **más autorizada** —`E1` antes que `E3`, porque reemplazarla degradaría el orden— y **no elige representante**: no hay identidades distintas entre las que elegir.

**B · Equivalencia.** Identidades distintas, agrupadas sólo si coinciden los diez ejes: sujeto, propiedad, clase, clase de evidencia, ámbito, polaridad, condición, tiempo, vigencia y disponibilidad. Cualquiera indeterminado excluye. **La duda no fusiona.**

**Invariante comprobado en ejecución** (§7.9): elegibles antes de agrupar = unión de los miembros de todos los grupos más los sueltos. Si dejara de cumplirse, el motor aborta con `RecuperacionInvalidaError` en vez de entregar una salida a la que le falta algo.

**Representante por cascada registrada** (§7.4): confirmación → autoridad → vigencia → procedencia → identidad estable. «Primero en llegar» queda prohibido: dependía del orden de la base de datos y no era reproducible.

---

## 3. La frontera que hace estructural la prohibición

`recuperar` gana un cuarto parámetro, `plano`, y ése es todo el mecanismo:

- el candidato recibe `ContextoDeEtapa`, que **no tiene** campo para el plano;
- el motor nunca se lo pasa a `candidatas()` ni a `leer()`;
- `ItemCanonico` **pierde** `criticidad`, que estaba al alcance de cualquiera que recibiese un ítem;
- el plano se abre en modo `ro`, de modo que ni siquiera `common` puede escribirlo.

El valor por defecto, `PLANO_COMUN_VACIO`, **no determina nada**: sin canal lateral no se agrupa —la duda no fusiona— y nada es crítico —ninguna etapa puede crear un nivel—. No es un plano permisivo; es la ausencia de canal declarada como ausencia.

La única traducción de vocabulario entre el corpus y el contrato común —`CRITICO` → `CRITICA`— vive en `projection/plane.py`, que conoce las dos partes. Ponerla en `common` habría obligado a la capa común a conocer el vocabulario del banco, y dejaría de ser neutral. Un nivel del corpus que no figure en la tabla **aborta**: elegir el «más parecido» reinterpretaría el nivel, y el traspaso a `B05` debe ser íntegro.

---

## 4. Ampliación aprobada: las cinco puertas que leían el estado colapsado

La v1.0 de este acta declaró como pendiente que `G3`, `G4`, `G6`, `G7` y `G9` seguían leyendo el estado colapsado en vez de los ejes verdaderos. **El usuario amplió el alcance del paso 5 en la solicitud de reaprobación y ordenó corregirlas antes de reaprobar A y B.** Queda hecho.

`ItemCanonico` gana `ejes: EjesDeclarados`, con confirmación, validez, disponibilidad, sensibilidad, autoridad, ámbito, las dos marcas de no uso, la procedencia y los miembros de una lista cerrada. El puerto los resuelve del plano `ejes_p2` **con consultas dirigidas y anotadas** —`WHERE identidad IN (...)`—, de modo que la garantía de ausencia de barrido no se debilita: el trabajo depende de cuántas identidades se materializaron, nunca del tamaño del plano.

| Puerta | Qué leía | Qué lee | Qué era imposible antes |
|---|---|---|---|
| `G3` | `not disponible` | `no_usar_como_memoria`, con la excepción literal de `M3`/`M4` | era un duplicado exacto de `G2`: ningún ítem marcado que siguiera disponible caía |
| `G4` | una sola clave foránea | las **tres** clases de ámbito, con los miembros de la lista cerrada | un ítem multiproyecto caía aunque la petición autorizase a todos sus miembros |
| `G6` | `vigente` | `confirmacion` de tres valores, visible según modo | candidata y rechazada caían o pasaban juntas |
| `G7` | `vigente` | `validez`: sustituida y sin soporte son **dos causas** | indistinguibles entre sí y de cualquier otra no vigencia |
| `G9` | `disponible` | `sensibilidad`, protección superior mantenida | la restricción no existía como eje |

**`None` no es permisivo.** Un eje que el sustrato no declara hace que la puerta **degrade al estado colapsado y lo diga en el motivo del descarte**: «eje no declarado: degradado a disponibilidad». Los fixtures técnicos, que no traen plano de ejes, siguen comportándose como antes y ahora lo declaran.

---

## 5. Reanclaje de la regla de parada

`test_adr002_b_static.py::test_la_base_de_a_no_cambio_ni_un_byte` fija los blobs de la capa común y de `adr002_a`. La regla no se levanta: **se reancla**. Los blobs nuevos quedan escritos ahí y el próximo cambio no autorizado seguirá fallando.

`adr002_a` queda alcanzado en exactamente dos puntos, los dos por la nulabilidad del sujeto: `lexical.sujeto_estructural` acepta `str | None` y `candidate` pliega `subject_key or ""`. Ninguna señal de `A` cambia.

---

## 6. Consecuencia de gobierno

La corrección modifica el árbol de `experiments/adr002/candidates`, y con él el subárbol `common` que declaran las fichas vigentes.

- `ADR002-A v3` y `ADR002-B v5` **exigen ficha sucesora**: su cláusula de congelación dice que «cualquier modificación posterior obligará a nueva versión de ficha y a repetir las ejecuciones ya realizadas», y la ficha de `B` añade que «si la base cambiara, cambiaría la huella de esta ficha y obligaría a versión sucesora».
- Es el **paso 6** del plan aprobado, y es el siguiente.
- `T0-control v1` **no** se ve afectada: su identidad está atada al árbol de `src/sirius`, que sigue en `6d8558ef1fe4994cb15a12967525bf3496b3c0b8`.

---

## 7. Custodia

| | |
|---|---|
| `src/sirius` | **intacto** |
| `migrations/` | **intacto** |
| Familias v0.4, v0.5 y v0.6 | **intactas** |
| Proyección experimental v0.1 | **intacta**, huella `755cbdfe…` |
| Fichas históricas | **intactas**; ninguna se reescribe |
| Benchmark | **BLOQUEADO, NO AUTORIZADO y NO EJECUTADO** |
