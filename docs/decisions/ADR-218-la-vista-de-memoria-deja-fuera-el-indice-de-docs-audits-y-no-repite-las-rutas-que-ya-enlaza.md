# ADR-218 — La vista de memoria deja fuera el índice de `docs/audits`, que pasa a una vista generada aparte, y no repite las rutas que ya enlaza

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR #664 por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-01-la-vista-vuelve-a-caber-en-una-sola-lectura.md`,
  confirmada antes del primer commit de arreglo, con las predicciones y el
  criterio de parada.

## Contexto y problema

`MEMORIA.md` existe para que **lo primero que lee una IA al entrar quepa en una
sola lectura** (ADR-171, criterio (c): 120.000 bytes, y lo que hacer si se
supera: «resúmenes más cortos o una sección fuera»). El 14-09 dejó de caber y
ADR-196 quitó la copia del resumen de los ADR anteriores a la frontera; compró
«unos 22 ADR» y dejó escrito cuál sería el siguiente corte: «el índice de
`docs/audits`: 83 filas y 11.026 bytes hoy, y crece a dos filas por ADR».

Han entrado 21 ADR (del 197 al 217) y el 01-10-2026 volvió a no caber. Quality
falló sobre la PR #664, la que trae la bitácora del ciclo a `main` (ADR-217):

```
FAILED tests/engine/test_memoria.py::test_la_memoria_cabe_en_una_sola_lectura
AssertionError: MEMORIA.md pesa 125587 bytes: por encima de 120000
```

No es culpa de esa PR sola. Sobre `main` (`a60c059a`) la vista pesa **116.854
bytes**: quedaban **3.146** de margen, menos de lo que añade un ADR, así que el
siguiente cambio con ADR la rompía fuera cual fuera. La PR #664 añade 138 filas
de `docs/audits/` al índice de documentos y la pasa de largo.

Dónde pesa, medido sobre este árbol antes de tocar nada:

| Sección | Bytes | De ellos, rutas |
|---|---|---|
| Tabla de decisiones (211 filas) | 59.228 | 23.035 |
| Lecciones por familia (43 lecciones) | 23.813 | **10.992**: 86 enlaces a ADR que la tabla de arriba ya enlaza |
| Documentos, de los que `docs/audits/` | 27.009, de ellos **20.446** | 138 filas, 82 sin fecha declarada |

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, resumido: no se sube el límite; no se borra nada
—cada fila que salga de la vista tiene que estar en el índice generado, y una
prueba lo mide por los dos lados—; el índice lo escribe el mismo comando y lo
vigila la misma guardia que la vista; si con los dos cortes el margen quedara
por debajo de 20 ADR, no se inventa un tercero en este ADR; tres mutaciones
tienen que caer antes de confirmar.

## Opciones consideradas

1. **Subir el límite.** Prohibido por ADR-196 y por la propia razón del
   límite: una vista que no se lee entera vuelve a ser un corpus.
2. **Quitar filas viejas de la tabla de decisiones.** Es la poda ingenua que
   ADR-196 dejó impedida por prueba (`test_el_indice_de_decisiones_esta_completo`)
   y que ADR-195 prohíbe: saber QUÉ se decidió es la orientación que la vista
   existe para dar.
3. **Resúmenes más cortos** (`LONGITUD_RESUMEN` de 240 a menos). Lo permite
   ADR-171, pero ahorra unos 3.000 bytes hoy y quita información; no toca lo
   que crece.
4. **El corte que ADR-196 dejó declarado, más no repetir lo que la vista ya
   enlaza. Esta.**

## Decisión

1. **El índice de `docs/audits/` sale de `MEMORIA.md` y vive en
   `docs/audits/INDICE.md`, generado.** Lo escribe el mismo comando
   (`uv run sirius-memoria conocimiento` escribe los dos ficheros) y lo vigila
   la misma guardia (`comprobar_memoria` y `--comprobar` recorren las dos
   vistas; `test_la_memoria_confirmada_en_este_arbol_esta_al_dia` falla si
   cualquiera de las dos no coincide con el árbol). En la vista queda, bajo
   `### docs/audits`, el recuento, cuántos no declaran fecha, la fecha más
   reciente declarada y el enlace al índice. El índice no cuenta como
   documento ni se indexa a sí mismo, igual que `MEMORIA.md`.
2. **La sección de lecciones nombra cada ADR por su número**, en la tabla de
   familias y en cada lección, en vez de repetir el enlace que la tabla de
   decisiones ya lleva para todos (`test_el_indice_de_decisiones_esta_completo`).

**Esto no es podar** (ADR-195): cada fila que sale de la vista está en el
índice, con la misma forma, y una prueba lo comprueba fila a fila por los dos
lados. Lo que se quita es la duplicación, no el contenido.

## Lo que se gana, con números

Medido sobre **este mismo árbol**, con el arreglo y sin él:

| | |
|---|---|
| `main` (`a60c059a`), antes de tocar nada | 116.854 bytes, **3.146** de margen |
| Este árbol **sin** el arreglo | **125.932** bytes: 5.932 por encima del límite |
| Este árbol **con** el arreglo | **94.931** bytes, **25.069** de margen |
| Ahorro | **31.001** bytes (predicho en la nota: «unos 31.000») |
| Índice generado aparte | `docs/audits/INDICE.md`, 21.251 bytes, 139 filas |

Lo que cada ADR añade ahora a la vista, medido sobre las 43 decisiones que
declaran lección: su fila en la tabla de decisiones (**436** bytes de media
con resumen) y su lección (**214** de media, antes 342 con el enlace); su nota
de arranque y su evidencia en `docs/audits/` ya no añaden nada. Son **unos 650
bytes por ADR: unos 38 ADR de margen**, menos si el ADR trae skills,
investigaciones o documentos fuera de `docs/audits/`. Está por encima de los
20 ADR que el criterio de parada exigía, así que este ADR no inventa un tercer
corte.

**Y la fecha de caducidad, que el criterio de parada exige declarar.** Esto
compra ADR, no un techo. Septiembre produjo 91 ADR; a ese ritmo, 38 ADR son
unas dos semanas. Y hay un suelo que ningún corte de los que ADR-171 permite
toca: la fila del índice completo de decisiones, que ADR-196 protege, pesa
unos 240 bytes por ADR aunque no lleve resumen; a 91 ADR al mes, el índice
completo él solo crece unos 22.000 bytes al mes. Que la vista siga llevando
el índice completo con ese ritmo, o que lleve recuentos y punteros y el
detalle viva en vistas generadas aparte —«cambia lo que un lector encuentra al
entrar», ADR-196—, es una decisión de producto: va a la hoja de decisiones del
propietario como **D-6**, no se toma aquí.

## Comprobación que la sostiene

- `uv run --no-sync sirius-memoria conocimiento` escribe `MEMORIA.md` (94.931
  bytes) y `docs/audits/INDICE.md` (21.251 bytes); `--comprobar` recorre los dos.
- `uv run --no-sync pytest tests/engine/test_memoria.py`: 37 pasan, con tres
  pruebas nuevas:
  - `test_el_indice_de_auditorias_vive_generado_aparte_y_la_vista_lleva_recuento_y_puntero`:
    la misma fila ausente en la vista y presente en el índice, el recuento y
    el puntero en la vista, y el índice fuera de la lista de documentos.
  - `test_la_guardia_vigila_el_indice_de_auditorias_igual_que_la_vista`: el
    índice editado a mano o borrado hace hablar a la guardia nombrándolo.
  - `test_las_lecciones_nombran_el_adr_por_numero_y_no_repiten_la_ruta_que_la_tabla_enlaza`.
- El árbol de prueba gana dos auditorías (una con fecha y otra sin ella) y una
  lección en el ADR de la frontera: sin ellas, las tres reglas solo se medirían
  por un lado.
- **Tres mutaciones, las tres vistas caer** (cada una aplicada sobre el
  generador, la batería de `test_memoria.py` ejecutada y el fichero restaurado):

| | Mutación | Cae |
|---|---|---|
| M1 | las filas de `docs/audits/` de vuelta en la vista | `el_indice_de_auditorias_vive_generado_aparte…` y `la_memoria_confirmada_en_este_arbol_esta_al_dia` |
| M2 | la guardia deja de mirar el índice (solo comprueba la primera vista) | `la_guardia_vigila_el_indice_de_auditorias…` y `conocimiento_escribe_y_comprobar_distingue` |
| M3 | el enlace de vuelta en cada lección | `las_lecciones_nombran_el_adr_por_numero…` y `la_memoria_confirmada_en_este_arbol_esta_al_dia` |

- `scripts/automation/sirius_check_docs.py` sobre `docs/audits/INDICE.md`, la
  nota de arranque y este ADR: sin defectos.
- Batería entera (`uv run --no-sync pytest`): el resultado está en la PR #664.

## Consecuencias

- Quien entra sigue leyendo una sola vista; para la lista de auditorías abre el
  índice, a un clic, y lo encuentra con la misma forma.
- `sirius-memoria conocimiento` escribe dos ficheros; quien regenere la vista
  tiene que confirmar los dos. La guardia lo recuerda nombrando el que falte.
- La skill `cadena-de-comprobacion` no cambia: el comando es el mismo.

## Alternativas descartadas y por qué

Las de «Opciones consideradas». Y una más: **un índice por carpeta para todas
las carpetas** de `docs/`. Generaliza antes de tiempo: hoy solo `docs/audits/`
crece con cada ADR, y las demás suman 7.630 bytes juntas.

## La lección

- familia: `vista-que-copia-el-corpus-del-que-venia-huyendo`
- sin esto se repetiría: dejar que la única lectura lleve dos veces la misma ruta y la fila de cada pieza de evidencia, y descubrirlo cuando la guardia bloquea una PR que no tiene la culpa; es la segunda vez que muerde esta familia en 17 días, y el suelo que no se puede cortar está declarado arriba con su cifra.
- lo hace cumplir: `tests/engine/test_memoria.py`
