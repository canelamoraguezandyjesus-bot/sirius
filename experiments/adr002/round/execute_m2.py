"""Observa el marcado de `M2` sobre los cinco participantes. **No mide tiempo.**

Recorre los casos ejecutables y, por cada resultado entregado, se queda con las
dos marcas que el canon exige —el estado y las dos referencias temporales— para
contrastarlas con lo que el corpus declara.

POR QUÉ NO SE REUTILIZA `participants.Observacion`
==================================================

Porque ``Observacion`` **no lleva las explicaciones**: guarda cuántas están
completas, no cuáles ni qué dicen. Añadirle un campo obligaría a tocar el módulo
que produjo las mediciones publicadas de `v0.1` y `v0.2`, y aunque el cambio
fuese aditivo, dejaría el arnés de las cifras publicadas distinto del que las
produjo. De modo que aquí se abre el motor **igual que lo abre `participants`** y
se lee lo que aquel descarta. El coste es una duplicación de seis líneas; la
alternativa era modificar la evidencia de su propio origen.

POR QUÉ SE VUELVE A RECUPERAR EN VEZ DE RELEER LA EVIDENCIA
===========================================================

Porque la evidencia congelada guarda **identidades**, no explicaciones: la marca
no está ahí. No es una medición nueva —la conformidad es determinista y los
conjuntos serán los mismos—, es un **canal de observación** que la primera
corrida no abrió. Ninguna cifra publicada cambia, y las pruebas lo comprueban
recomputando los conjuntos y exigiendo que coincidan.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.port import PuertoSqlite
from experiments.adr002.candidates.t0_control import conformance as t0
from experiments.adr002.projection import build
from experiments.adr002.projection.contracts import Plano
from experiments.adr002.projection.plane import PlanoReservado
from experiments.adr002.round import cases as cs
from experiments.adr002.round import m2_marking as m2
from experiments.adr002.round import participants as pt
from experiments.adr002.round import round_protocol as rp

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

#: Quien no publica explicación por resultado no puede medirse aquí, y su ficha
#: ya lo declara. No es una carencia de esta medición.
SIN_EXPLICACION: Final[tuple[str, ...]] = (t0.IDENTIFICADOR,)


def _senales(identificador: str, proyeccion: Any, trabajo: Path) -> Any:
    """Las señales del candidato pedido, construidas como en la ronda."""
    from experiments.adr002.candidates.adr002_a import candidate as ca
    from experiments.adr002.candidates.adr002_b import candidate as cb
    from experiments.adr002.candidates.adr002_c import candidate as cc
    from experiments.adr002.candidates.adr002_d import candidate as cd

    entrada = proyeccion.ruta_de_entrada()
    relacional = proyeccion.ruta(Plano.EJES_P2)
    if identificador == ca.IDENTIFICADOR:
        return ca.candidato()
    if identificador == cb.IDENTIFICADOR:
        return cb.candidato(entrada, _sidecar(proyeccion, trabajo))
    if identificador == cc.IDENTIFICADOR:
        return cc.candidato(relacional)
    if identificador == cd.IDENTIFICADOR:
        return cd.candidato(entrada, _sidecar(proyeccion, trabajo), relacional)
    msg = f"participante sin senales propias: {identificador!r}"
    raise ValueError(msg)


def _sidecar(proyeccion: Any, trabajo: Path) -> Path:
    trabajo.mkdir(parents=True, exist_ok=True)
    destino = trabajo / pt.SIDECAR
    from experiments.adr002.candidates.adr002_b import vectores

    vectores.construir(proyeccion.ruta_de_entrada(), destino)
    return destino


def observar(
    identificador: str, proyeccion: Any, casos: Sequence[cs.CasoEjecutable], trabajo: Path
) -> tuple[list[m2.Marca], dict[str, tuple[str, ...]]]:
    """Las marcas publicadas y los conjuntos devueltos, caso a caso."""
    senales = _senales(identificador, proyeccion, trabajo)
    plano = PlanoReservado(proyeccion)
    puerto = PuertoSqlite(proyeccion.ruta_de_entrada(), proyeccion.ruta(Plano.EJES_P2))
    marcas: list[m2.Marca] = []
    conjuntos: dict[str, tuple[str, ...]] = {}
    try:
        for caso in casos:
            recuperacion = engine.recuperar(caso.peticion, puerto, senales, plano)
            conjuntos[caso.identificador] = recuperacion.ids
            for resultado in recuperacion.resultados:
                explicacion = resultado.explicacion
                marcas.append(
                    m2.Marca(
                        caso=caso.identificador,
                        participante=identificador,
                        identidad=resultado.item.id,
                        estado_publicado=str(getattr(explicacion, "estado", "")),
                        tiempo_publicado=str(getattr(explicacion, "tiempo", "")),
                    )
                )
    finally:
        puerto.close()
        plano.close()
    return marcas, conjuntos


def conjuntos_publicados() -> dict[str, dict[str, tuple[str, ...]]]:
    """Los conjuntos que la corrida `v0.2` congeló, para poder compararlos."""
    ruta = RAIZ_REPOSITORIO / "artifacts/adr002_round/ronda_primaria_v0.2_evidencia.json"
    evidencia = json.loads(ruta.read_text(encoding="utf-8"))
    return {
        participante: {v["caso"]: tuple(v["obtenido"]) for v in veredictos}
        for participante, veredictos in evidencia["veredictos"].items()
    }


def divergencias(
    observado: Mapping[str, tuple[str, ...]], publicado: Mapping[str, tuple[str, ...]]
) -> list[str]:
    """Que observar de nuevo **no** haya cambiado ni un conjunto.

    Es el control que convierte «volví a recuperar» en «abrí otro canal sobre lo
    mismo». Si algo divergiera, esta medición no podría publicarse al lado de la
    corrida: sería una corrida distinta.
    """
    return [
        caso
        for caso, ids in observado.items()
        if caso in publicado and tuple(sorted(ids)) != tuple(sorted(publicado[caso]))
    ]


def ejecutar() -> int:
    """Observa, comprueba que nada cambió, y publica."""
    from experiments.adr002.tolerances.run_envelope import escribir_json_atomico

    trabajo = Path(tempfile.mkdtemp(prefix="adr002_m2_"))
    try:
        proyeccion = build.construir_desde_la_familia(trabajo / "planos")
        casos = cs.casos_ejecutables(cs.cargar_artefactos())
        corpus = build.cargar_familia()["conformance_corpus_v0_6.json"]
        canonicos = m2.estados_canonicos(corpus)
        publicado = conjuntos_publicados()

        marcas: dict[str, list[m2.Marca]] = {}
        desviados: list[str] = []
        for identificador in rp.PARTICIPANTES:
            if identificador in SIN_EXPLICACION:
                marcas[identificador] = []
                continue
            observadas, conjuntos = observar(
                identificador, proyeccion, casos, trabajo / identificador
            )
            marcas[identificador] = observadas
            for caso in divergencias(conjuntos, publicado.get(identificador, {})):
                desviados.append(f"{identificador}:{caso}")
    finally:
        shutil.rmtree(trabajo, ignore_errors=True)

    if desviados:
        print("la observacion no reprodujo los conjuntos publicados: no se publica nada.")
        for desviado in desviados[:10]:
            print(f"  - {desviado}")
        return 2

    print(f"conjuntos reproducidos sin una sola divergencia sobre {len(casos)} casos.")
    contenido = m2.documento(marcas, canonicos, SIN_EXPLICACION)
    escribir_json_atomico(RAIZ_REPOSITORIO / m2.SALIDA, contenido)
    print(f"artefacto escrito: {m2.SALIDA}")
    for participante, resumen in contenido["por_participante"].items():
        if not resumen["medible"]:
            print(f"  {participante:12} no medible: sin explicacion por resultado")
            continue
        print(
            f"  {participante:12} nunca-como-actual={resumen['m2_1_nunca_como_actual']}"
            f"  tiempos={resumen['m2_2_separa_tiempo_valido_de_corte']}"
            f"  tres-estados={resumen['m2_3_distingue_los_tres_estados']}"
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - punto de entrada
    del argv
    return ejecutar()


if __name__ == "__main__":  # pragma: no cover - punto de entrada
    raise SystemExit(main())
