# Evidencia — el doble de `gh` rechaza lo que el `gh` real rechaza

Acompaña a ADR-193 y a `docs/audits/arranque-el-doble-de-gh-rechaza-lo-que-el-real-rechaza.md`.
Aquí van las salidas tal cual, para que la decisión se pueda comprobar sin
creerle nada a la prosa.

## 1. El fallo en producción

Run 132 de «Reconciliar estados de Sirius», 14-09-2026, leyendo la #619:

```
2026-09-14T04:56:13.1277533Z the `--slurp` option is not supported with `--jq` or `--template`
2026-09-14T04:56:13.1300929Z sirius_retry: fallo tras 4 intento(s): gh api -X GET
  repos/canelamoraguezandyjesus-bot/sirius/issues/619/events -f per_page=100
  --paginate --slurp --jq (add // []) | [.[] | select(.event == "labeled" and
  .label.name == "sirius:ci-pending")] | if length == 0 then empty else
  (last | "\(.created_at) \(.id)") end
2026-09-14T04:56:13.1306693Z [AVISO] #619: ci-pending; no pude fechar el estado, así que no reparo a ciegas.
```

Los cuatro intentos fallan igual porque no es un fallo transitorio: es la
validación de argumentos de `gh`, antes de cualquier petición.

## 2. Desde cuándo

```
$ git log --format='%h %ad' --date=short -S'--slurp' --all -- . | sort -k2
aedb0711 2026-08-05
c4e0a25d 2026-08-10
f95b8d08 2026-08-10   <- la corrección del hallazgo P2, que introduce la combinación
5cc3f186 2026-08-31   <- extracción del guion desde el YAML (mismo texto)
e7a77c18 2026-09-05

$ git show -s --format='%ci %s' f95b8d08
2026-08-10 17:04:47 +0000 Corregir tres defectos de la revisión de Codex (#138)
```

Del 10-08-2026 al 14-09-2026: **35 días**.

## 3. La medida que decide: el doble absolvía

Las cuatro celdas salen de correr `uv run pytest
tests/automation/test_sirius_reconcile.py -q` sobre cada combinación.

| | doble permisivo (antes) | doble fiel (esta rama) |
|---|---|---|
| llamada con `--slurp --jq` (producción) | `41 passed` | `20 failed, 21 passed` |
| llamada con `--paginate --jq` (arreglo) | `41 passed` | `43 passed` |

La celda de arriba a la izquierda es el defecto entero.

## 4. Las cuatro mutaciones, con lo que imprimieron

- **M1 — la llamada vuelve a `--slurp --jq`.**
  `20 failed, 21 passed`. Entre ellas
  `test_recon_slurp_002_ningun_guion_de_automatizacion_combina_slurp_con_un_filtro`,
  que la nombra en el propio mensaje de fallo:
  `assert not ['sirius_reconcile.sh: sirius_retry gh api -X GET … --paginate --sl…']`.
  Es la prueba de que el guion se lee con las líneas continuadas ya pegadas: la
  llamada está partida en cuatro líneas.

- **M2 — el doble vuelve a aceptar la combinación.**
  `1 failed, 42 passed`; el que cae es
  `test_recon_slurp_001_el_doble_de_gh_rechaza_slurp_con_jq_como_el_real`.
  Y con **M1 y M2 puestas a la vez**: `41 passed`. Esa es la demostración de la
  raíz — no faltaba una prueba, absolvía el doble.

- **M3 — `tail -n 1` → `head -n 1`.**
  `2 failed, 41 passed`: `test_recon_stuck_001` y `test_recon_stuck_008`. La
  fecha pasa a ser la de la primera aplicación de la etiqueta, que es justo la
  propiedad que P2 defendía.

- **M4 — quitar `--paginate` de la llamada.**
  **`43 passed`: sobrevivió.** El simulado entregaba todas las páginas hubiera o
  no `--paginate`, así que una llamada que en producción lee solo la primera
  página pasaba entera. Enseñando al doble a paginar —sin `--paginate`, solo la
  primera página—, la misma mutación deja `1 failed, 42 passed`
  (`test_recon_stuck_008`).

## 5. Lo que NO se midió, dicho

- **No se ha reproducido contra un `gh` real.** No hay `gh` instalado en la
  sesión que hizo este trabajo. Lo que sostiene la regla es el mensaje del
  propio `gh` en el log de producción, que es la herramienta hablando de sí
  misma, no una suposición sobre ella.
- **No se ha medido cuántos avisos concretos se dejaron de publicar** en esos 35
  días. No hay dónde: el reconciliador no guarda lo que no dijo. Lo que sí
  consta es que ninguno pudo publicarse por antigüedad, porque ninguno podía
  fecharse.
- **No se ha auditado el resto del doble** en busca de otras opciones que `gh`
  valide y el simulado ignore. Se cierran las tres que ya han costado algo: el
  método, `--slurp` y `--paginate`.
