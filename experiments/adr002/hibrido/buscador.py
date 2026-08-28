"""``ADR002-HIB``: las dos vias corren en paralelo y se **fusionan** por puesto.

Es ``ADR002-B-SEM`` con una sola cosa cambiada, y la diferencia es de orden, no
de contenido: alli la senal semantica se **anadia detras** de las candidatas
lexicas; aqui las dos listas se fusionan por ``RRF`` y el resultado se ordena
por acuerdo. Todo lo demas —la base lexica de ``A``, las etapas, las puertas,
la lectura de polaridad, la materializacion por identidad, el fallo cerrado—
queda identico, de modo que cualquier diferencia observable es atribuible a la
fusion y a nada mas.

CORRECCION MEDIDA: EN ESTE BANCO LA FUSION NO CAMBIA NADA
=========================================================

Este modulo se escribio sobre una razon que la medida **refuto**, y la razon
refutada se queda escrita aqui porque borrarla dejaria el modulo pareciendo
mejor justificado de lo que esta.

Lo que se afirmo al crearlo: el contrato del puerto entrega como mucho
``IDENTIDADES_POR_LLAMADA`` identidades y ``G12`` recorta al limite pedido, asi
que anadir detras condena a la senal semantica a las ultimas posiciones y la
recorta antes de que ninguna puerta la mire; fusionar la rescataria.

Lo que se midio despues sobre el banco real:

* 45 de los 50 casos **no declaran limite**: su limite duro es el canon entero,
  97. De los cinco que si, dos lo fijan al numero exacto de elementos que su
  propia respuesta espera;
* solo 21 casos llegan a recorrer ``E3``, y ahi ``E3`` propone 5 candidatas de
  media;
* en **cero** de esos 21 casos una candidata anadida al final caeria fuera del
  limite duro.

De modo que concatenar no pierde nada en este banco, y por tanto fusionar no
puede ganar nada en este banco. Se comprobo tambien por el otro lado: con senal
activa —umbrales de coseno de 0.25 a 0.65— concatenar y fusionar dan cifras
identicas en los cinco puntos del barrido, y salidas identicas caso a caso.

QUE SE CONSERVA, ENTONCES
=========================

El mecanismo, porque es correcto y no cuesta nada: con senal nula la salida es
identica a la de la linea base en los 47 casos, luego la fusion no introduce
ruido propio. Y porque la premisa refutada es **del banco**, no de la fusion:
en cuanto un limite ate de verdad —un canon grande, una peticion acotada, una
interfaz que pida cinco resultados— el recorte vuelve a morder y el orden pasa
a decidir que sobrevive. Lo que no se puede es seguir presentando la fusion
como la solucion al problema medido en ``ADR-002``: no lo es, y lo unico que
mueve ese problema es que el codificador encuentre o no encuentre.

DONDE SE FUSIONA, Y POR QUE AHI
===============================

Dentro de ``E3``, no en todo el recorrido. ``B04-RF-15`` ordena las etapas por
autoridad: ``E1`` es coincidencia exacta y nada mas. Meter proximidad semantica
en ``E1`` destruiria esa autoridad —un vecino por coseno entraria con el mismo
rango que una clave que coincide literalmente— y ademas cambiaria dos cosas a
la vez respecto de la medicion anterior, con lo que ninguna conclusion seria
atribuible. La senal entra tarde, como ya entraba, y solo se reordena.

QUE PROVEEDOR HAY DETRAS
========================

Ninguno en concreto. Se habla con un ``CodificadorSemantico``, el mismo
protocolo de tres miembros que ya usa el sidecar, y el indice guarda cual lo
construyo. Cambiar de modelo es cambiar el objeto que se pasa al constructor.

POR QUE NO HAY UN INDICE VECTORIAL NATIVO AQUI
==============================================

Se evaluo anadir una extension de indice vectorial a ``SQLite``. No entra, y la
razon es medible, no de gusto: la version disponible resuelve el vecino mas
proximo **por fuerza bruta**, igual que ``LectorSemantico``, de modo que sobre
el canon medido devuelve exactamente el mismo resultado. Lo unico que cambiaria
es la velocidad, y a este tamano la busqueda no es el coste dominante. A cambio
habria que anadir una dependencia binaria y regenerar el fichero de bloqueo del
proyecto. Se anadira cuando el canon crezca lo bastante para que el coste se
note, y entonces sera **otra implementacion de la misma lectura**, no un cambio
de este modulo.
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
from experiments.adr002.hibrido import fusion

IDENTIFICADOR: Final = "ADR002-HIB"

#: Lo que este candidato pone a prueba.
SENAL_TARDIA: Final = "fusion_rrf_lexica_y_semantica_real"

DEFINICION_CANONICA: Final = (
    "expansion escalonada lexica/estructurada con senal semantica de modelo "
    "externo en etapas tardias, fusionando ambas listas por puesto (RRF) en "
    "lugar de concatenarlas."
)

#: Nombres de las dos listas. Viajan a la explicacion de ``RF-28`` tal cual, de
#: modo que la frase que lee una persona nombra la via, no un identificador.
LISTA_LEXICA: Final = "palabras"
LISTA_SEMANTICA: Final = "sentido"

_RAZON_ACUERDO: Final = "coincidencia de las dos vias: la lexica y la semantica proponen lo mismo"
_RAZON_SOLO_SENTIDO: Final = "proximidad semantica con la consulta segun un modelo externo"


class CandidatoHibrido:
    """La base de ``A`` y la senal semantica, **fusionadas** por puesto en ``E3``.

    Abre el indice de forma perezosa, igual que sus hermanos: si ``E1`` y ``E2``
    bastan, el sidecar no se abre, no se lee y no se verifica.
    """

    identificador: Final = IDENTIFICADOR

    def __init__(
        self,
        ruta_canon: Path,
        ruta_sidecar: Path,
        codificador: semantica.CodificadorSemantico,
        *,
        con_fusion: bool = True,
        k: int = semantica.TOP_K,
        coseno_minimo: float = semantica.COSENO_MINIMO,
        k_rrf: int = fusion.K_POR_DEFECTO,
    ) -> None:
        self._base = CandidatoA()
        self._ruta_canon = ruta_canon
        self._ruta_sidecar = ruta_sidecar
        self._codificador = codificador
        #: Apagado, este candidato **es** ``ADR002-B-SEM``: misma senal, mismo
        #: orden de concatenacion. Es el control de la fusion, y por eso vive
        #: aqui y no en otro modulo: las dos ramas comparten todo lo demas.
        self._con_fusion = con_fusion
        self._k = k
        self._coseno_minimo = coseno_minimo
        self._k_rrf = k_rrf
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
        """La misma lectura que ``ADR002-A``. La fusion no relaja ``RF-17``."""
        return self._base.leer(item, consulta)

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        """Las de la base siempre; fusionadas con la semantica solo en ``E3``."""
        de_la_base = list(self._base.candidatas(contexto))
        if contexto.etapa is not Etapa.E3:
            return de_la_base
        ya = contexto.ya_recuperados | {c.item.id for c in de_la_base}
        de_sentido = self._semanticas(contexto, frozenset(ya))
        if not self._con_fusion:
            # La rama de control: concatenar, que es lo que se midio antes.
            return [*de_la_base, *de_sentido]
        return fusionar(de_la_base, de_sentido, k=self._k_rrf)

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
                razon=_RAZON_SOLO_SENTIDO,
                senal=f"{SENAL_TARDIA}: coseno {c.similitud:.3f}",
            )
            for c in coincidencias
        ]


def fusionar(
    de_palabras: Sequence[Candidata],
    de_sentido: Sequence[Candidata],
    *,
    k: int = fusion.K_POR_DEFECTO,
) -> list[Candidata]:
    """Une las dos listas de candidatas ordenandolas por ``RRF``.

    No inventa ni descarta nada: el conjunto devuelto es exactamente la union de
    los dos, y lo unico que cambia es **el orden**. Esa contencion importa,
    porque quien decide que entra son las puertas, no esta funcion.

    La candidata que se conserva es la de la via lexica cuando aparece en las
    dos. No es arbitrario: su ``lectura`` la calcula el mismo metodo en ambos
    casos —``CandidatoA.leer``—, asi que los objetos solo difieren en el texto
    de la razon, y en ese caso se reescribe para nombrar a las dos vias.
    """
    listas = {
        LISTA_LEXICA: [c.item.id for c in de_palabras],
        LISTA_SEMANTICA: [c.item.id for c in de_sentido],
    }
    por_identidad: dict[str, Candidata] = {c.item.id: c for c in de_sentido}
    #: Las lexicas se escriben despues para que ganen en caso de coincidencia.
    por_identidad.update({c.item.id: c for c in de_palabras})

    fusionadas: list[Candidata] = []
    for puesto in fusion.fusionar(listas, k=k):
        original = por_identidad[puesto.identidad]
        acuerdo = puesto.en_cuantas_listas > 1
        fusionadas.append(
            Candidata(
                item=original.item,
                etapa=original.etapa,
                lectura=original.lectura,
                razon=_RAZON_ACUERDO if acuerdo else original.razon,
                # La explicacion de ``RF-28`` queda literal y verificable:
                # «2.º por palabras y 5.º por sentido».
                senal=f"{original.senal} [fusion RRF: {fusion.explicar(puesto)}]",
            )
        )
    return fusionadas


__all__ = [
    "DEFINICION_CANONICA",
    "IDENTIFICADOR",
    "LISTA_LEXICA",
    "LISTA_SEMANTICA",
    "SENAL_TARDIA",
    "CandidatoHibrido",
    "fusionar",
]
