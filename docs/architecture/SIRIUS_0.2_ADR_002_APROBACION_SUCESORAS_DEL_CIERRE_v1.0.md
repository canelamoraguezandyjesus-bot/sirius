# SIRIUS 0.2 — ADR-002 · Aprobación de las sucesoras del paquete de cierre

**Versión:** 1.0
**Estado:** **APRUEBA `A v7`, `B v9`, `C v4` y `D v4` como PREPARADOS PARA BENCHMARK**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** el usuario, sobre la solicitud de cierre: «**tú eres el que siempre
elige la forma de continuar… elige tú, y solo para y entrégame el resultado final
bueno**», con permiso expreso para todo lo necesario.

---

## 1. Qué se aprueba

| Candidato | Sustituye a | Ficha | Huella |
|---|---|---|---|
| `ADR002-A` | v6 | v7 | `653f216f67d389fdf0472159eea896366e623484` |
| `ADR002-B` | v8 | v9 | `93b9cf6c3a49ccd2ad0ef455ddf4a880c78a6d05` |
| `ADR002-C` | v3 | v4 | `5801987de7574c0b416c7b9c74acc6b527652f79` |
| `ADR002-D` | v3 | v4 | `eed670548216aef2fef23e435ad639d2fab72011` |

Las cuatro anteriores pasan a `SUSTITUIDA` con su huella recalculada. `T0-control
v1` **no se toca**: el paquete no alcanza al control.

---

## 2. Por qué hay sucesoras

Tres cambios en la capa común, y **ninguno cambia qué se recupera**:

1. **`trace.py` publica cuál** de los tres estados históricos es un elemento no
   vigente. `B04 M2` no pide solo que lo viejo vuelva marcado: pide que la
   respuesta **permita archivado, sustituido y finalizado**, y `M3` y `M4`
   necesitan saber cuál. La marca era binaria y los hacía indistinguibles.
2. **`grouping.py` usa la misma marca** para los miembros de un grupo. Dos marcas
   distintas del mismo elemento en la misma respuesta serían una contradicción.
3. **El lector base gana `con_validacion_semantica`**, apagado por defecto, que
   hace ejecutable la ablación `AB-4`.

Los ejes `P2` que la marca lee ya estaban en el elemento, y la lista blanca de la
familia vigente **ya autorizaba** su lectura: no se amplió ningún permiso.

---

## 3. La comprobación que sostiene «no cambia qué se recupera»

No es una afirmación de diseño; se midió antes de aprobar:

- **Los cincuenta conjuntos de la corrida `v0.2` se reprodujeron sin una sola
  divergencia** al reobservar el marcado con el código nuevo.
- La suite entera de `ADR-002` —1 916 pruebas— pasa sin tocar una sola aserción
  sobre resultados esperados.
- `G2` y `G8` deciden elegibilidad leyendo los ejes **directamente**, y no pasan
  por la marca publicada: la función nueva no puede admitir ni descartar a nadie.

La repetición de la ronda lo comprueba una vez más, y con la medición completa.

---

## 4. Lo que las tres guardas dijeron, y por qué se reanclaron

El paquete hizo fallar tres controles, y los tres estaban haciendo su trabajo:

- la prueba que afirmaba que **`AB-4` no era ejecutable** falló el día en que se
  añadió el interruptor, que es literalmente lo que decía que haría;
- la que afirmaba que **`M2.3` fallaba en los cuatro** falló al ponerse verde;
- los **blobs fijados** de `trace.py`, `grouping.py` y `adr002_a/candidate.py`
  denunciaron el cambio.

Ninguna se borró. Las dos primeras se reescribieron para afirmar lo que hay y
seguir vigilando lo que vigilaban; los blobs se reanclaron con su razón escrita,
como en cada sucesión anterior.

---

## 5. Alcance de esta aprobación

Se aprueba **congelar y medir bajo estas cuatro fichas**. No se elige alternativa
en firme, no se cierra `ADR-002` y no se fusiona el PR #117.

`ADR002-TOL-210` queda satisfecha por esta acta: las fichas son ancestro estricto
de la corrida que la cita.
