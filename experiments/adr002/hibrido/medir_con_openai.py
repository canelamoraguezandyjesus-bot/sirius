"""Paso 3: medir la senal semantica REAL sobre el banco, en la maquina con clave.

    python -m experiments.adr002.hibrido.medir_con_openai

QUE PREGUNTA CONTESTA, Y POR QUE ES LA UNICA QUE QUEDA
=====================================================

Lo medido en el paso 2 dejo el terreno muy limpio, y descarto media hipotesis:

* el cauce hibrido corre entero sobre el banco real;
* fusionar con senal nula no mueve **ni un** resultado en los 47 casos, de modo
  que la fusion no introduce ruido propio;
* y el recorte por limite —la razon que se habia dado para preferir fusionar a
  concatenar— **no llega a morder en este banco**: 45 de 50 casos no declaran
  limite, `E3` propone 5 candidatas de media, y en ninguno de los 21 casos que
  recorren `E3` una candidata anadida al final caeria fuera. Concatenar no
  pierde nada aqui, asi que fusionar tampoco puede ganar nada aqui.

Lo que queda es una sola variable: **si el codificador encuentra o no**. Los
tres modelos locales probados no encontraban, y por eso las once omisiones no
se movian. Este guion pone en su sitio un modelo entrenado para recuperar y
vuelve a medir exactamente lo mismo, sin cambiar ninguna otra cosa.

LO QUE SALE DE LA MAQUINA
=========================

Los 97 textos del canon experimental y la consulta de cada caso. El canon es un
corpus **inventado** para medir, no las memorias de nadie. No sale ninguna
identidad, ninguna criticidad, ninguna anotacion del banco ni el resultado
esperado de ningun caso.

LO QUE NO SE MIRA PARA DECIDIR
==============================

`resultado_esperado` se usa **solo** para puntuar al final, igual que en todas
las rondas anteriores. Ni la construccion del indice, ni la consulta, ni el
umbral leen nada del oraculo.

EL UMBRAL NO SE ELIGE MIRANDO EL RESULTADO
==========================================

Se barre entero y se publica la curva completa. Elegir despues el punto que
mejor sale seria fijar la medida sobre el resultado, que es justo lo que
`§8.1` prohibe.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Final

from experiments.adr002.candidates.adr002_a.candidate import CandidatoA
from experiments.adr002.candidates.adr002_b import semantica
from experiments.adr002.candidates.adr002_b.candidate_semantico import CandidatoBSemantico
from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.port import PuertoSqlite
from experiments.adr002.hibrido.buscador import CandidatoHibrido
from experiments.adr002.hibrido.codificador_openai import MODELO_POR_DEFECTO, CodificadorOpenAI
from experiments.adr002.projection import build
from experiments.adr002.projection.contracts import Plano
from experiments.adr002.projection.plane import PlanoReservado
from experiments.adr002.round import cases as cs
from experiments.adr002.round import metrics as mt
from experiments.adr002.round import participants as pt
from experiments.adr002.round.execute_round import _criticos_del_canon

#: La linea base publicada, para que quien lea la salida no tenga que buscarla.
#: Si la corrida no la reproduce, algo del entorno cambio y la comparacion no
#: vale: por eso se comprueba en vez de darse por supuesta.
BASE_PUBLICADA: Final = {"exactos": 24, "omisiones": 11, "contaminacion": 3, "etapa": 32}

#: Los umbrales de coseno que se barren. Fijados **antes** de ver ni un numero.
UMBRALES: Final[tuple[float, ...]] = (0.25, 0.35, 0.45, 0.55, 0.65)

#: Cuantas candidatas propone la senal en cada punto del barrido.
K_SEMANTICO: Final = 8


def _ampliaciones(raiz: Path) -> dict[str, list[str]]:
    ruta = raiz / "artifacts/adr002_round/ampliacion_de_consulta_v0.1.json"
    if not ruta.exists():
        return {}
    return dict(json.loads(ruta.read_text(encoding="utf-8"))["ampliaciones"])


def _veredictos(
    casos: Sequence[Any],
    cand: Any,
    puerto: Any,
    plano: Any,
    contexto: dict[str, Any],
    *,
    ampliacion: dict[str, list[str]] | None,
) -> list[Any]:
    veredictos = []
    for caso in casos:
        peticion = caso.peticion
        if ampliacion:
            extra = " ".join(ampliacion.get(caso.identificador, []))
            if extra:
                peticion = dataclasses.replace(peticion, consulta=f"{peticion.consulta} {extra}")
        recuperacion = engine.recuperar(peticion, puerto, cand, plano)
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


#: La unica identidad del canon cuyo proyecto declarado es el ambito global.
#:
#: Existe un desacuerdo **previo a este experimento** entre la proyeccion y la
#: metrica congelada, y hay que conocerlo para no leer mal un fallo duro:
#:
#: * la proyeccion la trata como global —``project_id`` nulo, ``ejes.ambito``
#:   ``GLOBAL``— y por eso ``G4`` la deja pasar en cualquier ambito
#:   («un item global es visible desde cualquier ambito: no pertenece a uno»);
#: * la metrica ``fuga_de_ambito`` numera los proyectos del corpus por su
#:   posicion, y ``PRJ-GLOBAL`` ocupa la primera, de modo que le asigna el
#:   proyecto ``'1'`` y la cuenta **fuera de ambito** en toda consulta acotada.
#:
#: En la ronda publicada esto nunca afloro porque ningun candidato llego a
#: entregarla en un caso acotado a proyecto. Una senal semantica real si puede
#: proponerla —es la memoria de tono, cercana a casi cualquier consulta—, y
#: entonces la corrida marcaria una fuga de ambito, que es fallo duro del §6.1,
#: **sin que ninguna puerta se haya saltado nada**.
#:
#: Aqui no se toca la metrica congelada: sigue contando lo que contaba. Lo que
#: se hace es **separar** el recuento y decirlo, para que quien lea la salida
#: sepa cual de las dos cosas esta viendo.
IDENTIDAD_GLOBAL_DEL_CANON: Final = "MEMORIA:1"


def _fila(nombre: str, veredictos: Sequence[Any]) -> dict[str, Any]:
    resumen = mt.resumir(nombre, veredictos, borrado_y_regeneracion=True)
    ausencias = sum(1 for v in veredictos if v.adjudicable and v.ausencia_correcta)

    fugas = [f for v in veredictos for f in v.fuga_de_ambito]
    artefacto = [f for f in fugas if f == IDENTIDAD_GLOBAL_DEL_CANON]
    reales = [f for f in fugas if f != IDENTIDAD_GLOBAL_DEL_CANON]

    fila = {
        "corrida": nombre,
        "exactos": resumen.casos_con_resultado_exacto,
        "casos": len([v for v in veredictos if v.adjudicable]),
        "omisiones_criticas": resumen.criticos_pendientes_total,
        "contaminacion": resumen.contaminacion_total,
        "fuga_de_ambito": resumen.fuga_de_ambito_total,
        "fuga_real": len(reales),
        "fuga_por_el_item_global": len(artefacto),
        "etapa_conforme": resumen.casos_con_etapa_conforme,
        "etapa_puntuable": resumen.casos_con_etapa_puntuable,
        "ausencia_correcta": ausencias,
    }
    aviso = f" (de ellas {len(artefacto)} son el item global)" if artefacto else ""
    print(
        f"  {nombre:38} exactos={fila['exactos']}/{fila['casos']} "
        f"omis={fila['omisiones_criticas']:2} contam={fila['contaminacion']} "
        f"FUGA={fila['fuga_de_ambito']}{aviso} "
        f"etapa={fila['etapa_conforme']}/{fila['etapa_puntuable']} "
        f"ausencia_ok={ausencias}/{fila['casos']}"
    )
    return fila


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--modelo", default=MODELO_POR_DEFECTO)
    analizador.add_argument("--dimensiones", type=int, default=512)
    analizador.add_argument(
        "--salida",
        type=Path,
        default=Path("resultado_semantica_real.json"),
        help="donde se escribe el artefacto de resultados",
    )
    argumentos = analizador.parse_args()

    raiz = Path(__file__).resolve().parents[3]
    casos = cs.casos_ejecutables(cs.cargar_artefactos())
    familia = build.cargar_familia()
    contexto = {
        "proyectos": pt.proyectos_del_canon(familia[cs.CORPUS]),
        "polaridades": pt.polaridades_del_canon(familia[cs.CORPUS]),
        "criticos": _criticos_del_canon(familia["applied_criticality_v0_1.json"]["valores"]),
    }
    ampliacion = _ampliaciones(raiz)

    print(f"modelo: {argumentos.modelo} con {argumentos.dimensiones} dimensiones")
    print("se enviaran a la API los 97 textos del canon experimental y una consulta por caso.")
    print("no se envia ninguna identidad, criticidad ni resultado esperado.")
    print()

    codificador = CodificadorOpenAI(modelo=argumentos.modelo, dimensiones=argumentos.dimensiones)
    filas: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory() as temporal:
        proyeccion = build.construir_desde_la_familia(Path(temporal) / "planos")
        canon = proyeccion.ruta_de_entrada()
        sidecar = Path(temporal) / "semantica.sqlite3"

        print("construyendo el indice semantico (una sola llamada por lote)...")
        semantica.construir(canon, sidecar, codificador)
        print("indice construido.")
        print()

        puerto = PuertoSqlite(canon, proyeccion.ruta(Plano.EJES_P2))
        plano = PlanoReservado(proyeccion)

        def medir(
            nombre: str, hacer: Callable[[], Any], *, con_ampliacion: bool = False
        ) -> dict[str, Any]:
            cand = hacer()
            try:
                veredictos = _veredictos(
                    casos,
                    cand,
                    puerto,
                    plano,
                    contexto,
                    ampliacion=ampliacion if con_ampliacion else None,
                )
            finally:
                if hasattr(cand, "close"):
                    cand.close()
            return _fila(nombre, veredictos)

        try:
            print("=== control: la linea base publicada, sin ninguna senal semantica ===")
            base = medir("linea base (solo lexica)", CandidatoA)
            filas.append(base)
            desviado = {
                clave: (base[campo], esperado)
                for clave, campo, esperado in (
                    ("exactos", "exactos", BASE_PUBLICADA["exactos"]),
                    ("omisiones", "omisiones_criticas", BASE_PUBLICADA["omisiones"]),
                    ("contaminacion", "contaminacion", BASE_PUBLICADA["contaminacion"]),
                )
                if base[campo] != esperado
            }
            if desviado:
                print()
                print("  AVISO: la linea base NO reproduce la publicada:", desviado)
                print("  la comparacion de abajo no es contra la ronda publicada.")
            print()

            print("=== la senal semantica real, barriendo el umbral entero ===")
            for umbral in UMBRALES:
                filas.append(
                    medir(
                        f"concatenada  coseno>={umbral:.2f}",
                        lambda u=umbral: CandidatoBSemantico(  # type: ignore[misc]
                            canon, sidecar, codificador, k=K_SEMANTICO, coseno_minimo=u
                        ),
                    )
                )
                filas.append(
                    medir(
                        f"fusionada    coseno>={umbral:.2f}",
                        lambda u=umbral: CandidatoHibrido(  # type: ignore[misc]
                            canon, sidecar, codificador, k=K_SEMANTICO, coseno_minimo=u
                        ),
                    )
                )
            print()

            if ampliacion:
                print("=== sobre la ampliacion de consulta, que es la via ya aprobada ===")
                filas.append(medir("ampliacion sola", CandidatoA, con_ampliacion=True))
                for umbral in UMBRALES:
                    filas.append(
                        medir(
                            f"ampliacion + fusionada coseno>={umbral:.2f}",
                            lambda u=umbral: CandidatoHibrido(  # type: ignore[misc]
                                canon, sidecar, codificador, k=K_SEMANTICO, coseno_minimo=u
                            ),
                            con_ampliacion=True,
                        )
                    )
        finally:
            puerto.close()
            plano.close()

    artefacto = {
        "que_es": (
            "senal semantica real medida sobre el banco de ADR-002, con el "
            "codificador detras del puerto y el umbral barrido entero"
        ),
        "modelo": argumentos.modelo,
        "dimensiones": argumentos.dimensiones,
        "umbrales_barridos": list(UMBRALES),
        "k_semantico": K_SEMANTICO,
        "linea_base_publicada": BASE_PUBLICADA,
        "filas": filas,
    }
    argumentos.salida.write_text(
        json.dumps(artefacto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print()
    print(f"resultados escritos en {argumentos.salida.resolve()}")
    print("ese fichero es lo unico que hace falta traer de vuelta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
