# ADR-258 — Hacer sitio en la memoria común nombrando cada ADR por su número, sin su ruta

- Estado: APROBADO
- Fecha: 2026-10-18
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205).

Este ADR es además la **nota de arranque** de este cambio dentro de la rama
`claude/que-no-se-enrolle` (skill `disciplina-evidencia`): las cuatro preguntas y el
criterio de parada están escritos antes de tocar el generador de `MEMORIA.md`.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** La batería de esta rama falla en
   `tests/engine/test_memoria.py::test_la_memoria_cabe_en_una_sola_lectura`:
   `MEMORIA.md` pesa 120 509 bytes con ADR-256 y ADR-257, y su tope es 120 000
   (ADR-171, criterio (c)). En `main` (`7fb10525`) pesa 119 537: quedan 463 bytes de
   margen, menos de lo que añade un ADR, así que cualquier rama con uno la rompe, la de
   la 0.4 también. La raíz es la que dejó escrita D-6
   (`docs/audits/decisiones-abiertas-del-propietario.md`): cada ADR añade a la vista
   su fila y su lección, contra un tope fijo. De los 72 417 bytes de la tabla de
   decisiones, 28 490 son la ruta de cada ADR, que repite su título en minúsculas y
   sin tildes. El arreglo va en el generador, `src/sirius_engine/memoria.py`: la fila
   nombra el ADR por su número, como ya lo nombran las lecciones desde ADR-218, y su
   fichero se encuentra por ese número. **¿Puede el sitio del arreglo observar el
   fallo?** Sí: la guarda mide el fichero que escribe el generador.
2. **Qué NO garantiza.**
   - No para el crecimiento: cada ADR sigue añadiendo su fila, ya sin ruta, y su
     lección. Compra unos 28 000 bytes, no un techo.
   - No decide D-6, que sigue abierta y es del propietario.
   - En GitHub la tabla deja de ser clicable: el fichero se abre por su número.
3. **Criterio de parada**, antes de tocar el generador:
   - La tabla sigue con todos los ADR, cada uno con su número, su fecha, su estado,
     su título y, desde el 174, su resumen: ninguna fila ni ningún resumen sale.
   - Las pruebas de la vista cambian solo donde miraban la ruta, y una nueva comprueba
     que la tabla no la repite y que cada número lleva a su fichero.
   - La batería entera en verde, con `MEMORIA.md` por debajo de 120 000 bytes.
   - Si para caber hiciera falta quitar una fila o un resumen, o subir el tope, se
     para: son las salidas de D-6, y son suyas.
4. **Qué lo haría imposible.** Una vista que no crezca con cada ADR: la salida B de
   D-6, el índice completo en una vista generada aparte, como ya vive
   `docs/audits/INDICE.md`. Cambia lo que encuentra quien entra y lo que `AGENTS.md`
   promete de `MEMORIA.md`, «cada ADR con su resumen»: es del propietario, y no se
   hace aquí.

## Contexto y problema

`MEMORIA.md` existe para que lo primero que lee una sesión al entrar quepa en una sola
lectura (ADR-171). Ya se ha quedado sin sitio tres veces: el 14-09, y ADR-196 quitó la
copia del resumen de los ADR viejos; el 01-10, y ADR-218 sacó el índice de
`docs/audits/` a una vista aparte y dejó de repetir rutas en las lecciones; y el 17-10,
y ADR-251 recortó el resumen de 240 a 160 caracteres. ADR-218 dejó escrito que no
quedaba otro corte de ese tipo que no fuera podar, y llevó a la hoja del propietario lo
que queda, D-6, con tres salidas que cambian lo que encuentra quien entra.

Quedaba uno sin podar: la fila de cada ADR enlaza su fichero con la ruta entera, y la
ruta es el título otra vez. Una fila media pesa 284 bytes, y de ellos 113 son la ruta.
Las sesiones leen la vista en texto, no en GitHub: ahí la ruta es el título repetido, y
el fichero se encuentra igual con su número, `docs/decisions/ADR-NNN-*.md`.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

1. **Subir el tope.** Lo prohibió ADR-196, y es la salida A de D-6: suya.
2. **Recortar otra vez el resumen.** Medido sobre este árbol: de 160 a 80 caracteres
   ahorra 4 366 bytes, unos diez ADR, y deja resúmenes que ya no dicen qué se decidió.
3. **Sacar el índice de decisiones a una vista aparte.** Es la salida B de D-6: suya.
4. **Nombrar cada ADR por su número, sin la ruta que repite su título.** Ahorra 28 490
   bytes medidos sobre este árbol, sin quitar ninguna fila ni ningún resumen. **Esta.**

## Decisión

La tabla de decisiones de `MEMORIA.md` nombra cada ADR por su número, con su fecha, su
estado, su título y, desde el 174, su resumen, y ya no lleva la ruta de su fichero. La
cabecera de la tabla dice dónde está cada uno: `docs/decisions/ADR-NNN-*.md`, por su
número, que es como ya los nombran las lecciones (ADR-218) y el registro de defectos.

**Esto no es podar** (ADR-195): todos los ADR siguen en la tabla, con todo lo que
llevaban menos la ruta, y la ruta repetía el título. D-6 sigue abierta, y la hoja del
propietario lo apunta con el margen que queda.

## Comprobación que la sostiene

- El fallo, en la batería de esta rama sobre `3af419ea`: 9 177 en verde, 15 omitidas,
  2 xfail y 1 fallo, `test_la_memoria_cabe_en_una_sola_lectura`, con `MEMORIA.md` a
  120 498 bytes.
- `MEMORIA.md` en `main` (`7fb10525`): 119 537 bytes, medido con `git show
  origin/main:MEMORIA.md | wc -c`.
- Dónde pesa, medido con el generador sobre este árbol antes de tocarlo: la tabla de
  decisiones, 72 417 bytes de 120 498; sus 251 filas, 284 bytes de media; sin la ruta,
  la vista pesaría 92 008 bytes, 28 490 menos. Con el resumen a 140, 120, 100 y 80
  caracteres, 119 588, 118 425, 117 400 y 116 132 bytes.

## Consecuencias

- `MEMORIA.md` vuelve a caber, con unos 28 000 bytes de margen.
- Quien lee la vista en GitHub ya no puede pinchar en la fila de un ADR: lo abre por su
  número.
- D-6 sigue abierta: el margen se gasta otra vez al ritmo de los ADR.

## Alternativas descartadas y por qué

- **Subir el tope y sacar el índice aparte**: son salidas de D-6, del propietario.
- **Otro recorte del resumen**: ahorra poco y quita lo que la vista existe para dar.

## La lección

- familia: `vista-que-copia-el-corpus-del-que-venia-huyendo`
- sin esto se repetiría: la fila de cada ADR llevaba su título dos veces, una en su ruta, y la vista volvía a no caber con el ADR siguiente
- lo hace cumplir: `tests/engine/test_memoria.py`
