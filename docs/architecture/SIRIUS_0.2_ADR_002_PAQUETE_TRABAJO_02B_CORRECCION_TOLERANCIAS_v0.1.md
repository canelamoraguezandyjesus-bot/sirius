# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 02B

## Corrección dirigida del Registro de Tolerancias

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA CORRECCIÓN Y REMEDICIÓN ACOTADA  
**Rama:** `evidence/adr001-spikes`  
**Dependencia:** paquete 02 ejecutado en `c8b64a9929c639a88f31e6ee092c7d6c728b8316`  
**No autoriza:** benchmark T1–T4, implementación productiva, aprobación del Registro ni merge.

## 1. Objetivo

Conservar toda la evidencia válida del paquete 02 y corregir únicamente tres defectos antes de presentar el Registro al usuario:

1. una contradicción con el contrato canónico de suficiencia y críticos;
2. tiempos de ciclo medidos con una sola pasada;
3. variación entre ejecuciones estimada con solo dos ejecuciones completas.

## 2. Corrección canónica obligatoria: críticos pendientes

La fila `ADR002-TOL-204` no puede quedar como `REGLA_CONFIRMADA_VALOR_CANDIDATO`.

B04 v1.0 ya fija:

- la expansión continúa cuando falta suficiencia **o queda un crítico elegible pendiente**;
- S1 solo puede operar en cardinalidad `EXACTA` o `ACOTADA` tras comprobar que **no queda ningún crítico elegible pendiente** en espacios autorizados;
- una consulta `EXHAUSTIVA` nunca termina por S1;
- B04-M01 exige 100 % de críticos recuperados por caso; bajo límite duro, todo crítico omitido debe contabilizarse y el desbordamiento debe ser visible.

Por tanto:

- umbral operativo para detener expansión por cobertura crítica: **0 críticos elegibles pendientes**;
- no se congela por candidato;
- el candidato solo decide cómo implementa y demuestra esa comprobación;
- si el límite duro impide incluirlos, la salida es `PARCIAL` visible, nunca suficiencia completa.

Crear en v0.2 una fila canónica o derivada-canónica que exprese esta regla sin cifra variable.

## 3. Remedición del ciclo del índice

La afirmación «irrepetible por naturaleza» es inválida. Borrado, construcción y reconstrucción pueden repetirse sobre copias o bases limpias independientes.

Repetir como mínimo 30 veces, cada vez sobre una copia/base preparada fuera del cronómetro:

1. borrado completo de cada derivado y tablas sombra;
2. construcción inicial desde el canon;
3. reconstrucción desde el canon;
4. `integrity-check`;
5. comprobación de filas idénticas.

Registrar P50/P95/P99 por operación mediante nearest-rank, mínimo, máximo y tasa de éxito.

El tiempo de `rebuild` interno puede conservarse como observación, pero nunca como evidencia de reconstrucción desde canon para `knowledge_fts`.

Actualizar `ADR002-TOL-105` con distribución real. La restitución idéntica y el 100 % de éxito siguen sin margen.

## 4. Remedición de variación entre ejecuciones

Dos ejecuciones no bastan para justificar un objetivo de variación.

Ejecutar al menos **5 sesiones completas independientes** del runner de consulta, con warm-up propio y las mismas condiciones.

Registrar por escenario:

- P50/P95 de cada sesión;
- coeficiente máximo de variación entre sesiones según la fórmula ya declarada;
- estabilidad de orden y conjunto;
- carga o incidencias observables de la máquina, si las hubiera.

Actualizar `ADR002-TOL-107` con el peor valor observado y margen explícito. Si cinco sesiones siguen siendo insuficientes para fijar un límite duro defendible, mantener el objetivo como `PROPUESTA` y clasificar el límite duro como `REGLA_CONFIRMADA_VALOR_ENTORNO`, no inventarlo.

## 5. Alcance de las cifras Linux

Todas las cifras medidas en esta ronda son tolerancias del **laboratorio comparativo Linux**, válidas para comparar T1–T4 en el mismo entorno.

No deben presentarse como aceptación final del producto Windows 11.

El Registro v0.2 debe distinguir:

- `LAB-LINUX`: umbral comparativo para ADR-002;
- `ACEPTACIÓN-WINDOWS`: pendiente de confirmación sobre el ejecutable o entorno de referencia Windows antes de aceptar implementación.

No hace falta repetir ahora todo en Windows. Sí debe quedar explícito que las cifras absolutas de latencia, tamaño y ciclo no se trasladan automáticamente a Windows.

## 6. TOL-002

Conservar la conclusión válida:

- estado, texto y conteo externos fueron equivalentes;
- no se observó diferencia temporal repetible;
- el barrido constante actual enmascara diferencias y el resultado no se hereda a candidatos.

No aprobar todavía una banda universal. Mantenerla como regla cuyo valor se fija por candidato antes de ejecutarlo.

La fracción de signo puede conservarse como una condición, pero no como única protección: el candidato deberá demostrar además ausencia de separación material en distribución y repetir en sesión independiente.

## 7. Entregables

No borrar ni modificar los artefactos v0.1.

Crear:

1. `artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json`
2. `artifacts/adr002_tolerances/INFORME_MEDICION_TOLERANCIAS_v0.2_PROPUESTO.md`
3. `docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.2_PROPUESTO.md`

Modificar únicamente el código experimental imprescindible dentro de:

- `experiments/adr002/tolerances/`

## 8. Validación

Ejecutar:

- pruebas propias del experimento;
- runner de remedición;
- Ruff sobre `experiments/adr002/tolerances/`;
- `git status`.

Confirmar:

- TOL-204 corregida a 0 críticos elegibles pendientes;
- 30 repeticiones del ciclo;
- 5 sesiones independientes para variación;
- cifras Linux marcadas como laboratorio, no aceptación Windows;
- ningún cambio en `src/`, `tests/`, `migrations/` o configuración productiva;
- no se ejecutó T1–T4;
- no se modificaron los artefactos v0.1.

## 9. Publicación

Commit:

`test(adr002): strengthen tolerance evidence`

Push a `evidence/adr001-spikes`. No abrir otro PR ni fusionar el PR #117.
