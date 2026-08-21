# ADR-051 — El cuerpo de una incidencia pasa por el mismo filtro de confianza que sus comentarios

- Estado: PROPUESTO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR por el propietario.

## Contexto y problema

Defecto **H-1** del parte `docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md`,
incidencia **#215**. Vivo en `main` desde el bloque A3.

`_texto_cronologico_de_confianza` (`src/sirius_engine/mirror_projection.py`)
filtraba los comentarios por autor de confianza y a continuación concatenaba
el cuerpo **sin filtrar**:

```python
de_confianza = [c.cuerpo for c in comentarios if es_autor_de_confianza(c)]
return "\n".join((*de_confianza, cuerpo))
```

Ese texto es el que alimenta `sirius_convergence.parse_round_records`,
`ci_failure_streak` y `history_after_last_resume`: gobierna **la numeración de
rondas y el corte por fallos de CI** del ciclo revisar-reparar.

Y no se podía arreglar dentro de la propia función. Es la pregunta que caza la
raíz en ADR-001 §1 —*¿puede el sitio del arreglo observar el fallo que
arregla?*—, y la respuesta era **no**: `LecturaCuerpo`
(`src/sirius_engine/ports/github_mirror.py`) transportaba `estado`, `cuerpo` y
`error`, y **ningún campo de autor**. La función no filtraba el cuerpo porque
no tenía con qué. El fallo estaba en el puerto; en la proyección solo se veía
el síntoma.

Al reproducirlo apareció **un segundo defecto en la misma función**: su
docstring promete «del más antiguo al más reciente» y ponía el cuerpo —lo
primero que existe en una incidencia— **al final** de la concatenación.

### Alcance real, comprobado

Nada de la automatización escribe el cuerpo de una incidencia: `grep` sobre
`scripts/automation/` y `.github/workflows/` solo devuelve
`issue edit --add-label/--remove-label` e `issue comment`. Lo escribe el
propietario. **El vector es acotado.** Lo que no es acotado es que el nombre de
la función prometiera una propiedad que la función no tenía: quien lea
`_texto_cronologico_de_confianza` y confíe en su nombre está confiando en algo
falso, y esa confianza se propaga a cada consumidor nuevo del espejo.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la incidencia #215 antes del primer commit
([comentario](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/215#issuecomment-5366056991)).
Entrego cuando se cumplan las cuatro:

1. Existe una prueba que, con el código de hoy, **falla** demostrando que el
   mismo texto de ronda se filtra en un comentario y no en el cuerpo, y que
   con el arreglo pasa.
2. La mutación —deshacer el arreglo— **tumba** esa prueba. Si no la tumba, la
   prueba no vale y se rehace.
3. La proyección de la #186 (fixture real, 41 comentarios) sale **igual** que
   antes: el arreglo no puede cambiar el espejo de una incidencia legítima.
4. `ruff format --check`, `ruff check`, `mypy src tests` y las pruebas **de
   los ficheros tocados** en verde.

Y paro sin parchear si aparecen dos rondas seguidas de defectos de la misma
familia (ADR-001 §2).

## Opciones consideradas

**(a) El puerto transporta el autor del cuerpo y la función filtra de verdad.**
Toca `ports/github_mirror.py`, los dos adapters y los llamadores.

**(b) La función deja de llamarse «de confianza» y el llamador sabe qué
recibe.** Tres líneas: renombrar a `_texto_cronologico` y documentar que el
cuerpo va sin filtrar porque lo escribe el propietario.

**(a′) Como (a), pero con los campos de autor opcionales en `LecturaCuerpo`**
(`autor_login: str | None = None`), para no tocar los ~15 puntos de
construcción existentes.

## Decisión

**(a)**, y con el autor del cuerpo como **objeto de valor obligatorio**, no
como campos opcionales.

Se añade al puerto `CuerpoIncidencia(autor_login, autor_asociacion, texto)`,
hermano de `Comentario`, y `LecturaCuerpo.cuerpo` pasa de `str | None` a
`CuerpoIncidencia | None`. `es_autor_de_confianza` pasa a aceptar cualquier
`ContenidoConAutor` —un protocolo de solo lectura que satisfacen los dos
dataclasses congelados—, de modo que cuerpo y comentario cruzan **el mismo**
predicado y no dos parecidos. Y el cuerpo se concatena **primero**, que es
donde le toca por antigüedad.

Tres razones para (a) sobre (b):

1. (b) deja el agujero abierto y documentado. Hoy el vector es acotado *porque
   nadie más abre incidencias que Sirius lea* — eso es una propiedad del
   entorno, no del código, y no la sostiene ninguna prueba. (a) responde a la
   cuarta pregunta de la nota de arranque: convierte «improbable» en
   «imposible por construcción».
2. (a) deja **un solo predicado de confianza** aplicado uniformemente. Con (b)
   el sistema tendría dos reglas distintas según de dónde venga el texto, y esa
   asimetría hay que recordarla en cada consumidor futuro del espejo.
3. El coste real de (a) resultó ser menor de lo que aparenta: `user.login` y
   `author_association` **ya viajan en la misma respuesta** que `.body`, así
   que transportarlos no cuesta ninguna llamada de red adicional, solo dos
   campos más en el `--jq`.

Y la razón para el objeto de valor sobre (a′): un campo de autor opcional
**reintroduce el defecto en silencio**. Por omisión el cuerpo saldría «no de
confianza» y desaparecería del historial sin que nadie lo notara —cambiando la
numeración de rondas— en cualquier punto de construcción que se olvidara de
rellenarlo. Con los tres campos obligatorios, un cuerpo sin autor **no se puede
construir**, y eso lo comprueba `mypy` en cada llamada, no una excepción en
producción.

### El segundo hallazgo va en el mismo cambio

El orden se arregla aquí y no en una incidencia aparte. Es la misma línea de
código y la misma familia de defecto —una función que promete lo que no hace—,
y arreglar la mitad de la ficción sería exactamente el parcheo que ADR-001 §2
prohíbe.

No se notaba en la numeración de rondas porque `parse_round_records` ordena
internamente por número de marcador (`records.sort(key=...)`). Sí se nota en
`history_after_last_resume`, que **corta** el texto por la última orden de
continuar: con el cuerpo al final, un `sirius-convergence-reset` escrito en el
cuerpo se leía como posterior a todos los comentarios y **borraba el historial
entero**.

## Comprobación que la sostiene

### 1. El defecto, reproducido antes de tocar nada

Mismo texto de ronda, mismo autor sin autoridad, dos sitios distintos
(`uv run python` sobre `main`):

```
A) comentario de un tercero con ronda 9:
   rondas = [1]   <- el filtro SI actua
B) el MISMO texto, puesto en el cuerpo en vez de en un comentario:
   rondas = [1, 9]   <- el filtro NO actua
C) racha de fallos de Quality desde el cuerpo:
   racha = 2
D) orden: el cuerpo (lo mas antiguo) se concatena AL FINAL
   primera linea = '<!-- sirius-round:1 -->'  ultima = 'CUERPO'
E) por eso una reanudacion en el cuerpo borra todos los comentarios:
   rondas tras el corte = []
```

### 2. Las pruebas, vistas fallar antes del arreglo

Con el puerto ya extendido pero la proyección todavía sin filtrar —que es el
estado en que el defecto se puede *expresar* por primera vez:

```
$ uv run pytest tests/engine/test_mirror_projection.py -q -k "..."

>       assert desde_cuerpo.rondas == (), "el cuerpo de un tercero fabricó una ronda en el espejo"
E       AssertionError: el cuerpo de un tercero fabricó una ronda en el espejo
E       assert (RondaHallazg...dad_total=0),) == ()
E         Left contains one more item: RondaHallazgos(numero=99, head='deadbeef', pendientes=0, gravedad_total=0)

>       assert mirrored.fallos_quality_consecutivos == 0
E       AssertionError: assert 2 == 0

>       assert [r.numero for r in mirrored.rondas] == [99], (
            "una reanudación escrita en el cuerpo borró rondas publicadas DESPUÉS"
        )
E       AssertionError: una reanudación escrita en el cuerpo borró rondas publicadas DESPUÉS
E       assert [] == [99]

3 failed, 1 passed, 17 deselected in 0.11s
```

La cuarta (`test_el_cuerpo_del_propietario_si_cuenta_como_de_confianza`) pasa ya
antes del arreglo: es la guarda contra la sobrecorrección, no contra el defecto.

### 3. Prueba por mutación

| # | Mutación sembrada | ¿Cae? | Qué cae |
|---|---|---|---|
| M1 | Quitar el filtro del cuerpo (el defecto H-1 original) | **SÍ** | `test_el_mismo_texto_de_ronda_se_filtra_igual_venga_del_cuerpo_o_de_un_comentario`, `test_el_cuerpo_de_un_tercero_tampoco_gobierna_la_racha_de_fallos_de_quality` |
| M2 | Devolver el cuerpo al final de la concatenación | **SÍ** | `test_el_cuerpo_se_concatena_primero_por_ser_lo_mas_antiguo` |
| M3 | Sobrecorregir: descartar el cuerpo SIEMPRE | **SÍ** | `test_el_cuerpo_del_propietario_si_cuenta_como_de_confianza` |
| M4 | El `--jq` deja de pedir el autor del cuerpo | **SÍ** (al segundo intento) | `test_leer_cuerpo_ok_transporta_el_autor_y_conserva_los_saltos_de_linea` |

**M4 no cayó la primera vez, y eso enseñó algo.** La prueba del adapter
sustituye `ejecutar` por un doble que devuelve una salida fija **pase lo que
pase en el `--jq`**: mutar la consulta era invisible mirando solo el valor
devuelto. La prueba afirmaba más de lo que comprobaba. Se corrigió fijando lo
que el adapter **sí** controla —el `argv` que construye—, no inventando un
aserto que tapara el hueco.

**Límite que queda escrito** (mismo espíritu que el `kill -9` de ADR-026):
ninguna prueba de este repositorio ejecuta `gh` ni `jq` (requisito 7 del bloque
A3), así que **nada de aquí demuestra que la salida real de ese `--jq` tenga la
forma que `json.loads` espera**. Eso solo lo enseña la API real. Lo que sí queda
fijado es que el adapter pide el autor, y que lo pide en la misma llamada.

### 4. La #186 real no cambia (criterio de parada 3)

Proyección de la incidencia #186 (fixture capturada de la API real, 41
comentarios) calculada con la concatenación nueva y con la vieja:

```
longitud del repr: 5676
IDENTICOS: True
mismo conjunto de caracteres: True
el texto SI cambia de orden (cuerpo movido al frente): True
empieza por el cuerpo: True
```

El texto concatenado **sí** cambia; el espejo resultante **no**. El autor del
cuerpo de la #186 se verificó contra la API real
(`repos/canelamoraguezandyjesus-bot/sirius/issues/186` →
`user.login = canelamoraguezandyjesus-bot`, `author_association = OWNER`) y se
añadió a la fixture; por eso el cuerpo sigue siendo de confianza y sigue
contando.

## Consecuencias

- `LecturaCuerpo.cuerpo` cambia de tipo. Es un cambio incompatible del puerto,
  y a propósito: obliga a `mypy` a señalar cada punto de construcción en vez de
  dejar que uno se quede con un autor vacío.
- Un cuerpo que no supera el filtro se descarta **en silencio**, igual que ya
  se descartaba un comentario ajeno. La uniformidad es la decisión; si algún
  día hace falta observarlo, es un campo nuevo en `MirroredWorkItem` y otra
  decisión.
- El filtro sigue siendo por **identidad, no por contenido**: un autor de
  confianza que publique una ronda equivocada la sigue publicando.
- `es_autor_de_confianza` sigue siendo el mismo predicado booleano que
  `SIRIUS_TRUSTED_AUTHOR_JQ` en `sirius_issue.sh`. Este cambio amplía **a qué
  se aplica**, no **qué decide**: no hay divergencia nueva con bash.
- No se tocó `scripts/automation/**` ni `.github/**`.

### Un defecto de la misma familia que NO se arregla aquí, y por qué

`context_recall.buscar_en_incidencias`
(`src/sirius_engine/context_recall.py`) tiene la misma asimetría: filtra los
comentarios con `es_autor_de_confianza` y busca en el cuerpo sin filtrar.
**Se deja como está, deliberadamente.** No es el mismo defecto con otro
disfraz: ahí el texto no gobierna nada del ciclo —produce `Referencia`s para
recuperar contexto—, y filtrar el cuerpo de un tercero significaría **perder
contexto legítimo**, que es lo contrario de lo que ese proveedor existe para
hacer. Cambiarlo es una decisión de producto sobre qué cuenta como contexto,
no la corrección de una promesa falsa, y no le corresponde a esta rama
tomarla. Queda anotado aquí para que se encuentre.

## Alternativas descartadas y por qué

- **(b) Renombrar la función y documentar el hueco.** Tres líneas, y deja la
  frase honesta. Descartada porque deja la propiedad dependiendo del entorno
  («hoy nadie más escribe cuerpos») en vez del código, y porque obliga a
  recordar dos reglas de confianza distintas en cada consumidor futuro. Cuesta
  menos hoy y más después, que es justo el reparto que ADR-001 intenta evitar.
- **(a′) Campos de autor opcionales en `LecturaCuerpo`.** Evita tocar los ~15
  puntos de construcción, y a cambio reintroduce el defecto en silencio en
  cualquiera que se olvide de rellenarlos. Un fallo silencioso que cambia la
  numeración de rondas es peor que el que veníamos a arreglar.
- **Validar el autor en `__post_init__` en vez de con el tipo.** Ruidoso en el
  momento correcto, pero es una excepción en producción donde puede haber un
  error de compilación. Se prefirió lo que `mypy` puede ver.
- **Avisar al llamador de que se descartó un cuerpo ajeno** (campo nuevo en
  `MirroredWorkItem`, al estilo de `etiquetas_contradictorias`). Descartada por
  alcance: hoy los comentarios ajenos se descartan en silencio y la uniformidad
  vale más que el aviso. Si aparece un caso real que lo pida, es su propia
  decisión.
