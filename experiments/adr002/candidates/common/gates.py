"""Las doce puertas ``G1-G12`` de ``B04 §11``, no compensables.

Su orden es normativo y su severidad tambien: ``G1-G10`` se aplican **antes de
generar o exponer candidatos**, ``G11`` valida integridad semantica **antes**
del ranking y ``G12`` protege criticidad y limite **antes** del handoff.
**Ninguna senal blanda rescata un fallo de puerta**: aqui no se pondera, se
descarta.

Las puertas son comunes a todos los candidatos y no consultan quien las
invoca. Un candidato no puede relajarlas, saltarlas ni compensarlas con un
resultado mejor en otra: si lo pudiera, la comparacion entre alternativas
mediria quien esquiva mejor el contrato, no quien recupera mejor.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

from experiments.adr002.candidates.common.contracts import (
    AMBITO_GLOBAL,
    AMBITO_MULTIPROYECTO,
    CONFIRMACION_VISIBLE_SIEMPRE,
    ORDEN_DE_CRITICIDAD,
    SENSIBILIDAD_PROTEGIDA,
    VALIDEZ_QUE_NO_ENTRA_EN_M1,
    Candidata,
    Criticidad,
    Modo,
    Peticion,
    Polaridad,
)

#: Modos que **si** pueden inspeccionar lo marcado y lo protegido. Es la
#: excepcion literal de ``G3`` —«solo M3/M4 autorizado inspecciona»— y la unica
#: via por la que la proteccion de ``G9`` se levanta.
_MODOS_QUE_INSPECCIONAN_MARCAS: Final[tuple[Modo, ...]] = (Modo.M3_FUENTE, Modo.M4_GESTION)

#: Modos en los que una confirmacion distinta de CONFIRMADA es visible: el
#: modo de gestion la administra y el de conflicto la contrasta.
_MODOS_QUE_VEN_NO_CONFIRMADAS: Final[tuple[Modo, ...]] = (Modo.M4_GESTION, Modo.M5_CONFLICTO)

#: Identificadores y regla de cada puerta, en orden canonico.
PUERTAS: Final[tuple[tuple[str, str], ...]] = (
    ("G1", "proposito y permiso: la operacion activa debe autorizar dato, espacio y explicacion"),
    ("G2", "no persistencia: eliminado, no guardado o purgado no es recuperable ni reconstruible"),
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

#: ``G1-G10`` filtran antes de exponer; ``G11`` antes de ordenar; ``G12`` antes
#: del limite. El orden es la garantia, no un detalle de implementacion.
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
    """Lo que sobrevive a las puertas y por que cayo lo demas."""

    admitidas: tuple[Candidata, ...]
    descartes: tuple[tuple[str, str, str], ...]  # (item_id, puerta, motivo)

    @property
    def veredictos_por_puerta(self) -> dict[str, int]:
        """Cuantas candidatas descarto cada puerta. Alimenta la traza."""
        conteo: dict[str, int] = {}
        for _item, puerta, _motivo in self.descartes:
            conteo[puerta] = conteo.get(puerta, 0) + 1
        return conteo


def _g1(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    autorizada = bool(peticion.proposito.strip())
    return VeredictoDePuerta("G1", autorizada, "" if autorizada else "proposito no declarado")


def _g2(candidata: Candidata, _peticion: Peticion) -> VeredictoDePuerta:
    # Un item no disponible no es recuperable NI reconstruible: no se degrada
    # a "visible en otro modo", desaparece.
    disponible = candidata.item.disponible
    return VeredictoDePuerta(
        "G2", disponible, "" if disponible else "eliminado, no guardado o purgado"
    )


def _g3(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    """Marcas de no uso: excluyen ``M1`` y el fallback; ``M3``/``M4`` inspecciona.

    El eje real es ``no_usar_como_memoria``, que el canon de Sirius 0.1 no
    tiene columna para expresar. Mientras se leyo ``not disponible``, esta
    puerta era un duplicado exacto de ``G2`` y ningun item marcado que siguiera
    disponible caia por ella.
    """
    ejes = candidata.item.ejes
    if ejes.no_usar_como_memoria is None:
        # El sustrato no lo declara: se degrada al estado colapsado y se dice.
        marcado = not candidata.item.disponible
        motivo = "marcado no usar como memoria (eje no declarado: degradado a disponibilidad)"
    else:
        marcado = ejes.no_usar_como_memoria
        motivo = "marcado no usar como memoria"
    if marcado and peticion.modo not in _MODOS_QUE_INSPECCIONAN_MARCAS:
        return VeredictoDePuerta("G3", False, motivo)
    return VeredictoDePuerta("G3", True, "")


def _g4(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    """``G4``: **tres** clases de ambito, no una.

    Una sola clave foranea no puede expresar una lista cerrada. Comparar solo
    ``project_id`` descartaba todo item de ambito multiproyecto aunque la
    peticion autorizase a todos sus miembros, y admitia un item global solo por
    tener la clave nula.
    """
    item = candidata.item
    ambito = item.ejes.ambito
    if ambito == AMBITO_GLOBAL:
        # Un item global es visible desde cualquier ambito: no pertenece a uno.
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
    dentro = peticion.ambito.autoriza(item.project_id)
    return VeredictoDePuerta("G4", dentro, "" if dentro else "fuera del ambito autorizado")


def _g5(candidata: Candidata, _peticion: Peticion) -> VeredictoDePuerta:
    resuelto = bool(candidata.item.id.strip())
    return VeredictoDePuerta("G5", resuelto, "" if resuelto else "entidad sin ID estable")


def _g6(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    """El **modo** decide si candidata, rechazada o conflicto son visibles.

    El eje es ``confirmacion``, de tres valores. Leyendo ``vigente`` no habia
    forma de distinguir una candidata de una rechazada, y las dos caian o
    pasaban juntas.
    """
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
    """Validez y soporte: **invalidado o sin soporte** no entra en ``M1``.

    Son dos causas distintas —sustituida por una sucesora, o sin soporte que la
    respalde— y el estado colapsado las hacia indistinguibles entre si y de
    cualquier otra no vigencia.
    """
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
    # La aplicabilidad se evalua contra el tiempo objetivo; el corte de
    # registro, cuando existe, acota lo que Sirius podia saber entonces.
    corte = peticion.ventana.corte_de_registro
    if corte is not None and candidata.item.created_at > corte:
        return VeredictoDePuerta("G8", False, "posterior al corte de registro")
    return VeredictoDePuerta("G8", True, "")


def _g9(candidata: Candidata, peticion: Peticion) -> VeredictoDePuerta:
    """Sensibilidad: la proteccion superior provisional **se mantiene**.

    La duda no abre acceso: si el eje no esta declarado, se degrada a la
    disponibilidad, que es mas restrictiva que asumir sensibilidad ordinaria.
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
    """``G1-G10``, antes de generar o exponer. Falla cerrado y no compensa.

    Se evaluan **todas** las puertas de una candidata aunque la primera ya la
    descarte: la traza debe poder decir por que cayo, no solo que cayo.
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
    """Integridad semantica **antes** del ranking.

    Una candidata cuya lectura no declare sujeto, o cuya polaridad contradiga
    materialmente a otra del mismo sujeto, no se fusiona ni se pondera: se
    conserva el conflicto y el motor podra adjudicar ``S6``.
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
    """Sujetos con apoyo y refutacion a la vez (``B04-RF-21``, ``S6``).

    No los resuelve: los **denuncia**. Fusionarlos silenciosamente seria
    exactamente lo que ``RF-20`` y ``RF-21`` prohiben.
    """
    por_sujeto: dict[str, set[Polaridad]] = {}
    for candidata in candidatas:
        por_sujeto.setdefault(candidata.lectura.sujeto, set()).add(candidata.lectura.polaridad)
    return tuple(sorted(s for s, polaridades in por_sujeto.items() if len(polaridades) > 1))


@dataclass(frozen=True, slots=True)
class ResultadoG12:
    """Lo que ``G12`` deja pasar y lo que obliga a declarar.

    Dos desbordamientos, no uno. Recortar elementos ordinarios **es**
    desbordamiento y hay que decirlo; recortar criticos es ademas lo que
    ``RF-24`` prohibe ocultar. Un solo indicador confundia «se entrego menos de
    lo elegible» con «cayo un critico», y el segundo es materialmente distinto.
    """

    dentro_del_limite: tuple[Candidata, ...]
    desbordamiento_declarado: bool
    desbordamiento_critico: bool
    criticos_omitidos: tuple[str, ...]
    #: Miembros de grupo que el limite dejo fuera. **Se cuentan y se declaran**;
    #: el grupo no es atomico frente al limite, pero omitir en silencio si esta
    #: prohibido.
    miembros_omitidos: tuple[str, ...]


def aplicar_g12(
    candidatas: Sequence[Candidata],
    peticion: Peticion,
    criticidad_de: Callable[[str], Criticidad] | None = None,
    pertenece_a_grupo: Callable[[str], bool] | None = None,
) -> ResultadoG12:
    """Criticidad y limite, **antes** del handoff, sobre **todos** los miembros.

    Recibe la lista completa —representantes y miembros por igual—, de modo que
    un critico no queda oculto por pertenecer a un grupo. Que antes se aplicase
    despues de agrupar y solo viese representantes hacia inalcanzable la regla
    3 de ``§7.7``.

    ``criticidad_de`` viene del plano comun. Sin el, nada es critico: ninguna
    etapa puede crear un nivel, y la ausencia de canal lateral no es permiso
    para inventarlo.
    """
    nivel = criticidad_de if criticidad_de is not None else (lambda _id: Criticidad.ORDINARIA)
    # Mayor criticidad primero; el limite recorta por abajo. El orden dentro de
    # cada nivel es el que trae la lista, que el motor ya dejo ordenado.
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
