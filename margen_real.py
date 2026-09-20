"""Cuanto margen le queda de verdad al filtro, con el rescate puesto.

Se aplica la formula EXACTA del arnes (aplicar_regla_de_criticas_original),
bajo el supuesto explicito candidatos == entraron_al_filtro (es lo unico que
la grabacion deja ver). Con ese supuesto, entregado = conservados | rescatadas.
"""
import json

B = json.load(open('tests/acceptance/fixtures/evidence_bank_47_casos.json', encoding='utf-8'))
G = json.load(open('tests/acceptance/fixtures/relevance_filter_frozen_run.json', encoding='utf-8'))
prot = {i['id'] for i in B['items'] if i['criticidad'] is not None}
texto = {i['id']: i['text'] for i in B['items']}
print(f'identidades protegidas (criticidad no nula): {len(prot)} de {len(B["items"])}')
print()

hoy = alcanzable = 0
ganables, bloqueados, ya_ok = [], [], []
for caso in B['casos']:
    cid = caso['id']
    esp = set(caso['resultado_esperado'])
    ent = set(G['casos'].get(cid, {}).get('entraron_al_filtro', []))
    cons = set(G['casos'].get(cid, {}).get('conservados_por_el_modelo', []))
    # arnes: si no conservo nada, RF-26 respeta el vacio; si conservo, rescata protegidas
    entregado = cons if not cons else cons | ((ent - cons) & prot)
    es_exacto = (entregado == esp)
    hoy += es_exacto
    # techo: filtro perfecto -> conserva exactamente esp&ent
    perf = esp & ent
    techo_entregado = perf if not perf else perf | ((ent - perf) & prot)
    puede = (techo_entregado == esp)
    alcanzable += puede
    if puede and not es_exacto:
        ganables.append((cid, caso['consulta'], sorted(entregado ^ esp)))
    elif not puede:
        bloqueados.append((cid, caso['consulta'], sorted(techo_entregado - esp), sorted(esp - ent)))

print('=' * 74)
print(f'  EXACTOS HOY con la grabacion ............ {hoy}/47')
print(f'  TECHO con filtro perfecto y rescate ..... {alcanzable}/47')
print(f'  MARGEN QUE LE QUEDA AL FILTRO ........... {alcanzable - hoy} casos')
print('=' * 74)
print()
print(f'GANABLES mejorando el filtro ({len(ganables)}):')
for cid, q, dif in ganables:
    print(f'  {cid}  {q[:50]}')
    for m in dif:
        print(f'      difiere: {m} {texto[m][:58]}')
print()
print(f'BLOQUEADOS aunque el filtro fuera perfecto ({len(bloqueados)}):')
for cid, q, forz, falta in bloqueados:
    razon = []
    if forz: razon.append(f'rescate fuerza {forz}')
    if falta: razon.append(f'no entro {falta}')
    print(f'  {cid}  {q[:44]:46} {"; ".join(razon)[:70]}')
