# ADR-196 — La vista de memoria lleva el índice completo de decisiones, y el resumen solo de las que siguen vigentes como método

- Estado: APROBADO
- Fecha: 2026-09-14
- Aprobación: el propietario, fusionando la PR de esta rama.

## Contexto y problema

`MEMORIA.md` es la vista que ADR-171 creó para que **lo primero que lee una IA al
entrar quepa en una sola lectura**. Su criterio (c) lo defiende una guarda:
`test_la_memoria_cabe_en_una_sola_lectura`, con un límite de 120.000 bytes.

El 14-09-2026 esa guarda se puso en rojo:

```
AssertionError: MEMORIA.md pesa 120207 bytes: por encima de 120000 deja de
leerse entera de una vez y vuelve a ser un corpus (ADR-171, criterio (c))
```

No fue culpa del cambio que la destapó. Sobre `main`, el fichero pesaba ya
**119.370 bytes**: quedaban **630 bytes** de margen. Y cada ADR que se fusiona
añade, medido sobre las cinco fusiones de esa misma noche, **unos 1.350 bytes**:

| Fusión | `MEMORIA.md` | Crecimiento |
|---|---|---|
| ADR-191 | 113.969 | — |
| ADR-192 | 115.170 | +1.201 |
| ADR-190 | 116.766 | +1.596 |
| ADR-193 | 118.047 | +1.281 |
| ADR-194 | 119.370 | +1.323 |

Es decir: **el siguiente ADR, fuera cual fuera, rompía la guarda.** El motor
quedaba bloqueado para toda decisión nueva.

## Dónde vive el fallo

No en `MEMORIA.md`, que es generado. No en la guarda, que hizo exactamente su
trabajo: avisar antes de que la vista dejara de ser una vista.

Vive en **lo que la vista decide llevar**. El generador copiaba, por cada ADR y
para siempre, el primer párrafo entero de su sección «Decisión». La sección de
decisiones pesaba **81.037 bytes de los 119.370**: el 68 % del fichero. Eso no
es un índice; es el corpus otra vez, que es justo de lo que ADR-171 venía
huyendo.

## Criterio de parada (escrito ANTES de decidir)

En `docs/audits/arranque-la-memoria-cabe-en-una-sola-lectura.md`, publicado en el
primer commit de esta rama. Lo que quedó prohibido de antemano:

- **Subir el límite.** Mover una frontera para que una guarda deje de morder es
  la mutación que ADR-192 dejó documentada como la peligrosa: la regla deja de
  existir en silencio.
- **Borrar nada.** Lo que salga de la vista sigue existiendo y sigue enlazado.
- **Sacar el índice completo de la lectura única.** Saber QUÉ se decidió es la
  orientación que esta vista existe para dar.
- **Elegir «los últimos N» a ojo** — la familia `lista-a-mano`.
- Y se exigió que el arreglo trajera **la cuenta de su propio vencimiento**.

## Decisión

**El índice se queda entero; la copia del resumen, no.**

- La tabla sigue listando **todos** los ADR, con número, fecha, estado, título y
  enlace. Nada desaparece de la vista.
- La columna «Resumen» la llevan los ADR **desde `PRIMER_ADR_CON_LECCION`**. De
  los anteriores queda `—`, y su resumen está **en el ADR que la propia fila
  enlaza**, a un clic.

La frontera no es un número elegido a ojo: es la constante que ya gobierna qué
ADR forman el corpus vivo del método —los que declaran lección (ADR-174)—. Se
reutiliza en vez de inventar otra, y por eso no puede desincronizarse de aquella.

**Esto no es podar.** El texto no se ha ido a ninguna parte: el resumen es una
*copia* del primer párrafo del ADR, y el original no se toca. Lo que se quita es
la duplicación, no el contenido.

## Lo que se gana, con números

Medido sobre **este mismo árbol** —con el arreglo y sin él—, para que las dos
cifras sean comparables:

| | |
|---|---|
| `main`, antes de tocar nada | 119.370 bytes, **630** de margen |
| Este árbol **sin** el arreglo | **121.022** bytes: por encima del límite |
| Este árbol **con** el arreglo | **90.142** bytes, **29.858** de margen |
| Ahorro | **30.880** bytes, de 168 filas |
| A 1.350 bytes por ADR fusionado | **unos 22 ADR de margen** |

La fila del medio es la que importa: este ADR, con sus dos documentos de
evidencia y su entrada en el registro, **habría roto la guarda él solo**.

**Y aquí está la fecha de caducidad de este arreglo, que el criterio de parada
exigía declarar:** esto compra unos 22 ADR, no un techo. A ritmo de noche
intensa —cinco ADR en una— son pocas semanas.

## Lo que este ADR NO hace, y cuándo tocará

- **No detiene el crecimiento.** Siguen creciendo con cada ADR: la fila de la
  tabla de decisiones (~430 bytes), las dos filas del índice de `docs/audits`
  —la nota de arranque y la evidencia—, la fila de lecciones y la del registro
  de defectos.
- **El siguiente corte, cuando el margen vuelva a apretar**, es el índice de
  `docs/audits`: 83 filas y 11.026 bytes hoy, y crece a dos filas por ADR. La
  vía que cerraría el problema del todo —que la vista lleve recuentos y punteros
  y el detalle viva en vistas generadas aparte, como ADR-171 ya hace con
  `DESENLACES.md`— es más cara y cambia lo que un lector encuentra al entrar.
  Queda declarada, sin hacerse.
- **No sube el límite** ni lo tocará este ADR si vuelve a apretar: eso sería
  cambiar la promesa en vez de cumplirla.

## Comprobación que la sostiene

Dos guardas nuevas, y el árbol de prueba pasa a tener **un ADR por encima de la
frontera**: sin él, «ninguno lleva resumen» habría pasado igual y la regla solo
se mediría por un lado.

- `test_el_indice_de_decisiones_esta_completo_aunque_el_resumen_no` — la mitad
  que de verdad importa proteger: aligerar la vista borrando filas sería podar
  en el sentido que el propietario prohibió, y se llevaría por delante la
  orientación.
- `test_solo_las_decisiones_desde_la_frontera_llevan_resumen_en_la_vista` — la
  regla, por sus dos lados.

**Tres mutaciones, las tres vistas caer:**

| | Mutación | Resultado |
|---|---|---|
| MA | todos llevan resumen (volver atrás) | cae `solo_las_decisiones_desde_la_frontera` |
| MB | ninguno lleva resumen | cae la misma, por el otro lado |
| MC | **la poda ingenua**: quitar de la tabla los ADR viejos | cae `el_indice_esta_completo` **la primera** |

MC es la que importa: es lo que alguien haría con prisa para que el fichero
quepa, y es exactamente lo que no se puede hacer.

## La lección

- familia: `vista-que-copia-el-corpus-del-que-venia-huyendo`
- sin esto se repetiría: una vista que existe para caber en una sola lectura
  copia, por cada elemento y para siempre, un trozo del documento que enlaza; el
  fichero crece sin techo por construcción y el aviso llega cuando ya no cabe
  —`MEMORIA.md` llegó a estar a 630 bytes del límite, con el siguiente ADR
  rompiéndolo fuera cual fuera—.
- lo hace cumplir: `tests/engine/test_memoria.py`
