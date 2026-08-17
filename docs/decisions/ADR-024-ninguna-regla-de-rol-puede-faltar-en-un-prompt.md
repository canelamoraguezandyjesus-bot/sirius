# ADR-024 — Extender al implementador las tres reglas de rol y vigilarlas con una prueba que recorre el directorio de prompts

- Estado: PROPUESTO
- Fecha: 2026-08-17
- Aprobación: la fusión de la PR de esta rama por el propietario.

## Contexto y problema

Tercera ronda perdida, tercer rol, misma causa. Los tres cerraron el turno creyendo que la
conversación seguía, y los tres con `terminal_reason: completed` — ninguno se quedó sin
turnos ni sin tiempo:

| Rol | Run | Último mensaje del modelo |
|---|---|---|
| Corrector | 31953500564 | «Espero a que termine el `pytest` en segundo plano […] y aviso» |
| Revisor | 31963233730 | «Standing by for the three background review agents to report back» |
| Implementador | 31985897583 | «I'm waiting for the background pytest run to finish; will resume automatically» |

El implementador trabajó 20 min 27 s de los 60 del job y no escribió veredicto: la ronda
murió en `sin-veredicto` —silencio, no diagnóstico— porque `implementer.md` era el único
de los tres sin veredicto provisional. Además intentó instalarse `uv` con
`curl -sSf https://astral.sh/uv/install.sh`, denegado, igual que el revisor el día anterior.

**Esta ronda era previsible y está registrada como tal.** ADR-021 escribió, al corregir el
corrector: «No se toca `reviewer.md` ni `implementer.md`: la misma trampa podría afectarles,
pero no hay evidencia de que les haya ocurrido, y parchear sin caso delante es la familia de
defecto que este repositorio lleva corrigiendo. Si aparece, se corrige entonces, con su
run». Le ocurrió al revisor doce horas después (ADR-022) y al implementador doce horas más
tarde. **Esperar al caso costó dos rondas.** La regla de «no parchear sin caso delante» es
buena para defectos hipotéticos; es cara para un modo de fallo ya demostrado en un rol
gemelo, que corre en el mismo runner, con el mismo perímetro y la misma consecuencia.

La raíz no es ningún fichero concreto: **las tres reglas son idénticas para los tres roles y
viven copiadas en tres sitios**, así que olvidar una es posible y ya pasó dos veces.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque
([#182, comentario 5311199981](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/182#issuecomment-5311199981)),
antes del primer commit. Alcance: `implementer.md` (las tres reglas), `corrector.md`
(añadir las dos que le faltaban), una prueba nueva y este ADR. `reviewer.md` no se toca.
Parar si el arreglo exigiera tocar `.github/**`, permisos o la convergencia — ninguno se
tocó. Desviación declarada por adelantado: tocar `corrector.md` va más allá del literal
«parchea el implementador», y se hace porque un invariante que solo se cumple en dos de
tres ficheros no cierra la familia.

## Opciones consideradas

1. **Parchear solo `implementer.md`**: descartada como solución completa — arregla el tercer
   caso y deja la trampa armada para el cuarto rol (auditor documental de C3, investigador
   de B1). Es lo que se hizo dos veces ya.
2. **Extraer un fragmento común e insertarlo desde los workflows**: es la solución correcta
   de fondo, y está **bloqueada**: los tres pasos que ensamblan el prompt viven en
   `.github/workflows/` y ADR-002 prohíbe que la automatización los toque. Requeriría una
   sesión interactiva del propietario. Queda pendiente, no descartada.
3. **Parchear los tres ficheros y vigilar el invariante con una prueba que recorra el
   directorio de prompts**: elegida. No toca workflows y hace que la omisión deje de
   depender de que alguien se acuerde.

## Decisión

1. **`implementer.md` recibe las tres reglas**: veredicto provisional `FAILED_SAFELY` como
   primera acción, prohibición de terminar el turno esperando algo (subagentes incluidos), y
   aviso de entorno acotado. `corrector.md` recibe las dos que le faltaban (la cláusula de
   subagentes y el entorno acotado). Los tres roles quedan uniformes.
2. **Una prueba nueva (`tests/automation/test_prompts_de_rol.py`) fija los invariantes
   comunes recorriendo `scripts/automation/prompts/*.md`.** El directorio ES la lista: no hay
   ninguna enumeración escrita a mano, así que **un cuarto prompt que se añada mañana no
   puede nacer sin las reglas** — falla al aparecer.
3. Se rectifica el criterio de ADR-021 en un punto: cuando un modo de fallo está demostrado
   en un rol, extenderlo a los roles gemelos **no es parchear sin caso delante**; el caso es
   el mismo y solo cambia el fichero. Lo que sigue prohibido es inventar defectos que nadie
   ha visto.

## Comprobación que la sostiene

- Volcado del run 31985897583 (job 95260759821) leído directamente: `result`,
  `terminal_reason`, `duration_ms` y la denegación de `curl`.
- Tope real del workflow verificado antes de citarlo: `implement-sirius-work.yml:40` declara
  `timeout-minutes: 60` a nivel de job y ningún tope de paso. Un borrador anterior de este
  prompt decía «55 del paso»: era inventado y se corrigió antes de commitear.
- **Las pruebas nacieron fallando y se vio.** Al escribirlas cayeron tres casos reales: el
  provisional del implementador (la frase «ÚLTIMA acción» ya aparecía antes en el fichero y
  el corte quedaba invertido) y la sección de entorno en dos ficheros (la frase caía partida
  por el ajuste a 80 columnas). Los dos primeros eran defectos del prompt; el tercero, de la
  prueba, que ahora normaliza espacios: un invariante que se rompe al reajustar un párrafo
  enseña a desactivar la prueba en vez de a leerla.
- **Prueba por mutación (ADR-001 §3), cuatro, todas cazadas:**

  | Mutación | Qué falla |
  |---|---|
  | quitar el provisional de `implementer.md` | el caso `implementer.md` |
  | quitar la cláusula de subagentes de `corrector.md` | el caso `corrector.md` |
  | **añadir un cuarto prompt sin ninguna regla** | **tres casos del prompt nuevo, al nacer** |
  | prometer una reanudación automática fuera de la sección anti-espera | la prueba de reanudación |

  La tercera es la que demuestra que la familia queda cerrada y no solo su tercer caso.
- Validaciones obligatorias en verde: `ruff format --check .`, `ruff check .`,
  `mypy src tests`, `pytest tests/automation/`.

## Consecuencias

- Los tres roles quedan uniformes y con la omisión vigilada por CI.
- **La duplicación sigue existiendo**: tres copias del mismo texto. Lo que cambia es que
  ahora divergir cuesta un fallo de CI en vez de una ronda perdida. La extracción del
  fragmento común (opción 2) queda pendiente para cuando el propietario quiera hacerla en
  sesión interactiva, que es lo que ADR-002 exige.
- **No se afirma que esto cierre todas las formas de terminar sin veredicto**: cierra la
  demostrada, tres veces, y convierte cualquier otro corte en diagnóstico.
- La incidencia #182 (S1) queda detenida en `sirius:failed-safely` hasta que esta PR se
  fusione. Reactivarla antes repetiría el fallo.

## Alternativas descartadas y por qué

Las opciones 1 y 2 de arriba —la segunda por la frontera de ADR-002, no por su mérito—.
Además: enumerar los tres prompts a mano en la prueba, descartada porque exigiría acordarse
de ampliar la lista, que es exactamente el olvido que la prueba existe para hacer imposible;
y subir el tope de turnos o de tiempo del implementador, descartada porque no se agotó
ninguno de los dos.
