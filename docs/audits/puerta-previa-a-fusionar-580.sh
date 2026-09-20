#!/usr/bin/env bash
# Puerta previa a fusionar la PR #580 (palanca 3, incidencia #579).
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

cuerpo=$(curl "${AUTH[@]}" "$API/pulls/580" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("body") or "")')
head_sha=$(curl "${AUTH[@]}" "$API/pulls/580" | python3 -c 'import sys,json; print(json.load(sys.stdin)["head"]["sha"])')
echo "== PR #580, head ${head_sha:0:8} =="

# --- 1. hallazgos de las rondas: SE RELLENA cuando la revision los publique ---
#   Deliberadamente vacio: este guion comprueba lo que las rondas senalen, y
#   todavia no hay rondas. Rellenarlo con cadenas LITERALES (grep -F) sobre
#   `$plano`, que ya trae los saltos de linea aplanados a espacios.
plano=$(tr '\n' ' ' <<<"$cuerpo")

# --- 2. la cadena re-anclada al arbol del head, no a uno anterior ---
#   MODOS DE FALLO 4 y 5, los dos del 08-09 y los dos por la FORMA del texto:
#   (4) el patron exigia negritas y el cuerpo usaba comillas invertidas;
#   (5) al arreglarlo escribi `.rbol` para esquivar la tilde, y `.` casa UN
#       BYTE mientras que 'a' acentuada ocupa DOS -> el modo de fallo 1 otra
#       vez, reaparecido por parchear el sintoma en vez de evitar acentos.
#   Regla: NINGUN patron de este guion contiene un caracter acentuado ni un
#   comodin que pretenda cubrirlo. Se usan clases negadas ([^ ]+).
if grep -qE "anclad[ao] al [^ ]+ de [^0-9a-f]{0,4}[0-9a-f]{7}" <<<"$plano"; then ok "la validacion declara a que arbol esta anclada"
else falla "el cuerpo no declara el arbol de la validacion"; fi
if grep -qE 'EXIT_CODE_CHECK=0' <<<"$cuerpo"; then ok "codigo de salida de la cadena transcrito"
else falla "falta EXIT_CODE_CHECK=0"; fi
if grep -qE '[0-9]{4} passed' <<<"$cuerpo"; then ok "terna de pytest transcrita"
else falla "falta la terna de pytest"; fi

# --- 3. cifras del banco: exportar CIFRAS_A_VIGILAR con las que la PR declare ---
#   p.ej.  CIFRAS_A_VIGILAR='17/47 78/81' bash antes_de_fusionar_580.sh
for cifra in ${CIFRAS_A_VIGILAR:-}; do
  if grep -qF "$cifra" <<<"$cuerpo"; then ok "el cuerpo sigue declarando $cifra"
  else falla "el cuerpo ya NO declara $cifra: la medicion cambio sin explicarse"; fi
done

# --- 4. la puerta de fusion: no puede ir por detras de la base ---
estado=$(curl "${AUTH[@]}" "$API/pulls/580" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("mergeable_state"), d.get("mergeable"))')
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
etiquetas=$(curl "${AUTH[@]}" "$API/issues/579/labels" | python3 -c '
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
