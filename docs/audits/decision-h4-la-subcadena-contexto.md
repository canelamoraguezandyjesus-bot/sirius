<!-- Informe para el propietario. Diagnostico cerrado; la decision no. -->

# H4 — no es un encargo de implementación: es una decisión de producto

**Estado**: diagnosticado hasta el mecanismo. No se lanza al motor hasta que el
propietario decida, porque lo que falta no es trabajo sino un criterio suyo.

## El caso

`B04-CA-30`, ámbito `PRJ-ALFA`: «Resume mi preferencia de redacción, el
presupuesto vigente y la condición de ahorro en escalas, con su razón».
Espera `DEC-003`, `MEM-001` y `MEM-016`. Hoy entran dos y **falta `MEM-001`**
—«El usuario prefiere que redactes en tono directo y sin adornos»—, que es
`PRJ-GLOBAL` con eje `ambito=GLOBAL`.

## Lo que ADR-148 dice, y por qué no se sostiene

ADR-148 lo clasifica como **de ranking**: «entra en EXHAUSTIVA y queda fuera del
límite en ACOTADA». Medido sobre `22e880e` con `--peticion`, forzando
`cardinalidad=EXHAUSTIVA` y `limite=None` **solo en ese caso**: entran 5 y
`MEM-001` **no está entre ellos**. No es el límite.

## La causa real, aislada variable a variable

| hipótesis | resultado |
|---|---|
| el límite de ACOTADA lo expulsa | **NO** — sin límite sigue fuera |
| el ámbito excluye lo global | **NO** — con ámbito global sigue fuera, y el banco cae a `12/47; 283; 69/81; 1` |
| `tiempo_objetivo` | **NO** |
| usar la política uniforme solo en ese caso | **SÍ entra**, `faltan=[]`, 8 elementos |
| sustituir **solo `proposito`** | **SÍ entra**, `faltan=[]`, con 2 extras más |

Y el mecanismo, leído en el código:

- `MEM-001` **no llega por la búsqueda**: llega por la **ampliación por
  categoría** (M14).
- Esa ampliación corre solo si `category_matching_enabled` **y**
  `pide_contexto(peticion.proposito)` — `rank_relevant_knowledge.py:539`.
- `pide_contexto` es una **comprobación de subcadena**:
  `PROPOSITO_DE_CONTEXTO in proposito.casefold()`, con
  `PROPOSITO_DE_CONTEXTO = "contexto"` — `relevance.py:156` y `345-354`.
- El propósito de la política uniforme, `'recuperacion de contexto relevante
  (B6b)'`, contiene «contexto». El que el caso declara,
  `'responder_al_usuario'`, no.

**Toda la diferencia es esa subcadena.**

## Por qué esto es tuyo y no del motor

1. **La ampliación exige `category_matching_enabled`**, que el arnés del banco
   abre (`category_matching_enabled=True`) y **producción no**. En el producto
   de hoy `MEM-001` es inalcanzable por ese camino **sea cual sea el
   propósito**. H4 no se cierra sin decidir sobre esa puerta, y ésa es
   justamente la decisión que ADR-148 reserva para el final de la línea.
2. **La activación depende de que una cadena libre contenga «contexto»**. Eso
   es la deuda 2 —decidir por subcadena— en un sitio nuevo y con más peso:
   aquí no produce un falso positivo, decide si se enciende un camino de
   recuperación entero.

## Las opciones, con lo que cuesta cada una

- **(a) Que responder al usuario active la ampliación.** Es lo que el caso
  espera. Coste medido: `MEM-001` entra y el caso queda exacto, con **2 extras
  más** en ese caso. Exige abrir `category_matching_enabled` en producción, o
  al menos decidir cuándo se abre.
- **(b) Dejar de decidir la activación por subcadena** y que la petición
  declare explícitamente si quiere la ampliación. Arregla la fragilidad de
  fondo (deuda 2) además de este caso, y es más trabajo.
- **(c) Aceptar que `MEM-001` no entra en este caso** y ajustar la expectativa
  del banco. **Ojo: esto tocaría `resultado_esperado`, que está prohibido sin
  decisión tuya explícita**, y yo no lo recomiendo: la pregunta pide
  literalmente la preferencia de redacción.

## Lo que NO se ha tocado para llegar aquí

Ni el corpus, ni `resultado_esperado`, ni ninguna adjudicación, ni `G8`, ni el
puerto, ni `src/`. Todo son sondas de solo lectura sobre `22e880e`.
