#!/usr/bin/env bash
# Espera a que Quality termine sobre el head nuevo. Emite en CUALQUIER estado
# terminal, no solo en verde: un filtro que solo busca el exito se calla en un
# fallo y el silencio se lee como progreso (entradas 126 y 140).
API="https://api.github.com/repos/canelamoraguezandyjesus-bot/sirius"
AUTH=(-s -H "Authorization: Bearer ${GH_TOKEN}" -H "Accept: application/vnd.github+json")
HEAD=178b1bee91344b8e35e36aba09d5ccdcf29150da
for _ in $(seq 1 120); do
  r=$(curl "${AUTH[@]}" "$API/commits/$HEAD/check-runs" 2>/dev/null | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    runs = [(c["name"], c["status"], c.get("conclusion")) for c in d.get("check_runs", [])]
    if not runs:
        print("SIN_RUNS"); raise SystemExit
    pend = [n for n, s, _ in runs if s != "completed"]
    if pend:
        print("PENDIENTE " + ",".join(pend))
    else:
        print("TERMINADO " + " ".join(f"{n}={c}" for n, _, c in runs))
except Exception as e:
    print("ERROR " + type(e).__name__)
' 2>/dev/null || echo "ERROR curl")
  case "$r" in
    TERMINADO*) echo "$r"; exit 0;;
  esac
  sleep 45
done
echo "SIN VEREDICTO de Quality tras 90 min sobre $HEAD: evento perdido, hay que mirarlo a mano"
