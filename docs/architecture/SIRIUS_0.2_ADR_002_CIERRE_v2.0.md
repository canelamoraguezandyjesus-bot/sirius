# SIRIUS 0.2 — ADR-002 · Cierre v2.0

**Versión:** 2.0 · **sustituye a** `SIRIUS_0.2_ADR_002_CIERRE_v1.0.md`
**Estado:** **ADR-002 sigue sin poder cerrarse eligiendo una alternativa.**
**Rama:** `evidence/adr001-spikes` · **PR:** #117, abierto y sin fusionar
**Decisión del responsable:** cerrar con la puerta roja y la causa nombrada, en vez de forzar el
verde.

**Artefactos:** `artifacts/adr002_round/las_dos_puertas_v0.1.json` y los seis resultados de
medición `resultado_modelo_local*.json`.

---

## 1. Lo que cambia respecto del cierre v1.0, y lo que no

El cierre v1.0 dejó **dos** obligaciones en rojo para los cuatro candidatos: **recall crítico** y
**conformidad de etapa**. La primera ha mejorado mucho. La segunda no se ha movido.

| puerta | al cerrarse v1.0 | ahora |
|---|---|---|
| **recall crítico** (`B04-M01`, 100 % por caso) | 16 omisiones en 6 casos | **1 omisión en 1 caso** |
| **conformidad de etapa** | roja | **roja: 14 de 46 casos** |

**El veredicto de v1.0 se mantiene.** No por lo mismo, y no con la misma distancia.

---

## 2. La primera puerta: de dieciséis a una

Los seis casos que la cerraban, uno por uno:

| caso | estado | qué lo resolvió |
|---|---|---|
| `N1-02` | resuelto | la categoría buscable |
| `N1-31` | resuelto | la categoría buscable |
| `N1-44` | resuelto | la regla de las críticas |
| `N1-33` | resuelto | la siembra al ensamblar contexto |
| `N1-34` | resuelto | la siembra al ensamblar contexto |
| **`N1-30`** | **abierto** | — |

Con el umbral en 100 %, **una omisión reproducible elimina la alternativa**. La puerta sigue roja.

### El caso que queda, y las cinco vías medidas

`N1-30` pide «preferencia de **redacción**»; el dato dice «prefiere que **redactes**». Es
derivación —nombre contra verbo, con cambio de raíz—, no flexión.

| vía | veredicto |
|---|---|
| recorte de sufijos, variantes, trigramas | no unen las palabras |
| **lematizador** | no une: son lemas distintos |
| señal semántica densa | medida y refutada en todo el banco |
| ampliación al guardar | medida dos veces: no aporta |
| **ampliación al buscar** | medida: **2 variantes de 256 palabras**. No cierra |

Y el atajo que sí lo cerraría: indexar `criticidad.razon`, que contiene la palabra «redacción». **No
se usa.** Es la anotación escrita por quien construyó el banco después de conocer las preguntas;
usarla haría que el banco se aprobase a sí mismo. Queda escrito para que conste que se vio.

---

## 3. La segunda puerta: intacta, y este trabajo no la mejora

**14 de 46 casos** no son conformes de etapa. Antes y después.

Lo construido esta semana **arregla `N1-33` y rompe `N1-31`**. Saldo cero.

Y el que rompe importa decirlo: **la categoría buscable rompe la etapa de `N1-31` justo por
arreglar su recall crítico**, porque trae en `E1` lo que el caso declaraba para más tarde. Es un
coste real de lo construido, no un detalle.

Las razones de los que fallan en las dos configuraciones:

| veces | razón |
|---|---|
| 5 | resuelto en `E1` y el caso declara `E4` |
| 3 | resuelto en `E1` y el caso declara `E3` |
| 1 | resuelto en `E3` y el caso declara `E4` |
| 1 | resuelto en `E2` y el caso declara `E3` |
| 1 | resuelto en `E3` y el caso declara `E1` |
| 1 | el caso declara `E0` y la expansión aportó en `E3` |
| 1 | resuelto en `E1` y el caso declara `E2` |

El patrón dominante es **resolver antes de lo declarado**. El cierre v1.0 ya advirtió que esta
puerta se mide contra una instanciación modificable; esa cuestión **no se resuelve aquí**, y no se
resuelve a propósito: reinterpretarla ahora, sabiendo que es lo único que queda, sería mover la
medida sobre el resultado.

---

## 4. Lo que sí queda establecido

Tres piezas construidas y medidas, con su estatuto declarado:

- **La regla de las críticas** — *medida y confirmada*. Si el filtro conserva algunas, no puede
  descartar una crítica; si declara que ninguna responde, ese veredicto se respeta entero. Vive en
  el código, no en la instrucción. Predicha antes de escribirse, confirmada en máquina.
- **La categoría buscable** — *medida, sin modelo*. Determinista y regenerable. Por sí sola lleva
  las omisiones de once a cinco.
- **La siembra al ensamblar contexto** — *no validable con este banco*, y así se declara: se
  escribió tras ver los fallos y los dos únicos casos con ese propósito son esos dos.

Y cinco vías cerradas con datos: fusión híbrida `RRF`, semántica densa, ampliación al guardar,
compuerta de sí/no, y devolver todas las críticas del ámbito.

---

## 5. Qué se recomienda

**No forzar el verde.** Ni reinterpretando la puerta de etapa, ni indexando la anotación prohibida,
ni bajando el umbral del 100 %.

ADR-002 queda cerrado como **no conforme**, con las dos puertas nombradas, la distancia a cada una
medida, y todas las vías intentadas publicadas con su resultado. La primera puerta está a un caso; la
segunda es un problema distinto y mayor, y merece su propio paquete cuando se abra la definición de
producto de Sirius 0.2.

Lo construido no se tira: está medido, probado y disponible. Lo que no se hace es llamarlo conforme.
