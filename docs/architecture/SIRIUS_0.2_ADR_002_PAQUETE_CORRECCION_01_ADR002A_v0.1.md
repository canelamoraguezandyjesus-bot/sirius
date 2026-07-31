# SIRIUS 0.2 — ADR-002 · Paquete de corrección 01 · defectos bloqueantes de `ADR002-A`

**Versión:** 0.1
**Estado:** **PROPUESTO · PREINSCRITO** — registra los defectos **antes** de corregirlos; no aprueba a `ADR002-A` como preparado para benchmark
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Commit de partida:** `a5fa3ff2994bf2b85d89427db0dd08a5871a7928`
**Detectados por:** el usuario, sobre el paquete de trabajo 11
**Ficha afectada:** `artifacts/adr002_cards/ficha_ADR002-A_v1.json` · huella `00571890294bcd18748e2ee600eb43bad1b92f80`
**No autoriza:** ejecutar el benchmark, medir rendimiento, usar el corpus congelado v0.4 para evaluar al candidato, implementar `ADR002-B/C/D`, abrir `EJE-1` o `EJE-2`, elegir ganador, modificar Sirius 0.1 ni fusionar el PR #117.

---

## 0. Estado que este paquete corrige

La infraestructura común y `ADR002-A` existen, **pero `ADR002-A` no está aprobado
como preparado para benchmark**. Tres defectos bloqueantes lo impiden, y los
tres son reales: se han verificado sobre el código antes de escribir este
documento.

Lo que sigue no los minimiza. Dos de ellos afectan a **declaraciones
congeladas de la ficha v1**, y el tercero invalida una prueba que decía
demostrar algo que no demostraba.

## 1. Defecto 1 — la prueba de `E3` no demuestra que `E3` recupere nada

`test_e3_alcanza_parafrasis_por_raiz_compartida` admite que el resultado
proceda de **`E1`, `E2` o `E3`**:

```python
assert origen["dragado-canales"] in (Etapa.E1, Etapa.E2, Etapa.E3)
```

Y el caso elegido **lo alcanza `E2`**, verificado:

```text
variantes("canal") = ('canal', 'canala', 'canalas', 'canales', 'canalo',
                      'canalos', 'canals')
```

`canales` está entre las variantes morfológicas que `E2` genera, de modo que
el item llega a `E2` y nunca hace falta `E3`. **La prueba pasa sin que `E3`
aporte un solo resultado**, y por tanto no acredita la afirmación central de
`ADR002-A`: que satisface `E3` por medios léxico-estructurados.

Es el defecto más grave de los tres, porque no es un error de implementación
sino de **evidencia**: la prueba daba por demostrado lo que no había probado.

**Declaración afectada de la ficha v1:** `senal_tardia.como_satisface_e3` y
`arquitectura.etapas_implementadas.E3` quedan **no demostradas**. No son
falsas por este defecto —`E3` existe en el código—, pero ninguna prueba las
respaldaba.

## 2. Defecto 2 — `E3` puede degenerar en barrido de proyecto

La implementación llamaba:

```python
puerto.por_entidad(contexto.peticion.ambito.proyectos)
```

El puerto interpreta esos valores como `project_id` y ejecuta:

```sql
SELECT id FROM memories  WHERE project_id = ? ORDER BY id LIMIT 512
SELECT id FROM decisions WHERE project_id = ? ORDER BY id LIMIT 512
```

Es decir: **hasta 512 memorias y 512 decisiones por proyecto**, materializadas
y filtradas después en Python. Sobre un proyecto de tamaño realista eso es un
**barrido del proyecto**, no una consulta dirigida.

Dos consecuencias, ambas materiales:

1. **Contradice —o como mínimo deja no demostrada— la declaración congelada**
   `extremo_a_extremo.no_invoca_el_barrido_de_t0 = true` de la ficha v1. El
   barrido que `RF-14` prohíbe y que define a T0 es exactamente «recuperar
   todo el espacio y filtrar después».
2. **Invalida el fundamento del límite por etapa de `E3`**, que la ficha v1
   justifica como «hasta dos consultas acotadas»: una consulta que enumera un
   proyecto entero no es una consulta acotada por su selectividad, sino por un
   tope arbitrario.

Además, **`project_id` se estaba usando como sustituto de `entity_id`**, que
son cosas distintas: el ámbito es una **puerta de seguridad** (`G4`), no un
generador de candidatos.

**Declaraciones afectadas de la ficha v1:** `extremo_a_extremo.no_invoca_el_barrido_de_t0`,
`coste_por_etapa.etapas[E3]` y `arquitectura.materializacion_de_relaciones`.

## 3. Defecto 3 — la regeneración del derivado era parcial

`fixtures.regenerar_derivado` eliminaba triggers y tablas, recreaba las tablas
**a mano** y repoblaba filas, pero **no restauraba los triggers**. Por tanto:

- no demostraba la regeneración **completa** del derivado;
- no demostraba que una modificación posterior del canon volviera a
  sincronizarse, que es justo lo que los triggers garantizan;
- copiaba parcialmente el DDL a una fixture en vez de usar el mecanismo
  canónico.

La prueba pasaba porque comparaba dos consultas de lectura sobre un índice ya
poblado: nunca tocó el canon después de reconstruir.

**Declaraciones afectadas de la ficha v1:** `ciclo_de_indice.reconstruccion_desde_el_canon`,
`ciclo_de_indice.desaparicion_completa` y la puerta previa común
`borrado_y_regeneracion_desde_el_canon`.

## 4. Qué se conserva y qué deja de estar vigente

1. **La ficha `ficha_ADR002-A_v1.json` se conserva intacta**, con su blob y su
   huella. No se reescribe, no se corrige y no se retira del repositorio: es
   historial, y borrarla ocultaría que estos defectos existieron.
2. **Las ejecuciones técnicas hechas bajo v1 se conservan** como historial en
   su commit. No se reinterpretan ni se presentan como si hubieran validado lo
   que no validaron.
3. **`v1` no puede seguir siendo la ficha vigente.** La corrección cambia
   fuentes incluidas en la huella del candidato —el árbol
   `experiments/adr002/candidates`—, y la regla 3 de custodia del acta de
   `TOL-210` es explícita: una sucesora obliga a marcar `SUSTITUIDA` la
   anterior y a **repetir** las ejecuciones hechas bajo ella.
4. Por tanto se emitirá **`ficha_ADR002-A_v2.json`**, con motivo de
   sustitución, y **v1 pasará a `SUSTITUIDA`** por el mecanismo de versionado
   que el contrato ya implementa.

## 5. Lo que la corrección debe demostrar

| Defecto | Criterio de corrección |
|---|---|
| 1 | una prueba que exija **`etapa_de_origen == E3`**, sin admitir `E1` ni `E2`, sobre un caso que `E1` y `E2` **no puedan** alcanzar |
| 2 | `E3` recupera por **consultas dirigidas** —términos y relaciones concretas—, el ámbito actúa solo como filtro de seguridad, y hay **instrumentación** que registra qué SQL se ejecuta y cuántas filas pide cada etapa |
| 3 | la reconstrucción usa el **mecanismo canónico existente**, restaura tablas **y triggers**, y una modificación posterior del canon vuelve a sincronizar el índice |

## 6. Lo que este paquete NO hace

- **No aprueba a `ADR002-A` como preparado para benchmark.** Eso será un acto
  posterior, y solo si la corrección demuestra los tres criterios del §5.
- No ejecuta el benchmark, no mide rendimiento y no usa el corpus congelado
  v0.4 para evaluar al candidato.
- No implementa `ADR002-B`, `ADR002-C` ni `ADR002-D`.
- No abre `EJE-1` ni `EJE-2`, no elige ganador, no modifica Sirius 0.1 y **no
  fusiona el PR #117**.

---

**Siguiente movimiento único:** corregir el prototipo conforme al §5, emitir la
ficha v2 que sustituya a v1, y solo entonces ejecutar las pruebas que
demuestren los tres criterios.
