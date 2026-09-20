# ADR-201 — La mina de aprendizaje tiene reloj: el día 1 de cada mes se pide la edición del mes que se cierra

- Estado: APROBADO
- Fecha: 2026-09-14
- Aprobación: el propietario, el 14-09-2026: «la poda mensual de la mina lo
  hacemos».
- Incidencia: #646
- Enmienda: precisa ADR-063 y ADR-082 sobre quién puede despachar

- Nota de arranque de esta rama: **este ADR**. Publicado, con criterio de parada
  fijado, ANTES del primer commit del workflow (precedente: ADR-063).

## Criterio de parada (escrito ANTES de tocar nada)

Terminado cuando:

1. El fichero existe, GitHub lo puede leer, y el texto de la orden viaja por una
   variable, no interpolado en el guion.
2. El disparo por reloj **ejecuta de verdad** y el disparo a mano **ensaya**
   salvo que se marque. Al revés, la pasada mensual no haría nada y el fallo
   sería invisible durante meses.
3. La hora cae **fuera** de la ventana de silencio del contador de siete días, y
   el `timeout-minutes` no supera el mayor ya declarado.
4. Comparte grupo de concurrencia con `motor-sirius.yml`.
5. La cadena entera en verde.

**Me detengo, sin terminar, si:** hiciera falta ampliar el alcance del PAT o los
`permissions:` más allá de lo que `despachar-orden.yml` ya declara.

## Contexto y problema

La mina de aprendizaje operativo es el único sitio donde este repositorio mira
sus propios ciclos y saca de ellos **una cifra en vez de una impresión**. Tiene
dos ediciones, agosto y septiembre, y **las dos se pidieron a mano**.

La de septiembre existe por una razón concreta: hacía falta medir el detector de
familia repetida para poder decidir si darle autoridad. Si esa decisión no
hubiera estado encima de la mesa esa noche, **no se habría escrito** — y la
medida que la sostiene (14 aciertos y 2 falsos sobre 16, ADR-197) no existiría.

Eso es H-198 otra vez: algo que hay que hacer periódicamente y que **no tiene
quien lo vuelva a poner delante de nadie**.

## La decisión, y la frontera que mueve

**1. Un reloj pide la mina del mes que se cierra.** `.github/workflows/mina-mensual.yml`,
el día 1 de cada mes, despacha un encargo de documentación con el texto de la
orden **escrito dentro del propio fichero**.

**2. Y hay que decir en voz alta lo que eso extiende.** `despachar-orden.yml`
lleva escrito que *«la automatización nunca crea trabajo por su cuenta»*, que es
lo que protege ADR-063. Un reloj que despacha **sí** crea trabajo sin que nadie
lo pida ese día.

La diferencia, y es la que sostiene esta decisión: **la orden no la inventa la
máquina**. Está escrita aquí, palabra por palabra, y entra en `main` por el mismo
gesto que cualquier otro cambio. El propietario no aprueba «que el motor decida»:
aprueba ESTE texto y ESTE reloj, y puede retirarlos igual que los puso. ADR-082 ya
movió esta frontera una vez —«lo invoca un workflow»—; esto es el siguiente paso
de la misma, y se registra como enmienda, no como excepción.

**3. Podar es archivar.** La orden incluye ADR-195: si una lección de la edición
anterior deja de estar vigente, se mueve a un fichero de archivo fechado y se
deja en su sitio la cita que dice dónde está. Nunca se borra.

## La hora: 09:24 UTC, y por qué «fuera de la ventana» no bastaba

Esta sección estaba escrita antes de correr la suite y **decía otra cosa**. Se
deja corregida, con lo que la comprobación enseñó.

**Lo que se creía.** `contador-siete-dias.yml` corre a las 03:24 UTC y exige que
nada se mueva en los **170 minutos previos** a su pasada, con **2 minutos de
margen** sobre los 172 que hay desde las 00:32. De ahí salió la primera elección:
las 04:00, que caen fuera de esa ventana.

**Lo que la suite enseñó.** El contador no elige su hora: la **deriva**.
`sirius-racha --hora-recomendada` busca el mayor hueco libre de disparos
periódicos del directorio y devuelve su punto medio, y una guarda exige que el
cron cableado sea **exactamente** esa hora (ADR-144), para que la frase de su
cabecera sea verdad sola.

Así que un `schedule:` nuevo tiene una condición **más fuerte** que «caer fuera
de la ventana»: **si parte el mayor hueco, la hora derivada se mueve** y el
contador deja de estar donde su propia guarda exige. Con las 04:00, la derivación
pasó a devolver **09:24** y las dos pruebas del contador se pusieron en rojo:

```
el contador dispara en [204] (minutos del día) y la derivación devuelve 564
(09:24 UTC, punto medio del mayor hueco libre ... tras las 06:32 UTC)
```

**El criterio bueno, que es el que queda escrito:** el contador se queda con el
mayor hueco, y un trabajo periódico nuevo se va al **punto medio del siguiente**.
Con 09:24 el mayor hueco sigue siendo 00:32 → 06:17 (345 min), la derivación
sigue devolviendo 03:24, y el contador no se toca.

Había una segunda salida —mover el contador a 09:24, que es lo que su propio
mensaje de error sugiere— y **no se tomó**: habría hecho que un trabajo mensual
nuevo moviera la pasada diaria de la que depende el hito D1. Mover lo estable
para acomodar lo nuevo es la dirección equivocada.

Por una cuenta parecida, el trabajo declara `timeout-minutes: 15`: la tolerancia
del contador es `max(timeout-minutes de todos los jobs) × 2`, así que un tope
mayor que el actual la movería y rompería lo mismo por el otro lado.

## Lo que este ADR NO hace

- **No decide qué dice la mina.** El encargo es de documentación y tiene
  prohibido implementar, cablear, decidir, escribir ADR o dar de alta defectos.
- **No toca `docs/canonical/`, el contrato, el Producto ni la Arquitectura.**
- **No abre la puerta a que el motor se encargue trabajo a sí mismo.** Lo que se
  autoriza es un texto fijo en un reloj fijo, no una capacidad.
- **No se ha ejecutado todavía.** Un workflow solo se demuestra ejecutándolo
  (`test_expresiones_de_workflow.py` lo dice de sí misma). El primer disparo
  real se vigila a mano.

## La lección

- familia: `tarea-periodica-sin-reloj`
- sin esto se repetiría: el único trabajo que mide los ciclos de este
  repositorio dependía de que a alguien se le ocurriera pedirlo, y la edición de
  septiembre solo existe porque esa noche hacía falta una cifra concreta para
  otra decisión.
- lo hace cumplir: ninguna prueba: que el reloj dispare de verdad no lo puede
  comprobar este árbol; lo demuestra el primer disparo, y hasta entonces se
  vigila a mano.
