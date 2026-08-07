"""Ejecución real de los niveles 2 y 3 del banco. **No mide tiempo.**

Ni un cronómetro. Las latencias publicadas son las de `v0.1` y `v0.2` y este
módulo no las toca: lo que produce son veredictos arquitectónicos y el efecto de
apagar cada señal, que son preguntas de contenido, no de velocidad.

QUÉ SE EJECUTA DE VERDAD
========================

- **`ARQ-CA-01`** ejecuta 30 ciclos completos de borrado y regeneración sobre el
  `FTS5` de los cinco y, además, sobre el sidecar de `B` y `D`.
- **`ARQ-CA-02`** construye el sidecar, hace `checkpoint` y `VACUUM`, lo purga y
  busca las cargas en los **bytes crudos** de `.db`, `-wal`, `-shm` y `-journal`.
- **`ARQ-CA-03`** corre `5` sesiones en **procesos distintos**, `30` repeticiones
  cada una, sobre los casos ejecutables completos.
- **`ARQ-CA-04`** y **`ARQ-CA-05`** leen la ficha congelada. No miden.
- **`AB-1`, `AB-2`, `AB-3`, `AB-6`** corren los casos ejecutables enteros.

`AB-0` es la línea base congelada de `0.1` —es `T0`, ya medido— y `AB-4` y `AB-5`
no son ejecutables sobre los candidatos congelados, con el motivo declarado en
``levels.ABLACIONES_NO_EJECUTABLES``.

POR QUÉ LA ESTABILIDAD SE MIDE EN PROCESOS DISTINTOS
====================================================

Porque `ARQ-CA-03` pide «>=5 sesiones **independientes**», y dos bucles dentro
del mismo intérprete comparten cachés, memoria y estado de SQLite: coincidirían
por compartir, no por ser estables. El protocolo ya usa procesos para el
rendimiento y aquí se usa el mismo mecanismo por la misma razón.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from experiments.adr002.projection import build
from experiments.adr002.round import cases as cs
from experiments.adr002.round import levels as lv
from experiments.adr002.round import participants as pt
from experiments.adr002.round import round_protocol as rp

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

#: Fichas vigentes, tomadas del protocolo congelado y no escritas otra vez aquí:
#: duplicar la tabla permitiría que divergiera de la que autoriza la ronda.
VERSIONES_VIGENTES: Final[Mapping[str, int]] = {
    identificador: version for identificador, (version, _) in rp.FICHAS_VIGENTES.items()
}

#: Las ablaciones que sí se ejecutan, con lo que apagan.
#: Las que se corren **sobre cada participante**. `AB-6` no está aquí porque no
#: depende del participante: es el azar, y se emite una vez por lectura.
ABLACIONES_EJECUTABLES: Final[tuple[str, ...]] = ("AB-1", "AB-3")


# --------------------------------------------------------------------------
# Recorrido de casos, común a las ablaciones
# --------------------------------------------------------------------------


def _respuestas(
    participante: Any, casos: Sequence[cs.CasoEjecutable], espacios: Any = None
) -> list[tuple[str, tuple[str, ...]]]:
    """Lo que un participante devuelve en cada caso, en orden."""
    salida: list[tuple[str, tuple[str, ...]]] = []
    for caso in casos:
        peticion = caso.peticion
        if espacios is not None:
            peticion = replace_espacios(peticion, espacios)
        salida.append((caso.identificador, participante.responder(peticion).ids))
    return salida


def replace_espacios(peticion: Any, espacios: Any) -> Any:
    """La misma petición con otros espacios autorizados. **Solo eso.**

    Cambiar cualquier otro campo convertiría la ablación en un caso distinto, y
    entonces la diferencia medida no sería la de la señal apagada.
    """
    from dataclasses import replace

    return replace(peticion, espacios_autorizados=espacios)


def exactos(
    respuestas: Sequence[tuple[str, tuple[str, ...]]], casos: Sequence[cs.CasoEjecutable]
) -> tuple[int, int, tuple[str, ...]]:
    """Aciertos exactos con el **mismo criterio** que la ronda publicada.

    ``tuple(sorted(obtenido)) == tuple(sorted(esperado))`` sobre los casos
    adjudicables, que es literalmente lo que ``execute_round._veredicto``
    calcula. Reimplementarlo con otro criterio haría incomparables las cifras.
    """
    por_caso = dict(respuestas)
    aciertos: list[str] = []
    adjudicables = [c for c in casos if c.adjudicable]
    for caso in adjudicables:
        obtenido = por_caso.get(caso.identificador, ())
        if tuple(sorted(obtenido)) == tuple(sorted(caso.resultado_esperado)):
            aciertos.append(caso.identificador)
    return len(aciertos), len(adjudicables), tuple(aciertos)


# --------------------------------------------------------------------------
# Nivel 3
# --------------------------------------------------------------------------


def ablaciones(
    proyeccion: Any, casos: Sequence[cs.CasoEjecutable], trabajo: Path
) -> list[lv.ResultadoDeAblacion]:
    """Las cuatro ejecutables sobre los cinco, más las dos que no lo son."""
    resultados: list[lv.ResultadoDeAblacion] = []

    completos: dict[str, tuple[str, ...]] = {}
    for identificador in rp.PARTICIPANTES:
        directorio = trabajo / f"completa-{identificador}"
        participante = pt.construir(identificador, proyeccion, directorio)
        try:
            _, _, aciertos = exactos(_respuestas(participante, casos), casos)
        finally:
            participante.close()
        completos[identificador] = aciertos

    #: `AB-6` no depende del participante —es el azar— y por eso se emite una
    #: vez por lectura y no cinco veces la misma cifra.
    universo = universo_canonico()
    conjunto_n, conjunto_total, conjunto_aciertos = suelo_de_conjunto(universo, casos)
    vacios = sum(1 for c in casos if c.adjudicable and not c.resultado_esperado)
    orden_n, orden_total, orden_aciertos, nota_de_orden = suelo_de_orden(casos)
    for lectura, (aciertos_n, total, aciertos, nota) in (
        (
            "conjunto",
            (
                conjunto_n,
                conjunto_total,
                conjunto_aciertos,
                (
                    f"el suelo recibe la CANTIDAD que el caso espera, que ningun sistema "
                    f"real conoce: es un suelo generoso. {vacios} de los {conjunto_total} "
                    f"casos esperan el conjunto vacio, y en ellos conocer la cantidad es "
                    f"conocer la respuesta, de modo que el suelo los acierta todos. La "
                    f"comparacion informativa es la de los {conjunto_total - vacios} casos "
                    f"con contenido"
                ),
            ),
        ),
        ("orden", (orden_n, orden_total, orden_aciertos, nota_de_orden)),
    ):
        resultados.append(
            lv.ResultadoDeAblacion(
                ablacion="AB-6",
                participante="(ninguno: es el azar)",
                ejecutada=True,
                exactos=aciertos_n,
                casos=total,
                perdidos_respecto_de_la_completa=(),
                ganados_respecto_de_la_completa=aciertos,
                lectura=f"{lv.LECTURAS_DE_AB_6[lectura]}. {nota}",
            )
        )

    for ablacion in ABLACIONES_EJECUTABLES:
        for identificador in rp.PARTICIPANTES:
            directorio = trabajo / f"{ablacion}-{identificador}"
            if ablacion == "AB-3":
                participante = pt.construir(
                    identificador,
                    proyeccion,
                    directorio,
                    con_senal_relacional=False,
                    con_senal_vectorial=False,
                )
                try:
                    aciertos_n, total, aciertos = exactos(_respuestas(participante, casos), casos)
                finally:
                    participante.close()
            else:
                participante = pt.construir(identificador, proyeccion, directorio)
                try:
                    respuestas = _respuestas(
                        participante, casos, lv.ESPACIOS_POR_ABLACION[ablacion]
                    )
                    aciertos_n, total, aciertos = exactos(respuestas, casos)
                finally:
                    participante.close()

            resultados.append(
                lv.ResultadoDeAblacion(
                    ablacion=ablacion,
                    participante=identificador,
                    ejecutada=True,
                    exactos=aciertos_n,
                    casos=total,
                    perdidos_respecto_de_la_completa=lv.perdido(completos[identificador], aciertos),
                    ganados_respecto_de_la_completa=lv.perdido(aciertos, completos[identificador]),
                )
            )

    for ablacion, motivo in lv.ABLACIONES_NO_EJECUTABLES.items():
        for identificador in rp.PARTICIPANTES:
            resultados.append(
                lv.ResultadoDeAblacion(
                    ablacion=ablacion,
                    participante=identificador,
                    ejecutada=False,
                    exactos=0,
                    casos=0,
                    perdidos_respecto_de_la_completa=(),
                    ganados_respecto_de_la_completa=(),
                    motivo_si_no_se_ejecuta=motivo,
                )
            )
    return resultados


def universo_canonico() -> tuple[str, ...]:
    """Todas las identidades canónicas del corpus. El universo del suelo.

    Es **el canon entero**, no los elegibles del caso: el banco define para
    `EXHAUSTIVA` que ``resultado_esperado == elegibles_semanticos``, de modo
    que un suelo que sortease entre los elegibles sacaría `n` de `n` y acertaría
    siempre. Eso no mide el azar, mide el oráculo.
    """
    from experiments.adr002.projection import contracts as pc

    corpus = build.cargar_familia()["conformance_corpus_v0_6.json"]
    identidades = (pc.referencia_canonica(str(item["id"])) for item in corpus["items"])
    return tuple(sorted({i for i in identidades if i is not None}))


def suelo_de_conjunto(
    universo: Sequence[str], casos: Sequence[cs.CasoEjecutable]
) -> tuple[int, int, tuple[str, ...]]:
    """`AB-6` como suelo del acierto **exacto**: azar sobre el canon."""
    aciertos: list[str] = []
    adjudicables = [c for c in casos if c.adjudicable]
    for indice, caso in enumerate(adjudicables):
        muestra = lv.suelo_aleatorio(
            universo, len(caso.resultado_esperado), lv.SEMILLA_DEL_SUELO + indice
        )
        if tuple(sorted(muestra)) == tuple(sorted(caso.resultado_esperado)):
            aciertos.append(caso.identificador)
    return len(aciertos), len(adjudicables), tuple(aciertos)


def suelo_de_orden(casos: Sequence[cs.CasoEjecutable]) -> tuple[int, int, tuple[str, ...], str]:
    """`AB-6` en su lectura literal: el conjunto correcto, barajado.

    Solo sobre los casos que **declaran** orden. Exigir orden a los catorce que
    no lo declaran inventaría una referencia que el caso no fijó.

    Devuelve además el recuento **estructural** de casos que no admiten ningún
    orden equivocado —los de un solo elemento—, porque esa cifra no depende de
    la semilla y la del sorteo sí. Publicar solo la del sorteo haría descansar
    una conclusión sobre la suerte de un número.
    """
    aciertos: list[str] = []
    con_orden = [c for c in casos if c.adjudicable and c.declara_orden]
    triviales = [c.identificador for c in con_orden if len(c.orden_esperado) <= 1]
    for indice, caso in enumerate(con_orden):
        barajado = lv.orden_barajado(caso.orden_esperado, lv.SEMILLA_DEL_SUELO + indice)
        if barajado == caso.orden_esperado:
            aciertos.append(caso.identificador)
    nota = (
        f"{len(triviales)} de los {len(con_orden)} casos con orden declarado tienen un "
        f"solo elemento: en ellos no existe orden que equivocar, y el suelo es del "
        f"100 % por construccion, sin depender de la semilla"
    )
    return len(aciertos), len(con_orden), tuple(aciertos), nota


# --------------------------------------------------------------------------
# ARQ-CA-03 · sesiones independientes
# --------------------------------------------------------------------------


def sesion_de_estabilidad(raiz_de_trabajo: Path) -> dict[str, Any]:
    """Una sesión: `30` repeticiones de todos los casos, por participante."""
    proyeccion = build.construir_desde_la_familia(raiz_de_trabajo / "planos")
    casos = cs.casos_ejecutables(cs.cargar_artefactos())
    observado: dict[str, Any] = {}
    for identificador in rp.PARTICIPANTES:
        participante = pt.construir(identificador, proyeccion, raiz_de_trabajo / identificador)
        try:
            distintos = {
                tuple((c, tuple(ids)) for c, ids in _respuestas(participante, casos))
                for _ in range(lv.REPETICIONES_DE_ESTABILIDAD)
            }
        finally:
            participante.close()
        observado[identificador] = {
            "repeticiones": lv.REPETICIONES_DE_ESTABILIDAD,
            "ordenes_distintos": [
                [[caso, list(ids)] for caso, ids in vector] for vector in sorted(distintos)
            ],
        }
    return observado


def ejecutor_de_sesiones() -> list[Mapping[str, Any]]:
    """Exactamente cinco procesos del sistema operativo, secuenciales."""
    resultados: list[Mapping[str, Any]] = []
    for sesion in range(1, lv.SESIONES_DE_ESTABILIDAD + 1):
        completado = subprocess.run(
            [
                sys.executable,
                "-m",
                "experiments.adr002.round.execute_levels",
                "--worker",
                "--session",
                str(sesion),
            ],
            cwd=str(RAIZ_REPOSITORIO),
            capture_output=True,
            text=True,
            check=False,
        )
        if completado.returncode != 0:
            detalle = completado.stderr.strip()[-500:]
            msg = f"sesion de estabilidad {sesion} fallida (rc={completado.returncode}): {detalle}"
            raise RuntimeError(msg)
        resultados.append(json.loads(completado.stdout))
        print(f"  sesion {sesion}/{lv.SESIONES_DE_ESTABILIDAD} completada")
    return resultados


def estabilidad(sesiones: Sequence[Mapping[str, Any]]) -> dict[str, tuple[lv.Veredicto, str]]:
    """`ARQ-CA-03` para cada participante, sobre las sesiones observadas."""
    resultado: dict[str, tuple[lv.Veredicto, str]] = {}
    for identificador in rp.PARTICIPANTES:
        repeticiones = [int(s[identificador]["repeticiones"]) for s in sesiones]
        distintos = {
            tuple((caso, tuple(ids)) for caso, ids in vector)
            for s in sesiones
            for vector in s[identificador]["ordenes_distintos"]
        }
        resultado[identificador] = lv.arq_ca_03(
            repeticiones, [[ids for _, ids in vector] for vector in sorted(distintos)]
        )
    return resultado


# --------------------------------------------------------------------------
# Nivel 2 completo
# --------------------------------------------------------------------------

TITULOS: Final[Mapping[str, tuple[str, str]]] = {
    "ARQ-CA-01": ("Borrado y regeneracion completos de todo indice derivado", "puerta 5"),
    "ARQ-CA-02": ("Purga fisica del derivado sin fragmento recuperable", "puerta 5"),
    "ARQ-CA-03": ("Estabilidad de orden y conjunto ante entradas identicas", "puerta 4"),
    "ARQ-CA-04": ("Declaracion congelada de tamano y ciclo de todo indice adicional", "puerta 7"),
    "ARQ-CA-05": ("Coste incremental declarado por etapa E0-E5", "puerta 7"),
}


def arquitectonicos(
    proyeccion: Any,
    trabajo: Path,
    cargas: Sequence[str],
    estabilidades: Mapping[str, tuple[lv.Veredicto, str]],
) -> list[lv.ResultadoArquitectonico]:
    """Los cinco casos de nivel 2 sobre los cinco participantes."""
    resultados: list[lv.ResultadoArquitectonico] = []
    canon = proyeccion.ruta_de_entrada()

    for identificador in rp.PARTICIPANTES:
        ficha = lv.cargar_ficha(identificador, VERSIONES_VIGENTES[identificador])
        veredictos = {
            "ARQ-CA-01": lv.arq_ca_01(identificador, canon, trabajo / f"ca01-{identificador}"),
            "ARQ-CA-02": lv.arq_ca_02(
                identificador, trabajo / f"ca02-{identificador}", canon, cargas
            ),
            "ARQ-CA-03": estabilidades[identificador],
            "ARQ-CA-04": lv.arq_ca_04(ficha),
            "ARQ-CA-05": lv.arq_ca_05(ficha),
        }
        for caso, (veredicto, detalle) in veredictos.items():
            titulo, puerta = TITULOS[caso]
            resultados.append(
                lv.ResultadoArquitectonico(
                    caso=caso,
                    titulo=titulo,
                    puerta=puerta,
                    participante=identificador,
                    veredicto=veredicto,
                    detalle=detalle,
                )
            )
    return resultados


def cargas_del_canon(limite: int = 12) -> tuple[str, ...]:
    """Trozos de texto canónico que `ARQ-CA-02` busca tras la purga.

    Textos reales del corpus, no identificadores: un identificador podría no
    estar nunca en el derivado, y encontrar «nada» diría más de la búsqueda que
    de la purga.
    """
    corpus = build.cargar_familia()["conformance_corpus_v0_6.json"]
    textos: list[str] = []
    for item in corpus["items"]:
        texto = str(item.get("text") or "").strip()
        if len(texto) >= 24:
            textos.append(texto[:24])
        if len(textos) >= limite:
            break
    if not textos:
        msg = "el corpus no trae textos con los que comprobar la purga"
        raise ValueError(msg)
    return tuple(textos)


# --------------------------------------------------------------------------
# Punto de entrada
# --------------------------------------------------------------------------


def ejecutar() -> int:
    """La corrida de los niveles 2 y 3."""
    trabajo = Path(tempfile.mkdtemp(prefix="adr002_niveles_"))
    try:
        proyeccion = build.construir_desde_la_familia(trabajo / "planos")
        casos = cs.casos_ejecutables(cs.cargar_artefactos())
        print(f"casos ejecutables: {len(casos)}; adjudicables: {sum(c.adjudicable for c in casos)}")

        print(f"ARQ-CA-03: {lv.SESIONES_DE_ESTABILIDAD} sesiones independientes...")
        sesiones = ejecutor_de_sesiones()
        estabilidades = estabilidad(sesiones)

        #: Las ablaciones van **antes** que el nivel 2 a propósito: `ARQ-CA-01`
        #: borra y regenera el `FTS5` de la proyección treinta veces, y aunque
        #: la regeneración sea fiel —que es justo lo que ese caso comprueba—,
        #: medir las ablaciones sobre una base ya reconstruida las haría
        #: depender del resultado de otro caso.
        print("nivel 3: ablaciones...")
        abl = ablaciones(proyeccion, casos, trabajo)

        print(f"nivel 2: cinco casos arquitectonicos ({lv.CICLOS_DE_REGENERACION} ciclos)...")
        arq = arquitectonicos(proyeccion, trabajo, cargas_del_canon(), estabilidades)
    finally:
        shutil.rmtree(trabajo, ignore_errors=True)

    lv.escribir(RAIZ_REPOSITORIO / lv.SALIDA, lv.documento(arq, abl))
    print(f"artefacto escrito: {lv.SALIDA}")

    for identificador in rp.PARTICIPANTES:
        propios = [r for r in arq if r.participante == identificador]
        marcas = " ".join(f"{r.caso[-2:]}:{r.veredicto.value[:2]}" for r in propios)
        print(f"  {identificador:12} {marcas}")
    print()
    for ablacion in ABLACIONES_EJECUTABLES:
        propias = [a for a in abl if a.ablacion == ablacion]
        detalle = " ".join(f"{a.participante.split('-')[-1]}:{a.exactos}" for a in propias)
        print(f"  {ablacion}  exactos  {detalle}")
    for suelo in (a for a in abl if a.ablacion == "AB-6"):
        print(f"  AB-6  suelo {suelo.exactos}/{suelo.casos}  ({suelo.lectura[:60]}...)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Niveles 2 y 3 del banco de ADR-002")
    analizador.add_argument("--worker", action="store_true")
    analizador.add_argument("--session", type=int, default=0)
    opciones = analizador.parse_args(list(argv) if argv is not None else None)

    if opciones.worker:
        raiz = Path(tempfile.mkdtemp(prefix=f"adr002_estab_{opciones.session}_"))
        try:
            print(json.dumps(sesion_de_estabilidad(raiz)))
        finally:
            shutil.rmtree(raiz, ignore_errors=True)
        return 0
    return ejecutar()


if __name__ == "__main__":  # pragma: no cover - punto de entrada
    raise SystemExit(main())
