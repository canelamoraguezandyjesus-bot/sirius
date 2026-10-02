# ADR-231 — Un defecto se cierra desde la PR que mete en `main` el ADR que lo nombra, no solo desde la del ADR que lo declaró

- Estado: APROBADO
- Fecha: 2026-10-02
- Aprobación: la fusión de la PR por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-02-un-defecto-se-cierra-desde-la-pr-que-mete-el-adr-que-lo-cierra.md`,
  publicada en el commit `e8336408` (02-10-2026, 13:15 UTC), antes del primer
  commit de arreglo.

## Contexto y problema

ADR-222 ató el `pr:` de un defecto cerrado a **la PR que metió en `main` el
ADR que lo declaró**: la guarda
`test_cada_referencia_pr_es_una_pr_fusionada_en_main_cuando_hay_historia`
busca el commit de primer padre que añadió `docs/decisions/ADR-<adr>-*.md` y
exige que su marca final «(#N)» sea ese `pr`. Es la forma fuerte que pidió la
ronda 1 de Codex en la PR #668, y vale para el caso común: el defecto se
declara y se arregla en la misma PR.

No vale para el otro caso, que ya existía cuando se escribió: **H-216**.
ADR-216 lo declaró abierto (PR #663, incidencia #662: la contradicción de
etiquetas de #392 llevaba 27 días apartada sin que nadie la viera) y lo arregló
ADR-227 en la PR #674 (las divergencias apartadas se escriben junto al diario y
la vista las enseña con su edad). El hecho quedó resuelto el 01-10-2026 (#392
con una sola etiqueta y el encargo entregado por el reflector), el mecanismo
que lo dejaba invisible está corregido, y el registro no lo puede decir: con
`pr: 674` la guarda lo rechaza (ADR-216 lo metió la #663) y con `pr: 663` la
referencia mentiría (esa PR no lo arregló). ADR-227 lo deja escrito en sus
consecuencias y remite a este ADR.

Medido sobre el registro en `main` (`68d81c5f`): tres defectos abiertos
(H-202, H-203 y H-216); H-216 es el único cuyo arreglo ya está en una PR
distinta de la que lo declaró. No es una excepción que se tapa con una lista:
es el camino normal de un defecto que se declara al verlo y se arregla después.

## Criterio de parada (escrito ANTES de decidir)

- Si la vía nueva obligara a leer el texto de todos los ADR en cada ejecución
  local y la batería del registro pasara de segundos a minutos, parar y buscar
  otra forma.
- Cuatro mutaciones tienen que caer: M1 la vía nueva no mira si el ADR nombra
  el defecto; M2 admite un ADR anterior al declarante; M3 reconoce el nombre
  por subcadena (`H-2160` por `H-216`); M4 la vía de ADR-222 deja de valer.
- H-216 se cierra solo cuando la #674 esté en `main` y la guarda, con la
  historia real, acepte `pr: 674`.
- Dos rondas de revisión externa con defectos de la misma familia → raíz.

## Opciones consideradas

1. **Una lista de excepciones** (`H-216 → 674`) junto a la guarda. Rechazada:
   es la lista que ADR-179 enseñó a evitar; la siguiente vez se añade otra
   línea y la regla deja de decir nada.
2. **Cerrar H-216 con `pr: 663`.** Rechazada: la referencia tiene que llevar
   a quien lo arregló, no a quien lo vio; es justo lo que ADR-222 quería que un
   clon de `main` pudiera seguir.
3. **Aflojar la guarda a «una PR fusionada cualquiera».** Rechazada: es la
   forma débil que la ronda 1 de Codex en la #668 ya tumbó.
4. **Admitir también la PR que metió un ADR posterior que nombra el defecto.**
   Elegida: conserva la fuerza (la PR tiene que estar fusionada, haber añadido
   un ADR posterior al declarante, y ese ADR tiene que nombrar el `H-NNN`) y
   modela el caso real: el arreglo cuenta en su ADR qué defecto cierra.

## Decisión

1. Un defecto cerrado puede citar en `pr:` **la PR que metió en `main` el ADR
   que lo declaró** (ADR-222) **o la que metió un ADR posterior que lo nombra
   por su id**, palabra entera. `_pr_que_puede_citar`
   (`tests/automation/test_registro_de_defectos.py`) lo decide, pura, con dos
   funciones inyectadas —qué PR y qué commit introdujeron cada ADR, y el
   texto de un ADR en un commit dado— y dice por cuál de las dos vías vale. El
   texto se lee **en el commit que introdujo el ADR**, no en la punta de
   `main`: una enmienda posterior que añadiera el `H-NNN` haría pasar a la PR
   original sin haberlo nombrado ni arreglado (ronda 1 de Codex).
2. La guarda de ADR-222 usa esa función donde antes comparaba solo con el ADR
   declarante. La comprobación fuerte sigue ejercitándose sobre todo defecto
   con `pr:` cuyo ADR está en `main` (su anti-vacua no cambia) y Quality sigue
   sin medir la existencia (clona con profundidad 1): lo hace la cadena local.
3. El texto de un ADR se lee con `git show <commit>:<ruta>` en el commit que lo
   introdujo, y solo cuando la vía de ADR-222 no vale: el coste es el de los
   defectos cerrados desde otra PR, hoy uno.
4. La skill `registro-de-defectos` lo dice en la línea de `pr:`: la PR que lo
   fusiona o, si el defecto quedó abierto y lo arregló otra PR, la PR del
   arreglo, cuyo ADR tiene que nombrar el `H-NNN`.
5. **H-216 se cierra con esta decisión**: `cerrado_por` el commit del arreglo
   en la rama de la #674 (`27a1196b`, el de ADR-227) y `pr: 674`, en cuanto esa
   PR esté en `main` y la guarda lo acepte con la historia real.

## Comprobación que la sostiene

- `test_la_pr_que_puede_citar_es_la_de_su_adr_o_la_de_un_adr_posterior_que_lo_nombra`
  (pura, con dobles): la vía de ADR-222 sigue valiendo; la del arreglo vale; una
  PR que metió un ADR que no lo nombra, una que no metió ninguno, `H-2160` por
  `H-216`, un ADR anterior al declarante y una enmienda posterior del ADR (el
  texto que metió esa PR no lo nombraba) no valen.
- `test_cada_referencia_pr_es_una_pr_fusionada_en_main_cuando_hay_historia`
  con la función nueva y la historia real de `main`: verde sobre el registro
  actual, con H-216 cerrado con `pr: 674` (ADR-227 lo nombra en el commit que
  lo introdujo, el aplastado de la #674).
- Mutaciones, cada una aplicada sobre la guarda y vista caer, con el fichero
  restaurado después (`diff -q` limpio):

| | Mutación | Resultado |
|---|---|---|
| M1 | la vía nueva no mira si el ADR nombra el defecto | cae la prueba pura (el caso de la PR 690) |
| M2 | la vía nueva admite un ADR anterior al declarante | cae la prueba pura (el caso del ADR-200) |
| M3 | el nombre se reconoce por subcadena | cae la prueba pura (`H-2160`) |
| M4 | la vía de ADR-222 deja de valer | cae la prueba pura (el caso de la PR 663) |
| M5 | el texto del ADR se lee en la punta de `main` y no en el commit que lo introdujo (ronda 1 de Codex en la PR #679) | cae la prueba pura (el caso de la enmienda posterior) |

- `ruff format`, `ruff check`, `mypy`, `sirius_check_docs.py` sobre el ADR y la
  nota, `sirius-memoria conocimiento` y las baterías del registro, de la memoria
  y de las lecciones, en verde.

## Consecuencias

- El registro puede decir la verdad sobre un defecto que se declaró al verlo y
  se arregló en otra PR: la referencia lleva al ADR del arreglo.
- Quien cierre así tiene que nombrar el `H-NNN` en el ADR del arreglo; si no lo
  nombra, la guarda lo rechaza y dice por qué.
- Una lectura más de `origin/main` en la cadena local por cada defecto cerrado
  desde otra PR; en Quality nada cambia.

## Alternativas descartadas y por qué

Las tres primeras opciones: la lista de excepciones (ADR-179), la referencia
que miente (ADR-222) y la forma débil (ronda 1 de Codex en la #668).

## La lección

- familia: `regla-nueva-sin-pasarla-por-los-casos-vivos`
- sin esto se repetiría: una guarda nueva que modela el camino común y prohíbe sin querer un caso legítimo que ya existía al escribirla (H-216 abierto con su arreglo en otra PR el mismo día que ADR-222), con la batería en verde y un defecto arreglado que el registro no puede cerrar.
- lo hace cumplir: `tests/automation/test_registro_de_defectos.py`
