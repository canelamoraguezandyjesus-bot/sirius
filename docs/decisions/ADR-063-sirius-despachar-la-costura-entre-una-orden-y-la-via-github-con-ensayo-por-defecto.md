# ADR-063 — `sirius-despachar`: la costura entre una orden y la vía GitHub, con ensayo por defecto

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR de esta rama por el propietario
- Nota de arranque de esta rama: este ADR. Publicado y con criterio de parada
  fijado antes del primer commit.

## Contexto y problema

Después de A5 y C2 el motor tiene las tres piezas del camino
"orden → incidencia activada", y **ninguna llama a la siguiente**:

    interpretar_intencion_v0 → decidir → aplicar_decision → dispatch_work_item

C2 declaró esa costura fuera de su encargo a propósito (frontera declarada en
la incidencia #240), así que la monta una sesión interactiva (ADR-002). Sin
ella, C2 es capacidad demostrada en pruebas y cero trabajo despachado: el
propietario sigue siendo el mensajero, que es justo lo que el Work Engine
existe para dejar de ser.

Al cablearla aparecen dos huecos que las pruebas de cada pieza no podían ver,
porque solo existen *entre* piezas:

**H-12.** El despachador exige que la orden del propietario conste enlazada en
`WorkItem.evidencia` y se niega a activar sin ella (`OrdenNoEnlazadaError`,
contrato v1.8 §12.1). ADR-062 ya dejó escrito que `evidencia` "existe desde A1
pero ningún código lo poblaba". Lo que no dijo —porque desde dentro de C2 no
se ve— es que **tampoco había por dónde poblarlo**: ni `create_work_item` ni
`aplicar_decision` aceptaban `evidencia`, y ningún método del almacén la
añadía después. La guarda era, desde producción, insatisfacible: todas las
pruebas de C2 construyen el `WorkItem` a mano con el marcador ya puesto.

**Segundo hueco, del ensayo.** La primera versión de este comando cortaba
justo antes de llamar al despachador y anunciaba "esto es lo que se crearía".
Un ensayo que no atraviesa las guardas no ensaya: decía que la orden saldría
adelante cuando el despachador la habría rechazado por H-12, y el rechazo solo
aparecía al ejecutar de verdad — el momento exacto en que ya no quieres
enterarte.

## Criterio de parada (escrito ANTES de decidir)

Si cablear la costura exigiera (a) tocar `.github/**` desde automatización,
(b) ampliar la escritura más allá de las dos operaciones que enumera
`GitHubWriterPort`, o (c) relajar la comprobación de orden enlazada —rellenarla
con un valor de adorno para que la guarda pase— se para y se pregunta. Dos
rondas de revisión con defectos de la misma familia paran la implementación
para buscar la raíz.

## Decisión

**1. Comando aparte, no subcomando de `sirius-motor`.** `sirius-motor` existe
para conversar y consultar, y **declina las órdenes a propósito**: la primera
propiedad de A5 es que conversar no crea trabajo, y hay pruebas que la fijan.
Meter dentro un camino que sí crea trabajo borraría esa garantía justo donde
está escrita.

**2. El ensayo es lo que sale por defecto; `--ejecutar` es explícito.** Una
orden mal entendida no puede costar una incidencia de verdad: de una incidencia
cuelga un ciclo entero —implementador, Quality, dos revisores—, así que el
accidente no es barato.

**3. El ensayo atraviesa el despachador real con un escritor que no escribe.**
No se salta ninguna guarda: recorre clase, estado y orden enlazada, y solo la
E/S se sustituye. El escritor de ensayo devuelve el número de incidencia `0`
—imposible— a propósito: si alguna vez se colara en un camino de verdad, lo que
salga apuntará a `issues/0`, que no existe, en vez de a una incidencia ajena.

**4. El ensayo no persiste.** Usa el almacén en memoria. Con el durable
dejaría un `WorkItem` ACTIVE que ningún despachador va a atender: trabajo
activo sin nada detrás, el estado inconsistente del que el resto del motor se
cuida. El ensayo enseña qué pasaría; no lo hace a medias.

**5. `evidencia` viaja en la creación** (`create_work_item`,
`create_and_escalate_work_item`, `aplicar_decision`), parámetro opcional con
defecto vacío. Es el único momento en que se sabe de dónde vino la orden, y
cierra H-12 sin tocar ninguna llamada existente.

**6. Sin `--orden-ref`, la referencia es el diario del motor**
(`diario-del-motor:<work_id>`). Cuando la orden se da por terminal no hay URL
que citar, pero el texto íntegro queda persistido bajo ese `work_id`: es una
respuesta real a "¿quién pidió esto?", no un relleno para pasar la guarda —que
es justo lo que el criterio de parada (c) prohíbe. Si la orden se dio en
GitHub, `--orden-ref` enlaza el comentario.

## Consecuencias

Aceptadas: el ensayo por defecto añade un paso a cada despacho —querido—; y
`evidencia` en la firma de creación amplía el contrato del almacén en las dos
implementaciones.

A vigilar: H-11 sigue abierto (incidencia #242) —el diario del despachador vive
en memoria, así que "una sola activación por WorkItem" no cruza procesos—. Con
este comando, dos invocaciones del mismo trabajo crearían dos incidencias. El
`work_id` derivado del segundo de la orden lo hace improbable a mano, no
imposible.

Lo que este ADR NO decide: quién invoca el comando. Hoy lo invoca una persona.
Que lo invoque un proceso es otra decisión, con otro riesgo, y va aparte.
