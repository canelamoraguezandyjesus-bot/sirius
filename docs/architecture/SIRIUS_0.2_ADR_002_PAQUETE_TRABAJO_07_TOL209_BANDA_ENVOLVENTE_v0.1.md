# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 07 · Preinscripción de la banda envolvente

| Campo | Valor |
| --- | --- |
| **Estado** | `PROPUESTO · PREINSCRIPCIÓN BANDA ENVOLVENTE` |
| **Puerta** | `ADR002-TOL-209` · **NO SATISFECHA** |
| **Acto de gobierno que lo autoriza** | `SIRIUS_0.2_ADR_002_TOL_107_BANDA_DEPENDIENTE_APROBACION_v1.0.md` |
| **Sustituye** | el **método** de determinación de la banda y del umbral de los paquetes 05 y 06 |
| **No sustituye** | la **evidencia** v0.1 y v0.2, conservada íntegra y verificada byte a byte |
| **Protocolo aplicable** | `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md` (blob `c298a6b8…`) |
| **Registro aplicable** | `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md`, fila `ADR002-TOL-107` **v0.5** (blob `b499b573…`) |
| **Entorno** | `LAB-LINUX` |
| **No autoriza** | aprobar TOL-209, fijar el límite duro de TOL-107, avanzar a T0, implementar o ejecutar candidatos, ejecutar el *benchmark*, fusionar el PR #117 |

---

## 0. Objeto

Preinscribir, **antes de medir**, el método con el que se determinan la
**banda `B(M)` dependiente de la magnitud** y el **umbral de conmutación `U`**
de `ADR002-TOL-107`, conforme al acto de gobierno que lo autoriza.

### 0.1 Por qué dos commits

1. **Commit de preinscripción** — acto de gobierno, actualización de la fila
   del Registro, este documento y los módulos que implementan el método,
   congelados **sin ninguna observación**.
2. **Commit de evidencia** — el artefacto y el informe producidos
   **exactamente** por el código del commit anterior, cuya cadena de custodia
   se verifica en ejecución contra los blobs que ese commit registra.

---

## 1. Qué corrige este paquete

Los paquetes 05 y 06 midieron correctamente y publicaron evidencia válida. Lo
que falló fue la **forma** de la banda:

| Paquete | `U` | `B` | Defecto |
| --- | ---: | ---: | --- |
| 05 | 48,79 µs | 9,76 µs | banda inalcanzable por debajo del milisegundo; contradice la propia fila TOL-107 |
| 06 | 100 ms | 20 ms | banda casi vacía por debajo del milisegundo; además `U` cayó en el último escalón medido |

La causa la demostró la evidencia del paquete 06: el suelo del entorno
**crece con la magnitud**. Una banda global sólo puede ser correcta en un
punto de esa curva. El paquete 07 sustituye el número por una función.

---

## 2. El método

### 2.1 Definiciones vinculantes

Sobre la escalera nominal preinscrita `s_1 < … < s_n`:

```
D(s_i)  = peor (máx − mín) entre procesos, sobre familias y P50/P95
E(s_i)  = máx( D(s_1), …, D(s_i) )                 envolvente monótona
B(M)    = E(s_j)   con   j = mín{ i : s_i ≥ M }    escalón superior
```

### 2.2 Por qué la envolvente y no la curva

`D` medida **no es monótona**. Con los números del paquete 06,
`D(100 µs) = 56 498 ns` pero `D(200 µs) = 46 720 ns`. Leer la banda
directamente de `D` daría a una operación de 200 µs una banda **más estrecha**
que a una de 100 µs: penalizaría al candidato más rápido por serlo, que es
exactamente el riesgo **M-03** que los dos regímenes cerraron.

`E` es no decreciente por construcción y `B` hereda esa propiedad. Es un
**control bloqueante**, no una expectativa: `banda_no_decreciente` la
comprueba sobre cada escalón y sobre el punto inmediatamente posterior a cada
escalón, que son los únicos puntos donde `B` puede cambiar de valor.

### 2.3 Dirección conservadora entre escalones

Para una magnitud entre dos escalones se usa el **superior**. El inferior
daría una banda más estrecha que el suelo demostrado en el tramo.

### 2.4 El umbral como cruce exacto

```
B(M) = 0,20 · M     ⟺     M = 5 · E(s_j)
```

Sobre el escalón `k` seleccionado, **`U := 5 · E(s_k)`**, y por tanto

```
m · B(U) = E(s_k) = U / 5 = 0,20 · U        con m = 1
```

**Demostración de que `s_(k−1) < U ≤ s_k`** (con `s_0 := 0`):

- `U = 5·E(s_k) ≤ s_k` es la propia condición de selección;
- si fuese `U ≤ s_(k−1)`, entonces, como `E` no decrece,
  `5·E(s_(k−1)) ≤ 5·E(s_k) = U ≤ s_(k−1)`, luego el escalón `k−1` también
  sería sostenible y todos los superiores también, contradiciendo que `k` es
  el mínimo.

De ahí que `B(U) = E(s_k)` y que la continuidad sea **exacta**. `m = 1` deja
de ser una decisión y pasa a ser la única solución de igualar los dos
regímenes en la frontera. La demostración se comprueba en ejecución:
`resolver_cruce` lanza si el intervalo no se cumple, y
`continuidad_exacta_en_u` es un control bloqueante.

### 2.5 `U` no es un escalón, y eso no es interpolar

`U` es el valor exacto del cruce: cinco veces una dispersión **observada**. No
se asume igualdad con ningún escalón medido. Es una consecuencia aritmética
en enteros, no una observación inventada, y por tanto no cae bajo la
prohibición de interpolar percentiles del §4.1 del protocolo, que impide
publicar un valor que nunca ocurrió.

Frente al paquete 06 esto es una mejora medible: allí `U` estaba cuantizado a
la resolución de la escalera; aquí sólo lo está el **escalón** en el que cae
el cruce.

### 2.6 Selección del escalón y monotonía

`k` es el **menor** índice con `5·E(s_k) ≤ s_k` **y** con la misma condición
en todos los escalones superiores. Un cruce aislado en un escalón bajo no
puede adelantar el umbral: la evidencia del paquete 06 mostró justamente eso
en el escalón de 50 µs.

### 2.7 Régimen relativo

Sin cambios: por encima de `U`, `(máx − mín)/mín ≤ 1/5` en P50 y P95.

### 2.8 `NO_EVALUABLE`

Sin publicar `U` ni banda alguna, si:

1. ningún escalón sostiene la condición de forma sostenida;
2. el cruce cae en el tramo del **último escalón medido**;
3. no queda al menos `CONFIRMACIONES_MINIMAS = 1` escala medida por encima de
   `U` que confirme el régimen relativo.

**Nota de honestidad sobre (3).** Con `CONFIRMACIONES_MINIMAS = 1`, la
condición (3) está **implicada** por la (2): todos los escalones por encima
del elegido son sostenibles por construcción y todos superan a `U`, de modo
que el recuento vale siempre `n − 1 − k`. Se implementan las dos por separado,
se publica el recuento y se comprueba la identidad en las pruebas, para que un
endurecimiento futuro de la constante tenga sobre qué morder. No se presenta
como una salvaguarda independiente porque hoy no lo es.

---

## 3. La escalera y las sesiones

### 3.1 Escalera nominal: dieciséis escalones

```
10 · 20 · 50 · 100 · 200 · 500 µs
1 · 2 · 5 · 10 · 20 · 50 · 100 · 200 · 500 ms
1 s
```

Los trece del paquete 06 más **200 ms, 500 ms y 1 s**. La ampliación no es
cosmética: con la escalera anterior el cruce cayó en el último escalón, donde
la cláusula «y todas las escalas mayores» no impone nada. Ahora hay tramo
por encima donde confirmar —o desmentir— el régimen relativo.

Progresión 1-2-5, cinco órdenes de magnitud. Todo escalón es múltiplo de 5.

### 3.2 Once sesiones independientes

El §3.3 del protocolo exige **cinco como mínimo**. Con banda global bastaban:
el ruido afectaba a un solo punto. Con banda dependiente de la magnitud,
**cada escalón ruidoso es una tolerancia ruidosa**, y `máx − mín` sobre cinco
observaciones lo fija un único proceso desafortunado —el paquete 06 lo
documentó: 5,5× de diferencia entre las dos familias en el mismo escalón de
50 ms—.

Once, y no diez o doce, porque es **impar**: el P50 entre procesos, publicado
como diagnóstico, cae así en una observación real.

### 3.3 Coste declarado

Con `n = 100` hasta 1 ms y `n = 30` por encima, más cinco de *warm-up* por
escalón, cada proceso resuelve unos 133 s de trabajo cronometrado. Once
procesos secuenciales son del orden de **25 minutos**. Se declara porque es
un cambio de escala frente a los 77 s del paquete 06 y afecta a la carga del
sistema durante la corrida.

---

## 4. Las sondas se heredan congeladas

**No se define ninguna sonda nueva.** El paquete 07 importa
`floor_scale_probes.py` del paquete 06 con su blob fijado
(`07408093…`), junto con `floor_scale_protocol.py` (`aa6e6492…`) y
`corpus.py` (`90c5118e…`).

Es deliberado: si las sondas cambiasen a la vez que el método, ninguna
diferencia de resultado sería atribuible a la corrección. Las dos familias
neutrales siguen siendo `cpu` —aritmética entera pura— y `canon` —consultas
por clave primaria sobre `memory_revisions`—, y ninguna nombra ni usa FTS5,
`rank()`, BM25, *embeddings* ni operación de candidato alguno. Una prueba
recorre el **AST** del módulo heredado para verificarlo sobre las expresiones
que se usan como SQL.

`SM` —peor P95 de las tres sondas de suelo unitario— conserva su papel de
guarda de dominancia del instrumento y **no** determina la banda.

---

## 5. Calibración

Idéntica al paquete 06 y por la misma razón: la hace el proceso **padre** una
sola vez y se impone idéntica a los once hijos, porque TOL-107 mide la
variación entre ejecuciones **equivalentes**.

```
unidades(s) = máx(1, redondeo( s · unidades_referencia / coste_referencia ))
```

en enteros, con `coste_referencia` el P50 de 21 observaciones. La magnitud
observada de cada escalón debe caer en **`[s/2, 2s]`**; fuera de banda la
corrida **falla cerrado**. La comprobación de progresión entre escalones
consecutivos usa tolerancia **1/3** y sólo se exige donde ambos escalones
emplean al menos 10 unidades de trabajo.

---

## 6. Constantes operativas preinscritas

| Constante | Valor | Fundamento |
| --- | --- | --- |
| `PROCESOS_MINIMOS` | **11** | §3.2 de este documento; el protocolo exige 5 como mínimo |
| `ESCALERA_NS` | 16 escalones, 10 µs – 1 s | §3.1 |
| `N_COSTE_BAJO` / `N_COSTE_ALTO` | 100 / 30 | §3.2 y §3.1 del protocolo |
| `UMBRAL_COSTE_BAJO_NS` | 1 000 000 | frontera entre ambos regímenes de `n` |
| `WARMUP_ESCALA` | 5 | descartado íntegro, por `(familia, escala)` |
| `N_UNITARIA` / `WARMUP_UNITARIA` | 100 / 5 | sondas de suelo unitario |
| `RONDAS_ROUND_ROBIN` | 5 | §5.2 aplicado a sondas; divide a 100 y a 30 |
| `SEMILLA` | 20260726 | §5.3 |
| `MUESTRAS_CALIBRACION` | 21 | impar, P50 en muestra real |
| `TOLERANCIA_PROGRESION` | 1/3 | con 1/2 el caso «no crece» pasaría en la frontera |
| `UNIDADES_MINIMAS_PROGRESION` | 10 | por debajo domina la cuantización |
| `TOLERANCIA_DERIVA` | 3/10 | criterio de *throttling*, conservado |
| `OBJETIVO_RELATIVO` | 1/5 | **congelado en el Registro**; no se elige aquí |
| `MARGEN_M` | 1 | **derivado**, no elegido: única solución de la continuidad |
| `CONFIRMACIONES_MINIMAS` | 1 | §2.8, con su nota de honestidad |

---

## 7. Orden de evaluación

1. **Guarda de dominancia.** Si `mín_s P95 < SM`, la magnitud es
   `NO_EVALUABLE` y no publica régimen.
2. **Régimen por percentil.** `RELATIVO` si `mín_s p(s) ≥ U`; `ABSOLUTO` en
   caso contrario.
3. **Criterio.** `RELATIVO`: `(máx − mín)/mín ≤ 1/5`. `ABSOLUTO`:
   `(máx − mín) ≤ m · B(mín_s p(s))`, con la banda **evaluada en la magnitud**.

El invariante `mín_s P95 ≥ mín_s P50` sigue siendo demostrable y sigue dejando
sólo tres combinaciones posibles; «P50 relativo · P95 absoluto» sigue siendo
imposible y se denuncia.

La banda sólo se necesita por debajo de `U`, y `U ≤ s_k ≤ s_n`, de modo que
`B(M)` siempre está definida donde se usa. Por encima del último escalón la
banda no existe **y no hace falta**: esa magnitud vive en régimen relativo.

---

## 8. Controles internos bloqueantes

Veintitrés, todos **recomputados desde los datos crudos**. Fallan **cerrado**.

| Control | Qué recomputa |
| --- | --- |
| `procesos_independientes` · `pids_distintos` | once resultados, PIDs enteros positivos sin repetir |
| `escalera_completa` | las 32 combinaciones `(familia, escala)` en cada proceso |
| `unidades_identicas` | plan de cada proceso y unidades de cada entrada contra el plan del padre |
| `calibracion_en_banda` | P50 de cada `(familia, escala, proceso)` en `[s/2, 2s]` |
| `carga_registrada` · `boot_id_estable` · `captura_ambiental_presente` | entorno |
| `estabilidad_intraproceso` | trabajo de referencia sin deriva monótona excesiva |
| `progresion_por_escala` | progresión exigible entre escalones consecutivos |
| **`envolvente_monotona`** | `E` no decrece |
| **`envolvente_cubre_el_suelo`** | `E(s_i) ≥ D(s_i)` en todo escalón |
| **`banda_no_decreciente`** | `B` no se estrecha al crecer la magnitud (cierra M-03) |
| **`continuidad_exacta_en_u`** | `m·B(U) = 0,20·U` sin resto |
| `vectores_crudos_completos` · `sin_muestras_negativas` | longitudes y signos |
| `sin_filtrado` · `warmup_separado` · `sin_redondeo_previo` | integridad de los vectores |
| `sondas_neutrales` | nombres de familias y sondas, y SQL heredado |
| **`evidencias_anteriores_intactas`** | los **cuatro** blobs de v0.1 y v0.2 |
| **`registro_actualizado_intacto`** | Registro v0.5, protocolo y línea base |
| `custodia_verificada` | cadena completa, **reverificada tras medir** |

### 8.1 `NO_EVALUABLE` y controles

`continuidad_exacta_en_u` presupone un umbral resuelto. Si el cruce no
existe, ese control **no puede** satisfacerse y no debe bloquear un
`NO_EVALUABLE` legítimo. El validador lo impone en ambas direcciones: sin `U`
publicado, es el único que puede fallar **y tiene que fallar**; con `U`
publicado, todos deben estar en `True`.

---

## 9. Limitaciones conocidas

1. **La banda puede ser más estricta que el 20 % en algún escalón bajo `U`.**
   Ocurre en escalones que sostienen la condición de forma aislada sin que la
   sostengan los superiores: allí `E(s_j) < 0,20·s_j`. No es inalcanzable —la
   banda cubre el suelo medido por construcción— pero es una **asimetría
   real**: una operación de esa escala recibe un criterio más duro que el
   objetivo relativo. Se publica escalón a escalón en el diagnóstico
   `holgura_de_banda` en lugar de disimularse. El remedio, si se decidiera
   aplicarlo, sería definir `B(M) := máx(E(s_j), 0,20·M)`; **no se aplica aquí
   porque el acto de gobierno prescribe la envolvente sin ese máximo**, y
   cambiarlo por iniciativa propia sería redefinir la regla aprobada.
2. **Escalado por cantidad de trabajo.** Se caracteriza la perturbación que la
   plataforma introduce en una **ventana** de duración `s`, no la varianza
   interna de una operación de producto. La componente de *jitter*
   independiente por unidad sí se promedia; la sistemática entre procesos, no.
3. **Resolución del escalón.** Aunque `U` es exacto, el **escalón** en el que
   cae el cruce sí está cuantizado, y con él el valor `E(s_k)` que fija `U`.
4. **Once procesos siguen siendo pocos para una cola.** `máx − mín` del P95
   sobre once observaciones tiene menos varianza que sobre cinco, pero sigue
   siendo un estadístico de extremo. La envolvente mitiga el efecto —absorbe
   un escalón anómalamente bajo, no uno anómalamente alto—, de modo que el
   sesgo residual es hacia bandas **más anchas**, es decir hacia la
   permisividad, no hacia la exigencia imposible.
5. **`n = 30` por encima de 1 ms.** En las nueve escalas caras el P99 coincide
   con el máximo observado. Cada entrada publica su `resolucion_percentil`.
6. **Un solo entorno.** Todo es `LAB-LINUX`. Nada se generaliza a otra máquina
   ni a otro sistema operativo.
7. **La corrida carga la máquina.** Once procesos secuenciales de ~2 min
   elevan la carga del sistema a lo largo de la corrida. Se publica la carga
   por proceso para que el efecto sea auditable.
8. **Autorreferencia inevitable del esquema.** El validador vive en el mismo
   commit que valida y no puede acreditar sus propios blobs; lo cierra la
   custodia externa vía `git rev-parse <sha>:<ruta>`.
9. **Lo que el validador no puede recomputar:** prosa libre, muestras de
   calibración distintas de la mediana, y carga ambiental. Todo lo demás
   —percentiles, unidades, `D(s)`, `E(s)`, cruce, `SM`, régimen, banda
   aplicada, veredicto, progresión y holgura— se recomputa y se contrasta.
10. **La coherencia con la fila TOL-107 no está garantizada de antemano.** El
    método se congela antes de medir. Si el resultado no situase las
    magnitudes de 0,14–1,0 ms en régimen absoluto, se publica igual, con su
    contradicción declarada. No se ajusta ninguna fórmula tras ver resultados.

---

## 10. Custodia

### 10.1 Ficheros preinscritos

| Ruta |
| --- |
| `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_07_TOL209_BANDA_ENVOLVENTE_v0.1.md` |
| `docs/architecture/SIRIUS_0.2_ADR_002_TOL_107_BANDA_DEPENDIENTE_APROBACION_v1.0.md` |
| `experiments/adr002/tolerances/envelope_protocol.py` |
| `experiments/adr002/tolerances/run_envelope.py` |
| `experiments/adr002/tolerances/schema_envelope_v0_1.py` |
| `experiments/adr002/tolerances/test_adr002_envelope.py` |

### 10.2 Blobs fijados por constante

| Documento | Blob |
| --- | --- |
| Protocolo aprobado | `c298a6b8…` |
| **Registro v0.5** | `b499b573…` |
| Línea base | `f9f05133…` |
| `corpus.py` | `90c5118e…` |
| `floor_scale_probes.py` | `07408093…` |
| `floor_scale_protocol.py` | `aa6e6492…` |
| `suelo_medicion_v0.1.json` | `899ecee8…` |
| `INFORME_SUELO_MEDICION_v0.1_PROPUESTO.md` | `e2b07549…` |
| `suelo_medicion_v0.2.json` | `1d73fa36…` |
| `INFORME_SUELO_MEDICION_v0.2_PROPUESTO.md` | `33f312dd…` |

Fijar el blob del **Registro** es lo que impide que la corrida se ejecute
contra una fila TOL-107 distinta de la que el acto de gobierno aprobó.

### 10.3 Recorrido

```
precondiciones (custodia + evidencias + Registro + salida inexistente)
  → captura ambiental inicial
  → calibración ÚNICA en el padre
  → once procesos independientes con el MISMO plan de unidades
  → sondas heredadas en round-robin sobre (familia, escala)
  → captura ambiental final
  → forma de los resultados
  → custodia REVERIFICADA tras medir
  → envolvente monótona → cruce exacto → SM
  → controles bloqueantes
  → documento → validación → escritura atómica → relectura y revalidación
```

Si cualquier paso falla, **no se escribe artefacto y no se publica ningún
valor**. La escritura usa `os.link`: si la ruta apareciese durante la
medición, falla sin destruir nada.

---

## 11. Matriz bloqueante

| # | Condición | Se hace cumplir en |
| --- | --- | --- |
| 1 | árbol limpio | `verificar_precondiciones_ejecucion` |
| 2 | `HEAD` = commit de preinscripción, y existe | `verificar_precondiciones_ejecucion` |
| 3 | ruta de salida inexistente | precondiciones + `os.link` |
| 4 | seis blobs preinscritos = árbol | `verificar_custodia` |
| 5 | seis blobs preinscritos = commit | `verificar_custodia` (`blob_en_commit`) |
| 6 | tres módulos heredados intactos | `verificar_custodia` |
| 7 | protocolo aprobado intacto | `fallos_documentos_de_referencia` |
| 8 | **Registro v0.5 intacto** | `fallos_documentos_de_referencia` |
| 9 | línea base intacta | `fallos_documentos_de_referencia` |
| 10 | corpus congelado intacto | `verificar_custodia` |
| 11 | **cuatro evidencias anteriores intactas** | `fallos_evidencias_anteriores` |
| 12 | diff vacío en los preinscritos | `verificar_custodia` |
| 13 | custodia reverificada tras medir | `ejecutar_corrida` |
| 14 | once procesos, PIDs distintos y positivos | controles + esquema |
| 15 | 32 combinaciones `(familia, escala)` por proceso | control + esquema |
| 16 | once procesos por `(familia, escala)` | esquema |
| 17 | unidades idénticas entre procesos | control + esquema |
| 18 | unidades derivadas de la calibración publicada | esquema |
| 19 | coste de calibración = P50 de sus muestras | esquema |
| 20 | P50 observado en `[s/2, 2s]` | control + esquema |
| 21 | carga y capturas ambientales presentes | controles + esquema |
| 22 | `boot_id` estable | control + esquema |
| 23 | sin deriva intraproceso | control + esquema |
| 24 | progresión exigible cumplida y recomputada | control + esquema |
| 25 | **envolvente monótona** | control + esquema |
| 26 | **envolvente cubre `D(s)`** | control + esquema |
| 27 | **banda no decreciente (M-03)** | control + esquema |
| 28 | **continuidad exacta en `U`** | control + esquema |
| 29 | **`U` dentro del intervalo de su escalón** | `resolver_cruce` + esquema |
| 30 | **`U = 5·B(U)`** | esquema |
| 31 | **cruce con confirmación posterior** | `resolver_cruce` + esquema |
| 32 | longitud exacta de cada vector | control + esquema |
| 33 | sin muestras negativas | control + esquema |
| 34 | sin filtrado y sin incidencias | control + esquema |
| 35 | warm-up declarado = preinscrito | control + esquema |
| 36 | sin redondeo previo a 100 ns | control + esquema |
| 37 | sondas neutrales (nombres, SQL y AST) | control + esquema + prueba |
| 38 | percentiles por rango más cercano, recomputados | esquema |
| 39 | `resolucion_percentil` coherente con `n` | esquema |
| 40 | familias y escalas de la escalera, sin intrusas | esquema |
| 41 | curva `D`/`E` recomputada | esquema |
| 42 | `detalle_por_escala` recomputado | esquema |
| 43 | `SM` recomputado | esquema |
| 44 | guarda de dominancia antes del régimen | `evaluar_magnitud` + esquema |
| 45 | invariante `mín_s P95 ≥ mín_s P50` | `evaluar_magnitud` + esquema |
| 46 | combinación P50 relativo / P95 absoluto rechazada | `evaluar_magnitud` + esquema |
| 47 | régimen recomputado desde `U` | esquema |
| 48 | **banda de cada magnitud recomputada desde `E`** | esquema |
| 49 | veredicto recomputado desde régimen y banda | esquema |
| 50 | `NO_EVALUABLE` con motivo explícito | esquema |
| 51 | `NO_EVALUABLE` no absuelve controles | esquema |
| 52 | sin `U`, `continuidad_exacta_en_u` **debe** ser False | esquema |
| 53 | no se publica `U` con controles fallidos | esquema |
| 54 | clasificación de la línea base divulgada | esquema |
| 55 | las dos listas de veredicto son la misma | esquema |
| 56 | evidencias anteriores citadas por blob exacto | esquema |
| 57 | cita histórica de los paquetes 05 y 06 fijada | esquema |
| 58 | contraste de métodos explicado por escrito | esquema |
| 59 | plan = plan preinscrito (orden incluido) | esquema |
| 60 | las siete negaciones de `no_autoriza` | esquema |
| 61 | ninguna clasificación de TOL-207 importada | esquema |
| 62 | PIDs medidos = procesos declarados | esquema |
| 63 | `commit_a`, `head` y blobs con forma de objeto Git | esquema |
| 64 | tabla de holgura recomputada | esquema |
| 65 | validador total: nunca lanza | `fallos_banda_envolvente` |
| 66 | artefacto releído y revalidado tras escribir | `ejecutar_corrida` |

---

## 12. Qué desbloquea y qué no

**Desbloquea**, si la corrida es válida: disponer de una **envolvente**, una
**banda `B(M)`** y un **umbral `U`** *propuestos*, con fundamento medido y
multiescala, para que la aprobación de `ADR002-TOL-209` pueda decidirse sobre
evidencia.

**No desbloquea nada más.** `ADR002-TOL-209` sigue **NO SATISFECHA**; el
límite duro de TOL-107 no se fija aquí; no se avanza a T0, candidatos ni
*benchmark*; no se fusiona el PR #117; y las evidencias v0.1 y v0.2 **no se
sustituyen ni se retiran**: se conservan y se citan.

---

## 13. Prohibiciones

1. No modificar ningún documento aprobado o congelado salvo la fila
   `ADR002-TOL-107` que el acto de gobierno autoriza expresamente.
2. No modificar, retirar ni reescribir las evidencias v0.1 y v0.2.
3. No definir sondas nuevas: se heredan congeladas del paquete 06.
4. No usar FTS5, `rank()`, BM25, *embeddings* ni operación de candidato como
   sonda normativa.
5. No ajustar fórmulas, constantes, escalera, controles ni criterios después
   de observar resultados.
6. No publicar `U` ni banda con algún control bloqueante fallido.
7. No inventar valores si el cruce no se resuelve: `NO_EVALUABLE` con motivo.
8. No sobrescribir ni destruir ningún fichero existente al publicar.
