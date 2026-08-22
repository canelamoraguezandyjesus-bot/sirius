# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 04

## TOL-207 · Caracterización reproducible y presupuesto absoluto de almacenamiento v0.2

**Versión:** 0.1
**Estado:** **EJECUTADO** · el resultado queda **PROPUESTO · PENDIENTE DE AUDITORÍA INDEPENDIENTE**
**Fecha:** 27 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Entrada:** commit `d7d4e30ad94ae651999e76c975202d6dec79614b` · PR #117 abierto y sin fusionar
**Especificación de origen:** dos revisiones forenses y una auditoría adversarial sobre `TOL-207 v0.1`
**No autoriza:** ejecutar T0, implementar o ejecutar `ADR002-A/B/C/D`, aprobar `ADR002-TOL-207`, modificar los siete artefactos congelados, tocar Sirius 0.1, abrir otro PR ni fusionar el PR #117.

---

## 1. Objetivo

Materializar la corrección de `TOL-207 v0.1` como propuesta v0.2 con:

1. **caracterización reproducible del entorno** como **envolvente**, no como máquina estable: captura atómica legible por máquina, huella estable propuesta y campos efímeros;
2. **aritmética exacta en bytes enteros**, con las cifras retiradas de la v0.1 registradas como errores históricos y nunca vigentes;
3. **regla de admisión con suelo absoluto** y condiciones de aborto expresas;
4. **proveniencia separada de las tres sesiones** conocidas y documentación de la anomalía de reserva;
5. **objeto contabilizado** (`st_blocks * 512`), presupuesto por candidato aplicado al máximo simultáneo, techo agregado y reserva operativa demostrada;
6. **denominador normativo** de 5.670 unidades lógicas primarias y escalas deterministas;
7. **protocolo de pico** con muestreador, checkpoints, doble contabilidad y regla `NO_EVALUABLE`;
8. **sondas del filesystem** con limpieza garantizada y residuo acotado;
9. **pruebas negativas obligatorias** que demuestran cada control rompiéndolo.

Este paquete define el contrato y produce la evidencia de la sesión actual. **No rellena resultados de candidatos inexistentes** y no aprueba nada.

## 2. Estado de partida verificado

| Comprobación | Resultado |
|---|---|
| HEAD | `d7d4e30ad94ae651999e76c975202d6dec79614b` |
| PR #117 | abierto · `merged: false` · head coincide |
| Corpus v0.4 | **APROBADO y CONGELADO** — siete blobs verificados intactos |
| `ADR002-TOL-208` paso 1 | **COMPLETADO** |
| `ADR002-TOL-207` | **NO SATISFECHA** |
| Suelo de admisión | superado por la sesión (ver evidencia JSON) |
| Repositorio y temporales | mismo filesystem (`st_dev` idéntico) |

## 3. Entregables

Exactamente once archivos nuevos, cero modificados, cero eliminados:

| # | Archivo | Contenido |
|---|---|---|
| 1 | `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_04_TOL207_CARACTERIZACION_v0.1.md` | este paquete |
| 2 | `docs/architecture/SIRIUS_0.2_ADR_002_TOL_207_PRESUPUESTO_ALMACENAMIENTO_v0.2_PROPUESTO.md` | propuesta normativa v0.2 |
| 3 | `docs/architecture/SIRIUS_0.2_ADR_002_TOL_207_ANEXO_PICO_v0.1_PROPUESTO.md` | anexo de contabilidad de picos |
| 4 | `experiments/adr002/storage/__init__.py` | paquete experimental |
| 5 | `experiments/adr002/storage/environment_capture.py` | captura atómica y ensamblado de evidencia |
| 6 | `experiments/adr002/storage/filesystem_probes.py` | sondas del filesystem |
| 7 | `experiments/adr002/storage/storage_accounting.py` | inventario, muestreador y pico |
| 8 | `experiments/adr002/storage/schema_storage_v0_1.py` | constantes, contrato y validador |
| 9 | `experiments/adr002/storage/test_storage_gate.py` | puerta de pruebas y negativas |
| 10 | `artifacts/adr002_storage/entorno_lab_v0.1.json` | evidencia legible por máquina |
| 11 | `artifacts/adr002_storage/INFORME_TOL207_CARACTERIZACION_v0.1_PROPUESTO.md` | informe |

## 4. Regla de admisión aplicada

Antes de producir la evidencia versionada se captura el entorno. Si
`f_bavail × f_frsize < 30.684.547.072 B`, no se rebaja ninguna reserva ni
presupuesto, no se crean los archivos, no se hace commit y se entrega
`VALOR_NO_RECOMENDABLE_AUN`. También se aborta sin commit si la reserva
operativa real necesaria supera 6.442.450.944 B, si el filesystem no permite
contabilización fiable, si la captura no puede hacerse atómicamente, si las
sondas no pueden limpiarse, si repositorio y temporales están en filesystems
distintos o si no puede demostrarse que los siete blobs congelados siguen
intactos.

## 5. Validación exigida

- pruebas de `experiments/adr002/storage/`;
- pytest completo de `experiments/adr002/` — los validadores históricos
  v0.1/v0.2, que reescriben de forma determinista idéntica (LC-F del acta de
  congelación), se ejecutan **únicamente sobre copia temporal**, nunca sobre
  el árbol real;
- `ruff format --check` y `ruff check`;
- `mypy` conforme al contrato del repositorio;
- validación del JSON contra su esquema y regeneración de los cálculos desde
  la captura fija;
- comprobación de que validar no muta artefactos;
- verificación de los siete blobs congelados y del blob de la proyección T0;
- `git status` limpio salvo los once archivos nuevos.

## 6. Publicación

Un único commit:

```
test(adr002): add TOL-207 storage characterization and budget v0.2
```

Push a `evidence/adr001-spikes`. El PR #117 permanece abierto y sin fusionar.
Después del commit no se aprueba TOL-207, no se crea acta, no se ejecuta T0,
no se implementan candidatos y no se propone iniciar el benchmark: la
siguiente sesión será una **auditoría adversarial independiente** en otro
contenedor.

---

**Siguiente movimiento único:** auditoría adversarial independiente del
paquete implementado, en un contenedor distinto, con su propia observación
del entorno.
