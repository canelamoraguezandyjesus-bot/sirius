# ADR-118 — Cuatro huecos operativos del motor: verdes sin registrar, reparaciones tras mover el head, bloqueos mal enrutados y decisiones invisibles al corrector (incidencias #435, #442, #453, #469, #471)

- Estado: PROPUESTO
- Fecha: 2026-08-31
- Aprobación: fusión de la PR por el propietario. El cambio lo escribe la
  sesión interactiva con autorización explícita del propietario (su orden
  «por arreglar el motor», dada tras avisarle de que esto toca los flujos
  protegidos), por el camino que la incidencia #270 deja diseñado: la
  automatización no puede tocar sus propios workflows (ADR-002, intacto); la
  sesión interactiva puede, con permiso, y el cambio pasa por Quality y
  revisión como cualquier otro. Nada se empuja a `main` directamente.

## Contexto y problema

La noche del 30 al 31 de agosto de 2026, la ola de incorporación del paquete
D1/D7 (27 fusiones) ejercitó el motor con más carga y más casos límite que
ninguna sesión anterior, y cuatro huecos operativos conocidos o nuevos
mordieron con nombre y hora. Ninguno rompió trabajo: en los cuatro, la
maquinaria se detuvo de forma segura. Pero cada uno convirtió una situación
resoluble en una parada muda que exigió cirugía manual de la sesión
interactiva (etiquetas repuestas a mano, incidencias cerradas y
redespachadas, decisiones re-transmitidas por otro canal).

## Los cuatro huecos, con su evidencia

**H-33 — `blocked-decision` tenía vuelta fija al corrector.**
`scripts/automation/sirius_resume_on_command.sh` asumía que solo la política
de convergencia (que siempre para al corrector) emite `blocked-decision`.
Falso: cualquier rol publica `BLOCKED_BY_DECISION` con su marcador
`:blocked:` (`scripts/automation/sirius_apply_verdict.sh`). En #453 el
implementador se bloqueó pidiendo decisión SIN abrir PR; la orden `continua`
del propietario despertó a un corrector sin nada que corregir, que se paró en
seguro: la orden murió en un rebote. En #471 volvió a pasar.
*Arreglo:* la fase se lee del historial también para `blocked-decision`
(mismo mecanismo que H-23 estableció para `failed-safely`, con el marcador
`:blocked:` añadido al juego reconocido); si el historial no publica ningún
rol —las paradas por convergencia anteriores al marcador— se conserva la
vuelta histórica al corrector.

**H-34 — un verde de Quality durante `failed-safely` quedaba sin registrar.**
`advance-sirius-after-quality.yml` buscaba candidatas únicamente en
`sirius:ci-pending`. En #435 y #442, un update-branch durante la parada
disparó Quality, el run terminó en verde y nadie lo anotó: el revisor no
despertó y el ciclo quedó mudo hasta reponer `ci-pending` a mano y relanzar
el run — dos veces en una noche.
*Arreglo:* el resultado VERDE considera también candidatas en
`sirius:failed-safely` y las revive hacia revisión, retirando la etiqueta de
origen que corresponda. Un resultado ROJO sigue actuando solo sobre
`ci-pending`: revivir una parada segura hacia corrección sería tomar una
decisión, no registrar un resultado.

**H-35 — las decisiones del propietario no llegaban al corrector.**
El corrector recibe únicamente las observaciones estructuradas de la última
revisión; los comentarios de la incidencia no entran en su contexto. En #469
(ronda 4) el corrector revirtió sin saberlo una decisión ya registrada del
propietario — lo cazó el revisor y costó una ronda entera —; en #471 volvió
a plantear una disyuntiva ya resuelta y la incidencia acabó cerrada y
redespachada con la decisión copiada dentro de la orden.
*Arreglo:* la puerta del corrector extrae los comentarios de la incidencia
con autoría OWNER cuyo cuerpo empieza por «DECISI» y el prompt los inyecta en
una sección propia; `scripts/automation/prompts/corrector.md` declara su
autoridad: una decisión registrada que resuelve la disyuntiva se ejecuta, no
se re-plantea ni se revierte; si ninguna la resuelve, la regla de parada
sigue intacta.

**H-36 — una reparación nacida de un CI_FAILURE moría si el head se movía.**
La puerta del corrector (H-14) acepta rondas sin observaciones cuando hay un
fallo de Quality registrado PARA EL HEAD ACTUAL. Si el head se movió después
del fallo (update-branch, push), el registro ya no corresponde y la puerta
paraba en `failed-safely` con una corrección legítima pendiente (#441, #442).
*Arreglo:* en ese caso exacto —sin observaciones, con un CI_FAILURE de un
head anterior— la incidencia vuelve a `sirius:ci-pending` y el resultado de
Quality del head actual la encamina por el camino normal. Es la misma cura
que se aplicaba a mano, ahora en el guion.

## Opciones consideradas

1. **No tocar nada y seguir con cirugía manual** — descartada: los cuatro
   huecos ya tienen cura conocida y repetida; dejarlos es elegir que cada
   noche de carga vuelva a necesitar una persona.
2. **Ordenárselo al motor** — descartada: tres de los cuatro arreglos viven
   en `.github/workflows/`, que ADR-002 prohíbe tocar a la automatización, y
   esa prohibición es una decisión de seguridad que este ADR no reabre.
3. **Sesión interactiva con autorización explícita del propietario, por
   rama y PR con Quality y revisión** — elegida. Es el camino que la
   incidencia #270 deja diseñado para exactamente esta situación.

## Decisión

Los cuatro arreglos descritos, cada uno con su prueba:

- H-33: `tests/automation/test_reanudar_ejecutando_el_guion.py` gana cuatro
  escenarios ejecutados contra el guion real (implementador bloqueado con y
  sin PR, corrector bloqueado, y que manda la última parada publicada);
  los diecisiete escenarios preexistentes siguen en verde sin cambios.
- H-34: `tests/automation/test_avance_registra_el_verde_de_una_parada_segura.py`
  (nuevo) fija las tres propiedades del arreglo sobre el guion sin
  comentarios: candidatas en ambas etiquetas, guarda del resultado rojo y
  retirada de la etiqueta de origen.
- H-35 y H-36: `tests/automation/test_corrector_ante_fallo_de_ci.py` gana
  cuatro comprobaciones (la rama `head-movido-tras-ci` y su transición a
  `ci-pending`; la extracción de decisiones con su filtro de autoría; la
  inyección en el prompt; la declaración de autoridad en el rol).

## Ronda de revisión de la PR #477

La revisión de Codex afinó tres piezas, incorporadas antes de fusionar:

1. **Carrera de eventos en H-36**: si el Quality del head actual terminó
   antes de la transición a `ci-pending`, su `workflow_run` ya se consumió;
   la rama relanza ese run terminado (con el PAT) para que su nueva
   finalización dispare el enrutado, en vez de esperar horas al
   reconciliador.
2. **H-35 falla cerrado**: una lectura caída de los comentarios no es
   «(ninguna) decisión» — la puerta se detiene en seguro en vez de arrancar
   al corrector a ciegas.
3. **El reset de convergencia es solo para bloqueos de convergencia**: un
   `blocked-decision` emitido por un rol (marcador `:blocked:`) se reanuda
   sin perdonar rondas; el listón del bucle queda intacto. Sin marcador
   (historiales anteriores al convenio) se conserva el comportamiento
   histórico.

La segunda pasada de la revisión afinó tres más, también incorporadas:

4. **El relanzamiento va con el token del workflow**: el PAT no tiene
   alcance de Actions (documentado en el propio avance) y el POST habría
   devuelto 403 en silencio; el workflow gana el permiso `actions: write`
   exactamente para esto.
5. **Sin transición no hay relanzamiento**: si devolver la incidencia a
   `ci-pending` falla, la rama sale reintentable en vez de consumir el
   nuevo evento con la incidencia aún en `repair-requested`.
6. **Manda el último disparador**: un fallo histórico de Quality no
   convierte en «head movido» una ronda cuyo último disparador fue una
   revisión con observaciones; si estas no se pudieron leer, la parada es
   «observaciones-ilegibles», reintentable, no un consumo de la ronda.

La tercera pasada endureció cuatro bordes más:

7. **Un head ilegible es reintentable, no un head movido** — pr_head vacío
   significa lectura caída; la rama sale con error en vez de consumir la
   reparación con una consulta de runs sin head.
8. **Un relanzamiento fallido se propaga** — el reconciliador solo
   auto-recupera verdes; el fallo del POST deja el job en rojo reintentable
   con la incidencia ya en `ci-pending`.
9. **Las decisiones llevan la doble ruta del contrato** — REST y, si cae,
   GraphQL (conservando la asociación de autoría) antes de declarar la
   parada.
10. **El avance deduplica incidencias con las dos etiquetas** — una
    transición parcial anterior no fabrica una falsa ambigüedad, y la
    etiqueta sobrante se retira tras la transición de éxito.

Las dos últimas pasadas cerraron la cola de bordes (22 hallazgos en total,
todos corregidos con su prueba): toda lectura del emparejado y de la rama
del head movido propaga su fallo como reintentable en vez de disfrazarse de
resultado vacío; el relanzamiento vuelve al PAT — la restricción real es la
anti-recursión del GITHUB_TOKEN, documentada y en producción en
`sirius_apply_verdict.sh`, no el alcance del PAT — con `actions: read` para
la consulta; el reanudador solo acepta marcadores de parada de la época
actual (posteriores al último permiso de reanudación), con la vuelta
histórica al corrector como respaldo; y la salida idempotente de
`sirius_transition` exige también las retiradas de `remove_csv`, para que
una transición parcial no certifique como completa una parada falsa.

## Consecuencias

- Positivas: las cuatro paradas mudas de la noche pasan a resolverse solas o
  a enrutar bien la orden del propietario; la cirugía manual de etiquetas
  deja de ser parte del ciclo normal.
- Negativas/riesgos: un verde de Quality ahora puede revivir una incidencia
  en `failed-safely` hacia revisión sin que una persona lo pida (H-34); es
  deliberado y acotado al resultado verde, y una persona conserva el veto
  cerrando la incidencia. La detección de decisiones (H-35) es por prefijo
  «DECISI» y autoría OWNER: una decisión redactada sin ese prefijo no se
  inyecta — el convenio queda escrito aquí y en el prompt del rol.
