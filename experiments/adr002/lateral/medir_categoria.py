"""Mide que aporta hacer buscable la categoria. Sin modelo y sin red.

    python -m experiments.adr002.lateral.medir_categoria

Esta medicion **no necesita Ollama**, no gasta ninguna llamada y es
determinista: dos corridas sobre el mismo canon dan lo mismo. Por eso se separa
de `modelo_local/medir.py`, que si lo necesita: mezclarlas obligaria a tener el
modelo encendido para comprobar algo que no depende de el.

Lo que se contrasta son dos corridas:

1. la busqueda tal cual, que es la linea base publicada;
2. mas la categoria buscable.

Y lo que se mira son **las once omisiones criticas** que quedaron tras la
corrida v0.4, porque de esas seis son de categoria y las otras cinco no. Se
publican las once una por una, con su causa, para que se vea cuales se mueven y
cuales no.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

from experiments.adr002.candidates.adr002_a.candidate import CandidatoA
from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.port import PuertoSqlite
from experiments.adr002.lateral import categoria as cat
from experiments.adr002.projection import build
from experiments.adr002.projection.contracts import Plano
from experiments.adr002.projection.plane import PlanoReservado
from experiments.adr002.round import cases as cs
from experiments.adr002.round import metrics as mt
from experiments.adr002.round import participants as pt
from experiments.adr002.round.execute_round import _criticos_del_canon

#: Las cifras publicadas de la linea base. Si no se reproducen, el entorno
#: cambio y la comparacion no vale: se comprueba, no se supone.
BASE_PUBLICADA: Final = {"exactos": 24, "omisiones": 11, "contaminacion": 3}

CRITICIDAD: Final = "applied_criticality_v0_1.json"


def _correr(
    casos: Sequence[Any], candidato: Any, puerto: Any, plano: Any, contexto: dict[str, Any]
) -> list[Any]:
    veredictos: list[Any] = []
    for caso in casos:
        recuperacion = engine.recuperar(caso.peticion, puerto, candidato, plano)
        ids = recuperacion.ids
        conforme, razon = mt.etapa_conforme(
            caso,
            tuple(p.etapa.value for p in recuperacion.traza.pasos),
            pt._etapa_de_resolucion(recuperacion),
        )
        veredictos.append(
            mt.VeredictoDeCaso(
                caso=caso.identificador,
                canonico=caso.canonico,
                adjudicable=caso.adjudicable,
                obtenido=ids,
                esperado=caso.resultado_esperado,
                contaminacion=mt.contaminacion(ids, caso),
                fuga_de_ambito=mt.fuga_de_ambito(ids, caso, contexto["proyectos"]),
                confusion_de_polaridad=mt.confusion_de_polaridad(
                    ids,
                    {r.item.id: r.lectura.polaridad for r in recuperacion.resultados},
                    contexto["polaridades"],
                ),
                polaridad_mal_leida=(),
                etapa_conforme=conforme,
                razon_de_etapa=razon,
                etapa_puntua=not caso.etapa_inconsistente,
                resultado_exacto=tuple(sorted(ids)) == tuple(sorted(caso.resultado_esperado)),
                declara_orden=caso.declara_orden,
                orden_exacto=caso.declara_orden and ids == caso.orden_esperado,
                ausencia_correcta=mt.ausencia_correcta(caso, ids, recuperacion.estado_externo),
                criticos_pendientes=mt.criticos_pendientes(caso, ids, contexto["criticos"]),
                explicaciones_completas=0,
                resultados_totales=len(ids),
                suficiencia=recuperacion.suficiencia.value,
                estado_externo=recuperacion.estado_externo,
                parada=recuperacion.parada.identificador,
                etapas_recorridas=tuple(p.etapa.value for p in recuperacion.traza.pasos),
            )
        )
    return veredictos


def _fila(nombre: str, veredictos: list[Any]) -> dict[str, Any]:
    resumen = mt.resumir(nombre, veredictos, borrado_y_regeneracion=True)
    adjudicables = [v for v in veredictos if v.adjudicable]
    con_contenido = [v for v in adjudicables if v.esperado]
    fila = {
        "corrida": nombre,
        "conjunto_exacto": resumen.casos_con_resultado_exacto,
        "casos_adjudicables": len(adjudicables),
        "lo_correcto_entra_entero": sum(
            1 for v in con_contenido if set(v.esperado) <= set(v.obtenido)
        ),
        "casos_con_contenido": len(con_contenido),
        "elementos_hallados": sum(len(set(v.esperado) & set(v.obtenido)) for v in con_contenido),
        "elementos_esperados": sum(len(v.esperado) for v in con_contenido),
        "elementos_de_mas": sum(len(set(v.obtenido) - set(v.esperado)) for v in con_contenido),
        "omisiones_criticas": resumen.criticos_pendientes_total,
        "contaminacion": resumen.contaminacion_total,
        "fuga_de_ambito": resumen.fuga_de_ambito_total,
        "ausencia_correcta": sum(1 for v in adjudicables if v.ausencia_correcta),
    }
    print(
        f"  {nombre:32} exacto={fila['conjunto_exacto']}/{fila['casos_adjudicables']}  "
        f"entra-entero={fila['lo_correcto_entra_entero']}/{fila['casos_con_contenido']}  "
        f"hallados={fila['elementos_hallados']}/{fila['elementos_esperados']}  "
        f"de-mas={fila['elementos_de_mas']}  omis={fila['omisiones_criticas']}  "
        f"fuga={fila['fuga_de_ambito']}"
    )
    return fila


def _omisiones(veredictos: list[Any]) -> dict[str, list[str]]:
    return {v.caso: list(v.criticos_pendientes) for v in veredictos if v.criticos_pendientes}


def main() -> int:
    analizador = argparse.ArgumentParser(description="Mide la categoria buscable, sin modelo")
    analizador.add_argument("--salida", type=Path, default=Path("resultado_categoria_v0.1.json"))
    analizador.add_argument("--sobrescribir", action="store_true")
    argumentos = analizador.parse_args()
    if argumentos.salida.exists() and not argumentos.sobrescribir:
        print(f"ERROR: «{argumentos.salida}» ya existe y no se pisa. Usa --sobrescribir.")
        return 2

    cabeza = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip()
    print(f"=== medido sobre HEAD {cabeza} ===")
    print("sin modelo, sin red, determinista")
    print()

    casos = cs.casos_ejecutables(cs.cargar_artefactos())
    familia = build.cargar_familia()
    corpus = familia[cs.CORPUS]
    contexto = {
        "proyectos": pt.proyectos_del_canon(corpus),
        "polaridades": pt.polaridades_del_canon(corpus),
        "criticos": _criticos_del_canon(familia[CRITICIDAD]["valores"]),
    }

    with tempfile.TemporaryDirectory() as temporal:
        proyeccion = build.construir_desde_la_familia(Path(temporal) / "planos")
        puerto = PuertoSqlite(proyeccion.ruta_de_entrada(), proyeccion.ruta(Plano.EJES_P2))
        plano = PlanoReservado(proyeccion)
        try:
            base = _correr(casos, CandidatoA(), puerto, plano, contexto)
            fila_base = _fila("1. busqueda tal cual", base)
            desviado = {
                c: (fila_base[k], v)
                for c, k, v in (
                    ("exactos", "conjunto_exacto", BASE_PUBLICADA["exactos"]),
                    ("omisiones", "omisiones_criticas", BASE_PUBLICADA["omisiones"]),
                    ("contaminacion", "contaminacion", BASE_PUBLICADA["contaminacion"]),
                )
                if fila_base[k] != v
            }
            if desviado:
                print("  AVISO: la linea base NO reproduce la publicada:", desviado)

            ruta = Path(temporal) / "categoria.sqlite3"
            registro = cat.construir(ruta, familia[CRITICIDAD]["valores"])
            con = _correr(casos, cat.ConCategoria(ruta), puerto, plano, contexto)
            fila_con = _fila("2. mas la categoria buscable", con)
            sembrado = _correr(
                casos,
                cat.ConCategoria(ruta, sembrar_en_contexto=True),
                puerto,
                plano,
                contexto,
            )
            fila_sembrado = _fila("3. y las criticas al ensamblar contexto", sembrado)
        finally:
            puerto.close()
            plano.close()

    antes, despues, final = _omisiones(base), _omisiones(con), _omisiones(sembrado)
    print()
    print("=== las omisiones criticas, una por una ===")
    for caso in sorted(antes):
        quedan = final.get(caso, [])
        marca = "RESUELTA" if not quedan else "sigue"
        print(
            f"  {caso:8} {marca:9} al empezar={len(antes[caso])}  "
            f"con categoria={len(despues.get(caso, []))}  al final={quedan or 0}"
        )

    artefacto = {
        "que_es": (
            "que aporta hacer buscable la categoria que el canon ya declara, "
            "sin modelo, sin red y de forma determinista"
        ),
        "commit": cabeza,
        "linea_base_publicada": BASE_PUBLICADA,
        "indice_de_categoria": registro,
        "filas": [fila_base, fila_con, fila_sembrado],
        "omisiones_criticas": {
            "antes": antes,
            "con_categoria": despues,
            "y_sembrando_en_contexto": final,
        },
        "estatuto_de_la_siembra": (
            "la regla de sembrar las criticas cuando la peticion declara que ensambla "
            "contexto se escribio DESPUES de ver que casos fallaban, y los dos unicos "
            "casos del banco con ese proposito son justo esos dos. El banco ya no puede "
            "confirmarla de forma independiente: se sostiene por diseno, no por medida"
        ),
    }
    argumentos.salida.write_text(
        json.dumps(artefacto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print()
    print(f"resultados escritos en {argumentos.salida.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
