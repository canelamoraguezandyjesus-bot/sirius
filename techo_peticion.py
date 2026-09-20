"""Techo REAL (con RF-25 puesto) de la configuracion «peticion declarada».

Reutiliza _medir del guion de diagnostico -- misma importacion que el guion
hace de si mismo, para no acabar con dos objetos de modulo distintos, que es
el fallo que ya me costo una medicion esta noche. La asercion del propio
guion (el filtro tiene que ver 47 consultas) es el guardian: si la identidad
del modulo fuera otra, `entradas` vendria vacia y esto para en rojo.
"""
import json, sys
from pathlib import Path
RAIZ = Path('/home/user/sirius')
sys.path.insert(0, str(RAIZ / 'scripts'))
import diagnosticar_busqueda_del_banco as diag

banco = json.loads((RAIZ / 'tests/acceptance/fixtures/evidence_bank_47_casos.json').read_text(encoding='utf-8'))
casos = banco['casos']
prot = {i['id'] for i in banco['items'] if i['criticidad'] is not None}
solo_crit = {i['id'] for i in banco['items'] if (i['criticidad'] or {}).get('nivel') == 'CRITICO'}

def techo(conjuntos, protegidas):
    """Un filtro perfecto conserva esp&cand; RF-25 le devuelve las protegidas
    que tiro, salvo que su veredicto fuera vacio (RF-26)."""
    n = 0
    bloq = []
    for caso, cand in zip(casos, conjuntos, strict=True):
        esp = set(caso['resultado_esperado'])
        if esp - cand:
            continue                      # la busqueda no lo trae: no cuenta aqui
        perf = esp & cand
        entregado = (perf | ((cand - perf) & protegidas)) if perf else perf
        if entregado == esp:
            n += 1
        else:
            bloq.append((caso['id'], sorted((cand - perf) & protegidas)))
    return n, bloq

for etiqueta, kw in (('--peticion', dict(con_ejes=False, con_peticion=True)),
                     ('--ejes --peticion', dict(con_ejes=True, con_peticion=True))):
    ejec, entradas, llamadas, _ = diag._medir(banco, con_cupo=False, motor_por_etapas=True, **kw)
    assert len(entradas) == len(casos), f'el filtro vio {len(entradas)} consultas, no {len(casos)}'
    conjuntos = [{ejec.real_a_canonico[c] for c in e if c in ejec.real_a_canonico} for e in entradas]
    trae_todo = sum(1 for c, cand in zip(casos, conjuntos, strict=True)
                    if not set(c['resultado_esperado']) - cand)
    t_hoy, bloq = techo(conjuntos, prot)
    t_crit, _ = techo(conjuntos, solo_crit)
    t_sin, _ = techo(conjuntos, set())
    print('=' * 74)
    print(f'[{etiqueta}]  exactos sin filtro: {ejec.metricas.aciertos_exactos}/47')
    print(f'  techo INGENUO (la busqueda trae el esperado entero) ..... {trae_todo}/47')
    print(f'  techo REAL con el candado de hoy (CRITICO+IMPORTANTE) ... {t_hoy}/47')
    print(f'  techo si protegiera solo CRITICO ........................ {t_crit}/47')
    print(f'  techo sin rescate ninguno ............................... {t_sin}/47')
    print(f'  casos que el rescate hace imposibles: {len(bloq)}')
    for cid, forz in bloq:
        print(f'     {cid}  fuerza {forz}')
