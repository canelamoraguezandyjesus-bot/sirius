"""``ADR002-D``: semantica y relacional **separadas**, en etapas tardias distintas.

Definicion canonica que asume (``ARQ-00 §23``, Resolucion de la particion §2):

    ambas senales en etapas tardias distintas, con orden predefinido y sin
    coordinacion simultanea fuera de la etapa autorizada.

**`ADR002-D` no es «B mas C».** La Resolucion de la particion §7 lo dice
expresamente y le impone **tres restricciones acumulativas**, las tres
obligatorias:

1. las senales semantica y relacional actuan en **etapas tardias distintas**;
2. con **orden predefinido**, declarado y congelado **antes** de ejecutar;
3. **nunca coordinacion simultanea** fuera de la etapa autorizada.

El orden esta congelado por
``SIRIUS_0.2_ADR_002_ORDEN_CONGELADO_DE_LAS_ETAPAS_TARDIAS_DE_ADR002_D_v1.0``,
en un commit **anterior** a este: ``E3`` relacional, ``E4`` vectorial. Aqui no
se elige nada; aqui se obedece, y ``ORDEN_CONGELADO`` es la unica tabla que
decide que senal puede correr en que etapa.

**Composicion, no copia.** Este candidato contiene a ``CandidatoA`` y delega
en el las cuatro etapas y la lectura semantica. La senal relacional es la
fuente de ``ADR002-C``, y la vectorial el lector de ``ADR002-B``: se **usan**
tal cual, sin reimplementarlas, para que la unica diferencia entre `D` y sus
vecinos sea **donde** actua cada senal, nunca **que** senal es.

**La restriccion 3 se hace estructural, no se promete.** Un unico despachador
consulta ``SENAL_DE_LA_ETAPA``, de modo que una etapa tiene como mucho una
senal tardia; y un guardia de reentrada aborta si alguna vez hubiese dos
activas a la vez. Cada ejecucion deja ademas su ``orden_observado``, que debe
ser prefijo del orden congelado: si no lo fuera, la ejecucion no seria de
``ADR002-D``.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.candidates.adr002_a.candidate import CandidatoA
from experiments.adr002.candidates.adr002_b import vectores
from experiments.adr002.candidates.adr002_c import relaciones
from experiments.adr002.candidates.common.contracts import (
    Candidata,
    ContextoDeEtapa,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
)
from experiments.adr002.candidates.common.port import IdentificadorInvalidoError

IDENTIFICADOR: Final = "ADR002-D"

#: Lo que ``ARQ-00 §23`` pone a prueba en este candidato.
SENAL_TARDIA: Final = "ambas_en_etapas_distintas"

DEFINICION_CANONICA: Final = (
    "ambas senales en etapas tardias distintas, con orden predefinido y sin "
    "coordinacion simultanea fuera de la etapa autorizada."
)

SENAL_RELACIONAL: Final = "relacional_explicita"
SENAL_VECTORIAL: Final = "semantica_vectorial"

#: El orden congelado, copiado del acta que lo fijo en un commit anterior.
#: Es una tupla, no una lista: no hay ruta por la que una ejecucion lo altere.
ORDEN_CONGELADO: Final[tuple[tuple[Etapa, str], ...]] = (
    (Etapa.E3, SENAL_RELACIONAL),
    (Etapa.E4, SENAL_VECTORIAL),
)

#: La misma tabla, indexada por etapa. Que sea un diccionario construido
#: **desde** ``ORDEN_CONGELADO`` es lo que garantiza que no puedan discrepar:
#: una etapa tiene a lo sumo una senal tardia, y es la del orden.
SENAL_DE_LA_ETAPA: Final[dict[Etapa, str]] = dict(ORDEN_CONGELADO)

#: Documento que congelo el orden, antes de que existiera este modulo.
ACTA_DEL_ORDEN: Final = (
    "SIRIUS_0.2_ADR_002_ORDEN_CONGELADO_DE_LAS_ETAPAS_TARDIAS_DE_ADR002_D_v1.0.md"
)


def _es_subsecuencia(
    observado: Sequence[tuple[Etapa, str]], congelado: Sequence[tuple[Etapa, str]]
) -> bool:
    """``observado`` aparece dentro de ``congelado`` conservando el orden."""
    pendiente = iter(congelado)
    return all(paso in pendiente for paso in observado)


class OrdenDeSenalesVioladoError(RuntimeError):
    """Se pidio una senal tardia fuera de su etapa congelada, o dos a la vez.

    Es un fallo **cerrado**: una ejecucion que coordine ambas senales, o que
    las corra en otro orden, no es una ejecucion de ``ADR002-D`` y no puede
    entregarse como si lo fuera.
    """


class CandidatoD:
    """Las senales de ``ADR002-A``, mas una tardia por etapa, en orden congelado.

    No implementa el motor, ni las puertas, ni el orden de etapas: los recibe.
    Lo unico propio es **que anade** y, sobre todo, **donde**.
    """

    identificador: Final = IDENTIFICADOR

    def __init__(
        self,
        ruta_canon: Path,
        ruta_sidecar: Path,
        ruta_plano_relacional: Path,
        *,
        con_senal_relacional: bool = True,
        con_senal_vectorial: bool = True,
    ) -> None:
        self._base = CandidatoA()
        self._ruta_canon = ruta_canon
        self._ruta_sidecar = ruta_sidecar
        self._ruta_plano = ruta_plano_relacional
        self._con_senal_relacional = con_senal_relacional
        self._con_senal_vectorial = con_senal_vectorial
        self._fuente: relaciones.FuenteRelacional | None = None
        self._lector: vectores.LectorVectorial | None = None
        #: Guardia de la restriccion 3: nombre de la senal tardia en curso.
        self._senal_en_curso: str | None = None
        #: ``(etapa, senal)`` de cada senal tardia realmente ejecutada, en el
        #: orden en que ocurrio. La restriccion se demuestra sobre esto.
        self._orden_observado: list[tuple[Etapa, str]] = []
        #: Cuantas veces se consulto cada ruta tardia. La activacion tardia se
        #: demuestra sobre estos contadores, no se promete.
        self.invocaciones_relacionales = 0
        self.invocaciones_vectoriales = 0

    # -- Instrumentacion ---------------------------------------------------

    @property
    def senal_tardia_habilitada(self) -> str:
        return SENAL_TARDIA

    @property
    def orden_observado(self) -> tuple[tuple[Etapa, str], ...]:
        """Lo que esta ejecucion hizo de verdad, en su orden real."""
        return tuple(self._orden_observado)

    @property
    def orden_respetado(self) -> bool:
        """El observado debe ser **subsecuencia** del congelado.

        Subsecuencia y no igualdad ni prefijo, y las dos razones por las que
        una senal puede faltar son legitimas y distintas:

        - **la politica escalonada**: una peticion que se satisface en ``E3``
          nunca llega a ``E4``, y esa ausencia es el contrato funcionando;
        - **una ablacion**: apagar una senal para poder falsarla la retira de
          su etapa sin mover nada, y con ``E3`` apagada lo observado empieza
          por ``E4`` — legitimo, pero no un prefijo.

        Lo que si es violacion, y esto lo detecta: una senal en una etapa que
        no es la suya, o ``E4`` antes que ``E3``. Ninguna ausencia reordena
        nada; lo unico prohibido es alterar el orden relativo.
        """
        return _es_subsecuencia(self.orden_observado, ORDEN_CONGELADO)

    @property
    def plano_abierto(self) -> bool:
        """Si el plano relacional llego a abrirse. Con ``E1``/``E2`` suficientes: jamas."""
        return self._fuente is not None

    @property
    def indice_abierto(self) -> bool:
        """Si el sidecar vectorial llego a abrirse. Con ``E3`` suficiente: jamas."""
        return self._lector is not None

    @property
    def registro_relacional(self) -> relaciones.RegistroRelacional | None:
        return None if self._fuente is None else self._fuente.registro

    @property
    def registro_vectorial(self) -> vectores.RegistroVectorial | None:
        return None if self._lector is None else self._lector.registro

    def cerrar(self) -> None:
        if self._fuente is not None:
            self._fuente.close()
            self._fuente = None
        if self._lector is not None:
            self._lector.close()
            self._lector = None

    # -- Lectura semantica: exactamente la de la base ----------------------

    def leer(self, item: ItemCanonico, consulta: str) -> LecturaSemantica:
        """La misma lectura que ``ADR002-A``, para las dos senales por igual.

        Que lo relacional y lo vectorial se validen con la MISMA lectura es lo
        que impide que una de las dos entre por una puerta mas laxa
        (``B04-RF-17``).
        """
        return self._base.leer(item, consulta)

    # -- Senales por etapa ---------------------------------------------------

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        """Las de la base siempre; **una** senal tardia, la de esta etapa.

        El despachador es unico y lee ``SENAL_DE_LA_ETAPA``. No hay rama que
        pueda encender dos senales en la misma etapa, porque no hay dos
        entradas para una misma etapa: el diccionario se construye desde el
        orden congelado.
        """
        de_la_base = list(self._base.candidatas(contexto))
        senal = SENAL_DE_LA_ETAPA.get(contexto.etapa)
        if senal is None:
            return de_la_base
        ya = frozenset(c.item.id for c in de_la_base) | contexto.ya_recuperados
        return [*de_la_base, *self._tardias(senal, contexto, ya)]

    def _tardias(
        self, senal: str, contexto: ContextoDeEtapa, ya: frozenset[str]
    ) -> list[Candidata]:
        """Ejecuta la senal tardia de esta etapa, con el guardia de la restriccion 3."""
        if SENAL_DE_LA_ETAPA.get(contexto.etapa) != senal:
            # Defensa en profundidad: hoy es imposible llegar aqui con una
            # senal ajena, porque el despachador la saca de esta misma tabla.
            # Se comprueba igual, porque es exactamente lo que hay que
            # proteger y una refactorizacion futura podria separarlos.
            msg = (
                f"senal fuera de su etapa congelada: {senal} se pidio en {contexto.etapa.value}, "
                f"y su puesto es {ORDEN_CONGELADO}"
            )
            raise OrdenDeSenalesVioladoError(msg)
        if senal == SENAL_RELACIONAL and not self._con_senal_relacional:
            return []
        if senal == SENAL_VECTORIAL and not self._con_senal_vectorial:
            return []
        if self._senal_en_curso is not None:
            msg = (
                f"coordinacion simultanea: {senal} se pidio con {self._senal_en_curso} "
                f"todavia activa; ADR002-D separa sus dos senales tardias y B04-D15 "
                f"prohibe coordinarlas"
            )
            raise OrdenDeSenalesVioladoError(msg)
        self._senal_en_curso = senal
        try:
            aportadas = (
                self._relacionales(contexto, ya)
                if senal == SENAL_RELACIONAL
                else self._vectoriales(contexto, ya)
            )
        finally:
            self._senal_en_curso = None
        self._orden_observado.append((contexto.etapa, senal))
        if not self.orden_respetado:
            msg = (
                f"orden de etapas tardias violado: se observo {self.orden_observado} y el "
                f"orden congelado por {ACTA_DEL_ORDEN} es {ORDEN_CONGELADO}"
            )
            raise OrdenDeSenalesVioladoError(msg)
        return aportadas

    # -- Primera senal tardia: relacional explicita, en E3 ------------------

    def _relacionales(self, contexto: ContextoDeEtapa, ya: frozenset[str]) -> list[Candidata]:
        """Un salto desde las semillas, por arista explicita y dirigida.

        Es la senal de ``ADR002-C``, con su misma fuente y sus mismas cotas.
        Si el plano falta, esta malformado o cita elementos que el canon no
        contiene, el fallo es cerrado y tipado: sin relaciones, esta mitad de
        ``ADR002-D`` no existe, y degradarla a «sin relaciones» convertiria al
        candidato en otro sin avisar.
        """
        self.invocaciones_relacionales += 1
        if self._fuente is None:
            self._fuente = relaciones.FuenteRelacional(self._ruta_plano)
        aristas = [
            a
            for a in self._fuente.salientes([c.item.id for c in contexto.semillas])
            if a.destino_canonico not in ya
        ]
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
                senal=f"{SENAL_RELACIONAL}: {arista.tipo} por {arista.id}",
            )
            for arista in aristas
            if arista.destino_canonico in por_identidad
        ]

    # -- Segunda senal tardia: semantica vectorial, en E4 -------------------

    def _vectoriales(self, contexto: ContextoDeEtapa, ya: frozenset[str]) -> list[Candidata]:
        """Similitud distribucional del indice local, materializada por identidad.

        Es la senal de ``ADR002-B``, con su mismo lector y sus mismas cotas.
        La apertura del sidecar ocurre AQUI, en ``E4`` y en ninguna otra parte:
        una peticion que se satisface en ``E3`` no lo abre, no lo lee y no lo
        verifica, y el contador lo demuestra.

        La similitud **no se convierte en identidad**: selecciona candidatas,
        que pasan por las mismas puertas y reciben la misma lectura semantica
        que las de la base y que las relacionales.
        """
        self.invocaciones_vectoriales += 1
        if self._lector is None:
            self._lector = vectores.LectorVectorial(self._ruta_canon, self._ruta_sidecar)
        terminos = lexical.terminos_significativos(contexto.peticion.consulta)
        coincidencias = self._lector.consultar(
            terminos[: vectores.CONSULTA_TERMINOS_MAXIMOS], excluidos=ya
        )
        if not coincidencias:
            return []
        try:
            materializacion = contexto.puerto.por_identificadores(
                tuple(coincidencia.elemento for coincidencia in coincidencias)
            )
        except IdentificadorInvalidoError as error:
            msg = (
                "el indice vectorial entrego identidades que el puerto "
                "canonico rechaza; un indice que cita identidades no "
                "canonicas no es utilizable"
            )
            raise vectores.IndiceCorruptoError(msg) from error
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
                senal=f"{SENAL_VECTORIAL}: coseno ppmi en banda {coincidencia.banda}",
            )
            for coincidencia in coincidencias
        ]


def candidato(
    ruta_canon: Path,
    ruta_sidecar: Path,
    ruta_plano_relacional: Path,
    *,
    con_senal_relacional: bool = True,
    con_senal_vectorial: bool = True,
) -> CandidatoD:
    """Instancia del candidato. Sus unicas configuraciones son las tres rutas y
    los dos interruptores de ablacion, que **apagan** una senal pero jamas la
    mueven de etapa: el orden no es configurable."""
    return CandidatoD(
        ruta_canon,
        ruta_sidecar,
        ruta_plano_relacional,
        con_senal_relacional=con_senal_relacional,
        con_senal_vectorial=con_senal_vectorial,
    )


__all__ = [
    "ACTA_DEL_ORDEN",
    "DEFINICION_CANONICA",
    "IDENTIFICADOR",
    "ORDEN_CONGELADO",
    "SENAL_DE_LA_ETAPA",
    "SENAL_RELACIONAL",
    "SENAL_TARDIA",
    "SENAL_VECTORIAL",
    "CandidatoD",
    "OrdenDeSenalesVioladoError",
    "candidato",
]
