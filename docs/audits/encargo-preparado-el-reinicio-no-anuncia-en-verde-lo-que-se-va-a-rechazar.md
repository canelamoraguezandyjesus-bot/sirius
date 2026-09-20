# Encargo preparado y SIN LANZAR — el reinicio no anuncia en verde lo que se va a rechazar

Redactado el 20-09-2026. **No se ha lanzado ninguna incidencia con esto.**

Cuerpo listo para copiar (por debajo de la línea). Validado con **las dos**
herramientas: `validate_issue_body.py` → exit 0, y `resolver_prompt.py --carril
ejecucion` → `implementer-v4.md`, exit 0.

---

## Work ID

`WI-20260920-REINICIO-HONESTO`

## Bloque

Motor de trabajo — automatización del ciclo. Guardián candidato número 7 de la
lista que empezó en la entrada 107 de la bitácora de auditoría.

Perfil: implementer@4

## Objetivo

Que un `continua` sobre una parada **anterior a la PR** no anuncie en verde un
reinicio **que va a rechazarse a sí mismo** y dejar la incidencia sin ninguna
etiqueta, inerte y muda.

**El defecto, medido el 20-09-2026 sobre #653.** El camino es éste, y está
todo en el árbol:

1. `sirius_resume_on_command.sh:171` declara el principio —«reanudar es reponer
   el **evento** que la parada consumió»— y `:182` lo aplica: para el rol
   `implementer` repone **una sola** etiqueta, `sirius:implement-requested`.
2. `:325` publica el permiso **en verde**: «lo que se autoriza es repetir desde
   cero la fase que se paró».
3. Pero la activación exige **las dos** etiquetas. Sin `sirius:planned`,
   `sirius_validate_activation.sh:136` rechaza por `sin-planned`.
4. Y `:88` **retira** `sirius:implement-requested` después de rechazar.

Resultado: la incidencia se queda **con cero etiquetas `sirius:`**. No hay nada
que la despierte y **nadie recibe un aviso**, porque el estado no «cambia» a
ningún sitio: simplemente desaparece. Lo detecté comprobando a mano.

**El agravante**: un vigilante que sólo habla cuando el estado cambia produce
**silencio**, y el silencio se lee como progreso.

## Base y dependencias

- Rama base: `main`.
- `scripts/automation/sirius_resume_on_command.sh` — líneas 171-182 (qué
  repone), 301-344 (el permiso escrito, que va **antes** de reponer), 349 (la
  reposición).
- `scripts/automation/sirius_validate_activation.sh` — líneas 136-139 (rechazo
  `sin-planned`) y 88 (retirada de la etiqueta disparadora).
- **`sirius_validate_activation.sh:12`**: «NO corrige automáticamente: añadir
  `sirius:planned` equivaldría a aprobar». **Esa salvaguarda es deliberada y
  este encargo NO la toca.**

## Alcance permitido

1. **`scripts/automation/sirius_resume_on_command.sh`**: antes de publicar el
   permiso, comprobar si la incidencia tiene `sirius:planned`. Si **no** la
   tiene y la etiqueta destino es una que exige el par:
   - **no publicar el mensaje en verde**;
   - publicar en su lugar uno que diga **qué falta y por qué no lo puede poner
     una automatización**, con el mismo texto que ya usa el rechazo
     `sin-planned` («certifica que el alcance está definido y aprobado»);
   - **no reponer la etiqueta disparadora**, para no consumir el evento ni
     dejar la incidencia peor que antes.
2. **Las pruebas de ese guion**: una que reproduzca el camino de #653 —parada
   pre-PR, sin `planned`, `continua` del propietario— y fije que la incidencia
   **conserva las etiquetas que tenía** y recibe un mensaje que nombra
   `sirius:planned`.
3. **El ADR**, con `scripts/siguiente_adr.py`.

## Fuera de alcance

- **Añadir `sirius:planned` automáticamente.** Es la salvaguarda de la
  incidencia #60 y de `sirius_validate_activation.sh:12`. Si algún día se
  decide que un `continua` del propietario certifica el alcance tanto como
  `planned`, **es una decisión suya y otro encargo**, no éste.
- **`sirius_validate_activation.sh`**: no se toca. Rechaza bien; el defecto
  está en anunciar antes de comprobar.
- El comportamiento sobre paradas **posteriores** a la PR, que funciona.
- El corpus, `resultado_esperado`, adjudicaciones, `memory_gates.py`,
  `settings.json`, `STATUS.md`, `docs/canonical/**`.
- **No se abre ningún interruptor.**

## Requisitos y pruebas de aceptación

1. Parada pre-PR **sin** `sirius:planned` + `continua` → **no** se repone
   ninguna etiqueta, y se publica un mensaje que nombra `sirius:planned` y dice
   que ninguna automatización puede aplicarla.
2. Parada pre-PR **con** `sirius:planned` presente + `continua` → el
   comportamiento de hoy, intacto.
3. Parada posterior a la PR → el comportamiento de hoy, intacto.
4. **La incidencia nunca termina sin ninguna etiqueta `sirius:`** por este
   camino. Es la propiedad que este encargo existe para garantizar.
5. **Una prueba vista fallar antes del cambio** (ADR-001) sobre el caso 1.
   Primera línea del fallo, transcrita en el ADR.

## Validaciones obligatorias

Una sola invocación de `pwsh -File scripts/check.ps1`, en primer plano, sin
partir `pytest` en tandas (ADR-145). Código de salida y terna completa
transcritos en la sección «Comprobación» del ADR, anclados al árbol que los
produjo (ADR-154).

## Rama base

`main`.

## Condiciones de parada

- Si la comprobación de `sirius:planned` no se puede hacer sin una llamada
  extra a la API que pueda fallar y dejar el camino peor: **parar** y decirlo,
  con el modo de fallo escrito.
- Si aparece un rol o una parada donde «la etiqueta destino exige el par» no
  sea decidible desde el guion: parar y enseñarlo en vez de adivinar.
- Dos rondas con defectos de la misma familia: parar y buscar la raíz
  (ADR-001).

## Salvaguardas

- **Ninguna automatización aplica `sirius:planned`.** Ni aquí ni en ningún
  camino que este encargo toque.
- No se toca `sirius_validate_activation.sh`.
- No se fusiona nada; la fusión es gesto del propietario.
- No se abre ningún interruptor de `memory_gates.py`.
