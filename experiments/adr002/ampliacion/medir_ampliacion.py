"""Medir si un modelo CIEGO se inventa las palabras tan bien como las escribi yo.

    python -m experiments.adr002.ampliacion.medir_ampliacion

LA PREGUNTA
===========

La ampliacion de consulta es lo unico que ha movido el resultado en `ADR-002`:
24/47 aciertos y 11 omisiones criticas pasan a 26/47 y 7. Pero las palabras las
escribi a mano, caso por caso, **habiendo visto ya las respuestas esperadas de
rondas anteriores**. El propio artefacto lo declara y deja la hipotesis
pendiente: «en produccion las escribiria el modelo de Sirius, que no ve el
banco».

Esto la comprueba. El modelo recibe **solo el texto de la pregunta**. Si iguala
el 26/47, la tabla escrita a mano se puede tirar. Si no lo iguala, la diferencia
mide exactamente cuanto de aquel resultado venia de que yo ya sabia la respuesta.

LAS DOS POLITICAS, PORQUE LA DIFERENCIA IMPORTA
===============================================

Ampliar **siempre** cuesta una llamada por busqueda; ampliar **solo cuando la
primera busqueda no basto** cuesta 21 de 47 y, con la tabla, deja 25/47 y 8
omisiones en vez de 26/47 y 7. Se miden las dos con el modelo porque la
eleccion entre ellas decide si Sirius sigue siendo utilizable sin conexion.

LO QUE SALE DE LA MAQUINA
=========================

El texto de cada consulta del banco, una vez por consulta distinta. Ni el canon,
ni identidades, ni criticidad, ni resultados esperados. Las consultas son
preguntas inventadas sobre un corpus inventado.

LO QUE SE TRAE DE VUELTA
========================

Un fichero con las cifras **y con las palabras que el modelo genero**, para que
se pueda juzgar si son sinonimos naturales o estan dirigidas a acertar —el
mismo escrutinio al que se sometio la tabla escrita a mano—.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final

from experiments.adr002.ampliacion import fuente as fu
from experiments.adr002.ampliacion.expansor import Expansor, Politica, recuperar_con_ampliacion
from experiments.adr002.ampliacion.modelo import MODELO_POR_DEFECTO, SinonimosDeModelo
from experiments.adr002.candidates.adr002_a.candidate import CandidatoA
from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.port import PuertoSqlite
from experiments.adr002.projection import build
from experiments.adr002.projection.contracts import Plano
from experiments.adr002.projection.plane import PlanoReservado
from experiments.adr002.round import cases as cs
from experiments.adr002.round import metrics as mt
from experiments.adr002.round import participants as pt
from experiments.adr002.round.execute_round import _criticos_del_canon

#: Las cifras publicadas. Si la corrida no las reproduce, el entorno cambio y la
#: comparacion no vale: se comprueba en vez de darse por supuesto.
BASE_PUBLICADA: Final = {"exactos": 24, "omisiones": 11}
TABLA_PUBLICADA: Final = {"exactos": 26, "omisiones": 7}

RUTA_TABLA: Final = Path("artifacts/adr002_round/ampliacion_de_consulta_v0.1.json")


def _fila(nombre: str, veredictos: list[Any], llamadas: int, fuente: str) -> dict[str, Any]:
    resumen = mt.resumir(nombre, veredictos, borrado_y_regeneracion=True)
    ausencias = sum(1 for v in veredictos if v.adjudicable and v.ausencia_correcta)
    adjudicables = len([v for v in veredictos if v.adjudicable])
    fila = {
        "corrida": nombre,
        #: De quien salieron las palabras. Sin esto, «50 llamadas» se lee como
        #: coste tambien en las filas cuya fuente es local y gratuita.
        "fuente": fuente,
        "exactos": resumen.casos_con_resultado_exacto,
        "casos": adjudicables,
        "omisiones_criticas": resumen.criticos_pendientes_total,
        "contaminacion": resumen.contaminacion_total,
        "fuga_de_ambito": resumen.fuga_de_ambito_total,
        "etapa_conforme": resumen.casos_con_etapa_conforme,
        "etapa_puntuable": resumen.casos_con_etapa_puntuable,
        "ausencia_correcta": ausencias,
        "llamadas_a_la_fuente": llamadas,
    }
    print(
        f"  {nombre:38} exactos={fila['exactos']}/{adjudicables} "
        f"omis={fila['omisiones_criticas']:2} contam={fila['contaminacion']} "
        f"FUGA={fila['fuga_de_ambito']} "
        f"etapa={fila['etapa_conforme']}/{fila['etapa_puntuable']} "
        f"ausencia_ok={ausencias}/{adjudicables} llamadas={llamadas}"
    )
    return fila


def main() -> int:
    analizador = argparse.ArgumentParser(description="Ampliacion de consulta: tabla contra modelo")
    analizador.add_argument("--modelo", default=MODELO_POR_DEFECTO)
    analizador.add_argument("--salida", type=Path, default=Path("resultado_ampliacion.json"))
    argumentos = analizador.parse_args()

    raiz = Path(__file__).resolve().parents[3]
    casos = cs.casos_ejecutables(cs.cargar_artefactos())
    familia = build.cargar_familia()
    proyectos = pt.proyectos_del_canon(familia[cs.CORPUS])
    polaridades = pt.polaridades_del_canon(familia[cs.CORPUS])
    criticos = _criticos_del_canon(familia["applied_criticality_v0_1.json"]["valores"])
    consultas = {c.identificador: c.peticion.consulta for c in casos}

    tabla = fu.SinonimosDeTabla.desde_artefacto(raiz / RUTA_TABLA, consultas)
    print(f"modelo: {argumentos.modelo}")
    print(f"consultas distintas que se enviaran: {len(set(consultas.values()))}")
    print("no se envia el canon, ni identidades, ni criticidad, ni resultados esperados.")
    print()

    filas: list[dict[str, Any]] = []
    palabras_generadas: dict[str, list[str]] = {}

    with tempfile.TemporaryDirectory() as temporal:
        proyeccion = build.construir_desde_la_familia(Path(temporal) / "planos")
        puerto = PuertoSqlite(proyeccion.ruta_de_entrada(), proyeccion.ruta(Plano.EJES_P2))
        plano = PlanoReservado(proyeccion)
        candidato = CandidatoA()

        def medir(nombre: str, hacer_expansor: Callable[[], Expansor]) -> dict[str, Any]:
            expansor = hacer_expansor()
            veredictos: list[Any] = []
            for caso in casos:
                recuperacion, ampliacion = recuperar_con_ampliacion(
                    caso.peticion,
                    lambda p: engine.recuperar(p, puerto, candidato, plano),
                    expansor,
                )
                if ampliacion.palabras_anadidas:
                    palabras_generadas.setdefault(
                        f"{expansor.identificador_de_la_fuente}|{caso.peticion.consulta}",
                        list(ampliacion.palabras_anadidas),
                    )
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
                        fuga_de_ambito=mt.fuga_de_ambito(ids, caso, proyectos),
                        confusion_de_polaridad=mt.confusion_de_polaridad(
                            ids,
                            {r.item.id: r.lectura.polaridad for r in recuperacion.resultados},
                            polaridades,
                        ),
                        polaridad_mal_leida=(),
                        etapa_conforme=conforme,
                        razon_de_etapa=razon,
                        etapa_puntua=not caso.etapa_inconsistente,
                        resultado_exacto=tuple(sorted(ids))
                        == tuple(sorted(caso.resultado_esperado)),
                        declara_orden=caso.declara_orden,
                        orden_exacto=caso.declara_orden and ids == caso.orden_esperado,
                        ausencia_correcta=mt.ausencia_correcta(
                            caso, ids, recuperacion.estado_externo
                        ),
                        criticos_pendientes=mt.criticos_pendientes(caso, ids, criticos),
                        explicaciones_completas=0,
                        resultados_totales=len(ids),
                        suficiencia=recuperacion.suficiencia.value,
                        estado_externo=recuperacion.estado_externo,
                        parada=recuperacion.parada.identificador,
                        etapas_recorridas=tuple(p.etapa.value for p in recuperacion.traza.pasos),
                    )
                )
            return _fila(
                nombre,
                veredictos,
                expansor.llamadas_a_la_fuente,
                expansor.identificador_de_la_fuente,
            )

        try:
            print("=== controles: sin ampliar, y con la tabla escrita a mano ===")
            base = medir("sin ampliar (linea base)", lambda: Expansor(fu.SinonimosNulos()))
            filas.append(base)
            con_tabla = medir("tabla a mano, ampliar SIEMPRE", lambda: Expansor(tabla))
            filas.append(con_tabla)
            filas.append(
                medir(
                    "tabla a mano, solo si no basto",
                    lambda: Expansor(tabla, Politica.SI_NO_BASTO),
                )
            )

            desviado = []
            if base["exactos"] != BASE_PUBLICADA["exactos"]:
                desviado.append(f"base exactos {base['exactos']} != {BASE_PUBLICADA['exactos']}")
            if con_tabla["exactos"] != TABLA_PUBLICADA["exactos"]:
                desviado.append(
                    f"tabla exactos {con_tabla['exactos']} != {TABLA_PUBLICADA['exactos']}"
                )
            if desviado:
                print()
                print("  AVISO: no se reproducen las cifras publicadas:", "; ".join(desviado))
                print("  la comparacion de abajo no es contra la ronda publicada.")
            print()

            print("=== el modelo, viendo SOLO el texto de cada pregunta ===")
            modelo = SinonimosDeModelo(modelo=argumentos.modelo)
            filas.append(medir("modelo, ampliar SIEMPRE", lambda: Expansor(modelo)))
            filas.append(
                medir(
                    "modelo, solo si no basto",
                    lambda: Expansor(modelo, Politica.SI_NO_BASTO),
                )
            )
        finally:
            puerto.close()
            plano.close()

    artefacto = {
        "que_es": (
            "ampliacion de consulta generada por un modelo ciego, medida contra "
            "la tabla escrita a mano sobre el banco de ADR-002"
        ),
        "modelo": argumentos.modelo,
        "cifras_publicadas": {"sin_ampliar": BASE_PUBLICADA, "tabla_a_mano": TABLA_PUBLICADA},
        "lo_que_vio_el_modelo": "unicamente el texto de cada consulta",
        "filas": filas,
        "palabras_por_consulta": palabras_generadas,
    }
    argumentos.salida.write_text(
        json.dumps(artefacto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print()
    print(f"resultados escritos en {argumentos.salida.resolve()}")
    print("incluye las palabras que genero el modelo, para poder juzgarlas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
