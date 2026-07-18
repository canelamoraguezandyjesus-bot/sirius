# Prueba de humo de Claude Code cloud

**Estado: SUPERADA — CLOUD_SMOKE_PASSED — 18 de julio de 2026.**
Rama `chore/cloud-smoke-20260718-03`, fusionada mediante PR #34
(`docs: record successful cloud smoke test`), con 562 pruebas superadas.
Evidencia versionada en
[`docs/implementation/CLOUD_SMOKE_EVIDENCE_20260718.md`](CLOUD_SMOKE_EVIDENCE_20260718.md).
La puerta para B4a queda satisfecha. Este documento se conserva como
protocolo histórico y reutilizable para futuras ejecuciones de la misma
prueba.

## Propósito

Demostrar antes de B4a que una sesión cloud puede trabajar sobre Sirius sin depender del ordenador del usuario ni exigir aprobaciones rutinarias continuas.

Esta prueba no valida una función de producto y no autoriza cambios en Sirius 0.1. Solo valida el mecanismo de trabajo remoto.

## Resultado esperado

La prueba debe terminar en uno de estos estados:

- `CLOUD_SMOKE_PASSED`
- `BLOCKED_BY_PERMISSION`
- `BLOCKED_BY_ENVIRONMENT`
- `FAILED_SAFELY`
- `USAGE_LIMIT_REACHED`

Un estado verde de infraestructura no equivale por sí solo a `CLOUD_SMOKE_PASSED`.

## Alcance permitido

- Clonar y preparar el repositorio en una sesión cloud limpia.
- Leer las instrucciones operativas.
- Ejecutar las comprobaciones de calidad.
- Crear una rama temporal de prueba.
- Añadir un único archivo de evidencia dentro de `docs/implementation/`.
- Preparar una pull request borrador.

## Prohibiciones

- No modificar `src/`, `tests/`, `migrations/`, documentos canónicos ni decisiones.
- No usar claves reales, red del proveedor, Credential Manager ni datos personales.
- No cambiar permisos para conseguir que la prueba pase.
- No hacer merge.
- No reutilizar la rama de B4a.
- No declarar superada ninguna PA, PS o SP.

## Tarea de humo

Usar una rama nueva con nombre similar a:

`chore/cloud-smoke-YYYYMMDD`

Prompt recomendado para la sesión cloud:

```text
Realiza exclusivamente la prueba de humo cloud de Sirius.

Lee AGENTS.md, CLAUDE.md, docs/canonical/STATUS.md,
docs/implementation/PLAN.md, docs/implementation/V8_EXECUTION.md y
docs/implementation/CLOUD_SMOKE_TEST.md.

No modifiques código, pruebas, migraciones, configuración de permisos ni
fuentes canónicas.

1. Registra sistema operativo, versión de Python y versión de uv.
2. Prepara las dependencias desde un clon limpio.
3. Ejecuta las cuatro comprobaciones equivalentes a scripts/check.ps1:
   - uv run ruff format --check .
   - uv run ruff check .
   - uv run mypy src tests
   - uv run pytest
4. Ejecuta git diff --check y git status.
5. Crea docs/implementation/CLOUD_SMOKE_EVIDENCE.md con los comandos,
   códigos de salida, número de pruebas y cualquier permiso o bloqueo.
6. Prepara una pull request borrador. No hagas merge.

Devuelve CLOUD_SMOKE_PASSED solo si todo termina con código 0, la PR borrador
existe y no necesitaste intervención rutinaria del usuario. Si un permiso,
entorno, cuota o comando lo impide, detente y devuelve el estado de bloqueo
correspondiente con la causa exacta. No amplíes permisos por tu cuenta.
```

## Evidencia obligatoria

El archivo temporal `CLOUD_SMOKE_EVIDENCE.md` debe incluir:

- fecha y hora UTC;
- identificador o enlace de la sesión, cuando esté disponible;
- commit base de `main`;
- sistema operativo;
- versión de Python;
- versión de `uv`;
- comandos ejecutados y códigos de salida;
- resultado de Ruff format;
- resultado de Ruff lint;
- resultado de mypy;
- número total de pruebas y resultado de pytest;
- resultado de `git diff --check`;
- archivos modificados;
- número de solicitudes de permiso que requirieron intervención humana;
- estado final.

No debe contener prompts completos de usuario, secretos, rutas personales ni contenido de la base de datos.

## Criterio de aprobación

La prueba queda `CLOUD_SMOKE_PASSED` únicamente si:

1. La sesión parte de un clon limpio.
2. El ordenador del usuario puede permanecer apagado o desconectado.
3. Las dependencias se preparan sin intervención repetitiva.
4. Las cuatro comprobaciones terminan con código 0.
5. `git diff --check` termina con código 0.
6. Solo se añade el archivo temporal de evidencia.
7. Se crea una PR borrador sin push directo a `main`.
8. No se usa ninguna credencial real.
9. No se amplían permisos durante la ejecución.
10. El estado final y la evidencia coinciden.

## Criterios de fallo y acción

### `BLOCKED_BY_PERMISSION`

Algún comando legítimo y necesario requiere aprobación o está denegado.

Acción: registrar el comando exacto y decidir después si merece un permiso estrecho. No conceder comodines amplios.

### `BLOCKED_BY_ENVIRONMENT`

Falta Python, `uv`, PowerShell, una dependencia del sistema o una capacidad necesaria del entorno cloud.

Acción: preparar una corrección reproducible y volver a ejecutar la prueba completa.

### `USAGE_LIMIT_REACHED`

La cuota se agota antes de completar el protocolo.

Acción: no modificar el flujo; repetir cuando se renueve la cuota o reducir únicamente trabajo no esencial.

### `FAILED_SAFELY`

La sesión falla sin modificar código de producto, `main`, secretos ni fuentes canónicas.

Acción: conservar evidencia suficiente y corregir la causa antes de B4a.

## Limpieza posterior

Por defecto la PR de humo no se fusiona en `main` salvo que el usuario decida conservar una evidencia mínima. En esta ejecución (18 de julio de 2026) el usuario decidió conservar y fusionar la evidencia: la PR #34 se fusionó en `main` con el único archivo `docs/implementation/CLOUD_SMOKE_EVIDENCE_20260718.md`, sin cambios funcionales. No fue necesario borrar ninguna rama adicional para conservar la evidencia.

## Puerta para B4a

B4a puede comenzar cuando ocurra una de estas dos condiciones:

- `CLOUD_SMOKE_PASSED`; o
- el usuario decide explícitamente continuar temporalmente con el flujo local semiautomático, aceptando que el ordenador deberá permanecer encendido.

La primera condición ya se cumplió el 18 de julio de 2026 (`CLOUD_SMOKE_PASSED`, PR #34 fusionada). La puerta para B4a queda satisfecha; B4a todavía no ha comenzado.
