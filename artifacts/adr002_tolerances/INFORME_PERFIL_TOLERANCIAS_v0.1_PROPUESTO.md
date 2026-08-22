# Informe del perfil de tolerancias P50/P95 v0.1 — `LAB-LINUX` — ADR002-TOL-209

| Campo | Valor |
| --- | --- |
| **Estado** | `PROPUESTO · PERFIL DERIVADO — NO APRUEBA TOL-209` |
| **Resultado del método** | **perfil completo**: `SM`, `E50`, `U50`, `B50(M)`, `E95`, `B95(M)` |
| **Puerta** | `ADR002-TOL-209` · **NO SATISFECHA** |
| **Artefacto** | `artifacts/adr002_tolerances/perfil_tolerancias_v0.1.json` (blob `41003495…`) |
| **Fuente** | `artifacts/adr002_tolerances/suelo_medicion_v0.3.json` (blob `72732648…`) · **sin medición nueva** |
| **Paquete** | `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_08_TOL209_PERFIL_TOLERANCIAS_v0.1` |
| **Acto de gobierno** | `SIRIUS_0.2_ADR_002_TOL_107_PERFIL_P50_P95_APROBACION_v1.0.md` |
| **Protocolo** | `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md` |
| **Registro** | fila `ADR002-TOL-107` **v0.5** |
| **Commit de preinscripción** | `7fc028fef243babeeb524fce94b7de724942a057` |
| **Sesiones** | **exactamente 11**, las mismas en toda la escalera |
| **Controles bloqueantes** | **15 / 15** en `True` |

---

## 1. Resultado

El paquete 07 devolvió `NO_EVALUABLE` con una vara única. Separando los dos
percentiles, **el método resuelve**: hay cruce para P50 y hay banda para P95
en todo el rango cubierto.

| Magnitud | Valor |
| --- | --- |
| `SM` — suelo del instrumento | **17 405 ns** (≈ 17,4 µs) |
| `U50` — cruce `B50(M) = 0,20 · M` | **2 685 ns** |
| `B50(U50)` | **537 ns** |
| Escalón del cruce | **10 µs**, intervalo `(0, 10 000]` |
| Continuidad `m · B50(U50) = 0,20 · U50` | **exacta**: `1 · 537 = 2 685 / 5` |
| Rango cubierto por `B95` | **`[17 405, 1 000 000 000]` ns** |

Nada de esto es normativo todavía: son **valores propuestos** hasta el acta
que los apruebe.

---

## 2. Las dos curvas y sus envolventes

`D_p(s)` es la dispersión `(máx − mín)` del percentil `p` entre las once
sesiones, tomada en la peor de las dos familias neutrales.
`E_p(s_i) = máx(D_p(s_1), …, D_p(s_i))` es su envolvente monótona, y la banda
`B_p(M) = E_p(s_j)` con `s_j` el menor escalón `≥ M`.

| Escala | `D50(s)` | `E50(s)` | `E50/s` | `D95(s)` | `E95(s)` | `E95/s` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 µs | 537 ns | 537 ns | 0,053 | 11 000 ns | 11 000 ns | 1,100 |
| 20 µs | 1 462 ns | 1 462 ns | 0,073 | 26 939 ns | 26 939 ns | 1,346 |
| 50 µs | 4 081 ns | 4 081 ns | 0,081 | 30 558 ns | 30 558 ns | 0,611 |
| **100 µs** | 15 777 ns | 15 777 ns | **0,157** | 95 953 ns | 95 953 ns | 0,959 |
| 200 µs | 23 784 ns | 23 784 ns | 0,118 | 155 066 ns | 155 066 ns | 0,775 |
| 500 µs | 43 543 ns | 43 543 ns | 0,087 | 332 895 ns | 332 895 ns | 0,665 |
| 1 ms | 60 044 ns | 60 044 ns | 0,060 | 971 628 ns | 971 628 ns | 0,971 |
| 2 ms | 206 469 ns | 206 469 ns | 0,103 | 1 497 366 ns | 1 497 366 ns | 0,748 |
| 5 ms | 579 360 ns | 579 360 ns | 0,115 | 2 195 694 ns | 2 195 694 ns | 0,439 |
| 10 ms | 539 701 ns | *579 360 ns* | 0,057 | 3 973 044 ns | 3 973 044 ns | 0,397 |
| 20 ms | 1 799 022 ns | 1 799 022 ns | 0,089 | 8 894 142 ns | 8 894 142 ns | 0,444 |
| 50 ms | 3 154 646 ns | 3 154 646 ns | 0,063 | 22 662 076 ns | 22 662 076 ns | 0,453 |
| 100 ms | 6 600 294 ns | 6 600 294 ns | 0,066 | 25 197 279 ns | 25 197 279 ns | **0,251** |
| 200 ms | 11 324 952 ns | 11 324 952 ns | 0,056 | 187 831 392 ns | 187 831 392 ns | 0,939 |
| 500 ms | 27 006 310 ns | 27 006 310 ns | 0,054 | 165 166 235 ns | *187 831 392 ns* | 0,375 |
| **1 s** | 48 791 690 ns | 48 791 690 ns | **0,048** | 256 936 311 ns | 256 936 311 ns | 0,256 |

*En cursiva, los dos escalones donde la envolvente queda por encima de la
dispersión medida: 10 ms en `E50` y 500 ms en `E95`. Es lo que hace la
monotonía, y es su precio.*

**La asimetría que motivó la separación queda confirmada con precisión.**
`E50(s)/s` **nunca llega al 20 %**: su peor valor es **0,157**, en 100 µs.
`E95(s)/s` **nunca baja del 20 %**: su mejor valor es **0,251**, en 100 ms.
Las dos curvas están separadas por la frontera del objetivo en las dieciséis
escalas, sin un solo cruce entre ellas. Exigirles la misma vara no era
severo: era **contradictorio**.

---

## 3. Lo que hay que leer con incomodidad: `U50 < SM`

`U50` vale **2 685 ns** y `SM` vale **17 405 ns**. El cruce cae **más de seis
veces por debajo del suelo del instrumento**. La consecuencia es aritmética y no
admite matices:

- el régimen **absoluto** de P50 rige para `M < U50 = 2 685 ns`;
- pero por debajo de `SM = 17 405 ns` **no se emite afirmación de latencia**;
- luego el intervalo donde `B50(M)` decidiría algo está **enteramente dentro
  de la zona muda**. `B50(M)` **nunca llega a vincular**.

**Para P50, este perfil equivale al objetivo relativo del 20 % aplicado en
todo el rango medible.** Toda la maquinaria de envolvente, escalón superior y
cruce —construida en los paquetes 06 y 07— acaba siendo, para el centro de la
distribución, **vestigial**. No es un fallo del método: es lo que el método
dice cuando el centro resulta ser estable. Se declara porque un lector que
viese `U50` publicado sin esta advertencia podría creer que hay dos regímenes
operativos donde solo hay uno.

Esto ya estaba anticipado como limitación 4 del paquete 08, **antes** de
derivar. Los números lo confirman en vez de sorprenderlo.

**Donde la banda sí es todo lo que hay es en P95.** Allí no existe umbral
relativo, y `B95(M)` es el **único** criterio en `[SM, 1 s]`. La separación no
traslada la exigencia de un percentil a otro: se la quita al que no podía
cumplirla en ninguna escala y se la deja **íntegra** al que sí.

**El riesgo M-03 queda cerrado por la separación, no por la banda.** La
preocupación original era que un objetivo relativo único penalizase a los
candidatos *más rápidos* por serlo. Con `E50(s)/s ≤ 0,157` en las dieciséis
escalas, el 20 % de P50 es alcanzable **hasta los 10 µs**; y la cola, que no
lo era en ninguna, deja de estar sujeta a él.

### Lo que este cruce no acredita

El cruce cae en el **primer** escalón de la escalera y su intervalo es
`(0, 10 000]`. Su posición exacta descansa por tanto **sobre un solo punto**,
`E50(10 µs) = 537 ns`, sin ninguna escala medida por debajo que la confirme.
Extender la escalera hacia abajo no está autorizado por este paquete, y no
haría falta para P50 mientras el cruce siga por debajo de `SM`: en esa zona
no se emite afirmación de todas formas.

---

## 4. Cómo se consulta el perfil

`M` es el **mínimo entre sesiones del mismo percentil que se evalúa**: `B50`
en `mín_s P50` y `B95` en `mín_s P95`. **Nunca se mezcla el mínimo de un
percentil con la banda del otro** — y como los dos mínimos suelen caer en
escalones distintos, suelen recibir bandas distintas.

| Percentil | Debajo de `SM` | `[SM, 1 s]` | Encima de 1 s |
| --- | --- | --- | --- |
| **P50** | sin afirmación | `≤ 20 %` relativo *(el tramo absoluto queda por debajo de `SM`)* | `≤ 20 %` relativo |
| **P95** | `NO_EVALUABLE` | `(máx − mín) ≤ B95(M)` | `NO_EVALUABLE` |

**Agregación.** Basta que uno de los dos falle para que la magnitud falle.
Hacen falta **los dos**, evaluables y válidos, para que sea válida. En
particular, **una magnitud por encima de 1 s no recibe veredicto positivo**:
su cola está fuera del rango calibrado y el perfil calla en vez de afirmar
estabilidad sobre algo que no ha medido.

---

## 5. La línea base histórica: `NO_COMPARABLE`, sin excepción

La regla 5 prohíbe comparar rangos obtenidos con números distintos de
sesiones. La línea base se midió con **cinco**. Sus seis magnitudes se
publican como **contraste declarado**, con sus cifras íntegras y **sin
veredicto**:

| Magnitud | Sesiones | mín P50 | máx P50 | `D` P50 | mín P95 | máx P95 | `D` P95 | Resultado |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `cero_resultados.recuperacion_completa_rank` | 5 | 116 286 300 | 128 586 400 | 12 300 100 | 125 809 200 | 145 663 000 | 19 853 800 | `NO_COMPARABLE` |
| `cero_resultados.solo_indice_fts5` | 5 | 140 700 | 181 900 | 41 200 | 188 400 | 254 500 | 66 100 | `NO_COMPARABLE` |
| `un_resultado_exacto.recuperacion_completa_rank` | 5 | 115 518 500 | 127 762 700 | 12 244 200 | 127 777 300 | 143 538 100 | 15 760 800 | `NO_COMPARABLE` |
| `un_resultado_exacto.solo_indice_fts5` | 5 | 155 800 | 190 100 | 34 300 | 216 900 | 288 200 | 71 300 | `NO_COMPARABLE` |
| `muchos_candidatos.recuperacion_completa_rank` | 5 | 117 817 400 | 121 151 400 | 3 334 000 | 127 499 800 | 147 176 400 | 19 676 600 | `NO_COMPARABLE` |
| `muchos_candidatos.solo_indice_fts5` | 5 | 596 200 | 675 900 | 79 700 | 735 700 | 1 003 800 | 268 100 | `NO_COMPARABLE` |

*(ns; los campos «banda que le correspondería» se publican en `null` a
propósito: insinuar una banda para una magnitud no comparable sería emitir el
veredicto que la regla prohíbe.)*

El artefacto **no publica** ninguna banda para estas magnitudes, y el
validador rechaza que se publique. Un rango de cinco tiene una esperanza
menor que uno de once por razones de tamaño de muestra, no de estabilidad:
compararlo con estas bandas favorecería sistemáticamente a la línea base.
**El perfil no puede pronunciarse sobre FTS5 ni sobre `rank()`.** Para
hacerlo habría que remedirlos con once sesiones, lo que este paquete **no
autoriza**.

---

## 6. Qué acredita esta derivación

**No hubo medición.** No se abrió cronómetro, no se lanzó ningún proceso, no
se tocó SQLite. La fuente es la evidencia congelada v0.3, fijada por blob, y
los percentiles se **recomputan desde sus vectores crudos**: si la fuente
publicase un percentil incoherente con su propio vector, el perfil se
construiría con el vector.

**Los quince controles bloqueantes están en `True`, y los quince se
recomputan.** Ninguno se publica como constante:

| Control | Cómo se comprueba |
| --- | --- |
| `fuente_intacta` | blob de la fuente, sobre **los mismos bytes** que se interpretan |
| `fuente_con_once_sesiones` | 11 identificadores, 11 observaciones y **las mismas 11** en toda la fuente |
| `escalera_completa` | 32 combinaciones y escalera estrictamente creciente |
| `percentiles_recomputados` | los recomputados coinciden con los que la fuente publica |
| `envolventes_monotonas` · `envolventes_cubren_el_suelo` · `bandas_no_decrecientes` | sobre `E50` y `E95` |
| `continuidad_p50_exacta` | `1 · 537 = 2 685 / 5`, sin resto |
| `p95_no_mas_estable_que_p50` | `E95(s) ≥ E50(s)` en los dieciséis escalones |
| `sin_umbral_relativo_para_p95` | se **interroga** al evaluador en todo el rango |
| `guarda_de_sesiones_activa` | contra el número exigido, no contra el perfil |
| `evidencias_anteriores_intactas` · `documentos_de_gobierno_intactos` | seis evidencias, protocolo v0.1 y Registro v0.4 |
| `derivacion_determinista` | resultado de comparar los bytes de dos pasadas |
| `custodia_verificada` | cadena completa contra el árbol y contra el commit |

**El determinismo se comprueba, no se promete.** La derivación se ejecuta dos
veces desde la misma fuente y se comparan los **bytes serializados**; el
control publicado es el resultado de esa comparación. Una prueba lo repite a
través de la interfaz completa.

**Las evidencias v0.1, v0.2 y v0.3 siguen intactas**, verificadas byte a
byte, y el protocolo v0.1 y el Registro v0.4 tampoco se han tocado: por eso
el protocolo v0.2 y el Registro v0.5 son **documentos nuevos**.

---

## 7. Limitaciones

1. **`U50` queda por debajo de `SM`.** El régimen absoluto de P50 no llega a
   vincular. Se explica en el §3.
2. **La fuente es una sola corrida.** Once sesiones siguen siendo pocas para
   caracterizar una cola, y la máquina no tenía la carga controlada.
3. **`E95` arrastra el atípico de 200 ms** hasta 500 ms. Es el precio de la
   monotonía, que es lo que impide dar a una operación mayor una banda más
   estrecha.
4. **El cruce descansa sobre un solo escalón**, el primero, sin escalas
   medidas por debajo que lo confirmen.
5. **El perfil no puede juzgar la línea base**, por el §5.
6. **Un solo entorno.** Todo es `LAB-LINUX`. `ACEPTACIÓN-WINDOWS` sigue
   pendiente.
7. **Por encima de 1 s no hay veredicto**, ni positivo ni negativo: `B95` no
   está definida allí.

---

## 8. Estado de la puerta

**`ADR002-TOL-209` sigue NO SATISFECHA.**

Este perfil es la **cifra que le faltaba** a `ADR002-TOL-107` para poder
instanciarse, y por tanto el último insumo técnico de la puerta. Pero la
puerta la abre un **acta de aprobación**, no una derivación, y esa acta no
existe.

`ADR002-TOL-107` conserva `PROPUESTA` para objetivos y umbral, y
`REGLA_CONFIRMADA_VALOR_ENTORNO` para el límite duro, **que este paquete no
fija**.

**Este informe no autoriza:** aprobar `ADR002-TOL-209`; ninguna medición
nueva; fijar el límite duro; avanzar a **T0**; implementar o ejecutar
**candidatos**; ejecutar el **benchmark**; ni fusionar el **PR #117**.

**Siguiente movimiento único:** que el usuario apruebe o corrija el acto de
gobierno, el protocolo v0.2, el Registro v0.5 y las cifras de este perfil.
