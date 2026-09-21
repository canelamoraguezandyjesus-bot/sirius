---
name: documento-con-lector
description: >-
  Qué se comprueba antes de crear o de dejar vivo un documento en `docs/`:
  quién lo lee y desde dónde se llega a él, si puede generarse del árbol en vez
  de escribirse a mano, qué fecha declara y con qué caduca, y qué se hace con el
  que ya no describe nada (archivar, nunca borrar). Cárgala antes de crear
  cualquier `.md` nuevo fuera de `docs/decisions/`, cuando encuentres un
  documento que contradice el árbol, cuando `MEMORIA.md` lo liste «sin fecha
  declarada», y al cerrar un trabajo que haya dejado documentos por el camino.
---

# Un documento tiene lector, o no se escribe

**Regla única: un documento sin lector nombrado y sin fecha declarada se pudre
solo. En esta casa se genera, se fecha o se archiva, y no se escribe uno nuevo
sin saber quién lo leerá y desde dónde llegará a él.**

## Por qué existe, con fechas

- **PROC-010 (20-09-2026)**: la base de conocimiento de `docs/operations/`
  auditaba el contrato **v1.1** cuando el vigente era **v1.10**, nueve
  versiones de retraso; el onboarding conservaba su «estado a 20 de julio».
  Nadie las manda leer: la entrada es `MEMORIA.md`. Veredicto: «sin dueño,
  resuelta de hecho por abandono».
- **ADR-207 (20-09-2026)**: dos mapas de julio archivados y el workflow de Word
  retirado. **ADR-210 (20-09-2026)**: incidencias que ya no describían nada,
  archivadas. **ADR-196**: la vista de memoria copiaba el corpus del que venía
  huyendo.
- La familia `pieza-sin-lector` suma **cinco ADR**, y `MEMORIA.md` cuenta hoy
  **97 de 150 documentos sin fecha declarada**.
- No habrá guardián de prosa: la guarda de citas se midió y **no** se amplió a
  `docs/` (ADR-190: 0 defectos reales, 23 falsos). Lo que impide la
  podredumbre es esta comprobación, no una prueba.

## Antes de crear uno

1. **Nombra el lector y el camino.** Quién lo lee (una sesión al abrir, el
   propietario, el motor) y desde dónde llega: la tabla «Dónde mirar» de
   `AGENTS.md`, `MEMORIA.md`, un ADR o una skill que lo cite. Sin camino no hay
   lector: entonces no se escribe, y lo que iba a decir va al ADR o a la skill
   que sí se leen.
2. **Si puede generarse, se genera.** `MEMORIA.md` se produce del árbol
   (ADR-171) y las vistas del registro de defectos y de decisiones también.
   Una lista que el árbol puede producir y alguien teclea es la familia
   `lista-a-mano`: se desactualiza en el primer cambio.
3. **Declara la fecha y de qué depende.** Una línea `- Fecha: AAAA-MM-DD` al
   principio: es lo que `sirius-memoria` lee, y sin ella el documento sale
   «sin fecha declarada». Si caduca con algo —una versión del contrato, un
   modelo, una medición—, dilo: «caduca con…», como hacen las de
   `docs/investigaciones/`.
4. **Un documento de estado no es evidencia** (`verificar-el-estado-real`): si
   el árbol dice otra cosa, se corrige en el mismo commit que lo descubre o
   se archiva.

## Cuando ya no describe nada

**Archivar, no borrar** (ADR-195; ADR-207 lo hizo con los dos mapas de julio):
el documento se queda donde está, con una nota al principio que diga que está
archivado, desde cuándo y qué lo sustituye, y deja de exigírsele la política
vigente. Nada de lo que un workflow o un ADR necesite se archiva sin resolver
antes esa dependencia. Qué documento concreto se archiva, si no es de tu
trabajo, se le pregunta al propietario en una línea: es él quien pidió que
podar fuera archivar.

## Qué NO hace esta skill

- **No es una guarda**: ninguna prueba mira la prosa de `docs/` (ADR-190). Lo
  que sí está vigilado son las rutas y los ADR que citan las skills y los ADR.
- **No cubre `docs/decisions/`**: los ADR tienen sus propias guardas (ADR-182,
  ADR-209 y la de citas) y su skill (`adr`).
- **No decide por el propietario qué se archiva** de lo que no es tuyo.
