"""Contrato de la proyeccion experimental: quien lee que, y que se pierde.

Tres decisiones estructurales viven aqui, y las tres son comprobables:

1. **La identidad canonica es una biyeccion declarada**, no un orden de
   insercion. ``MEM-007`` es ``MEMORIA:7`` en cualquier maquina y en cualquier
   corrida; una colision aborta la construccion.
2. **La capacidad gobierna el fichero.** Un candidato no puede leer
   ``property_key`` porque no recibe la ruta del plano reservado, no porque una
   norma se lo prohiba.
3. **Lo que Sirius 0.1 no puede sostener se declara perdido y se materializa
   aparte.** El esquema canonico tiene tres estados de memoria; el corpus
   distingue confirmacion, validez y disponibilidad por separado. El colapso es
   inevitable, y por eso el eje verdadero viaja intacto en ``ejes_p2``.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

VERSION_PROYECCION: Final = "0.1"

#: Familia de conformidad de la que esta proyeccion es imagen ejecutable.
FAMILIA_FUENTE: Final = "0.6"

#: Los cuatro congelables de la v0.6 mas el canal de criticidad heredado por
#: blob. Es todo lo que el constructor lee, y se comprueba antes de construir.
ARTEFACTOS_FUENTE: Final[tuple[str, ...]] = (
    "conformance_corpus_v0_6.json",
    "subject_keys_v0_2.json",
    "property_keys_v0_2.json",
    "applied_criticality_v0_1.json",
)


class ProyeccionError(RuntimeError):
    """Fallo de construccion o de acceso. Siempre cerrado, nunca por defecto."""


class AccesoNoAutorizadoError(ProyeccionError):
    """Un consumidor pidio un plano que su capacidad no le autoriza."""


class ProyeccionImposibleError(ProyeccionError):
    """El esquema canonico de Sirius 0.1 no admite proyeccion fiel del valor.

    No se inventa una equivalencia aproximada: si el corpus declarase una
    decision purgada —estado que ``DecisionStatus`` no tiene—, la construccion
    aborta en vez de elegir el estado "mas parecido".
    """


# --------------------------------------------------------------------------
# Planos y capacidades
# --------------------------------------------------------------------------


class Plano(StrEnum):
    """Un fichero por capacidad. La separacion fisica **es** el control."""

    ENTRADA = "entrada"
    EJES_P2 = "ejes_p2"
    RESERVADO = "reservado"


FICHEROS: Final[Mapping[Plano, str]] = {
    Plano.ENTRADA: "entrada.sqlite3",
    Plano.EJES_P2: "ejes_p2.sqlite3",
    Plano.RESERVADO: "reservado.sqlite3",
}

#: Capacidad de la clasificacion aprobada que gobierna cada plano.
CAPACIDAD_DEL_PLANO: Final[Mapping[Plano, tuple[str, ...]]] = {
    Plano.ENTRADA: ("ENTRADA_DE_CANDIDATO", "COMUN_Y_SENAL_DECLARADA_DE_A"),
    Plano.EJES_P2: ("ENTRADA_DE_CANDIDATO",),
    Plano.RESERVADO: ("SOLO_CAPA_COMUN", "HANDOFF_A_B05"),
}

#: Quien puede abrir cada plano. ``B05`` aparece solo donde la clasificacion lo
#: autoriza; ningun candidato aparece en el plano reservado, y esa ausencia es
#: la que hace estructural la prohibicion.
CONSUMIDORES_DEL_PLANO: Final[Mapping[Plano, tuple[str, ...]]] = {
    Plano.ENTRADA: ("common", "ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D", "T0-control"),
    Plano.EJES_P2: ("common", "ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D"),
    Plano.RESERVADO: ("common", "B05"),
}

#: Campos que la clasificacion aprobada declara ``ENTRADA_DE_CANDIDATO`` y que
#: **aun asi** no se cablean a ``ItemCanonico``. No es una restriccion nueva:
#: el contrato comun ya asigna su derivacion al candidato —«derivarlas es
#: trabajo del candidato, y como las derive es justamente parte de la
#: alternativa que se pone a prueba»—, de modo que inyectarlas sustituiria la
#: senal que el banco mide por la respuesta. Siguen materializadas en
#: ``ejes_p2``: quien las quiera tendra que pedirlas y declarar para que.
CAMPOS_QUE_NO_CRUZAN_A_ITEM_CANONICO: Final[Mapping[str, str]] = {
    "polaridad": (
        "RF-19 mide si el candidato la deriva; entregarla la convertiria en "
        "dato de entrada y el banco no mediria nada"
    ),
    "condicion": (
        "identica razon que polaridad: es lo que la lectura semantica debe "
        "producir, no lo que recibe"
    ),
}


# --------------------------------------------------------------------------
# Identidad canonica
# --------------------------------------------------------------------------

#: Identificadores del corpus que **tienen** identidad canonica en Sirius 0.1.
#: Documentos, entidades y proyectos no la tienen: no existen como tabla del
#: canon, y fingirles una seria inventar un espacio de identidad paralelo.
_PREFIJO_A_CLASE: Final[Mapping[str, str]] = {
    "MEM": "MEMORIA",
    "DEC": "DECISION",
    "MSG": "MENSAJE",
    "DOC": "DOCUMENTO",
}

_FORMA_DEL_IDENTIFICADOR: Final = re.compile(r"^(MEM|DEC|MSG|DOC)-(\d+)$")

#: Clases cuya identidad canonica el puerto entrega tal cual.
CLASES_DEL_CANON: Final[tuple[str, ...]] = ("MEMORIA", "DECISION")


def identidad_canonica(identificador_de_corpus: str) -> str:
    """``MEM-007`` -> ``MEMORIA:7``. Determinista y sin depender del orden.

    El numero se toma del propio identificador, no de un contador de
    insercion: dos construcciones sobre el mismo corpus producen las mismas
    identidades aunque el generador recorriese los items en otro orden.
    """
    forma = _FORMA_DEL_IDENTIFICADOR.match(identificador_de_corpus)
    if forma is None:
        msg = (
            f"identificador de corpus sin identidad canonica: "
            f"{identificador_de_corpus!r}; las formas admitidas son "
            f"{sorted(_PREFIJO_A_CLASE)} seguidas de un entero"
        )
        raise ProyeccionError(msg)
    numero = int(forma.group(2))
    if numero <= 0:
        msg = f"numero no positivo en {identificador_de_corpus!r}: la identidad canonica lo prohibe"
        raise ProyeccionError(msg)
    return f"{_PREFIJO_A_CLASE[forma.group(1)]}:{numero}"


def numero_canonico(identificador_de_corpus: str) -> int:
    """La clave primaria que el identificador induce en la tabla del canon."""
    _, _, numero = identidad_canonica(identificador_de_corpus).partition(":")
    return int(numero)


def referencia_canonica(identificador_de_corpus: str) -> str | None:
    """Identidad canonica si la hay; ``None`` si el corpus no la tiene.

    ``ENT-ROTOR`` y ``PRJ-ALFA`` devuelven ``None``: son extremos legitimos de
    una relacion y **no** elementos del canon. Devolver una identidad inventada
    para ellos haria indistinguible «no existe en el canon» de «existe».
    """
    if _FORMA_DEL_IDENTIFICADOR.match(identificador_de_corpus) is None:
        return None
    return identidad_canonica(identificador_de_corpus)


# --------------------------------------------------------------------------
# Colapso declarado sobre el vocabulario de estados de Sirius 0.1
# --------------------------------------------------------------------------

#: El canon distingue tres estados de memoria y cuatro de decision; el corpus
#: distingue confirmacion x validez x disponibilidad. La proyeccion colapsa, y
#: **declara** que colapsa: el eje verdadero viaja intacto en ``ejes_p2`` y las
#: puertas que lo necesitan lo leen de alli.
PERDIDA_POR_COLAPSO_DE_ESTADO: Final = (
    "memories.status tiene tres valores y decisions.status cuatro; el corpus "
    "declara confirmacion, validez y disponibilidad por separado. G3, G6, G7 y "
    "G9 necesitan los tres ejes y no pueden obtenerlos del estado colapsado: "
    "los leen del plano ejes_p2, donde viajan verbatim."
)

_DISPONIBILIDAD_QUE_BORRA: Final[frozenset[str]] = frozenset({"PURGADA", "NO_GUARDADA"})


def estado_de_memoria(confirmacion: str, validez: str, disponibilidad: str) -> str:
    """Estado canonico de una memoria. Vigente solo si los tres ejes lo son."""
    if disponibilidad in _DISPONIBILIDAD_QUE_BORRA:
        return "deleted"
    if confirmacion == "CONFIRMADA" and validez == "VIGENTE" and disponibilidad == "DISPONIBLE":
        return "current"
    return "archived"


def estado_de_decision(confirmacion: str, validez: str, disponibilidad: str) -> str:
    """Estado canonico de una decision. Falla cerrado donde no hay proyeccion."""
    if disponibilidad in _DISPONIBILIDAD_QUE_BORRA:
        msg = (
            f"decision con disponibilidad {disponibilidad!r}: DecisionStatus no "
            f"tiene estado equivalente y la proyeccion no elige el mas parecido"
        )
        raise ProyeccionImposibleError(msg)
    if confirmacion == "CONFIRMADA" and validez == "VIGENTE" and disponibilidad == "DISPONIBLE":
        return "approved"
    if validez == "SUSTITUIDA":
        return "superseded"
    if confirmacion == "CANDIDATA":
        return "proposed"
    return "archived"


# --------------------------------------------------------------------------
# Criticidad aplicada · lo unico que cruza a B05
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CriticidadAplicada:
    """Los cuatro campos seguros, integros hasta ``B05``.

    ``razon`` y ``regla`` del corpus viajan **verbatim**; lo que no viaja es
    ``criticidad.fuente`` bruta, que porta identificadores de caso del banco y
    convertiria el handoff en una filtracion del oraculo.
    """

    nivel: str
    razon_segura: str
    fuente_de_politica: str
    regla_de_politica: str


CAMPOS_DE_CRITICIDAD_APLICADA: Final[tuple[str, ...]] = (
    "nivel",
    "razon_segura",
    "fuente_de_politica",
    "regla_de_politica",
)


# --------------------------------------------------------------------------
# La proyeccion materializada
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProyeccionExperimental:
    """Las tres rutas y la puerta que decide quien abre cual."""

    raiz: Path

    def ruta(self, plano: Plano) -> Path:
        return self.raiz / FICHEROS[plano]

    def abrir(self, plano: Plano, consumidor: str) -> sqlite3.Connection:
        """Conexion de **solo lectura** al plano, si el consumidor la tiene.

        La autorizacion se comprueba aqui y la ruta no se devuelve: un
        consumidor no autorizado no obtiene ni el fichero ni su nombre.
        """
        autorizados = CONSUMIDORES_DEL_PLANO[plano]
        if consumidor not in autorizados:
            msg = (
                f"{consumidor!r} no puede abrir el plano {plano.value!r}: "
                f"su capacidad es {CAPACIDAD_DEL_PLANO[plano]} y solo la tienen "
                f"{list(autorizados)}"
            )
            raise AccesoNoAutorizadoError(msg)
        destino = self.ruta(plano)
        if not destino.exists():
            msg = f"plano no materializado: {destino}"
            raise ProyeccionError(msg)
        conexion = sqlite3.connect(f"file:{destino}?mode=ro", uri=True)
        conexion.row_factory = sqlite3.Row
        return conexion

    def ruta_de_entrada(self) -> Path:
        """Lo unico que un candidato recibe: la base del esquema canonico."""
        return self.ruta(Plano.ENTRADA)


# --------------------------------------------------------------------------
# Los dos mecanismos, deliberadamente separados
# --------------------------------------------------------------------------


def clases_por_identidad_exacta(identidades: Iterable[str]) -> dict[str, tuple[str, ...]]:
    """Mecanismo **A**: misma identidad canonica aportada varias veces.

    Es el unico eje que decide que dos apariciones son *el mismo elemento*. No
    consulta sujeto, ni propiedad, ni texto: si lo hiciera, dejaria de ser
    identidad y seria equivalencia con otro nombre.
    """
    clases: dict[str, list[str]] = {}
    for identidad in identidades:
        clases.setdefault(identidad, []).append(identidad)
    return {clave: tuple(miembros) for clave, miembros in sorted(clases.items())}


def clases_candidatas_de_equivalencia(
    sujetos: Mapping[str, str | None],
    propiedades: Mapping[str, str | None],
) -> dict[tuple[str, str], tuple[str, ...]]:
    """Mecanismo **B**: identidades **distintas** que *podrian* equivaler.

    Devuelve **candidatas**, no grupos. Aqui solo coinciden dos de los siete
    ejes de ``B04-Q13``; los otros cinco los adjudica la capa comun, y por eso
    esta funcion no decide ninguna fusion. Un sujeto o una propiedad ausentes
    excluyen: la duda no fusiona.
    """
    clases: dict[tuple[str, str], list[str]] = {}
    for identidad in sorted(sujetos):
        sujeto = sujetos.get(identidad)
        propiedad = propiedades.get(identidad)
        if not sujeto or not propiedad:
            continue
        clases.setdefault((sujeto, propiedad), []).append(identidad)
    return {
        clave: tuple(sorted(miembros))
        for clave, miembros in sorted(clases.items())
        if len(miembros) > 1
    }


__all__ = [
    "ARTEFACTOS_FUENTE",
    "CAMPOS_DE_CRITICIDAD_APLICADA",
    "CAMPOS_QUE_NO_CRUZAN_A_ITEM_CANONICO",
    "CAPACIDAD_DEL_PLANO",
    "CLASES_DEL_CANON",
    "CONSUMIDORES_DEL_PLANO",
    "FAMILIA_FUENTE",
    "FICHEROS",
    "PERDIDA_POR_COLAPSO_DE_ESTADO",
    "VERSION_PROYECCION",
    "AccesoNoAutorizadoError",
    "CriticidadAplicada",
    "Plano",
    "ProyeccionError",
    "ProyeccionExperimental",
    "ProyeccionImposibleError",
    "clases_candidatas_de_equivalencia",
    "clases_por_identidad_exacta",
    "estado_de_decision",
    "estado_de_memoria",
    "identidad_canonica",
    "numero_canonico",
    "referencia_canonica",
]
