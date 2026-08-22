# SIRIUS 0.2 — ADR-002 · Reaprobación conjunta de las cuatro fichas sucesoras

**Versión:** 1.0
**Estado:** **APROBADAS · `A` v6, `B` v8, `C` v3 y `D` v3 PREPARADAS PARA BENCHMARK**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**
**HEAD aprobado:** `77fe7c78f84ba80f2491165550c6e01e379a51c6`

**Autoridad:** `SIRIUS_0.2_ADR_002_PAQUETE_CORRECCION_CAPA_COMUN_v0.1.md` §6,
paso 3, sobre la elección del usuario de corregir la capa común.

**Acto de aprobación:** el usuario, directamente en el chat de trabajo, sobre la
solicitud única que citaba las cuatro huellas:

> «**Sí venga**»

---

## 1. Lo aprobado

| Ficha | Estado | Huella canónica | Sustituye a |
|---|---|---|---|
| `ficha_ADR002-A_v6.json` | **CONGELADA · PREPARADA** | `d305073ce5bb21a07e8523969752a9f06a966d01` | v5 |
| `ficha_ADR002-B_v8.json` | **CONGELADA · PREPARADA** | `b7ea269da379fc0de324efa5ca2da7baa616d112` | v7 |
| `ficha_ADR002-C_v3.json` | **CONGELADA · PREPARADA** | `ef71f944536ffc07dd18b39278ba43da2776232c` | v2 |
| `ficha_ADR002-D_v3.json` | **CONGELADA · PREPARADA** | `5ca687f88a7d194a922ca39eb32778c0ab02608c` | v3 → v2 |

Las cuatro predecesoras pasan a **SUSTITUIDA** y se conservan íntegras. Ninguna
se borra ni se reescribe.

---

## 2. Por qué había que reaprobar

Las fichas describen a los candidatos, y el paquete de corrección cambió lo que
los cuatro hacen:

- la lectura de polaridad mira ahora el **alcance** de la negación y no su
  presencia —de 66 lecturas contrarias al canon a **cero**, sin perder ninguna
  de las tres negaciones reales—;
- la puerta del tiempo comprueba la **aplicabilidad** además del corte de
  registro, de modo que lo que aún no está en vigor deja de entrar;
- la puerta de disponibilidad lee el **eje `P2`** en vez del estado colapsado, de
  modo que lo archivado deja de pasar por modos ordinarios.

`ADR002-TOL-210` es explícito: medir bajo una ficha distinta de la declarada
produce **evidencia no utilizable**. Con las fichas viejas, la repetición de la
ronda no habría valido para nada.

---

## 3. Lo que cambia en cada ficha, y lo que no

Cada sucesora parte de la ficha que sustituye y cambia **solo** lo que la
corrección cambió: la versión, el commit del prototipo, los árboles de fuentes,
el motivo de la sucesión y las citas a las versiones vigentes de sus
dependencias. Todo lo demás viaja byte a byte, y eso es comprobable comparando
las dos versiones.

**Una de esas citas estaba mal en la primera emisión** y una prueba lo detectó:
`D` v3 declaraba derivar de `A` v5, `B` v7 y `C` v2 —fichas que su propia
emisión acababa de sustituir—. Una ficha que nombra como base a una ficha
sustituida describe un candidato que ya no existe. Se corrigió antes de esta
aprobación, y por eso las huellas de `C` y `D` no son las que se emitieron
primero: la cita forma parte de la forma canónica.

---

## 4. Lo que esta acta autoriza y lo que no

**Autoriza** repetir la ronda primaria con el **arnés congelado y sin tocar**:
los mismos cinco participantes sin reducción, las mismas once sesiones exactas,
las mismas cien repeticiones, el mismo warm-up de diez descartado, la misma
semilla `20260726`, el mismo reloj y el mismo orden intercalado y rotado, sobre
el mismo sustrato.

**No autoriza** cambiar el plan de medición, reducir la ronda, elegir
alternativa, cerrar `ADR-002`, abrir ningún eje contingente, tocar Sirius 0.1
productivo ni fusionar el PR #117.

La corrida `v0.1` **se conserva íntegra** como evidencia de lo que se midió
antes de corregir. La repetición se publica aparte, y el contraste entre las dos
es parte de lo que hay que entregar: sin él, la corrección sería una promesa.
