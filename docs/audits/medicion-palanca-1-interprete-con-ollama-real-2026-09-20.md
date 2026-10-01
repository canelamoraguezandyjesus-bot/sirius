# Palanca 1 (ADR-164) medida con Ollama real — 20-09-2026

Primera y única ejecución de `scripts/medir_interprete_de_peticion.py` con
modelo de verdad. La hizo el propietario en su máquina; CI no puede hacerla.
Árbol: `main` en `66f11424`. Modelo: `qwen3:4b-instruct`
(`0edcdef34593`, 2.5 GB). Adaptador: `num_ctx=8192`, `temperature=0.1`,
`think=false`, `keep_alive=15m`, timeout 30 s por llamada.

Las cadenas de consulta aparecen aquí corregidas del destrozo de la página de
códigos de la consola de Windows (`┐QuÚ` → `¿Qué`). Nada más se ha tocado: las
consultas se leen del JSON del banco y se comparan dentro del proceso, así que
la consola no afecta a ninguna cifra.

## Corrida 1 — CONTAMINADA, se registra igual

Una llamada de 47 agotó el timeout de 30 s y el adaptador **falló abierto**
(contrato del puerto), así que ese caso se resolvió con valores por defecto:

```
Interpretación de la consulta no disponible, se falla abierto (ReadTimeout)
```

Causa: arranque en frío. Se calentó con `ollama run`, que usa el contexto por
defecto, y el adaptador pide `num_ctx=8192`; Ollama recarga el modelo cuando el
contexto no coincide, así que la primera llamada real volvió a pagar la carga.

```
COINCIDENCIA CAMPO A CAMPO: 22/47
   modo: 40/47   admite_no_vigentes: 43/47   cardinalidad: 30/47
   limite: 42/47   tiempo_objetivo: 41/47    corte: 41/47
[interprete] SIN FILTRO: 0/47 exactos; 387 de mas; 74/81 hallados; omisiones criticas=0
```

## Corrida 2 — LIMPIA, cero rendiciones

Calentada con una petición idéntica a la del adaptador (`/api/chat`, mismo
`num_ctx`, mismo `keep_alive`). `ollama ps` confirmó `CONTEXT 8192` y
`100% GPU` antes de medir. **Ninguna línea de «se falla abierto».**

```
COINCIDENCIA CAMPO A CAMPO: 24/47
   modo: 40/47   admite_no_vigentes: 43/47   cardinalidad: 30/47
   limite: 42/47   tiempo_objetivo: 41/47    corte: 42/47
[interprete] SIN FILTRO: 0/47 exactos; 386 de mas; 74/81 hallados; omisiones criticas=0
```

### Contraste con la predicción, publicada en ADR-164 ANTES de medir

| criterio | predicho | medido | |
|---|---|---|---|
| coincidencia campo a campo | >= 45/47 | **24/47** | **FALLADA** |
| aciertos exactos | >= 16/47 | **0/47** | **FALLADA** |
| elementos de más | <= 162 | **386** | **FALLADA** |
| hallados | >= 73/81 | **74/81** | cumplida |
| críticas perdidas | 0 | **0** | cumplida |

Tres de cinco falladas. La predicción **no se ha retocado** después de verla.

### Los 23 casos que fallan (corrida limpia)

```
CA-03 cardinalidad        CA-05 tiempo_objetivo, corte
CA-06 tiempo_objetivo     CA-08 cardinalidad
CA-13 limite              CA-14 cardinalidad
CA-17 cardinalidad        CA-18 modo, cardinalidad
CA-22 modo, admite_no_vigentes, tiempo_objetivo, corte
CA-23 modo, admite_no_vigentes, limite
CA-25 cardinalidad        CA-26 cardinalidad, limite, tiempo_objetivo
CA-27 modo, cardinalidad  CA-28 modo, admite_no_vigentes
CA-30 cardinalidad, limite
CA-32 cardinalidad, corte CA-34 cardinalidad, limite
CA-36 cardinalidad, tiempo_objetivo, corte
CA-44 cardinalidad, tiempo_objetivo
CA-46 cardinalidad
CA-47 modo, admite_no_vigentes, cardinalidad, corte
CA-49 modo, cardinalidad  CA-50 cardinalidad
```

## Lo que las dos corridas dicen juntas

**El error está concentrado en `cardinalidad`: 30/47 en las DOS corridas.**
17 fallos, más de la mitad de todo el error, y el mismo número por dos caminos
distintos. No es ruido.

- **`ACOTADA` no se produce nunca.** Los cuatro casos que la piden —CA-26,
  CA-30, CA-34, CA-44— fallan en las dos corridas, y arrastran el `limite`.
- **`EXACTA` y `EXHAUSTIVA` se confunden en los dos sentidos**, unos 13 casos.
- Lo segundo es `modo: 40/47`: `M3_FUENTE` y `M2_HISTORICO` se colapsan en
  `M1_ORDINARIO`.
- Todos los demás campos están entre 41 y 43 de 47.

**El modelo no va mal en general. Va mal en un campo.**

## Hallazgo lateral: la medición NO es reproducible del todo

Los totales por campo son casi idénticos entre las dos corridas, pero el
global se movió de 22 a 24. Lo que cambió fue **dónde** caen los errores:
CA-01 (la víctima del timeout) y CA-15 se arreglaron, pero **CA-18 ganó un
fallo de cardinalidad que en la corrida 1 no tenía**. A `temperature=0.1` hay
ruido residual.

**Consecuencia operativa: cualquier comparación futura de esta medida tiene que
contar con un jitter de ±2 en el global**, o se leerán como mejoras cosas que
son azar. Ninguna decisión debe colgar de una diferencia de uno o dos casos.

## Dónde queda la palanca 1 dentro del mapa

| configuración | exactos | de más | hallados | críticas perdidas |
|---|---|---|---|---|
| **cerrada** — lo que corre hoy (ADR-203) | 10/47 | 218 | 57/81 | **10** |
| abierta + petición fija | 0/47 | 487 | 72/81 | 0 |
| abierta + **petición del modelo** | 0/47 | 386 | 74/81 | 0 |
| abierta + petición declarada (techo) | 17/47 | 162 | 78/81 | 0 |

1. El intérprete **mejora sobre la política fija en todos los ejes**: 487→386
   de más, 72→74 hallados. Pero de los 325 elementos de más que separan la
   política fija del techo recupera **101**, un 31%; y de los 17 aciertos
   exactos recupera **cero**.
2. La configuración que corre hoy pierde **10 elementos críticos** y encuentra
   57 de 81. Ninguna configuración abierta pierde críticos y todas encuentran
   entre 72 y 78. A cambio, todas meten bastante más ruido.

**Con la advertencia que ADR-203 ya dejó escrita y que aquí no se salta:** la
diferencia entre la fila cerrada y las abiertas es la distancia entre dos
configuraciones completas, **no el aporte de un interruptor**. El instrumento
todavía no sabe separar `staged_engine_enabled` de `relevance_filter_enabled`.

## Estado en que queda

ADR-164 dice que la palanca 1 **no se da por cerrada hasta que el propietario
la corra**. La ha corrido. El resultado **no alcanza la predicción publicada**,
así que la palanca 1 queda **medida y NO cerrada**. Qué hacer con eso —atacar
la cardinalidad, aceptar el 31%, o dejarla— es decisión del propietario, y no
se toma aquí.

Sigue sin registrar el umbral de D7 punto 6 en `STATUS.md`, que es justo el
número que haría no-arbitraria la lectura de la tabla de arriba: cuánto ruido
se acepta a cambio de dejar de perder críticos.
