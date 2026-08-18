# ADR-036 — Una lectura caída no es una ausencia, y el llamador tiene que poder distinguirlas

- **Estado**: aceptada
- **Fecha**: 2026-08-18
- **Contexto**: incidencia #193, la parada de la ronda 4
- **Relacionadas**: ADR-030 (una parada se levanta con una orden), ADR-035 (que
  lo registró sin arreglarlo)

## Contexto

ADR-035 dejó este defecto escrito y sin arreglar, con una prueba `xfail`, porque
el criterio de parada de aquel lote lo decía. Este ADR lo cierra.

`sirius_find_pr_for_issue` es la función que localiza la PR de una incidencia.
La usan los **tres** ejecutores del ciclo: el que fusiona por orden, el que
reanuda por orden y el que aplica veredictos. Sus tres lecturas llevaban
`2>/dev/null || :` y la función devolvía `0` siempre:

```bash
sirius_read_issue_body "$repo" "$num" >"$body_file" 2>/dev/null || : >"$body_file"
sirius_read_issue_comments "$repo" "$num" >"$comments_file" 2>/dev/null || : >"$comments_file"
...
pr_json="$(sirius_retry _sirius_gh api "repos/${repo}/pulls/${pr}" 2>/dev/null || true)"
```

Un 503 salía por el mismo sitio que una incidencia sin PR: vacío y éxito. Y los
tres llamadores usaban `mapfile -t pr_numbers < <(...)`, que además **descarta
el código de salida** aunque lo hubiera.

El resultado, comprobado ejecutando el guion contra un `gh` que devuelve 503:

> 🛑 **No he podido reanudar el ciclo**
> No he encontrado ninguna PR asociada a esta incidencia, así que no puedo saber
> sobre qué head autorizas continuar.

Es **falso**. La PR estaba abierta. Lo que falló fue la lectura. Y el
propietario lo recibe como diagnóstico, con instrucciones de actuar.

La diferencia no es cosmética: **una lectura caída es reintentable y no pide
nada de nadie; una PR de verdad ausente sí**. Decir la segunda cuando pasó la
primera manda a una persona a buscar un problema que no existe — y esto ocurrió
el mismo día en que GitHub estuvo degradado durante horas.

## Decisión

### El código de salida es la mitad del contrato

```
0 — se pudo leer. Cero líneas significa «leí y no hay ninguna»: es un HECHO.
2 — NO se pudo leer. No imprime nada, y ese vacío no significa nada.
```

Las tres lecturas dejan de tragarse el fallo, incluida la del estado de cada
candidata: **una PR ilegible no es una PR cerrada**. Antes se omitía en
silencio, así que una incidencia con una sola PR y un fallo puntual al leerla
salía como «ninguna PR» — el mismo error, un nivel más abajo.

### Los tres llamadores dejan de perder ese código

`mapfile -t x < <(f)` descarta el estado de `f`. Los tres pasan a capturar la
salida en un fichero y comprobar el código antes de interpretarla:

- **reanudar** y **fusionar**: `::error::` con «Reintentable» y salida ≠ 0, **sin
  publicar comentario**. Publicar un diagnóstico exige haber leído algo.
- **aplicar veredicto**: motivo `historial-ilegible`, distinto de `sin-pr`. El
  primero describe lo que pasó; el segundo era una afirmación sobre la
  incidencia que además la mandaba a parada segura con un diagnóstico falso.

## Prueba por mutación (ADR-001 §3)

Cuatro mutaciones sembradas, vistas fallar y revertidas:

| Mutación | Qué cayó |
| --- | --- |
| Volver a tragarse el fallo del cuerpo | `test_find_pr_devuelve_2_si_no_puede_leer_el_cuerpo` |
| Volver a tragarse el fallo de los comentarios | esa prueba **y** la del guion de reanudación |
| Volver a descartar en silencio una PR ilegible | `test_find_pr_devuelve_2_si_no_puede_leer_el_estado_de_una_candidata` |
| Devolver `2` **siempre** (arreglo falso) | 16 pruebas |

La cuarta es la que importa más: sin ella, «devolver 2 y ya» habría pasado por
arreglo, matando el único caso en que el llamador puede concluir algo. Por eso
hay una prueba dedicada a que un `0` con salida vacía **sí** es una afirmación.

Y en el guion de fusión —el que se usa esta misma noche— revertir su sitio de
llamada al `mapfile < <(...)` hace caer
`test_una_lectura_caida_no_se_publica_como_ausencia_de_pr`.

## Lo que apareció al arreglarlo

La guardia nueva salta **antes** que la de numeración de ronda, y eso dejó sin
medir a esta última: `test_changes_requested_stops_safely_when_the_history_is_unreadable`
tumbaba las lecturas desde la primera, así que ahora paraba en la guardia
anterior y nunca llegaba a la que quería aislar. Las dos guardias son correctas
y las dos hacen falta.

El simulador de `gh` pasa a poder fallar **a partir de la lectura n+1**, lo que
no es un artificio para esquivar la guardia: localizar la PR y numerar la ronda
son llamadas distintas a la API, y una puede caer sin la otra. Al hacerlo
apareció un segundo defecto, esta vez del propio simulador: el respaldo GraphQL
no estaba cubierto por la palanca, así que rescataba la lectura y el guion
seguía como si nada — la prueba habría pasado sin simular nada. Ahora las dos
vías caen con la misma lectura lógica.

## Consecuencias

- Ningún ejecutor de órdenes puede volver a publicar «no hay PR» cuando lo que
  hubo fue un fallo de lectura.
- Con GitHub degradado, las órdenes del propietario fallan **diciendo que se
  pueden reintentar**, en vez de inventar un estado del repositorio.
- Se retira el `xfail(strict=True)` de ADR-035. El `strict` cumplió su función:
  la prueba pasó en cuanto el defecto se arregló, y no se pudo olvidar.
