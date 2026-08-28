# SIRIUS 0.2 — ADR-002 · Fe de erratas 01 · corrección de identidad Git en la evidencia de TOL-208

**Versión:** 1.0
**Estado:** **APROBADO** — corrección de custodia; **no altera evidencia, cifras ni veredictos**
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**HEAD de partida verificado:** `c5f76cd89a56d45d2822b3e9010ca02c9a9f6a20`
**Detectado por:** el usuario, sobre la evidencia final de `ADR002-TOL-208`
**Alcance:** exclusivamente la **cita de identidad Git** errónea; ninguna otra cosa
**No autoriza:** ejecutar mediciones, reescribir evidencia v0.1 o v0.2, aprobar `ADR002-TOL-208`, crear su acta final de satisfacción, iniciar el benchmark ni fusionar el PR #117.

---

## 1. La errata

| | Valor |
|---|---|
| **SHA erróneo publicado** | `5797f5205cdb3054921054461f77dbdb8f550af4` |
| **SHA correcto y vinculante** | `5797f523c9d4f0e0d3f99599493b6e3167b29f9d` |
| **Prefijo abreviado compartido** | `5797f52` — **idéntico en ambos** |
| **Objeto identificado** | commit 1 de la repetición única del §6.8: acta de autorización, condiciones controladas congeladas y arnés preinscrito |
| **Naturaleza** | transcripción humana del SHA completo en un informe de lectura; **no** un valor derivado de ningún cálculo, medición ni artefacto |

El SHA erróneo **no resuelve a ningún objeto** del repositorio:

```text
$ git cat-file -e 5797f5205cdb3054921054461f77dbdb8f550af4^{commit}
fatal: Not a valid object name 5797f5205cdb3054921054461f77dbdb8f550af4^{commit}

$ git rev-parse 5797f52
5797f523c9d4f0e0d3f99599493b6e3167b29f9d
```

### 1.1 Por qué la identidad vinculante es el SHA completo

Ambos SHA comparten el prefijo abreviado `5797f52`, y ese prefijo **sí resuelve
correctamente** al commit real. Esa coincidencia es exactamente lo que impidió
que la errata se detectara en una lectura humana: un lector que abrevia mentalmente
—o que copia los siete primeros caracteres— obtiene el objeto correcto.

**La identidad vinculante de un commit es su SHA completo**, no su prefijo. Un
prefijo es una comodidad de lectura cuya resolución depende del contenido del
repositorio en el momento de resolverlo; el SHA completo es la identidad
criptográfica del objeto. Por eso la corrección fija el completo y por eso este
documento declara ambos: para que quien encuentre el erróneo en la evidencia
inmutable sepa, sin ambigüedad, a qué objeto se refería.

### 1.2 Cómo se produjo, y por qué la evidencia máquina no la sufrió

El informe humano transcribió el SHA; el artefacto de máquina lo **obtuvo de
Git en tiempo de ejecución**. Por eso
`rederivacion_t0_v0.2_muestras.json` lleva, desde el momento de la corrida, el
SHA **correcto** en su campo `head_en_ejecucion`:

```json
"head_en_ejecucion": "5797f523c9d4f0e0d3f99599493b6e3167b29f9d",
```

La lección está registrada y ya materializada (§4): **un dato observable no se
transcribe, se observa**; y toda cita de identidad debe ser comprobable por
máquina, no por lectura.

## 2. Dónde aparece la referencia incorrecta

Auditoría exhaustiva sobre `docs/architecture/` y `artifacts/`: **225 SHA de
cuarenta caracteres examinados en 45 ficheros**. La referencia incorrecta
aparece en **un único lugar**:

| Documento | Línea | Contexto | Blob del documento |
|---|---|---|---|
| `artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.2_PROPUESTO.md` | 7 | «**Commit de ejecución (`HEAD` al medir)**» | `dac5155914d55b7e1e294ebca1d16f0ef6e6e656` |

Y, fuera del repositorio, en el **informe de misión** entregado al usuario por
mensaje, que no es un artefacto versionado y queda corregido por el informe
sucesor del §3.

**Ningún otro documento, acta, artefacto o módulo contiene la referencia
incorrecta.** En particular **no** la contienen: el artefacto normativo
`rederivacion_t0_v0.2.json`, las muestras crudas
`rederivacion_t0_v0.2_muestras.json` (que llevan el SHA correcto), el acta de
autorización de la repetición, ni ninguno de los tres artefactos v0.1.

### 2.1 Las demás citas no resueltas, y por qué son correctas

La misma auditoría encontró otros cinco SHA que no resuelven a objetos Git.
**Ninguno es una errata**, y se inventarían aquí para que nadie tenga que
volver a decidirlo:

| SHA | Apariciones | Por qué su ausencia es correcta |
|---|---|---|
| `d47a767e61b30729e15f48c9924413f6fddc9429` | 4 | **Huella canónica** de la ficha `T0-control` v1: SHA-1 del blob de la *forma canónica* de la ficha —el JSON ordenado **excluido el propio campo de huella**—, un contenido que por construcción nunca se escribe como fichero. Que Git no lo encuentre es lo correcto; su verificación es **recomputarla**, y recomputa |
| `b57ad7b24c7f0232d45540cde73294e2d68e02ef` | 1 | **Captura de entorno de ADR-001**: `HEAD` observado de la rama histórica `fix/chat-history-layout` al ejecutar los spikes, registrado como observación ambiental —no como cita vinculante de ADR-002—. Esa rama no forma parte del historial de `evidence/adr001-spikes`. **Fuera del alcance** de esta fe de erratas; se registra como hallazgo |

## 3. Corrección publicada, sin reescribir nada

**La evidencia no se reescribe.** El informe v0.2 conserva su contenido exacto
y su blob `dac5155914d55b7e1e294ebca1d16f0ef6e6e656`: corregirlo en el sitio
destruiría la inmutabilidad que toda la cadena de custodia existe para
sostener, y dejaría sin rastro el hecho de que la errata ocurrió.

La corrección se publica como **documento sucesor**, que sustituye al v0.2
**como lectura vigente** sin sustituirlo como evidencia:

> `artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.2.1_PROPUESTO.md`

El sucesor reproduce el informe v0.2 **íntegro y sin un solo cambio de fondo**
—mismas cifras, mismas tablas, mismo veredicto, mismo §6.9—, con exactamente
dos diferencias: el SHA de ejecución correcto, y el enlace explícito a esta fe
de erratas. Ambos documentos coexisten y se citan mutuamente.

## 4. La corrección de fondo: la cita de identidad, comprobable por máquina

Una errata que ninguna prueba podía detectar es un defecto del aparato de
custodia, no solo del documento. Este commit lo cierra:
`experiments/adr002/rederivation/custody_errata.py` recorre `docs/architecture/`
y `artifacts/`, extrae **todo** SHA de cuarenta caracteres y exige que resuelva
a un objeto del repositorio. Falla cerrado.

Las dos únicas clases de excepción están **inventariadas con su motivo** —los
hashes que por construcción no son objetos almacenados (§2.1) y las erratas
declaradas (§1)—, y la excepción de la errata queda **anclada al blob del
documento afectado**: si alguien editara el informe v0.2, su blob cambiaría, la
excepción caducaría y la comprobación volvería a fallar. La excepción tampoco
se hereda: el SHA erróneo solo puede aparecer en el documento afectado y en los
documentos cuya función declarada es discutir la errata. **Una cita rota nueva,
en un documento nuevo, falla.**

## 5. Qué NO afecta esta errata

Comprobado, no supuesto:

| Aspecto | Estado |
|---|---|
| **Muestras crudas** | intactas: 6 600 valores v0.1 + 6 600 v0.2, byte a byte |
| **Cifras** | ninguna cambia: percentiles, mínimos, máximos, dispersiones y bandas se recomputan desde los crudos |
| **Método** | intacto: protocolo v0.2, perfil, bandas, corpus, ficha, consultas, escenarios, capas, cronómetro, repeticiones, sesiones, esquema, percentiles |
| **Blobs** | los seis artefactos de evidencia conservan sus blobs exactos (§6) |
| **Veredictos** | idénticos: 3 `VALIDA` · 3 `INVALIDA` en la corrida v0.2 |
| **Resultado §6.9** | idéntico: 3 `VALIDA` · 3 `NO_EVALUABLE` en rendimiento |
| **Repetición única** | sigue **consumida**; ninguna corrida adicional se ha ejecutado ni se autoriza |
| **Custodia de anterioridad** | intacta: la ficha `T0-control` v1 entró en `95d00a1c…`, ancestro estricto de **ambos** commits de ejecución, y esa relación se observa en el grafo, no en el texto del informe |

La errata afecta a **una cadena de cuarenta caracteres en la cabecera de un
informe de lectura humana**, y a nada más.

## 6. Identidad verificada de la evidencia

### 6.1 Los tres commits, con su SHA completo correcto

| Commit | SHA completo vinculante |
|---|---|
| Ejecución original (evidencia v0.1) | `425964872c73ec4e4f44d80189907d7ca08bedff` |
| Autorización de la repetición §6.8 y arnés (commit 1) | **`5797f523c9d4f0e0d3f99599493b6e3167b29f9d`** |
| Repetición consumida y evidencia v0.2 (commit 2) | `c5f76cd89a56d45d2822b3e9010ca02c9a9f6a20` |
| HEAD de partida de la repetición | `3c9a1cb4185fead79c4c13d0c07d2223d223f782` |

### 6.2 Los seis artefactos de evidencia, intactos byte a byte

| Artefacto | Blob Git |
|---|---|
| `rederivacion_t0_v0.1.json` | `781132bfe0365f6b7ebcb9139330d10dc76fd0db` |
| `rederivacion_t0_v0.1_muestras.json` | `04cd805181f9067318adaf84aaa676df1eb52c7c` |
| `INFORME_REDERIVACION_T0_v0.1_PROPUESTO.md` | `11d41f42838a3fb3512bfe32dcf9e35689980611` |
| `rederivacion_t0_v0.2.json` | `9140c1c031ed4bff891fc0fdabb04b4480a8d817` |
| `rederivacion_t0_v0.2_muestras.json` | `8a61b8e519d6d854d782106aed19614ebd2377a5` |
| `INFORME_REDERIVACION_T0_v0.2_PROPUESTO.md` | `dac5155914d55b7e1e294ebca1d16f0ef6e6e656` |

Los tres primeros son además intangibles por el módulo de condiciones
controladas, que los comprueba como precondición de cualquier ejecución.

## 7. Lo que esta fe de erratas no hace

- **No reescribe ni elimina** la evidencia v0.1 ni la v0.2: ambas conservan sus
  blobs exactos y su valor probatorio.
- **No ejecuta ninguna medición** ni corrida adicional. La repetición del §6.8
  sigue consumida y una tercera corrida sigue **prohibida**.
- **No modifica** ninguna cifra, veredicto, tolerancia, criterio ni resultado.
- **No aprueba `ADR002-TOL-208`** ni crea su acta final de satisfacción.
- No inicia el benchmark, no implementa candidatos, no modifica Sirius 0.1
  (`src/`, `tests/`, `migrations/`, configuración productiva) y **no fusiona el
  PR #117**.

---

**Decisión final:** queda establecido que la identidad vinculante del commit de
autorización y preinscripción de la repetición única del §6.8 es
**`5797f523c9d4f0e0d3f99599493b6e3167b29f9d`**, que la cita
`5797f5205cdb3054921054461f77dbdb8f550af4` publicada en el informe v0.2 es
**errónea y no resuelve a ningún objeto**, y que el error **no afecta muestras,
cifras, método, blobs, veredictos ni el resultado del §6.9**. La lectura
vigente pasa a ser el informe sucesor v0.2.1; el informe v0.2 se conserva
intacto como evidencia. `ADR002-TOL-208` permanece **NO SATISFECHA** a la
espera del acto explícito del usuario.
