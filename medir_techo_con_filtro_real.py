"""El techo real: peticion DECLARADA del corpus + filtro de relevancia REAL.

POR QUE EXISTE
==============

Ninguna medicion ha juntado nunca las dos cosas:

- `scripts/medir_banco_con_ollama_real.py` usa el filtro real, pero con la
  peticion FIJA (la politica de hoy). Da 8/47; 218; 0 criticas; 70/81.
- `scripts/diagnosticar_busqueda_del_banco.py --peticion` usa la peticion
  declarada, pero SIN filtro. Da 17/47; 162; 0 criticas; 78/81.

Falta la esquina que decide el mapa entero: **con la mejor peticion posible y
el filtro real puesto, que sale?** Esa cifra responde a si el suelo de D1
(29/47) esta al alcance arreglando el interprete, o si hace falta algo mas.

La entrada 120 de la bitacora lo dejo dicho: con la peticion declarada la
busqueda sola da 17/47 y el suelo es 29/47, asi que el interprete es necesario
pero no suficiente. Lo que ese 17/47 no dice es cuanto de los 162 elementos de
mas se lleva el filtro. Si se llevara casi todos, el panorama cambia.

QUE HACE
========

Reutiliza los dos arneses que ya existen, sin reimplementar nada: la
sustitucion de la peticion de `diagnosticar_busqueda_del_banco._medir` y el
adaptador real de `medir_banco_con_ollama_real`. Solo los junta.

NO toca `src/`, ni el corpus, ni ninguna adjudicacion.

USO
===

    uv run python medir_techo_con_filtro_real.py
    uv run python medir_techo_con_filtro_real.py --modelo llama3.2 --espera 60

QUE MIRAR
=========

`rendiciones` tiene que ser 0. Si no, la medicion esta contaminada y no vale.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(_RAIZ / "tests" / "acceptance"))
sys.path.insert(0, str(_RAIZ / "scripts"))

import diagnosticar_busqueda_del_banco as diag  # noqa: E402
import medir_banco_con_ollama_real as real  # noqa: E402
from sirius.adapters.ollama_relevance_filter import OllamaRelevanceFilterAdapter  # noqa: E402

_BANCO = _RAIZ / "tests" / "acceptance" / "fixtures" / "evidence_bank_47_casos.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", default="qwen3:4b-instruct")
    parser.add_argument("--espera", type=float, default=30.0)
    args = parser.parse_args()

    banco = json.loads(_BANCO.read_text(encoding="utf-8"))
    contador = real._FiltroQueSeDejaContar(
        OllamaRelevanceFilterAdapter(args.modelo, timeout_seconds=args.espera)
    )

    print(f"Modelo: {args.modelo}   Espera: {args.espera:g} s")
    print("Peticion DECLARADA del corpus + filtro REAL. Tarda varios minutos.\n")

    # `_medir` construye su propio doble del filtro; aqui se sustituye por el
    # puerto real en el MISMO objeto de modulo que `diag` usa.
    #
    # `diag.arnes`, no un import propio: el arnes se puede importar por dos
    # rutas —`tests.acceptance.test_...` y `test_...` a secas— y Python crea
    # DOS objetos de modulo distintos. Parchear el que no es deja el filtro
    # real sin conectar y la medicion sale identica a la de sin filtro, con
    # `llamadas al filtro = 0` como unica pista. Visto fallar.
    arnes = diag.arnes
    arnes_original = arnes._ejecutar_banco_paquete_completo

    def con_filtro_real(ruta, **kw):
        kw["relevance_filter_port"] = contador
        return arnes_original(ruta, **kw)

    arnes._ejecutar_banco_paquete_completo = con_filtro_real
    comienzo = time.monotonic()
    try:
        ejecucion, _entradas, llamadas, _puertos = diag._medir(
            banco, con_ejes=False, con_peticion=True
        )
    finally:
        arnes._ejecutar_banco_paquete_completo = arnes_original
    duracion = time.monotonic() - comienzo

    m = ejecucion.metricas
    print("=" * 66)
    print("TECHO REAL: peticion declarada + filtro de Ollama")
    print("=" * 66)
    print(f"  Aciertos exactos ...... {m.aciertos_exactos}/47   (suelo D1: 29/47)")
    print(f"  Omisiones criticas .... {m.omisiones_criticas}     (suelo D1: 1 o menos)")
    print(f"  Cobertura ............. {m.elementos_hallados}/81  (suelo D1: 63)")
    print(f"  Elementos de mas ...... {m.elementos_de_mas}")
    print()
    print(f"  Tiempo ................ {duracion / 60:.1f} min")
    print(f"  Llamadas al filtro .... {contador.llamadas}")
    print(f"  Rendiciones ........... {contador.rendiciones}", end="")
    print("   <- si no es 0, la medicion NO VALE" if contador.rendiciones else "   OK")
    if contador.llamadas == 0:
        print("\n  AVISO: el filtro no se llamo ni una vez. El puerto real NO quedo\n  conectado y estas cifras son las de SIN FILTRO. La medicion no vale.")
    print()
    print("  Para comparar:")
    print("    peticion fija  + filtro real :  8/47; 218 de mas; 0 criticas; 70/81")
    print("    peticion declarada SIN filtro: 17/47; 162 de mas; 0 criticas; 78/81")
    print("=" * 66)

    _desglose(banco, ejecucion)
    return 0


def _desglose(banco, ejecucion) -> None:
    """Separa el exceso DECIDIDO del que nadie decidio (entrada 136).

    `aciertos_exactos` exige conjunto IDENTICO al esperado, asi que un solo
    protegido de mas suspende el caso -- y ADR-128 manda meterlo. Las dos
    reglas no pueden cumplirse a la vez, y hasta ahora solo se imprimia una.
    Esto imprime las dos al lado, para que la decision D-1 de
    `docs/audits/decisiones-abiertas-del-propietario.md` se pueda tomar con
    datos de esta maquina y este modelo, en vez de con los de la grabacion.

    NO es una metrica nueva del banco y no sustituye a nada: el numero que
    cuenta sigue siendo `aciertos_exactos`, impreso arriba.
    """
    protegidas = {i["id"] for i in banco["items"] if i["criticidad"] is not None}
    falta_algo = solo_protegido = sobra_no_decidido = 0
    elementos_no_decididos = 0
    casos_no_decididos: list[tuple[str, int]] = []
    for caso in banco["casos"]:
        esperado = set(caso["resultado_esperado"])
        entregado = set(ejecucion.obtenido_por_caso.get(caso["id"], ()))
        if esperado - entregado:
            falta_algo += 1
            continue
        sobra_sin_decidir = (entregado - esperado) - protegidas
        if sobra_sin_decidir:
            sobra_no_decidido += 1
            elementos_no_decididos += len(sobra_sin_decidir)
            casos_no_decididos.append((caso["id"], len(sobra_sin_decidir)))
        else:
            solo_protegido += 1
    print()
    print("=" * 66)
    print("DESGLOSE: que clase de fallo es cada suspenso  (NO es otra metrica)")
    print("=" * 66)
    print(f"  Le falta algo esperado ............... {falta_algo}/47"
          "   <- fallo por cualquier regla")
    print(f"  No le falta nada y solo sobra")
    print(f"    alguna PROTEGIDA (ADR-128 la manda)  {solo_protegido}/47"
          "   <- exceso DECIDIDO")
    print(f"  No le falta nada pero sobra algo que")
    print(f"    nadie decidio ...................... {sobra_no_decidido}/47"
          f"   ({elementos_no_decididos} elementos)")
    if casos_no_decididos:
        peores = sorted(casos_no_decididos, key=lambda x: -x[1])[:5]
        print("    los casos con mas exceso sin decidir: "
              + ", ".join(f"{cid} (+{n})" for cid, n in peores))
    print()
    print("  Sobre la grabacion congelada esto daba 9 / 36 / 2 (entrada 136).")
    print("  El del MEDIO es cuantos casos pasarian si la regla perdonase la")
    print("  critica de mas -- los del tercero seguirian suspendiendo, porque su")
    print("  exceso no lo decidio nadie. Es la decision D-1, y es de Andy.")
    print("=" * 66)


if __name__ == "__main__":
    raise SystemExit(main())
