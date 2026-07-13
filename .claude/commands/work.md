---
description: Implementa una tarea de Sirius dentro del alcance ya aprobado, verifica con /check y se detiene ante decisiones reales
argument-hint: <tarea>
---

Tarea solicitada: $ARGUMENTS

Sigue estos pasos en orden. No te saltes ninguno.

## 1. Lectura obligatoria

Lee, en este orden:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/canonical/STATUS.md`
4. `docs/implementation/PLAN.md`
5. `REPOSITORY_STATUS.md`

Estos cinco archivos definen el estado vigente, la vertical activa y las reglas obligatorias. No implementes nada que los contradiga.

## 2. Fuentes canónicas relevantes

- Localiza en `docs/canonical/` y `docs/decisions/` solo las fuentes que tengan relación directa con la tarea solicitada. No leas el resto.
- Para cualquier archivo `.docx`, léelo ejecutando:
  `python scripts/read_docx.py <ruta>`
  No abras un `.docx` de ninguna otra forma.
- No modifiques ningún archivo dentro de `docs/canonical/` bajo ninguna circunstancia.

## 3. Distingue aprobado de propuesto

Al leer cada fuente, clasifica cada afirmación relevante como una de:

- **Aprobado**: registrado como decisión vigente (p. ej. `docs/canonical/STATUS.md`, ATD-001 a ATD-012, o marcado explícitamente como aprobado aunque el nombre del archivo diga `PROPUESTO`).
- **Propuesta**: contenido marcado `PROPUESTO` o equivalente que no tenga una aprobación registrada.
- **Inferencia tuya**: cualquier cosa que estés deduciendo porque el documento no lo dice explícitamente.

Implementa únicamente lo clasificado como **Aprobado**. Si la tarea solicitada requiere algo Propuesto o depende de una Inferencia, detente y pide la decisión antes de tocar código (ver sección 7).

## 4. Implementación

- Trabaja solo sobre la vertical activa indicada por `docs/implementation/PLAN.md` y relevante para la tarea solicitada.
- No amplíes el alcance de Sirius 0.1, no cambies arquitectura, modelo de datos, privacidad, costes o alcance.
- Mantén las dependencias hacia dentro (presentación → aplicación → dominio); los adaptadores implementan puertos.
- No accedas a SQLite, OpenAI o secretos desde la interfaz. No guardes claves en código, SQLite, logs o texto plano.
- Añade o actualiza pruebas junto con cada cambio de comportamiento.
- Haz cambios pequeños, trazables y reversibles.

## 5. Verificación

- Ejecuta `/check`.
- Si algo falla, corrígelo y vuelve a ejecutar `/check`. Repite hasta que las cuatro comprobaciones (Ruff format, Ruff lint, mypy, pytest) pasen.
- No marques la tarea como terminada mientras `/check` siga fallando.

## 6. Revisión final

Antes de entregar, revisa el diff completo (`git diff`, `git status`) y confirma que:

- solo se tocaron los archivos necesarios para la tarea;
- no quedó código muerto, temporal o de depuración;
- la documentación de implementación (`docs/implementation/`) refleja el cambio si el comportamiento aprobado cambió.

## 7. Cuándo detenerte

Detente de inmediato y pide una decisión al usuario, sin seguir implementando, si la tarea implica:

- una decisión real de producto (algo no cubierto por lo Aprobado);
- una contradicción entre fuentes canónicas o entre la tarea pedida y la arquitectura aprobada;
- una operación peligrosa (borrado destructivo, cambios de credenciales, acceso a red, ampliar qué datos salen del equipo);
- una prueba que solo puede hacerse manualmente en el Windows real del usuario (Credential Manager, UI visual, clave real de OpenAI).

Describe con precisión qué decisión falta y por qué, sin proponerla como ya tomada.

## 8. Límites duros

- No hagas `git commit`.
- No hagas `git push`.
- No hagas `git merge` ni `git rebase`.
- No ejecutes ninguna operación destructiva (borrado recursivo forzado, `git reset --hard`, `git clean`, borrado de ramas).
- No toques `.claude/`, `.github/`, `.gitignore`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `PRIVATE_PROJECT.md` ni `docs/canonical/`.

## 9. Entrega final

Termina con un resumen que incluya, en este orden:

1. **Cambios**: qué se implementó y en qué archivos.
2. **Pruebas**: qué pruebas se añadieron o actualizaron y el resultado de `/check`.
3. **Pendientes**: qué queda fuera de esta tarea, qué requiere decisión del usuario, y qué requiere prueba manual.
