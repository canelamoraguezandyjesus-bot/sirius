# ADR-028 — Una avería transitoria de un tercero no justifica una invariante permanente en la suite

- Estado: PROPUESTO
- Fecha: 2026-08-17
- Aprobación: la fusión de la PR de esta rama por el propietario.
- Revisa: [ADR-027](ADR-027-las-etiquetas-se-leen-del-objeto-de-la-incidencia.md), puntos 2 y 3 de su decisión.

## Contexto y problema

ADR-027 decidió cuatro cosas el mismo día. Dos siguen en pie y dos se retiran aquí.

Su punto 2 creaba `tests/automation/test_lectura_de_etiquetas.py`, que **prohibía
permanentemente** la llamada `gh api …/issues/{n}/labels` en todos los scripts y todos los
workflows del repositorio. Su punto 3 añadía una prueba anti-vacuidad para que esa
prohibición no pudiera cumplirse sin leer etiquetas.

La evidencia detrás era real —el endpoint devolvía **200 con cuerpo vacío** durante más de
una hora mientras `/issues/{n}` respondía— pero la **premisa implícita** no lo era: que el
defecto fuese una propiedad estable de ese endpoint. Unas horas después:

- `/issues/186/labels` volvió a responder **200** con normalidad, sin que nadie tocara nada.
- De forma independiente, `/collaborators` empezó a devolver **503 «No server is currently
  available»** mientras `repo`, `issues`, `comments`, `pulls`, `commits`, `branches` y
  `labels` respondían 200 en la misma sonda.
- El propietario tuvo fallos simultáneos en la app móvil de GitHub. Cliente distinto, red
  distinta, mismo día.
- El `POST` de un comentario a la PR #187 falló también con 503, en medio de todo esto.

Y el dato que lo cierra, tomado del endpoint que tumbó dos rondas de A2:

| hora (UTC) | `/collaborators` |
|---|---|
| 15:48 | 503 |
| 15:50–16:00 | 503, tres reproducciones |
| **16:21** | **200, dos sondas seguidas** |
| 16:30:52 | 503 (run 32045885719) |
| 16:31 | 503 (`POST` de comentario) |

**No estaba caído: parpadeaba.** Ningún endpoint concreto estaba roto; GitHub tenía una
degradación parcial e intermitente que iba cambiando de sitio.

Sobre eso se había escrito una ley permanente del repositorio. Un lector dentro de seis meses
habría concluido que `/issues/{n}/labels` está averiado. No lo está, y no lo estaba: le tocó
la ventana.

Es la misma familia que este repositorio lleva corrigiendo desde la PR #136 —*afirmar más de
lo que el dato sostiene*— y esta vez la cometí en el documento que existe para evitarla.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque
([PR #187, comentario 5317722473](https://github.com/canelamoraguezandyjesus-bot/sirius/pull/187#issuecomment-5317722473)),
antes del primer commit. Alcance: borrar la prueba, este ADR y un puntero en ADR-027. Los
simulados de `gh` no se tocan. **El cambio de código no se toca**: si aparecía la tentación de
revertir también los seis puntos de llamada, parar — son dos decisiones y solo una está en
revisión. Si al borrar la prueba se caía otra, parar y contarlo en vez de ajustarla.

## Opciones consideradas

1. **Dejarlo como está**: descartada. La prueba no hace daño técnico, pero afirma algo falso
   sobre el mundo y lo afirma con la autoridad de un test en verde. Una prueba que miente es
   peor que no tenerla: se cita.
2. **Suavizar el texto de la prueba manteniendo la prohibición**: descartada. El problema no
   es cómo está redactada, es que prohíbe. Reformularla dejaría la misma regla con mejor
   prosa.
3. **Revertir también el cambio de código**: descartada. Leer las etiquetas del objeto de la
   incidencia es correcto por sí solo y ahorra una llamada. Que la justificación fuera
   excesiva no lo vuelve incorrecto.
4. **Borrar la prueba y registrar por qué**: elegida.

## Decisión

1. **Se borra `tests/automation/test_lectura_de_etiquetas.py` entero.** No solo la
   prohibición: sus otras dos pruebas existían únicamente para sostenerla —una impedía que el
   `parametrize` quedase vacío, la otra que la prohibición se cumpliera en vacío—. Sin la
   regla que apuntalaban, no apuntalan nada.
2. **Se mantiene el punto 1 de ADR-027**: las etiquetas se leen del objeto de la incidencia.
   Deja de ser un remedio a una avería y pasa a ser lo que siempre fue: una llamada menos
   para el mismo resultado.
3. **Se mantiene el punto 4 de ADR-027**: los simulados de `gh` despachan por el filtro y
   aplican el `--jq` real del llamador. Eso mide el filtro y es correcto con independencia de
   todo lo demás.
4. **Regla de método que este caso deja escrita**, que es lo único que de verdad vale de aquí:
   ante una respuesta **imposible** de una API de terceros —un 200 con cuerpo vacío, un 503,
   un cliente ajeno fallando a la vez—, la primera comprobación es **el estado de la
   plataforma**, no el código propio. Sondear otros endpoints cuesta un minuto. Reescribir
   siete puntos de llamada costó una tarde y produjo una invariante falsa.

## Comprobación que la sostiene

- Sondas repetidas sobre catorce endpoints del repositorio, con las horas de la tabla de
  arriba. Los 403 de mi propio token sobre `/collaborators` se descartaron por inútiles: son
  falta de permiso, no degradación. El dato válido son los **503** del token del MCP.
- Los dos runs de A2 caídos por lo mismo, citados del log y no reconstruidos:
  `GET …/collaborators/{u}/permission - 503`, a los 1322 ms (run 32043385675) y a los 801 ms
  (run 32045885719), en ambos casos **antes de arrancar el modelo**.
- Suite completa tras el borrado: ver la PR.

## Consecuencias

- Volver a `gh api …/issues/{n}/labels` deja de ser una infracción. Nunca debió serlo.
- **Queda menos cobertura de la que había esta mañana, y está bien.** La cobertura que se
  retira no medía nada real.
- **Lo que este ADR NO afirma**: que ese endpoint sea fiable. Afirma que no tenemos evidencia
  de que no lo sea, que es distinto y más pequeño.
- **Debilidad conocida, declarada y sin arreglar**: un fallo transitorio de una sola llamada a
  GitHub consume el evento, quema la ronda y deja la incidencia en un estado terminal que
  necesita a una persona. Sirius envuelve sus llamadas en `sirius_retry`, pero la comprobación
  de permisos que hace `anthropics/claude-code-action` como primera acción no la envuelve
  nadie, y no es nuestra para envolverla. Sondear antes de relanzar **no lo resuelve**: quedó
  demostrado hoy, con una sonda en 200 a las 16:21 y un 503 a las 16:30. Queda como decisión
  pendiente, no como defecto olvidado.

## Alternativas descartadas y por qué

Las cuatro de arriba. Además: **reescribir ADR-027 para que no conste la equivocación** —
descartada. El repositorio no define mecanismo de sustitución de ADRs, y borrar el rastro
eliminaría justo lo aprovechable. ADR-027 se queda como está, con un puntero de una línea
hacia aquí.
