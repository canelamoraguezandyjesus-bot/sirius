---
name: revision-externa
description: >-
  Cómo una sesión pasa su propia PR por Codex, el segundo revisor de esta casa,
  sin que el propietario haga de correo: cómo se pide, qué devuelve, cómo se
  verifica cada hallazgo antes de aceptarlo, cómo se cuentan las rondas para no
  caer en el goteo, cuándo se vuelve a pedir y cuándo se fusiona. Cárgala
  cuando una PR tuya tenga Quality en verde y toque pedir revisión, cuando
  llegue una revisión de Codex a una PR que llevas, y cuando el propietario diga
  «pásala por Codex» o «a ver qué opina».
---

# La revisión externa, sin correo

**Regla única: el revisor está fuera, el corrector dentro, y el que cuenta las
rondas eres tú. Si nadie las cuenta, vuelve la PR #576: cuatro rondas en un
día con el mismo fallo.**

## Cómo se pide

Un comentario en la PR con `@codex review`, el head exacto que quieres
revisado y qué se espera: solo defectos concretos con severidad, fichero y
línea, problema observado, comportamiento esperado y evidencia. Nunca «@codex
address that feedback»: Codex revisa, no modifica (regla del 11-08-2026,
ADR-156). No uses el marcador oculto de la tubería del motor
(`sirius-codex-review:<head>`): es suyo y comprueba quién lo emitió.

Cada petición gasta cuota del propietario, y esa cuota se agota («Codex se
quedó sin uso otra vez», 12-09-2026 16:41). Se pide una vez por head, después
de Quality en verde, nunca por cada commit.

## Qué devuelve, y qué cuenta como pasada limpia

- Una review con «Reviewed commit: <sha>» cuyo cuerpo dice «Here are some
  automated review suggestions»: **hay hallazgos**, y están en los hilos de las
  líneas afectadas con insignia P1, P2 o P3, no en el cuerpo. Se leen los hilos
  (PR #659, 21-09-2026: un cuerpo sin una sola insignia y cuatro hallazgos en
  los hilos).
- Un comentario «Codex Review: Didn't find any major issues» o un 👍 sobre tu
  petición: la pasada está limpia **solo si pasa las mismas comprobaciones que
  el recolector del motor** (`docs/implementation/AUTOMATION_OPERATING_CONTRACT.md`,
  «Ambos revisores deben revisar exactamente el mismo SHA»), y las cinco fallan
  cerrado:
  1. lo firma el conector oficial, `chatgpt-codex-connector[bot]`; una
     reacción o una frase de cualquier otra cuenta no es señal;
  2. es posterior a tu comentario `@codex review`, y el 👍 está sobre ese
     comentario, no en otro sitio;
  3. se refiere al head que pediste: en una review o un comentario, el
     «Reviewed commit:» o el `commit_id` es el head actual de la PR; un 👍
     no lleva sha, así que vale solo si está sobre tu comentario disparador
     exacto, no hay ninguna review del conector posterior a ese disparador y
     el head de la PR sigue siendo el que pediste (si empujaste después, no
     vale): es como lo correlaciona el recolector
     (`scripts/automation/sirius_codex_review.py`, `_check_reactions`);
  4. ningún otro comentario ni review del conector sobre ese mismo head trae
     hallazgos: se miran **todos**, no el último; basta uno con insignia para
     que la pasada no sea limpia, aunque otro diga que no encontró nada;
  5. la frase es la fórmula conocida («did(n't) find any [major] issues»);
     otra redacción no aprueba, se lee entera y, en la duda, no es limpia.

  Si falla cualquiera de las cinco, la pasada no está limpia y no se fusiona.

Un comentario que diga «este hallazgo llega tarde por goteo del revisor» es el
propio revisor reconociendo que mira líneas ya revisadas: cuenta como ronda
igual.

## Qué se hace con cada hallazgo (ADR-001, §4)

1. Se verifica contra el código antes de aceptarlo. En la PR #658 (21-09-2026)
   los cuatro P2 eran ciertos; en la PR #136 dos hallazgos válidos traían el
   mecanismo equivocado y aceptarlos tal cual habría empeorado las cosas.
2. Se arregla en el mínimo **y en el límite que el hallazgo marca**: si dice
   «elimina solo X», se elimina X, no se sustituye por una versión más suave
   de X; y si describe un caso que no es el que tienes delante —un checkout
   de una sola rama, una reacción sin sha—, se reproduce ese caso antes de
   escribir el arreglo. En la PR #659 (21-09-2026) la ronda 2 devolvió tres
   de los cuatro arreglos de la ronda 1 por eso: dos a medias y uno que, por
   endurecer, dejaba un canal imposible. Después se prueba la propiedad —si
   es una guarda, mutación en memoria: quitar lo que vigila y ver que
   falla—, se pasa la cadena (skill `cadena-de-comprobacion`) y se empuja.
3. Se resuelve el hilo y se vuelve a pedir la revisión **sobre el head nuevo**,
   una sola vez.
4. Se anota en el ADR de la rama qué ronda encontró qué, con el sha.

## Contar las rondas

Dos rondas seguidas con hallazgos de la misma familia → se deja de parchear y
se busca la raíz (ADR-001, §2). Las rondas de la PR #576 el 08-09-2026 fueron
cinco → cuatro → tres → una, todas «la puerta afirma lo que no ha comprobado»,
y nadie paró porque el propietario traía cada ronda a mano. El motor tiene su
detector de familia (ADR-121, ADR-197, ADR-199); una PR de sesión no: el
detector eres tú, y lo escribes en el ADR.

## Cuándo se fusiona

Las comprobaciones previas a la fusión son las del contrato operativo
(`docs/implementation/AUTOMATION_OPERATING_CONTRACT.md`, §14.2, «Qué NO
cambia»): las mismas que aplica el motor, menos la etiqueta y la incidencia,
que son del ciclo. Para una PR de sesión son cinco, todas sobre el head
vigente:

1. la PR está abierta, no es borrador y no está fusionada;
2. la pasada de Codex es limpia según las cinco comprobaciones de arriba, y el
   head que revisó es el head actual;
3. Quality está en verde sobre ese head exacto;
4. no hay conflicto con `main`;
5. la rama no va por detrás de `main`: la punta de `main` es ancestro del head
   (ADR-191: una rama entra a revisión solo si `main` ya está dentro de ella,
   y omitirlo dejó `main` en rojo). Se comprueba con
   `git fetch origin +main:refs/remotes/origin/main` y
   `git rev-list --count origin/main ^HEAD`, que tiene que dar 0. Si no da 0,
   se trae `main` a la rama (desde la nube, con «Update branch» de GitHub:
   la sesión no puede hacer `git merge`), se vuelve a pasar la cadena y se
   pide otra pasada, porque la combinación que aterrizará es otra.

Si el contrato cambia esa lista, manda el contrato y se corrige esta sección,
no al revés. Cumplidas las cinco, se fusiona aplastando, como `main`, con la
autorización que ya existe (ADR-205 para el ciclo; para las PR de sesión, la
delegación del propietario del 20-09-2026: «que puedas fusionar todo simple
cuando ambos revisores den el visto bueno»). Si él ha dicho «a ver qué
opina», se le cuenta lo que dijo Codex y lo que se corrigió, en cinco líneas,
y se fusiona.

## Qué NO hace esta skill

- **No sustituye a la tubería del motor**
  (`scripts/automation/sirius_codex_review.py`): eso es para las PR del ciclo;
  esto es para las PR de sesión.
- **No aprueba nada por el propietario**: si la PR cambia producto, dinero o
  salud, la fusión sigue siendo suya (ADR-204).
- **No hace a Codex infalible**: una pasada limpia dice que no vio nada, no que
  no haya nada. La cadena de comprobación y la mutación siguen siendo
  obligatorias.
- **No cuenta las rondas por ti**: no hay guarda; hay un sitio donde escribirlas
  (el ADR de la rama) y una regla (dos, y se para).
