"""``ADR002-A``: expansion escalonada **solo** lexica y estructurada.

Definicion canonica que asume (``ARQ-00 §23``):

    expansion escalonada solo lexica/estructurada en todas las etapas E0-E5.

Este candidato **no es T0**. T0 es Sirius 0.1 tal cual: no implementa las
etapas, no tiene puertas ni paradas e incumple ``RF-06``, ``RF-14`` y
``RF-19``. ``ADR002-A`` es una realizacion correcta del contrato B04 que debe
cumplir los tres como cualquier otro candidato, y lo hace apoyandose en el
motor comun —que posee el bucle— y aportando aqui **solo las senales**.

Tampoco es una variante degradada. Ejecuta ``E3`` integra: busca parafrasis,
dependencias, apoyo/refutacion y relaciones por medios lexico-estructurados
—raices compartidas, variantes morfologicas, claves de sujeto emparentadas y
relaciones que el canon ya materializa— y valida sujeto, polaridad, condicion
y tiempo en cada item que propone.

Que no habilite senal tardia adicional **es la hipotesis que se pone a
prueba**, no un deficit: ``B04-RF-31`` prohibe convertir ``RF-17`` en una
obligacion de realizacion.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.candidates.common.contracts import (
    Candidata,
    ContextoDeEtapa,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
    Polaridad,
)

IDENTIFICADOR: Final = "ADR002-A"

#: Lo que ``ARQ-00 §23`` pone a prueba en este candidato.
SENAL_TARDIA: Final = "ninguna_adicional"

DEFINICION_CANONICA: Final = (
    "expansion escalonada solo lexica/estructurada en todas las etapas E0-E5."
)

#: Medios con los que este candidato satisface cada etapa. Se declaran aqui y
#: la ficha los cita: el mecanismo no puede cambiar en silencio.
MEDIOS_POR_ETAPA: Final[dict[Etapa, str]] = {
    Etapa.E1: "clave de sujeto normalizada y coincidencia literal del indice lexico medido",
    Etapa.E2: "variantes morfologicas por recorte de sufijo flexivo y raiz compartida",
    Etapa.E3: "raices compartidas, claves de sujeto emparentadas y relaciones del canon",
    Etapa.E4: "historial y fuentes como evidencia atribuida, cotejada con lo vigente",
}


class CandidatoA:
    """Las senales de ``ADR002-A``, etapa por etapa.

    No implementa el motor, ni las puertas, ni el orden de etapas: los recibe.
    Lo unico que decide es **que propone** cuando el motor le pregunta.
    """

    identificador: Final = IDENTIFICADOR

    @property
    def senal_tardia_habilitada(self) -> str:
        """``ninguna_adicional``: sin senal vectorial ni indice relacional."""
        return SENAL_TARDIA

    # -- Lectura semantica -------------------------------------------------

    def leer(self, item: ItemCanonico, consulta: str) -> LecturaSemantica:
        """Sujeto, polaridad, condicion y tiempo por medios lexicos (``RF-17``).

        La validacion **no se hereda de ninguna senal**: se calcula aqui, item
        a item, y por eso ``ADR002-A`` puede satisfacer ``E3`` sin recurrir a
        similitud vectorial.
        """
        return LecturaSemantica(
            sujeto=lexical.sujeto_estructural(item.subject_key, item.texto),
            polaridad=(
                Polaridad.NEGATIVA
                if lexical.polaridad_negativa(item.texto)
                else Polaridad.AFIRMATIVA
            ),
            condicion=lexical.condicion_declarada(item.texto),
            tiempo=item.created_at,
            medio="lexico-estructurado: marcadores de negacion, condicion y clave de sujeto",
        )

    # -- Senales por etapa -------------------------------------------------

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        """Candidatas de la etapa que el motor pide. Nunca de otra."""
        consulta = contexto.peticion.consulta
        terminos = lexical.terminos_significativos(consulta)
        if not terminos:
            return ()
        if contexto.etapa is Etapa.E1:
            return self._e1(contexto, terminos)
        if contexto.etapa is Etapa.E2:
            return self._e2(contexto, terminos)
        if contexto.etapa is Etapa.E3:
            return self._e3(contexto, terminos)
        if contexto.etapa is Etapa.E4:
            return self._e4(contexto, terminos)
        return ()

    def _construir(
        self,
        items: Sequence[ItemCanonico],
        contexto: ContextoDeEtapa,
        *,
        senal: str,
        razon: str,
    ) -> list[Candidata]:
        """Envuelve items en candidatas, sin repetir lo ya recuperado."""
        return [
            Candidata(
                item=item,
                etapa=contexto.etapa,
                lectura=self.leer(item, contexto.peticion.consulta),
                razon=razon,
                senal=senal,
            )
            for item in items
            if item.id not in contexto.ya_recuperados
        ]

    def _e1(self, contexto: ContextoDeEtapa, terminos: Sequence[str]) -> list[Candidata]:
        """``E1`` estructurada exacta: claves normalizadas y literal.

        Es la etapa de maxima autoridad: solo entra lo que coincide sin
        interpretacion. Empezar por aqui es lo que ``B04-RF-15`` ordena.
        """
        claves = lexical.ordenar_estable([contexto.peticion.consulta.strip(), *terminos])
        exactos = contexto.puerto.por_clave_exacta(claves)
        literales = contexto.puerto.por_termino_lexico(terminos)
        vistos = {i.id for i in exactos}
        items = [*exactos, *[i for i in literales if i.id not in vistos]]
        return self._construir(
            items,
            contexto,
            senal=MEDIOS_POR_ETAPA[Etapa.E1],
            razon="coincidencia exacta de clave o termino literal",
        )

    def _e2(self, contexto: ContextoDeEtapa, terminos: Sequence[str]) -> list[Candidata]:
        """``E2`` lexica y alias: variantes morfologicas del propio termino.

        Cubre vocabulario **sin asumir equivalencia semantica**: una variante
        es la misma palabra flexionada, no un sinonimo inferido.
        """
        expandidos = lexical.ordenar_estable(
            variante for termino in terminos for variante in lexical.variantes(termino)
        )
        nuevos = [t for t in expandidos if t not in terminos]
        if not nuevos:
            return []
        items = contexto.puerto.por_termino_lexico(nuevos)
        return self._construir(
            items,
            contexto,
            senal=MEDIOS_POR_ETAPA[Etapa.E2],
            razon="variante morfologica de un termino de la consulta",
        )

    def _e3(self, contexto: ContextoDeEtapa, terminos: Sequence[str]) -> list[Candidata]:
        """``E3`` semantica y relacional, **por medios lexico-estructurados**.

        Tres senales, ninguna vectorial:

        1. **parafrasis y dependencias** por raiz compartida entre la consulta
           y el texto del item;
        2. **relaciones** que el canon ya materializa —ambito del item—, sin
           construir ningun indice derivado;
        3. **apoyo y refutacion** conservados: la polaridad se lee item a item
           y el motor no fusiona posturas distintas.

        La validacion de sujeto, polaridad, condicion y tiempo se aplica a
        **todo** lo que esta etapa propone, que es lo que ``B04-RF-17`` exige.
        """
        raices = lexical.ordenar_estable(lexical.raiz(t) for t in terminos)
        por_raiz = contexto.puerto.por_termino_lexico(raices)
        relacionados: list[ItemCanonico] = []
        if contexto.peticion.ambito.proyectos:
            relacionados = list(contexto.puerto.por_entidad(contexto.peticion.ambito.proyectos))

        vistos: set[str] = set()
        seleccion: list[ItemCanonico] = []
        for item in [*por_raiz, *relacionados]:
            if item.id in vistos:
                continue
            # Solo entra lo que comparte raiz con la consulta o clave de
            # sujeto emparentada: sin este filtro, E3 seria un barrido.
            comparte = bool(lexical.solapamiento(terminos, item.texto))
            emparentado = any(lexical.comparten_estructura(item.subject_key, t) for t in terminos)
            if comparte or emparentado:
                vistos.add(item.id)
                seleccion.append(item)
        return self._construir(
            seleccion,
            contexto,
            senal=MEDIOS_POR_ETAPA[Etapa.E3],
            razon="parafrasis o dependencia por raiz compartida, o relacion del canon",
        )

    def _e4(self, contexto: ContextoDeEtapa, terminos: Sequence[str]) -> list[Candidata]:
        """``E4`` fuentes e historial: **evidencia atribuida**, nunca canonica.

        El puerto ya marca estos items como ``ATRIBUIDA``; este candidato no
        los eleva a verdad confirmada, que es lo que ``B04-RF-13`` prohibe.
        """
        items = contexto.puerto.historial_y_fuentes(terminos)
        return self._construir(
            items,
            contexto,
            senal=MEDIOS_POR_ETAPA[Etapa.E4],
            razon="evidencia atribuida del historial, cotejada con lo vigente",
        )


def candidato() -> CandidatoA:
    """Instancia del candidato. Sin estado ni configuracion oculta."""
    return CandidatoA()


__all__ = [
    "DEFINICION_CANONICA",
    "IDENTIFICADOR",
    "MEDIOS_POR_ETAPA",
    "SENAL_TARDIA",
    "CandidatoA",
    "candidato",
]
