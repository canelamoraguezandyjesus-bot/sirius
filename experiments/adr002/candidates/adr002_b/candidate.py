"""``ADR002-B``: base lexico-estructurada + senal semantica vectorial tardia.

Definicion canonica que asume (``ARQ-00 §23``):

    expansion escalonada lexica/estructurada con senal semantica vectorial
    unicamente en etapas tardias tras fallar la puerta de suficiencia.

**`ADR002-B` = `ADR002-A` v2 + senal vectorial tardia, por composicion.** Este
candidato **contiene** a ``CandidatoA`` y delega en el todas las etapas: la
``E1`` exacta, la ``E2`` morfologica, la expansion lexico-estructurada de
``E3``, la ``E4`` atribuida y la lectura de sujeto, polaridad, condicion y
tiempo. No copia su logica: la usa. Lo unico que anade es la senal vectorial
dentro de ``E3``, y por eso cualquier diferencia observable con A que no sea
esa senal es un defecto, no una caracteristica.

La senal es **tardia de verdad**: el motor comun posee el bucle y solo
pregunta por ``E3`` tras la insuficiencia de ``E1`` y ``E2`` (B04-RF-14,
RF-16); este candidato ademas abre el indice de forma **perezosa**, de modo
que cuando las etapas tempranas bastan el sidecar no se abre, no se lee y no
se verifica: cero trabajo adelantado, comprobable por instrumentacion.

La similitud **no se convierte en identidad ni en verdad** (salida normativa
de ``E3``): selecciona candidatas, que pasan por las mismas puertas
``G1-G12``, reciben la misma lectura semantica item a item que las de la base
y conservan polaridad y condicion sin fusionarse (RF-17, RF-19).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.candidates.adr002_a.candidate import CandidatoA
from experiments.adr002.candidates.adr002_b import vectores
from experiments.adr002.candidates.common.contracts import (
    Candidata,
    ContextoDeEtapa,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
)

IDENTIFICADOR: Final = "ADR002-B"

#: Lo que ``ARQ-00 §23`` pone a prueba en este candidato.
SENAL_TARDIA: Final = "semantica_vectorial"

DEFINICION_CANONICA: Final = (
    "expansion escalonada lexica/estructurada con senal semantica vectorial "
    "unicamente en etapas tardias tras fallar la puerta de suficiencia."
)


class CandidatoB:
    """La composicion: las senales de ``ADR002-A`` mas la vectorial en ``E3``.

    No implementa el motor, ni las puertas, ni el orden de etapas, ni la base
    lexico-estructurada: los recibe. Lo unico propio es **que anade** cuando
    el motor pregunta por ``E3``.
    """

    identificador: Final = IDENTIFICADOR

    def __init__(
        self,
        ruta_canon: Path,
        ruta_sidecar: Path,
        *,
        con_senal_vectorial: bool = True,
    ) -> None:
        self._base = CandidatoA()
        self._ruta_canon = ruta_canon
        self._ruta_sidecar = ruta_sidecar
        self._con_senal_vectorial = con_senal_vectorial
        self._lector: vectores.LectorVectorial | None = None
        #: Cuantas veces se consulto la ruta vectorial. La activacion tardia
        #: se demuestra sobre este contador, no se promete.
        self.invocaciones_vectoriales = 0

    # -- Instrumentacion ---------------------------------------------------

    @property
    def senal_tardia_habilitada(self) -> str:
        """``semantica_vectorial``: la senal que distingue a esta alternativa."""
        return SENAL_TARDIA

    @property
    def indice_abierto(self) -> bool:
        """Si el sidecar llego a abrirse. Con E1/E2 suficientes: jamas."""
        return self._lector is not None

    @property
    def registro_vectorial(self) -> vectores.RegistroVectorial | None:
        """Las consultas vectoriales realmente ejecutadas, si el indice abrio."""
        return None if self._lector is None else self._lector.registro

    # -- Lectura semantica: exactamente la de la base ----------------------

    def leer(self, item: ItemCanonico, consulta: str) -> LecturaSemantica:
        """La misma lectura que ``ADR002-A``: la validacion de sujeto,
        polaridad, condicion y tiempo de lo vectorial no es distinta ni mas
        laxa que la de lo lexico (``B04-RF-17``)."""
        return self._base.leer(item, consulta)

    # -- Senales por etapa ---------------------------------------------------

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        """Las de la base siempre; la senal vectorial solo dentro de ``E3``."""
        de_la_base = list(self._base.candidatas(contexto))
        if contexto.etapa is not Etapa.E3 or not self._con_senal_vectorial:
            return de_la_base
        ids_de_la_base = frozenset(candidata.item.id for candidata in de_la_base)
        return [*de_la_base, *self._vectoriales(contexto, ids_de_la_base)]

    def _vectoriales(
        self, contexto: ContextoDeEtapa, ids_de_la_base: frozenset[str]
    ) -> list[Candidata]:
        """La senal vectorial: identidades del indice, contenido del puerto.

        La apertura del lector ocurre AQUI, en la primera consulta real, y en
        ningun otro sitio: si el indice falta, esta corrupto o esta desfasado,
        el fallo es cerrado y tipado. No hay degradacion a «sin vector».

        La materializacion es **por identidad canonica exacta**: se piden al
        puerto los mismos identificadores que el sidecar devolvio, nunca sus
        claves de sujeto —una clave vacia, duplicada o con mas de 512 filas
        no puede perder una coincidencia, porque la clave ya no decide que
        fila se recupera (paquete de correccion 02)—. Si el canon no contiene
        alguna de esas identidades, el derivado esta inconsistente y se falla
        cerrado: ninguna recuperacion parcial, ninguna continuacion callada.
        """
        self.invocaciones_vectoriales += 1
        if self._lector is None:
            self._lector = vectores.LectorVectorial(self._ruta_canon, self._ruta_sidecar)
        terminos = lexical.terminos_significativos(contexto.peticion.consulta)
        coincidencias = self._lector.consultar(
            terminos[: vectores.CONSULTA_TERMINOS_MAXIMOS],
            excluidos=contexto.ya_recuperados | ids_de_la_base,
        )
        if not coincidencias:
            return []
        materializacion = contexto.puerto.por_identificadores(
            tuple(coincidencia.elemento for coincidencia in coincidencias)
        )
        if materializacion.ausentes:
            msg = (
                "el indice vectorial cita identidades que el canon no contiene: "
                f"{', '.join(materializacion.ausentes)}; un derivado que afirma "
                "elementos inexistentes no es utilizable"
            )
            raise vectores.IndiceInconsistenteError(msg)
        por_identidad = {item.id: item for item in materializacion.items}
        return [
            Candidata(
                item=por_identidad[coincidencia.elemento],
                etapa=contexto.etapa,
                lectura=self.leer(por_identidad[coincidencia.elemento], contexto.peticion.consulta),
                razon=(f"similitud distribucional con la consulta en banda {coincidencia.banda}"),
                senal=f"semantica_vectorial: coseno ppmi en banda {coincidencia.banda}",
            )
            for coincidencia in coincidencias
        ]


def candidato(
    ruta_canon: Path, ruta_sidecar: Path, *, con_senal_vectorial: bool = True
) -> CandidatoB:
    """Instancia del candidato. Su unica configuracion son las dos rutas y el
    interruptor de ablacion, y las tres estan declaradas."""
    return CandidatoB(ruta_canon, ruta_sidecar, con_senal_vectorial=con_senal_vectorial)


__all__ = [
    "DEFINICION_CANONICA",
    "IDENTIFICADOR",
    "SENAL_TARDIA",
    "CandidatoB",
    "candidato",
]
