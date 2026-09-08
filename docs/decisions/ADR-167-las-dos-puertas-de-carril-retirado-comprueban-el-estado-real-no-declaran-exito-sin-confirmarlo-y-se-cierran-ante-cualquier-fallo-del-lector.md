# ADR-167 — Las dos puertas de carril retirado comprueban el estado real, no declaran éxito sin confirmarlo y se cierran ante cualquier fallo del lector

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Corrige: **ADR-163** (PR #569, fusionada como `afe704e`), cuya implementación
  de la retirada reversible traía los cinco defectos que este ADR arregla
- Numeración: 167 y no 165. `scripts/siguiente_adr.py` propuso 165 porque solo
  ve las ramas del clon; las PR abiertas **#573 y #575** ya tienen tomados el
  165 y el 166. Es el mismo modo de fallo que ADR-069 documenta, y aquí se
  evitó mirando las PR abiertas antes de asignar
- Relacionadas: ADR-161 (la retirada acordada), ADR-014 y ADR-015 (la etiqueta
  se escribe con el PAT), ADR-004 y contrato §9.1 (qué repara de verdad el
  reconciliador), ADR-001

> **Este ADR es también la nota de arranque de la rama**, publicado en su propio
> commit antes del primer cambio de código.

## Nota de arranque (publicada ANTES del primer cambio)

**1. ¿Dónde vive el fallo y dónde va el arreglo?** Los cinco defectos viven en
las dos puertas que ADR-163 añadió —`investigar-orden.yml` y
`audit-sirius-repository.yml`— y en el arnés que las prueba. Cuatro son de la
misma familia y conviene decirlo antes de arreglar nada: **la puerta afirma cosas
que no ha comprobado**. Afirma que respondió (sin confirmar el comentario), que
transicionó (sin confirmar las etiquetas), que el carril está activo (cuando el
lector falló de un modo que no previó) y que el evento describe la incidencia
(cuando el evento puede venir atrasado). El quinto es distinto: una prueba que
fija como requisito permanente lo que el contrato promete reversible.

El arreglo vive en las mismas dos puertas, y puede funcionar porque el sitio del
arreglo sí puede observar el fallo: cada afirmación tiene una comprobación
disponible —el código de salida de la llamada, la lectura del estado por la API,
el código del lector— que hoy simplemente no se mira.

**2. ¿Qué NO va a garantizar esto?**

- **No garantiza exactamente-una-vez en el comentario.** `sirius_comment_once`
  ya declara por qué eso es imposible contra la API de GitHub: un POST aceptado
  cuya respuesta se pierde deja el comentario publicado sin que nadie lo sepa.
  Se acota la ventana con el marcador; no se cierra.
- **No garantiza que el job termine en verde.** Al contrario: cuando la
  respuesta o la transición no se puedan confirmar, el paso terminará en **rojo**
  a propósito, que es lo que hoy no hace.
- **No reactiva ningún carril.** El registro real sigue con los dos retirados.
- **No cambia Sirius, la memoria común, el roadmap, permisos, secretos ni
  configuración remota.** No toca revisores, corrector, agregación,
  convergencia, Quality, diario ni informes.
- **No prueba con agentes reales ni con red**: todo con dobles explícitos.

**3. Criterio de parada (escrito ANTES de tocar nada).**

- **(a)** Si algún hallazgo resulta ya corregido en `main`, se dice y no se
  «arregla» otra vez. *Comprobado: los cinco siguen presentes en `afe704e`.*
- **(b)** Si el arreglo del #1 exigiera apoyarse en el reconciliador, **hay que
  demostrar** que repara el estado concreto que se le deja; si no lo repara, el
  diseño cambia en vez de suponerlo. *Se disparó: no lo repara. Ver abajo.*
- **(c)** Si corregir el #2 obligara a leer el estado con credenciales que la
  puerta no tiene, o a tocar permisos, se para.
- **(d)** Si el arreglo del #5 debilitara las comprobaciones de formato o de
  seguridad del registro, se rechaza aunque pase.
- **(e)** Dos rondas con defectos de la misma familia → parar y buscar la raíz.
  La familia ya está nombrada arriba y es la que ordena los cuatro primeros
  arreglos, así que la raíz se ataca de una vez: **ninguna puerta afirma nada
  que no haya confirmado.**

**4. ¿Qué haría imposible el error más probable, en vez de improbable?** El error
más probable es el que ya ocurrió: probar la puerta buscando cadenas en el YAML
en vez de ejecutarla. Una prueba que lee texto no distingue «llama a
`sirius_comment_once`» de «lo llama y comprueba su resultado». Lo hace imposible
**ejecutar el guion real con `bash` y un doble de `gh` que puede fallar a
voluntad**, y comprobar el efecto observable: qué comentarios se publicaron, qué
etiquetas quedaron, qué código de salida dio el paso y si el agente llegó a
ejecutarse. Eso es lo que se construye aquí. Lo que **no** se puede hacer
imposible desde el repositorio: que GitHub acepte un POST y pierda la respuesta.

## Lo que el reconciliador SÍ repara, medido (criterio de parada (b))

Se leyó `scripts/automation/sirius_reconcile.sh` antes de diseñar el arreglo del
hallazgo 1, porque el encargo exige demostrarlo y no suponerlo:

- **Solo repara dos casos**: el A (marcador de completado) y el B
  (`sirius:ci-pending` con Quality ya resuelto). Para todo lo demás **informa y
  no toca** (contrato §9.1, límites 2 y 4).
- Un `sirius:planned` + `sirius:implement-requested` atascado **no se repara**:
  el propio guion lo excluye del informe de contradicción por ser «el ÚNICO
  estado en que `implement-requested` existe en produccion sana».
- Y un `sirius:completed` + `sirius:failed-safely` simultáneo —el síntoma del
  hallazgo 2— le sale como **CONTRADICCION que requiere revisión humana**.

**Conclusión: el reconciliador no es la vía de recuperación de estas puertas.**
El arreglo no se apoya en él. La recuperación es que el paso termine en rojo y
que reejecutarlo converja, porque cada operación es idempotente.

## Decisión

Una regla, de la que salen los cuatro primeros arreglos: **ninguna puerta afirma
nada que no haya confirmado, y ante lo que no puede confirmar se detiene en rojo
en vez de continuar en verde.**

1. **Orden de operaciones e informe de fallos (hallazgo 1).** Primero el
   comentario, después las etiquetas, y **cualquier fallo de cualquiera de los
   dos termina el paso en rojo**. El comentario **no menciona el estado final**,
   así que sigue siendo cierto aunque la transición no llegue a hacerse.
   Reejecutar converge: el marcador evita el comentario duplicado y las
   etiquetas se aplican igual.
2. **Estado real antes de tocar (hallazgo 2).** La puerta lee la incidencia por
   la API y decide con eso, no con el cuerpo del evento: si está cerrada, si
   lleva una etiqueta terminal o de completado, o si ya no lleva
   `sirius:implement-requested`, **no toca nada** y sale con `valid=false`. El
   perfil se relee del cuerpo actual, no del que traía el evento.
3. **Contrato del lector, explícito (hallazgo 3).** `0` retirado, `1` activo,
   **cualquier otro código detiene el paso** con diagnóstico y sin ejecutar el
   carril. Vale para las dos puertas.
4. **Marcador en el cuerpo (hallazgo 4).** El marcador va como primera línea del
   comentario, en la convención de comentario HTML que ya usa
   `sirius_apply_verdict.sh`, y es el mismo que se pasa como argumento.
5. **Pruebas del mecanismo, no del estado del registro (hallazgo 5).** Las
   pruebas usan registros controlados —uno con carriles retirados y otro sin
   ninguno— y dejan de exigir que el registro real tenga siempre las dos
   entradas. Se conservan las comprobaciones de formato y de seguridad, y se
   añade una que demuestra que una reactivación válida las supera.

## Comprobación que la sostiene

Se rellena en el commit que la produce, con los resultados reales.

## Consecuencias

- Las dos puertas pueden terminar en rojo donde antes terminaban en verde. Es el
  cambio buscado: un verde que no se ha ganado es peor que un rojo.
- El registro real **no cambia**: los dos carriles siguen retirados.
