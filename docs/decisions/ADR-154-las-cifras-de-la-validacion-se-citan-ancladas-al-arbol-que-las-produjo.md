# ADR-154 — Las cifras de la validación se citan ancladas al árbol que las produjo

- Estado: PROPUESTO
- Fecha: 2026-09-06
- Aprobación: la fusión de esta PR por el propietario (ficha del operador;
  no toca `.github/**`: vive en dos prompts, el manifiesto de prompts, el
  perfil del implementador y sus guardianes).

Esta es también la nota de arranque de la rama
`claude/adr-154-cifras-ancladas-al-arbol`, publicada antes del primer
cambio, con las cuatro preguntas de la disciplina de evidencia (ADR-001).

## Contexto y problema

Los ADR de los encargos citan la terna de `pytest` de la validación
obligatoria («4997 passed, 16 skipped, 2 xfailed») como afirmación sobre «el
árbol de esta rama». Esa cifra caduca en cuanto la rama recibe commits que no
son suyos, y desde el 06-09 los recibe por diseño: el guion de fusión
(`sirius_merge_on_command.sh`) exige que la PR esté al día con `main` —«su
Quality se calculó contra una base que ya no existe»—, así que toda PR que
espere detrás de otra pasa por un «Update branch» antes de fusionarse. Ese
merge trae de `main` pruebas nuevas y no toca el ADR.

El dato: #550, ronda 2 (run 34013060064, 05:12 UTC). La PR #552 fue aprobada
sobre `823d3ac` con su terna correcta; el «Update branch» de las 04:13 trajo
las 12 pruebas de ADR-152; ADR-142 devolvió el head a revisión y el revisor
encontró exactamente eso (CLAUDE-CR-151-004, baja): «la cifra ya no describe
el árbol que se va a fusionar». Codex aprobó. Coste: una ronda de corrector y
otra de revisión —alrededor de una hora— por una línea de documentación, y
se repetirá con cada actualización de rama. Es la deuda 11 de la bitácora del
ciclo («los ADR citan recuentos de la suite completa, que se desfasan con
cada merge a `main`»), que ya costó tres rondas el 04-09 (entrada 29).

El propio revisor dio la forma que no caduca: anclar la cifra al head sobre el
que se midió y, si existe, al run de Quality de ese head. Una cifra anclada
sigue siendo verdad de su árbol después de cualquier merge; lo que engaña es
una cifra sin árbol presentada como la del head vigente.

## Nota de arranque (cuatro preguntas, ADR-001)

1. **¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
   observar el fallo?** Vive en cómo los roles escriben la evidencia, y eso lo
   gobiernan sus prompts (la lección exacta de ADR-145: una regla que el
   agente no lee en su prompt no existe para él). El arreglo va a la viñeta
   de validación de `corrector.md` y del prompt vigente del implementador. Se
   observa en el texto de los ADR de los encargos siguientes y en la ausencia
   del hallazgo «la cifra ya no describe el árbol».
2. **¿Qué NO garantiza esto?** No hace verdad ninguna cifra: la ancla dice de
   qué árbol es, no que se midiera bien (eso es ADR-153). No evita la ronda de
   revisión que ADR-142 exige tras un «Update branch»: esa ronda es correcta
   —el head es otro—; lo que evita es que esa ronda encuentre un hallazgo
   fabricado por el propio merge. No cambia a los revisores: describen
   Quality, no exigen una forma concreta de cifra; con la cifra anclada no
   tienen nada que objetar, como el propio hallazgo reconoce en su opción (b).
3. **Criterio de parada (decidido antes de ver ningún resultado).** El
   guardián nuevo ve FALLAR los dos prompts vigentes y pasa con el cambio;
   el implementador se versiona por H-28 (`implementer@4`, fichero nuevo,
   filas en los dos carriles del manifiesto, perfil a 4, `implementer-v3.md`
   intacto en sus bytes) y todos los guardianes del manifiesto y del perfil
   quedan en verde; `corrector.md` se edita in situ como en ADR-135 y
   ADR-145; la cadena completa termina en 0. En vivo: el siguiente encargo
   nace con `implementer@4` y su ADR ancla la terna; la siguiente ronda de
   corrector ancla la suya; y un «Update branch» posterior a una aprobación
   no produce un hallazgo sobre la cifra.
4. **¿Qué hace esto imposible, en vez de improbable?** Que un agente que obedece
   su prompt escriba una terna sin árbol: la regla está en la misma viñeta que
   exige la invocación única, y el guardián prohíbe que desaparezca de
   cualquiera de los dos prompts. Lo que NO se hace imposible es que un agente
   desobedezca: eso lo detecta el revisor, como hoy.

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque.

## Opciones consideradas

1. **Anclar la cifra al árbol en los prompts de los dos roles que validan**
   (elegida). Una frase en la viñeta de validación; el implementador se
   versiona por H-28.
2. **Que el corrector reejecute el script tras cada «Update branch» y
   reescriba la terna.** Descartada: repite nueve minutos de validación por
   una cifra que ya era verdad, y necesita una ronda de corrector para
   hacerlo, que es justo el coste que se quiere evitar.
3. **Que los ADR no citen recuentos.** Descartada: la terna es evidencia
   útil (delata suites partidas y pruebas no recolectadas); lo que sobra no
   es la cifra sino la falta de ancla.
4. **Un guardián que compare el recuento del ADR con `pytest`.** Descartada
   por el propio revisor: se rompería con cada actualización de rama, que es
   exactamente el defecto que se corrige.

## Decisión

- `scripts/automation/prompts/corrector.md` (in situ, como ADR-135/145): la
  viñeta de validación exige transcribir la terna y el código de salida
  **anclados al árbol** («sobre el árbol de `<sha corto>`», y el run de
  Quality de ese head si existe), declara que una actualización de la rama
  no invalida una cifra anclada ni obliga a repetir el script, y prohíbe
  presentar una cifra sin árbol como la del head vigente.
- `scripts/automation/prompts/implementer-v4.md` (H-28): el texto de
  `implementer-v3.md` con la misma regla en su viñeta de validación;
  `implementer@4` en los dos carriles del manifiesto (ejecución → el fichero
  nuevo; revisión → `reviewer-v2.md`, igual que `@2` y `@3`); perfil a 4 con
  `procedimiento_ref` al fichero nuevo; `implementer-v3.md` intacto.
- Guardián nuevo en `tests/automation/test_prompts_de_rol.py`: los dos
  prompts que validan llevan la regla de la cifra anclada.

## Comprobación que la sostiene

- Rojo previo, visto fallar: el guardián nuevo contra los prompts vigentes
  de `main`; y su resultado con el cambio, junto con los guardianes del
  manifiesto, del perfil y de la proyección: transcritos en el cuerpo de la
  PR.
- Cadena completa como una sola invocación sobre el árbol final: transcrita
  en el cuerpo de la PR (sin `pwsh` en el contenedor, los cuatro comandos
  bajo `bash -ec` con el código capturado). Y, coherente con esta misma
  decisión, la cifra se cita allí anclada a su árbol.
- Lo que NO se ha medido: el caso en vivo (criterio 3).

## Consecuencias

- Un «Update branch» deja de fabricar hallazgos sobre la evidencia: la
  ronda de ADR-142 revisa el head nuevo, no una cifra caducada.
- Los ADR ganan una convención estable para citar recuentos; la deuda 11 de
  la bitácora se salda en cuanto el primer encargo la ejerza.
- Los encargos ya despachados con `implementer@3` conservan su texto
  congelado (H-28); los nuevos nacen con `@4`.

## Alternativas descartadas y por qué

Ver «Opciones consideradas».
