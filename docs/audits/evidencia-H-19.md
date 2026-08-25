# Evidencia — H-19

## Las cuatro preguntas, decididas ANTES de medir

1. ¿Cuántos fallos distintos produce la comparación por subcadena del intérprete?
2. ¿Alguno deja pasar una orden que la puerta debería escalar?
3. ¿Alguno rechaza una orden legítima?
4. ¿Se arreglan por separado, o comparten raíz?

## Criterio de parada, escrito antes de ver resultados

- Si sale **un solo** fallo, se despacha como encargo normal.
- Si salen **dos o más de la misma familia**, se aplica la regla de las dos
  rondas (ADR-001): **parar y buscar la raíz**, no parchear casos sueltos, y no
  despachar hasta saber si la raíz se puede tocar sin decidir producto.
- Si alguno afecta a **qué escala la puerta**, no se despacha en absoluto: el
  alcance del *fail-closed* es criterio del propietario sobre su propia
  barrera, no del implementador.

## Afirmación

`intent_interpreter` compara sus marcadores con `in` sobre el texto
normalizado, **sin frontera de palabra**, y además comprueba los marcadores de
pasado **antes** que la sensibilidad. De esa única raíz salen al menos tres
fallos, dos de ellos serios en direcciones opuestas.

## Comprobación que la sostiene

**(a) Deja pasar lo que debería escalar.** Una orden destructiva que contenga
por casualidad `estado de` sale por la rama de consulta y nunca llega al
detector de sensibilidad:

```
'borra el estado de la base de produccion'  -> consultar_pasado  None
'elimina el estado del cache'               -> consultar_pasado  None
'implementa esto usando una clave real de pago
 y borra el estado de la cola'              -> consultar_pasado  None
```

Ese último pierde además la causa `gasto_o_presupuesto`. El propio comentario
del módulo declara lo contrario: «es preferible sobre-marcar como sensible que
dejarlo pasar».

**(b) Rechaza lo legítimo.** `estado de` es subcadena de `estado del`, giro
corriente en este repositorio:

```
'documenta el estado del motor'      -> consultar_pasado
'audita el estado de las pruebas'    -> consultar_pasado
'corrige el estado del despachador'  -> consultar_pasado
```

Y el mensaje de ayuda desorienta: dice que hace falta «corrige» o «implementa»
al principio, cuando el verbo **sí** estaba al principio y **sí** está
reconocido.

**(c) Rechaza su propio ejemplo documentado.** `_primer_verbo` no quita la
puntuación, así que el formato que el propio `--help` propone falla:

```
'Corrige el fallo'    -> orden_inequivoca
'«Corrige el fallo»'  -> ambigua
'"Corrige el fallo"'  -> ambigua
'Corrige, ya, el fallo' -> ambigua
```

## Cómo decidió el criterio de parada

Los tres son de la **misma familia** —comparación por subcadena sin frontera,
más el orden de las comprobaciones—, así que se aplica la regla de las dos
rondas: **no se despacha ningún parche suelto**. Y (a) toca el alcance del
*fail-closed* de la puerta, que es criterio del propietario. Por eso esta
incidencia queda **abierta y sin activar**, con la raíz nombrada, en vez de
convertirse en tres encargos que se pisarían entre sí.

## Lo que hace falta antes de despacharlo

Una decisión del propietario sobre **una** pregunta: si la comprobación de
sensibilidad debe ir **antes** que la de marcadores de pasado. Con eso
respondido, el resto —frontera de palabra y limpieza de puntuación— es
mecánico y cabe en un solo encargo.

## Por qué esto no lleva ADR todavía

Porque la decisión aún no está tomada. El ADR lo escribirá quien responda a
esa pregunta, con esta medición delante. Escribirlo ahora sería decidir por el
propietario sobre su propia barrera de seguridad.
