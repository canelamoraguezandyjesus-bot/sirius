"""Techo real con la ampliacion por criticidad APAGADA. Solo mide; restaura."""
import json, sys
from pathlib import Path
RAIZ = Path('/home/user/sirius')
sys.path.insert(0, str(RAIZ / 'scripts'))
import diagnosticar_busqueda_del_banco as diag
import sirius.application.rank_relevant_knowledge as recuperacion

banco = json.loads((RAIZ / 'tests/acceptance/fixtures/evidence_bank_47_casos.json').read_text(encoding='utf-8'))
casos = banco['casos']
prot = {i['id'] for i in banco['items'] if i['criticidad'] is not None}

def analizar(conjuntos, protegidas):
    trae, techo, bloq, sin_esperado = 0, 0, [], []
    for caso, cand in zip(casos, conjuntos, strict=True):
        esp = set(caso['resultado_esperado'])
        falta = esp - cand
        if falta:
            sin_esperado.append((caso['id'], sorted(falta)))
            continue
        trae += 1
        perf = esp & cand
        entregado = (perf | ((cand - perf) & protegidas)) if perf else perf
        if entregado == esp: techo += 1
        else: bloq.append(caso['id'])
    return trae, techo, bloq, sin_esperado

def medir(etiqueta, kw, apagar):
    original = recuperacion.category_index_activated
    if apagar:
        # solo_por_criticidad se enciende con el vocabulario de criticidad;
        # solo_por_categoria usa el de categoria. Se apaga SOLO la llamada que
        # usa el vocabulario de criticidad, comparando el objeto vocabulario.
        def parche(query_text, vocabulario):
            if vocabulario is _VOCAB_CRIT: return False
            return original(query_text, vocabulario)
        recuperacion.category_index_activated = parche
    try:
        ejec, entradas, _, _ = diag._medir(banco, con_cupo=False, motor_por_etapas=True, **kw)
    finally:
        recuperacion.category_index_activated = original
    assert len(entradas) == len(casos), f'el filtro vio {len(entradas)}, no {len(casos)}'
    conj = [{ejec.real_a_canonico[c] for c in e if c in ejec.real_a_canonico} for e in entradas]
    return ejec, analizar(conj, prot)

# el vocabulario de criticidad, tal como lo ve el caso de uso
_VOCAB_CRIT = None
_orig_init = recuperacion.RankRelevantKnowledgeUseCase.__init__
def _captura(self, *a, **k):
    global _VOCAB_CRIT
    _orig_init(self, *a, **k)
    _VOCAB_CRIT = self._criticality_vocabulary
recuperacion.RankRelevantKnowledgeUseCase.__init__ = _captura

for etiqueta, kw in (('--peticion', dict(con_ejes=False, con_peticion=True)),
                     ('--ejes --peticion', dict(con_ejes=True, con_peticion=True))):
    ej0, (t0, c0, b0, s0) = medir(etiqueta, kw, apagar=False)
    assert _VOCAB_CRIT is not None, 'no se capturo el vocabulario de criticidad'
    ej1, (t1, c1, b1, s1) = medir(etiqueta, kw, apagar=True)
    print('=' * 74)
    print(f'[{etiqueta}]')
    print(f'{"":28} {"ampliacion ON":>14} {"ampliacion OFF":>15}')
    print(f'{"  exactos sin filtro":28} {ej0.metricas.aciertos_exactos:>11}/47 {ej1.metricas.aciertos_exactos:>12}/47')
    print(f'{"  elementos de mas":28} {ej0.metricas.elementos_de_mas:>14} {ej1.metricas.elementos_de_mas:>15}')
    print(f'{"  hallados /81":28} {ej0.metricas.elementos_hallados:>14} {ej1.metricas.elementos_hallados:>15}')
    print(f'{"  omisiones criticas":28} {ej0.metricas.omisiones_criticas:>14} {ej1.metricas.omisiones_criticas:>15}')
    print(f'{"  la busqueda trae todo":28} {t0:>11}/47 {t1:>12}/47')
    print(f'{"  TECHO REAL (RF-25)":28} {c0:>11}/47 {c1:>12}/47')
    print(f'{"  bloqueados por rescate":28} {len(b0):>14} {len(b1):>15}')
    print(f'  bloqueados ON : {b0}')
    print(f'  bloqueados OFF: {b1}')
    perdidos = [cid for cid, _ in s1 if cid not in {c for c, _ in s0}]
    print(f'  CASOS QUE PIERDEN esperado al apagar: {len(perdidos)} {perdidos}')
    for cid, falta in s1:
        if cid in perdidos: print(f'      {cid} deja de traer {falta}')
