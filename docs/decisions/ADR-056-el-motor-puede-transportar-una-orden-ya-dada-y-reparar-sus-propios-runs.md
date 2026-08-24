# ADR-056 — El motor puede transportar una orden ya dada y reparar sus propios Runs

- Estado: APROBADO
- Fecha: 2026-08-21
- Enmendado: ADR-082 supera «el motor es un observador externo» como razón de la separación §12 / §9.1, que se mantiene con otro criterio (decisión I4, #270)
- Aprobación: decisión del propietario por interrogatorio (21-08-2026); fusión de la PR
- Contexto: bloque E1b del plan del Work Engine (ADR-020); contradicciones C1 y C2 de la arquitectura §14; contrato operativo v1.7 → v1.8
- Relacionadas: ADR-004 (la red periódica no es motor), ADR-037 (qué gestos son del propietario), ADR-041 (autoridad por clase, v1.7)

## Contexto y problema

La arquitectura §14 dejó cinco contradicciones «presentadas y detenidas, no
resueltas». Tres siguen abiertas al llegar aquí; **C1 y C2 son las dos que la
Fase C consume**, y sin ellas la Fase C no empieza:

- **C1.** El contrato §9.1 límite 1 dice «no aplica **nunca**
  `sirius:implement-requested`». Pero el despacho del motor necesita esa
  etiqueta. Sin resolverlo, el motor puede preparar el trabajo entero y la
  activación sigue siendo un clic humano: **se conserva exactamente el cuello de
  botella que el Work Engine viene a eliminar**.
- **C2.** El contrato §9 prohíbe «usar vigilancia periódica como **motor** del
  flujo». Pero el supervisor sondea y **actúa**. Sin resolverlo, el motor no
  existe como motor: se reduce a otra colección de reacciones a eventos, con la
  misma clase de atascos ya pagados.

La arquitectura no las resolvió a propósito: las dejó como enmiendas del
contrato «al autorizar la implementación», que es este bloque.

## Criterio de parada (escrito ANTES de decidir)

Este bloque se decidió con el método de interrogatorio
(`docs/implementation/METODO_INTERROGATORIO.md`), cuyo criterio de parada es
parte del método y estaba escrito antes de la primera pregunta:

> Para cuando **lo que queda por saber ya no cambia lo que construirías**.

Y uno propio de la enmienda, fijado antes de redactar una línea:

> La enmienda vale solo si, después de ella, **§8 y §9.1 siguen diciendo
> exactamente lo que decían**. Si para autorizar al motor hay que aflojar el
> merge o los límites del vigilante periódico, la redacción está mal: son
> actores distintos y relajar dos cosas creyendo que se relaja una es el error
> que esta sección tiene que evitar.

## Opciones consideradas

1. Aflojar los límites de §9.1 para que amparen también al motor.
2. Borrar las dos prohibiciones de §9 y reescribirlas.
3. Dejar §8 y §9.1 intactas y **añadir** una sección propia del motor, con sus
   propios límites, y acotar las prohibiciones de §9 con un puntero.

## Decisión

**La tercera.** Se añade **§12** al contrato (v1.8) y no se toca ni una palabra
de §8 ni de §9.1.

**§12.1 — transportar una orden ya dada no es iniciativa.** El motor puede
aplicar `sirius:implement-requested`, y solo si existe una orden explícita del
propietario **registrada y enlazada en la evidencia** de ese WorkItem. Sin orden
enlazada, no arranca nada. Lo que sigue prohibido es lo que el límite protegía:
la máquina no decide qué trabajo existe.

**§12.2 — supervisar y reparar sus propios Runs**, con cuatro límites: solo SUS
Runs; no inventa trabajo; **no fusiona nunca**; y el vigilante de §9.1 se queda
como respaldo con sus límites intactos.

**§12.3** enumera explícitamente lo que no cambia, para que nadie lo deduzca al
revés.

### Lo que decidió el propietario, con sus palabras

Tres preguntas, una cada vez, cada una con una propuesta y con lo que habría
hecho cambiar de opinión:

| Pregunta | Respuesta |
| --- | --- |
| ¿Qué prefieres que Sirius sepa hacer antes: investigar de verdad, o desatascarse solo? | «desatascarse solo» |
| Cuando tú ya has pedido un trabajo, ¿puede el motor darle la salida él solo? | «que la dé el motor» |
| Cuando un trabajo que el motor lanzó se queda colgado, ¿puede arreglarlo él solo? | «que lo arregle solo» |

La primera no es decorativa: fija que la Fase C va antes que la Fase B, y por
tanto que esta enmienda hace falta **ahora** y no después de M2 —el plan la
prefería tras M2, y el propietario invirtió ese orden a propósito—.

### Lo que decidió la sesión, y por qué

- **Sección nueva en vez de aflojar §9.1.** El motor y el vigilante periódico
  son actores distintos con razones distintas. §9.1 existe porque «un proceso
  que muere no puede informar de su propia muerte»; el motor es justamente un
  observador externo. Meterlos en la misma excepción habría relajado los límites
  del vigilante sin que nadie lo hubiera decidido.
- **Las prohibiciones de §9 se acotan con un puntero, no se borran.** Quien lea
  §9 sigue leyendo la prohibición, y ve dónde están sus dos excepciones. Borrar
  la frase habría hecho desaparecer la norma junto con su límite.
- **El texto sale literal de las recomendaciones de la arquitectura §14**, que
  es lo que el plan exigía para no enmendar de más.

## Comprobación que la sostiene

### El criterio de parada se cumple: §8 y §9.1 quedan intactas

```
$ git diff --stat docs/implementation/AUTOMATION_OPERATING_CONTRACT.md
```

Los únicos cambios en texto preexistente son la cabecera de versión y los dos
guiones de §9 que ganan su puntero. **§8 y §9.1 no tienen ni una línea
modificada.** Todo lo demás es sección nueva.

### Las pruebas estructurales que vigilan §9.1 siguen en verde

Es la prueba de terminado que el plan exige para este bloque, y era el riesgo
real: el límite 1 de §9.1 —«no aplica nunca `sirius:implement-requested`»— es
exactamente lo que §12.1 autoriza **al motor**, y aflojarlo por descuido habría
autorizado también al vigilante.

```
$ uv run pytest tests/automation/test_sirius_reconcile.py -q
41 passed
```

### El argumento práctico de §12.1 no es teórico

Mientras el propietario delegó ese gesto en la sesión interactiva, esa sesión
puso la etiqueta mal **tres veces en una sola noche** (20-21 de agosto), y las
tres detuvieron un bloque:

| Fallo | Qué paró |
| --- | --- |
| Activación con `sirius:implement-requested` sin `sirius:planned` | La puerta de activación lo rechazó; la incidencia #211 quedó sin etiquetas |
| `sirius:review-requested` puesta 48 s antes de que Quality terminara | El revisor se detuvo: el head no tenía Quality verde |
| Repetir esa etiqueta creyendo arreglarlo | El registro seguía diciendo lo mismo; se detuvo otra vez |

Poner esa etiqueta es comprobar precondiciones mecánicas. Una máquina lo hace
mejor que una persona a las cuatro de la mañana, y las tres paradas lo
demuestran sin necesidad de argumentar.

## Consecuencias

- La Fase C queda desbloqueada: C1 puede empezar en cuanto esta PR se fusione.
- El propietario deja de teclear la etiqueta de arranque, sin perder el control
  de qué trabajo existe: sin orden suya enlazada, no hay arranque.
- El merge sigue siendo su único gesto obligatorio.
- Las contradicciones C1 y C2 de la arquitectura §14 pasan de «detenidas» a
  resueltas. Queda C5, que entró en vigor con la v1.7 (ADR-041).
- Y una consecuencia que conviene decir: **el motor podrá levantar trabajos
  caídos sin despertar a nadie.** Esa es la mitad que el propietario eligió
  primero, y también la que más hay que vigilar: §12.2 límite 4 deja la red
  periódica debajo precisamente por eso.

## Alternativas descartadas y por qué

**Aflojar §9.1 para que amparase también al motor.** Es lo que pedía el camino
corto, y es el error que el criterio de parada prohibía por adelantado: los
cinco límites de §9.1 protegen a un actor que no puede informar de su propia
muerte, y el motor no es ese actor. Relajarlos de paso habría autorizado al
vigilante a arrancar bloques, que es justo lo que RECON-STUCK-007/013 vigilan.

**Borrar las dos prohibiciones de §9 y reescribirlas.** Más limpio de leer y
peor de mantener: la norma y su excepción dejarían de estar en el mismo sitio, y
la próxima persona leería la excepción sin haber leído nunca la regla.

**Esperar a M2, como prefería el plan.** El plan decía «conviene tras M2
(evidencia de que el motor existe y aporta)». El propietario invirtió el orden a
propósito al elegir «desatascarse solo» antes que «investigar de verdad», y la
razón que dio es buena: la evidencia de que el motor aporta la quiere en forma
de no tener que vigilarlo él, no en forma de un informe.
