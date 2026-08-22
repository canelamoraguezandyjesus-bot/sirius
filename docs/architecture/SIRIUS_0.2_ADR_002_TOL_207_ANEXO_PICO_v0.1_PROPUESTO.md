# SIRIUS 0.2 — ADR-002 · TOL-207 · Anexo de contabilidad de picos de almacenamiento

**Versión:** 0.1
**Estado:** **PROPUESTO** · continúa PROPUESTO hasta aprobar `ADR002-TOL-207`
**Fecha:** 27 de julio de 2026
**Ámbito:** específico de **contabilidad de almacenamiento** para `ADR002-TOL-207`
**Relación con TOL-209:** **no modifica ni sustituye** el `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md` aprobado. Define únicamente cómo medir **reposo y picos de bytes e inodos**; toda medición temporal sigue rigiendo por el protocolo común
**Código:** `experiments/adr002/storage/storage_accounting.py` y `experiments/adr002/storage/filesystem_probes.py`
**No autoriza:** benchmark, ejecución de T0, implementación de candidatos ni aprobación de TOL-207.

---

## 0. Por qué existe

El protocolo común de TOL-209 incluye «tamaño» en su alcance pero no define
método alguno para bytes en disco: reloj monotónico, warm-up y percentiles
no capturan un **máximo simultáneo de bloques asignados** durante una
operación. Sin este anexo, el presupuesto por candidato —que se aplica al
máximo simultáneo, no al reposo— no sería medible ni auditable.

Nota terminológica: el protocolo común escribe su veredicto `NO EVALUABLE`;
este anexo y su evidencia legible por máquina usan el identificador
`NO_EVALUABLE` para el mismo concepto aplicado a almacenamiento.

## 1. Inventario por inode

- La unidad primaria de consumo es **`st_blocks × 512`** (bloques
  asignados). `st_size` se registra pero no es consumo.
- El inventario deduplica por `(st_dev, st_ino)`: un inode físico se cuenta
  **una vez**; los hard links no duplican; las copias físicas distintas sí.
- El inventario atribuible de un candidato cubre todas las partidas del §6
  de la propuesta v0.2, incluidos WAL, SHM, journal, temporales, spills,
  índice viejo y nuevo coexistentes y copia de VACUUM.

## 2. Muestreador

- Período **predeterminado de 5 ms**, configurable.
- **Hilo o proceso dedicado**; cada muestra lleva **timestamp monotónico**
  propio y procede de **una única llamada `statvfs`**.
- Se registra el **intervalo real** entre muestras y el **máximo intervalo
  observado** — la validez se juzga con lo observado, nunca con lo
  solicitado.
- Cada muestra registra `f_bavail`, `f_favail` y los bytes e inodos del
  inventario atribuible.

## 3. Checkpoints síncronos

Instantáneas síncronas obligatorias, cada una con una única `statvfs` más el
inventario atribuible:

1. antes de la operación;
2. después de crear temporales;
3. antes de intercambiar viejo/nuevo;
4. antes de borrar temporales;
5. antes y después de checkpoint/journal;
6. antes y durante VACUUM, cuando sea instrumentable;
7. final.

## 4. Doble contabilidad y banda de ruido

- Se comparan la **variación global de `f_bavail`** y la **variación del
  inventario atribuible** entre el primer checkpoint y el final.
- **No se inventa una tolerancia fija de ruido.** Antes de la operación se
  mide una **ventana inactiva** y se registran su mínimo, su máximo, su
  rango y la granularidad del filesystem (`f_frsize`).
- Toda diferencia no explicada se registra como **escritura externa**.
- Si la diferencia global/inventario supera la **banda observada más la
  granularidad**, la medida es **inválida**.

## 5. Regla `NO_EVALUABLE`

No se publica pico numérico como válido si la operación:

1. dura menos de **tres intervalos reales** del muestreador;
2. tiene una **pausa máxima del muestreador incompatible** con su duración;
3. crea y borra objetos **sin observación ni checkpoint**;
4. usa **rutas no atribuibles**;
5. o **no permite calcular una cota determinista**.

En todos esos casos el resultado es **`NO_EVALUABLE`**: sin número
publicado, la cota determinista queda como único dato utilizable cuando
existe.

## 6. Reconstrucción y VACUUM

- Se calcula además la **cota determinista** `viejo + nuevo` (u
  `original + copia` en VACUUM).
- Se compara con el pico muestreado y se **publica el mayor valor válido**.
- **Nunca se sustituye un máximo conocido por una muestra inferior.**

## 7. Sondas del filesystem y residuo

- Las sondas trabajan exclusivamente en un directorio temporal **fuera del
  repositorio y en el mismo filesystem** (`st_dev` idéntico).
- Tamaño simultáneo máximo asignado físicamente: **64 MiB**.
- Comprueban: escritura densa; tamaño aparente frente a bloques asignados;
  fichero sparse; reflink/`FICLONE`; COW; compresión o deduplicación
  aparente; creación y liberación de inodos; liberación de bloques tras
  borrado; residuo; y comportamiento de la ruta de error.
- **Todo se borra mediante `finally` incluso si una sonda falla.**
- Residuo máximo admisible tras la limpieza: **65.536 B**. Por encima, la
  medición es inválida; se permite **una única repetición controlada**; un
  segundo fallo produce **`NO_EVALUABLE`**.

## 8. Lo que este anexo no hace

- No modifica el protocolo común de TOL-209 ni sus reglas §2–§8.
- No fija umbrales de TOL-107 ni ningún valor del Registro.
- No mide candidatos: define el contrato con el que se medirán.
- No aprueba TOL-207: continúa **NO SATISFECHA**.

---

**Siguiente movimiento único:** auditoría adversarial independiente del
paquete 04; este anexo se aprueba o corrige junto con la propuesta v0.2 de
TOL-207, nunca por separado.
