# Nota de arranque — la memoria cabe en una sola lectura, y dejó de caber

Rama `fix/la-memoria-cabe-en-una-sola-lectura`, 14-09-2026. Publicada **antes
del primer commit de arreglo**, como exige ADR-001.

## El suceso

Al regenerar `MEMORIA.md` tras dar de alta un defecto nuevo, la guarda de
ADR-171 se puso en rojo:

```
AssertionError: MEMORIA.md pesa 120207 bytes: por encima de 120000 deja de
leerse entera de una vez y vuelve a ser un corpus (ADR-171, criterio (c))
```

No es un defecto de ese cambio: sobre `main`, `MEMORIA.md` pesa ya **119.370
bytes**. Quedaban **630 bytes** de margen y cada ADR nuevo añade unos 430. Es
decir: **el siguiente ADR, fuera cual fuera, rompía la guarda.** El motor está
bloqueado para toda decisión nueva hasta que esto se arregle.

## 1. ¿Dónde vive el fallo y dónde va el arreglo?

No vive en `MEMORIA.md`: es un fichero generado, no lo escribe nadie. No vive en
la guarda: el límite es la promesa de ADR-171 y está haciendo exactamente su
trabajo —avisar antes de que la vista deje de ser una vista—.

Vive en **lo que la vista decide llevar**: el generador mete, por cada ADR y
para siempre, el primer párrafo entero de su sección «Decisión». Eso no es un
índice, es el corpus otra vez, y crece sin techo por construcción.

El arreglo va, por tanto, en el generador —`src/sirius_engine/memoria.py`—, y
consiste en decidir **qué parte de cada decisión merece estar en la vista de una
sola lectura**.

*¿Puede el sitio del arreglo observar el fallo que arregla?* Sí: el generador es
quien produce el fichero cuyo tamaño se mide.

## 2. ¿Qué NO va a garantizar esto?

- **No detiene el crecimiento.** Compra margen. Un ADR nuevo seguirá pesando, y
  este arreglo tiene que decir con números **cuándo volverá a hacer falta**, en
  vez de dejarlo para que lo descubra otra vez una guarda en rojo.
- **No cambia qué es la memoria.** El índice completo de ADR —número, fecha,
  estado, título y enlace— sigue entero en una sola lectura. Lo que se va es el
  párrafo de resumen de las decisiones viejas, que está **literalmente en el ADR
  que la fila enlaza**.
- **No toca el límite.**
- **No borra nada.**

## 3. Criterio de parada, decidido ANTES de mirar ningún resultado

- **El límite NO se sube.** Subir una frontera para que una guarda deje de
  morder es la mutación que ADR-192 dejó documentada como la peligrosa: la regla
  deja de existir en silencio. Si la única salida fuera subirlo, se para y se
  consulta al propietario.
- **No se borra nada** (ADR-195): lo que salga de la vista tiene que seguir
  existiendo y estar enlazado desde donde estaba.
- **El índice completo se queda en una lectura.** Si el arreglo obliga a salir
  del fichero para saber *qué ADR existen*, no vale: eso es justo la orientación
  que la vista existe para dar.
- **El criterio de qué se conserva tiene que ser derivado**, no un «los últimos
  N» elegido a ojo, que es la familia `lista-a-mano`.
- **El arreglo trae la cuenta de su propio vencimiento:** cuántos ADR caben
  después, con el dato con el que se calcula.
- **Una mutación sembrada y vista caer por cada regla nueva.**

## 4. ¿Qué haría el fallo imposible en vez de improbable?

**Que nada que crezca con cada ADR viva dentro de la vista.** Hoy hay tres
secciones que crecen así: el índice de decisiones, el de documentos y el de
lecciones. Mientras alguna lleve texto por elemento sin techo, el fichero vuelve
a crecer sin techo; lo único que cambia es cuándo.

Lo que lo cerraría del todo es que la vista lleve **recuentos y punteros** y que
el detalle viva en vistas generadas aparte —el patrón que ADR-171 ya usa con
`DESENLACES.md`—. Es más caro, cambia lo que un lector encuentra al entrar, y
**no se hace aquí**: queda declarado, con la cifra que dirá cuándo toca.
