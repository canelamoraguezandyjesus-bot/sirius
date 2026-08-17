# ADR-014 — Quien escribe una etiqueta notificable usa la identidad real, y el recolector de Codex no aprueba por comentario

- Estado: PROPUESTO
- Fecha: 2026-08-14
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Numeración: 011, 012 y 013 están tomados por ramas abiertas. Se comprueba
  antes de asignar porque en la PR #153 se crearon dos ADR-008 por no hacerlo.

## Contexto y problema

Dos hallazgos P1 de AUDITOR-V0-RUN-001 (incidencia #154), ambos sostenidos por
un verificador independiente, y ambos con más de una salida razonable. Por eso
dejan ADR: no era obvio cuál elegir.

**Uno.** Al mudar los tres roles a GitHub Actions, las etiquetas pasaron a
escribirse con el `GITHUB_TOKEN`. GitHub suprime los eventos que produce ese
token para evitar recursión, así que `notify-sirius-state.yml` dejó de recibir
el `issues: labeled` de `sirius:implementing` y `sirius:completed` — dos de los
seis estados que el contrato §7 declara notificables. El verificador reconcilió
la contradicción aparente con la auditoría de julio, que sí veía avisos de
`implementing`: entonces esa transición la aplicaba una Routine externa, con
identidad real. Es una **regresión**, no un estado histórico.

**Dos.** El recolector de Codex no miraba los comentarios de la conversación,
que es uno de los canales por los que responde el conector. En la incidencia
#148 gastó los 1200 s completos y después afirmó que Codex «no entregó un
resultado identificable», habiendo respondido 101 s después del disparador, del
autor permitido y sobre el SHA esperado.

## Criterio de parada (escrito ANTES de decidir)

Ninguno de los dos arreglos puede ampliar lo que la automatización está
autorizada a decidir. Si al implementarlos hiciera falta que una señal más débil
aprobara una revisión, o que un workflow nuevo consumiera los eventos añadidos,
se para y se decide de nuevo: eso sería cambiar el contrato, no repararlo.

## Opciones consideradas

Para las notificaciones: (A) el PAT escribe también las etiquetas notificables;
(B) cada workflow publica su propio comentario de notificación; (C) dejarlo y
enmendar §7 para declarar que esos dos estados no se notifican.

Para el recolector: (A) leer el comentario solo para fallar rápido con el motivo
exacto, sin tocar el contrato; (B) ampliar §4.1 para que ese comentario cuente
como aprobación; (C) lo anterior más extraer hallazgos de su cuerpo.

## Decisión

**(A) y (A)**, elegidas por el propietario el 14 de agosto de 2026.

Las etiquetas se escriben con el PAT, reutilizando el patrón ya aprobado y
auditado en `advance-sirius-after-quality.yml`. Y el recolector mira ese canal
como **último recurso**, solo cuando no hay revisión formal ni reacción, para no
debilitar la precedencia que §4.1 exige. **El contrato no cambia**: esa señal no
aprueba; la aprobación sigue exigiendo revisión formal `APPROVED` o reacción
`+1`. Lo único que cambia es que la ronda termina en segundos con el motivo
verdadero en vez de mentir con un timeout.

Dos detalles de implementación que son decisión y no detalle:

- **La regla es ancha**: *todo* paso que escriba etiquetas usa la identidad
  real, no solo los que añaden un estado notificable. Acotarla exigiría deducir
  del texto del comando qué argumento añade y cuál quita, que es reconstruir
  desde fuera la semántica de otro sistema — el patrón que ya costó quince
  defectos (ADR-001). El coste de la regla ancha es algún evento que nadie
  consume; el de la estrecha, una notificación perdida en silencio.
- **El PAT se toma con respaldo** (`${SIRIUS_TRIGGER_TOKEN:-$GH_TOKEN}`): bajo
  `set -u` una variable sin definir aborta, y una parada segura que revienta por
  un secreto ausente deja la incidencia muda — que es exactamente lo que la PR
  #136 tardó ocho rondas en cerrar. Sin PAT se degrada a notificar peor, nunca a
  no parar.

## Comprobación que la sostiene

- Prueba estructural que **deriva** del propio `notify` la lista de estados
  notificables en vez de copiarla, y comprueba **paso a paso**. Su primera
  versión miraba si el fichero contenía el PAT en alguna parte y **pasaba con la
  mutación puesta**; al hacerla precisa encontró dos pasos más que se habían
  escapado.
- Cuatro mutaciones verificadas en las dos direcciones.
- Verificado que ningún workflow reacciona a los estados afectados salvo el
  notificador: los tres roles escuchan únicamente sus etiquetas-evento.
- **Lo que NO demuestra:** que el PAT recupere de verdad la notificación. Eso
  solo puede verse en una ejecución real; la prueba fija quién escribe con qué
  identidad, no el comportamiento de GitHub.

## Consecuencias

- Cada transición emite un `issues: labeled` más desde una identidad real. Hoy
  nadie lo consume salvo el notificador; si algún día un workflow reacciona a un
  estado persistente, habrá que revisar esta decisión.
- Los avisos de arranque y cierre de bloque vuelven a llegar.
- Una ronda en la que Codex responde por comentario termina en segundos con
  `respuesta-por-comentario` en vez de agotar 20 minutos de runner.

## Alternativas descartadas y por qué

**(B) notificaciones**: duplicaría en cuatro sitios la lógica de deduplicación y
de resolución del head que hoy vive en un solo fichero. **(C)**: barato, pero
renuncia a los dos avisos que marcan el principio y el final de cada bloque.

**(B)/(C) del recolector**: harían que una frase en texto libre de un tercero
decidiera una aprobación. Un cambio de redacción del conector la falsearía, y el
contrato exige hoy una señal formal precisamente para eso. Quedan disponibles si
el propietario redacta la cláusula, con una prueba de mutación por cada frase
que se acepte como «sin hallazgos».

**Retirado durante el trabajo:** una tercera propuesta (P3) interpretaba un
resumen formal solitario como parada rápida. Rompía dos pruebas que defienden
algo real —una revisión con cuerpo pero sin comentarios inline debe seguir
esperando por si llegan tarde—, así que no se aplicó. La propuesta del
verificador, aplicada literalmente, habría debilitado el sistema.
