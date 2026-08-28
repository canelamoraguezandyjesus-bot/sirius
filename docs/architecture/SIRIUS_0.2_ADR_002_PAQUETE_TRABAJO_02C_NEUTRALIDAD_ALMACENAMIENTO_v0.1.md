# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 02C

## Corrección final de neutralidad en tolerancias de almacenamiento

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA CORRECCIÓN DOCUMENTAL DIRIGIDA  
**Rama:** `evidence/adr001-spikes`  
**Dependencia:** Registro de Tolerancias v0.2 en `80b9de67060a4cfba46f2cbb9555cc33adf341c0`  
**No autoriza:** benchmark T1–T4, nuevos prototipos, remedición, aprobación automática ni merge.

## 1. Motivo

El Registro v0.2 es válido salvo por la formulación común de `ADR002-TOL-104`:

- objetivo `≤ ×4,0` por índice;
- límite duro `≤ ×8,0` por índice;
- suma de derivados `≤ 50 %` del fichero.

Esas cifras proceden exclusivamente de dos índices léxicos de Sirius 0.1. Sin embargo, T1–T4 incorporan obligatoriamente señal semántica tardía y T2/T4 pueden incorporar además un índice relacional derivado.

Un vector, incluso razonablemente compacto, puede ocupar más de ocho veces el texto corto que representa. Aplicar el mismo ratio a un índice léxico y a uno semántico no es neutral: favorece por adelantado dimensiones, precisiones, cuantizaciones o técnicas concretas que ADR-002 todavía no ha comparado.

La puerta 7 exige coste compatible, no que todos los índices tengan la misma relación física que FTS5.

## 2. Corrección obligatoria

Crear `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.3_PROPUESTO.md`, conservando intactas v0.1 y v0.2.

No modificar ninguna medición ni ningún artefacto experimental.

### 2.1 Separar el sustrato léxico de los índices adicionales

#### ADR002-TOL-104L · Sustrato léxico · LAB-LINUX

Conservar como propuesta comparativa para el índice léxico:

- objetivo `≤ ×4,0` sobre el canon léxico que cubre;
- límite duro `≤ ×8,0`;
- las cifras son `LAB-LINUX` y no aceptación Windows.

Aplican a FTS5 o al índice léxico alternativo comparable, no a embeddings ni a índices relacionales.

#### ADR002-TOL-104A · Índices adicionales por candidato

Para señales semánticas y relacionales:

- no fijar un ratio universal desde la línea base léxica;
- exigir antes de ejecutar cada candidato una ficha congelada con:
  - tipo de índice;
  - datos canónicos que cubre;
  - número de elementos;
  - dimensiones o estructura equivalente;
  - precisión/representación;
  - bytes totales;
  - bytes por elemento;
  - ratio respecto del canon que cubre;
  - porcentaje del fichero total;
  - crecimiento observado o esperado a 500, 5.000 y 50.000 unidades cuando aplique;
  - tiempo y espacio de construcción/reconstrucción;
  - límite duro del candidato y fundamento;
  - comportamiento de borrado.

Estado: `REGLA_CONFIRMADA_VALOR_CANDIDATO`.

La ficha y su límite se congelan antes de la primera ejecución. No pueden ajustarse después de observar resultados.

### 2.2 Tratar almacenamiento como métrica comparativa, no como sesgo técnico

Un candidato no se descarta únicamente por superar el ratio del índice léxico.

Sí se descarta si:

- incumple el límite de almacenamiento que declaró y congeló;
- su crecimiento no es acotado o no es explicable;
- no cabe en el entorno local de referencia cuando este quede fijado;
- no puede reconstruirse desde el canon;
- no puede borrarse completamente;
- acopla el sistema a un proveedor o formato no portable;
- el coste adicional no produce mejora material frente a alternativas más simples.

### 2.3 Corregir TOL-203

`ADR002-TOL-203` no debe decir que todo índice adicional hereda el ratio de TOL-104 léxica.

Debe heredar:

- declaración completa de tamaño;
- límite congelado por candidato;
- reconstrucción desde el canon;
- desaparición completa;
- al menos 30 repeticiones para tiempos de ciclo cuando sea ejecutable;
- tasa de éxito del 100 % en restitución, integridad y borrado.

### 2.4 Eliminar el límite agregado universal del 50 %

El valor “derivados ≤50 % del fichero” se conserva como dato comparativo de la propuesta v0.2, pero no como límite duro común a T1–T4.

La razón es metodológica: el tamaño del fichero canónico depende del corpus y la longitud media del texto, mientras un vector depende principalmente del número de elementos, dimensiones y precisión. El porcentaje del fichero puede variar radicalmente sin que la arquitectura sea peor.

La eventual restricción absoluta de almacenamiento local pertenece al entorno de referencia y debe congelarse antes del benchmark o, para aceptación, sobre Windows.

## 3. Qué no cambia

Conservar sin cambios:

- TOL-001–006;
- B04-M01–M21;
- TOL-204 con cero críticos elegibles pendientes;
- TOL-101, 102, 103, 105, 106 y 107;
- TOL-201, 202 y 205;
- todas las mediciones v0.1 y v0.2;
- alcance LAB-LINUX y aceptación Windows pendiente.

## 4. Entregable

Crear únicamente:

- `docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.3_PROPUESTO.md`

El documento debe explicar con claridad que esta corrección evita elegir por adelantado dimensión, precisión, cuantización, extensión vectorial o representación relacional.

## 5. Validación

Confirmar:

- v0.1 y v0.2 intactas;
- ninguna medición nueva;
- ningún cambio en `experiments/`, `artifacts/`, `src/`, `tests/`, `migrations/` o configuración;
- TOL-104L solo para sustrato léxico;
- TOL-104A y TOL-203 congelados por candidato;
- eliminado el 50 % como límite universal;
- ninguna puerta canónica rebajada;
- sin benchmark, sin PR nuevo y sin merge.

## 6. Publicación

Commit:

`docs(adr002): make storage tolerances technology-neutral`

Push a `evidence/adr001-spikes`.
