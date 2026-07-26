# SIRIUS 0.2 — ADR-002 · TOL-207 · Presupuesto absoluto de almacenamiento

**Versión:** 0.1
**Estado:** **PROPUESTO** · requiere aprobación explícita del usuario
**Fecha:** 26 de julio de 2026
**Alcance:** **LAB-LINUX** · **no es aceptación Windows**
**Exigido por:** `ADR002-TOL-207` del `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md`, aprobado el 26 de julio de 2026
**No autoriza:** ejecutar T0 ni T1–T4, implementar candidatos, elegir realización técnica ni merge.

---

## 0. Qué es esta fila y por qué hace falta

La v0.2 del Registro tenía dos techos de almacenamiento: el ratio `≤ ×4,0 / ×8,0` por índice y el agregado «derivados ≤ 50 % del fichero». La v0.3 retiró el primero para los índices no léxicos —era una cifra de FTS5 aplicada a vectores— y la v0.4 confirmó la retirada del segundo, porque un porcentaje del canon penaliza corpus de texto corto sin relación con la calidad del diseño.

**El resultado fue un vacío**: sin ninguno de los dos, el criterio 3 del §5.1 del Registro —«no cabe en el entorno local de referencia»— quedaba inerte, y el almacenamiento dejaba de discriminar en la puerta 7. `TOL-207` es el único techo operativo que queda, y por eso es **puerta de arranque**: sin él, el benchmark no puede comenzar.

**Regla de método aplicada:** no se ha fijado ninguna cifra antes de medir. Todo el §1 es medición directa del entorno; el §2 deriva la propuesta de esas mediciones.

---

## 1. Medición del entorno de laboratorio

Medido el 26 de julio de 2026 sobre el entorno que ejecutará el benchmark. Ninguna cifra es estimada.

### 1.1 Sistema de ficheros

| Magnitud | Valor medido | Método |
|---|---|---|
| Dispositivo y tipo | `/dev/vda`, **ext4**, montado en `/` | `df -PT` |
| Tamaño total del sistema de ficheros | **270.553.174.016 B** (252,0 GiB) | `statvfs.f_blocks × f_frsize` |
| Espacio libre bruto del dispositivo | 262.937.780.224 B | `statvfs.f_bfree × f_frsize` |
| **Espacio disponible para el proceso** | **31.304.323.072 B** (**29,15 GiB**) | `statvfs.f_bavail × f_frsize` |
| Escritura real verificada | 67.108.864 B escritos y borrados, sin error | sonda `dd` de 64 MiB |

**Advertencia de método.** El «libre» del dispositivo (262 GB) **no es utilizable**: este entorno aplica una cuota de escritura por sesión, y `df` induce a error. La única cifra que gobierna es **`f_bavail` = 31.304.323.072 B**, confirmada por una escritura real. Toda la propuesta se deriva de ella, no del tamaño del disco.

### 1.2 Ocupación actual

| Elemento | Bytes medidos |
|---|---|
| Árbol de trabajo del repositorio, sin `.venv` | **7.032.692** |
| `.git` | 2.550.849 |
| Contenido versionado (412 ficheros) | 3.990.571 |
| `experiments/` | 713.773 |
| `experiments/adr002/benchmark/` (corpus, casos, referencias y código) | 476.560 |
| `artifacts/` | 231.261 |
| `docs/architecture/canonical_sources/` | 285.026 |
| `.venv` (no versionado, en `.gitignore`, recreable) | 813.283.526 |

### 1.3 Derivados experimentales existentes

| Elemento | Bytes medidos | Origen |
|---|---|---|
| **Índices derivados de la línea base FTS5** | **364.544** | `mediciones_linea_base_v0.2.json` → `E-TAMANO` |
| `knowledge_fts` y sus sombras | 122.880 | ídem |
| `message_fts` y sus sombras | 241.664 | ídem |
| Fichero completo de la línea base | 1.462.272 | ídem |
| Derivados sobre el fichero | 24,93 % | ídem |
| Ficheros `.db`/`.sqlite` residentes hoy | **ninguno** | `find` |

**Densidad léxica medida:** `knowledge_fts` cubre 549 elementos vigentes (499 memorias + 50 decisiones) en 122.880 B → **223,83 B por elemento**. Es la única densidad medida que existe; no hay ninguna para índices semánticos ni relacionales.

---

## 2. Propuesta de presupuesto

### 2.1 Cifra propuesta

| Nivel | Presupuesto | Bytes | % del disponible |
|---|---|---|---|
| **Por candidato** — suma de **todos** sus derivados sobre el corpus congelado | **1,5 GiB** | **1.610.612.736** | **5,15 %** |
| **Agregado** — todos los candidatos co-residentes (T0 + T1–T4) | **8 GiB** | **8.589.934.592** | **27,43 %** |

### 2.2 Fundamento y derivación

Se parte de los 31.304.323.072 B disponibles y se reserva antes de asignar:

| Concepto | Bytes | Razón |
|---|---|---|
| **Reserva de seguridad intocable** | 15.652.167.680 (50 %) | La cuota es por sesión y compartida con el sistema, los registros y cualquier otro proceso. **No se usa todo el espacio libre**: la mitad no se asigna en absoluto |
| **Reserva operativa** | 6.442.450.944 (6 GiB) | `.venv` recreable (0,81 GB medidos), repositorio y `.git`, artefactos y evidencia de ejecución, y **copias limpias del ciclo**: TOL-105 y TOL-203 exigen ≥30 repeticiones, cada una sobre una copia independiente |
| **Presupuesto asignable a derivados** | 8.589.934.592 (8 GiB) | Lo que queda, redondeado a la baja |
| **Suma** | 30.684.553.216 | ≤ 31.304.323.072 disponibles ✔ |

El reparto por candidato sale del agregado: **1,5 GiB × 5 candidatos (T0 + T1–T4) = 8.053.063.680 B ≤ 8.589.934.592 B**. Encaja con 536 MB de holgura.

**Por qué 1,5 GiB y no menos.** Es el orden de magnitud que un candidato de T1–T4 puede necesitar de forma legítima a la escala máxima proyectada, sin preseleccionar dimensión, precisión ni cuantización: cualquier configuración razonable de índice semántico más un índice léxico más un índice relacional cabe holgadamente. Poner menos equivaldría a fijar un techo técnico encubierto, que es exactamente lo que TOL-104A prohíbe.

**Por qué no más.** Porque un presupuesto que nadie pueda superar no es un presupuesto. 1,5 GiB es ~4.400 veces el tamaño completo de los derivados medidos hoy: quien lo agote tendrá que explicarlo, y el §5.1 criterio 7 —«el coste adicional no produce mejora material»— se aplica igual.

### 2.3 Margen reservado

| Reserva | Bytes | % del disponible |
|---|---|---|
| Seguridad intocable | 15.652.167.680 | **50,00 %** |
| Operativa (repo, artefactos, evidencia, copias del ciclo, `.venv`) | 6.442.450.944 | 20,58 % |
| **Total reservado** | **22.094.618.624** | **70,58 %** |
| Asignado a derivados del benchmark | 8.589.934.592 | 29,42 % |

**Se reserva más del doble de lo que se asigna.** Ningún candidato puede tocar el 70,58 % reservado.

### 2.4 Escala común de proyección — obligatoria para todo candidato

Todo candidato reporta estas cuatro magnitudes a los tres tamaños, en la ficha de candidato (`ADR002-TOL-210`):

| Magnitud | 500 elementos | 5.000 elementos | 50.000 elementos |
|---|---|---|---|
| Bytes totales de los derivados | *a declarar* | *a declarar* | *a declarar* |
| Bytes por elemento | *a declarar* | *a declarar* | *a declarar* |
| % del presupuesto por candidato (1,5 GiB) | *a declarar* | *a declarar* | *a declarar* |
| % del presupuesto agregado (8 GiB) | *a declarar* | *a declarar* | *a declarar* |

**Única proyección que este documento puede rellenar hoy**, por extrapolación lineal de la densidad medida de 223,83 B/elemento del sustrato léxico FTS5:

| | 500 | 5.000 | 50.000 |
|---|---|---|---|
| Sustrato léxico FTS5, bytes | 111.913 | 1.119.126 | 11.191.257 |
| % del presupuesto por candidato | 0,007 % | 0,069 % | 0,695 % |

**Esta fila es extrapolación lineal de una medición, no una medición a esas escalas.** El escalado real de FTS5 no tiene por qué ser lineal.

**Para índices semánticos y relacionales no se rellena ninguna casilla.** No existe ninguna medición: `ADR002-TOL-104A` lo dice expresamente —«Dato observado: **Ninguno**»— y este documento **no inventa** una proyección aritmética que pareciera evidencia. Las casillas las rellena cada candidato antes de ejecutarse.

### 2.5 Consecuencia de superar el presupuesto

| Situación | Consecuencia |
|---|---|
| Un candidato supera **su** presupuesto de 1,5 GiB sobre el corpus congelado | **Descarta por la puerta 7**, vía §5.1 criterio 3 del Registro v0.4 |
| El conjunto co-residente supera los 8 GiB agregados | **La ejecución no es válida**: no se descarta a nadie, se libera espacio y se repite conforme al protocolo (`ADR002-TOL-209`) |
| Un candidato supera el límite que **él mismo** declaró y congeló, aun cabiendo en 1,5 GiB | **Descarta por la puerta 7**, vía §5.1 criterio 1 |
| Crecimiento no acotado o no explicable dentro del presupuesto | **Descarta**, vía §5.1 criterio 2 |
| Ajustar el presupuesto **después** de observar resultados | Prohibido por el §9 regla 1 del Registro. Cambiarlo obliga a **repetir** todas las comparaciones ya ejecutadas (§9 regla 10) |

**El presupuesto es común y no lo elige el candidato.** `TOL-104A` deja que cada uno declare *su propio límite*, que puede ser **más estricto** que 1,5 GiB pero **nunca más laxo**. Los dos techos son acumulativos: se incumple el que se incumpla primero.

### 2.6 Alcance: LAB-LINUX, no aceptación Windows

Esta cifra es **exclusivamente del laboratorio comparativo Linux**. Sirve para comparar T1–T4 entre sí en el mismo entorno, y solo para eso.

**No es, ni se aproxima a, el presupuesto del equipo del usuario.** Cuánto puede ocupar Sirius en la máquina de una persona es una restricción distinta, pertenece a **`ADR002-TOL-205`** y debe congelarse antes de aceptar la implementación productiva, junto con `secure_delete`, el tokenizador y la secuencia de purga que ADR-001 dejó pendientes.

Presentar los 1,5 GiB de laboratorio como si fueran presupuesto de producto **invalidaría la aceptación**.

### 2.7 Observación honesta sobre el poder discriminante

**Este presupuesto es generoso y discrimina poco.** Los derivados medidos hoy ocupan 364.544 B: el 0,02 % del presupuesto por candidato. Un candidato tendría que ser ~4.400 veces mayor que la línea base completa para incumplirlo.

Eso es consecuencia honesta de la medición, no un defecto de la propuesta: **el laboratorio tiene 29 GiB y no se puede inventar una escasez que no existe**. Pero conviene decir con claridad qué significa:

1. En el laboratorio, el eje del almacenamiento **casi no separará candidatos**. Lo que separará será el crecimiento no acotado (§5.1 criterio 2) y la ausencia de mejora material (criterio 7), que son cualitativos.
2. **El presupuesto que sí morderá es el de `TOL-205`**, sobre el equipo del usuario, y todavía no está fijado.
3. Por tanto, `TOL-207` cumple su función —cerrar el vacío y hacer operativo el criterio 3— pero **no debe presentarse como la prueba de que el coste de almacenamiento es aceptable**. Esa prueba es de Windows.

**Recomendación asociada:** fijar el presupuesto de `TOL-205` cuanto antes, con el entorno de referencia real. Es previsiblemente uno o dos órdenes de magnitud menor y será el binding constraint.

---

## 3. Cómo se verifica

```
python3 -c "import os;s=os.statvfs('.');print(s.f_bavail*s.f_frsize)"   # disponible
du -sb --exclude=.venv .                                                # repositorio
du -sb experiments artifacts                                            # derivados experimentales
```

La medición se **repite y se registra** al congelar el corpus definitivo (`ADR002-TOL-208`), porque el espacio disponible del laboratorio puede haber cambiado. Si `f_bavail` cae por debajo de **22.094.618.624 B + 8.589.934.592 B = 30.684.553.216 B**, el presupuesto debe recalcularse **antes** de ejecutar, nunca después.

---

## 4. Estado y qué desbloquea

| Puerta | Estado tras esta propuesta |
|---|---|
| `SRC-ADR002-01` · fuentes canónicas | **SATISFECHA** (26 de julio de 2026) |
| **`ADR002-TOL-207` · presupuesto absoluto** | **PROPUESTA · pendiente de aprobación explícita** |
| `ADR002-TOL-208` · corpus congelado y T0 rederivada | **NO SATISFECHA** |
| `ADR002-TOL-209` · protocolo común de medición | **NO SATISFECHA** — el documento existe y está aprobado; falta congelar el umbral de conmutación y la banda absoluta de TOL-107 con el entorno |
| `ADR002-TOL-210` · ficha de candidato | **NO SATISFECHA** — la plantilla existe; no hay candidato que fichar |

Aprobar esta cifra **no** autoriza ejecutar nada. El benchmark sigue bloqueado por las tres puertas restantes.

---

**Siguiente movimiento único:** que el usuario apruebe, corrija o rechace los dos presupuestos —1,5 GiB por candidato y 8 GiB agregados— y decida si se fija ya el presupuesto de `TOL-205` sobre el entorno de referencia Windows, que es el que realmente acotará el producto.
