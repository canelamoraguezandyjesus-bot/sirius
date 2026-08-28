"""Fuente relacional explicita de ``ADR002-C``. Falla cerrada, sin oraculo.

Lee **unicamente** las relaciones que el corpus declara, sin su nota: la
clasificacion aprobada marca ``relaciones[].nota`` como oraculo prohibido, y
este lector no tiene por donde alcanzarla porque no la selecciona.

**Que tipos expanden, y por que no todos.** Dos de los ocho tipos declarados
los adjudica ya otro mecanismo del contrato: ``SUSTITUYE_A`` esta materializado
en ``decisions.supersedes_decision_id`` y lo gobierna la validez en ``G7``;
``CONFLICTO_CON`` lo adjudica la parada ``S6``. Expandir por ellos no seria una
senal adicional: seria alcanzar por relacion lo que otra regla ya decidio, y
convertiria a ``C`` en un candidato que esquiva puertas en vez de recuperar
mejor. Los otros seis expanden.

**Un solo salto y una sola direccion.** Del origen al destino, una vez. No es
una limitacion de implementacion: mas saltos convertirian la senal relacional
en una travesia del grafo, y el alcance dejaria de poder atribuirse a una
arista concreta —que es justamente lo que el discriminante debe demostrar—.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

#: Tipos que **no** expanden, con la regla que ya los adjudica.
TIPOS_NO_EXPANDEN: Final[dict[str, str]] = {
    "SUSTITUYE_A": "materializado en decisions.supersedes_decision_id y adjudicado por G7",
    "CONFLICTO_CON": "adjudicado por la parada S6, que conserva el conflicto sin fusionarlo",
}

#: Los seis que si expanden. Lista cerrada: un tipo desconocido falla cerrado.
TIPOS_QUE_EXPANDEN: Final[tuple[str, ...]] = (
    "ALIAS_DE",
    "APOYA",
    "CORRIGE",
    "DERIVA_DE",
    "ORIGINA_CANDIDATA",
    "REFUTA",
)

TIPOS_CONOCIDOS: Final[frozenset[str]] = frozenset({*TIPOS_QUE_EXPANDEN, *TIPOS_NO_EXPANDEN})

#: Clases que el puerto comun sabe materializar. Las demas referencias del
#: grafo —documentos, entidades, proyectos— son extremos legitimos y **no**
#: elementos del canon.
CLASES_MATERIALIZABLES: Final[frozenset[str]] = frozenset({"MEMORIA", "DECISION"})

#: Cota de aristas por consulta. Sin ella, pedir "todas las relaciones de todas
#: las semillas" seria un barrido del grafo escrito de otra forma.
ARISTAS_MAXIMAS: Final = 64

#: Cota de semillas por consulta, del mismo orden que la del puerto comun.
SEMILLAS_MAXIMAS: Final = 16

#: Saltos. **Uno.** Declarado como constante para que la ablacion lo lea.
SALTOS: Final = 1


class FuenteRelacionalError(RuntimeError):
    """Base de los fallos de la fuente relacional. Todos son cerrados."""


class PlanoRelacionalAusenteError(FuenteRelacionalError):
    """No hay plano de relaciones. No se degrada a «sin relaciones»."""


class RelacionInvalidaError(FuenteRelacionalError):
    """Una arista malformada: tipo desconocido, extremo vacio o bucle."""


class RelacionInconsistenteError(FuenteRelacionalError):
    """Una arista cita un elemento que el canon no contiene."""


@dataclass(frozen=True, slots=True)
class Arista:
    """Una relacion explicita, con su tipo y su direccion conservados."""

    id: str
    tipo: str
    origen: str
    destino: str
    origen_canonico: str | None
    destino_canonico: str | None

    @property
    def expande(self) -> bool:
        return self.tipo in TIPOS_QUE_EXPANDEN

    @property
    def alcanzable(self) -> bool:
        """Si el destino es un elemento que el puerto puede materializar.

        Entidades, proyectos y documentos son extremos legitimos de una
        relacion y **no** son elementos del canon: el puerto solo materializa
        ``MEMORIA`` y ``DECISION``. Que un documento tenga referencia canonica
        no lo convierte en recuperable, y pasarselo al puerto haria que un
        grafo perfectamente valido pareciese corrupto.
        """
        if self.destino_canonico is None:
            return False
        clase, _, _ = self.destino_canonico.partition(":")
        return clase in CLASES_MATERIALIZABLES


@dataclass(slots=True)
class RegistroRelacional:
    """Lo que la fuente relacional consulto de verdad."""

    consultas: list[tuple[str, tuple[str, ...], int]] = field(default_factory=list)
    #: Aristas descartadas por tipo no expansivo, con su motivo.
    descartadas_por_tipo: list[tuple[str, str, str]] = field(default_factory=list)
    #: Destinos sin identidad canonica, declarados en vez de callados.
    no_materializables: list[tuple[str, str]] = field(default_factory=list)

    @property
    def aristas_leidas(self) -> int:
        return sum(filas for _op, _params, filas in self.consultas)


class FuenteRelacional:
    """Lector de solo lectura del plano de relaciones. Un salto, dirigido."""

    def __init__(self, ruta_plano: Path) -> None:
        if not ruta_plano.exists():
            msg = (
                f"plano relacional ausente: {ruta_plano}; ADR002-C no degrada a "
                f"«sin relaciones», porque su senal es exactamente esa"
            )
            raise PlanoRelacionalAusenteError(msg)
        self._conexion = sqlite3.connect(f"file:{ruta_plano}?mode=ro", uri=True)
        self._conexion.row_factory = sqlite3.Row
        self.registro = RegistroRelacional()
        self._validar_el_grafo()

    def close(self) -> None:
        self._conexion.close()

    def __enter__(self) -> FuenteRelacional:
        return self

    def __exit__(self, *_excepcion: object) -> None:
        self.close()

    def _validar_el_grafo(self) -> None:
        """Comprueba el grafo entero **una vez, al abrir**, y falla cerrado.

        Se valida al abrir y no por consulta: una arista malformada invalida la
        fuente, no solo la consulta que la toco. Descubrirla a mitad de una
        recuperacion daria resultados parciales de una fuente que ya se sabia
        rota.
        """
        for fila in self._conexion.execute(
            "SELECT id, tipo, origen, destino FROM relaciones ORDER BY id"
        ):
            identificador, tipo = str(fila["id"]), str(fila["tipo"])
            origen, destino = str(fila["origen"]), str(fila["destino"])
            if tipo not in TIPOS_CONOCIDOS:
                msg = (
                    f"{identificador}: tipo de relacion desconocido {tipo!r}; la lista "
                    f"es cerrada y no admite tipos nuevos sin decision aprobada"
                )
                raise RelacionInvalidaError(msg)
            if not origen.strip() or not destino.strip():
                msg = f"{identificador}: extremo vacio; una arista sin extremos no es una relacion"
                raise RelacionInvalidaError(msg)
            if origen == destino:
                msg = (
                    f"{identificador}: bucle {origen} -> {destino}; un elemento relacionado "
                    f"consigo mismo se alcanzaria a si mismo y no aportaria nada"
                )
                raise RelacionInvalidaError(msg)

    def salientes(self, semillas: Sequence[str]) -> tuple[Arista, ...]:
        """Aristas que **salen** de las semillas dadas. Dirigida y acotada.

        La direccion se respeta: se sigue de origen a destino y nunca al reves.
        Seguirlas en ambos sentidos convertiria ``APOYA`` y ``REFUTA`` en
        simetricas, que es justo lo que no son.
        """
        acotadas = sorted({s for s in semillas if s})[:SEMILLAS_MAXIMAS]
        if not acotadas:
            self.registro.consultas.append(("salientes:sin_semillas", (), 0))
            return ()
        marcas = ",".join("?" * len(acotadas))
        filas = self._conexion.execute(
            "SELECT id, tipo, origen, destino, origen_canonico, destino_canonico "
            f"FROM relaciones WHERE origen_canonico IN ({marcas}) "
            "ORDER BY id LIMIT ?",
            (*acotadas, ARISTAS_MAXIMAS),
        ).fetchall()
        self.registro.consultas.append(("salientes", tuple(acotadas), len(filas)))
        aristas = [
            Arista(
                id=str(f["id"]),
                tipo=str(f["tipo"]),
                origen=str(f["origen"]),
                destino=str(f["destino"]),
                origen_canonico=(
                    None if f["origen_canonico"] is None else str(f["origen_canonico"])
                ),
                destino_canonico=(
                    None if f["destino_canonico"] is None else str(f["destino_canonico"])
                ),
            )
            for f in filas
        ]
        utiles: list[Arista] = []
        for arista in aristas:
            if not arista.expande:
                self.registro.descartadas_por_tipo.append(
                    (arista.id, arista.tipo, TIPOS_NO_EXPANDEN[arista.tipo])
                )
                continue
            if not arista.alcanzable:
                self.registro.no_materializables.append((arista.id, arista.destino))
                continue
            utiles.append(arista)
        return tuple(utiles)


__all__ = [
    "ARISTAS_MAXIMAS",
    "CLASES_MATERIALIZABLES",
    "SALTOS",
    "SEMILLAS_MAXIMAS",
    "TIPOS_CONOCIDOS",
    "TIPOS_NO_EXPANDEN",
    "TIPOS_QUE_EXPANDEN",
    "Arista",
    "FuenteRelacional",
    "FuenteRelacionalError",
    "PlanoRelacionalAusenteError",
    "RegistroRelacional",
    "RelacionInconsistenteError",
    "RelacionInvalidaError",
]
