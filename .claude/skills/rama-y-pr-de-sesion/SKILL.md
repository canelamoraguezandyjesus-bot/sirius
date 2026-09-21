---
name: rama-y-pr-de-sesion
description: >-
  Cómo una sesión abre su rama y su PR en este repositorio sin tropezar con lo
  que la sesión no puede hacer: rama nueva desde `main` recién traído para cada
  unidad, nunca sobre una rama cuya historia ya se fusionó aplastada; nada de
  forzar, borrar ni `merge` local (los deniega `.claude/settings.json`); el
  cuerpo de la PR con lo que los dos revisores necesitan; y el cierre aplastado
  con el título y el número. Cárgala antes de crear una rama, cuando un `git
  push` te rechace por no ser avance directo, cuando vayas a abrir o a
  actualizar una PR, y al retomar una rama que ya tuvo una PR fusionada.
---

# La rama y la PR de una sesión

**Regla única: cada unidad de trabajo nace en una rama nueva desde `main`
recién traído, y una rama cuya PR se fusionó aplastada no se reutiliza: no se
puede reiniciar sin forzar, y forzar está denegado.**

## Por qué existe, con fechas

- **20-09-2026**: la rama del paso 5 de la auditoría (PR #658) hubo que
  reiniciarla desde `main` porque la anterior conservaba la historia de la PR
  #652, ya fusionada aplastada.
- **21-09-2026**: el empujón de la tanda de skills (PR #659) a esa misma rama
  fue rechazado por no ser avance directo; `git push --force`, `--delete`,
  `git branch -D`, `git merge`, `git rebase` y `git reset --hard` están
  denegados en `.claude/settings.json`, así que la sesión no pudo reiniciarla
  ni borrarla y tuvo que preguntar al propietario para abrir una rama nueva.
  Esa pregunta es la que esta skill ahorra.
- **ADR-180**: los dos ADR-016 del registro nacieron en ramas distintas; el
  número de un ADR se calcula contra las ramas del remoto, no contra el árbol
  local (skill `adr`).

## Los pasos

1. **Antes de tocar nada**: la skill `obra-en-curso` (otras sesiones), y
   después
   `git fetch origin +main:refs/remotes/origin/main` —con destino explícito,
   porque un fetch a secas no mueve `origin/main` en un checkout de una sola
   rama (`verificar-el-estado-real`)— y
   `git switch -c claude/<lo-que-hace-la-unidad> origin/main`, que **falla si
   el nombre ya existe en local**, y eso es lo que se quiere. Nunca
   `checkout -B`: reinicia en silencio una rama local con commits sin empujar
   y los deja solo en el reflog (ronda 1 de Codex sobre la PR #660,
   21-09-2026). Antes de elegir el nombre, `git branch --list 'claude/*'` y
   `git ls-remote --heads origin 'claude/*'`: si ya existe, en local o en el
   remoto con historia fusionada, otro nombre (`-2`), y el cuerpo de la PR
   dice por qué.
2. **Lo que la sesión no puede hacer, y no intenta**: forzar, borrar ramas,
   `git merge`, `git rebase`, `git reset --hard`, `git clean`. Traer `main` a
   una rama con PR abierta se hace con «Update branch» de GitHub
   (`update_pull_request_branch`), no en local. Y si GitHub tampoco puede
   porque hay conflicto —el 21-09-2026 `main` avanzó con la PR #654 mientras
   la #660 estaba en revisión, y chocaron `MEMORIA.md` y el registro de
   defectos—, la salida es la misma que para la historia fusionada: rama
   nueva desde `main` recién traído y **solo tu diff** reaplicado sobre ella,
   en este orden. Primero, qué rutas tocaron los dos lados:
   `comm -12 <(git diff --name-only <base> origin/main | sort) <(git diff
   --name-only <base> <head-anterior> | sort)`. Las rutas que `main` no tocó
   se restauran enteras (`git checkout <head-anterior> -- <rutas>`); las que
   tocaron los dos, **nunca**: restaurar el fichero entero sustituye lo que
   llegó de `main` por tu instantánea vieja. En esas, lo generado se
   regenera con su herramienta (`MEMORIA.md`), lo que se añade a un registro
   se añade otra vez detrás de lo que llegó, y el resto se reaplica hunk a
   hunk (`git diff <base> <head-anterior> -- <ruta> | git apply`, y a mano lo
   que no aplique limpio). Después, PR nueva que cierra la anterior diciendo
   por qué. Sin `merge`, sin `rebase` y sin `cherry-pick` de los commits de
   `main`: la rama nueva solo lleva lo tuyo. Reiniciar una rama con historia
   fusionada solo puede hacerlo el propietario; la salida de la sesión es la
   rama nueva.
3. **Los commits**: el mensaje dice qué cambia y por qué, con lo comprobado y
   sus cifras; el número del ADR sale de `scripts/siguiente_adr.py`; si el
   cambio toca `docs/` o un registro, `MEMORIA.md` se regenera en el mismo
   commit (ADR-171; skill `cadena-de-comprobacion`).
4. **La PR**: el título dice lo que trae, con el ADR entre paréntesis. El
   cuerpo lleva tres bloques y se actualiza en cada ronda, porque es lo que los
   dos revisores y el propietario leen: **Qué trae** (una viñeta por pieza, con
   su porqué), **Revisión externa** (cada ronda de Codex, sobre qué head y qué
   se corrigió) y **Comprobaciones** (cifras, no adjetivos: pruebas, tiempo y
   qué ficheros pasaron por el comprobador de documentos).
5. **Después de empujar**: pedir la revisión externa (`revision-externa`),
   suscribirse a la actividad de la PR si tienes la herramienta, y dejar un
   repaso programado por si los avisos fallan (`modo-nocturno`, regla 2).
6. **El cierre**: aplastado, con el head exacto que Codex y Quality aprobaron
   como `expectedHeadSha`, título «<lo que trae> (#N)», y solo cuando se
   cumplen las condiciones de «Cuándo se fusiona» de `revision-externa`.
   Después, la rama no se vuelve a tocar.

## Qué NO hace esta skill

- **No sustituye a `obra-en-curso`** (quién más trabaja) **ni a
  `revision-externa`** (cuándo se fusiona): las enlaza.
- **No borra ramas**: no puede. Las que sobran se le dan al propietario en
  lote, con el comando (`comandos-para-su-ordenador`).
- **No cubre las PR del motor**: esas siguen el contrato operativo y las
  fusiona `merge-sirius-work.yml`.
