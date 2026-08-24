# SIRIUS 0.2 — ADR-002 · El marcado de `M2`, medido

**Versión:** 1.0
**Estado:** **DOS OBLIGACIONES CUMPLIDAS · una incumplida, y es de la capa común**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** el usuario, sobre la solicitud única de los niveles 2 y 3: «**Toma
el consumo adecuado para resolver eso, yo no entiendo lo que me planteas, tú
sabrás qué es mejor**». La elección de vía —instrumentar `M2` antes que
descongelar para `AB-4`— es mía, y el §6 dice por qué.

**Artefacto:** `artifacts/adr002_round/marcado_de_m2_v0.1.json`.

---

## 1. La obligación que llevaba tres documentos sin métrica

`B04`, modo `M2 · Histórico explícito`:

> «Permite archivado, sustituido y finalizado con marcas temporales; separa
> tiempo válido de corte de registro **y nunca lo presenta como actual**.»

La readjudicación la dejó escrita como `pendiente_de_medir` y ahí siguió. Era
**una obligación canónica sin ningún control**, y cerrar `ADR-002` sin ella
habría sido cerrar sobre una puerta que nunca se abrió.

---

## 2. Por qué esta vía y no `AB-4`

Quedaban tres carencias. Elegí esta por cuatro razones, en orden de peso:

1. **Es la única que bloquea el cierre.** La puerta de etapa es de cumplimiento
   obligatorio y el marcado de `M2` es obligación canónica. `AB-4` es un
   instrumento de medida que el propio banco declara que **nunca produce
   veredicto de conformidad**: informa, no desbloquea.
2. **No cuesta gobierno.** La marca **ya sale**: `trace.py` rellena
   `Explicacion.estado` y `Explicacion.tiempo` en cada resultado. Esto se **lee**.
   `AB-4` habría exigido descongelar los cuatro candidatos y emitir fichas
   sucesoras.
3. **No cambia la decisión.** La preferencia por `ADR002-C` es estable en cuatro
   instrumentos independientes; `AB-4` afinaría *por qué* gana, no *quién*.
4. **Es reversible.** Si después se decide correr `AB-4`, esto no estorba.

---

## 3. Cómo se midió sin tocar nada congelado

Se recorrieron los cincuenta casos y, por cada resultado entregado, se guardaron
las dos marcas publicadas para contrastarlas con lo que el corpus declara.

**No se tocó `metrics.py`**, que produjo las cifras de `v0.1` y `v0.2`: el §8.1
prohíbe cambiar la medición después de observarla. **No se tocó
`participants.py`** —el arnés que produjo esas cifras— sino que se abrió el motor
igual que él lo abre, para leer lo que él descarta.

### 3.1 El control que hace esto publicable

Volver a recuperar podía parecer «otra corrida». No lo es, y hay un control que
lo demuestra: **los cincuenta conjuntos se reprodujeron sin una sola
divergencia** frente a los congelados en `v0.2`. Si uno solo hubiera cambiado, el
ejecutor se detiene y no escribe artefacto.

No es una medición nueva: es **un canal de observación** que la primera corrida
no abrió sobre exactamente los mismos hechos.

---

## 4. Lo que dice, obligación por obligación

| | `T0` | `A` | `B` | `C` | `D` |
|---|---|---|---|---|---|
| **`M2.1` nunca lo presenta como actual** | n/m | ✅ | ✅ | ✅ | ✅ |
| **`M2.2` separa tiempo válido de corte** | n/m | ✅ | ✅ | ✅ | ✅ |
| **`M2.3` distingue archivado / sustituido / finalizado** | n/m | ❌ | ❌ | ❌ | ❌ |

`n/m`: `T0` **no es medible** aquí. No publica explicación por resultado, de modo
que no hay marca que leer. Es un incumplimiento que su ficha ya declara, no una
carencia de esta medición.

### 4.1 `M2.1` pasa, y **no** en el vacío

Esto era el riesgo real: si ningún candidato hubiera devuelto un solo elemento no
vigente, «nunca lo presenta como actual» habría salido verde sin comprobar nada
—aprobar sin presentarse—.

No es el caso. Los cuatro devolvieron los **tres** estados que `M2` nombra:

| Elemento | Ejes del canon | Estado | Marca recibida |
|---|---|---|---|
| `DECISION:2`, `DECISION:12` | `validez = SUSTITUIDA` | sustituido | `no vigente` |
| `MEMORIA:17` | `validez = SIN_SOPORTE` | finalizado | `no vigente` |
| `MEMORIA:4` | `disponibilidad = ARCHIVADA` | archivado | `no vigente` |

Ninguno volvió como actual. Y `MEMORIA:9` (`PURGADA`) y `MEMORIA:19`
(`NO_GUARDADA`) **no se devolvieron nunca**, que es lo que corresponde: esos no
son estados históricos, son elementos que no deberían poder recuperarse, y si
aparecieran el defecto sería de contaminación —puerta 1— y no de marcado.

Una prueba dedicada exige que los tres estados se ejerciten; si el banco dejara de
ejercitarlos, el verde dejaría de valer y la prueba lo diría.

### 4.2 `M2.3` falla, y el detalle importa

La salida publica **dos** valores: `vigente` y `no vigente`. El canon nombra
**tres** estados históricos.

De modo que lo no vigente **vuelve marcado**, pero no vuelve marcado **con cuál**.
Un archivado, uno sustituido y uno finalizado son indistinguibles en la respuesta,
y `M3 · Fuente` y `M4 · Gestión` necesitan exactamente esa distinción.

**El motor sí lee los ejes por dentro** —la corrección de la capa común le dio a
`G2` el eje de disponibilidad y a `G8` la aplicabilidad temporal—. El defecto no
es que no lo sepa: es que **no lo publica**.

---

## 5. Lo más importante para el cierre: el fallo **no separa alternativas**

`M2.3` falla **idéntico en los cuatro**, porque la marca la construye
`trace.py`, que es **capa común**.

Esto cambia de naturaleza la carencia:

- no es un defecto de `ADR002-C` que elegir `A`, `B` o `D` evitaría;
- **lo arrastraría cualquier alternativa que se elija**;
- y por tanto **no es un criterio de elección**: es una **condición de cierre**
  de `ADR-002`, que la decisión de alternativa no puede resolver.

---

## 6. Estado de las tres carencias

| Carencia | Antes | Ahora |
|---|---|---|
| Marcado de `M2` | **sin métrica** | **medida**: 2 de 3 cumplidas; la tercera, de la capa común |
| Conformidad de etapa | roja (`CA-25`, `CA-33`) | **roja, igual** |
| `AB-4` | no ejecutable | **no ejecutable, igual** |

Conviene ser exacto en lo que esto **no** hace: **no readjudica `CA-25` ni
`CA-33`**. Aquellos son fallos de conformidad de etapa —expandir más allá de lo
declarado y devolver mal—, y el marcado histórico no dice nada sobre ellos.
Esperar que los resolviera habría sido confundir dos obligaciones distintas.

Lo que sí hace es que **la puerta ya no está sin abrir**. Antes había una
obligación canónica que nadie medía; ahora está medida y dice algo concreto y
accionable.

---

## 7. Un defecto propio, corregido antes de publicar

La primera versión nombraba «vigente» a lo `PURGADA` y lo `NO_GUARDADA`, a la vez
que el mismo objeto los daba por **no** vigentes: una contradicción interna que
además habría contado un elemento purgado devuelto como un simple fallo de
marcado, cuando es contaminación y es mucho más grave.

Se corrigió —se nombran `no recuperable` y quedan fuera del alcance de `M2`— y el
defecto quedó escrito como prueba.

---

## 8. Solicitud única

> **¿Se aprueba esta medición como evidencia y se acepta que el incumplimiento de
> `M2.3` es una condición de cierre de `ADR-002` —de la capa común, no de ninguna
> alternativa—, o se prefiere corregir `trace.py` para publicar los tres estados
> antes de decidir?**

Corregir `trace.py` tocaría la **capa común congelada** y obligaría a emitir
fichas sucesoras de los cuatro candidatos y a repetir la ronda. No lo hago por
iniciativa propia.

No se elige alternativa en firme, no se cierra `ADR-002`, no se toca código
congelado y no se fusiona el PR #117.
