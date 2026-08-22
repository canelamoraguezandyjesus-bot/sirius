# SIRIUS 0.2 — ADR-002 · TOL-207 · Presupuesto absoluto de almacenamiento

**Versión:** 0.2
**Estado:** **PROPUESTO · PENDIENTE DE AUDITORÍA INDEPENDIENTE**
**Fecha:** 27 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_TOL_207_PRESUPUESTO_ALMACENAMIENTO_v0.1_PROPUESTO.md`, que se conserva sin modificar
**Alcance:** **LAB-LINUX** · **no es aceptación Windows**
**Exigido por:** `ADR002-TOL-207` del Registro v0.4, aprobado por `SIRIUS_0.2_ADR_002_REGISTRO_TOLERANCIAS_APROBACION_v1.0.md`
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_04_TOL207_CARACTERIZACION_v0.1.md`
**Evidencia legible por máquina:** `artifacts/adr002_storage/entorno_lab_v0.1.json`
**Código:** `experiments/adr002/storage/`
**No autoriza:** ejecutar T0 ni T1–T4, implementar candidatos, aprobar esta tolerancia ni merge. `ADR002-TOL-207` continúa **NO SATISFECHA**.

---

## 0. Qué corrige esta versión

La v0.1 fijó el método correcto —derivar todo de `f_bavail` medido— pero no
era aprobable. Defectos corregidos:

| # | Defecto de la v0.1 | Corrección v0.2 |
|---|---|---|
| 1 | Reserva de seguridad **15.652.167.680 B** («50 %») con error de **+6.144 B** | El 50 % exacto de 31.304.323.072 es **15.652.161.536 B**. La cifra v0.1 queda retirada como error histórico |
| 2 | Suelo **30.684.553.216 B** arrastraba el mismo error de **+6.144 B** | Suelo exacto **30.684.547.072 B**, suma entera de sus tres partidas |
| 3 | Porcentaje agregado publicado como **27,43 %** | 8.589.934.592 ÷ 31.304.323.072 = 27,4401… % → redondeo correcto **27,44 %** |
| 4 | El entorno se presentaba como una máquina estable implícita | Clasificación **`ENVOLVENTE_REPRODUCIBLE`**: huella estable verificable más campos efímeros por contenedor |
| 5 | Sin regla de admisión operativa ni condición de aborto | Suelo de admisión con fórmula fija y salida `VALOR_NO_RECOMENDABLE_AUN` |
| 6 | Sin separación de proveniencia entre sesiones | Tres proveniencias etiquetadas; la evidencia forense no versionada nunca se presenta como primaria |
| 7 | La reserva aparente del dispositivo variaba entre sesiones sin explicación registrada | Anomalía de 861.171.712 B documentada y demostrada para la sesión actual |
| 8 | Sin objeto contabilizado definido | Unidad primaria **`st_blocks × 512`**; `st_size` se registra pero no es consumo |
| 9 | Sin protocolo de pico ni doble contabilidad | Anexo de pico con muestreador, checkpoints, banda de ruido observada y `NO_EVALUABLE` |
| 10 | «Elementos» sin denominador normativo cerrado | **5.670 unidades lógicas primarias**, no modificable por candidato |

**Qué conserva de la v0.1:** el principio de que la única cifra que gobierna
es `f_bavail` confirmada por escritura real; los presupuestos de 1,5 GiB por
candidato y 8 GiB agregados; la reserva operativa de 6 GiB; la advertencia de
que `df` induce a error; el alcance LAB-LINUX y la relación con TOL-205.

---

## 1. Clasificación del entorno: `ENVOLVENTE_REPRODUCIBLE`

El laboratorio **no es una máquina estable**: cada sesión corre en un
contenedor efímero con su propio hostname, machine-id, boot-id y `f_fsid`, y
la disponibilidad por sesión varía. Lo reproducible es la **envolvente**: la
geometría y semántica del filesystem más el suelo de admisión.

No se usan las etiquetas `LABORATORIO_ESTABLE`, «presupuesto APROBADO»,
«TOL-207 SATISFECHA» ni «entorno contractual garantizado».

### 1.1 Huella estable propuesta

| Campo | Valor | Confirmado por la captura actual |
|---|---|---|
| Filesystem | ext4 | sí |
| `f_frsize` | 4.096 | sí |
| `f_blocks` (statvfs) | 66.053.021 | sí |
| Tamaño total | 270.553.174.016 B | sí |
| Montaje | lectura/escritura | sí |
| Bloques reservados | mecanismo observable | sí |
| Inodos totales | 16.777.216 | sí |
| Arquitectura | x86_64 | sí |
| SO mayor | Ubuntu 24.04 | sí |
| Suelo de admisión | 30.684.547.072 B | sí |

### 1.2 Campos efímeros

Registrados pero **no exigidos idénticos** entre contenedores: hostname,
machine-id, boot-id, parche exacto del kernel y `f_fsid`.

`f_fsid` y `st_dev` sirven para comprobar que repositorio, temporales y
objetos medidos pertenecen al **mismo filesystem dentro de una sesión**. Un
contenedor válido **no se rechaza** únicamente por tener otro `f_fsid`.

### 1.3 Admisión de una sesión futura

Una sesión es admisible cuando: coincide con la geometría y semántica
estable; repositorio y temporales comparten filesystem; supera el suelo; las
sondas de asignación reproducen el comportamiento esperado; tiene inodos
suficientes; y no presenta compresión, COW ni cuotas ocultas incompatibles.

---

## 2. Constantes exactas

La identidad obligatoria es el **número de bytes**. Los GiB son
exclusivamente informativos.

| Constante | Bytes | Informativo |
|---|---|---|
| `E_MIN_HISTORICO` | **31.304.323.072** | `f_bavail` de la sesión del 26-jul (v0.1) |
| `PRESUPUESTO_POR_CANDIDATO` | **1.610.612.736** | 1,5 GiB |
| `PRESUPUESTO_AGREGADO` | **8.589.934.592** | 8 GiB |
| `RESERVA_SEGURIDAD` | **15.652.161.536** | 50 % exacto de `E_MIN_HISTORICO` |
| `RESERVA_OPERATIVA` | **6.442.450.944** | 6 GiB exactos |
| `SUELO_ADMISION` | **30.684.547.072** | suma exacta de las tres partidas |
| `HOLGURA_AGREGADO` | **536.870.912** | 8.589.934.592 − 5 × 1.610.612.736 |
| `MARGEN_SUELO_SOBRE_E_MIN` | **619.776.000** | 31.304.323.072 − 30.684.547.072 |

Porcentajes sobre `E_MIN_HISTORICO`, recalculados con redondeo half-up a dos
decimales: por candidato **5,15 %** · agregado **27,44 %** · reserva de
seguridad **50,00 %** · reserva operativa **20,58 %** · total reservado
**70,58 %** · margen no asignado **1,98 %**.

### 2.1 Cifras retiradas — errores históricos de la v0.1

| Cifra retirada | Error | Vigente |
|---|---|---|
| Reserva de seguridad 15.652.167.680 B | **+6.144 B** | 15.652.161.536 B |
| Suelo 30.684.553.216 B | **+6.144 B** | 30.684.547.072 B |
| Porcentaje agregado 27,43 % | redondeo incorrecto | 27,44 % |

Las cifras retiradas no aparecen como vigentes en código, tablas ni
cálculos; el validador de la evidencia las rechaza expresamente.

---

## 3. Regla de admisión y aborto

Antes de producir la evidencia versionada se captura el entorno actual. Si

```
f_bavail × f_frsize < 30.684.547.072
```

entonces: no se rebaja ninguna reserva ni presupuesto, no se cambia la
fórmula, se genera únicamente un diagnóstico temporal fuera del repositorio,
no se crean los archivos del paquete, no se hace commit y se entrega
**`VALOR_NO_RECOMENDABLE_AUN`** por sesión bajo el suelo.

También se detiene sin commit si: la reserva operativa real necesaria supera
6.442.450.944 B; el filesystem no permite contabilización fiable; la captura
no puede hacerse atómicamente; las sondas no pueden limpiarse; el
repositorio y el directorio temporal de sondas están en filesystems
distintos; o no puede demostrarse que los siete blobs congelados siguen
intactos.

**Resultado de esta sesión:** suelo superado; sesión **ADMITIDA**. Los
valores exactos están en `admision_sesion` de la evidencia JSON.

---

## 4. Proveniencia de sesiones y anomalía de reserva

### 4.1 Tres proveniencias separadas

| Etiqueta | Fuente | ¿Evidencia primaria? |
|---|---|---|
| `MEDICION_VERSIONADA_HISTORICA` | TOL-207 v0.1 (26-jul): `f_bfree` 262.937.780.224 · `f_bavail` 31.304.323.072 · reserva aparente 231.633.457.152 | **Sí** — versionada |
| `INFORME_FORENSE_NO_VERSIONADO` | sesiones previas de revisión: `f_bfree` ≈ 262.930.505.728 · `f_bavail` ≈ 32.158.220.288 · reserva aparente 230.772.285.440 | **No** — no se presenta como captura independiente versionada |
| `MEDICION_PAQUETE_04` | captura producida ahora por `environment_capture.py` | **Sí** — versionada en este paquete |

La futura auditoría independiente añadirá otra observación en un contenedor
diferente; no se versiona en este commit.

### 4.2 Anomalía de reserva

```
231.633.457.152 − 230.772.285.440 = 861.171.712 B
```

Explicación admitida: la diferencia `f_bfree − f_bavail` refleja los
**bloques reservados y la configuración de ext4**. La captura actual lo
demuestra para su propia sesión: el superbloque es legible
(`reserved_block_count` = 56.336.794 bloques, `resuid/resgid` = 65534 en las
opciones de montaje) y la diferencia observada `f_bfree − f_bavail` cuadra
con esa reserva más un residual de 4.096 bloques consistente con los
clusters que el kernel ext4 reserva para *delayed allocation*
(`s_resv_clusters`, 4.096 por defecto). **No puede demostrarse al 100 %
retrospectivamente** para la sesión del 26-jul porque su superbloque ya no
está disponible. La anomalía **no se atribuye** a `.venv` ni a contenido
ordinario, **no se oculta** y **no se usa** una cuota fija entre sesiones.

---

## 5. Objeto contabilizado

Unidad primaria de consumo: **`st_blocks × 512`** (bloques asignados
físicamente). `st_size` se registra siempre, pero **no** se usa como
almacenamiento consumido: un fichero sparse aparenta más de lo que asigna.

Un inode físico se cuenta **una vez**: los hard links al mismo inode no
duplican consumo. Las copias físicas distintas **sí** cuentan cada una.

---

## 6. Presupuesto por candidato: 1.610.612.736 B

Se aplica al **máximo simultáneo** de todos los objetos atribuibles al
candidato durante **reposo, construcción, reconstrucción, borrado, purga y
VACUUM**. Incluye: índices léxicos, semánticos y relacionales; tablas
sombra; embeddings; metadatos; caches persistentes; WAL; SHM; journal;
temporales; spills; ficheros intermedios; índice viejo y nuevo coexistentes;
copia de VACUUM; cualquier representación reversible derivada del canon; y
escrituras en rutas externas atribuibles al candidato.

Un candidato que supere su presupuesto individual queda **descartado**
(§5.1 criterio 3 del Registro v0.4, puerta 7) aunque el agregado tenga
espacio.

---

## 7. Techo agregado: 8.589.934.592 B

Instanciación operativa **LAB-LINUX** —no es mandato canónico—: los
derivados de T0 y `ADR002-A/B/C/D` pueden mantenerse residentes para evitar
reconstrucciones repetidas entre bloques intercalados. Solo se permite **una
operación pesada simultánea**; el agregado instantáneo se calcula como
residentes en reposo más el único pico activo. **Exceder el agregado
invalida la sesión** de medición, pero no descarta automáticamente a un
candidato individual. La holgura sobre cinco candidatos es 536.870.912 B.

---

## 8. Reserva operativa: 6.442.450.944 B

Contiene y mide de forma desglosada: repositorio; `.git`; `.venv`; corpus
congelado; base canónica cuando exista; copias limpias necesarias;
artefactos; informes; logs; resultados; checkpoints; snapshots; modelos
locales compartidos; y temporales comunes no atribuibles a un candidato.

**Modelos locales:** no son derivados regenerables desde el canon; **no**
consumen presupuesto individual; **sí** consumen reserva operativa; se
cuentan físicamente una sola vez si son compartidos; deberán declararse en
la ficha TOL-210.

### 8.1 Demostración aritmética del plan

Como T0 y los candidatos todavía no existen, el plan separa **bytes medidos
actualmente** (asignados por inode, `st_blocks × 512`), **asignaciones
máximas prefijadas** y **partidas pendientes**. Nada medido se presenta como
asignación ni al revés.

| Partida | Tipo | Asignación máxima (B) |
|---|---|---|
| Repositorio (sin `.git` ni `.venv`) | medida | 134.217.728 |
| `.git` | medida | 134.217.728 |
| `.venv` | medida | 1.610.612.736 |
| Corpus congelado | medida · dentro del repositorio, no se suma dos veces | — |
| Base canónica (pendiente; T0 no se ejecuta aquí) | pendiente | 536.870.912 |
| Copias limpias del ciclo (TOL-105/TOL-203) | asignación | 1.073.741.824 |
| Artefactos, informes, logs y resultados | medida | 536.870.912 |
| Checkpoints y snapshots | asignación | 536.870.912 |
| Modelos locales compartidos | asignación | 1.073.741.824 |
| Temporales comunes no atribuibles | asignación | 536.870.912 |
| **Suma de asignaciones máximas** | | **6.174.015.488** |
| **Margen restante** | | **268.435.456** |

**6.174.015.488 ≤ 6.442.450.944** ✔ — el plan cabe en 6 GiB con 256 MiB de
margen. Los bytes medidos de cada partida están en la evidencia JSON y todos
caben en su asignación. Si el plan completo no cupiera, no se robaría
espacio de la reserva de seguridad ni se reduciría el agregado: el resultado
sería `VALOR_NO_RECOMENDABLE_AUN` sin commit.

---

## 9. Denominador normativo

```
UNIDADES_LOGICAS_PRIMARIAS = 5.670
```

Definición: **objeto recuperable portador de contenido del corpus de
rendimiento congelado**. Se define sobre el corpus, **no** sobre los objetos
que cada candidato decida indexar, y no es modificable por candidato.

| Colección | Recuento |
|---|---|
| Items estructurados (500 memorias + 50 decisiones) | 550 |
| Mensajes | 5.000 |
| Documentos | 120 |
| **Total** | **5.670** |

Las **180 relaciones** y **24 entidades** son cargas estructurales: forman
parte del **numerador** de consumo, pero **no** del denominador primario.

Se reportan: `bytes_por_unidad_logica_primaria`,
`bytes_por_item_estructurado`, `bytes_por_mensaje`, `bytes_por_documento`,
`bytes_por_relacion` y `bytes_por_entidad`. Solo
**`bytes_por_unidad_logica_primaria`** es la comparación normativa común.

---

## 10. Escalas

**Medición directa:** 500 · 5.000 · 5.670 (corpus completo) unidades
lógicas primarias. Los subconjuntos se derivan **sin modificar el corpus
congelado**, son deterministas, identificables por IDs y preservan las
proporciones de colecciones mediante **reparto por resto mayor** (cuota de
Hare) con empates resueltos por orden fijo y redondeo determinista:

| Escala | Items (MEM/DEC) | Mensajes | Documentos |
|---|---|---|---|
| 500 | 48 (44/4) | 441 | 11 |
| 5.000 | 485 (441/44) | 4.409 | 106 |
| 5.670 | 550 (500/50) | 5.000 | 120 |

La selección dentro de cada colección toma los primeros elementos en orden
canónico ascendente de ID (`MEM-P-00001…`, `DEC-P-00001…`, `MSG-P-00001…`,
`DOC-P-001…`).

**Proyección:** 50.000 unidades, **siempre etiquetada `PROYECTADO`**, nunca
`MEDIDO` salvo que una versión futura materialice esa escala. Antes de medir
un candidato deberá fijarse: modelo de crecimiento, métrica de ajuste,
tolerancia de residuo y cota superior conservadora. Si el crecimiento no
puede modelarse con la regla prefijada: **`NO_EVALUABLE`**. Este paquete
define el contrato, no rellena resultados de candidatos inexistentes.

---

## 11. Matriz fija de aceptación

Bloquea TOL-207 cualquiera de:

1. límite sin bytes exactos;
2. sesión sin huella verificable;
3. suelo no comprobado;
4. derivado, sidecar, temporal o pico omitido;
5. denominador ambiguo o modificable por candidato;
6. pico publicado sin resolución válida;
7. reserva invadida o insuficiente;
8. sesgo tecnológico material;
9. sparse/COW/compresión sin caracterizar;
10. admisión sin captura legible por máquina;
11. aritmética incoherente;
12. evidencia sin proveniencia;
13. anomalía ocultada;
14. operación más rápida que la observación sin `NO_EVALUABLE`;
15. co-residencia presentada como canon;
16. valores modificados después de observar candidatos.

Todo lo demás se clasifica como `CORRECCION_NO_BLOQUEANTE`,
`LIMITACION_CONOCIDA` o `TRABAJO_POSTERIOR`.

---

## 12. Poder discriminante y relación con otras tolerancias

El presupuesto sigue siendo generoso y **discrimina poco en laboratorio**;
lo que separará candidatos es el crecimiento no acotado y la ausencia de
mejora material (§5.1 criterios 2 y 7). La restricción vinculante del
producto pertenece a **TOL-205** sobre Windows y no está fijada.

| Tolerancia | Relación |
|---|---|
| TOL-104A | escala común obligatoria: % del presupuesto absoluto de TOL-207 |
| TOL-203 | límites de ciclo por magnitud; las copias del ciclo viven en la reserva operativa |
| TOL-205 | reverificación obligatoria en Windows; este presupuesto no se traslada |
| TOL-206 | la purga física opera sobre los mismos objetos contabilizados (`-wal`, `-shm`, `-journal`) |
| TOL-208 | denominador y escalas definidos sobre el corpus congelado por su acta v0.4 |
| TOL-209 | el anexo de pico no modifica el protocolo común; lo complementa para bytes/inodos |
| TOL-210 | la ficha de candidato declarará consumo, % del presupuesto y modelos compartidos |

---

## 13. Estado y qué desbloquea

| Puerta | Estado tras este paquete |
|---|---|
| `SRC-ADR002-01` | **SATISFECHA** |
| **`ADR002-TOL-207`** | **NO SATISFECHA — PROPUESTA v0.2 PENDIENTE DE AUDITORÍA INDEPENDIENTE** |
| `ADR002-TOL-208` paso 1 | **COMPLETADO** — corpus congelado |
| `ADR002-TOL-208` global | **NO SATISFECHA** |
| `ADR002-TOL-209` | **NO SATISFECHA** |
| `ADR002-TOL-210` | **NO SATISFECHA** |

Este paquete **no aprueba TOL-207** y no crea acta de aprobación. El
benchmark sigue bloqueado.

---

**Siguiente movimiento único:** auditoría adversarial independiente de esta
propuesta en otro contenedor, con su propia captura de entorno, antes de
cualquier decisión del usuario sobre TOL-207.
