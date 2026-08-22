# SIRIUS 0.2 — ADR-002 · Aprobación de TOL-207

**Versión:** 1.0  
**Estado:** **APROBADO · ADR002-TOL-207 SATISFECHA**  
**Fecha:** 28 de julio de 2026  
**Rama:** `evidence/adr001-spikes`  
**Autoridad:** Usuario / Proyecto Sirius  
**Commit auditado:** `dab27dddd52cab683af762290fac01c21895d61a`  
**Commit de materialización inicial:** `ea66ceade3ed4210f666a9b82ce5beb211b2ba47`  
**Autorización explícita del usuario:** «Si venga»

## 0. Objeto

Esta acta materializa la aprobación explícita de `ADR002-TOL-207` tras:

1. la caracterización forense del entorno LAB-LINUX;
2. la auditoría adversarial de la propuesta v0.2;
3. la corrección quirúrgica del bloqueante B-1 en el instrumento de contabilidad de picos;
4. la auditoría final focalizada sobre el commit `dab27dddd52cab683af762290fac01c21895d61a`, cuyo veredicto fue **B-1 CERRADO CON CORRECCIONES NO BLOQUEANTES · TOL-207 APROBABLE**.

Desde esta acta, `ADR002-TOL-207` queda **SATISFECHA** dentro del alcance exacto definido aquí.

Los documentos y artefactos conservan sus nombres y etiquetas históricas `PROPUESTO`. Esta acta prevalece sobre esas etiquetas sin reescribirlos, preservando las identidades exactas auditadas.

## 1. Decisión aprobada

Se aprueba como presupuesto absoluto de almacenamiento del laboratorio Linux de ADR-002:

| Concepto | Valor vinculante |
|---|---:|
| Presupuesto máximo por candidato, aplicado al pico | `1.610.612.736 B` |
| Techo agregado co-residente | `8.589.934.592 B` |
| Reserva de seguridad | `15.652.161.536 B` |
| Reserva operativa | `6.442.450.944 B` |
| Suelo de admisión previo a ejecutar | `30.684.547.072 B` |
| Holgura del agregado sobre cinco candidatos | `536.870.912 B` |
| Denominador normativo | `5.670` unidades lógicas primarias |

Los valores normativos son los enteros en bytes. Las expresiones en GiB son únicamente informativas.

### 1.1 Clasificación del entorno

Se aprueba la clasificación:

> **ENVOLVENTE_REPRODUCIBLE**

No se aprueba ni se declara un laboratorio físico estable. Una sesión válida debe verificar, antes de ejecutar, la huella estable del entorno, la semántica de asignación del filesystem y el suelo de admisión.

La disponibilidad concreta de una sesión no es contractual. Si `f_bavail × f_frsize` queda por debajo de `30.684.547.072 B`, la sesión se aborta sin rebajar reservas ni presupuestos.

### 1.2 Objeto contabilizado

La unidad primaria de consumo aprobada es:

```text
st_blocks × 512
```

`st_size` puede registrarse como tamaño aparente, pero no se usa como consumo de almacenamiento.

El presupuesto individual se aplica al máximo simultáneo observado o acotado durante reposo, construcción, reconstrucción, borrado, purga y `VACUUM`, incluyendo:

- índices léxicos, semánticos y relacionales;
- tablas sombra y estructuras auxiliares;
- embeddings persistidos;
- metadatos y cachés persistentes;
- `WAL`, `SHM` y journal;
- temporales, spills y ficheros intermedios;
- coexistencia de índice viejo y nuevo;
- copia transitoria de `VACUUM`;
- cualquier representación reversible derivada del canon.

Los hard links al mismo inode físico se cuentan una vez. Las copias físicas independientes se cuentan por separado.

### 1.3 Techo agregado y co-residencia

El techo agregado de `8.589.934.592 B` se aprueba como **instanciación operativa LAB-LINUX**, no como mandato canónico.

Puede mantener residentes T0 y ADR002-A/B/C/D, con una sola operación pesada simultánea. Superar el techo agregado invalida la sesión; superar el límite individual descarta al candidato aunque el agregado conserve espacio.

### 1.4 Denominador y escalas

El denominador normativo queda fijado en:

```text
550 items estructurados + 5.000 mensajes + 120 documentos
= 5.670 unidades lógicas primarias
```

Las `180` relaciones y `24` entidades forman parte de la carga que puede producir derivados y, por tanto, del numerador, pero no alteran el denominador común.

Las escalas aprobadas son:

- `500`: medición directa sobre subconjunto determinista;
- `5.000`: medición directa sobre subconjunto determinista;
- `5.670`: medición directa sobre el corpus completo;
- `50.000`: siempre `PROYECTADO`, salvo que una versión futura materialice realmente esa escala.

### 1.5 Protocolo de pico

Se aprueba el instrumento fail-closed presente en el commit auditado:

- inventario por inode y bloques asignados;
- doble contabilidad global/inventario;
- checkpoints materiales por tipo de operación;
- muestreo temporal con intervalos reales;
- invalidez por inventario incompleto, escritura no atribuible, doble contabilidad fuera de banda, fallo del hilo, hilo vivo tras timeout o resolución insuficiente;
- resultado `NO_EVALUABLE` sin pico numérico cuando cualquier componente material es inválido;
- publicación del máximo entre una muestra válida y las cotas deterministas válidas de reconstrucción o `VACUUM`.

El bloqueante B-1 queda cerrado por el commit `dab27dddd52cab683af762290fac01c21895d61a`.

## 2. Identidad vinculante de la familia aprobada

La identidad de los contenidos aprobados y de su evidencia se fija mediante sus blobs Git en el commit auditado.

### 2.1 Documentación normativa y paquete

| Artefacto | Blob Git |
|---|---|
| `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_04_TOL207_CARACTERIZACION_v0.1.md` | `bca75e5fdb851a4f38541f3ccbbafa9b4505b4c0` |
| `docs/architecture/SIRIUS_0.2_ADR_002_TOL_207_PRESUPUESTO_ALMACENAMIENTO_v0.2_PROPUESTO.md` | `006617d978492d1f1a1df7b50b3cd63a2b20e7cf` |
| `docs/architecture/SIRIUS_0.2_ADR_002_TOL_207_ANEXO_PICO_v0.1_PROPUESTO.md` | `f715c442cdec79d5e578fefb1d15a8d242d9f97a` |

### 2.2 Contrato ejecutable y verificación

| Artefacto | Blob Git |
|---|---|
| `experiments/adr002/storage/environment_capture.py` | `5b9ac565b82000d4cc10d9241dd8c002a4eefd63` |
| `experiments/adr002/storage/filesystem_probes.py` | `a777ba9759324bdb32788a9fca50d973af226092` |
| `experiments/adr002/storage/storage_accounting.py` | `ec30c6c44b6a0d4bdf268ba949863d9395619b9d` |
| `experiments/adr002/storage/schema_storage_v0_1.py` | `49fb93704f7fc0206bed7ed24bd4042ef056a565` |
| `experiments/adr002/storage/test_storage_gate.py` | `8b2b94d5bdf203dfbe5be3753d0017f411fdbc22` |

### 2.3 Evidencia versionada

| Artefacto | Blob Git |
|---|---|
| `artifacts/adr002_storage/entorno_lab_v0.1.json` | `eff724a1746c3f7e83a222b55597daece3011e0f` |
| `artifacts/adr002_storage/INFORME_TOL207_CARACTERIZACION_v0.1_PROPUESTO.md` | `b2b590bd4f9ab4e7671e8a17313bca838cbd5b5e` |

Cualquier modificación posterior de estos contenidos requiere revisión explícita y un acto sucesor. No se reescriben para retirar sus etiquetas históricas.

## 3. Evidencia y resultado de auditoría

La auditoría final focalizada verificó de forma diferencial el código anterior y la corrección:

- escritura externa con doble contabilidad inválida: `VALIDO` antes, `NO_EVALUABLE` después;
- rutas atribuibles anteriormente presumidas: ahora derivadas;
- checkpoints nominales insuficientes: ahora bloquean;
- errores de inventario anteriormente omitidos: ahora marcan inventario incompleto;
- excepción o hilo vivo del muestreador: ahora invalidan;
- ninguna medición materialmente inválida publica pico numérico;
- reconstrucción, construcción, borrado, purga y `VACUUM` válidos siguen siendo evaluables.

La auditoría informó `246 PASS`, y las suites del repositorio informaron:

- puerta storage: `111 passed`;
- `experiments/adr002`: `376 passed`;
- Ruff: conforme;
- mypy: sin errores;
- blobs del corpus congelado y proyección T0: intactos;
- validación: no mutante.

## 4. Correcciones no bloqueantes registradas

Estas correcciones no invalidan la aprobación y no autorizan modificar ahora la familia aprobada:

1. La medición actual de reserva operativa puede solapar `artifacts/` con el árbol del repositorio; sus topes por partida pueden endurecerse en una revisión futura.
2. El validador no fija todavía todas las asignaciones máximas por partida ni todos los casos `suma_excluida`.
3. La guarda de ubicación de sondas puede endurecerse para rechazar explícitamente `base == repo`.
4. El pico demostrativo del informe no tiene una sección equivalente en la evidencia JSON.
5. La captura de entorno no registra la versión del intérprete Python.
6. Una excepción no-`OSError` en la muestra final síncrona propaga y aborta en lugar de devolver un objeto `NO_EVALUABLE`; sigue fallando cerrado.
7. Los checkpoints duplicados no se rechazan; son instantáneas redundantes, no sustituyen checkpoints ausentes.
8. Un error al resolver una ruta de `excluir` propaga antes de incorporarse al inventario; el orquestador aprobado no usa ese parámetro.

## 5. Limitaciones conocidas registradas

1. La corrección semántica de una cota determinista declarada no puede probarse automáticamente; el instrumento impide publicarla como pico válido cuando la medición es `NO_EVALUABLE`.
2. Una escritura externa transitoria que se crea y elimina entre los checkpoints extremos puede dejar una excursión por muestra sin alterar la diferencia inicio-final. Cerrar esta limitación requiere una regla contractual por muestra y no forma parte de esta aprobación.
3. Un objeto creado y eliminado por debajo de la resolución temporal puede no dejar una señal observable. El contrato exige cotas deterministas para los máximos no observables.
4. La completitud de las rutas atribuibles depende de la declaración operativa. Una declaración vacía o incompleta no puede validarse semánticamente solo mediante el arnés.
5. La escala `500` no representa todas las colas de estado ni toda la densidad relacional; la comparación normativa principal se realiza sobre el corpus completo de `5.670` unidades.
6. La neutralidad experimental plena entre ADR002-A/B/C/D solo podrá comprobarse cuando existan candidatos ejecutables.
7. El presupuesto LAB-LINUX es deliberadamente generoso y puede discriminar poco. La restricción de producto seguirá correspondiendo a `TOL-205` en Windows.

Estas limitaciones son conocidas, visibles y no permiten modificar retrospectivamente los valores después de observar candidatos.

## 6. Estado de las puertas tras esta acta

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` | **SATISFECHA** |
| `ADR002-TOL-207` | **SATISFECHA** — por esta acta |
| `ADR002-TOL-208` · paso 1 | **COMPLETADO** — corpus v0.4 congelado |
| `ADR002-TOL-208` · global | **NO SATISFECHA** |
| `ADR002-TOL-209` | **NO SATISFECHA** |
| `ADR002-TOL-210` | **NO SATISFECHA** |

**El benchmark continúa bloqueado.** Satisfacer TOL-207 no satisface TOL-208 global, TOL-209 ni TOL-210.

## 7. Lo que esta acta no autoriza

- No ejecutar T0.
- No ejecutar los pasos 2 y 3 de `ADR002-TOL-208`.
- No implementar ni ejecutar `ADR002-A`, `ADR002-B`, `ADR002-C` ni `ADR002-D`.
- No iniciar el benchmark.
- No modificar los siete artefactos del corpus congelado.
- No modificar la proyección T0.
- No modificar Sirius 0.1 (`src/`, `tests/`, `migrations/` o configuración productiva).
- No abrir otro PR.
- No fusionar el PR #117.

## 8. Reglas de custodia

1. Los valores de TOL-207 quedan fijados antes de observar resultados de candidatos.
2. Una sesión que no cumpla la huella y el suelo se aborta; no se recalculan valores para acomodarla.
3. Cualquier cambio de los contenidos vinculados en §2 exige una revisión y un acto sucesor.
4. Las etiquetas internas `PROPUESTO` permanecen como historia auditada y no disminuyen la autoridad de esta acta.
5. Las correcciones no bloqueantes y limitaciones registradas no autorizan cambios implícitos ni reabren TOL-207.

---

**Decisión final:** `ADR002-TOL-207` queda **APROBADA y SATISFECHA**. El siguiente trabajo debe limitarse a las puertas aún pendientes y requiere autorización expresa independiente. T0, los candidatos, el benchmark y la fusión del PR #117 continúan no autorizados.
