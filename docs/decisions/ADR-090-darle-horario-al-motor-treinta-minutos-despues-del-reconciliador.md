# ADR-090 — Darle horario al motor, treinta minutos después del reconciliador

- Estado: PROPUESTO
- Fecha: 2026-08-25
- Aprobación: la fusión de la PR por el propietario
- Relacionadas: ADR-082 (el motor dentro de Actions), ADR-083 (su memoria),
  ADR-086 (el despachador con manos), ADR-064, y la excepción del contrato
  v1.6 §9.1 bajo la que corre `reconcile-sirius-states`

**Esta es también la nota de arranque de la rama**, publicada antes del primer
cambio (ADR-001).

## Contexto y problema

`motor-sirius.yml` sólo se disparaba a mano. Su propia cabecera decía por qué, y
la razón era buena:

> «Un motor que empieza a correr solo antes de que nadie le haya visto dar un
> turno es cómo se rompen las cosas de madrugada. La cadencia es la decisión
> siguiente, y necesita medir antes cómo convive con `reconcile-sirius-states`.»

Las tres condiciones que esa frase pedía **ya se cumplen**:

- Se le ha visto dar turnos a mano, y los siete pasos corren.
- Su camino de escritura está probado por ejecución (ADR-083).
- Su diario dejó de estar vacío: el despachador anotó el primer encargo real el
  25-08-2026, y con él nació la rama de memoria (ADR-086).

Sin lo tercero el horario no tenía sentido: un motor puntual vigilando un mundo
vacío es un gasto sin contrapartida.

## Criterio de parada (escrito ANTES de decidir)

**(a)** Si el motor y el reconciliador pueden **escribir lo mismo**, se para. No
comparten grupo de concurrencia, así que nada los serializa: si tocaran el mismo
estado habría que serializarlos antes de programar nada.

**(b)** Si un turno programado **puede quedarse en ensayo sin que nadie lo note**,
se para. Un motor que corre cada seis horas para no hacer nada, en verde, es el
peor resultado posible: cuesta minutos y aparenta funcionar.

**(c)** Si la cadencia se elige **sin medir** con qué convive, se para. Es
literalmente lo que la cabecera antigua exigía.

## Medición

**Criterio (a) — no escriben lo mismo.** Medido:

```
reconcile-sirius-states.yml : cron '17 */6 * * *' · group reconcile-sirius-states
motor-sirius.yml            :                      · group motor-sirius
```

Grupos distintos, sí, pero el reconciliador escribe **etiquetas** y el motor
escribe **su diario**. El motor no lleva `issues: write` -está en su bloque
`permissions`, y una prueba lo vigila-. No hay escritura compartida, así que no
hace falta serializarlos. Con quien **sí** comparte candado el motor es con el
despachador (ADR-086), porque ésos dos sí escriben el mismo diario.

**Criterio (b) — y aquí saltó el defecto, antes de entrar.** El paso «Dar el
turno» decidía así:

```bash
if [ "${{ inputs.ensayo }}" = "false" ]; then
```

En un evento `schedule` **no hay inputs**: `inputs.ensayo` se expande a la
cadena vacía, y `"" = "false"` es falso. **Todos** los turnos programados se
habrían ido por la rama del ensayo. El motor corriendo cada seis horas para no
hacer nada, en verde y para siempre — y cableado a propósito.

Es la misma familia que costó el 24-08 («un verde que no dice *funciona* sino
*no llegó a intentarlo*»), y esta vez la habría introducido quien la había
diagnosticado.

## Decisión

**El motor corre a `47 */6 * * *`**, treinta minutos después del reconciliador.

El desfase no es estético: el reconciliador **repara estados que ningún evento
puede ya revivir**, así que dejarle asentar el mundo antes de que el motor lo
mire evita que el motor razone sobre un estado que está a punto de cambiar.
Primero se asienta, luego se supervisa.

**Cada seis horas y no más**, a propósito: hoy el diario tiene un encargo, y el
valor de un turno es proporcional al trabajo en vuelo. Se sube cuando haya algo
que mirar.

**Y la rama se decide por el EVENTO, no por un input que en ese evento no
existe:**

```bash
if [ "$EVENTO" = "schedule" ]; then          # actúa
elif [ "$ENSAYO_PEDIDO" = "false" ]; then    # actúa
else                                          # ensaya
```

## Comprobación que la sostiene

Las cuatro combinaciones, **ejecutadas** como bash las ve:

```
evento=schedule           ensayo=(vacio) -> ACTUA (programado)
evento=workflow_dispatch  ensayo=false   -> ACTUA (a mano)
evento=workflow_dispatch  ensayo=true    -> ensayo
evento=workflow_dispatch  ensayo=(vacio) -> ensayo
```

**La guarda se vio fallar**, devolviéndole al workflow el condicional original:

```
FAILED test_el_guion_real_toma_la_rama_que_debe[schedule--actua]
FAILED test_un_turno_programado_no_puede_decidirse_solo_por_el_input
2 failed, 5 passed
```

`tests/automation/test_turno_programado_actua.py` **ejecuta el guión real** del
paso, no lo lee. Leerlo no habría bastado: el defecto no estaba en el texto,
estaba en cómo bash trata una variable vacía, y una prueba que buscara una frase
en el YAML habría pasado en verde con el fallo dentro.

## Consecuencias

**El motor deja de depender de que alguien se acuerde de él.** Es el último
tramo de D2, y con él la supervisión —construida desde C1 y sin nada que
supervisar hasta hoy— empieza a tener trabajo por su cuenta.

**Aparece un turno de madrugada sin nadie mirando**, que es lo que la cautela
antigua temía. Lo que ha cambiado no es el riesgo: es que ahora su camino de
escritura está probado, su diario existe, y un turno sin trabajo dentro sale en
verde sin escribir nada -medido-.

**Lo que esto NO resuelve:** que el motor sepa qué hacer con lo que encuentre
más allá de reconciliar y escalar. Sigue sin decidir nada por su cuenta, y esa
frontera no la mueve este ADR.

## Alternativas descartadas y por qué

- **Cadencia horaria**: gasta minutos de Actions proporcionalmente al reloj, no
  al trabajo en vuelo. Con un encargo en el diario, no compra nada.
- **El mismo minuto que el reconciliador**: arrancarían a la vez sin nada que
  los serialice, y el motor miraría un mundo que el otro está cambiando.
- **Programarlo antes de tener el diario con trabajo**: es lo que la cabecera
  antigua impedía, y tenía razón. El horario llega después del primer encargo
  real, no antes.
