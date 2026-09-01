"""Las doce puertas ``G1-G12``, no compensables. Portadas desde
``experiments/adr002/candidates/common/gates.py`` (rama
``evidence/adr001-spikes``, PR #117), incidencia #457/ADR-109.

Su orden es normativo y su severidad también: ``G1-G10`` se aplican antes de
exponer candidatos, ``G11`` valida integridad semántica antes del ranking y
``G12`` protege criticidad y límite antes del handoff. Ninguna señal blanda
rescata un fallo de puerta: aquí no se pondera, se descarta.

Sobre los ejes que el esquema canónico de Sirius 0.1 no persiste hoy
(``ambito``, ``sensibilidad``, confirmación/validez granular, ventana de
vigencia): cuando ``item.ejes`` es ``SIN_EJES`` (todo candidato real del
producto, hasta que exista una migración fuera del alcance de esta
incidencia), cada puerta que los necesita degrada al estado colapsado que
Sirius sí persiste (``vigente``/``disponible``) — nunca inventa un valor
permisivo distinto de esa degradación documentada. Es la garantía que hace
"falla abierta, no descarta" literal: con ``SIN_EJES`` estas puertas se
comportan exactamente igual que hoy, sin el porte.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

from sirius.domain.staged_engine_contracts import (
    AMBITO_GLOBAL,
    AMBITO_MULTIPROYECTO,
    CONFIRMACION_VISIBLE_SIEMPRE,
    DISPONIBILIDAD_QUE_NO_ENTRA_EN_MODOS_ORDINARIOS,
    ORDEN_DE_CRITICIDAD,
    SENSIBILIDAD_PROTEGIDA,
    VALIDEZ_QUE_NO_ENTRA_EN_M1,
    Candidata,
    Criticidad,
    Modo,
    Peticion,
    Polaridad,
)

#: Modos que sí pueden inspeccionar lo marcado y lo protegido (``G3``/``G9``).
_MODOS_QUE_INSPECCIONAN_MARCAS: Final[tuple[Modo, ...]] = (Modo.M3_FUENTE, Modo.M4_GESTION)

#: Modos en los que una confirmación distinta de CONFIRMADA es visible.
_MODOS_QUE_VEN_NO_CONFIRMADAS: Final[tuple[Modo, ...]] = (Modo.M4_GESTION, Modo.M5_CONFLICTO)

#: Identificadores y regla de cada puerta, en orden canónico.
PUERTAS: Final[tuple[tuple[str, str], ...]] = (
    ("G1", "proposito y permiso: la operacion activa debe autorizar dato, espacio y explicacion"),
    (
        "G2",
        "persistencia y disponibilidad: lo borrado no es recuperable y lo archivado "
        "no entra en modos ordinarios",
    ),
    ("G3", "marcas de no uso: excluyen M1 y el fallback; solo M3/M4 autorizado inspecciona"),
    (
        "G4",
        "ambito: global, proyecto o lista cerrada deben coincidir; fuera de ambito no contamina",
    ),
    ("G5", "entidad: ID resuelto o ambiguedad aclarada; los alias no fusionan homonimos"),
    ("G6", "modo y confirmacion: el modo decide si candidata, rechazada o conflicto son visibles"),
    ("G7", "validez y soporte: invalidado o sin soporte no entra en M1"),
    ("G8", "tiempo: aplicabilidad respecto del tiempo objetivo y, si procede, corte de registro"),
    ("G9", "sensibilidad: la proteccion superior provisional se mantiene"),
    ("G10", "procedencia: todo resultado conserva fuente y transformacion suficientes"),
    ("G11", "integridad semantica: negaciones, condiciones y relaciones no se pierden"),
    ("G12", "criticidad y limite: los criticos se preservan o se declara desbordamiento"),
)

PUERTAS_PREVIAS: Final[tuple[str, ...]] = tuple(g for g, _ in PUERTAS[:10])
PUERTA_SEMANTICA: Final = "G11"
PUERTA_CRITICIDAD: Final = "G12"


@dataclass(frozen=True, slots=True)
class VeredictoDePuerta:
    """Resultado de aplicar una puerta a una candidata."""

    puerta: str
    pasa: bool
    motivo: str


@dataclass(frozen=True, slots=True)
class Filtrado:
    """Lo que sobrevive a las puertas y por qué cayó lo demás."""

    admitidas: tuple[Candidata, ...]
    descartes: tuple[tuple[str, str, str], ...]  # (item_id, puerta, motivo)

    @property
    def veredictos_por_puerta(self) -> dict[str, int]:
        """Cuántas candidatas descartó cada puerta. Alimenta la traza."""
        conteo: dict[str, int] = {}
        for _item, puerta, _motivo in self.descartes:
            conteo[puerta] = conteo.get(puerta, 0) + 1
        return conteo


def _g1(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    autorizada = bool(peticion.proposito.strip())
    return VeredictoDePuerta("G1", autorizada, "" if autorizada else "proposito no declarado")


def _g2(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    """Persistencia y disponibilidad. Con ``SIN_EJES`` degrada a
    ``item.disponible``, que ya excluye lo borrado y lo purgado."""
    if not candidata.item.disponible:
        return VeredictoDePuerta("G2", False, "eliminado, no guardado o purgado")
    disponibilidad = candidata.item.ejes.disponibilidad
    if (
        disponibilidad in DISPONIBILIDAD_QUE_NO_ENTRA_EN_MODOS_ORDINARIOS
        and peticion.modo not in _MODOS_QUE_INSPECCIONAN_MARCAS
        and not peticion.admite_no_vigentes
    ):
        return VeredictoDePuerta("G2", False, f"disponibilidad {disponibilidad}: no entra")
    return VeredictoDePuerta("G2", True, "")


def _g3(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    """Marcas de no uso. Sin el eje declarado, degrada a ``not disponible``."""
    ejes = candidata.item.ejes
    if ejes.no_usar_como_memoria is None:
        marcado = not candidata.item.disponible
        motivo = "marcado no usar como memoria (eje no declarado: degradado a disponibilidad)"
    else:
        marcado = ejes.no_usar_como_memoria
        motivo = "marcado no usar como memoria"
    if marcado and peticion.modo not in _MODOS_QUE_INSPECCIONAN_MARCAS:
        return VeredictoDePuerta("G3", False, motivo)
    return VeredictoDePuerta("G3", True, "")


def _g4(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    """``G4``: tres clases de ámbito, no una."""
    item = candidata.item
    ambito = item.ejes.ambito
    if ambito == AMBITO_GLOBAL:
        return VeredictoDePuerta("G4", True, "")
    if ambito == AMBITO_MULTIPROYECTO:
        miembros = item.ejes.miembros_de_ambito
        if not miembros:
            return VeredictoDePuerta(
                "G4", False, "lista cerrada sin miembros resueltos: la duda no abre ambito"
            )
        dentro = all(peticion.ambito.autoriza(m) for m in miembros)
        return VeredictoDePuerta(
            "G4", dentro, "" if dentro else "lista cerrada con miembros fuera del ambito"
        )
    if ambito is None:
        dentro = peticion.ambito.autoriza(item.project_id)
    else:
        # Eje de ambito declarado explicitamente (p.ej. "PROYECTO"): a
        # diferencia del caso sin eje, aqui el candidato afirma pertenecer a
        # un proyecto, asi que su membresia debe poder comprobarse. La
        # excepcion de ``Ambito.autoriza`` para ``project_id is None`` es
        # para el candidato sin eje declarado (ver docstring de
        # ``autoriza``); aplicarla aqui admitiria un item que se declara de
        # proyecto sin poder verificar cual, colando el atajo pensado para
        # memorias globales. Sin project_id resuelto, la peticion cerrada
        # cierra el ambito; una peticion global lo sigue admitiendo.
        dentro = peticion.ambito.global_ or (
            item.project_id is not None and item.project_id in peticion.ambito.proyectos
        )
    return VeredictoDePuerta("G4", dentro, "" if dentro else "fuera del ambito autorizado")


def _g5(candidata: Candidata, _peticion: Peticion) -> VeredictoDePuerta:
    resuelto = bool(candidata.item.id.strip())
    return VeredictoDePuerta("G5", resuelto, "" if resuelto else "entidad sin ID estable")


def _g6(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    """El modo decide si candidata, rechazada o conflicto son visibles."""
    confirmacion = candidata.item.ejes.confirmacion
    if confirmacion is None:
        if candidata.item.vigente:
            return VeredictoDePuerta("G6", True, "")
        if peticion.modo is Modo.M1_ORDINARIO and not peticion.admite_no_vigentes:
            return VeredictoDePuerta(
                "G6", False, "no vigente y el modo M1 no lo admite (confirmacion no declarada)"
            )
        return VeredictoDePuerta("G6", True, "")
    if confirmacion == CONFIRMACION_VISIBLE_SIEMPRE:
        return VeredictoDePuerta("G6", True, "")
    if peticion.modo in _MODOS_QUE_VEN_NO_CONFIRMADAS or peticion.admite_no_vigentes:
        return VeredictoDePuerta("G6", True, "")
    return VeredictoDePuerta(
        "G6", False, f"confirmacion {confirmacion} no visible en el modo {peticion.modo.value}"
    )


def _g7(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    """Validez y soporte: invalidado o sin soporte no entra en ``M1``."""
    validez = candidata.item.ejes.validez
    if validez is None:
        if peticion.modo is Modo.M1_ORDINARIO and not candidata.item.vigente:
            return VeredictoDePuerta(
                "G7", False, "invalidado o sin soporte para M1 (validez no declarada)"
            )
        return VeredictoDePuerta("G7", True, "")
    if validez in VALIDEZ_QUE_NO_ENTRA_EN_M1 and peticion.modo is Modo.M1_ORDINARIO:
        return VeredictoDePuerta("G7", False, f"validez {validez}: no entra en M1")
    return VeredictoDePuerta("G7", True, "")


def _g8(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    """Tiempo: aplicabilidad y corte de registro, por separado.

    Sin ``valid_from``/``valid_to`` declarados, la puerta degrada al corte
    de registro únicamente.
    """
    corte = peticion.ventana.corte_de_registro
    if corte is not None and candidata.item.created_at > corte:
        return VeredictoDePuerta("G8", False, "posterior al corte de registro")

    objetivo = peticion.ventana.tiempo_objetivo
    ejes = candidata.item.ejes
    if ejes.valid_from is not None and ejes.valid_from > objetivo:
        return VeredictoDePuerta("G8", False, "aun no vigente en el tiempo objetivo")
    if ejes.valid_to is not None and ejes.valid_to <= objetivo and not peticion.admite_no_vigentes:
        return VeredictoDePuerta("G8", False, "vigencia expirada en el tiempo objetivo")
    return VeredictoDePuerta("G8", True, "")


def _g9(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    """Sensibilidad: la protección superior provisional se mantiene.

    Sin el eje declarado, degrada a la disponibilidad (más restrictiva que
    asumir sensibilidad ordinaria).
    """
    sensibilidad = candidata.item.ejes.sensibilidad
    if sensibilidad is None:
        disponible = candidata.item.disponible
        return VeredictoDePuerta(
            "G9", disponible, "" if disponible else "protegido (sensibilidad no declarada)"
        )
    protegida = sensibilidad in SENSIBILIDAD_PROTEGIDA
    if protegida and peticion.modo not in _MODOS_QUE_INSPECCIONAN_MARCAS:
        return VeredictoDePuerta(
            "G9", False, f"sensibilidad {sensibilidad}: la proteccion superior se mantiene"
        )
    return VeredictoDePuerta("G9", True, "")


def _g10(candidata: Candidata, _peticion: Peticion) -> VeredictoDePuerta:
    con_procedencia = bool(candidata.senal.strip()) and bool(candidata.razon.strip())
    return VeredictoDePuerta(
        "G10", con_procedencia, "" if con_procedencia else "sin procedencia suficiente"
    )


_PREVIAS = (_g1, _g2, _g3, _g4, _g5, _g6, _g7, _g8, _g9, _g10)


def aplicar_previas(candidatas: Sequence[Candidata], peticion: Peticion) -> Filtrado:
    """``G1-G10``, antes de exponer. Falla cerrado y no compensa.

    Se evalúan todas las puertas de una candidata aunque la primera ya la
    descarte: la traza debe poder decir por qué cayó, no solo que cayó.
    """
    admitidas: list[Candidata] = []
    descartes: list[tuple[str, str, str]] = []
    for candidata in candidatas:
        fallos = [v for puerta in _PREVIAS if not (v := puerta(candidata, peticion)).pasa]
        if fallos:
            descartes.extend((candidata.item.id, v.puerta, v.motivo) for v in fallos)
            continue
        admitidas.append(candidata)
    return Filtrado(tuple(admitidas), tuple(descartes))


def aplicar_g11(candidatas: Sequence[Candidata], peticion: Peticion) -> Filtrado:
    """Integridad semántica antes del ranking.

    Una candidata cuya lectura no declare sujeto no se fusiona ni se
    pondera: se descarta como incompleta, y el motor conserva cualquier
    conflicto de polaridad entre las que sí la declaran.
    """
    admitidas: list[Candidata] = []
    descartes: list[tuple[str, str, str]] = []
    for candidata in candidatas:
        lectura = candidata.lectura
        if not lectura.sujeto.strip() or not lectura.medio.strip():
            descartes.append((candidata.item.id, PUERTA_SEMANTICA, "lectura semantica incompleta"))
            continue
        admitidas.append(candidata)
    return Filtrado(tuple(admitidas), tuple(descartes))


def conflictos_de_polaridad(candidatas: Sequence[Candidata]) -> tuple[str, ...]:
    """Sujetos con apoyo y refutación a la vez. No los resuelve: los
    denuncia — fusionarlos en silencio perdería la contradicción."""
    por_sujeto: dict[str, set[Polaridad]] = {}
    for candidata in candidatas:
        por_sujeto.setdefault(candidata.lectura.sujeto, set()).add(candidata.lectura.polaridad)
    return tuple(sorted(s for s, polaridades in por_sujeto.items() if len(polaridades) > 1))


@dataclass(frozen=True, slots=True)
class ResultadoG12:
    """Lo que ``G12`` deja pasar y lo que obliga a declarar.

    Dos desbordamientos, no uno: recortar elementos ordinarios es
    desbordamiento y hay que decirlo; recortar críticos es además lo que no
    puede ocultarse.
    """

    dentro_del_limite: tuple[Candidata, ...]
    desbordamiento_declarado: bool
    desbordamiento_critico: bool
    criticos_omitidos: tuple[str, ...]
    #: Miembros de grupo que el límite dejó fuera. Se cuentan y se declaran.
    miembros_omitidos: tuple[str, ...]


def aplicar_g12(
    candidatas: Sequence[Candidata],
    peticion: Peticion,
    criticidad_de: Callable[[str], Criticidad] | None = None,
    pertenece_a_grupo: Callable[[str], bool] | None = None,
) -> ResultadoG12:
    """Criticidad y límite, antes del handoff, sobre todos los miembros.

    ``criticidad_de`` viene del plano común. Sin él, nada es crítico: ninguna
    etapa puede crear un nivel, y la ausencia de canal lateral no es permiso
    para inventarlo.
    """
    nivel = criticidad_de if criticidad_de is not None else (lambda _id: Criticidad.ORDINARIA)
    por_nivel = sorted(
        range(len(candidatas)),
        key=lambda i: (-ORDEN_DE_CRITICIDAD.index(nivel(candidatas[i].item.id)), i),
    )
    priorizadas = [candidatas[i] for i in por_nivel]
    dentro = priorizadas[: peticion.limite_duro]
    fuera = priorizadas[peticion.limite_duro :]
    omitidos = tuple(c.item.id for c in fuera if nivel(c.item.id) is Criticidad.CRITICA)
    en_grupo = pertenece_a_grupo if pertenece_a_grupo is not None else (lambda _id: False)
    return ResultadoG12(
        dentro_del_limite=tuple(dentro),
        desbordamiento_declarado=bool(fuera),
        desbordamiento_critico=bool(omitidos),
        criticos_omitidos=omitidos,
        miembros_omitidos=tuple(c.item.id for c in fuera if en_grupo(c.item.id)),
    )


__all__ = [
    "PUERTAS",
    "PUERTAS_PREVIAS",
    "PUERTA_CRITICIDAD",
    "PUERTA_SEMANTICA",
    "Filtrado",
    "ResultadoG12",
    "VeredictoDePuerta",
    "aplicar_g11",
    "aplicar_g12",
    "aplicar_previas",
    "conflictos_de_polaridad",
]
