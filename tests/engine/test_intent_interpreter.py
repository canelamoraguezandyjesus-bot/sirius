"""interpretar_intencion_v0: heurística determinista de texto libre (ADR-042).

Marcador de posición v0 -no es el intérprete con modelo que exige
arquitectura §11-, pero determinista: misma entrada, misma
:class:`IntentSignal` siempre.
"""

from __future__ import annotations

import pytest

from sirius_engine.domain.escalation import CausaEscalado
from sirius_engine.domain.intent import TipoIntencion
from sirius_engine.domain.work_item import WorkItemClass
from sirius_engine.intent_interpreter import interpretar_intencion_v0


@pytest.mark.parametrize("mensaje", ("hola", "Hola", "gracias", "vale", "  ", ""))
def test_saludos_y_mensajes_vacios_son_conversar(mensaje: str) -> None:
    assert interpretar_intencion_v0(mensaje).tipo is TipoIntencion.CONVERSAR


@pytest.mark.parametrize(
    "mensaje",
    (
        "¿Qué pasó con el bloque B12?",
        "¿Cuál es el estado de la incidencia 177?",
        "¿Cómo va la migración de la base de datos?",
    ),
)
def test_preguntas_sobre_el_pasado_son_consultar_pasado(mensaje: str) -> None:
    signal = interpretar_intencion_v0(mensaje)
    assert signal.tipo is TipoIntencion.CONSULTAR_PASADO
    assert signal.consulta == mensaje


@pytest.mark.parametrize(
    "mensaje",
    (
        "Quizá deberíamos revisar el enfoque del despachador",
        "¿Deberíamos usar SQLite o un fichero plano?",
        "Tal vez convendría separar esto en dos bloques",
    ),
)
def test_debate_y_exploracion_no_crean_trabajo(mensaje: str) -> None:
    assert interpretar_intencion_v0(mensaje).tipo is TipoIntencion.EXPLORAR


def test_mensaje_sin_verbo_reconocido_es_ambigua() -> None:
    signal = interpretar_intencion_v0("el despachador")
    assert signal.tipo is TipoIntencion.AMBIGUA
    assert signal.pregunta_aclaratoria


@pytest.mark.parametrize(
    ("mensaje", "clase_esperada"),
    (
        ("implementa el despachador de programación", WorkItemClass.PROGRAMACION),
        ("corrige el fallo de sintaxis en context_recall", WorkItemClass.PROGRAMACION),
        ("investiga el coste real de GPT Researcher", WorkItemClass.INVESTIGACION),
        ("documenta el flujo de escalado", WorkItemClass.DOCUMENTACION),
        ("audita el ciclo de revisión dual", WorkItemClass.AUDITORIA),
        ("prepara un resumen del estado actual", WorkItemClass.CONSULTA_LARGA),
    ),
)
def test_ordenes_inequivocas_infieren_la_clase_por_el_verbo(
    mensaje: str, clase_esperada: WorkItemClass
) -> None:
    signal = interpretar_intencion_v0(mensaje)
    assert signal.tipo is TipoIntencion.ORDEN_INEQUIVOCA
    assert signal.datos_trabajo is not None
    assert signal.datos_trabajo.clase is clase_esperada


_CREDENCIALES = CausaEscalado.PERMISOS_O_CREDENCIALES_SENSIBLES
_PRIVACIDAD = CausaEscalado.PRIVACIDAD_O_INFORMACION_SENSIBLE


@pytest.mark.parametrize(
    ("mensaje", "causa_esperada"),
    (
        ("borra la base de producción", CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE),
        ("implementa esto usando una clave real de pago", CausaEscalado.GASTO_O_PRESUPUESTO),
        ("implementa esto con la credencial de administrador", _CREDENCIALES),
        ("implementa esto exportando información sensible", _PRIVACIDAD),
    ),
)
def test_ordenes_sensibles_se_clasifican_con_su_causa(
    mensaje: str, causa_esperada: CausaEscalado
) -> None:
    signal = interpretar_intencion_v0(mensaje)
    assert signal.tipo is TipoIntencion.SENSIBLE_O_MATERIAL
    assert signal.causa_sensibilidad is causa_esperada


def test_es_determinista() -> None:
    mensaje = "implementa el despachador de programación"
    assert interpretar_intencion_v0(mensaje) == interpretar_intencion_v0(mensaje)


def test_limite_de_presupuesto_configurable() -> None:
    signal = interpretar_intencion_v0("implementa X", limite_presupuesto=42.0)
    assert signal.datos_trabajo is not None
    assert signal.datos_trabajo.limites["presupuesto"] == {"limite": 42.0}
