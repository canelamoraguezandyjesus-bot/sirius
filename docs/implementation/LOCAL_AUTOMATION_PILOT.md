# Piloto local semiautomático

## Estado

ACTIVO - fase operativa actual (sustituye a la Fase A cloud, cerrada en `BLOCKED_BY_ENVIRONMENT` el 18 de julio de 2026; ver `docs/implementation/CLOUD_SMOKE_TEST.md` y `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` Sección 13).

## Objetivo

Demostrar que una sesión de Claude Code, ejecutada localmente en el ordenador del usuario y con el ordenador encendido durante toda la ejecución, puede leer las fuentes obligatorias, ejecutar la validación completa (`scripts/check.ps1`), dejar evidencia auditable y detenerse de forma segura, sin depender de intentos cloud adicionales.

Este documento no valida ninguna función de producto de Sirius 0.1 ni sustituye la prueba de humo cloud. Solo abre y regula una vía alternativa temporal para acumular evidencia antes de B4a.

## Alcance

Piloto inicial de validación del flujo local:

- Leer las fuentes obligatorias (`AGENTS.md`, `CLAUDE.md`, `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md`, este documento).
- Ejecutar `scripts/check.ps1` sobre el estado actual del repositorio.
- Registrar comandos, códigos de salida y resultado en un archivo de evidencia dentro de `docs/implementation/`.
- Detenerse sin realizar ninguna otra acción.

Este piloto no implementa B4a ni ningún requisito funcional de Sirius. No crea infraestructura de commit, push o PR automatizado.

## Precondiciones

- Rama dedicada, distinta de cualquier rama de B4a (`chore/local-automation-pilot` para esta validación inicial).
- `main` local actualizado y limpio antes de partir.
- `scripts/check.ps1` disponible y ejecutable sin modificaciones.
- El usuario ha aprobado explícitamente cerrar la vía cloud y activar esta vía local (decisión registrada el 18 de julio de 2026).
- Ninguna clave real, Credential Manager real ni red del proveedor en uso.

## Acciones permitidas

- Leer cualquier archivo del repositorio.
- Ejecutar `scripts/check.ps1` (Ruff format, Ruff lint, mypy, pytest) con los permisos ya existentes en `.claude/settings.json`.
- Crear o actualizar el archivo de evidencia del piloto dentro de `docs/implementation/`.
- Ejecutar comandos git de solo lectura (`status`, `diff`, `log`, `show`, `branch --show-current`).
- Detenerse y pedir decisión ante cualquier resultado que no sea un éxito limpio.

## Acciones prohibidas

- Modificar `src/`, `tests/` o `migrations/` durante este piloto inicial de validación.
- Hacer `git commit`, `git push`, crear una pull request o usar `gh` en cualquier forma.
- Ampliar, sustituir o añadir permisos en `.claude/settings.json` o `.claude/settings.local.json`.
- Modificar `.claude/`, `scripts/`, `AGENTS.md`, `CLAUDE.md` o cualquier documento en `docs/canonical/`.
- Hacer merge, rebase o cualquier operación destructiva de git.
- Usar clave real, Credential Manager real, red del proveedor o datos personales.
- Reanudar intentos cloud sin una nueva decisión explícita del usuario.
- Iniciar B4a bajo cualquier pretexto de este piloto.

## Evidencia obligatoria

Un archivo `docs/implementation/LOCAL_AUTOMATION_PILOT_EVIDENCE.md` (creado en una ejecución real del piloto, no en esta puesta en marcha documental) debe incluir:

- fecha y hora local;
- commit base y rama;
- comandos ejecutados y códigos de salida;
- resultado de Ruff format, Ruff lint, mypy y pytest (número de pruebas);
- resultado de `git status` y `git diff --check`;
- archivos modificados durante la ejecución (debe ser únicamente el propio archivo de evidencia);
- cualquier permiso solicitado o bloqueado;
- estado final.

No debe contener secretos, rutas personales sensibles ni contenido de la base de datos.

## Estados finales

- `READY_FOR_HUMAN_REVIEW` - la validación terminó limpia; el usuario decide el siguiente paso.
- `BLOCKED_BY_PERMISSION` - un comando necesario requirió un permiso no concedido; no se amplía por iniciativa propia.
- `BLOCKED_BY_ENVIRONMENT` - falta una dependencia local reproducible.
- `FAILED_SAFELY` - la ejecución falla sin tocar `src/`, `tests/`, `migrations/`, `main` ni documentos canónicos.
- `BLOCKED_BY_DECISION` - el resultado exige una decisión del usuario no cubierta por este documento.
- `USAGE_LIMIT_REACHED` - la cuota se agota antes de completar el protocolo. Acción: detenerse de forma segura, conservar la evidencia disponible hasta ese punto, esperar la renovación de cuota y reanudar entonces sin rediseñar el flujo.

## Criterios de aceptación

El piloto inicial queda aceptado únicamente si:

1. Solo se creó o modificó el archivo de evidencia dentro de `docs/implementation/`.
2. `scripts/check.ps1` terminó con código 0 en sus cuatro comprobaciones, o el fallo quedó documentado sin corrección improvisada.
3. No se ejecutó ningún `git commit`, `git push`, `merge`, `rebase` ni operación destructiva.
4. No se amplió ningún permiso de `.claude/settings.json` ni `.claude/settings.local.json`.
5. No se tocó `src/`, `tests/`, `migrations/`, `.claude/`, `scripts/`, `AGENTS.md`, `CLAUDE.md` ni `docs/canonical/`.
6. El estado final declarado coincide con la evidencia registrada.

## Recuperación segura

Ante cualquier fallo, bloqueo o resultado inesperado:

- No revertir con `git reset --hard`, `git clean` ni ninguna operación destructiva.
- Dejar el árbol de trabajo tal como quedó y registrar el estado exacto en la evidencia.
- Si el archivo de evidencia quedó a medias o corrupto, crear una versión nueva y corregida; no editar retroactivamente un resultado ya registrado como final.
- Si el bloqueo es de permiso, registrar el comando exacto denegado y esperar decisión del usuario antes de solicitar un permiso nuevo.
- El usuario conserva en todo momento la opción de descartar la rama del piloto sin que eso afecte a `main` ni a ninguna otra rama.

## Puerta explícita antes de B4a

Este piloto local, por sí solo, **no autoriza B4a**. B4a solo puede comenzar cuando, además de lo exigido en `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` y `docs/implementation/B4_EXECUTION.md`:

1. este piloto inicial de validación haya terminado en `READY_FOR_HUMAN_REVIEW`;
2. el usuario haya revisado la evidencia y decidido explícitamente abrir B4a bajo el flujo local;
3. exista una definición separada y aprobada de cómo B4a ejecutará su alcance funcional en local (B4a sí necesita tocar `src/`, `tests/` y `migrations/`, lo que este piloto de validación prohíbe expresamente; esa siguiente definición es una decisión distinta y posterior a este documento, no cubierta aquí).

Hasta que se cumplan estas tres condiciones, la única acción válida relacionada con B4a es: no ha comenzado y no está autorizado.
