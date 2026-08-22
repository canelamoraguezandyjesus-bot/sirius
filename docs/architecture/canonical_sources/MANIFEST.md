# SIRIUS 0.2 — ADR-002 · Manifiesto de fuentes canónicas

**Versión:** 1.0
**Estado:** **MATERIALIZADO Y VERIFICADO**
**Fecha de materialización:** 26 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_MATERIALIZACION_FUENTES_CANONICAS_v0.1.md`
**Autoridad:** Usuario / Proyecto Sirius
**Origen de los tres archivos:** archivos adjuntos aportados por el usuario en Claude Code
**Puerta que satisface:** `SRC-ADR002-01` del `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md`
**No autoriza:** ejecutar el benchmark, ejecutar T0 o T1–T4, implementar prototipos, elegir realización técnica ni merge.

---

## 0. Objeto

Esta carpeta contiene las **tres fuentes canónicas completas** de las que dependía el arranque del benchmark de ADR-002. Se materializan **sin alterar un solo byte**: no se han reconstruido, convertido, renombrado internamente ni editado sus propiedades.

Los ficheros son la **autoridad canónica**. Los documentos de análisis del repositorio —inventario normativo, especificación de benchmark, línea base, Registro de Tolerancias— son derivados y **ceden ante estos originales** ante cualquier discrepancia.

---

## 1. Inventario

### 1.1 `SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO.docx`

| Campo | Valor |
|---|---|
| **Nombre exacto** | `SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO.docx` |
| **Identificador interno** | `SIRIUS-0.2-B04` |
| **Versión** | **1.0** |
| **Estado** | **APROBADO · CANÓNICO PARA SIRIUS 0.2** |
| **Fecha del documento** | 23 de julio de 2026 |
| **Tamaño** | **93.326 bytes** |
| **SHA-256** | `b28a2cbed62b90f35e28db2412e46939b9bd2cdb8f145a5e9bbb2a8e7a5cbb45` |
| **Origen** | archivos adjuntos aportados por el usuario en Claude Code |
| **Fecha de materialización** | 26 de julio de 2026 |
| **Autoridad de aprobación** | Usuario / Proyecto Sirius · autoridad procedimental: Método Maestro Sirius 0.2 v1.0 |
| **Validación DOCX** | ZIP OOXML válido · 19 entradas · CRC correcto en todas · `[Content_Types].xml`, `word/document.xml` y `_rels/.rels` presentes · **1.714 párrafos legibles** |
| **Validación de seguridad** | **Sin `vbaProject.bin`, sin macros, sin ActiveX, sin objetos OLE ni ejecutables incrustados. 0 relaciones externas.** No es enlace, acceso directo ni archivo vacío |
| **Huella previa de contraste** | **No existía.** El paquete 02D no disponía de referencia anterior para B04. La huella aquí registrada es la **obtenida en esta materialización**, y así queda declarada: **no se ha inventado ninguna referencia previa** |
| **Relación con `SRC-ADR002-01`** | Satisface el requisito 1 de la puerta |

**Cobertura canónica verificada** — todos los identificadores que la puerta exige, contados sobre el texto del documento:

| Serie | Exigido | Encontrado | Resultado |
|---|---|---|---|
| `RF-01` … `RF-32` | 32 | 32 | **COMPLETO** |
| `CA-01` … `CA-50` | 50 | 50 | **COMPLETO** |
| `M01` … `M21` | 21 | 21 | **COMPLETO** |
| `D01` … `D16` | 16 | 16 | **COMPLETO** |
| `G1` … `G12` | 12 | 12 | **COMPLETO** |
| `S1` … `S7` | 7 | 7 | **COMPLETO** |
| `E0` … `E5` | 6 | 6 | **COMPLETO** |
| Alternativa B | — | presente | **COMPLETO** |

### 1.2 `SIRIUS_0.2_PLAN_DE_PRUEBAS_Y_REGISTRO_EXTERNO_DE_DELEGACIONES_v1.0_APROBADO.docx`

| Campo | Valor |
|---|---|
| **Nombre exacto** | `SIRIUS_0.2_PLAN_DE_PRUEBAS_Y_REGISTRO_EXTERNO_DE_DELEGACIONES_v1.0_APROBADO.docx` |
| **Identificador interno** | `SIRIUS-0.2-PDP-RED` |
| **Versión** | **1.0** |
| **Estado** | **APROBADO · CANÓNICO** |
| **Fecha del documento** | 24 de julio de 2026 |
| **Tamaño** | **93.708 bytes** |
| **SHA-256** | `39058c0f5fe50bb4b703411bd5296e1bb8b1ede513ccf2d9eacabb35da3f59fd` |
| **Contraste con la referencia previa** | **COINCIDE EXACTAMENTE** en tamaño y SHA-256 con la referencia registrada en el paquete de materialización §3 |
| **Origen** | archivos adjuntos aportados por el usuario en Claude Code |
| **Fecha de materialización** | 26 de julio de 2026 |
| **Autoridad de aprobación** | Usuario / Proyecto Sirius |
| **Validación DOCX** | ZIP OOXML válido · 19 entradas · CRC correcto en todas · partes obligatorias presentes · **2.472 párrafos legibles** |
| **Validación de seguridad** | **Sin `vbaProject.bin`, sin macros, sin ActiveX, sin objetos OLE ni ejecutables incrustados. 0 relaciones externas.** No es enlace, acceso directo ni archivo vacío |
| **Relación con `SRC-ADR002-01`** | Satisface el requisito 2 de la puerta |

**Estructura verificada.** Dos artefactos normativamente separados que comparten fichero físico: **Parte I `RED-1.0`** y **Parte II `PDP-1.0`**, ambos presentes. **79 delegaciones RED distintas** (`RED-001` … `RED-079`), incluidas las ocho que ADR-002 traza —`RED-027` a `RED-034`— y `RED-040`. **25 familias PDP** (`F01` … `F25`); el inventario del repositorio solo conocía trece.

### 1.3 `SIRIUS_0.2_ARQ_00_MARCO_RECTOR_ARQUITECTURA_Y_MAPA_DECISIONES_v1.0_APROBADO.docx`

| Campo | Valor |
|---|---|
| **Nombre exacto** | `SIRIUS_0.2_ARQ_00_MARCO_RECTOR_ARQUITECTURA_Y_MAPA_DECISIONES_v1.0_APROBADO.docx` |
| **Identificador interno** | `SIRIUS-0.2-ARQ-00` |
| **Versión** | **1.0** |
| **Estado** | **APROBADO** |
| **Fecha del documento** | 25 de julio de 2026 |
| **Tamaño** | **85.951 bytes** |
| **SHA-256** | `730a5fd13dce18bfcdb8dd4afee23dfe22c067c7cb3b953a9bd115cf73224f49` |
| **Contraste con la referencia previa** | **COINCIDE EXACTAMENTE** en tamaño y SHA-256 con la referencia registrada en el paquete de materialización §3 |
| **Origen** | archivos adjuntos aportados por el usuario en Claude Code |
| **Fecha de materialización** | 26 de julio de 2026 |
| **Autoridad de aprobación** | Usuario / Proyecto Sirius · propietario declarado en el documento: Usuario / Proyecto Sirius |
| **Validación DOCX** | ZIP OOXML válido · 29 entradas · CRC correcto en todas · partes obligatorias presentes · **1.487 párrafos legibles** |
| **Validación de seguridad** | **Sin `vbaProject.bin`, sin macros, sin ActiveX, sin objetos OLE ni ejecutables incrustados. 0 relaciones externas.** No es enlace, acceso directo ni archivo vacío |
| **Relación con `SRC-ADR002-01`** | Satisface el requisito 3 de la puerta |

**Alcance declarado en el propio documento:** *«ARQ-00 fija el marco y el mapa de decisiones; no es la arquitectura final, no decide los ADR y no autoriza implementación.»* Referencia el mapa completo de decisiones: `ADR-001`, `ADR-001A`, `ADR-002`, `ADR-003`, `ADR-003A`, `ADR-003B`, `ADR-003C` y `ADR-004`.

---

## 2. Verificación de identidad origen → destino

Huellas **recalculadas desde las copias ya presentes en el repositorio**, no reutilizadas del cálculo de origen.

| Archivo | Bytes origen | Bytes destino | SHA-256 origen = destino | `cmp` byte a byte |
|---|---|---|---|---|
| B04 | 93.326 | **93.326** | **sí** | **idéntico** |
| Plan de Pruebas + RED/PDP | 93.708 | **93.708** | **sí** | **idéntico** |
| ARQ-00 | 85.951 | **85.951** | **sí** | **idéntico** |

**Ningún byte, propiedad, nombre interno ni contenido ha sido alterado.** No se ha convertido ningún formato ni reconstruido ningún documento. No se ha utilizado ninguna versión `PROPUESTO`.

---

## 3. Observación registrada, sin alterar el archivo

En `SIRIUS_0.2_PLAN_DE_PRUEBAS_Y_REGISTRO_EXTERNO_DE_DELEGACIONES_v1.0_APROBADO.docx`, la propiedad interna `docProps/core.xml → dc:title` conserva un texto de una fase anterior de redacción:

> `SIRIUS 0.2 — Plan de Pruebas y Registro Externo de Delegaciones v0.2`

**No es una discrepancia de versión ni de estado.** El cuerpo del documento es inequívoco: portada «Versión 1.0 · APROBADO · CANÓNICO», bloque «ESTADO DE ESTA VERSIÓN: APROBADO Y CANÓNICO», y tabla de control documental con `Identificador SIRIUS-0.2-PDP-RED`, `Versión 1.0`, `Estado APROBADO · CANÓNICO`, `Fecha 24 de julio de 2026`. Además, **el fichero coincide exactamente en tamaño y SHA-256 con la referencia de contraste** registrada en el paquete: es el archivo designado como canónico, no otro.

Se deja constancia y **no se corrige**: el paquete prohíbe alterar bytes o propiedades. La autoridad es el contenido aprobado del documento, no un campo de metadatos obsoleto.

---

## 4. Estado de `SRC-ADR002-01`

> ### **SATISFECHA — 3 de 3 fuentes materializadas, verificadas y completas**

| Requisito de la puerta | Estado |
|---|---|
| B04 v1.0 APROBADO íntegro, con CA-01–50, M01–21, D01–16, detalle de E0–E5, G1–G12 y S1–S7 | **SATISFECHO** |
| Plan de Pruebas + RED/PDP v1.0 APROBADO | **SATISFECHO** |
| ARQ-00 v1.0 APROBADO | **SATISFECHO** |

### 4.1 Qué desbloquea

- La **materialización del nivel 1** del benchmark: los casos canónicos `B04-CA-01–50` y los del PDP dejan de ser inaccesibles.
- La **medibilidad de B04-M01–M21** y, con ella, la de `ADR002-TOL-204` (cero críticos elegibles pendientes), cuyo umbral ya estaba cerrado pero no era comprobable.
- La comprobación de las **tolerancias de texto, estado, conteo y tiempo de RF-26**, registrada como dependencia en `ADR002-TOL-201`.
- La **regla de muestreo de B04-M14**, registrada como dependencia en el §3 del Registro v0.4.
- El **mapeo exacto de RED-032**, que el paquete 01B difirió expresamente al Plan canónico.
- La traza a **CA concretos** en las columnas «pendiente» de la Especificación de benchmark §6, que ahora pueden completarse **desde la fuente** y nunca por analogía.

### 4.2 Qué NO desbloquea

El benchmark **sigue bloqueado**. `SRC-ADR002-01` era una de **cinco** puertas de arranque. Continúan sin satisfacer:

| Puerta | Estado |
|---|---|
| `ADR002-TOL-207` · presupuesto absoluto de almacenamiento del laboratorio | **NO SATISFECHA** |
| `ADR002-TOL-208` · corpus congelado, T0 rederivada sobre él y comparación rederivada | **NO SATISFECHA** |
| `ADR002-TOL-209` · protocolo común de medición congelado | **NO SATISFECHA** |
| `ADR002-TOL-210` · ficha de candidato confirmada antes de la primera ejecución | **NO SATISFECHA** |

Esta materialización **no autoriza** ejecutar T0 ni T1–T4, implementar prototipos, elegir realización técnica, modificar Sirius 0.1 ni fusionar el PR #117.

---

## 5. Reglas de custodia

1. **Estos tres ficheros no se modifican.** Cualquier cambio de byte invalida las huellas de este manifiesto y, con ellas, la puerta.
2. **No se sustituyen por versiones `PROPUESTO`** ni por reconstrucciones, resúmenes o conversiones a otro formato.
3. **Prevalecen sobre todo documento derivado** del repositorio ante cualquier discrepancia.
4. Toda reinterpretación posterior del canon —instanciación de casos, trazas a CA, umbrales— debe citar **estos ficheros**, no los resúmenes que los precedieron.
5. Si una fuente se actualizara a una versión posterior aprobada, se materializa **junto a** la actual, con nueva entrada de manifiesto y nuevas huellas; **no se sobrescribe**.
6. Las huellas se reverifican con:

```
cd docs/architecture/canonical_sources
sha256sum -c SHA256SUMS.txt   # si se genera; en su defecto, contrastar con la tabla §1
```

---

## 6. Resumen de huellas

```
b28a2cbed62b90f35e28db2412e46939b9bd2cdb8f145a5e9bbb2a8e7a5cbb45  SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO.docx
39058c0f5fe50bb4b703411bd5296e1bb8b1ede513ccf2d9eacabb35da3f59fd  SIRIUS_0.2_PLAN_DE_PRUEBAS_Y_REGISTRO_EXTERNO_DE_DELEGACIONES_v1.0_APROBADO.docx
730a5fd13dce18bfcdb8dd4afee23dfe22c067c7cb3b953a9bd115cf73224f49  SIRIUS_0.2_ARQ_00_MARCO_RECTOR_ARQUITECTURA_Y_MAPA_DECISIONES_v1.0_APROBADO.docx
```

---

**Siguiente movimiento único:** con `SRC-ADR002-01` satisfecha, el trabajo autorizado es **verificar la trazabilidad y completitud del canon frente a los documentos derivados** —inventario normativo, especificación de benchmark y Registro de Tolerancias v0.4— antes de abordar las cuatro puertas de arranque restantes. No se construye corpus, no se ejecuta T0 y no se ejecuta ningún candidato.
