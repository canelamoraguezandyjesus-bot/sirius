# ADR-086 — Dar manos al despachador dentro de Actions, para que el encargo llegue al diario del motor

- Estado: PROPUESTO
- Fecha: 2026-08-25
- Aprobación: la fusión de la PR por el propietario
- Relacionadas: ADR-063 (el despachador y su ensayo), ADR-002 (la automatización
  no toca los workflows que la gobiernan), ADR-082 y ADR-083 (el motor y su
  memoria), ADR-064 (la reserva de despacho vive en el diario)

**Esta es también la nota de arranque de la rama**, publicada antes del primer
cambio (ADR-001).

## Contexto y problema

`sirius-despachar` convierte una orden del propietario en una incidencia
activada, y está construido y probado desde C2. Para escribir en GitHub necesita
dos cosas: la credencial `SIRIUS_BOT_TOKEN` y la herramienta `gh`.

**Una sesión interactiva no tiene ninguna de las dos.** El token vive en los
secretos de Actions —donde lleva meses, y donde lo consumen siete workflows del
ciclo— y no se expone a la sesión. Medido: al construir el escritor real desde
esta sesión,

```
MissingCredentialError: falta la variable de entorno 'SIRIUS_BOT_TOKEN'
```

Consecuencia práctica hasta hoy: la sesión generaba el cuerpo correcto con el
despachador **en ensayo** y luego publicaba la incidencia **a mano**, por fuera
de `dispatch_work_item`.

**Lo que eso rompía no era la comodidad.** Una incidencia creada a mano no pasa
por el despachador, así que el encargo **no se anota en el diario del motor**. El
ciclo arrancaba igual —va por etiquetas— pero el supervisor no sabía que ese
trabajo existía y no podía rescatarlo si se atascaba. Las seis incidencias
despachadas los días 24 y 25 llevan esa nota escrita en su propio cuerpo.

Dicho de otro modo: **el motor llevaba semanas vigilando un mundo vacío**, y no
por un defecto suyo.

## Criterio de parada (escrito ANTES de decidir)

**(a)** Si la solución exige **exponer la credencial a la sesión interactiva**,
se para. Un token de escritura en el contexto de una sesión es un permiso que
sobrevive a la tarea que lo pidió.

**(b)** Si la solución permite que **la automatización decida despachar por su
cuenta**, se para. Eso es lo que ADR-063 protege: la orden nace del propietario,
y una máquina que se crea trabajo a sí misma no tiene freno.

**(c)** Si exige **tocar el código del despachador**, se para. Si hiciera falta
cambiar `src/`, sería señal de que la abstracción estaba mal, y eso es otro
bloque.

**(d)** Si el despacho puede **coincidir con un turno del motor**, se para. Los
dos escriben el mismo diario, y la exclusión está medida en
`tests/engine/test_exclusion_entre_invocaciones.py`.

## Opciones consideradas

1. **Dar la credencial a la sesión.** Descartada por el criterio (a).
2. **Un workflow que recoja órdenes de los comentarios de una incidencia.**
   Descartada por (b) y por prematura: convierte «por dónde habla el propietario
   con Sirius» en una decisión de fontanería, cuando es una decisión de producto
   que el propietario todavía no ha tomado. Además el propietario declaró el
   25-08 que su centro de mando **es la sesión interactiva**, así que este canal
   no resolvería un problema que tenga hoy.
3. **Un workflow disparable con la orden como entrada.** Es la elegida.

## Decisión

**Opción 3.** `.github/workflows/despachar-orden.yml`, disparado a mano
(`workflow_dispatch`) con dos entradas: `orden` —el texto tal cual— y `ejecutar`
—apagado por defecto, así que **lo normal es ensayar**—.

El workflow trae la memoria del motor a un árbol de trabajo, ejecuta
`sirius-despachar` con `SIRIUS_MOTOR_DIARIO` apuntando a ese diario, y confirma
lo anotado con un `push` a la rama de memoria. Es el mismo baile que
`motor-sirius.yml`, y se copia de ahí a propósito: ya está probado.

**Quién decide sigue siendo quien decidía** (criterio b, respetado). El workflow
no elige despachar: recibe el texto de una orden que ya salió del propietario a
través de su sesión interactiva, y le pone las manos. La automatización sigue
sin poder crear trabajo por su cuenta y sin poder tocar los workflows que la
gobiernan.

**No se toca `src/`** (criterio c, respetado): `SIRIUS_MOTOR_DIARIO` y
`--ejecutar` ya existían.

**Comparte grupo de concurrencia con el motor** (criterio d, respetado):
`group: motor-sirius`, `cancel-in-progress: false`. No es cosmético — los dos
escriben el mismo diario en la misma rama, y dos invocaciones simultáneas crean
el mismo trabajo dos veces con la misma clave de idempotencia y el mismo número
de secuencia. Un grupo propio habría dejado esa puerta abierta.

## La orden viaja por `env:`, nunca interpolada

`${{ inputs.orden }}` dentro de un `run:` se sustituye **antes** de que bash lea
nada, así que una orden con acentos graves o `$(...)` ejecutaría lo que llevara
dentro con los permisos del trabajo. El texto entra por `env: ORDEN` y se usa
como `"$ORDEN"`: así es un dato y no puede ser código.

Se dice aquí y no solo en el fichero porque es la clase de detalle que alguien
«simplifica» en un cambio posterior sin ver lo que abre.

## Comprobación que la sostiene

El fichero pasa las dos guardas que este repositorio pagó caras:

```
uv run pytest tests/automation/test_expresiones_de_workflow.py   -> 4 passed
uv run pytest tests/automation/test_serializacion_del_motor.py   -> 5 passed
uv run ruff check .                                              -> código 0
uv run pytest tests/automation                                   -> 720 passed, 5 skipped
```

La de serialización es la que importa aquí: reconoce `despachar-orden.yml` como
invocación del motor —deriva los comandos de `[project.scripts]`, no de una
lista escrita a mano— y exige grupo constante y `cancel-in-progress: false`.

**Lo que estas comprobaciones NO dicen**, y conviene no leerlo de más: que el
despacho funcione en el servidor. Eso solo lo dice ejecutarlo, y este mismo
fichero ya enseñó el 24-08 que un workflow puede pasar Quality en verde y no
arrancar siquiera, porque **Quality no mira los workflows**. La ejecución real
va después de fusionar, y su resultado se anota en la PR.

## Consecuencias

**El motor deja de vigilar un mundo vacío.** Es el efecto que se buscaba: a
partir del primer despacho real, su diario tiene encargos, y la supervisión
—construida, probada y hasta hoy sin nada que supervisar— empieza a tener
trabajo. También significa que el camino de escritura del motor, probado por
ejecución pero nunca ejercitado por un turno real, se ejercitará solo.

**La sesión interactiva deja de publicar incidencias a mano.** Con ello
desaparece la nota que las seis incidencias de estos días llevan en el cuerpo, y
el WorkID vuelve a significar lo que dice.

**Sigue habiendo un humano en el bucle, y dos.** El propietario dicta la orden y
aprueba el merge. Lo que se automatiza es el tramo mecánico de en medio.

**Lo que esto NO resuelve, y no hay que leerlo aquí:** que alguien sepa partir un
objetivo grande en bloques. `sirius-despachar` convierte **una frase en un
encargo**. Pedirle una versión entera del producto produce un encargo de alcance
imposible, y esa pieza no existe todavía.
