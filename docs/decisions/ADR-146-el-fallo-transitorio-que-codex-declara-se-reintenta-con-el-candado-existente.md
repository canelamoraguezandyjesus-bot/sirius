# ADR-146 — El fallo transitorio que Codex declara se reintenta con el candado existente

- Estado: PROPUESTO
- Fecha: 2026-09-05
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario o
  por su operador bajo la autorización vigente del 05-09. No toca `.github/**`:
  vive en dos guiones de scripts/automation y sus pruebas.

## Contexto y problema

ADR-141 dejó el reintento automático de una ronda de revisión para exactamente
tres causas de infraestructura, y excluyó a propósito el «resultado de Codex
ausente/fuera de contrato»: «puede ser un defecto real y repetible del
recolector; reintentarlo taparía la señal. Si la práctica enseña que suele ser
transitorio, se amplía con su medición.»

La medición llegó el mismo día de estrenarse ADR-141. El 05-09 a las 15:36 UTC
(incidencia #541, vuelta 3), Codex declaró su propio fallo — «Codex Review:
Something went wrong. Try again later by commenting "@codex review".» — y el
recolector lo clasificó correctamente como `codex-fallo-declarado` (ADR-060).
Al no estar en el conjunto reintentable, la incidencia paró en `failed-safely`
y costó un `continua` manual; la ronda re-armada aprobó a la primera. El texto
del propio conector pedía el reintento, y el reintento funcionó.

Pero la razón `codex-fallo-declarado` cubre CUATRO prefijos observados
(`sirius_codex_review.py`, tabla de `_declara_fallo_del_conector`), y no todos
son transitorios: «You have reached your Codex usage» (límite de uso) y «To use
Codex here,» (configuración) son persistentes, y «Codex couldn't complete this
request.» es de transitoriedad no demostrada. Reintentar la razón entera
quemaría la única ronda del candado de ADR-141 contra fallos que un reintento
no arregla.

## Criterio de parada (escrito ANTES de decidir)

- Si el reintento exigiera tocar `review-sirius-work.yml` o el aplicador de
  veredictos, parar: ADR-141 ya dejó la decisión en el aplicador y la
  clasificación en Python testeable, y este cambio debe caber entero ahí.
- Si el subtipo transitorio no fuera distinguible por un criterio material
  (el prefijo del cuerpo, ya censado), parar: adivinar transitoriedad por
  heurística blanda reintentaría fallos persistentes.
- El candado de ADR-141 (un reintento por head, marcador material) no se toca
  ni se amplía: si el diseño lo necesitara, parar.

## Opciones consideradas

1. El recolector etiqueta el subtipo transitorio con razón propia
   (`codex-fallo-declarado-transitorio`, solo el prefijo cuyo texto pide el
   reintento) y el agregador amplía su conjunto reintentable a
   `{timeout, codex-fallo-declarado-transitorio}`. El resto del mecanismo de
   ADR-141 — bandera, aplicador, candado por head — queda intacto.
2. Ampliar el conjunto del agregador a toda la razón `codex-fallo-declarado`.
3. Dejarlo como está (un `continua` manual por cada fallo declarado).

## Decisión

**Opción 1.** Dos piezas:

- `sirius_codex_review.py`: la tabla de prefijos declarados se parte por
  transitoriedad — `_FALLOS_TRANSITORIOS_DEL_CONECTOR` («Codex Review:
  Something went wrong.», el único cuyo propio texto pide «Try again later» y
  el único observado recuperándose al re-armar) y
  `_FALLOS_PERSISTENTES_DEL_CONECTOR` (los otros tres). La rama del fallo
  declarado emite `codex-fallo-declarado-transitorio` para el primero y
  conserva `codex-fallo-declarado` para el resto. Nada más cambia: ni la
  detección (mismos prefijos, misma unión), ni el resumen, ni el no-publicar.
- `sirius_aggregate_reviews.py`: el conjunto reintentable de la regla 3 pasa
  de `{"timeout"}` a `{"timeout", "codex-fallo-declarado-transitorio"}`
  (variable renombrada a `solo_infra_transitoria_de_codex`). El subtipo
  persistente sigue parando para diagnóstico humano.

Por qué no la 2: reintentaría límites de uso y errores de configuración —
persistentes — quemando la ronda del candado sin arreglar nada, y taparía una
señal que conviene mirar (la exclusión original de ADR-141, que sigue vigente
para ese subtipo). Coste del peor caso con la opción 1: idéntico al de
ADR-141 — una ronda extra si el fallo «transitorio» resultara persistente,
acotada por el candado por head.

## Comprobación que la sostiene

- Censo previo de lectores de la razón: `codex-fallo-declarado` solo lo leen
  el recolector, sus pruebas (tres aserciones) y ADR-060; ni el reanudador ni
  la proyección del espejo la consumen. La razón nueva no colisiona con nadie.
- Rojo previo, visto fallar (ADR-001), con el par de pruebas escrito ANTES del
  código: «2 failed, 110 passed» sobre
  `test_sirius_aggregate_reviews.py` + `test_sirius_codex_review.py` — las dos
  nuevas expectativas (el cuerpo real de la PR #233 con la razón transitoria;
  la bandera con esa razón) contra el código vigente, con la adversaria del
  subtipo persistente ya en verde de serie. Tras el cambio: «112 passed».
- Mutaciones vistas fallar, una por dirección y cada una tumbando EXACTAMENTE
  su guardián: (a) el subtipo transitorio devuelto a la razón genérica →
  `1 failed`:
  `FAILED tests/automation/test_sirius_codex_review.py::test_collect_para_en_cuanto_el_conector_declara_un_fallo_suyo`;
  (b) el agregador aceptando también `codex-fallo-declarado` → `1 failed`:
  `FAILED tests/automation/test_sirius_aggregate_reviews.py::test_fallo_declarado_persistente_de_codex_no_se_reintenta_solo`.
  Árbol restaurado: «112 passed».
- Papeles dependientes sincronizados en el mismo commit (ADR-135): ADR-141
  (su alternativa descartada remite aquí: la medición que pedía llegó y amplió
  solo el subtipo transitorio) y ADR-060 (la razón gana un hermano transitorio
  sin cambiar la detección).
- Validación obligatoria completa sobre el árbol final en UNA sola invocación
  del encadenado exacto de `scripts/check.ps1` (`bash -e`; este contenedor no
  tiene `pwsh`, exit 127 comprobado — Quality revalida en CI con el script
  real): resultado exacto transcrito en la PR que introduce este ADR.

## Consecuencias

- El caso del 05-09 se habría absorbido solo: re-armado en ~1 minuto con el
  candado de ADR-141, sin `continua` manual.
- Un fallo declarado PERSISTENTE (límite de uso, configuración) sigue parando
  a la primera, con su diagnóstico intacto — la señal que ADR-141 protegía.
- Si el conector cambia su texto de error, el reconocimiento degrada al
  comportamiento previo (esperar el plazo → timeout → reintentable por la vía
  de siempre), nunca a un reintento indebido.

## Alternativas descartadas y por qué

- **Toda la razón reintentable (opción 2):** quemaría el candado contra
  fallos persistentes y taparía su señal; arriba.
- **No hacer nada (opción 3):** el dato del día muestra el coste — un
  `continua` humano por un fallo cuyo propio texto pedía el reintento y que
  el reintento resolvió a la primera.
- **Distinguir la transitoriedad en el agregador leyendo el resumen:**
  cruzaría capas y dependería de texto libre; el prefijo censado vive donde
  se reconoce, en el recolector.
