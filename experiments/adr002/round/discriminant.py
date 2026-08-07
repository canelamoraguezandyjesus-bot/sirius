"""El caso discriminante relacional del banco, `N4-01`. **No mide tiempo.**

El banco tiene un caso de **nivel 4** cuyo propósito literal es «falsar la
suficiencia de una expansión exclusivamente léxica-estructurada ante una
dependencia explícita entre dos sujetos sin solapamiento léxico», con su
referencia calculada **por un camino independiente del generador**.

La ronda primaria no lo ejecutaba. `cases.casos_ejecutables` recorría
`nivel_1` y solo `nivel_1`, de modo que las dos corridas publicadas midieron la
aportación de la señal relacional **sin ejecutar el único caso construido para
que esa señal importe**. Este módulo lo ejecuta.

POR QUÉ NO ENTRA EN LA MÉTRICA DE CONFORMIDAD
=============================================

Porque no es un caso de conformidad y él mismo lo dice: su bloque ``no_mide``
excluye latencia, memoria, almacenamiento y «calidad comparada entre
candidatos». Es un **experimento de falsación** con dos preguntas de sí o no:

1. ¿alcanza el participante el elemento que **solo** una arista explícita
   alcanza?
2. ¿lo alcanza **por la etapa** en que su señal está declarada?

Meterlo en el recuento de los cincuenta habría convertido un experimento de
falsación en un caso más, y habría diluido en una fracción lo que es una
respuesta binaria.

LO QUE NO SE ARREGLA AQUÍ
=========================

Las cifras publicadas de `v0.1` y `v0.2` **no cambian**: aquellas midieron los
cincuenta casos de nivel 1 y eso es lo que dicen que midieron. Lo que cambia es
lo que puede concluirse de ellas, y eso se corrige en el documento, no en el
artefacto.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Cardinalidad,
    Modo,
    Peticion,
    VentanaTemporal,
)
from experiments.adr002.projection import contracts as pc

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]
SALIDA: Final = "artifacts/adr002_round/discriminante_relacional_v0.1.json"

CASO: Final = "N4-01"
IDENTIFICADOR: Final = "ADR002-DISC-REL-01"
NIVEL: Final = 4


@dataclass(frozen=True, slots=True)
class CasoDiscriminante:
    """El caso de nivel 4, traducido, con su oráculo al lado."""

    peticion: Peticion
    #: Lo que alcanza una expansión léxica-estructurada. Todos deberían.
    alcance_lexico: tuple[str, ...]
    #: Lo que **solo** se alcanza siguiendo una arista de un salto.
    por_salto_relacional: tuple[str, ...]
    #: Consulta con la que el destino sí es recuperable por sí mismo. Sirve para
    #: distinguir «no alcanzable» de «no existe».
    consulta_propia_del_destino: str
    arista: str


@dataclass(frozen=True, slots=True)
class Veredicto:
    """Dos preguntas de sí o no, y nada más."""

    participante: str
    obtenido: tuple[str, ...]
    alcanza_el_lexico: bool
    alcanza_por_arista: bool
    etapa_de_aporte: str | None

    @property
    def falsa_la_suficiencia_lexica(self) -> bool:
        """Alcanzar el destino es exactamente lo que el caso viene a falsar."""
        return self.alcanza_por_arista


def _identidades(valores: Sequence[str]) -> tuple[str, ...]:
    convertidas = (pc.referencia_canonica(str(v)) for v in valores)
    return tuple(i for i in convertidas if i is not None)


def cargar(
    artefactos: Mapping[str, Any], numeros_de_proyecto: Mapping[str, int]
) -> CasoDiscriminante:
    """Traduce el caso congelado. La petición sale del caso, no de aquí."""
    caso = next(c for c in artefactos["cases_v0_5.json"]["nivel_4"] if c["id"] == CASO)
    entrada = caso["entrada"]
    p = entrada["peticion"]
    oraculo = caso["oraculo"]

    ambito = str(p["ambito"])
    numero = numeros_de_proyecto.get(ambito)
    if numero is None:
        msg = f"ambito del caso discriminante que el corpus no numera: {ambito!r}"
        raise ValueError(msg)

    return CasoDiscriminante(
        peticion=Peticion(
            operation_id=str(p["operation_id"]),
            consulta=str(p["consulta"]),
            proposito=str(p["proposito"]),
            modo=Modo(str(p["modo"])),
            ambito=Ambito(global_=False, proyectos=(str(numero),)),
            ventana=VentanaTemporal(
                tiempo_objetivo=str(p["tiempo_objetivo"]),
                corte_de_registro=None if p["corte_registro"] is None else str(p["corte_registro"]),
            ),
            cardinalidad=Cardinalidad(str(p["cardinalidad"])),
            limite_objetivo=int(p["limite_objetivo"]),
            limite_duro=int(p["limite_duro"]),
            objetivos=int(p["objetivos"]),
        ),
        alcance_lexico=_identidades(oraculo["alcance_lexico_estructurado"]),
        por_salto_relacional=_identidades(oraculo["aportado_por_un_salto_relacional"]),
        consulta_propia_del_destino=str(entrada["consulta_propia_del_destino"]),
        arista=str(entrada["relacion"]["id"]),
    )


def juzgar(
    participante: str, obtenido: Sequence[str], etapas: Mapping[str, str], caso: CasoDiscriminante
) -> Veredicto:
    """Las dos preguntas, contra el oráculo. Sin promediar y sin ponderar."""
    entregado = frozenset(obtenido)
    alcanza_arista = all(i in entregado for i in caso.por_salto_relacional)
    return Veredicto(
        participante=participante,
        obtenido=tuple(obtenido),
        alcanza_el_lexico=all(i in entregado for i in caso.alcance_lexico),
        alcanza_por_arista=alcanza_arista,
        etapa_de_aporte=etapas.get(participante) if alcanza_arista else None,
    )


def documento(caso: CasoDiscriminante, veredictos: Sequence[Veredicto]) -> dict[str, Any]:
    """El artefacto. Publica quién falsa la suficiencia léxica y quién no."""
    return {
        "documento": "Caso discriminante relacional de ADR-002 (nivel 4)",
        "version_esquema": "discriminante-relacional-adr002-0.1",
        "estado": "EVIDENCIA",
        "caso": CASO,
        "identificador": IDENTIFICADOR,
        "nivel": NIVEL,
        "proposito": (
            "falsar la suficiencia de una expansion exclusivamente lexica-estructurada "
            "ante una dependencia explicita entre dos sujetos sin solapamiento lexico"
        ),
        "por_que_se_publica_aparte": (
            "la ronda primaria ejecutaba solo el nivel 1, de modo que las corridas v0.1 "
            "y v0.2 midieron la aportacion de la senal relacional sin ejecutar el unico "
            "caso construido para que esa senal importe. Sus cifras no cambian; lo que "
            "cambia es lo que puede concluirse de ellas"
        ),
        "no_mide": ["latencia", "memoria", "almacenamiento", "calidad comparada entre candidatos"],
        "consulta": caso.peticion.consulta,
        "arista": caso.arista,
        "oraculo": {
            "alcance_lexico_estructurado": list(caso.alcance_lexico),
            "aportado_por_un_salto_relacional": list(caso.por_salto_relacional),
            "consulta_propia_del_destino": caso.consulta_propia_del_destino,
        },
        "veredictos": [
            {
                "participante": v.participante,
                "obtenido": list(v.obtenido),
                "alcanza_el_lexico": v.alcanza_el_lexico,
                "alcanza_por_arista": v.alcanza_por_arista,
                "etapa_de_aporte": v.etapa_de_aporte,
                "falsa_la_suficiencia_lexica": v.falsa_la_suficiencia_lexica,
            }
            for v in veredictos
        ],
        "no_elige": (
            "este caso no elige alternativa: responde si la expansion lexica basta, y "
            "para quien no basta"
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - punto de entrada
    del argv
    import shutil
    import tempfile

    from experiments.adr002.projection import build
    from experiments.adr002.round import participants as pt
    from experiments.adr002.round import round_protocol as rp
    from experiments.adr002.tolerances.run_envelope import escribir_json_atomico

    artefactos = {
        "cases_v0_5.json": json.loads(
            (RAIZ_REPOSITORIO / "experiments/adr002/benchmark/cases_v0_5.json").read_text(
                encoding="utf-8"
            )
        )
    }
    corpus = build.cargar_familia()["conformance_corpus_v0_6.json"]
    numeros = {str(p["id"]): i for i, p in enumerate(corpus["proyectos"], start=1)}
    caso = cargar(artefactos, numeros)

    trabajo = Path(tempfile.mkdtemp(prefix="adr002_discriminante_"))
    try:
        proyeccion = build.construir_desde_la_familia(trabajo / "planos")
        veredictos = []
        for identificador in rp.PARTICIPANTES:
            participante = pt.construir(identificador, proyeccion, trabajo / identificador)
            try:
                observacion = participante.responder(caso.peticion)
            finally:
                participante.close()
            etapas = {identificador: observacion.etapa_de_resolucion or ""}
            veredictos.append(juzgar(identificador, observacion.ids, etapas, caso))
    finally:
        shutil.rmtree(trabajo, ignore_errors=True)

    escribir_json_atomico(RAIZ_REPOSITORIO / SALIDA, documento(caso, veredictos))
    print(f"artefacto escrito: {SALIDA}")
    for v in veredictos:
        marca = "FALSA la suficiencia lexica" if v.falsa_la_suficiencia_lexica else "no la falsa"
        print(f"  {v.participante:12} {marca}  (etapa {v.etapa_de_aporte or '-'})")
    return 0


if __name__ == "__main__":  # pragma: no cover - punto de entrada
    raise SystemExit(main())
