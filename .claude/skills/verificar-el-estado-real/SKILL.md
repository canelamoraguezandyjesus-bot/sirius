---
name: verificar-el-estado-real
description: >-
  Antes de afirmar que algo está hecho, de actualizar un registro de estado o de
  planificar sobre «lo que falta»: comprobar el estado real contra el árbol de
  main, las PR y lo que el propietario dice, porque los documentos de esta casa
  han afirmado más de una vez lo que no era, y él era quien lo sabía. Cárgala
  antes de tocar un registro de estado o de decir «esto ya está», al abrir una
  sesión sobre una rama vieja, y siempre que él te corrija con «eso ya lo
  hicimos» o «¿tú sabes bien lo que se ha hecho?».
---

# Verificar el estado real

**Regla única: un documento que dice TERMINADO no es evidencia. El árbol de
`main`, la PR fusionada y la prueba que él hizo a mano, sí.**

## Las veces que el documento mintió y él tenía razón

- 10-08-2026 22:08: el registro decía «V7 — implementación automatizada
  terminada»; él: «¿tú sabes bien lo que se ha hecho? Porque creo que no lo
  tienes. Me dices que la memoria útil está hecha, pero todavía estamos con el
  benchmark». Model Studio sí funcionaba, en una rama sin fusionar.
- 14-08-2026 14:51: «todo eso ya lo hicimos» sobre las partidas de B14; el
  modelo retiró su plan y luego su hipótesis de recambio: «tenías razón en
  todo».
- 14-08-2026 15:28: una sesión reconcilió el estado desde una rama 28 commits
  atrás y encargó construir un bloque cerrado cuatro días antes (#165). De ahí
  ADR-016: el estado se lee de `main`.
- 17-08-2026 15:00-15:47: la clave real, el cierre forzado y la partida 3 ya
  estaban probados por él; la voz estaba fuera del alcance de 0.1 desde la
  línea 50 del registro.
- 19-08-2026 00:44: «12 de 13 piezas ya existen» era falso, y la afirmación
  falsa apareció siete veces en tres documentos, una de ellas como corrección.

Seis correcciones suyas medidas, seis acertadas; en cinco, el hecho no estaba
en `main`: estaba en una rama ajena, en una prueba manual suya o en su cabeza
(`AGENTS.md`, regla 5).

## Los cinco pasos

1. **El estado se lee de `main` en el remoto**, no de la rama en la que estás
   (ADR-016), y solo recién traído con destino explícito:
   `git fetch origin +main:refs/remotes/origin/main` y después
   `git rev-parse origin/main`. Un `git fetch origin main` a secas no sirve:
   en un checkout de una sola rama —el de la nube— deja `origin/main` como
   estaba, inexistente o parado, y solo mueve `FETCH_HEAD` (reproducido el
   21-09-2026 en un repositorio de prueba: tras el fetch a secas,
   `origin/main` «no existe» y `FETCH_HEAD` ya estaba en el sha remoto). Si no
   se puede traer, se lee en GitHub, y si tampoco, no se afirma el estado. Las
   otras sesiones se miran antes (skill `obra-en-curso`).
2. **Para cada «hecho»**: ¿hay PR fusionada? ¿Hay prueba que lo demuestre? ¿O
   solo lo dice un documento? Solo las dos primeras cuentan.
3. **Lo que él afirma probado a mano se toma como probado**, y se escribe así:
   «probado a mano por el propietario, fecha». No se le pide que lo demuestre
   otra vez (skill `hablar-con-el-propietario`, disparador 3).
4. **Lo que no puedas demostrar se escribe como no demostrado**, nunca como
   hecho. El informe de Windows del 10-08-2026 (14:49) lo hizo bien: «77
   comprobaciones, 0 fallos, 3 omitidas» y, aparte, «NO se ha demostrado:
   onboarding sin clave».
5. **Si un documento afirma lo que no es, se corrige en el mismo commit** en
   que se descubre, y se dice qué decía y qué dice ahora: dejarlo es la familia
   `prosa-que-el-cambio-deja-falsa`.

## Qué NO hace esta skill

- **No sustituye la validación en Windows real** (ficha PROC-008 de la
  auditoría): «probado a mano por él» es evidencia de él, no una prueba
  automatizada, y así se anota.
- **No mira las otras sesiones**: eso es `obra-en-curso`.
- **No decide qué está en alcance**: si algo está hecho pero fuera de alcance,
  se dice, y el alcance lo fija él (ADR-204).
