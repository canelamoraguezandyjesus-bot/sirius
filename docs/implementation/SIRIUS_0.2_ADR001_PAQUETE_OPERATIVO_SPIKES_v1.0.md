# SIRIUS 0.2 — Paquete operativo de spikes de ADR-001

**Versión:** 1.0  
**Estado:** APROBADO PARA EJECUCIÓN EXPERIMENTAL AISLADA  
**Ámbito:** Spikes decisivos de ADR-001  
**No autoriza:** implementación productiva de Sirius 0.2, modificación de Sirius 0.1, cambios en migraciones canónicas ni apertura de ADR-002.

## 1. Objetivo

Ejecutar de forma aislada los spikes decisivos de ADR-001 para determinar si:

- se ratifica la alternativa A;
- el modelo heredado exige escalar a B;
- SQLite presenta una limitación propia que obliga a abrir la contingencia C.

## 2. Spikes decisivos

Ejecutar: **1–8, 10 y 15–19**.

1. Afirmación atómica con varias procedencias.
2. Apoyo y refutación múltiples.
3. Tiempo válido separado del tiempo de registro.
4. Corrección retroactiva.
5. Consulta válida en T.
6. Consulta conocida en T.
7. Siete dimensiones ortogonales de estado.
8. Ámbito multi-proyecto cerrado.
10. Borrado duro con FTS5 y derivados.
15. Migración de datos 0.1 representativos.
16. Rollback.
17. Fallo inyectado durante escritura crítica.
18. Ningún derivado actúa como canon.
19. No reconstruibilidad.

## 3. Restricciones

- No modificar código productivo de Sirius 0.1.
- No modificar la cadena canónica de migraciones Alembic.
- No usar bases reales, datos personales, secretos ni claves API.
- No realizar llamadas de red.
- No fijar DDL definitivo, nombres productivos ni estrategia final de migración.
- No hacer push directo a `main` ni merge automático.
- Todo código y evidencia debe ser experimental, reproducible y eliminable.

## 4. Ubicaciones autorizadas

Crear, si no existen, únicamente estas rutas nuevas:

- `experiments/adr001/`
- `artifacts/adr001_spikes/`

No escribir fuera de ellas salvo los cambios mínimos de configuración de pruebas que resulten imprescindibles y queden expresamente justificados en la incidencia operativa.

## 5. Clasificación de resultados

Cada spike termina en una categoría:

- `PASS`
- `FAIL_IMPLEMENTATION`
- `FAIL_STRUCTURAL_MODEL`
- `FAIL_ENGINE_SQLITE`
- `INCONCLUSIVE`

Regla final:

- Todos en `PASS` → **RATIFICAR A**.
- `FAIL_STRUCTURAL_MODEL` en 1–8 o 15–18 → **ESCALAR A B**.
- `FAIL_ENGINE_SQLITE` confirmado en 10 o 19 → **ABRIR CONTINGENCIA C**.
- Cualquier `INCONCLUSIVE` → **DECISIÓN BLOQUEADA**.

## 6. Evidencia mínima por spike

Cada spike debe registrar:

- objetivo;
- incertidumbre;
- dataset sintético;
- preparación;
- operación;
- resultado esperado;
- criterio de fallo;
- evidencia producida;
- resultado;
- repetición desde base limpia;
- conclusión sobre A, B o C.

## 7. Prevuelo y cierre

Antes:

- registrar `git status`;
- registrar versiones de Python, SQLite, SQLAlchemy y Alembic;
- identificar head de Alembic, FTS5, triggers, UnitOfWork y PRAGMA relevantes;
- ejecutar `scripts/check.ps1`.

Después:

- repetir `scripts/check.ps1`;
- registrar `git status`;
- confirmar que Sirius 0.1 no fue modificado;
- no hacer merge sin autorización explícita del usuario.

## 8. Informe obligatorio

Crear:

`artifacts/adr001_spikes/SIRIUS_0.2_ADR_001_RESULTADOS_SPIKES_v0.1_PROPUESTO.md`

Debe incluir entorno, tabla de los 14 spikes, evidencias, pruebas, archivos creados, limitaciones, decisión resultante y siguiente movimiento único.
