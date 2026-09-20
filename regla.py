"""Separa el exceso DECIDIDO (protegidas) del exceso que nadie decidio.

Solo lee y cuenta. No toca el banco ni ninguna metrica del arnes.
NO se propone cambiar la metrica.
"""
import json, sys
from pathlib import Path
RAIZ = Path('/home/user/sirius')
sys.path.insert(0, str(RAIZ / 'scripts'))
import diagnosticar_busqueda_del_banco as diag

banco = json.loads((RAIZ / 'tests/acceptance/fixtures/evidence_bank_47_casos.json').read_text(encoding='utf-8'))
casos = banco['casos']
prot = {i['id'] for i in banco['items'] if i['criticidad'] is not None}

for etiqueta, kw in (('--peticion', dict(con_ejes=False, con_peticion=True)),
                     ('--ejes --peticion', dict(con_ejes=True, con_peticion=True))):
    ejec, entradas, _, _ = diag._medir(banco, con_cupo=False, motor_por_etapas=True, **kw)
    assert len(entradas) == len(casos), f'el filtro vio {len(entradas)}, no {len(casos)}'
    conj = [{ejec.real_a_canonico[c] for c in e if c in ejec.real_a_canonico} for e in entradas]

    nada_falta = solo_protegido = sobra_no_prot = 0
    elems_no_prot = 0
    casos_no_prot = []
    for caso, cand in zip(casos, conj, strict=True):
        esp = set(caso['resultado_esperado'])
        if esp - cand:
            continue
        nada_falta += 1
        sobra = cand - esp
        sobra_np = sobra - prot
        if not sobra_np:
            solo_protegido += 1
        else:
            sobra_no_prot += 1
            elems_no_prot += len(sobra_np)
            casos_no_prot.append((caso['id'], len(sobra_np), len(sobra & prot)))
    print('=' * 74)
    print(f'[{etiqueta}]   (esto es la ETAPA DE BUSQUEDA: el doble no descarta nada)')
    print(f'  aciertos exactos que publica el arnes ............... {ejec.metricas.aciertos_exactos}/47')
    print(f'  (1) no falta NADA de lo esperado .................... {nada_falta}/47')
    print(f'  (2) no falta nada y TODO lo que sobra es protegido .. {solo_protegido}/47')
    print(f'  (3) no falta nada pero sobra algo NO protegido ...... {sobra_no_prot}/47')
    print(f'  (4) elementos de mas NO protegidos ................. {elems_no_prot}'
          f'   (de {ejec.metricas.elementos_de_mas} de mas en total)')
    print(f'      los cinco casos con mas exceso no decidido:')
    for cid, n_np, n_p in sorted(casos_no_prot, key=lambda x: -x[1])[:5]:
        print(f'        {cid}  no protegidos={n_np:<4} protegidos={n_p}')
