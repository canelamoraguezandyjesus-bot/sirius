# Nota de arranque — el doble de `gh` acepta lo que el `gh` real rechaza

Rama `fix/el-doble-de-gh-rechaza-lo-que-el-real-rechaza`, 14-09-2026. Publicada
**antes del primer commit de arreglo**, como exige ADR-001.

**Cómo apareció, dicho sin adornos.** Este defecto no se buscaba. Se estaba
midiendo otro —por qué la incidencia #619 llevaba cinco horas en
`sirius:ci-pending`— y la medida devolvió una causa distinta de la que la nota
de arranque de aquel trabajo suponía. Así que aquella nota queda como está, para
su decisión, y esta se escribe entera para lo que la medida sí enseñó. Las
cuatro preguntas y el criterio de parada de abajo se fijan **antes de escribir
una sola línea de arreglo**; la medida que destapó el defecto ya estaba tomada y
se transcribe tal cual, sin recortarla para que encaje.

## El hecho

En el run 132 del reconciliador (14-09-2026, 04:56:13 UTC), leyendo la #619:

```
the `--slurp` option is not supported with `--jq` or `--template`
sirius_retry: fallo tras 4 intento(s): gh api -X GET repos/.../issues/619/events
  -f per_page=100 --paginate --slurp --jq (add // []) | ...
[AVISO] #619: ci-pending; no pude fechar el estado, así que no reparo a ciegas.
```

`gh api` **rechaza `--slurp` junto con `--jq`**. No es un fallo de red ni un
límite de cuota: es la validación de argumentos del propio `gh`, así que falla
siempre, en los cuatro intentos y en todas las pasadas.

`label_applied_at` es la única forma que tiene `sirius_reconcile.sh` de saber
cuándo se puso una etiqueta. Si no puede leerla, `stale_minutes` tampoco, y todo
lo que dependa de la antigüedad de un estado se cae al camino de fallo seguro:
«no pude fechar el estado, así que no reparo a ciegas». Que es lo correcto, y es
justamente por lo que nadie se ha enterado.

La invocación entró el **2026-08-10 a las 17:04 UTC** (commit `f95b8d08`,
«Corregir tres defectos de la revisión de Codex»), y sigue ahí hoy palabra por
palabra.

## Lo que lo convierte en un defecto de método y no en una errata

Dos líneas más arriba, en la misma función, hay escrito esto:

> `-X GET` es OBLIGATORIO… sin esto TODA lectura fallaba, `marca` salía vacía y
> la rama de fallo seguro impedía publicar un solo aviso. **La detección entera
> habría estado muerta en producción sin que ninguna prueba lo notara.**

Es el mismo fallo, en la misma función, por la misma razón, y el aviso ya estaba
escrito ahí. La corrección de P2 —añadir `--slurp`— volvió a matar la detección
exactamente como P1, y el doble de `gh` de las pruebas lo dio por bueno las dos
veces. Dos rondas de la misma familia: ADR-001 manda parar de parchear y buscar
la raíz.

**La raíz no es `--slurp`.** Es que el doble de `gh` de
`tests/automation/test_sirius_reconcile.py` modela lo que `gh` *hace* —cómo
pagina, qué devuelve— pero no lo que `gh` *rechaza*. Un doble más permisivo que
el real convierte a la suite en una comprobación de que el código le gusta al
doble.

## 1. ¿Dónde vive el fallo y dónde va el arreglo?

El fallo vive en **el contrato con una herramienta externa**, que es justo lo que
ningún doble reproduce si no se le pide. Por eso el arreglo tiene dos mitades y
ninguna vale sola:

- La llamada, en `scripts/automation/sirius_reconcile.sh`. Y no hay que inventar
  la forma correcta: está escrita en esta misma casa, en `sirius_issue.sh`, que
  dice literalmente que **no** usa `--slurp` y por qué —con `--paginate --jq` el
  filtro se aplica por página y las salidas se concatenan en orden—. El
  reconciliador se salió de esa regla y se rompió.
- El doble, en `tests/automation/test_sirius_reconcile.py`, que pasa a rechazar
  lo que el `gh` real rechaza. Esa es la mitad que hace que no vuelva a pasar:
  cualquier llamada futura que combine `--slurp` con `--jq` rompe la suite.

*¿Puede el sitio del arreglo observar el fallo que arregla?* Sí, y es lo que hoy
no pasa: el doble tiene delante los argumentos completos y no los valida.

## 2. ¿Qué NO va a garantizar esto?

- **No garantiza que el doble sea fiel en todo lo demás.** Fija UNA regla
  documentada de `gh` que ya nos ha costado dos rondas. Otras incompatibilidades
  de argumentos seguirán sin estar modeladas, y eso se dice aquí.
- **No arregla el otro defecto de la #619.** Con la fecha ya legible, una
  incidencia en `ci-pending` cuya PR está en conflicto sigue sin recibir aviso,
  porque el camino del aviso exige que Quality haya concluido y ahí no concluye
  nunca. Es trabajo aparte, con su propia nota ya escrita.
- **No recupera lo que no se avisó** en estos 35 días. No hay nada que recuperar:
  el reconciliador no guarda lo que no dijo.
- **No cambia ninguna transición.** Solo vuelve a hacer legible un dato que se
  leía mal.

## 3. Criterio de parada, decidido ANTES de escribir el arreglo

- **Si el arreglo no se puede ver fallar, no vale.** Tiene que existir una
  prueba que, con el código de hoy, esté ROJA por la razón exacta —el `gh`
  rechaza la combinación— y no por cualquier otra.
- **La propiedad de P2 tiene que sobrevivir.** Lo que `--slurp` venía a
  garantizar —que la fecha y el id salgan del MISMO suceso, aunque los sucesos
  vengan repartidos en varias páginas— sigue siendo obligatorio. Si el arreglo
  lo pierde, es un cambio de un defecto por otro y se tira.
- **El arreglo no puede depender de las opciones del shell del llamador.**
  Lectura y transformación van separadas, como ya exige `sirius_issue.sh`: en
  una tubería el estado de salida sería el de `jq` y un 503 se convertiría en
  «no hay sucesos».
- **Fallo cerrado.** Si la lectura falla de verdad, se sigue sin afirmar
  antigüedad. Esa parte está bien y no se toca.
- **No debilita nada.** Las demás pruebas de `sirius_reconcile.sh` pasan sin
  retocarse. Las que haya que tocar son las que afirmaban la forma rota, y cada
  una se dice por su nombre.
- **Cada regla nueva trae una mutación sembrada y vista caer.**

## 4. ¿Qué haría el fallo imposible en vez de improbable?

**Que el doble no pueda ser más permisivo que el real.** Mientras el doble sea
un guion escrito a mano, puede aceptar cualquier cosa; lo que sí se puede hacer
—y es lo que se hace— es que las reglas de la herramienta que ya nos han costado
una ronda queden ESCRITAS EN EL DOBLE, de modo que romperlas rompa la suite.
Cada regla así deja de depender de que alguien se acuerde.

Lo que lo haría imposible del todo sería no tener doble: ejercitar estas
lecturas contra un `gh` real en un repositorio de juguete. Es mucho más caro, es
otra decisión, y queda declarado aquí sin hacerse.

Y hay una tercera vía, más barata que la segunda y más fuerte que la primera,
que este trabajo deja anotada y no toma: que las llamadas a `gh` no se escriban
sueltas por el guion, sino a través de una función única que valide sus propios
argumentos. Eso convierte «acordarse de la regla» en «no poder saltársela», que
es la forma de ADR-174. No se hace ahora porque tocaría todas las llamadas del
guion a la vez, y eso es una PR entera aparte.

## La medida (tomada antes de escribir esta nota, transcrita sin recortar)

| | |
|---|---|
| Momento del fallo observado | 14-09-2026 04:56:13 UTC, run 132 del reconciliador |
| Mensaje | `the --slurp option is not supported with --jq or --template` |
| Intentos gastados | 4 (los que `sirius_retry` concede), todos con el mismo fallo |
| Invocación introducida | 2026-08-10 17:04 UTC, `f95b8d08` |
| Días en producción sin poder fechar una sola etiqueta | **35** |
| Llamadas afectadas | 1 (`label_applied_at`), y por ella `stale_minutes` |
| Sitios del guion que dependen de la fecha | 3 (líneas 284, 399 y 472) |
| Otras llamadas con `--slurp` en el repositorio | ninguna |
