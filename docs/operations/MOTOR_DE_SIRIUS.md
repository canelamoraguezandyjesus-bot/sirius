# Cómo se usa el motor de Sirius

## Para qué está esto aquí

Hasta hoy, `sirius-supervisar` no aparecía en ningún documento del repositorio y
`sirius-despachar` solo dentro de ADRs, que son actas de decisión y no manuales.
Es decir: existían las dos piezas que mueven el motor y **no había ningún sitio
que dijera cómo se usan**.

Esto no describe cómo está construido el motor —eso son ADR-082 y ADR-083—, sino
qué se teclea y qué hay que esperar que pase.

## 1. Darle una orden: `sirius-despachar`

Se le habla en lenguaje llano. Él convierte la orden en una incidencia con
objetivo, alcance permitido, lo que queda fuera y sus validaciones obligatorias,
y le pone la etiqueta que arranca el ciclo.

```
uv run sirius-despachar "Corrige el fallo X en el módulo Y"
```

**Por defecto solo ENSAYA: no escribe nada.** Enseña la incidencia que crearía y
sale. Para que escriba de verdad hace falta `--ejecutar`.

Esa asimetría no es prudencia decorativa. De una incidencia de verdad cuelga un
ciclo entero —implementador, Quality y dos revisores—, así que una orden mal
entendida no cuesta un aviso: cuesta cuatro agentes trabajando sobre algo que
nadie pidió.

El ensayo **atraviesa el mismo despachador** que la ejecución, con un escritor
que no escribe. Se hizo así porque antes cortaba justo antes de llamarlo, y por
eso podía anunciar «esto saldría» de un trabajo que el despachador habría
rechazado (H-12). Un ensayo que no pasa por las guardas no ensaya nada.

### Lo que hoy NO acepta, y conviene saberlo antes de teclear

- **Los verbos son pocos.** Quien interpreta la orden es un apaño provisional
  (ADR-043): para programación entiende «corrige» o «implementa» **al principio
  de la frase**. Una orden que empiece por otro verbo sale rechazada como
  «intención ambigua», y no crea nada.
- **Solo despacha `programacion` y `auditoria`.** Una orden de documentación se
  acepta al entrar y luego el despachador la rechaza.
- **`--ejecutar` necesita dos cosas, y falla en este orden.** Primero la
  variable `SIRIUS_BOT_TOKEN`: sin ella el escritor **no llega ni a
  construirse** —el fallo ocurre antes de cualquier escritura, con un mensaje
  claro y código de salida 4, no con un crash—. Y después la herramienta `gh`,
  porque es por donde habla con GitHub. El ensayo funciona sin ninguna de las
  dos, porque no sale al exterior.

  Donde falte cualquiera de ellas, la incidencia se puede crear a mano con el
  cuerpo y la etiqueta que el ensayo imprime. El apartado 4 dice qué se pierde
  al hacerlo.

## 2. Darle un turno al motor: `sirius-supervisar`

El motor no implementa nada. Su trabajo es **reconciliar el mundo**: cerrar como
perdido lo que se perdió, reactivar o sustituir lo que se puede salvar, y
escalar lo que no.

```
uv run sirius-supervisar            # da el turno de verdad
uv run sirius-supervisar --ensayo   # solo resuelve rutas y lo dice
```

Normalmente no se teclea a mano: lo lanza el workflow «Motor de Sirius» desde la
pestaña Actions.

**Un turno sin trabajo dentro no anota nada, y eso es correcto.** Si el diario
está vacío, el motor mira, no encuentra nada que reconciliar y sale en verde sin
escribir. No confundir ese verde con «el motor funciona»: significa «no había
nada que hacer». Es una distinción que ya costó un día entero de dar por
probado lo que no se había ejecutado.

**Dos turnos a la vez se pisan.** Un turno es ciego a todo lo que ocurra después
de arrancar, así que dos simultáneos sobre el mismo diario pueden crear el mismo
trabajo dos veces. Lo único que lo impide es el grupo de concurrencia del
workflow. Quien invoque este comando desde otro sitio hereda ese deber.

## 3. Dónde vive su memoria

En la rama **`estado-del-motor`**, huérfana a propósito: no comparte historia con
`main` y no la arrastra. Son dos ficheros:

- `diario.jsonl` — los encargos, sus ejecuciones y sus transiciones.
- `diario-supervision.jsonl` — lo que ya hizo el supervisor, para que un turno no
  repita lo del anterior.

El workflow la trae a un árbol de trabajo **fuera del espacio de trabajo**, para
no ensuciar el estado de `main`, y devuelve lo anotado con un `push` a esa misma
rama. El porqué de que viva ahí y no en `main` está en ADR-083.

La rama **no existe hasta la primera anotación**: el motor la crea huérfana él
mismo la primera vez que tenga algo que escribir. Que no aparezca todavía no es
un fallo.

## 4. Cómo encajan las dos piezas

```
orden tuya
   -> sirius-despachar   -> incidencia + etiqueta -> el ciclo la implementa
                         -> anota el encargo en el diario del motor
                                                        |
   -> sirius-supervisar  <---------------------------- lee de ahí
      (mira si algo se perdió y actúa)
```

**El ciclo va por etiquetas, no por el diario.** Una incidencia creada a mano con
la etiqueta correcta se implementa igual. Lo que se pierde entonces es la
anotación: el supervisor no sabrá de ese encargo, así que si se atasca **no lo va
a recuperar**. El diario no mueve el trabajo; es lo que permite rescatarlo.
