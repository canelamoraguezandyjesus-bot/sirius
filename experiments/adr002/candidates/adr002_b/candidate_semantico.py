"""``ADR002-B-SEM``: la base de ``A`` con semantica **real** como senal tardia.

Es ``ADR002-B`` con una sola cosa cambiada, y por eso es una falsacion limpia:
donde ``B`` pone coocurrencia PPMI **calculada sobre este mismo corpus**, aqui
va un modelo entrenado **fuera** de el. Todo lo demas —la base lexica de ``A``,
las etapas, las puertas, la lectura de polaridad, la materializacion por
identidad, el fallo cerrado— es identico, de modo que cualquier diferencia
observable es atribuible a la senal y a nada mas.

POR QUE HACE FALTA UN CANDIDATO NUEVO Y NO UN INTERRUPTOR EN ``B``
=================================================================

``ADR002-B`` esta **congelado** con su ficha, y ``ADR002-C`` es la linea base
contra la que hay que comparar. Tocar ``candidate.py`` para meter un modo mas
obligaria a emitir ficha sucesora y a repetir la ronda **antes** de saber si la
senal sirve para algo. Aqui el orden es el contrario: primero la evidencia,
despues el congelado. Este modulo no importa nada de ``B`` salvo su sidecar
hermano, y ``candidate.py`` queda byte a byte.

LO QUE ESTE CANDIDATO NO PUEDE VER
==================================

No recibe el plano reservado, no lee ``criticidad.razon_segura`` y no conoce el
banco. El texto que se indexa es el del canon, tal como el puerto lo entrega.
Esa frontera es la que hace que un buen resultado signifique algo.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

from experiments.adr002.candidates.adr002_a.candidate import CandidatoA
from experiments.adr002.candidates.adr002_b import semantica
from experiments.adr002.candidates.common.contracts import (
    Candidata,
    ContextoDeEtapa,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
)
from experiments.adr002.candidates.common.port import IdentificadorInvalidoError

IDENTIFICADOR: Final = "ADR002-B-SEM"

#: Lo que este candidato pone a prueba, y que ``ARQ-00 §23`` dejo sin decidir.
SENAL_TARDIA: Final = "semantica_real_externa"

DEFINICION_CANONICA: Final = (
    "expansion escalonada lexica/estructurada con senal semantica de modelo "
    "externo unicamente en etapas tardias tras fallar la puerta de suficiencia."
)


class CandidatoBSemantico:
    """La base de ``A`` mas la senal semantica real, solo en ``E3``.

    Igual que ``B``, abre el indice de forma **perezosa**: si ``E1`` y ``E2``
    bastan, el sidecar no se abre, no se lee y no se verifica. La activacion
    tardia se demuestra sobre el contador, no se promete.
    """

    identificador: Final = IDENTIFICADOR

    def __init__(
        self,
        ruta_canon: Path,
        ruta_sidecar: Path,
        codificador: semantica.CodificadorSemantico,
        *,
        con_senal_semantica: bool = True,
        k: int = semantica.TOP_K,
        coseno_minimo: float = semantica.COSENO_MINIMO,
    ) -> None:
        self._base = CandidatoA()
        self._ruta_canon = ruta_canon
        self._ruta_sidecar = ruta_sidecar
        self._codificador = codificador
        self._con_senal_semantica = con_senal_semantica
        self._k = k
        self._coseno_minimo = coseno_minimo
        self._lector: semantica.LectorSemantico | None = None
        #: Cuantas veces se consulto la ruta semantica. Instrumentacion, no promesa.
        self.invocaciones_semanticas = 0

    @property
    def senal_tardia_habilitada(self) -> str:
        return SENAL_TARDIA

    @property
    def indice_abierto(self) -> bool:
        """Si el sidecar llego a abrirse. Con ``E1``/``E2`` suficientes: jamas."""
        return self._lector is not None

    def close(self) -> None:
        if self._lector is not None:
            self._lector.close()
            self._lector = None

    def leer(self, item: ItemCanonico, consulta: str) -> LecturaSemantica:
        """La misma lectura que ``ADR002-A``. La senal no relaja ``RF-17``."""
        return self._base.leer(item, consulta)

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        """Las de la base siempre; la senal semantica solo dentro de ``E3``."""
        de_la_base = list(self._base.candidatas(contexto))
        if contexto.etapa is not Etapa.E3 or not self._con_senal_semantica:
            return de_la_base
        ya = contexto.ya_recuperados | frozenset(c.item.id for c in de_la_base)
        return [*de_la_base, *self._semanticas(contexto, ya)]

    def _semanticas(self, contexto: ContextoDeEtapa, ya: frozenset[str]) -> list[Candidata]:
        """Identidades del indice, contenido del puerto. Falla cerrado.

        La similitud **no se convierte en identidad ni en verdad**: selecciona
        candidatas que despues pasan por las mismas puertas y reciben la misma
        lectura item a item que las de la base.
        """
        self.invocaciones_semanticas += 1
        if self._lector is None:
            self._lector = semantica.LectorSemantico(
                self._ruta_sidecar, self._ruta_canon, self._codificador
            )
        coincidencias = [
            c
            for c in self._lector.consultar(
                contexto.peticion.consulta, k=self._k + len(ya), minimo=self._coseno_minimo
            )
            if c.identidad not in ya
        ][: self._k]
        if not coincidencias:
            return []
        try:
            materializacion = contexto.puerto.por_identificadores(
                tuple(c.identidad for c in coincidencias)
            )
        except IdentificadorInvalidoError as error:
            msg = (
                "el indice semantico entrego identidades que el puerto canonico "
                "rechaza; un indice que cita identidades no canonicas no es utilizable"
            )
            raise semantica.IndiceCorruptoError(msg) from error
        if materializacion.ausentes:
            msg = (
                "el indice semantico cita identidades que el canon no contiene: "
                f"{', '.join(materializacion.ausentes)}; un derivado que afirma "
                "elementos inexistentes no es utilizable"
            )
            raise semantica.IndiceNoUtilizableError(msg)
        por_identidad = {item.id: item for item in materializacion.items}
        return [
            Candidata(
                item=por_identidad[c.identidad],
                etapa=contexto.etapa,
                lectura=self.leer(por_identidad[c.identidad], contexto.peticion.consulta),
                razon="proximidad semantica con la consulta segun un modelo externo al corpus",
                senal=f"{SENAL_TARDIA}: coseno {c.similitud:.3f}",
            )
            for c in coincidencias
        ]


__all__ = ["DEFINICION_CANONICA", "IDENTIFICADOR", "SENAL_TARDIA", "CandidatoBSemantico"]
