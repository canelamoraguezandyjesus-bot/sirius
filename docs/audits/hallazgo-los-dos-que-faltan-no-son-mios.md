# Los dos que la mejor búsqueda no trae: ninguno es arreglable desde aquí — 20-09-2026

Responde a `arranque-los-dos-que-la-mejor-busqueda-no-trae.md`, escrita antes de
mirar. Determinista, sin Ollama.

## `CA-29`: el banco espera un elemento que él mismo declara no vigente

`B04-CA-29` «¿Cuál es el plazo legal de entrega?» espera `MEM-020` y **su
conjunto de candidatas está vacío**. No es que la búsqueda no lo encuentre: es
que **no hay nada que encontrar**.

`MEM-020` declara `confirmacion: "CANDIDATA"`. Y el cargador del banco
(`test_pa_0_2_rec_01_banco_evidencia.py:333`, `_vigente`) mete en Sirius un
elemento **solo si sus tres estados lo dicen a la vez**:

```python
item["confirmacion"] == "CONFIRMADA"
and item["validez"] == "VIGENTE"
and item["disponibilidad"] == "DISPONIBLE"
```

`MEM-020` **nunca llega a la base de datos**. Comprobado: entra en **0 de 47**
casos en las tres configuraciones, y el otro elemento `CANDIDATA` del corpus
(`MEM-007`) también entra en 0 — y ése no se espera en ningún caso.

> **`B04-CA-29` es inalcanzable por construcción.** Ningún filtro, ningún
> modelo, ninguna configuración puede acertarlo, porque el único elemento que
> espera no existe dentro de Sirius.

Y es una **contradicción dentro del propio banco**: la adjudicación espera un
elemento que los campos de estado del mismo banco declaran no vigente. Hay tres
salidas y **las tres son del propietario**:

1. el `resultado_esperado` del caso está mal;
2. la `confirmacion` de `MEM-020` está mal;
3. la regla «una candidata no entra» está mal —y entonces el caso está probando
   precisamente eso, que Sirius sepa responder con lo no confirmado marcándolo.

**No toco ninguna.** El corpus, `resultado_esperado` y las adjudicaciones están
fuera de mi alcance por regla dura, y con razón: cualquiera de los tres cambios
mueve la cifra sin que el sistema mejore.

## `CA-30`: la parada por suficiencia, alimentada por una adjudicación

`B04-CA-30` «Resume mi preferencia de redacción, el presupuesto vigente y la
condición de ahorro en escalas» espera tres elementos y pierde `MEM-001`.

`MEM-001` **no tiene ningún problema**: está `CONFIRMADA`/`VIGENTE`/`DISPONIBLE`
y entra sin dificultad en `CA-01`, `CA-02`, `CA-26`, `CA-31`, `CA-34`, `CA-38`
y `CA-44`. Entra en todos los demás casos `ACOTADA`. Solo falta en éste.

Lo que tiene de distinto `CA-30` es su `limite`:

| caso | `limite.n` | ¿entra `MEM-001`? | candidatas |
|---|---|---|---|
| `CA-26` | 10 | sí | 13 |
| `CA-34` | 10 | sí | 22 |
| `CA-38` | 10 | sí | 13 |
| `CA-44` | 5 | sí | 13 |
| **`CA-30`** | **3** | **no** | **4** |

Con `objetivos = 3`, la expansión **para en cuanto tiene bastante**
(`_suficiente`/`evaluar_suficiencia`, `sirius.domain.staged_engine`) y no llega
a la etapa que trae lo `GLOBAL`. Con cuatro candidatas ya cumple la cuota.

**Y la petición declarada lo empeora**: con la petición **fija** este caso
recupera 8 candidatas **e incluye `MEM-001`**; con la declarada recupera 4 y lo
pierde. Es el único sitio de toda la auditoría donde `--peticion` va hacia atrás.

Esa `n = 3` no la produce Sirius: **la declara el banco** en `peticion_p2.limite`.
Es adjudicación, igual que la `n` de los casos de cuota (entrada 117). Remite
directamente a la **deuda 38**: sin una política de `limite.n` que no salga del
oráculo, estos casos no son medibles de forma honesta.

## Veredicto contra el criterio de parada

El criterio escrito antes decía: *si la causa es una guarda declarada haciendo su
trabajo, no es defecto; si es un fallo de recuperación de algo elegible, es
defecto y hay encargo; si es el cupo, remite a la deuda 38.*

- `CA-29`: **guarda declarada haciendo su trabajo** (el cargador), sobre un
  elemento que el banco declara no vigente y espera igualmente. **No es defecto
  de Sirius.**
- `CA-30`: **parada por suficiencia alimentada por una adjudicación**. **Deuda 38.**

> **Ninguno de los dos es arreglable desde aquí, y ninguno es un defecto de
> Sirius.** La línea de la búsqueda queda **cerrada**.

## Contraste con las predicciones

| predicción (escrita antes de mirar) | resultado |
|---|---|
| `CA-29` es una guarda declarada (70%) | **ACERTADA** — el cargador `_vigente`, no una guarda de recuperación |
| `CA-30` no es guarda: es ámbito o multiobjetivo (60%) | **ACERTADA A MEDIAS** — no es guarda ni es ámbito; es la parada por suficiencia, que sí es consecuencia de pedir tres cosas |
| al menos uno es una guarda, así que **como mucho uno** es atacable (75%) | **ACERTADA, y de más**: no es atacable **ninguno** |

## Lo que esto significa para el trabajo que queda

La nota de arranque lo anticipó y conviene decirlo sin adornos:

> *«Sería la primera vez en esta auditoría que no queda nada que yo pueda hacer
> solo, y conviene saberlo antes que tarde.»*

**Es esa vez.** El mapa entero, al cierre de hoy:

| línea | estado |
|---|---|
| siembra | cerrada (entrada 118) |
| ranking del motor | cerrada, negativo medido (entrada 120) |
| ampliación por criticidad | cerrada, negativo medido (entrada 135) |
| **búsqueda** | **cerrada — los dos que faltan no son defectos de Sirius** |
| intérprete (`cardinalidad`) | **#653, en `ready-for-merge`, esperando su gesto** |
| intérprete (`modo`, `corte`) | encargo **preparado y sin lanzar** |
| filtro de relevancia | 4 descartes + 2 excesos; **exige Ollama, o sea su máquina** |
| candado / métrica / `limite.n` / umbral D7 / `CA-29` | **deudas 38, 39, 42, 43 y ésta: suyas** |

Lo único que puedo hacer sin él es lanzar el segundo encargo, y eso está
bloqueado hasta que #653 sea terminal.
