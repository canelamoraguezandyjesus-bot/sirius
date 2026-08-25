# Evidencia — H-18

## Las cuatro preguntas, decididas ANTES de medir

1. ¿Puede una sesión de Claude escribir en `.claude/evidencia/`, uno de los dos
   sitios que el hook ofrece?
2. ¿Reconoce el hook `docs/audits/` como sitio válido para evidencia?
3. ¿Produjo un falso positivo real, o el aviso era correcto?
4. ¿Puede arreglarlo el ciclo, o hace falta el propietario?

## Criterio de parada, escrito antes de ver resultados

- Si `.claude/evidencia/` **sí** es escribible, no hay contradicción y esto no se
  registra: sería una queja sobre una molestia, no un defecto.
- Si el hook **sí** mira `docs/audits/`, el aviso fue correcto y el error es mío
  por no haber leído dónde lo pedía. Tampoco se registra.
- Si el arreglo cae dentro de lo que el ciclo puede tocar, se despacha como
  encargo. Si no, se abre incidencia **sin** etiquetas de activación: activar
  algo que sólo puede acabar en rechazo es fabricar ruido.

## Afirmación

El hook ofrece dos ubicaciones y **una está en la lista `deny`**, así que ninguna
sesión de Claude puede usarla. Como además no reconoce `docs/audits/`, marca
como «sin evidencia» una rama que sí la tenía.

## Comprobación que la sostiene

**Pregunta 1** — intento real de escribir en `.claude/evidencia/registrar-h17.md`:

```
Permission to use Bash with command … .claude/evidencia/registrar-h17.md …
has been denied.
```

Y la causa, en el propio fichero de ajustes: `Edit(./.claude/**)` está en
`permissions.deny`.

**Pregunta 2 y 3** — la evidencia se escribió en `docs/audits/evidencia-H-17.md`
y se publicó en la rama:

```
51621ae Registrar H-17: …
 docs/audits/evidencia-H-17.md     | 71 +++++++++++++++++++++++++++++++++++++++
 docs/audits/registro_defectos.yml | 10 ++++++
```

Y aun así el hook volvió a bloquear el final del turno pidiendo evidencia. Es
decir: **falso positivo confirmado**, no una omisión.

**Pregunta 4** — el arreglo vive en `.claude/hooks/recordar_parada.py`, dentro
del mismo árbol denegado. El ciclo tampoco lo toca. Luego es del propietario.

## Cómo decidió el criterio de parada

Los tres primeros puntos se cumplieron en contra de descartar, así que se
registra. El cuarto decidió la forma: incidencia **#311 sin etiquetas de
activación**, porque despacharla sólo produciría un rechazo.

## Por qué esto no lleva ADR

No hay decisión que registrar todavía. El arreglo propuesto —aceptar
`docs/audits/evidencia-*.md` y retirar `.claude/evidencia/` de la oferta
mientras siga denegada— es una consecuencia directa de la medición, no una
elección entre opciones. Si el propietario prefiriese en cambio **abrir**
`.claude/evidencia/` en la lista de permisos, eso sí sería una decisión sobre
sus propias barreras, y entonces el ADR lo escribe él con esta medición delante.
