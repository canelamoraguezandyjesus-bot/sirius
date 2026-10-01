#!/usr/bin/env bash
# Puerta previa a fusionar la PR #578 (H1, ADR-168).
#
# DOS MODOS DE FALLO QUE ESTE GUION YA HA COMETIDO Y NO REPITE (ver bitacora 61):
#   1. `grep -E` con clases como [ií] NO casa UTF-8 multibyte -> da OK falso.
#      Por eso aqui solo se usan cadenas LITERALES con `grep -F`.
#   2. `set -o pipefail` + `printf ... | grep -q` sobre entrada grande -> grep
#      sale al primer acierto, printf recibe SIGPIPE, y una COINCIDENCIA se
#      convierte en FALLO. Por eso se usa `<<<` (here-string), nunca tuberia.
set -uo pipefail

API="https://api.github.com/repos/canelamoraguezandyjesus-bot/sirius"
AUTH=(-s -H "Authorization: Bearer ${GH_TOKEN}" -H "Accept: application/vnd.github+json")
fallos=0
ok()    { printf '  OK    %s\n' "$1"; }
falla() { printf '  FALLA %s\n' "$1"; fallos=$((fallos+1)); }

cuerpo=$(curl "${AUTH[@]}" "$API/pulls/578" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("body") or "")')
head_sha=$(curl "${AUTH[@]}" "$API/pulls/578" | python3 -c 'import sys,json; print(json.load(sys.stdin)["head"]["sha"])')
echo "== PR #578, head ${head_sha:0:8} =="

# --- 1. los dos hallazgos de la ronda 1 tienen que estar atendidos ---
# CLAUDE-R1-001: la comparacion created_at <= hasta mezclaba dos formas de cadena.
if grep -qF "created_at" <<<"$cuerpo"; then ok "el cuerpo habla de created_at (CLAUDE-R1-001)"
else falla "el cuerpo NO menciona created_at: CLAUDE-R1-001 sin transcribir"; fi

# CODEX-001: git diff --check tiene que llevar RANGO, no ir a secas.
#   MODO DE FALLO 3 (08-09, cuarto veredicto equivocado de este guion): el
#   cuerpo de una PR viene con saltos de linea donde el redactor los puso, asi
#   que 'git diff --check' y el hash pueden caer en LINEAS distintas. Un patron
#   que exige los dos en la misma linea da FALLA falsa. Se aplanan los saltos
#   a espacios antes de comparar.
plano=$(tr '\n' ' ' <<<"$cuerpo")
if grep -qE 'git diff --check +[0-9a-f]{7,40}' <<<"$plano"; then
  ok "git diff --check aparece CON rango de revisiones (CODEX-001)"
else
  falla "git diff --check sin rango: es la forma que no demuestra nada"
fi

# --- 2. la cadena tiene que estar re-anclada al arbol NUEVO, no a ffd8d05 ---
if grep -qF "ffd8d05" <<<"$cuerpo"; then
  falla "el cuerpo conserva el ancla vieja ffd8d05: la validacion no se re-ancla"
else
  ok "sin rastro del ancla vieja ffd8d05"
fi
if grep -qE 'EXIT_CODE_CHECK=0' <<<"$cuerpo"; then ok "codigo de salida de la cadena transcrito"
else falla "falta EXIT_CODE_CHECK=0"; fi
if grep -qE '[0-9]{4} passed' <<<"$cuerpo"; then ok "terna de pytest transcrita"
else falla "falta la terna de pytest"; fi

# --- 3. las cuatro cifras del banco no pueden haber empeorado ---
# H1 dejo --peticion en 17/47; 162; 78/81; 0. Si cambian, hay que explicarlo.
for cifra in "17/47" "78/81"; do
  if grep -qF "$cifra" <<<"$cuerpo"; then ok "el cuerpo sigue declarando $cifra"
  else falla "el cuerpo ya NO declara $cifra: la medicion cambio sin explicarse"; fi
done

# --- 4. la puerta de fusion: no puede ir por detras de la base ---
estado=$(curl "${AUTH[@]}" "$API/pulls/578" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("mergeable_state"), d.get("mergeable"))')
echo "  (mergeable_state = $estado)"

# --- 5. Quality verde SOBRE ESTE head, no sobre uno anterior ---
concl=$(curl "${AUTH[@]}" "$API/commits/$head_sha/check-runs" | python3 -c '
import sys, json
d = json.load(sys.stdin)
for c in d.get("check_runs", []):
    if c["name"] == "quality": print(c["status"], c.get("conclusion")); break
else: print("sin-quality")')
if [ "$concl" = "completed success" ]; then ok "Quality verde sobre ESTE head"
else falla "Quality no esta verde sobre este head: $concl"; fi

# --- 6. EL CICLO TIENE QUE HABER CERRADO, no estar a medias ---
#   Sin esto el guion daba OK con la incidencia todavia en `reviewing`: es el
#   mismo error de tomar un estado intermedio por final que cometi yo el 08-09
#   leyendo un arbol a medio corregir (bitacora, entrada 71). Un `mergeable_
#   state` limpio dice que GIT puede fusionar, no que el CICLO haya terminado.
etiquetas=$(curl "${AUTH[@]}" "$API/issues/577/labels" | python3 -c '
import sys, json
print(",".join(sorted(l["name"] for l in json.load(sys.stdin))))')
echo "  (etiquetas = $etiquetas)"
if grep -qF "sirius:ready-for-merge" <<<"$etiquetas"; then
  ok "la incidencia esta en ready-for-merge: el ciclo cerro"
else
  falla "la incidencia NO esta en ready-for-merge ($etiquetas): el ciclo sigue abierto"
fi

echo
if [ "$fallos" -eq 0 ]; then echo "VEREDICTO: se puede fusionar (comprobaciones: 0 fallos)"
else echo "VEREDICTO: NO fusionar todavia ($fallos fallo(s))"; fi
exit "$fallos"
