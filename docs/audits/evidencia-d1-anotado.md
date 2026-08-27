# Evidencia — D1, anotado sin exagerar

Rama `d1-anotado`, 27-08-2026. Sin ADR: no hay decisión nueva. La de cablear la
reversión está en `evidencia-autoridad-sin-llamante.md`; esto solo pone el
registro al día.

## Afirmación

Las tres mitades de D1 tienen ya llamante:

| mitad | módulo | quién la llama |
|---|---|---|
| D1a — comparar motor e incidencia | `projection_verifier` | la pasada diaria |
| D1b — contar los siete días | `seven_day_streak` | `contador-siete-dias.yml`, 03:24 UTC |
| D1c — la salida de emergencia §11.4 | `authority_reversion` | la pasada diaria, desde hoy |

## Comprobación

```
uv run pytest tests/automation/test_piezas_con_llamante.py  -> 5 passed
uv run pytest tests/automation/test_registro_de_bloques.py  -> 30 passed
```

Y la mutación que lo sostiene: quitar el `import` de `authority_reversion` de la
pasada diaria pone en rojo `test_cada_pieza_tiene_quien_la_llame`.

## Lo que este apunte NO dice, que es la mitad que importa

Un registro que solo cuenta lo bueno se convierte en propaganda, así que queda
escrito en el propio bloque:

- **Los siete días siguen sin empezar.** Un día sin línea no es un día verde, y
  las líneas dependen de que haya trabajo circulando **y** de que sus incidencias
  se puedan leer.
- **La salvaguarda está conectada, no ejercitada.** Hoy no hay ninguna clase
  conmutada al motor, así que la pasada dirá «ninguna clase requiere reversión».
  Eso es lo correcto y hay que leerlo como lo que es.
- **D1 sigue `pendiente`.** Tener las tres piezas cableadas no lo cierra: lo
  cierra el contrato §11.2, y ése pide días verdes medidos, no piezas conectadas.

## Criterio de parada (escrito antes)

Si al anotar hubiera que cambiar el `estado` de D1 a algo distinto de
`pendiente`, se para: cablear no es medir, y confundirlos sería exactamente el
defecto que este repositorio lleva toda la noche persiguiendo.

No hizo falta: el estado no se toca.
