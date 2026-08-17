# ADR-025 — Ninguna afirmación de un prompt sobre su entorno vale sin una prueba que la ate al workflow que lo ejecuta

- Estado: PROPUESTO
- Fecha: 2026-08-17
- Aprobación: la fusión de la PR de esta rama por el propietario.

## Contexto y problema

En la PR #183 escribí en `implementer.md` y `corrector.md` que las validaciones «se ejecutan
con lo que ya está disponible» y que «`uv` ya está en el runner». **No lo verifiqué. Era
falso.**

Solo `quality.yml` y `quality-windows.yml` instalaban `uv` (`astral-sh/setup-uv`). Los
workflows que ejecutan los tres roles de Claude —implementación, corrección, revisión— no
instalaban nada: ni `uv`, ni el entorno sincronizado del proyecto.

Consecuencia inmediata (incidencia #182, run 31990550597): el implementador comprobó que no
existía `uv` —`command -v uv`, `find / -iname uv`, búsqueda de pyenv/asdf/mise—, vio que el
contrato le prohibía instalarlo, y se detuvo en `FAILED_SAFELY` con el diagnóstico exacto.
**Hizo lo correcto con la información que le di; la información era mía y estaba mal.**

La sección de entorno la escribí pensando en el revisor, que solo lee un diff después de que
Quality haya corrido, y la copié tal cual a dos roles que **tienen que ejecutar las cuatro
validaciones**. El error no fue prohibir instalar: fue afirmar, sin comprobarlo, que no haría
falta.

Es la misma familia que este repositorio lleva corrigiendo desde la PR #136: *afirmar más de
lo que el dato sostiene*. Solo que esta vez la afirmación no estaba en un informe, sino
dentro del contrato de un rol, donde nadie la contrastaba.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque
([#182, comentario 5311782823](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/182#issuecomment-5311782823)),
antes del primer commit. Alcance: los dos prompts, la prueba y este ADR. `reviewer.md` no se
toca. Parar si hiciera falta tocar workflows o permisos — no hizo falta. Prueba nueva
verificada por mutación en las dos direcciones antes de darla por buena.

## Opciones consideradas

1. **Corregir el texto y ya**: descartada como solución completa. Deja el mismo agujero: la
   siguiente afirmación sobre el entorno tampoco tendría quien la contraste.
2. **Quitar del prompt toda mención al entorno**: descartada — el rol necesita saber que no
   debe improvisar instalaciones; fue precisamente esa regla la que evitó que se pusiera a
   instalar cosas a ciegas.
3. **Corregir el texto y atar la afirmación al workflow con una prueba**: elegida.

## Decisión

1. Los dos prompts pasan a decir la verdad: **es el workflow quien prepara el entorno** —
   instala `uv`, sincroniza dependencias con `uv sync --locked --all-groups` y añade las
   bibliotecas de Qt que necesita la suite de GUI—, así que `uv run …` funciona sin instalar
   nada. Y si aun así faltara algo, **eso es un fallo del entorno**, cuyo desenlace correcto
   sigue siendo `FAILED_SAFELY` con diagnóstico.
2. **Una prueba ata la promesa a los pasos reales**: si un prompt afirma que el entorno viene
   preparado, el workflow que ejecuta ese rol debe tener `astral-sh/setup-uv` y `uv sync`, y
   ambos **antes** del paso que arranca el modelo. Escribir la promesa donde no se cumple, o
   quitar el `setup-uv` de un workflow cuyo prompt la promete, falla en CI.
3. Regla general que este caso deja escrita: **una afirmación de un prompt sobre su propio
   entorno es una afirmación técnica como cualquier otra, y necesita su comprobación.** El
   prompt no es prosa: es contrato ejecutable, y lo que dice se cumple o se rompe una ronda.

## Comprobación que la sostiene

- Los tres pasos nuevos leídos de `main` (`0654a18`) parseando el YAML de verdad, no de una
  captura: ambos workflows válidos, con `Install Qt` / `Install uv` / `Sync environment` en
  posiciones 2, 3 y 4 — después del `Checkout` y antes del gate y del modelo.
- Diagnóstico del rol tomado literal del run 31990550597, no reconstruido.
- **Prueba por mutación (ADR-001 §3), en las dos direcciones:**

  | Mutación | Resultado |
  |---|---|
  | apuntar `implementer.md` a un workflow que NO instala `uv` (`review-sirius-work.yml`) | **falla** — la aserción muerde |
  | quitar la frase de promesa del prompt del corrector | **se salta** — correcto: la prueba solo aplica a quien promete |

- El resto de invariantes de `test_prompts_de_rol.py` siguen en verde: 16 pasan, 1 se salta
  (el revisor no hace esa promesa).

## Consecuencias

- La ronda perdida del run 31990550597 no fue en balde: su `FAILED_SAFELY` bien diagnosticado
  es lo que hizo visible el defecto del workflow. **Es el primer caso en esta incidencia en
  que una parada segura produjo valor** en vez de solo coste, y conviene registrarlo: es
  exactamente lo que el veredicto provisional vino a comprar.
- **Debilidad conocida y declarada**: si alguien sustituye la frase de promesa por otra
  redacción distinta, la prueba se salta en silencio. El invariante general de la sección de
  entorno sigue exigido, pero la atadura con el workflow no.
- No se afirma que el entorno no pueda fallar. Se afirma que, si el prompt promete algo, el
  workflow lo cumple.

## Alternativas descartadas y por qué

Las opciones 1 y 2 de arriba. Además: hacer que el propio rol instale `uv` cuando falte
—descartada, porque convierte cada ronda en una instalación no auditada y contradice el
perímetro—; y comprobar la promesa ejecutando el workflow —imposible sin red desde las
pruebas, y `astral-sh/setup-uv` es una dependencia externa: lo que se comprueba es que el
paso está declarado y en el orden correcto, no que GitHub lo ejecute bien.
