# ADR-102 — Las pruebas de aceptación de Sirius 0.2 no resuelven las decisiones que la Definición deja abiertas

- Estado: PROPUESTO
- Fecha: 2026-08-29
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario

Este ADR es también la nota de arranque de la rama que introduce
`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md` (incidencia #419):
se publica antes del primer commit de trabajo sobre ese documento.

## Contexto y problema

`docs/evolution/RECTOR.md` §17 exige, como segunda puerta de activación antes
de una etapa posterior a 0.1, «pruebas de aceptación reproducibles»
(`RECTOR.md:288`). La incidencia #419 pide operacionalizar como tales los
criterios de comprobación que
`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` ya fija en
§2.4, §3.4, §4.4, §5.4, §6.4 y §7.1.

Esa Definición deja explícitamente cuatro decisiones sin resolver en su §7.3
(fusionar o no la PR #117, la dependencia de Ollama, la última omisión crítica
de recuperación, y el origen de los estados `CANDIDATA`/`RECHAZADA`), y la
Arquitectura Técnica en curso (PR #418, no aprobada) deja pendiente una
quinta: el disparador de la sugerencia de guardado tras una conversación. El
riesgo concreto de este trabajo documental es que, al escribir pasos y
resultados esperados «reproducibles», resulte tentador rellenar esos huecos
con una elección propia para que la prueba quede más concreta — y esa elección
sería una decisión de producto o arquitectura que ni la incidencia ni el
perfil documentalista autorizan a tomar.

## Criterio de parada (escrito ANTES de decidir)

Si alguna de las seis secciones pedidas (§2.4, §3.4, §4.4, §5.4, §6.4, §7.1)
resultara indefinible sin inventar un umbral que la Definición no fija, o sin
resolver alguna de las cinco decisiones pendientes citadas arriba, la sección
se detiene y se emite `BLOCKED_BY_DECISION` en vez de rellenar el hueco. No
llegó a ocurrir: las seis secciones se definieron citando directamente los
criterios ya aprobados, marcando cada decisión pendiente como precondición no
resuelta o diseñando la prueba para que valga con cualquier salida posible de
esa decisión (ver «Comprobación que la sostiene»).

## Opciones consideradas

1. **Dejar cada PA condicionada a su decisión pendiente**, sin resolverla:
   citar la decisión, marcarla como precondición, y — donde sea posible —
   redactar el paso o el resultado esperado de forma agnóstica al mecanismo
   que la decisión acabe eligiendo (por ejemplo, PA-0.2-SUG no asume si el
   disparador de la sugerencia es automático, por heurística o a petición del
   usuario).
2. Elegir una salida plausible para cada decisión pendiente (p. ej. asumir que
   la sugerencia se dispara automáticamente tras cada conversación) para que
   las pruebas queden más concretas y fáciles de implementar después.
3. No escribir las PA de los bloques con decisiones pendientes y dejarlas
   como hueco declarado, igual que el plan de 0.1 declara huecos para lo que
   no puede automatizarse.

## Decisión

**Opción 1.** Las seis PA se escriben completas — con precondiciones, pasos y
resultado esperado — pero cada una que depende de una decisión pendiente lo
declara explícitamente como precondición y, cuando el mecanismo concreto
afecta al paso o al resultado (PA-0.2-SUG-01, PA-0.2-SUG-02, PA-0.2-BUS-01), se
redacta para valer con cualquiera de las salidas posibles. La opción 2 se
descarta porque publicaría como aceptación una elección que corresponde al
propietario o a la Arquitectura Técnica, y esa elección quedaría enterrada en
un documento de pruebas en vez de announced como la decisión que es. La
opción 3 se descarta porque las seis secciones sí tienen contenido conocido y
citable de la Definición (el objetivo, el resultado esperado, los casos de
uso existentes que sirven de patrón); dejarlas en blanco desperdiciaría eso.

Una segunda decisión, menor, tomada al mismo tiempo: el piso de no-regresión
de PA-0.2-PUERTA-01 no es una cifra fija copiada de la PR #117, sino «la
última cifra incorporada a `main`», siguiendo literalmente la metodología que
la propia Definición ya fija para la puerta integral §7.1
(`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:279-280,282`); esa regla
solo es aplicable ahí porque, para cuando PUERTA-01 se ejecuta, las seis PA
anteriores ya la establecieron en `main`. PA-0.2-REC-01 no puede usar la
misma regla — es la primera prueba en fijar esa cifra en `main`, así que
«la última cifra incorporada a `main`» estaría vacía — y mantiene en su lugar
el piso literal de la PR #117 de §3.4, exacto para aciertos exactos (29/47),
pero bloqueado para cobertura hasta que el propietario registre cuál de las
dos cifras que la Definición cita sin distinguir («63/81 frente a 64/81»,
línea 74) es la alcanzada bajo el paquete activo — fijar una de las dos a
ciegas, o delegar la elección a quien ejecute la prueba, sería inventar un
umbral que la Definición no sostiene.

## Comprobación que la sostiene

Cada afirmación comprobable del plan de pruebas cita fichero y línea contra el
estado real de `main` en esta revisión:

- Las cinco decisiones pendientes citadas se verificaron contra
  `SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:297-310` (§7.3) y contra
  el objetivo literal de la incidencia #419 (la quinta, el disparador de
  sugerencias, que #419 atribuye a la Arquitectura en curso).
- Los seis criterios de comprobación operacionalizados se citan literalmente
  de `SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` líneas 84-90,
  120-125, 167-172, 216-220, 245-249 y 253-290.
- Las citas de código que sostienen «qué ya existe» en cada bloque se
  verificaron leyendo el archivo real, no reproduciendo la Definición sin
  comprobar: `src/sirius/domain/precedence.py:123-192`,
  `src/sirius/application/detect_precedence_conflicts.py:28-46`,
  `src/sirius/presentation/knowledge_widget.py:627-669` (conflictos, ninguna
  acción de resolución cableada todavía — confirmado leyendo el método
  completo), `src/sirius/ports/project_repository.py:29-36` (solo
  `get_project` por id, ningún listado), `src/sirius/application/save_manual_memory.py:48`,
  `src/sirius/application/propose_decision.py:1-10`,
  `src/sirius/application/memory_origin.py:52`,
  `src/sirius/application/decision_origin.py:63`.
- Las pruebas citadas como patrón análogo ya existente se verificaron por
  nombre exacto de función, no solo por nombre de archivo:
  `tests/integration/test_manual_memory_origin.py:32:def test_explicit_save_creates_a_traceable_memory_and_its_origin_can_be_opened`,
  `tests/integration/test_decision_lifecycle.py:62:def test_debating_alternatives_never_creates_a_decision`,
  `tests/gui/test_knowledge_widget.py:517-535` (existencia del archivo y del
  rango confirmada; contenido tomado de
  `docs/implementation/TRAZABILIDAD_PA_SP.md:46,50`, tabla que su propio
  README declara comprobada por
  `tests/unit/test_pa_sp_traceability.py`), `tests/integration/test_initial_project_persistence.py`
  (existencia del archivo confirmada con `ls`).
- El documento de 0.1 usado como referencia de estilo,
  `docs/canonical/SIRIUS_PLAN_PRUEBAS_TRAZABILIDAD_0.1_v1.0_PROPUESTO.docx`, se
  extrajo con `python3`/`zipfile` (biblioteca estándar, sin instalar nada) y
  se leyó completo antes de citar su estructura y su regla de aceptación.

## Consecuencias

- El plan de pruebas queda válido con independencia de cómo el propietario
  resuelva las cinco decisiones pendientes: no habrá que reescribirlo cuando
  se decidan, solo completar las precondiciones que hoy declara abiertas.
- Ninguna PA de este plan puede declararse superada hoy: seis de seis
  dependen de trabajo de implementación que todavía no existe (§4.1 de la
  Definición: «nada» cubre sugerencias confirmadas en 0.1) o de decisiones sin
  tomar. Eso es correcto para un documento en estado PROPUESTO que no autoriza
  implementación — no es un defecto de este ADR ni del plan.
- La tabla de trazabilidad del plan (su sección 9) queda deliberadamente
  separada de `docs/implementation/TRAZABILIDAD_PA_SP.md`: extender esa matriz
  con `PA-0.2-*` es trabajo de implementación posterior, fuera del alcance de
  esta incidencia («no modifiques ningún otro fichero»).

## Alternativas descartadas y por qué

Ver «Opciones consideradas»: la opción 2 (elegir una salida plausible para
cada decisión pendiente) y la opción 3 (dejar los bloques en blanco) se
descartan por las razones dadas en «Decisión».
