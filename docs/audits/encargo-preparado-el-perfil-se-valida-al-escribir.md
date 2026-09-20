# Encargo preparado y SIN LANZAR — el `Perfil:` se valida al escribir

Redactado el 20-09-2026. **No se ha lanzado ninguna incidencia con esto.**
Se lanza sólo cuando Andy lo diga.

Cuerpo listo para copiar a una incidencia nueva (por debajo de la línea).
Validado con `scripts/automation/validate_issue_body.py`: **exit 0**.

---

## Work ID

`WI-20260920-PERFIL-AL-ESCRIBIR`

## Bloque

Motor de trabajo — automatización del ciclo. Guardián candidato número 6 de la
lista que empezó en la entrada 107 de la bitácora de auditoría.

Perfil: implementer@4

## Objetivo

Que un cuerpo de incidencia **sin `Perfil: rol@N`**, o con un `rol@N` que no
está en el manifiesto, **se rechace al escribirlo** en vez de morir al
ejecutarlo.

**El defecto, medido el 20-09-2026.** La incidencia #653 se activó con un
cuerpo que `validate_issue_body.py` aprobó con **exit 0** y que no declaraba
`Perfil:`. El ciclo **paró a los 6 segundos**: `resolver_prompt.py` falla
cerrado, con razón, porque sin `Perfil:` no puede saber qué prompt ejecutar.
Coste: un run consumido, la incidencia marcada, y un `continua` para revivirla
—que además destapó el defecto de la entrada 126—.

Las dos herramientas **no comprueban lo mismo**: `validate_issue_body.py` mira
once encabezados y una longitud mínima; `resolver_prompt.py` exige `Perfil:` y
lo resuelve contra `scripts/automation/prompts/manifiesto.json` verificando
`sha256`. Un cuerpo puede pasar la primera y reventar en la segunda, y eso es
exactamente lo que pasó.

## Base y dependencias

- Rama base: `main`.
- `scripts/automation/validate_issue_body.py` — el validador estructural.
- `scripts/automation/resolver_prompt.py` — ya hace la resolución correcta:
  parsea con `sirius_engine.profile_field.parse_perfil_field`, busca
  `rol@N` en el carril y verifica `sha256` byte a byte. **Es la referencia: no
  se reimplementa, se reutiliza.**
- `scripts/automation/prompts/manifiesto.json` — carriles `ejecucion` y
  `revision`.
- `docs/implementation/work_engine/perfiles/*.yml` — declaran el `version`
  vigente de cada rol.

## Alcance permitido

1. **`scripts/automation/validate_issue_body.py`**: añadir la comprobación del
   campo `Perfil:`. Debe (a) exigir que el campo exista, (b) resolverlo contra
   el manifiesto en el carril `ejecucion`, y (c) fallar con un mensaje que diga
   **qué falta y qué claves hay registradas**, como ya hace
   `ResolucionImposible`.
2. **Un aviso, no un fallo, cuando la versión declarada no es la vigente**: si
   el cuerpo dice `implementer@2` y `perfiles/implementer.yml` dice
   `version: 4`, el cuerpo es válido pero **se avisa por la salida de error**.
   Motivo: #650 se fusionó el 19-09 declarando `implementer@2` con el perfil
   vigente en 4, y nadie se enteró. **Avisar, no rechazar**: puede haber una
   razón para fijar una versión vieja, y esta incidencia no la conoce.
3. **Las pruebas de ese guion**, incluida una que fije que **el cuerpo real de
   #653 tal como se escribió** —sin `Perfil:`— ahora se rechaza.
4. **El ADR**, con `scripts/siguiente_adr.py`.

## Fuera de alcance

- **`resolver_prompt.py`**: no se toca. Funciona, falla cerrado y es la
  referencia. Duplicar su lógica en vez de reutilizarla sería el defecto
  `dos-verdades-que-pueden-divergir` que la bitácora ya tiene fichado.
- **El manifiesto y los prompts**: no se registran versiones nuevas aquí.
- **El carril `revision`**: el validador se usa antes de ejecutar, no antes de
  revisar. Si hiciera falta, es otro encargo.
- **Los workflows de `.github/`**: el arreglo va en el guion, que es lo que
  ellos llaman.
- El corpus, `resultado_esperado`, adjudicaciones, `memory_gates.py`,
  `settings.json`, `STATUS.md`, `docs/canonical/**`.
- **No se abre ningún interruptor.**

## Requisitos y pruebas de aceptación

1. Un cuerpo **sin** línea `Perfil:` → **exit 1**, con un mensaje que lo diga.
2. Un cuerpo con `Perfil: implementer@99` → **exit 1**, y el mensaje **enumera
   las claves registradas** del carril.
3. Un cuerpo con `Perfil: implementer@4` y las once secciones → **exit 0**, sin
   aviso.
4. Un cuerpo con `Perfil: implementer@2` (registrado, pero no vigente) →
   **exit 0** **y un aviso** por la salida de error nombrando la versión
   vigente.
5. **Una prueba vista fallar antes del cambio** (ADR-001) que use el cuerpo de
   #653 tal como se escribió. Primera línea del fallo, transcrita en el ADR.
6. El guion sigue corriendo con el `python3` a secas del runner —sólo stdlib—,
   como ya exige `test_sirius_runner_python_compat.py`.

## Validaciones obligatorias

Una sola invocación de `pwsh -File scripts/check.ps1`, en primer plano, sin
partir `pytest` en tandas (ADR-145). Código de salida y la terna completa
transcritos en la sección «Comprobación» del ADR, anclados al árbol que los
produjo (ADR-154).

## Rama base

`main`.

## Condiciones de parada

- Si reutilizar `resolver_prompt.resolver_prompt` obliga a que el validador
  deje de ser sólo-stdlib o deje de correr con el `python3` del runner:
  **parar** y decirlo. Ese requisito es anterior a este encargo.
- Si aparece un cuerpo real en el histórico que sería rechazado por la regla
  nueva y **no debería**: parar y enseñarlo, antes de endurecer nada.
- Dos rondas con defectos de la misma familia: parar y buscar la raíz
  (ADR-001).

## Salvaguardas

- No se toca `resolver_prompt.py`, ni el manifiesto, ni ningún prompt.
- No se fusiona nada; la fusión es gesto del propietario.
- No se abre ningún interruptor de `memory_gates.py`.
- No se inventa ninguna cifra: este encargo no mide el banco.
