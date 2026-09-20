import json, sys
from pathlib import Path
RAIZ = Path('/home/user/sirius'); sys.path.insert(0, str(RAIZ/'scripts'))
import diagnosticar_busqueda_del_banco as diag
banco = json.loads((RAIZ/'tests/acceptance/fixtures/evidence_bank_47_casos.json').read_text(encoding='utf-8'))
casos = banco['casos']
out={}
for etiqueta, kw in (('peticion', dict(con_ejes=False, con_peticion=True)),
                     ('ejes_peticion', dict(con_ejes=True, con_peticion=True)),
                     ('fija', dict(con_ejes=False, con_peticion=False))):
    ejec, entradas, _, _ = diag._medir(banco, con_cupo=False, motor_por_etapas=True, **kw)
    assert len(entradas)==len(casos)
    out[etiqueta] = {c['id']: sorted({ejec.real_a_canonico[x] for x in e if x in ejec.real_a_canonico})
                     for c, e in zip(casos, entradas, strict=True)}
json.dump(out, open('/tmp/claude-0/-home-user-sirius/d94d693f-1b60-51fe-8521-40cdd7080cb4/scratchpad/candidatas.json','w',encoding='utf-8'), ensure_ascii=False)
print('volcadas las tres configuraciones')
