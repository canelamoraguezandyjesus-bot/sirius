# ADR-035 — El revisor no juzga con el intérprete del runner, y toda parada tiene vuelta

- Estado: APROBADO
- Fecha: 2026-08-18
- Aprobación: fusión de la PR #198 por el propietario
- Contexto: incidencia #193 (A3), PR #194, ronda 4
- Relacionadas: ADR-001 (disciplina de evidencia), ADR-030 (una parada se
  levanta con una orden), ADR-033 (una regla que enumera vehículos siempre
  tiene un hueco más)

## Contexto y problema

La ronda 4 de #193 terminó en `sirius:failed-safely` con **Quality en verde**
sobre `e90e984a` y sin ningún defecto real en el trabajo. Reconstruido el
[run 32183288737](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/32183288737),
pasaron tres cosas distintas, y solo dos son nuestras.

### 1. Codex no contestó (no es nuestro)

`sirius_codex_review: resultado FAILED_SAFELY (timeout)` — 1200 s de plazo
absoluto agotados entre las 20:40:08 y las 20:57:51. La agregación se negó a
aprobar en silencio y produjo `FAILED_SAFELY`. **Ese comportamiento es
correcto y no se toca**: aprobar por silencio es peor que parar.

### 2. El revisor juzgó con un intérprete que no es el del proyecto

Claude publicó `CLAUDE-A3-001` como bloqueante: «`SyntaxError` en
`context_recall.py`; el módulo no se puede importar; pytest no pudo haber
pasado en verde». Era falso. `except UnicodeDecodeError, OSError:` es válido
desde Python 3.14 (PEP 758), y el proyecto fija `requires-python = ">=3.14,<3.15"`
con `target-version = "py314"`:

```
$ uv run --python 3.14 --no-project python -c "import ast; ast.parse(...)"
interprete real: 3.14.6
RESULTADO: compila SIN ERROR bajo el interprete del proyecto
```

Lo publicó **dos veces**, en las rondas 2 y 4. La segunda vez, «verificado por
dos vías independientes» que eran el mismo intérprete equivocado.

La causa no es el modelo: es que `review-sirius-work.yml` **no instala `uv` ni
sincroniza el proyecto**, a diferencia de `implement-sirius-work.yml` y
`repair-sirius-work.yml`, y `reviewer.md` **no lo decía**. Ni lo prometía ni lo
desmentía. Era el único de los tres prompts sin una sola mención al intérprete.

`tests/automation/test_prompts_de_rol.py` ya cubría una dirección —«si el
prompt promete un entorno, el workflow debe montarlo»— desde la #182. Faltaba
la contraria. El silencio también engaña.

### 3. `sirius:failed-safely` no tenía vuelta

ADR-030 dio una orden de vuelta a `sirius:blocked-decision` y dejó fuera
`sirius:failed-safely` con esta razón escrita en la prueba:

> «su salida está documentada y probada en `sirius_validate_activation.sh`
> (línea 46), y consiste en retirar la etiqueta tras leer el diagnóstico»

**Esa razón era falsa por dos vías independientes.** La línea 46 habla de
reactivar el trabajo **desde cero** con `sirius:implement-requested`, no de
retomar la ronda interrumpida; y **ningún workflow escucha `unlabeled`**, así
que retirar la etiqueta no dispara nada. Una parada segura sobre una PR con
Quality en verde, 5 commits y 3 rondas de trabajo no tenía más salida que la
cirugía manual — exactamente lo que ADR-030 vino a eliminar.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la incidencia #193 **antes de tocar nada**
([comentario 5334002579](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/193#issuecomment-5334002579)),
con las cuatro preguntas y esto:

> Paro cuando se cumplan las tres: el revisor **no pueda** volver a comprobar
> sintaxis con un intérprete que no es el del proyecto, y haya una prueba que lo
> sostenga; **toda** etiqueta de parada declare la orden que la levanta, con una
> prueba escrita como propiedad y no como lista; A3 vuelva a estar en revisión
> sobre `e90e984a`.
>
> Si aparece una **tercera** familia distinta, la registro y **no** la arreglo
> en este lote.

Las tres se cumplieron. Y apareció la tercera familia, que se registró sin
arreglar (ver más abajo) — el criterio hizo su trabajo justo donde incomodaba.

## Opciones consideradas

**Para el intérprete del revisor:**

1. Instalar `uv` y sincronizar el proyecto en `review-sirius-work.yml`, como
   hacen los workflows del implementador y del corrector.
2. Decírselo al prompt como propiedad: este runner no tiene el intérprete del
   proyecto, así que ejecutar código aquí no afirma nada sobre el proyecto.

**Para la parada sin vuelta:**

1. Devolver todo `failed-safely` a una etiqueta fija.
2. Leer del historial el rol que se detuvo y reponer su disparador.

## Decisión

### El prompt del revisor enuncia una propiedad, no una lista

> Lo que averigües *ejecutando* código en este runner es una afirmación **sobre
> este runner**, no sobre el proyecto. Da igual con qué lo ejecutes.

Y con ella la consecuencia que ahorra rondas: Quality ya ejecutó las cuatro
validaciones con el intérprete real, así que **todo hallazgo de la forma «esto
no compila / no importa / mypy lo rechazaría / esta prueba falla» está refutado
antes de escribirse**. Se dice también lo que Quality **no** cubre, para no
frenar al revisor donde sí es imprescindible.

Es propiedad y no enumeración por ADR-033: prohibir `python3` habría dejado
fuera `python`, `py`, `compileall`, `ast` y los que vengan.

### Toda parada que espera a una persona declara quién la levanta

`sirius_resume_on_command.sh` acepta ahora `sirius:failed-safely` además de
`sirius:blocked-decision`, y **reanuda la fase que se detuvo**, leyéndola del
rol que el marcador del veredicto ya publica. Reanudar es reponer el evento que
la parada consumió, no elegir una etiqueta fija: un `failed-safely` del revisor
que volviera a `repair-requested` «corregiría» observaciones que nadie escribió.

Las dos paradas **no** publican el mismo marcador. `sirius-convergence-reset`
mueve el listón del progreso y solo vale para `blocked-decision`, que es una
parada *por* falta de progreso; publicarlo en una parada operativa borraría el
listón sin que nadie lo pidiera, y un ciclo de verdad estancado podría correr
para siempre.

### La prueba deja de enumerar y pasa a deducir

Las paradas salen ahora de `INCOMPATIBLE_STATES` —la enumeración real que
mantiene la automatización viva— restándole, por su forma, lo que no puede
estar esperando a nadie: los `*-requested` son eventos, las fases en curso
tienen un job corriendo, `completed` es el final. Una parada nueva entra sola
en la prueba y tendrá que traer su orden.

## Comprobación que la sostiene

### Dos pruebas mías que no mordían

La prueba por mutación (ADR-001 §3) encontró que **mi propia prueba estática
pasaba en verde con el defecto sembrado, dos veces seguidas**:

| Mutación | Primera versión | Por qué pasaba |
| --- | --- | --- |
| Sacar `sirius:failed-safely` del conjunto de paradas | ✅ pasó | El nombre seguía en un comentario de cabecera |
| La misma, filtrando ya los comentarios | ✅ pasó | El nombre seguía dentro de un mensaje de error |
| Tratar una lectura caída como historial vacío | ✅ pasó | La prueba solo miraba el código de salida, y el camino equivocado también acaba en `!=0` |

Una comprobación que se conforma con que algo se **mencione** certifica
documentación, no comportamiento. De ahí sale
`tests/automation/test_reanudar_ejecutando_el_guion.py`: ejecuta el guion
contra un `gh` simulado y mira qué etiquetas quedan puestas. Con él, las tres
mutaciones caen.

Mutaciones sembradas y verificadas: quitar la propiedad del prompt del revisor,
sacar `failed-safely` del conjunto, publicar `sirius-convergence-reset` en una
parada operativa, devolver un `failed-safely` del revisor a `repair-requested`,
y tratar un historial ilegible como vacío. Las cinco cayeron.

## Lo que se registra SIN arreglar

La nota de arranque de #193 fijó el criterio antes de mirar: *«si aparece una
tercera familia distinta, la registro y no la arreglo en este lote»*. Apareció.

**`sirius_find_pr_for_issue` traga los fallos de lectura.** Sus lecturas llevan
`2>/dev/null || :`, así que un historial ilegible sale como «no hay PR», y el
propietario recibe «No he encontrado ninguna PR asociada a esta incidencia» —
falso: la PR está ahí, lo que falló fue la lectura. Es la familia que este
repositorio lleva un año corrigiendo, y la comparten **todos** los ejecutores de
órdenes, incluido `sirius_merge_on_command.sh`.

No se arregla aquí porque tocar esa función es un cambio de otro alcance y el
lote de hoy ya cierra dos familias. Queda escrito como prueba, no como prosa:
`test_el_diagnostico_de_una_lectura_caida_no_debe_afirmar_que_no_hay_pr`, con
`xfail(strict=True)`. Cuando alguien lo arregle, la prueba pasará y el `strict`
obligará a retirar el marcador — no se puede olvidar en silencio.

## Alternativas descartadas y por qué

**Instalar `uv` en el workflow del revisor.** Habría hecho verdadero lo que el
revisor suponía, en vez de corregir el razonamiento. Tres motivos: obliga a
tocar `.github/**`, que el propietario pega a mano (ADR-002); gasta minutos de
Actions en cada ronda de revisión; y contradice la postura del propio prompt de
no reconstruir el entorno de CI. Además no arregla el error de fondo — el
revisor seguiría pudiendo concluir cosas del proyecto ejecutando cosas del
runner.

**Enumerar las herramientas vetadas** («no uses `python3`»). Descartada por
ADR-033: prohibir `python3` deja fuera `python`, `py`, `compileall`, `ast` y las
que vengan. La propiedad cubre todas sin nombrar ninguna.

**Devolver todo `failed-safely` a `repair-requested`.** Es lo que hace ADR-030
para `blocked-decision`, y aquí sería incorrecto: una revisión caída se
«reanudaría» corrigiendo observaciones que nadie escribió.

## Consecuencias

- El revisor deja de gastar rondas en hallazgos que Quality ya refutó, y la
  regla no depende de acordarse de vetar la herramienta de turno.
- Una parada segura, venga del rol que venga, se levanta con `continua`.
- Una parada nueva no puede nacer sin salida: la prueba la deduce.
- Sigue habiendo un hueco conocido, y está numerado.
