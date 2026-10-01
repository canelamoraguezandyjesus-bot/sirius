# Nota de arranque — la referencia de cierre de un defecto se puede seguir desde `main`

Rama `claude/la-referencia-de-cierre-se-sigue-desde-main`, fecha 01-10-2026 (la
hora es la del commit que la publica, y la lleva el ADR). Publicada **antes del
primer commit de arreglo**, como exige ADR-001.

## El suceso

La skill `registro-de-defectos` cierra un defecto con `cerrado_por: <sha de 40
caracteres del commit que lo arregló>`, en dos commits: el arreglo y, después,
la entrada con su sha. La convención presupone fusiones que conservan el commit.
El repositorio fusiona **aplastado** desde ADR-205 (20-09-2026), y antes las
ramas de sesión también entraban aplastadas: el sha que la entrada cita vive en
la rama de origen —que no se borra (ADR-195)— y **no es antepasado de `main`**.
Codex lo cazó en la PR #664 sobre H-217, y la mina de septiembre (PR #665,
rama `claude/mina-de-septiembre-entero`) lo midió con el guion que vive en esa
rama, `scripts/mina/cerrado_por_inalcanzable.py` (clon entero, `git cat-file -e` y
`git merge-base --is-ancestor` contra `origin/main`): **29 de 68** defectos
cerrados citan un commit que `main` no contiene —los 14 cerrados desde el
20-09, todos; 13 anteriores que viven solo en su rama; y 2 con un sha corto
(H-7, H-9)—. Quien clona `main` y abre el registro no puede llegar al arreglo.

Lo que sí se puede seguir desde `main`: **la PR** que lo fusionó (el aplastado
lleva «(#N)» en el título del commit de `main`) y, cuando lo hay, **el ADR**
(su fichero entra en `main` en ese mismo commit). La correspondencia de las 29
ya está medida con la API (`GET /commits/{sha}/pulls`): H-1 #222, H-2 #227,
H-4 #207, H-5 #221, H-6 #226, H-8 #235, H-10 #239, H-12 #245, H-14 #355,
H-18 #357, H-20 #354, H-23 #355, H-24 #377, H-204…H-211 #652, H-212 #654,
H-213 #658, H-214 #659, H-215 #661, H-217 y H-218 #664; H-7 y H-9 se buscan
por su sha corto.

## Las cuatro preguntas y la predicción

1. ¿Qué referencia se puede seguir desde un clon de `main` para todo defecto
   cerrado? Predicción: la PR, siempre (incluso para los 39 cuyo sha sí está en
   `main`, que entraron por fusión con commit de mezcla); el commit de `main`
   se deriva de ella con `git log --grep="(#N)" --first-parent`.
2. ¿Rompe esto el orden de dos commits? Predicción: no, lo alarga un paso: el
   número de la PR se conoce al abrirla, así que el segundo commit (la entrada)
   va después de abrir la PR, en la misma rama; para el motor, cuya PR la abre
   el workflow tras el run, la referencia es la incidencia del encargo, que ya
   es un campo del registro.
3. ¿Puede la guarda comprobarlo en Quality? Predicción: la forma sí (campo
   presente y entero); la existencia en la historia solo donde hay historia,
   porque Quality clona con profundidad 1 (`test_registro_de_defectos.py` ya lo
   dice de otra comprobación); donde no la hay, la guarda lo dice y no afirma.
4. ¿Cuánto cuesta? Predicción: un campo nuevo en 29 entradas (las medidas) y
   obligatorio desde la frontera de este ADR; la skill actualizada; un
   resolutor de línea de órdenes; sin tocar ningún workflow.

## Criterio de parada (antes de medir)

- **No se reescribe ningún `cerrado_por`**: el sha del arreglo sigue siendo
  dato (ADR-195: nada se borra); se añade la referencia que falta.
- La frontera es el número de este ADR, como hizo ADR-192 con el identificador:
  no se rellena de memoria lo que no se midió; las 29 medidas se rellenan con
  la correspondencia de la API, y se dice cuál se obtuvo por sha corto.
- Si la guarda necesitara red (consultar la API) para pasar, no se entrega: la
  batería no sale a la red.
- Tres mutaciones tienen que caer: M1 una entrada cerrada desde la frontera
  sin referencia seguible; M2 una referencia con la forma mal (`pr: "664"`
  como texto, o un número que no es entero); M3 el resolutor que, con historia
  disponible, devuelve un commit que no lleva «(#N)».
