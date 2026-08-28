# Informe del suelo multiescala v0.2 — `LAB-LINUX` — ADR002-TOL-209

| Campo | Valor |
| --- | --- |
| **Estado** | `PROPUESTO · SUELO MULTIESCALA MEDIDO — NO APRUEBA TOL-209` |
| **Puerta** | `ADR002-TOL-209` · **NO SATISFECHA** |
| **Artefacto** | `artifacts/adr002_tolerances/suelo_medicion_v0.2.json` (blob `1d73fa36…`) |
| **Paquete** | `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_06_TOL209_SUELO_MULTIESCALA_v0.1` |
| **Protocolo** | `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md` (blob `c298a6b8…`) |
| **Commit de preinscripción** | `a23dbcff4a2248f7af07b107bab38f24c6181f2f` |
| **Sustituye** | el **método** de determinación de `B` y `U` del paquete 05 |
| **No sustituye** | la **evidencia** del paquete 05, verificada intacta byte a byte |

---

## 1. Resultado

| Magnitud | Valor | Lectura |
| --- | --- | --- |
| `SM` | **15 811 ns** (0,0158 ms) | nivel del instrumento · guarda de dominancia |
| `U` | **100 000 000 ns** (100 ms) | umbral de conmutación propuesto |
| `B` | **20 000 000 ns** (20 ms) | banda absoluta propuesta · `B = U / 5`, exacta |
| `m` | **1** | continuidad exacta en `M = U` |
| Resultado del punto fijo | `RESUELTO` | — |

Los diecinueve controles bloqueantes pasaron. Cero incidencias. Cinco
procesos independientes (`30767`, `30768`, `30770`, `30772`, `30774`),
10 300 muestras crudas publicadas íntegras en nanosegundos.

---

## 2. La curva `D(s)` medida

`D(s)` es el peor `máx − mín` entre procesos, sobre las dos familias
neutrales y sobre P50 y P95.

| Escala nominal | `D(s)` | `D(s)/s` | ¿`5·D(s) ≤ s`? |
| --- | --- | --- | --- |
| 10 µs | 6 404 ns | 0,640 | no |
| 20 µs | 6 640 ns | 0,332 | no |
| 50 µs | 5 346 ns | **0,106** | sí |
| 100 µs | 56 498 ns | 0,564 | no |
| 200 µs | 46 720 ns | 0,233 | no |
| 500 µs | 330 419 ns | 0,660 | no |
| 1 ms | 274 175 ns | 0,274 | no |
| 2 ms | 964 694 ns | 0,482 | no |
| 5 ms | 1 553 846 ns | 0,310 | no |
| 10 ms | 2 388 363 ns | 0,238 | no |
| 20 ms | 5 041 895 ns | 0,252 | no |
| 50 ms | 18 425 838 ns | 0,368 | no |
| **100 ms** | **15 982 352 ns** | **0,159** | **sí** |

El escalón de 50 µs cumple la condición de forma **aislada**: la rompe la
escala inmediatamente superior. La cláusula de monotonía del método —la
condición debe sostenerse en `U` y en **todas** las escalas mayores— la
descartó, que es exactamente para lo que se preinscribió. `U` quedó por
tanto en 100 ms, el único escalón desde el cual la condición se sostiene.

`banda_cubre_el_suelo` pasó: el peor suelo por debajo de `U` es 18 425 838 ns
(escalón de 50 ms) frente a una banda de 20 000 000 ns. **El margen es del
7,9 %.** Un escalón de 50 ms algo más ruidoso habría bloqueado la corrida.

---

## 3. Qué dice realmente la medición: es la cola, no el centro

La descomposición por familia y percentil es la parte más informativa del
artefacto, y contradice la lectura ingenua de la tabla anterior.

**El P50 es estable a todas las escalas.** Su dispersión relativa entre
procesos no llega al 7 % en ninguna escala ni familia:

| Familia | `D/s` del P50, mínimo → máximo sobre las trece escalas |
| --- | --- |
| `cpu` | 0,003 → 0,026 |
| `canon` | 0,043 → 0,067 |

Si el umbral se hubiese resuelto solo con el P50, `U` habría caído en el
**primer** escalón de la escalera. No se hizo, y no se hace ahora: el §6.1
del protocolo evalúa P50 **y** P95, y TOL-107 congela su objetivo sobre
ambos.

**Todo el suelo está en el P95**, es decir en la cola:

| Familia | `D/s` del P95, mínimo → máximo |
| --- | --- |
| `cpu` | 0,048 → 0,661 |
| `canon` | 0,067 → 0,640 |

El mecanismo es transparente: una ventana cronometrada larga tiene más
probabilidad de sufrir una expropiación del planificador, y basta que **un**
proceso de los cinco la sufra para que `máx − mín` del P95 se dispare. La
máquina tiene 4 CPU y la propia corrida la carga: la media de carga sube de
0,43 en el primer proceso a 0,84 en el quinto.

Esto se ve con nitidez en el escalón de 50 ms, donde las dos familias miden
la **misma** escala nominal y difieren en un factor 5,5:

| Escalón de 50 ms | `D(s)` del P95 | `D/s` |
| --- | --- | --- |
| `cpu` | 18 425 838 ns | 0,369 |
| `canon` | 3 339 757 ns | 0,067 |

La regla del peor caso entre familias —preinscrita, y conservadora por
diseño— tomó 0,369 y descartó ese escalón. El escalón de 100 ms, con
`cpu` en 0,160 y `canon` en 0,100, lo sostuvo.

---

## 4. ¿Resuelve la contradicción que motivó el sucesor?

Sí. Ésta era la razón de existir del paquete 06.

| Magnitud de la línea base | mín P95 | Régimen con `U = 48,79 µs` (paquete 05) | Régimen con `U = 100 ms` (sucesor) | Lo que dice el Registro |
| --- | --- | --- | --- | --- |
| `cero_resultados.solo_indice_fts5` | 0,188 ms | relativo | **absoluto** | *«a esa escala la comparación debe hacerse en valor absoluto»* |
| `un_resultado_exacto.solo_indice_fts5` | 0,217 ms | relativo | **absoluto** | ídem |
| `muchos_candidatos.solo_indice_fts5` | 0,736 ms | relativo | **absoluto** | ídem |
| `cero_resultados.recuperacion_completa_rank` | 125,81 ms | relativo | relativo | objetivo relativo ≤ 20 % |
| `un_resultado_exacto.recuperacion_completa_rank` | 127,78 ms | relativo | relativo | ídem |
| `muchos_candidatos.recuperacion_completa_rank` | 127,50 ms | relativo | relativo | ídem |

Las tres magnitudes submilisegundo pasan al régimen **absoluto**, que es
literalmente lo que la fila `ADR002-TOL-107` del Registro v0.4 declara para
la escala de 0,14–1,0 ms. Las tres magnitudes de `rank()` permanecen en
régimen **relativo**, donde el objetivo del ≤ 20 % está anclado. Las seis
resultan `VALIDA` con los valores propuestos.

Esta clasificación es **diagnóstica**: se calcula con el umbral ya resuelto
y no participó en resolverlo. Ninguna sonda normativa usó FTS5, `rank()`,
BM25, *embeddings* ni operación de candidato alguno.

---

## 5. Tres tensiones que este resultado deja abiertas

Se declaran porque son reales, no porque el método haya fallado. Ninguna se
corrige aquí: hacerlo sería ajustar el criterio después de ver el resultado.

### 5.1 `U` cayó en el último escalón de la escalera

La condición de selección exige que se sostenga en `U` **y en todas las
escalas mayores**. En el último escalón esa segunda mitad no impone nada,
porque no hay escalas mayores. El `U = 100 ms` publicado descansa por tanto
sobre la estimación de un solo escalón, sin el respaldo de monotonía que sí
respalda a cualquier `U` interior.

La escalera no llega lo bastante arriba para comprobar si `D(s)/s` se
mantiene por debajo de 0,20 por encima de 100 ms. Con la evidencia
disponible **no se puede afirmar** que 100 ms sea el punto fijo verdadero;
solo que es el menor escalón **medido** que sostiene la condición.

### 5.2 El estimador de la cola es ruidoso con cinco procesos

`máx − mín` del P95 sobre cinco observaciones tiene varianza alta: lo fija
el peor de cinco procesos, y basta una expropiación para moverlo. La
diferencia de 5,5× entre `cpu` y `canon` en el mismo escalón de 50 ms
(§3) no es una propiedad física de la escala: es la firma de ese ruido.

Cinco sesiones es el mínimo que el §3.3 del protocolo exige, y es la misma
base sobre la que se produjo la evidencia del paquete 05. Aumentarlo habría
cambiado dos cosas a la vez —el método y la potencia estadística— y habría
hecho imposible atribuir la diferencia de resultado a la corrección del
método. Se deja declarado para quien decida si conviene remedir con más
sesiones.

### 5.3 `B = 20 ms` es muy permisiva en las magnitudes pequeñas

Es consecuencia necesaria de dos cosas que **no** se eligen en este paquete:
TOL-107 congela **una sola** banda absoluta, y la continuidad en `M = U` con
`m = 1` obliga a `B = 0,20 · U`. Con `U = 100 ms`, eso son 20 ms.

En la práctica significa que, para una operación de 0,2 ms en régimen
absoluto, el criterio de TOL-107 es prácticamente no vinculante. Es el fallo
**opuesto** al del paquete 05, que con `B = 9,8 µs` era inalcanzable a esa
escala.

Esto no es un defecto del punto fijo: es la tensión entre *«una banda
absoluta congelada»* y *«un suelo que crece con la magnitud»*. Resolverla
exige una de estas dos decisiones, que **no corresponden a este paquete**:

1. aceptar que el régimen absoluto sea permisivo por debajo de `U`, apoyado
   en que la puerta de rendimiento real es TOL-101/TOL-104 y no TOL-107; o
2. modificar TOL-107 para admitir una banda **dependiente de la magnitud**
   —por ejemplo `máx(m·B, D(M))` interpolada sobre la curva publicada—, lo
   que exigiría reabrir una fila del Registro.

La curva `D(s)` completa se publica en el artefacto precisamente para que
esa decisión pueda tomarse con evidencia.

---

## 6. Controles internos

Los diecinueve controles bloqueantes preinscritos pasaron. Todos se
recomputaron desde los datos crudos; ningún *flag* declarado por un proceso
se aceptó como fuente única.

| Control | Resultado |
| --- | --- |
| `procesos_independientes` · `pids_distintos` | 5 procesos, PIDs distintos |
| `escalera_completa` | 26 combinaciones `(familia, escala)` en cada proceso |
| `unidades_identicas` | misma cantidad de trabajo en los cinco procesos |
| `calibracion_en_banda` | los 130 P50 dentro de `[s/2, 2s]` |
| `carga_registrada` · `boot_id_estable` · `captura_ambiental_presente` | sí |
| `estabilidad_intraproceso` | sin deriva ni *throttling* |
| `progresion_por_escala` | cumplida donde es exigible |
| `banda_cubre_el_suelo` | sí, con un 7,9 % de margen |
| `vectores_crudos_completos` · `sin_muestras_negativas` | 10 300 muestras íntegras |
| `sin_filtrado` · `warmup_separado` · `sin_redondeo_previo` | sí |
| `sondas_neutrales` | nombres y SQL verificados |
| `evidencia_anterior_intacta` | blobs del paquete 05 sin cambio |
| `custodia_verificada` | reverificada **después** de medir |

### 6.1 Calibración

| Familia | Cantidad de referencia | Coste medido | Unidades en 10 µs → 100 ms |
| --- | --- | --- | --- |
| `cpu` | 10 000 vueltas | 345 052 ns | 290 → 2 898 114 |
| `canon` | 10 consultas por PK | 52 491 ns | 2 → 19 051 |

La calibración la hizo el proceso padre **una sola vez** y se impuso
idéntica a los cinco hijos, de modo que las cinco ejecuciones resuelven
exactamente el mismo trabajo. Sin eso no serían ejecuciones equivalentes y
TOL-107 no tendría sobre qué operar.

Las dos escalas más bajas de `canon` usan 2 y 4 unidades: por debajo de 10
unidades la cuantización del entero domina y la comprobación de progresión
queda **no exigible**, como el paquete preinscribió. Se publican igualmente.

---

## 7. Custodia

| Elemento | Valor |
| --- | --- |
| Commit de preinscripción | `a23dbcff4a2248f7af07b107bab38f24c6181f2f` |
| `HEAD` durante la corrida | `a23dbcff4a2248f7af07b107bab38f24c6181f2f` |
| Árbol de trabajo | limpio antes y después |
| Custodia reverificada tras medir | sí, antes de publicar |

Blobs preinscritos, verificados contra el árbol **y** contra lo que el
commit registra (`git rev-parse <sha>:<ruta>`):

| Blob | Fichero |
| --- | --- |
| `c0326b25…` | `docs/architecture/…PAQUETE_TRABAJO_06_TOL209_SUELO_MULTIESCALA_v0.1.md` |
| `07408093…` | `experiments/adr002/tolerances/floor_scale_probes.py` |
| `aa6e6492…` | `experiments/adr002/tolerances/floor_scale_protocol.py` |
| `0ffc6786…` | `experiments/adr002/tolerances/run_floor_scale.py` |
| `c410cee6…` | `experiments/adr002/tolerances/schema_floor_scale_v0_1.py` |
| `2fb29117…` | `experiments/adr002/tolerances/test_adr002_floor_scale.py` |

Módulo heredado: `corpus.py` = `90c5118e…`. Protocolo aprobado:
`c298a6b8…`. Los siete blobs del corpus congelado, intactos.

**Evidencia del paquete 05, verificada intacta:**

| Blob | Fichero |
| --- | --- |
| `899ecee8…` | `artifacts/adr002_tolerances/suelo_medicion_v0.1.json` |
| `e2b07549…` | `artifacts/adr002_tolerances/INFORME_SUELO_MEDICION_v0.1_PROPUESTO.md` |

No se ha modificado, retirado ni reescrito ni un byte de esa evidencia. El
sucesor corrige el **método**; la medición anterior sigue siendo una
observación válida de su propio escalón.

---

## 8. Entorno

| Campo | Valor |
| --- | --- |
| Sistema | Ubuntu 24.04.4 LTS · kernel 6.18.5 |
| CPU | 4 × Intel(R) Xeon(R) @ 2,80 GHz |
| `boot_id` | `0b593221-eda7-4a3e-abb4-4e6af8927881` (estable inicio→fin) |
| Carga (1 min) por proceso | 0,43 · 0,56 · 0,66 · 0,73 · 0,79 |
| Duración total | ≈ 77 s |

La carga sube de forma monótona a lo largo de la corrida: la propia
medición carga la máquina. Los cinco procesos son secuenciales, de modo que
ninguno compite con otro proceso de la corrida, pero el estado de la caché
y la frecuencia sí evolucionan. El diagnóstico de referencia intraproceso
no detectó deriva ni *throttling* en ninguno de los cinco.

---

## 9. Reproducción y verificación independiente

```bash
git checkout a23dbcff4a2248f7af07b107bab38f24c6181f2f
uv run python -m experiments.adr002.tolerances.run_floor_scale \
    --execute \
    --preinscription-commit a23dbcff4a2248f7af07b107bab38f24c6181f2f \
    --output <ruta_nueva>.json
```

Los valores **no** se reproducirán idénticos: son mediciones. Lo que sí es
reproducible es todo lo derivado: partiendo de los `muestras_ns` publicados,
`SM`, `D(s)`, `U`, `B`, los percentiles, las unidades, la tabla de
progresión y el régimen de cada magnitud se recomputan exactamente, en
aritmética entera y sin coma flotante.

Esa recomputación se hizo **desde cero**, sin usar el código del paquete, y
coincidió en todo: 0 entradas con percentiles divergentes sobre 130 + 15,
`U` y `B` idénticas, `SM` idéntica, `D(s)` idéntica en las trece escalas.

El validador `schema_floor_scale_v0_1` rechaza cualquier artefacto cuya
derivación no salga de sus propios vectores. Se sometió a un barrido
adversarial sobre las 327 rutas del documento —cada campo borrado y
sustituido, en el artefacto resuelto y en uno `NO_EVALUABLE`—: de 186
mutaciones inicialmente indetectadas quedaron 51, todas ellas prosa libre,
muestras de calibración distintas de la mediana, o carga ambiental. Están
declaradas en la limitación 11 del paquete.

---

## 10. Limitaciones

Se mantienen las once del paquete 06. Estas cuatro **se materializaron** en
esta corrida y conviene leerlas con los números delante:

1. **Escalado por cantidad de trabajo** (limitación 1). El sesgo declarado
   —subestimar `D` en escalas altas— empujaría `U` hacia abajo. `U` acabó en
   el escalón más alto, así que el sesgo, de existir, no explica el
   resultado: lo atenúa.
2. **Resolución de la escalera** (limitación 2) y **`U` en el último
   escalón** (§5.1): una escalera más densa o más alta solo podría bajar
   `U`, nunca subirlo.
3. **Cinco procesos** (limitación 3): materializada de lleno; véase §5.2.
4. **`n = 30` por encima de 1 ms** (limitación 4): en las siete escalas
   caras el P99 coincide con el máximo observado. Acota la cola, no la
   caracteriza. Cada entrada publica su `resolucion_percentil`.

---

## 11. Qué NO hace este informe

- **No aprueba `ADR002-TOL-209`.** La puerta sigue **NO SATISFECHA** hasta
  el acta de aprobación correspondiente.
- **No fija el límite duro de TOL-107**: eso se congela con el entorno de
  ejecución.
- **No sustituye ni retira la evidencia del paquete 05.**
- **No autoriza** avanzar a T0, implementar o ejecutar candidatos, ejecutar
  el *benchmark* ni fusionar el PR #117.
- **No resuelve** la tensión del §5.3: esa es una decisión de producto sobre
  TOL-107, y se traslada tal cual a quien aprueba.

`SM`, `U` y `B` son **propuestos**. Adquieren carácter normativo únicamente
con el acta que apruebe la fila correspondiente del Registro.
