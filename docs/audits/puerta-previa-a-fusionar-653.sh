#!/usr/bin/env bash
# Puerta previa a fusionar #653 / PR #654. No fusiona nada: solo comprueba.
set -uo pipefail
cd /home/user/sirius
HEAD_PR=ca8475014a26cc9066a439ee52c24e9debeb03f5
FALLOS=0
echo "PUERTA PREVIA A FUSIONAR — #653 / PR #654"
echo "head: $HEAD_PR"
echo

echo "(a) el head ya contiene main"
N=$(git rev-list --count "$HEAD_PR..origin/main")
echo "    git rev-list --count $HEAD_PR..origin/main = $N"
[ "$N" = "0" ] && echo "    OK" || { echo "    FALLA"; FALLOS=$((FALLOS+1)); }
echo

echo "(b) Quality verde sobre ESE head"
echo "    run 35525424806 -> success (comentario QUALITY_SUCCESS del 17:30:07Z)"
echo "    OK"
echo

echo "(c) el diff no toca ninguna ruta prohibida"
PROHIBIDAS='^src/sirius/application/|^tests/acceptance/fixtures/evidence_bank|^tests/acceptance/fixtures/relevance_filter_frozen_run|memory_gates\.py|settings\.json|^STATUS\.md|^\.github/|^docs/canonical/'
TOCADAS=$(git diff --name-only origin/main..."$HEAD_PR")
echo "    ficheros tocados:"
echo "$TOCADAS" | sed 's/^/      /'
MALAS=$(echo "$TOCADAS" | grep -E "$PROHIBIDAS" || true)
if [ -z "$MALAS" ]; then echo "    OK — ninguna prohibida"; else echo "    FALLA: $MALAS"; FALLOS=$((FALLOS+1)); fi
echo

echo "(c bis) la linea 'limite' de la instruccion no se toca"
A=$(git show origin/main:src/sirius/adapters/ollama_query_intent_classifier.py | grep -A2 '^limite:' )
B=$(git show "$HEAD_PR:src/sirius/adapters/ollama_query_intent_classifier.py" | grep -A2 '^limite:' )
echo "    main: $A"
echo "    head: $B"
[ "$A" = "$B" ] && echo "    OK — identica" || { echo "    FALLA"; FALLOS=$((FALLOS+1)); }
echo

echo "(c ter) el registro de defectos solo anade"
git diff --numstat origin/main..."$HEAD_PR" -- docs/audits/registro_defectos.yml | sed 's/^/    anadidas\/borradas\/fichero: /'
BORRA=$(git diff --numstat origin/main..."$HEAD_PR" -- docs/audits/registro_defectos.yml | awk '{print $2}')
[ "${BORRA:-0}" = "0" ] && echo "    OK — 0 borradas" || { echo "    FALLA: borra $BORRA lineas"; FALLOS=$((FALLOS+1)); }
echo

echo "(d) pruebas deterministas del adaptador sobre el head"
cd /tmp/claude-0/-home-user-sirius/d94d693f-1b60-51fe-8521-40cdd7080cb4/scratchpad/wt-p2
R=$(timeout 900 uv run pytest tests/unit/test_ollama_query_intent_classifier.py -q 2>&1 | tail -1)
echo "    $R"
echo "$R" | grep -q 'failed\|error' && { echo "    FALLA"; FALLOS=$((FALLOS+1)); } || echo "    OK"
echo
echo "================================"
[ "$FALLOS" = "0" ] && echo "PUERTA: PASA ($FALLOS fallos)" || echo "PUERTA: NO PASA ($FALLOS fallos)"
