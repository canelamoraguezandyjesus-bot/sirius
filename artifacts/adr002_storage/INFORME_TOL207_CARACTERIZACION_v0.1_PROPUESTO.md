# SIRIUS 0.2 — ADR-002 · Informe de caracterización de almacenamiento TOL-207

**Versión:** 0.1
**Estado:** **PROPUESTO** · informe de caracterización, no aprueba ni decide nada
**Fecha:** 27 de julio de 2026
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_04_TOL207_CARACTERIZACION_v0.1.md`
**Propuesta que acompaña:** `SIRIUS_0.2_ADR_002_TOL_207_PRESUPUESTO_ALMACENAMIENTO_v0.2_PROPUESTO.md`
**Evidencia legible por máquina:** `artifacts/adr002_storage/entorno_lab_v0.1.json`
**Código:** `experiments/adr002/storage/`
**Alcance:** LAB-LINUX — no es aceptación Windows
**No autoriza:** benchmark T1–T4, ejecución de T0, implementación, aprobación de TOL-207 ni merge.

---

## 1. Por qué la v0.1 no era aprobable

La v0.1 acertó en el método —gobernar por `f_bavail` confirmado con
escritura real, no por el «libre» del dispositivo— pero contenía tres
errores aritméticos y cuatro carencias estructurales:

1. **Reserva de seguridad 15.652.167.680 B**: el 50 % exacto de
   31.304.323.072 es 15.652.161.536. Error de **+6.144 B**.
2. **Suelo 30.684.553.216 B**: arrastraba el mismo error. El suelo exacto
   es 30.684.547.072 B.
3. **27,43 %** como porcentaje agregado: 8.589.934.592 ÷ 31.304.323.072 =
   27,4401… % → el redondeo correcto es **27,44 %**.
4. Trataba el entorno como una máquina implícitamente estable, cuando cada
   sesión es un contenedor distinto con disponibilidad distinta.
5. No tenía regla de admisión operativa ni salida de aborto.
6. No separaba proveniencias ni explicaba por qué la reserva aparente del
   dispositivo cambia entre sesiones.
7. No definía objeto contabilizado, protocolo de pico ni denominador.

Un límite cuya propia aritmética no cuadra no puede ser puerta de arranque:
la matriz de aceptación (condición 11) lo bloquea.

## 2. Qué conserva y qué corrige la v0.2

**Conserva:** `E_MIN_HISTORICO` = 31.304.323.072 B como base normativa; los
presupuestos de 1.610.612.736 B por candidato y 8.589.934.592 B agregados;
la reserva operativa de 6.442.450.944 B; la advertencia sobre `df`; el
alcance LAB-LINUX y la remisión del presupuesto de producto a TOL-205.

**Corrige:** las tres cifras retiradas (registradas como errores históricos
con su desviación exacta de +6.144 B y el redondeo 27,43→27,44, y
rechazadas por el validador si reaparecen como vigentes); y añade
clasificación de envolvente, regla de admisión, proveniencia, anomalía
documentada, objeto contabilizado, protocolo de pico, denominador y
escalas.

## 3. Por qué el entorno es una envolvente y no una máquina estable

Tres sesiones conocidas del mismo laboratorio dieron `f_bavail` de
31.304.323.072 B (26-jul), ≈32.158.220.288 B (forense) y 31.231.950.848 B
(este paquete). Hostname, machine-id, boot-id y `f_fsid` cambian por
contenedor. Lo que **sí** se repite es la geometría: ext4, `f_frsize`
4.096, `f_blocks` 66.053.021, 270.553.174.016 B totales, 16.777.216
inodos, montaje rw con mecanismo de bloques reservados observable, x86_64,
Ubuntu 24.04. La clasificación honesta es **`ENVOLVENTE_REPRODUCIBLE`**:
huella estable verificable más suelo de admisión, sin prometer un
laboratorio estable ni un entorno contractual garantizado.

## 4. Por qué la reserva aparente cambia

```
231.633.457.152 (26-jul) − 230.772.285.440 (forense) = 861.171.712 B
```

La diferencia `f_bfree − f_bavail` no es contenido: es la **reserva de
ext4**. Esta sesión lo demuestra para sí misma con el superbloque legible:

| Observación de esta sesión | Valor |
|---|---|
| `f_bfree − f_bavail` | 56.340.890 bloques = 230.772.285.440 B |
| `Reserved block count` del superbloque | 56.336.794 bloques |
| Residual | 4.096 bloques = 16.777.216 B |
| Opciones de montaje | `rw,relatime,resuid=65534,resgid=65534` |

El residual de 4.096 bloques es consistente con los clusters que el kernel
ext4 reserva para *delayed allocation* (`s_resv_clusters`, 4.096 por
defecto). La diferencia observada hoy coincide además byte a byte con la
reserva aparente del informe forense. Para la sesión del 26-jul **no puede
demostrarse al 100 % retrospectivamente** porque su superbloque ya no
existe; la anomalía no se atribuye a `.venv` ni a contenido ordinario, no
se oculta y no se modela como cuota fija entre sesiones.

## 5. Proveniencia: qué es evidencia primaria y qué no

| Sesión | Etiqueta | ¿Primaria? |
|---|---|---|
| 26-jul (TOL-207 v0.1) | `MEDICION_VERSIONADA_HISTORICA` | Sí — versionada en el repositorio |
| Revisión forense | `INFORME_FORENSE_NO_VERSIONADO` | **No** — nunca se presenta como captura independiente versionada |
| Este paquete | `MEDICION_PAQUETE_04` | Sí — `captura_cruda` del JSON |

La auditoría independiente añadirá una cuarta observación en otro
contenedor; no se versiona en este commit.

## 6. Aritmética exacta

Todas las cifras normativas son enteros en bytes; el validador y las
pruebas las recalculan, nunca se duplican a mano:

```
RESERVA_SEGURIDAD   = 31.304.323.072 // 2                = 15.652.161.536
SUELO_ADMISION      = 15.652.161.536 + 6.442.450.944
                      + 8.589.934.592                    = 30.684.547.072
HOLGURA_AGREGADO    = 8.589.934.592 − 5 × 1.610.612.736  =    536.870.912
MARGEN_SOBRE_E_MIN  = 31.304.323.072 − 30.684.547.072    =    619.776.000
```

Porcentajes sobre `E_MIN_HISTORICO` (half-up, dos decimales): candidato
5,15 % · agregado 27,44 % · seguridad 50,00 % · operativa 20,58 % · total
reservado 70,58 % · margen 1,98 %.

## 7. Admisión de esta sesión

```
f_bavail × f_frsize = 7.624.988 × 4.096 = 31.231.950.848 B
31.231.950.848 ≥ 30.684.547.072  →  ADMITIDA
```

Margen sobre el suelo: **547.403.776 B**. Repositorio y temporales
comparten filesystem (`st_dev` idéntico); inodos disponibles: 16.609.465.
Si la sesión hubiera quedado bajo el suelo, el resultado habría sido
`VALOR_NO_RECOMENDABLE_AUN` sin crear archivos ni hacer commit.

## 8. Objeto contabilizado y pico

La unidad primaria de consumo es **`st_blocks × 512`**; `st_size` se
registra pero no es consumo. Un inode físico cuenta una vez (hard links no
duplican); las copias físicas distintas cuentan cada una. El presupuesto
por candidato se aplica al **máximo simultáneo** durante reposo,
construcción, reconstrucción, borrado, purga y VACUUM, incluidos WAL, SHM,
journal, temporales, spills, índice viejo y nuevo coexistentes y copia de
VACUUM.

El anexo de pico implementa: muestreador de 5 ms en hilo dedicado con
intervalos reales registrados; checkpoints síncronos; doble contabilidad
global/inventario contra una **banda de ruido observada** en ventana
inactiva (nunca inventada); cota determinista `viejo + nuevo`; publicación
del mayor valor válido; y `NO_EVALUABLE` para operaciones más rápidas que
la observación. En la demostración ejecutada, el muestreador capturó un
pico de 8.392.704 B con doble contabilidad exacta (diferencia no explicada:
0 B).

## 9. Reserva operativa: demostración

| Partida | Tipo | Medido hoy (B) | Asignación máx. (B) |
|---|---|---|---|
| Repositorio sin `.git`/`.venv` | medida | 65.671.168 | 134.217.728 |
| `.git` | medida | 4.485.120 | 134.217.728 |
| `.venv` | medida | 839.802.880 | 1.610.612.736 |
| Corpus congelado | medida · no se suma dos veces | 3.751.936 | — |
| Base canónica | pendiente | 0 | 536.870.912 |
| Copias limpias del ciclo | asignación | 0 | 1.073.741.824 |
| Artefactos, informes, logs, resultados | medida | 450.560 | 536.870.912 |
| Checkpoints y snapshots | asignación | 0 | 536.870.912 |
| Modelos locales compartidos | asignación | 0 | 1.073.741.824 |
| Temporales comunes | asignación | 0 | 536.870.912 |
| **Suma de asignaciones** | | | **6.174.015.488** |

**6.174.015.488 ≤ 6.442.450.944** ✔ · margen restante **268.435.456 B** ·
medido actualmente en total: 910.409.728 B. Nada medido se presenta como
asignación ni al revés. Los modelos locales compartidos no consumen
presupuesto individual, se cuentan físicamente una vez y se declararán en
la ficha TOL-210.

## 10. Denominador y escalas

`UNIDADES_LOGICAS_PRIMARIAS = 5.670` (550 items estructurados + 5.000
mensajes + 120 documentos), definido sobre el corpus congelado y verificado
contra él elemento a elemento; no es modificable por candidato. Las 180
relaciones y 24 entidades son numerador, no denominador. Solo
`bytes_por_unidad_logica_primaria` es la comparación normativa común.

Escalas de medición directa 500/5.000/5.670 derivadas por resto mayor con
redondeo determinista (48/441/11, 485/4.409/106 y corpus completo),
identificables por IDs y sin modificar el corpus congelado. La escala
50.000 es **siempre `PROYECTADO`**; el contrato exige fijar modelo de
crecimiento, métrica de ajuste, tolerancia de residuo y cota superior
conservadora **antes** de medir cada candidato, con salida `NO_EVALUABLE`
si el crecimiento no se modela con la regla prefijada.

## 11. Neutralidad y poder discriminante

El presupuesto es absoluto en bytes y común: no preselecciona dimensión,
precisión, cuantización ni representación (TOL-104A). Las sondas
caracterizan el sustrato físico (sparse sí, reflink/COW no, compresión no)
para que ningún candidato dependa de semánticas no verificadas. El poder
discriminante en laboratorio **sigue siendo limitado**: la línea base
completa ocupa el 0,02 % del presupuesto por candidato; lo que discriminará
es el crecimiento no acotado y la mejora material (§5.1 criterios 2 y 7), y
la restricción vinculante del producto pertenece a **TOL-205** (Windows),
aún sin fijar.

## 12. Relación con otras tolerancias

TOL-104A (escala común con % del presupuesto absoluto) · TOL-203 (copias
del ciclo en la reserva operativa) · TOL-205 (reverificación Windows; nada
se traslada) · TOL-206 (purga sobre los mismos objetos contabilizados) ·
TOL-208 (denominador sobre el corpus congelado por el acta v0.4) · TOL-209
(el anexo de pico complementa, no modifica, el protocolo común) · TOL-210
(la ficha declarará consumo, porcentaje y modelos compartidos).

## 13. Limitaciones

1. El superbloque del 26-jul no es recuperable: la anomalía solo se
   demuestra al 100 % para la sesión actual.
2. El muestreador convive con el GIL de CPython; gobierna el intervalo
   real observado, no el solicitado.
3. La granularidad de observación de `f_bavail` es 4.096 B.
4. El proceso corre como root y podría asignar bloques reservados; la
   envolvente cuenta solo `f_bavail` (cifra conservadora).
5. El entorno es una cuota por sesión compartida; el margen sobre el suelo
   de esta sesión (547 MB) depende del propio utillaje (`.venv`, caches).
6. La medición del repositorio incluye caches de herramientas presentes en
   el árbol; son parte honesta del consumo de la sesión.

## 14. Resultado de las pruebas

| Comprobación | Resultado |
|---|---|
| `experiments/adr002/storage/` (puerta y 36 negativas) | **93/93 PASS** |
| v0.3 + v0.4 + tolerances sobre el árbol real | **144/144 PASS** |
| pytest completo `experiments/adr002/` en copia temporal (incluye validadores mutantes v0.1/v0.2, nunca sobre el árbol real) | **358/358 PASS** |
| `ruff format --check .` | 289 ficheros conformes |
| `ruff check .` | sin hallazgos |
| `mypy src tests` (contrato del repositorio) | 236 ficheros sin errores |
| `mypy --explicit-package-bases experiments/adr002/storage` (estricto) | 6 ficheros sin errores |
| Validador del JSON (`fallos_entorno_lab`) | 0 fallos |
| Regeneración desde la captura fija | byte a byte idéntica |
| Validar no muta artefactos | SHA-256 idéntico antes/después |
| Siete blobs congelados + SHA-256 + blob T0 | intactos |

## 15. Estado final

**`ADR002-TOL-207` continúa NO SATISFECHA.**
**PROPUESTA v0.2 LISTA PARA AUDITORÍA INDEPENDIENTE.**

Este informe no aprueba la tolerancia, no crea acta, no ejecuta T0, no
implementa candidatos y no propone iniciar el benchmark.

---

**Siguiente movimiento único:** auditoría adversarial independiente del
paquete 04 en otro contenedor, con su propia observación del entorno.
