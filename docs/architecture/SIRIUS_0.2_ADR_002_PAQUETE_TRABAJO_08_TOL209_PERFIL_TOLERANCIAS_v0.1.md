# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 08 · Perfil de tolerancias P50/P95

| Campo | Valor |
| --- | --- |
| **Estado** | `PROPUESTO · PERFIL DERIVADO — NO APRUEBA TOL-209` |
| **Puerta** | `ADR002-TOL-209` · **NO SATISFECHA** |
| **Acto de gobierno** | `SIRIUS_0.2_ADR_002_TOL_107_PERFIL_P50_P95_APROBACION_v1.0.md` |
| **Protocolo aplicable** | `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md` |
| **Registro aplicable** | `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.5_PROPUESTO.md`, fila `ADR002-TOL-107` |
| **Fuente** | `artifacts/adr002_tolerances/suelo_medicion_v0.3.json` (blob `72732648…`), **congelada** |
| **Medición nueva** | **ninguna** |
| **No autoriza** | aprobar TOL-209, fijar el límite duro de TOL-107, medir de nuevo, avanzar a T0, implementar o ejecutar candidatos, ejecutar el *benchmark*, fusionar el PR #117 |

---

## 0. Objeto

Derivar, de forma **determinista y sin medir**, el perfil de tolerancias que
la fila `ADR002-TOL-107` necesita para poder instanciarse: `SM`, la
envolvente `E50` con su cruce `U50` y su banda `B50(M)`, y la envolvente
`E95` con su banda `B95(M)`.

### 0.1 Por qué dos commits

1. **Commit de preinscripción** — acto de gobierno, Registro v0.5, protocolo
   v0.2, este documento y los módulos que implementan la derivación,
   congelados **antes de producir el perfil**.
2. **Commit del perfil** — el artefacto y el informe producidos
   **exactamente** por el código del commit anterior.

La separación importa menos que en los paquetes de medición —la derivación
es determinista y cualquiera puede reproducirla bit a bit— pero se conserva
porque es la disciplina de la puerta y porque hace explícito que las reglas
se escribieron antes de ver sus consecuencias numéricas.

---

## 1. Qué corrige este paquete

El paquete 07 devolvió `NO_EVALUABLE` porque exigía a **ambos** percentiles el
mismo objetivo relativo del 20 %. La asimetría estaba en su propia evidencia:

| Estadístico | Peor `D(s)/s` | Peor por escala: el mínimo |
| --- | ---: | ---: |
| **P50** | 0,158 | 0,049 |
| **P95** | 1,347 | **0,252** |

El paquete 08 no vuelve a medir: **relee los mismos vectores con la vara
correcta para cada percentil.**

---

## 2. El método

### 2.1 Definiciones vinculantes

Para cada percentil `p ∈ {P50, P95}`, sobre la escalera `s_1 < … < s_n`:

```
D_p(s_i)  = peor (máx − mín) entre las 11 sesiones, sobre las dos familias
E_p(s_i)  = máx( D_p(s_1), …, D_p(s_i) )          envolvente monótona
B_p(M)    = E_p(s_j)   con   j = mín{ i : s_i ≥ M } escalón superior
```

**`D_p` ya no toma el peor caso sobre percentiles.** Ésa es la separación:
cada percentil construye su curva con sus propios datos.

### 2.2 P50

| Rango de `M = mín_s P50` | Regla |
| --- | --- |
| `M < SM` | **sin afirmación de latencia** |
| `SM ≤ M < U50` | `(máx − mín) ≤ m · B50(M)` |
| `M ≥ U50` | `(máx − mín) / mín ≤ 1/5` |

`U50 = 5 · E50(s_k)` sobre el menor escalón `k` que sostiene
`5·E50(s_k) ≤ s_k` y todos los superiores. Se demuestra —y se comprueba en
ejecución— que `s_(k−1) < U50 ≤ s_k`, de modo que `B50(U50) = E50(s_k)` y

```
m · B50(U50) = U50 / 5 = 0,20 · U50
```

es **exacto**. `m = 1` no se elige: es la única solución.

### 2.3 P95

| Rango de `M = mín_s P95` | Regla |
| --- | --- |
| `M < SM` | **`NO_EVALUABLE`** |
| `SM ≤ M ≤ s_n` | `(máx − mín) ≤ m · B95(M)` |
| `M > s_n` | **`NO_EVALUABLE`** |

**No hay umbral relativo para P95.** El validador lo hace cumplir: publicar
`u95_ns`, `umbral_ns`, `objetivo_relativo` o `factor_u` dentro de la sección
`p95` es un fallo, igual que publicar `sostenible` en su curva.

### 2.4 La banda se consulta en el mínimo de SU percentil

`B50` en `mín_s P50` y `B95` en `mín_s P95`. Como `mín_s P95 ≥ mín_s P50` por
el invariante, los dos mínimos caen en general en **escalones distintos** y
por tanto reciben **bandas distintas**. Mezclarlos sería aplicar a la cola la
banda del centro.

### 2.5 Exactamente once sesiones

`(máx − mín)` es un **rango**. La esperanza de un rango crece con el tamaño
de la muestra. Por eso:

- las bandas se construyen con **exactamente 11** sesiones —ni 10 ni 12: la
  cobertura comprueba once **identificadores**, once **observaciones** —una
  por sesión, de modo que el rango no se tome sobre doce muestras— y que sean
  **las mismas once en toda la escalera**; falla cerrado;
- una magnitud evaluada con otro número de sesiones sale **`NO_COMPARABLE`**
  y **sin veredicto**;
- la **línea base histórica**, medida con **cinco** sesiones, entra en el
  perfil como **contraste declarado no comparable**. Se publican sus cifras
  para que la asimetría entre P50 y P95 sea auditable, y **jamás** como
  veredicto. El validador rechaza cualquier intento de emitirlo.

Esta última consecuencia es incómoda y se declara: el perfil **no puede
pronunciarse** sobre las magnitudes históricas de FTS5 y `rank()`. Para
hacerlo habría que remedirlas con once sesiones, lo que **este paquete no
autoriza**.

### 2.6 Agregación

Un percentil `NO_EVALUABLE` **no emite afirmación**, y la consecuencia se
toma en la dirección conservadora:

- **basta un fallo** para que la magnitud falle;
- **hacen falta los dos**, evaluables y válidos, para que sea válida. Si
  alguno es `NO_EVALUABLE`, la magnitud lo es.

Lo segundo importa: el §2.3 ordena declarar `NO_EVALUABLE` el P95 de una
magnitud **por encima de la mayor escala medida**. Si la agregación heredase
ahí el veredicto del P50, el perfil afirmaría estabilidad sobre una magnitud
cuya cola está fuera del rango calibrado. La regla se declara además en el
propio artefacto, en `metodo.agregacion`, para que un consumidor del JSON
pueda reconstruirla sin salir de él.

---

## 3. Determinismo

La derivación es una **función pura** de la fuente congelada. No hay reloj,
ni PID, ni carga, ni orden de proceso, ni nada dependiente del momento de
ejecución.

La corrida lo **comprueba en vez de prometerlo**: deriva el documento dos
veces desde la misma fuente y compara los **bytes serializados**. Si
difieren, se bloquea. Una prueba lo repite a través de `main()` escribiendo
dos artefactos y comparando sus contenidos.

Es la garantía que ninguna medición podía ofrecer, y compensa que la
separación preinscripción/evidencia tenga aquí menos fuerza probatoria.

### 3.1 Los percentiles se recomputan

El perfil **no acepta** los percentiles que la fuente publica: los recomputa
por rango más cercano desde `muestras_ns`. Si el artefacto v0.3 publicase un
percentil incoherente con su propio vector, el perfil se construiría con el
vector. La coincidencia entre ambos se publica como control
(`percentiles_recomputados`), no como supuesto.

---

## 4. Lo que se hereda congelado

| Módulo | Blob | Qué aporta |
| --- | --- | --- |
| `envelope_protocol.py` | `afa4a7fe…` | envolvente, escalón superior, cruce, continuidad, `banda_no_decreciente` |

La aritmética del cruce ya fue auditada en el paquete 07. Reutilizarla en vez
de copiarla es lo que permite atribuir cualquier diferencia de resultado a la
**separación por percentil** y no a una reimplementación.

La escalera (16 escalones, 10 µs – 1 s), las familias neutrales y las sondas
de suelo unitario se heredan sin cambio.

---

## 5. Controles internos bloqueantes

Quince. **Los quince se recomputan**: ninguno se publica como constante ni se
declara sin comprobarse. Fallan **cerrado** —ausente o distinto de `True` es
fallido— y el esquema rechaza publicar `U50` con alguno fallido.

| Control | Qué comprueba |
| --- | --- |
| `fuente_intacta` | el blob de `suelo_medicion_v0.3.json` |
| `fuente_con_once_sesiones` | 11 PIDs distintos **y** 11 observaciones —una por sesión— en cada `(familia, escala)`, **las mismas 11 sesiones en toda la fuente** y el plan declarado |
| `escalera_completa` | las 32 combinaciones y la escalera estrictamente creciente |
| `percentiles_recomputados` | los recomputados coinciden con los publicados por la fuente |
| `envolventes_monotonas` | `E50` y `E95` no decrecen |
| `envolventes_cubren_el_suelo` | `E_p(s_i) ≥ D_p(s_i)` en todo escalón |
| `bandas_no_decrecientes` | ninguna banda se estrecha al crecer `M` (cierra M-03) |
| `continuidad_p50_exacta` | `m·B50(U50) = 0,20·U50` sin resto |
| `p95_no_mas_estable_que_p50` | `E95(s) ≥ E50(s)` en todo escalón |
| `sin_umbral_relativo_para_p95` | se **interroga** a `evaluar_p95` en todo el rango: régimen siempre absoluto, la banda es lo que vincula, y existe un punto donde una magnitud con variación relativa **superior** al 20 % es válida |
| `guarda_de_sesiones_activa` | una magnitud de 5 sesiones sale `NO_COMPARABLE`, una de 11 no |
| `evidencias_anteriores_intactas` | los **seis** blobs de v0.1, v0.2 y v0.3 |
| `documentos_de_gobierno_intactos` | protocolo **v0.1** y Registro **v0.4** sin tocar |
| `derivacion_determinista` | el documento se construye **con el resultado** de comparar los bytes de dos pasadas |
| `custodia_verificada` | cadena completa contra el árbol y contra el commit |

`continuidad_p50_exacta` presupone un `U50` resuelto: sin él no puede
satisfacerse, y el validador lo impone en ambas direcciones.

---

## 6. Limitaciones conocidas

1. **El perfil no puede juzgar la línea base.** Es consecuencia directa de la
   regla de las once sesiones (§2.5). La comparación histórica queda
   suspendida hasta que exista una medición de esas magnitudes con once
   sesiones. Se declara en lugar de rodearse.
2. **La fuente es una sola corrida.** El perfil hereda todas las limitaciones
   del paquete 07: once sesiones siguen siendo pocas para una cola, la
   máquina se cargó durante la corrida, y el escalón de 200 ms contiene un
   valor atípico que la envolvente propaga hacia arriba en `E95`.
3. **`E95` arrastra ese atípico.** Es el precio de la monotonía, que es lo
   que impide que una operación mayor reciba una banda más estrecha. La
   alternativa —leer `D95` directamente— reabriría M-03.
4. **`U50` depende del primer escalón.** Si `D50` es pequeña en 10 µs, el
   cruce cae ahí y `U50` queda muy por debajo de `SM`, de modo que el régimen
   absoluto de P50 resulta **vestigial**: todo lo medible vive en el relativo.
   No es un defecto —significa que el centro es estable— pero conviene leerlo
   sabiéndolo.
5. **El validador no ve la fuente.** Recomputa a partir de las curvas que el
   propio perfil publica y comprueba su coherencia interna, sus invariantes y
   sus reglas. La correspondencia con la fuente la garantiza la custodia por
   blob, no el esquema.
6. **Un solo entorno.** Todo es `LAB-LINUX`.
7. **Una magnitud por encima de 1 s no recibe veredicto.** La agregación
   exige los **dos** percentiles evaluables para declarar válida una
   magnitud, y por encima de la mayor escala medida P95 es `NO_EVALUABLE`.
   La consecuencia querida es que el perfil **calla** en vez de afirmar
   estabilidad sobre una cola fuera del rango calibrado; la consecuencia
   práctica es que ese tramo exige ampliar la escalera antes de poder
   juzgarse.
8. **El método no resuelve `D50(s_1) = 0`.** Con dispersión P50 nula en el
   primer escalón el cruce degeneraría a `U50 = 0`, fuera del dominio en que
   la aritmética heredada está demostrada. La derivación lo **denuncia y se
   detiene** en vez de propagar un invariante violado. No ocurre con la
   fuente congelada, y con `SM > 0` esa dispersión no se distinguiría de la
   resolución del propio instrumento.
7. **Autorreferencia inevitable del esquema.** Vive en el mismo commit que
   valida; lo cierra la custodia externa vía `git rev-parse <sha>:<ruta>`.
8. **Lo que el validador no puede recomputar:** prosa libre y notas. Todo lo
   demás —curvas, envolventes, bandas, cruce, continuidad, guarda de
   sesiones, controles y negaciones— se recomputa y se contrasta.

---

## 7. Custodia

### 7.1 Ficheros preinscritos

| Ruta |
| --- |
| `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_08_TOL209_PERFIL_TOLERANCIAS_v0.1.md` |
| `docs/architecture/SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md` |
| `docs/architecture/SIRIUS_0.2_ADR_002_TOL_107_PERFIL_P50_P95_APROBACION_v1.0.md` |
| `docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.5_PROPUESTO.md` |
| `experiments/adr002/tolerances/derive_profile.py` |
| `experiments/adr002/tolerances/profile_protocol.py` |
| `experiments/adr002/tolerances/schema_profile_v0_1.py` |
| `experiments/adr002/tolerances/test_adr002_profile.py` |

### 7.2 Lo que NO se toca, y por qué es un control

| Documento | Blob | Por qué |
| --- | --- | --- |
| `PROTOCOLO_MEDICION_v0.1` | `c298a6b8…` | citado por las evidencias v0.1, v0.2 y v0.3 |
| `REGISTRO_TOLERANCIAS_v0.4` | `b499b573…` | citado por la evidencia v0.3 |
| `suelo_medicion_v0.1.json` + informe | `899ecee8…` / `e2b07549…` | evidencia publicada |
| `suelo_medicion_v0.2.json` + informe | `1d73fa36…` / `33f312dd…` | evidencia publicada |
| `suelo_medicion_v0.3.json` + informe | `72732648…` / `2c4da11a…` | evidencia publicada **y fuente del perfil** |
| `mediciones_linea_base_v0.2.json` | `f9f05133…` | contraste histórico |

Editar cualquiera de ellos haría **incomprobable la custodia** de evidencia
ya publicada. Por eso el protocolo y el Registro se **versionan**, no se
editan, y su intangibilidad es un control bloqueante.

### 7.3 Recorrido

```
precondiciones (custodia + gobierno anterior + evidencias + salida inexistente)
  → lectura de la fuente congelada
  → recomputación de percentiles desde muestras_ns
  → D50/D95 → E50/E95 → cruce U50 → SM
  → contraste NO_COMPARABLE de la línea base
  → controles bloqueantes
  → documento → SEGUNDA derivación → comparación de bytes
  → validación → escritura atómica → relectura y revalidación
```

Si cualquier paso falla, **no se escribe artefacto y no se publica ningún
valor**. La escritura usa `os.link`: si la ruta apareciese durante la
derivación, falla sin destruir nada.

---

## 8. Matriz bloqueante

| # | Condición | Se hace cumplir en |
| --- | --- | --- |
| 1 | árbol limpio y `HEAD` = commit de preinscripción | `verificar_precondiciones` |
| 2 | ruta de salida inexistente | precondiciones + `os.link` |
| 3 | ocho blobs preinscritos contra el árbol y contra el commit | `verificar_custodia` |
| 4 | módulo heredado intacto | `verificar_custodia` |
| 5 | protocolo v0.1 y Registro v0.4 intactos | `fallos_documentos_de_gobierno` |
| 6 | seis evidencias anteriores intactas | `fallos_evidencias_anteriores` |
| 7 | línea base intacta | `comprobar_precondiciones` |
| 8 | fuente con el blob congelado, hasheado sobre **los mismos bytes** que se interpretan | `ejecutar_derivacion` con lectura única |
| 9 | exactamente 11 sesiones, 11 observaciones y **las mismas** en toda la escalera | `comprobar_cobertura` |
| 10 | exactamente 11 sesiones por sonda unitaria, y las mismas en las tres | `calcular_sm` |
| 11 | percentiles recomputados desde los vectores | `observaciones_desde_fuente` |
| 12 | `D50` y `D95` construidas por separado | `dispersion_de_escala` |
| 13 | envolventes = máximo acumulado de su curva | esquema |
| 14 | envolventes monótonas | control + esquema |
| 15 | envolventes cubren su dispersión | control + esquema |
| 16 | bandas no decrecientes (M-03) | control + esquema |
| 17 | `E95(s) ≥ E50(s)` en todo escalón | control + esquema |
| 18 | `U50` recomputado desde `E50` | esquema |
| 19 | `U50` dentro del intervalo de su escalón | `resolver_cruce` + esquema |
| 20 | continuidad `m·B50(U50) = 0,20·U50` exacta | control + esquema |
| 21 | sin `U50`, no se publican `U50` ni `B50(U50)` | esquema |
| 22 | P95 sin umbral relativo ni `sostenible`, **bajo ningún nombre** | control operativo + esquema con el conjunto de campos cerrado |
| 23 | `rango_cubierto_ns` = `[SM, s_n]` | esquema |
| 24 | banda = envolvente en cada escalón | esquema |
| 25 | razones por mil recomputadas | esquema |
| 26 | `B` se consulta en el mínimo de SU percentil | `evaluar_p50` / `evaluar_p95` + prueba |
| 27 | guarda de sesiones activa, contra `SESIONES_EXIGIDAS` y no contra el perfil | `Perfil.__post_init__` + control + esquema |
| 28 | magnitud con `n ≠ 11` → `NO_COMPARABLE` sin veredicto, y con `n = 11` veredicto **recomputado** | `evaluar_magnitud` contra `SESIONES_EXIGIDAS` + esquema en sus dos direcciones |
| 29 | contraste sin bandas para lo no comparable | esquema |
| 30 | dispersiones del contraste recomputadas | esquema |
| 31 | invariante `mín_s P95 ≥ mín_s P50` | `evaluar_magnitud` + esquema |
| 32 | agregación: `NO_EVALUABLE` no convalida **ni se hereda** el veredicto del otro percentil | `agregar` + prueba del caso «por encima de la escalera» |
| 33 | derivación determinista (bytes), y sin traducir saltos de línea | control derivado de la comparación + `newline="\n"` + prueba |
| 34 | el perfil no republica la medición, ni renombrando la sección | esquema con el conjunto de secciones cerrado |
| 35 | no se publica `U50` con controles fallidos | esquema |
| 36 | las ocho negaciones de `no_autoriza` | esquema |
| 37 | `commit_a`, `head` y blobs con forma de objeto Git | esquema |
| 38 | identidad: acta, protocolo v0.2, Registro v0.5, paquete | esquema |
| 39 | validador total: nunca lanza | `fallos_perfil_tolerancias` |
| 40 | artefacto releído y revalidado tras escribir | `ejecutar_derivacion` |

---

## 9. Qué desbloquea y qué no

**Desbloquea**, si la derivación es válida: disponer de un **perfil de
tolerancias propuesto** —`SM`, `E50`, `U50`, `B50(M)`, `E95`, `B95(M)`— con
el que `ADR002-TOL-107` puede por fin instanciarse, y una regla explícita
sobre qué mediciones son comparables con él.

**No desbloquea nada más.** `ADR002-TOL-209` sigue **NO SATISFECHA**; no se
autoriza medición nueva; el límite duro no se fija; no se avanza a T0,
candidatos ni *benchmark*; no se fusiona el PR #117; y las evidencias v0.1,
v0.2 y v0.3 **no se sustituyen ni se retiran**.

---

## 10. Prohibiciones

1. No editar el protocolo v0.1, el Registro v0.4 ni ninguna evidencia
   publicada: se versionan.
2. No medir. Este paquete deriva.
3. No comparar rangos obtenidos con números distintos de sesiones.
4. No crear umbral relativo para P95.
5. No mezclar el mínimo de un percentil con la banda del otro.
6. No ajustar reglas, escalera ni constantes después de observar el perfil.
7. No publicar `U50` ni bandas con algún control bloqueante fallido.
8. No sobrescribir ni destruir ningún fichero existente al publicar.
