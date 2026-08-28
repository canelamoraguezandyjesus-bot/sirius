# SIRIUS 0.2 — ADR-002 · Corrección de la recomendación

**Versión:** 1.0
**Estado:** **CORRIGE la recomendación de `ADR002-A` · pasa a `ADR002-C`**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Artefacto:** `artifacts/adr002_round/discriminante_relacional_v0.1.json`.

---

## 1. El defecto

La ronda primaria ejecutaba **solo el nivel 1**. `cases.casos_ejecutables`
recorre `casos["nivel_1"]` y nada más.

El banco tiene un caso de **nivel 4**, `N4-01` / `ADR002-DISC-REL-01`, cuyo
propósito literal es:

> «Falsar la suficiencia de una expansión **exclusivamente léxica-estructurada**
> ante una dependencia explícita entre dos sujetos **sin solapamiento léxico**.»

Con su referencia calculada **por un camino independiente del generador** —los
textos cargados en una tabla `FTS5` con la configuración efectiva del índice de
Sirius 0.1, resuelta con `MATCH`—, y con cero tokens compartidos entre los dos
extremos.

**Ese caso nunca se ejecutó.** Las dos corridas publicadas midieron la
aportación de la señal relacional **sin ejecutar el único caso construido para
que esa señal importe**.

---

## 2. Lo que dije, tres veces, y por qué estaba mal

Escribí en tres documentos alguna variante de:

> «Este corpus tiene diez relaciones, de modo que `C` no cambie ni un resultado
> describe la superficie relacional del banco tanto como al candidato.»

La frase presentaba como **limitación del banco** lo que era **un hueco de mi
arnés**. El banco no es pobre en discriminación relacional: tiene un caso
dedicado, con oráculo independiente, y yo no lo corría. La cautela era correcta
en la forma y falsa en el fondo.

---

## 3. Lo que el caso dice, ejecutado

| Participante | ¿Alcanza `MEMORIA:950`, el léxico? | ¿Alcanza `MEMORIA:951`, **solo por la arista**? | Etapa |
|---|---|---|---|
| `T0-control` | sí (entre otros 21) | **no** | — |
| `ADR002-A` | sí | **no** | — |
| `ADR002-B` | sí | **no** | — |
| `ADR002-C` | sí | **sí** | `E3` |
| `ADR002-D` | sí | **sí** | `E3` |

**`ADR002-A` falla el caso discriminante.** La señal vectorial de `ADR002-B`
**no lo suple**: la similitud distribucional no encuentra un destino que no
comparte ni un token con la consulta. Solo la arista explícita lo alcanza, y la
alcanza en `E3`, que es exactamente la etapa en que `C` y `D` la declaran.

Es la falsación que el caso venía a hacer, y la hace: **la expansión
exclusivamente léxica-estructurada no basta.**

---

## 4. La recomendación corregida: **`ADR002-C`**

| | Nivel 1 exactos | Etapa | Discriminante `N4-01` | `P50` | Almacenamiento |
|---|---|---|---|---|---|
| **`ADR002-C`** | **23/47** | **43/45** | **PASA** | 222–259 ms | **0 B** |
| `ADR002-D` | 21/47 | 41/45 | **PASA** | 235–293 ms | 35 016 704 B |
| `ADR002-A` | **23/47** | **43/45** | **falla** | 221–262 ms | 1 462 272 B |
| `ADR002-B` | 21/47 | 41/45 | **falla** | 241–290 ms | 35 016 704 B |

`ADR002-C`:

1. **Empata con `A`** en todas las métricas de nivel 1 —los mismos 23 exactos,
   la misma conformidad de etapa, latencia indistinguible—;
2. **pasa el caso discriminante que `A` falla**;
3. **consume cero almacenamiento adicional**, menos que `A`;
4. y lo hace con **una sola** señal tardía, en `E3`, la etapa que `B04 §15.1`
   nombra para las relaciones.

`ADR002-D` también pasa el discriminante, pero añade la señal vectorial, que en
las dos corridas **no mejoró ni un caso**, rompió dos que `C` acierta exactos y
cuesta 35 MB. `D` es `C` más algo que solo resta.

---

## 5. Lo que **no** cambia

- **Las cifras publicadas de `v0.1` y `v0.2`** siguen intactas: midieron los
  cincuenta casos de nivel 1 y eso es lo que dicen. Lo que cambia es lo que
  puede concluirse de ellas.
- **La readjudicación** sigue válida: cuatro puertas en verde, una roja.
- **`ADR-002` sigue sin poder cerrarse por cumplimiento**: la conformidad de
  etapa sigue roja para los cuatro, con dos incumplimientos reales.
- **La señal vectorial sigue sin pagar su coste.** Eso se midió tres veces y el
  discriminante no lo cambia: `B` tampoco lo pasa.

---

## 6. Lo que esto enseña sobre el método

La conclusión anterior no era falsa **por los datos**: sobre los cincuenta casos
de nivel 1, `A` y `C` empatan y eso sigue siendo cierto. Era falsa **por el
recorte**: un conjunto de casos que excluía el único diseñado para separarlos.

El banco había previsto exactamente este riesgo —por eso existe un nivel 4— y el
arnés lo perdió. La lección no es «medir más», es que **un recorte del banco es
una decisión metodológica** y no un detalle de implementación: `casos["nivel_1"]`
parecía una línea de código y era la hipótesis de la comparación.

---

## 7. Lo que queda abierto, ahora sí

- **La conformidad de etapa**, roja para los cuatro: `CA-25` y `CA-33` expandieron
  de más y devolvieron mal.
- **El marcado de `M2`**, exigido por el canon y sin métrica.
- **Los niveles 2 y 3 del banco** —cinco casos arquitectónicos y siete
  ablaciones— **tampoco se han ejecutado**. Lo declaro ahora que sé lo que cuesta
  no declararlo: no sé qué dirían, y hasta ejecutarlos ninguna comparación entre
  `C` y `D` está completa.

---

## 8. Solicitud única

> **¿Se aprueba esta corrección, se acepta `ADR002-C` como alternativa preferida
> —sin declararla conforme—, y se autoriza ejecutar los niveles 2 y 3 del banco
> antes de plantear el cierre de `ADR-002`?**

No se elige alternativa en firme, no se cierra `ADR-002` y no se fusiona el
PR #117.
