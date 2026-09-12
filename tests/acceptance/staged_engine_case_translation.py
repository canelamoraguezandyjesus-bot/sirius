"""Traductor de petición por caso, portado de
``experiments/adr002/round/cases.py:334-366`` (``_traducir``, commit
``dfdcdaff04dcba10939cc0b0569c55b6a636296f`` de ``evidence/adr001-spikes``,
el mismo que ya citaba la nota de procedencia del fixture del banco).

ADR-110 diagnosticó que el 29/47 que el laboratorio midió no lo alcanza una
política uniforme para las 47 consultas: lo alcanza una petición **por
caso** (modo, permiso, cardinalidad y límite, cada uno declarado por
consulta) que ``_traducir`` construye a partir de ``cases_v0_5.json``
(instanciación) y ``references_v0_5.json`` (adjudicación, el límite
duro/objetivo real de cada caso). La incidencia #461 autoriza portar ese
traductor: solo la parte que convierte un caso ya declarado en una
``Peticion``, no la carga de los tres artefactos congelados que
``cargar_artefactos``/``casos_ejecutables`` hacían en el laboratorio — el
fixture ``evidence_bank_47_casos.json`` ya trae, por caso, los mismos
campos verbatim bajo ``peticion_p2`` (incidencia #461), así que este módulo
solo repite la traducción, no la lectura de los ficheros originales.

Tres traducciones no obvias, heredadas literalmente del comentario del
módulo original:

- **El permiso.** ``Peticion`` no tiene campo de permiso: lo que el motor
  comprueba en ``E0`` es que el propósito esté declarado, y un propósito no
  declarado bloquea antes de recuperar. Un caso ``NO_AUTORIZADO`` se
  traduce como **propósito vacío**.
- **El límite.** Un caso sin límite declarado recibe uno que **no ata**:
  el tamaño del canon, igual para todos los que no lo declaran.
- **El tiempo.** Un caso puede declarar su instante objetivo como un
  intervalo; se toma **el extremo final** como instante objetivo. Desde
  ADR-168 el extremo inicial deja de tirarse: viaja en
  ``VentanaTemporal.tiempo_objetivo_desde``, que es lo que la vía de
  recuperación por vigencia necesita para enumerar. El instante objetivo no
  cambia —sigue siendo el extremo final, que es lo que ``G8`` compara—, así
  que ningún caso cambia de veredicto por esto solo.

Una cuarta, no heredada del comentario original ni de ``_traducir`` (que
nunca asigna ``objetivos`` y lo deja siempre en su valor por defecto)
sino lógica nueva de la incidencia #461, cerrada por su revisión: **los
objetivos de ``EXACTA``**. ``Peticion.objetivos`` es la cuota que
``_suficiente``/``evaluar_suficiencia`` exigen antes de detener la
expansión en cardinalidad ``EXACTA`` (``staged_engine.py``); por defecto
vale 1. El fixture no trae un campo de adjudicación separado para esta
cuota (a diferencia del límite, que sí lo trae en ``peticion_p2.limite``),
pero por construcción del banco, para los casos con algún elemento
esperado, coincide con el número de elementos que ``resultado_esperado``
adjudica al caso: ``EXACTA`` toma ``max(1, len(caso["resultado_esperado"]))``
en vez del valor por defecto. El ``max(1, …)`` importa para los diez casos
``EXACTA`` cuyo ``resultado_esperado`` está vacío (ninguno de los 47 debe
igualarlo a cero): una cuota 0 satisface ``_suficiente`` de forma trivial
tras la primera etapa (``0 >= 0``), deteniendo la expansión antes de
recorrer las etapas que sí recorre un caso con cuota 1, y esa expansión
más corta no es la traducción que ``_traducir`` produce — el original
nunca adjudica una cuota, ni siquiera cero. Medido contra el banco
(``test_peticion_desde_caso_no_asigna_cuota_cero_a_exacta_sin_resultado``
y las cuatro métricas de ``test_pa_0_2_rec_01_banco_evidencia.py``),
``max(1, …)`` no cambia ninguna de las cuatro cifras que ADR-111
publica frente a tomar ``len(...)`` sin ese suelo: para estos diez casos
el banco no tiene nada que el motor pueda encontrar en ninguna etapa
autorizada, así que detenerse antes o después no cambia el conjunto
final admitido.

Una quinta, nueva de ADR-177 (H4 de ADR-148, incidencia #581): **la
ampliación por categoría**. Hasta entonces no se traducía en absoluto —el
motor la deducía mirando si el propósito traducido contenía la subcadena
«contexto»—, así que el banco activaba la siembra en sus dos únicos casos
con propósito ``ensamblar_contexto_b05`` sin que este traductor dijera una
palabra al respecto. Ahora la traduce, y por pertenencia a
``PROPOSITOS_QUE_AMPLIAN_POR_CATEGORIA``: mismo conjunto activado, dicho en
vez de deducido.

Ámbito no se traduce aquí: a diferencia del laboratorio (que numera
proyectos del corpus), el arnés del banco ya resuelve ``caso["ambito"]``
contra los ``Project`` reales que él mismo crea, así que el llamador
construye el ``Ambito`` y lo pasa ya resuelto.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from sirius.domain.staged_engine_contracts import (
    Ambito,
    Cardinalidad,
    Modo,
    Peticion,
    VentanaTemporal,
)

#: Permiso que, por B04-RF-02, impide recuperar. Se traduce como propósito
#: vacío: el motor no tiene campo de permiso, y `E0` bloquea sobre un
#: propósito no declarado.
PERMISO_SIN_AUTORIZAR: Final = "NO_AUTORIZADO"

#: Modo cuyo contrato admite elementos no vigentes.
MODO_HISTORICO: Final = "M2"


class CasoNoTraducibleError(RuntimeError):
    """Un caso cuyo modo o cardinalidad no está en el vocabulario del motor."""


def _modo(declarado: str) -> Modo:
    try:
        return Modo(declarado)
    except ValueError as error:
        msg = f"modo declarado fuera de M1-M5: {declarado!r}"
        raise CasoNoTraducibleError(msg) from error


def _cardinalidad(declarada: str) -> Cardinalidad:
    try:
        return Cardinalidad(declarada)
    except ValueError as error:
        msg = f"cardinalidad declarada fuera del vocabulario: {declarada!r}"
        raise CasoNoTraducibleError(msg) from error


def _instante(declarado: str) -> str:
    """El instante objetivo. Un intervalo se resuelve por su extremo final."""
    return declarado.split("/")[-1] if "/" in declarado else declarado


def _instante_inicial(declarado: str) -> str | None:
    """El extremo INICIAL, o ``None`` si el caso declara un instante suelto.

    Un intervalo con más de dos extremos, o con alguno en blanco, no es un
    intervalo declarado: se trata como si no lo hubiera (ADR-168), que es el
    comportamiento anterior y no uno más permisivo.
    """
    if "/" not in declarado:
        return None
    extremos = declarado.split("/")
    if len(extremos) != 2 or not all(extremo.strip() for extremo in extremos):
        return None
    return extremos[0]


def _limites(limite: Mapping[str, Any] | None, *, sin_atar: int) -> tuple[int, int]:
    """``(objetivo, duro)``. Sin límite declarado, uno que no ata."""
    if limite is None:
        return sin_atar, sin_atar
    n = int(limite["n"])
    if limite.get("tipo") == "DURO":
        return n, n
    return n, sin_atar


#: Los propósitos declarados del banco que piden la ampliación por categoría
#: (M20, ADR-129; ``Peticion.amplia_por_categoria``). **Lista cerrada**, y
#: esa es la diferencia que introduce ADR-177 (H4 de ADR-148, incidencia
#: #581): la activación se decide por PERTENENCIA a un vocabulario cerrado
#: —el mismo patrón que ``_modo``, ``_cardinalidad`` o los vocabularios de
#: las puertas—, no por buscar una subcadena dentro de un texto libre.
#:
#: Su contenido es exactamente el conjunto que el banco activaba antes del
#: cambio: de los siete propósitos que las 47 filas declaran, solo
#: ``ensamblar_contexto_b05`` contenía «contexto», y por eso solo
#: ``B04-CA-33`` y ``B04-CA-34`` sembraban. No se amplía ni se recorta: la
#: incidencia #581 deja fuera, por decisión del propietario del 12-09-2026,
#: cambiar qué peticiones activan la ampliación.
#:
#: Un propósito nuevo en el banco NO amplía por accidente de redacción: hay
#: que añadirlo aquí, que es justamente lo que se quiere que cueste.
PROPOSITOS_QUE_AMPLIAN_POR_CATEGORIA: Final[frozenset[str]] = frozenset({"ensamblar_contexto_b05"})


def peticion_desde_caso(
    caso: Mapping[str, Any],
    *,
    operation_id: str,
    ambito: Ambito,
    limite_sin_atar: int,
) -> Peticion:
    """La ``Peticion`` de un caso del banco, con su propia ``peticion_p2``
    (modo, propósito, permiso, cardinalidad, límite) — no una política
    uniforme para las 47."""
    peticion_p2 = caso["peticion_p2"]
    modo_declarado = str(peticion_p2["modo"])
    permiso = str(peticion_p2["permiso"])
    proposito = "" if permiso == PERMISO_SIN_AUTORIZAR else str(peticion_p2["proposito"])
    # ADR-177: la ampliación por categoría sale del propósito DECLARADO por
    # pertenencia a la lista cerrada de arriba, y un permiso sin autorizar la
    # apaga por la misma razón que vacía el propósito — una operación que no
    # está autorizada a recuperar tampoco lo está a recuperar más. Hasta
    # ADR-177 ese apagado ocurría de rebote (el propósito vacío no contenía
    # la subcadena); ahora está dicho, y ``test_peticion_desde_caso_apaga_la_
    # ampliacion_sin_permiso`` lo fija.
    amplia_por_categoria = (
        permiso != PERMISO_SIN_AUTORIZAR
        and str(peticion_p2["proposito"]) in PROPOSITOS_QUE_AMPLIAN_POR_CATEGORIA
    )
    objetivo, duro = _limites(peticion_p2["limite"], sin_atar=limite_sin_atar)
    corte_registro = peticion_p2["corte_registro"]
    cardinalidad = _cardinalidad(str(peticion_p2["cardinalidad"]))
    objetivos = (
        max(1, len(caso["resultado_esperado"])) if cardinalidad is Cardinalidad.EXACTA else 1
    )
    return Peticion(
        operation_id=operation_id,
        consulta=str(caso["consulta"]),
        proposito=proposito,
        amplia_por_categoria=amplia_por_categoria,
        modo=_modo(modo_declarado),
        ambito=ambito,
        ventana=VentanaTemporal(
            tiempo_objetivo=_instante(str(peticion_p2["tiempo_objetivo"])),
            corte_de_registro=None if corte_registro is None else str(corte_registro),
            tiempo_objetivo_desde=_instante_inicial(str(peticion_p2["tiempo_objetivo"])),
        ),
        cardinalidad=cardinalidad,
        limite_objetivo=objetivo,
        limite_duro=duro,
        admite_no_vigentes=modo_declarado == MODO_HISTORICO,
        objetivos=objetivos,
    )


__all__ = [
    "MODO_HISTORICO",
    "PERMISO_SIN_AUTORIZAR",
    "PROPOSITOS_QUE_AMPLIAN_POR_CATEGORIA",
    "CasoNoTraducibleError",
    "peticion_desde_caso",
]
