"""Que techo daria cada definicion de 'protegida'. Solo aritmetica sobre la
grabacion y el banco; ningun cambio de codigo, ninguna propuesta."""
import json
B = json.load(open('tests/acceptance/fixtures/evidence_bank_47_casos.json', encoding='utf-8'))
G = json.load(open('tests/acceptance/fixtures/relevance_filter_frozen_run.json', encoding='utf-8'))
nivel = {i['id']: (i['criticidad'] or {}).get('nivel') for i in B['items']}
texto = {i['id']: i['text'] for i in B['items']}

def evaluar(prot):
    hoy = techo = 0
    bloq = []
    for caso in B['casos']:
        cid = caso['id']
        esp = set(caso['resultado_esperado'])
        ent = set(G['casos'].get(cid, {}).get('entraron_al_filtro', []))
        cons = set(G['casos'].get(cid, {}).get('conservados_por_el_modelo', []))
        hoy += ((cons | ((ent - cons) & prot)) if cons else cons) == esp
        perf = esp & ent
        te = (perf | ((ent - perf) & prot)) if perf else perf
        if te == esp: techo += 1
        elif not (esp - ent): bloq.append(cid)
    return hoy, techo, bloq

TODAS = {i for i in nivel if nivel[i] is not None}
SOLO_CRIT = {i for i in nivel if nivel[i] == 'CRITICO'}
print(f'protegidas CRITICO+IMPORTANTE ... {len(TODAS)}   (lo que hay hoy, ADR-128/M19b)')
print(f'protegidas solo CRITICO ......... {len(SOLO_CRIT)}')
print(f'la unica IMPORTANTE ............. {sorted(TODAS-SOLO_CRIT)} -> {texto[sorted(TODAS-SOLO_CRIT)[0]]}')
print()
print(f'{"definicion de protegida":36} {"exactos hoy":>12} {"techo":>8} {"bloquea":>9}')
for nombre, p in (('CRITICO + IMPORTANTE (hoy)', TODAS), ('solo CRITICO', SOLO_CRIT), ('ninguna (sin rescate)', set())):
    h, t, b = evaluar(p)
    print(f'{nombre:36} {h:>9}/47 {t:>5}/47 {len(b):>9}')
print()
h1,t1,b1 = evaluar(TODAS); h2,t2,b2 = evaluar(SOLO_CRIT)
print(f'casos que desbloquea quitar IMPORTANTE del rescate: {sorted(set(b1)-set(b2))}')
