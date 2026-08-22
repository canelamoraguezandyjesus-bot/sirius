"""``ADR002-C``: base lexico-estructurada + senal relacional explicita tardia.

Definicion canonica que asume (Resolucion de la particion §2):

    base lexica/estructurada y senal relacional explicita unicamente en etapas
    tardias, tras fallar la puerta de suficiencia.

**`ADR002-C` = `ADR002-A` + senal relacional tardia, por composicion.** Este
candidato **contiene** a ``CandidatoA`` y delega en el todas las etapas: la
``E1`` exacta, la ``E2`` morfologica, la expansion lexico-estructurada de
``E3``, la ``E4`` atribuida y la lectura de sujeto, polaridad, condicion y
tiempo. No copia su logica: la usa. Lo unico que anade es la expansion por
**arista explicita** dentro de ``E3``, y cualquier diferencia observable con A
que no sea esa expansion es un defecto, no una caracteristica.

La senal es **tardia de verdad**: el motor comun posee el bucle y solo pregunta
por ``E3`` tras la insuficiencia de ``E1`` y ``E2`` (``B04-RF-14``, ``RF-16``);
este candidato ademas abre el plano relacional de forma **perezosa**, de modo
que cuando las etapas tempranas bastan el plano no se abre, no se lee y no se
valida.

La relacion **no se convierte en verdad**: selecciona candidatas, que pasan por
las mismas puertas ``G1-G12``, reciben la misma lectura semantica item a item
que las de la base y conservan polaridad y condicion sin fusionarse.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

from experiments.adr002.candidates.adr002_a.candidate import CandidatoA
from experiments.adr002.candidates.adr002_c import relaciones
from experiments.adr002.candidates.common.contracts import (
    Candidata,
    ContextoDeEtapa,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
)
from experiments.adr002.candidates.common.port import IdentificadorInvalidoError

IDENTIFICADOR: Final = "ADR002-C"

#: Lo que ``ARQ-00 §23`` pone a prueba en este candidato.
SENAL_TARDIA: Final = "relacional_explicita"

DEFINICION_CANONICA: Final = (
    "base lexica/estructurada y senal relacional explicita unicamente en "
    "etapas tardias, tras fallar la puerta de suficiencia."
)


class CandidatoC:
    """La composicion: las senales de ``ADR002-A`` mas la relacional en ``E3``."""

    identificador: Final = IDENTIFICADOR

    def __init__(
        self,
        ruta_plano_relacional: Path,
        *,
        con_senal_relacional: bool = True,
        con_validacion_semantica: bool = True,
    ) -> None:
        self._base = CandidatoA(con_validacion_semantica=con_validacion_semantica)
        self._ruta_plano = ruta_plano_relacional
        self._con_senal_relacional = con_senal_relacional
        self._fuente: relaciones.FuenteRelacional | None = None
        #: Cuantas veces se consulto la ruta relacional. La activacion tardia
        #: se demuestra sobre este contador, no se promete.
        self.invocaciones_relacionales = 0

    # -- Instrumentacion ---------------------------------------------------

    @property
    def senal_tardia_habilitada(self) -> str:
        return SENAL_TARDIA

    @property
    def plano_abierto(self) -> bool:
        """Si el plano relacional llego a abrirse. Con E1/E2 suficientes: jamas."""
        return self._fuente is not None

    @property
    def registro_relacional(self) -> relaciones.RegistroRelacional | None:
        return None if self._fuente is None else self._fuente.registro

    def cerrar(self) -> None:
        if self._fuente is not None:
            self._fuente.close()
            self._fuente = None

    # -- Lectura semantica: exactamente la de la base ----------------------

    def leer(self, item: ItemCanonico, consulta: str) -> LecturaSemantica:
        """La misma lectura que ``ADR002-A``: la validacion de sujeto,
        polaridad, condicion y tiempo de lo relacional no es distinta ni mas
        laxa que la de lo lexico (``B04-RF-17``)."""
        return self._base.leer(item, consulta)

    # -- Senales por etapa ---------------------------------------------------

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        """Las de la base siempre; la senal relacional solo dentro de ``E3``."""
        de_la_base = list(self._base.candidatas(contexto))
        if contexto.etapa is not Etapa.E3 or not self._con_senal_relacional:
            return de_la_base
        ya = frozenset(c.item.id for c in de_la_base) | contexto.ya_recuperados
        return [*de_la_base, *self._relacionales(contexto, ya)]

    def _relacionales(self, contexto: ContextoDeEtapa, ya: frozenset[str]) -> list[Candidata]:
        """Un salto desde las semillas, por arista explicita y dirigida.

        Las semillas son lo ya admitido: expandir **desde lo recuperado** es lo
        que distingue una senal relacional de una segunda consulta a la
        base. Si el plano falta, esta malformado o cita elementos que el canon
        no contiene, el fallo es cerrado y tipado; no hay degradacion a «sin
        relaciones», porque sin relaciones este candidato no es este candidato.
        """
        self.invocaciones_relacionales += 1
        if self._fuente is None:
            self._fuente = relaciones.FuenteRelacional(self._ruta_plano)
        semillas = [c.item.id for c in contexto.semillas]
        aristas = [a for a in self._fuente.salientes(semillas) if a.destino_canonico not in ya]
        if not aristas:
            return []
        destinos = tuple(dict.fromkeys(a.destino_canonico for a in aristas if a.destino_canonico))
        try:
            materializacion = contexto.puerto.por_identificadores(destinos)
        except IdentificadorInvalidoError as error:
            msg = (
                "el plano relacional cita identidades que el puerto canonico "
                "rechaza; un grafo que nombra identidades no canonicas no es "
                "utilizable"
            )
            raise relaciones.RelacionInconsistenteError(msg) from error
        if materializacion.ausentes:
            msg = (
                "el plano relacional cita elementos que el canon no contiene: "
                f"{', '.join(materializacion.ausentes)}; un grafo que afirma "
                "elementos inexistentes no es utilizable"
            )
            raise relaciones.RelacionInconsistenteError(msg)
        por_identidad = {item.id: item for item in materializacion.items}
        return [
            Candidata(
                item=por_identidad[arista.destino_canonico],
                etapa=contexto.etapa,
                lectura=self.leer(
                    por_identidad[arista.destino_canonico], contexto.peticion.consulta
                ),
                razon=(
                    f"relacion explicita {arista.tipo} a un salto desde {arista.origen_canonico}"
                ),
                senal=f"relacional_explicita: {arista.tipo} por {arista.id}",
            )
            for arista in aristas
            if arista.destino_canonico in por_identidad
        ]


def candidato(
    ruta_plano_relacional: Path,
    *,
    con_senal_relacional: bool = True,
    con_validacion_semantica: bool = True,
) -> CandidatoC:
    """Instancia del candidato. Su unica configuracion son la ruta del plano y
    el interruptor de ablacion, y las dos estan declaradas."""
    return CandidatoC(
        ruta_plano_relacional,
        con_senal_relacional=con_senal_relacional,
        con_validacion_semantica=con_validacion_semantica,
    )


__all__ = [
    "DEFINICION_CANONICA",
    "IDENTIFICADOR",
    "SENAL_TARDIA",
    "CandidatoC",
    "candidato",
]
