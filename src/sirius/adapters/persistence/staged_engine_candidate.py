"""Fuente de candidatas léxico-estructurada del motor por etapas. Portado
desde ``experiments/adr002/candidates/adr002_a/candidate.py`` (rama
``evidence/adr001-spikes``, PR #117; el candidato allí se llama
``ADR002-A``), incidencia #457/ADR-109.

Es la única fuente de candidatas que Sirius 0.1 instancia: expansión
escalonada solo léxica y estructurada en las cuatro etapas de expansión
(``E1-E4``), sin ninguna señal semántica vectorial. No implementa el motor,
ni las puertas, ni el orden de etapas — los recibe de
``sirius.domain.staged_engine``. Lo único que decide es qué propone cuando
el motor le pregunta por una etapa.

Desde ADR-168 (hueco H1 de ADR-148) tiene una señal que no es léxica:
``E3`` propone además lo vigente en la ventana cuando la petición declara un
intervalo de vigencia. No es una excepción al párrafo anterior sino su
límite medido: una pregunta cuyo único criterio es un intervalo —«¿qué
decisiones eran válidas entre enero y marzo?»— no da ninguna palabra de la
que partir, y sin esa señal no tiene camino de entrada por ninguna de las
cuatro etapas.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from sirius.adapters.persistence import lexical_query_treatment as lexical
from sirius.domain.staged_engine_contracts import (
    Candidata,
    ContextoDeEtapa,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
    Polaridad,
)

IDENTIFICADOR: Final = "sirius-lexico-estructurado"

#: Lo que este candidato no habilita: ninguna señal tardía adicional.
SENAL_TARDIA: Final = "ninguna_adicional"

#: Cotas de la expansión de ``E3``. Acotan el trabajo antes de pedirlo.
TERMINOS_PUENTE_MAXIMOS: Final = 8
FAMILIAS_MAXIMAS: Final = 4
PREFIJO_MINIMO: Final = 3

#: Medios con los que este candidato satisface cada etapa.
MEDIOS_POR_ETAPA: Final[dict[Etapa, str]] = {
    Etapa.E1: "clave de sujeto normalizada y coincidencia literal del indice lexico medido",
    Etapa.E2: "variantes morfologicas por recorte de sufijo flexivo y raiz compartida",
    Etapa.E3: (
        "expansion desde lo ya recuperado: terminos puente de las semillas y familias de "
        "sujeto por prefijo, ambos consultados de forma dirigida"
    ),
    Etapa.E4: "historial y fuentes como evidencia atribuida, cotejada con lo vigente",
}

#: Medio de la TERCERA señal de ``E3`` (ADR-168), la única de este candidato
#: que no parte de una palabra: la ventana de vigencia que la propia petición
#: declara. No está en ``MEDIOS_POR_ETAPA`` a propósito — ese mapa dice con
#: qué medio se satisface cada etapa, y esta señal convive con los otros dos
#: medios de ``E3`` en vez de sustituirlos.
MEDIO_POR_VIGENCIA: Final = (
    "ventana de vigencia declarada por la peticion, consultada de forma dirigida"
)


class CandidatoLexicoEstructurado:
    """Las señales léxico-estructuradas, etapa por etapa."""

    identificador: Final = IDENTIFICADOR

    @property
    def senal_tardia_habilitada(self) -> str:
        return SENAL_TARDIA

    # -- Lectura semántica ---------------------------------------------

    def leer(self, item: ItemCanonico, consulta: str) -> LecturaSemantica:
        """Sujeto, polaridad, condición y tiempo por medios léxicos."""
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

    # -- Señales por etapa -----------------------------------------------

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        """Candidatas de la etapa que el motor pide. Nunca de otra.

        ``E3`` se pregunta aunque la consulta no deje ningún término
        significativo (ADR-168): su señal por vigencia no sale del texto sino
        de la ventana que la petición declara, y salir antes por «no hay
        palabras» era exactamente lo que dejaba sin camino de entrada a una
        pregunta cuyo único criterio es la vigencia.
        """
        consulta = contexto.peticion.consulta
        terminos = lexical.terminos_significativos(consulta)
        if contexto.etapa is Etapa.E3:
            return self._e3(contexto, terminos)
        if not terminos:
            return ()
        if contexto.etapa is Etapa.E1:
            return self._e1(contexto, terminos)
        if contexto.etapa is Etapa.E2:
            return self._e2(contexto, terminos)
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
        """``E1`` estructurada exacta: claves normalizadas y literal."""
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
        """``E2`` léxica y alias: variantes morfológicas del propio término.

        Repartidas entre los términos, no amontonadas por el primero: el
        puerto acota los argumentos, y repartir por rondas garantiza que
        cada término conserve al menos su primera variante mientras quepa
        alguna.
        """
        por_termino = [
            [v for v in lexical.ordenar_estable(lexical.variantes(termino)) if v not in terminos]
            for termino in terminos
        ]
        nuevos = [
            variantes[ronda]
            for ronda in range(max((len(v) for v in por_termino), default=0))
            for variantes in por_termino
            if ronda < len(variantes)
        ]
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
        """``E3`` semántica y relacional, por medios léxico-estructurados.

        Tres señales dirigidas. Dos expanden desde lo ya recuperado —a
        diferencia de ``E2``, que expande la consulta—: términos puente
        (vocabulario discriminante de las semillas ausente de la consulta) y
        familias de sujeto (prefijos estructurales de las claves de las
        semillas). La tercera (ADR-168) expande desde lo que la **petición**
        declara: la ventana de vigencia, cuando la pregunta declara un
        intervalo en vez de un instante. Ninguna enumera un espacio: el
        ámbito no genera candidatas, filtra en ``G4``.

        La señal por vigencia va delante de las otras dos dentro de la etapa
        porque no depende de qué se haya recuperado antes; el motor las trata
        igual (misma etapa, misma autoridad de orden) y deduplica por
        identidad, así que esta posición solo decide cuál de las dos razones
        se registra cuando un mismo ítem cae por las dos señales.
        """
        por_vigencia = self._por_vigencia(contexto)
        vistos = {c.item.id for c in por_vigencia}
        if not contexto.semillas:
            return por_vigencia

        puente = self._terminos_puente(contexto, terminos)
        familias = self._familias_de_sujeto(contexto)
        if not puente and not familias:
            return por_vigencia

        por_puente = contexto.puerto.por_termino_lexico(puente) if puente else ()
        por_familia = contexto.puerto.por_prefijo_de_sujeto(familias) if familias else ()

        seleccion: list[ItemCanonico] = []
        for item in [*por_puente, *por_familia]:
            if item.id in vistos or item.id in contexto.ya_recuperados:
                continue
            vistos.add(item.id)
            seleccion.append(item)
        return [
            *por_vigencia,
            *self._construir(
                seleccion,
                contexto,
                senal=MEDIOS_POR_ETAPA[Etapa.E3],
                razon="dependencia con lo ya recuperado por termino puente o familia de sujeto",
            ),
        ]

    def _por_vigencia(self, contexto: ContextoDeEtapa) -> list[Candidata]:
        """Lo vigente en la ventana, cuando la petición declara un intervalo.

        Es el camino de entrada que faltaba (hueco H1 de ADR-148): una
        pregunta cuyo único criterio es un intervalo de vigencia no aporta
        ninguna palabra de la que partir, y las otras señales de este
        candidato son todas léxicas. Sin intervalo declarado —46 de los 47
        casos del banco y toda pregunta ordinaria de producción— esta señal
        no aporta nada y ``E3`` se comporta exactamente como antes.

        No sustituye a ninguna señal léxica: **añade**. Lo que la búsqueda
        léxica ya encontraba lo sigue encontrando, y antes, porque lo aportan
        ``E1``/``E2``, cuya autoridad de orden es mayor que la de ``E3``
        (``staged_engine._clave_de_orden``).
        """
        intervalo = contexto.peticion.ventana.intervalo_de_vigencia
        if intervalo is None:
            return []
        desde, hasta = intervalo
        return self._construir(
            contexto.puerto.por_ventana_de_vigencia(desde, hasta),
            contexto,
            senal=MEDIO_POR_VIGENCIA,
            razon=(
                "decision aprobada cuyo registro no es posterior al final de la "
                f"ventana declarada por la peticion ({desde} a {hasta})"
            ),
        )

    def _terminos_puente(self, contexto: ContextoDeEtapa, terminos: Sequence[str]) -> list[str]:
        """Vocabulario de las semillas que la consulta no contiene."""
        de_la_consulta = set(terminos)
        for termino in terminos:
            de_la_consulta.update(lexical.variantes(termino))
        raices_consulta = {lexical.raiz(t) for t in terminos}

        puente: list[str] = []
        for semilla in contexto.semillas:
            for token in lexical.terminos_significativos(semilla.item.texto):
                if token in de_la_consulta or lexical.raiz(token) in raices_consulta:
                    continue
                if token not in puente:
                    puente.append(token)
        return sorted(puente)[:TERMINOS_PUENTE_MAXIMOS]

    def _familias_de_sujeto(self, contexto: ContextoDeEtapa) -> list[str]:
        """Prefijos estructurales de las claves de sujeto de las semillas."""
        familias: list[str] = []
        for semilla in contexto.semillas:
            prefijo = lexical.plegar(semilla.item.subject_key or "").split("-")[0]
            if len(prefijo) >= PREFIJO_MINIMO and prefijo not in familias:
                familias.append(prefijo)
        return sorted(familias)[:FAMILIAS_MAXIMAS]

    def _e4(self, contexto: ContextoDeEtapa, terminos: Sequence[str]) -> list[Candidata]:
        """``E4`` fuentes e historial: evidencia atribuida, nunca canónica."""
        items = contexto.puerto.historial_y_fuentes(terminos)
        return self._construir(
            items,
            contexto,
            senal=MEDIOS_POR_ETAPA[Etapa.E4],
            razon="evidencia atribuida del historial, cotejada con lo vigente",
        )


def candidato() -> CandidatoLexicoEstructurado:
    """Instancia de la fuente de candidatas léxico-estructurada."""
    return CandidatoLexicoEstructurado()


__all__ = [
    "IDENTIFICADOR",
    "MEDIOS_POR_ETAPA",
    "MEDIO_POR_VIGENCIA",
    "SENAL_TARDIA",
    "CandidatoLexicoEstructurado",
    "candidato",
]
