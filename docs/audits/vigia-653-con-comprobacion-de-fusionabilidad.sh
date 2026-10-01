#!/usr/bin/env bash
# Solo mira #653 (linea base del banco) y su PR cuando exista.
API="https://api.github.com/repos/canelamoraguezandyjesus-bot/sirius"
AUTH=(-s -H "Authorization: Bearer ${GH_TOKEN}" -H "Accept: application/vnd.github+json")
prev=""
primera=1
vacias=0
while true; do
  etiquetas=$(curl "${AUTH[@]}" "$API/issues/653/labels" 2>/dev/null | python3 -c '
import sys, json
try:
    print(",".join(sorted(l["name"] for l in json.load(sys.stdin))))
except Exception:
    print("?")
' 2>/dev/null || echo "?")
  inc=$(curl "${AUTH[@]}" "$API/issues/653" 2>/dev/null | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print("com=" + str(d.get("comments", 0)) + " " + d["state"])
except Exception:
    print("?")
' 2>/dev/null || echo "?")
  # Entrada 140: el 20-09 la PR #654 paso de `clean` a `dirty` -la fusion de
  # #652 en main- SIN que cambiara ni la etiqueta ni el head, y este vigia se
  # callo cuatro horas. Un vigia que solo mira el estado de la incidencia no ve
  # que la PR ha dejado de poder fusionarse. Se mira tambien.
  fus=$(curl "${AUTH[@]}" "$API/pulls/654" 2>/dev/null | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(("MERGED" if d.get("merged") else d.get("mergeable_state") or "?") + " head=" + (d.get("head") or {}).get("sha","?")[:8])
except Exception:
    print("?")
' 2>/dev/null || echo "?")
  ahora="etiquetas=[$etiquetas] inc=[$inc] pr=[$fus]"
  if [ "$ahora" != "$prev" ]; then
    echo "[$(TZ=Europe/Madrid date +%H:%M:%S)] $ahora"
    prev="$ahora"
  fi
  # Entrada 126 de la bitacora: una incidencia SIN etiquetas esta inerte, y un
  # vigilante que solo habla al cambiar produce silencio justo ahi. El silencio
  # se lee como progreso. Dos lecturas seguidas sin etiquetas: se avisa y se sale.
  if [ -z "$etiquetas" ] || [ "$etiquetas" = "?" ]; then
    vacias=$((vacias + 1))
  else
    vacias=0
  fi
  if [ "$vacias" -ge 2 ]; then
    echo "653 SIN ETIQUETAS en dos lecturas: incidencia inerte, nadie la va a despertar"
    exit 0
  fi
  if [ "$primera" = "0" ]; then
    case "$etiquetas" in
      *blocked-decision*) echo "653 PARADA POR DECISION"; exit 0;;
      *failed-safely*)    echo "653 PARADA FAILED_SAFELY"; exit 0;;
      *completed*)        echo "653 COMPLETADA"; exit 0;;
      *ready-for-merge*)  echo "653 LISTA PARA FUSIONAR (no fusionar: es gesto del propietario)"; exit 0;;
    esac
    case "$fus" in
      dirty*)   echo "654 YA NO SE PUEDE FUSIONAR (conflicto con main): trae main y resuelvelo"; exit 0;;
      behind*)  echo "654 se ha quedado detras de main: trae main"; exit 0;;
      MERGED*)  echo "654 FUSIONADA"; exit 0;;
    esac
  fi
  primera=0
  sleep 120
done
