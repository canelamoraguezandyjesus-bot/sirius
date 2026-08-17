# ADR-027 — Las etiquetas se leen del objeto de la incidencia, nunca del endpoint `/issues/{n}/labels`

- Estado: PROPUESTO — **revisado parcialmente el mismo día por
  [ADR-028](ADR-028-una-averia-transitoria-no-justifica-una-invariante-permanente.md): los
  puntos 2 y 3 de la decisión (la prohibición del endpoint y su prueba) quedan retirados; los
  puntos 1 y 4 siguen en pie.**
- Fecha: 2026-08-17
- Aprobación: la fusión de la PR de esta rama por el propietario.

## Contexto y problema

El bloque A2 (incidencia #186) no arrancó **cuatro veces seguidas** a lo largo de más de una
hora. Las cuatro con el mismo síntoma en el log: `unexpected end of JSON input`.

El log dice exactamente dónde. Contando las apariciones del error en una ejecución hay
**cinco**: cuatro con reintento —las que emite `sirius_retry` desde
`sirius_validate_activation.sh:119`— y una sin reintento, la del gate del workflow. Ambas
llamaban al mismo sitio:

```
gh api "repos/${REPO}/issues/${ISSUE}/labels" --jq '.[].name'
```

Lo decisivo es lo que **sí** funcionaba en esas mismas ejecuciones: `gh api
repos/{o}/{r}/issues/186` respondía sin problema, con el mismo token y en el mismo instante.
La incidencia se leía; sus etiquetas, no.

Eso descarta las tres explicaciones habituales de un `gh api` que falla: **permisos**,
**autenticación** y **límite de tasa** habrían roto las dos llamadas, no una. Ambos workflows
declaran además `issues: write`. Lo que queda es el endpoint concreto: `/issues/{n}/labels`
devolvía **cuerpo vacío** —de ahí que `--jq` se quede sin JSON que parsear— mientras el
objeto de la incidencia respondía normal.

`sirius_retry` hizo lo suyo: reintentó cuatro veces. Un reintento no arregla una respuesta
vacía **estable**, y ese es justo el caso. La incidencia quedaba con sus etiquetas puestas y
sin ningún evento capaz de revivirla.

No es un sitio: eran **siete**. La misma llamada estaba copiada en `sirius_issue.sh` (×2),
`sirius_merge_on_command.sh`, `sirius_reconcile.sh`, `sirius_validate_activation.sh` (×2) y
en el gate de `implement-sirius-work.yml`. El revisor, el corrector, el merge y el
reconciliador estaban a un evento de fallar igual que A2.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque
([#186, comentario 5317185383](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/186#issuecomment-5317185383)),
antes del primer commit, con el recuento de cinco apariciones como evidencia. Alcance: las
llamadas de lectura de etiquetas, sus simulados y este ADR; los workflows no los toco
(ADR-002), se entregan al propietario para pegar. Criterio de parada literal: **si tras este
cambio A2 sigue sin arrancar, no reintento a ciegas: vuelvo al log.**

## Opciones consideradas

1. **Reintentar más veces / con más espera**: descartada. Cuatro reintentos ya fallaban, y el
   fallo era estable durante más de una hora. Reintentar más es gastar tiempo en una respuesta
   que no cambia, y además convierte una avería en una espera silenciosa.
2. **Detectar la respuesta vacía y caer a una segunda vía**: descartada. Añade una rama de
   respaldo —código que casi nunca se ejecuta y que por tanto casi nunca se comprueba— para
   sostener una llamada que no hace falta hacer.
3. **Leer las etiquetas del objeto de la incidencia**: elegida. El objeto ya trae `labels`, así
   que da exactamente los mismos nombres por una vía que sí responde, y **ahorra una llamada**
   en vez de añadirla.

## Decisión

1. Toda lectura de etiquetas usa `gh api repos/{o}/{r}/issues/{n} --jq '.labels[].name'`.
   Las siete llamadas quedan convertidas; seis en esta PR y la del workflow en el pegado que
   acompaña a esta rama.
2. **Una prueba estructural impide volver al endpoint roto por costumbre**
   (`tests/automation/test_lectura_de_etiquetas.py`). Recorre el directorio de scripts y el de
   workflows —el directorio **es** la lista, así que un script nuevo queda cubierto sin que
   nadie se acuerde de añadirlo— y prohíbe el patrón `gh api …/issues/<n>/labels`.
3. La prohibición no puede cumplirse en vacío: `test_la_alternativa_esta_realmente_en_uso`
   exige que la vía correcta siga usándose. Sin ella, borrar toda lectura de etiquetas dejaría
   la familia en verde mientras la automatización pierde una comprobación que necesita.
4. **Los simulados de `gh` despachan por el FILTRO, no por la ruta, y aplican el `--jq` real
   del llamador.** La ruta ya no distingue esta lectura de la del cuerpo, y un simulado que
   devolviera la lista ya filtrada dejaría el filtro —lo único que este cambio toca— sin
   medir por ninguna prueba. Es el criterio que los propios simulados ya aplicaban a los
   comentarios y a las PRs; aquí solo se extiende a las etiquetas.

## Comprobación que la sostiene

- **Diagnóstico contado en el log, no inferido**: cinco apariciones de `unexpected end of JSON
  input`, cuatro con reintento (`sirius_validate_activation.sh:119`) y una sin él (el gate).
  Runs 32035648135, 32037335181, 32039249452 y 32039796936.
- **Prueba por mutación (ADR-001 §3)**, antes de dar la prueba por buena:

  | Mutación | Resultado |
  |---|---|
  | reintroducir `/issues/<n>/labels` en `sirius_issue.sh` | **falla** ese caso |
  | ídem en `sirius_merge_on_command.sh` | **falla** ese caso |
  | ídem en `sirius_reconcile.sh` | **falla** ese caso |
  | ídem en `sirius_validate_activation.sh` | **falla** ese caso |
  | borrar la vía correcta de los cuatro scripts | **falla** `test_la_alternativa_esta_realmente_en_uso` |
  | cambiar el filtro a `.[].name` (el viejo) en `sirius_validate_activation.sh` | **fallan 6 pruebas de comportamiento** de `test_sirius_activation.py` |

  La última es la que importa de verdad: demuestra que los simulados **miden el filtro** y no
  se limitan a devolver lo que el llamador espera. Sobre un objeto, `.[].name` es un error de
  jq, y las pruebas lo notan.
- **Un defecto real encontrado por la prueba nueva, no plantado**: el gate de
  `implement-sirius-work.yml` sigue llamando al endpoint roto. Esa es la única aserción en rojo
  de la rama, y se apaga con el pegado del propietario.
- Suite de automatización completa: 435 pasan, 1 se salta, 1 falla (la anterior).

## Consecuencias

- **La prueba de workflows quedará en rojo hasta que el propietario pegue el archivo
  corregido.** Es deliberado y se declara aquí: la automatización no puede editar `.github/**`
  (ADR-002), así que una aserción visible es el único mecanismo que tiene para pedir un cambio
  que no puede hacer. El rojo es el encargo, no un descuido.
- Una llamada menos por comprobación de etiquetas en los siete sitios.
- **Lo que esto NO afirma**: que el endpoint esté mal en general, ni que GitHub no vaya a
  arreglarlo. Afirma que esta automatización no depende de él, que es lo único que está en
  nuestra mano.
- **Debilidad conocida y declarada**: si el objeto de la incidencia dejara de responder, no hay
  respaldo — la lectura falla ruidosamente, que es el comportamiento que la #138 y el pegado
  del gate ya buscaban, pero sigue siendo una parada.

## Alternativas descartadas y por qué

Las opciones 1 y 2 de arriba. Además: **suprimir la comprobación de etiquetas** en el gate
para que A2 arrancara —descartada sin discusión: es la comprobación que distingue una
activación válida de una carrera entre eventos, y quitarla para desbloquear un bloque sería
cambiar un fallo ruidoso por uno silencioso.
