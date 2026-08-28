# Nota de arranque — implementar el descarte de ADR-098

Fecha: 2026-08-28. Publicada ANTES del primer cambio de código (ADR-001).

## Lo medido que obliga

Pasada 5 del banco (run 33139753661): el atestado paró la pasada en **5
segundos, cero cuota gastada** — correcto — porque `gemini-3.5-flash` está en
`429: You exceeded your current quota`. La cuota diaria de Google se la comieron
sus dos pasadas fallidas de hoy (7 preguntas × ~192 s de llamadas cada una, dos
veces), y hasta que reponga, el banco entero está bloqueado.

La foto: **Google está DESCARTADO por ADR-098 y aun así sigue en el banco**,
quemando su cuota en cada pasada —lo que garantiza el mismo 429 mañana— y su
agotamiento bloquea la medición de NVIDIA, que es la configuración elegida y
está viva. Un descarte decidido que no se implementa no es un descarte: es una
factura recurrente.

## Lo que se decide construir

1. **`configuraciones.yml` queda con la configuración elegida** (NVIDIA). La
   revancha de Google está escrita en ADR-098 y ejecutarla es revertir este
   cambio de una línea.
2. **El comparador aprende lo que ya es verdad**: con UNA configuración
   declarada, la pasada es una MEDICIÓN, no una comparación. Si esa única sale
   medida → `MEDIDA ÚNICA`, código 0. Si no → NO CONCLUYENTE, código 2, como
   siempre. Con dos o más declaradas, nada cambia: el criterio «medir una sola
   no vale» era de la PREGUNTA comparativa, que ADR-098 cerró.
3. **El workflow deja de exigir la clave de Google**: el guardián de claves
   deriva de `configuraciones.yml` y los dos tienen que decir lo mismo.

## Las cuatro preguntas

1. ¿Con una declarada y medida, el código es 0 y el veredicto dice MEDIDA
   ÚNICA? ¿Y el informe deja claro que NO es una comparación?
2. ¿Con una declarada y NO medida, sigue siendo código 2? Una pasada vacía no
   puede salir verde por ser pequeña.
3. ¿Con DOS o más declaradas, el veredicto viejo queda intacto? (medir una →
   NO CONCLUYENTE; servidores iguales → COMPARACIÓN FALSA).
4. ¿El atestado sigue mandando con una sola? Sin atestado o con el modelo no
   usable, código 5, exactamente igual que hoy.

## Criterio de parada

- (a) Si «medición única» pudiera colarse como «comparación concluyente» en
  cualquier salida (veredicto, JSON, informe), se para.
- (b) La propiedad anti-contaminación (el hijo no hereda variables no
  declaradas) tiene que seguir probada EJECUTANDO con dos configuraciones de
  laboratorio: quitar a Google del fichero real no puede llevarse la prueba.
- (c) Regla de las dos rondas (ADR-001).

## Lo que NO se toca

Ni el banco, ni `fuentes > 0`, ni el atestado, ni la configuración de NVIDIA.
