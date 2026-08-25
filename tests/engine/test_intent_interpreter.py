"""interpretar_intencion_v0: heurística determinista de texto libre (ADR-043).

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


# --- H-19: sensibilidad antes que marcadores de pasado, frontera de palabra,
# --- y puntuación en el primer verbo -----------------------------------------
#
# docs/audits/evidencia-H-19.md mide los tres fallos con salidas literales.
# Los tres comparten raíz: comparación de marcadores por subcadena (`in`) sin
# frontera de palabra, más el orden en que se comprueban las clasificaciones.
# Decisión del propietario en #324: la sensibilidad se comprueba SIEMPRE
# antes que los marcadores de pasado, aunque a veces avise de más.


@pytest.mark.parametrize(
    ("mensaje", "causa_esperada"),
    (
        (
            "borra el estado de la base de produccion",
            CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE,
        ),
        ("elimina el estado del cache", CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE),
        (
            "implementa esto usando una clave real de pago y borra el estado de la cola",
            CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE,
        ),
    ),
)
def test_sensibilidad_se_comprueba_antes_que_marcadores_de_pasado(
    mensaje: str, causa_esperada: CausaEscalado
) -> None:
    """Antes del fix, estas frases contienen un marcador de pasado ("estado
    de") por casualidad y la puerta las despachaba como CONSULTAR_PASADO sin
    llegar nunca al detector de sensibilidad: fail-open en una puerta
    fail-closed. Fallaban con ``AssertionError: assert <CONSULTAR_PASADO>
    is <SENSIBLE_O_MATERIAL>``.
    """
    signal = interpretar_intencion_v0(mensaje)
    assert signal.tipo is TipoIntencion.SENSIBLE_O_MATERIAL
    assert signal.causa_sensibilidad is causa_esperada


@pytest.mark.parametrize(
    ("mensaje", "clase_esperada"),
    (
        ("documenta el estado del motor", WorkItemClass.DOCUMENTACION),
        ("audita el estado de las pruebas", WorkItemClass.AUDITORIA),
        ("corrige el estado del despachador", WorkItemClass.PROGRAMACION),
    ),
)
def test_marcador_de_pasado_respeta_frontera_de_palabra(
    mensaje: str, clase_esperada: WorkItemClass
) -> None:
    """Estas órdenes legítimas sobre la situación actual de un módulo salían
    clasificadas como CONSULTAR_PASADO: en dos casos "estado de" es subcadena
    de "estado del" sin frontera de palabra; en el tercero el marcador
    aparece de verdad, pero un primer verbo reconocido (audita/documenta/
    corrige) debe decidir antes que ese marcador. Fallaban con
    ``AssertionError: assert <TipoIntencion.CONSULTAR_PASADO> is <TipoIntencion.ORDEN_INEQUIVOCA>``.
    """
    signal = interpretar_intencion_v0(mensaje)
    assert signal.tipo is TipoIntencion.ORDEN_INEQUIVOCA
    assert signal.datos_trabajo is not None
    assert signal.datos_trabajo.clase is clase_esperada


@pytest.mark.parametrize(
    "mensaje",
    (
        "«Corrige el fallo»",
        '"Corrige el fallo"',
        "Corrige, ya, el fallo",
    ),
)
def test_primer_verbo_ignora_puntuacion_de_borde(mensaje: str) -> None:
    """``_primer_verbo`` no quitaba la puntuación, así que el formato que el
    propio ``--help`` propone como ejemplo (verbo entre comillas angulares)
    salía AMBIGUA mientras el mismo texto sin comillas se despachaba bien.
    Fallaban con
    ``AssertionError: assert <TipoIntencion.AMBIGUA> is <TipoIntencion.ORDEN_INEQUIVOCA>``.
    """
    signal = interpretar_intencion_v0(mensaje)
    assert signal.tipo is TipoIntencion.ORDEN_INEQUIVOCA
    assert signal.datos_trabajo is not None
    assert signal.datos_trabajo.clase is WorkItemClass.PROGRAMACION


# --- Alcance y criterio derivados de la clase -------------------------------
#
# Antes, estos dos campos eran constantes: un eco literal de la orden y una
# tautología ("el entregable existe y satisface la orden"). El eco iba a la
# sección "Alcance permitido" del cuerpo de la incidencia -la única de las dos
# que alguien obedece- sin acotar nada, y la tautología a una sección que
# ninguna comprobación puede falsar.


@pytest.mark.parametrize(
    ("mensaje", "clase"),
    [
        ("implementa el despachador", WorkItemClass.PROGRAMACION),
        ("documenta el flujo de escalado", WorkItemClass.DOCUMENTACION),
        ("investiga el coste real", WorkItemClass.INVESTIGACION),
        ("audita el ciclo de revision", WorkItemClass.AUDITORIA),
        ("prepara un resumen", WorkItemClass.CONSULTA_LARGA),
    ],
)
def test_el_alcance_y_el_criterio_dependen_de_la_clase(mensaje: str, clase: WorkItemClass) -> None:
    datos = interpretar_intencion_v0(mensaje).datos_trabajo
    assert datos is not None
    assert datos.clase is clase
    # No son constantes: cada clase acota una cosa distinta.
    otras = {
        interpretar_intencion_v0(otro).datos_trabajo.entregable  # type: ignore[union-attr]
        for otro in ("implementa x", "documenta x", "investiga x", "audita x", "prepara x")
    }
    assert len(otras) == 5, "cinco clases deben dar cinco alcances distintos"


def test_el_alcance_no_repite_la_orden_que_ya_esta_en_el_objetivo() -> None:
    orden = "Corrige la cita rota al contrato en sirius_codex_review.py"
    datos = interpretar_intencion_v0(orden).datos_trabajo
    assert datos is not None
    assert datos.objetivo == orden
    assert orden not in datos.entregable, (
        "el objetivo ya lleva la orden entera justo encima; repetirla en el "
        "alcance no acota nada, que era el defecto"
    )
    assert "y nada mas" in datos.entregable.replace("á", "a"), (
        "el alcance tiene que ACOTAR, no describir"
    )


# --- H-19-REV-001: el verbo solo se adelanta a los marcadores de pasado,
# --- no a exploración ni a la interrogación final ---------------------------
#
# #324 autorizó -y evidencia-H-19.md midió- únicamente el caso "verbo
# reconocido antes que marcadores de PASADO". La ronda anterior adelantó el
# verbo también por delante de exploración y de "?", sin que nadie lo pidiera
# ni lo midiera. Frente a esos dos, debe mantenerse el orden previo a H-19:
# esos dos chequeos antes que el verbo.


@pytest.mark.parametrize(
    "mensaje",
    (
        "Corrige esto, no crees que deberiamos revisarlo antes?",
        "Implementa esto, no se si es buena idea?",
    ),
)
def test_verbo_no_se_adelanta_a_exploracion_ni_a_pregunta_final(mensaje: str) -> None:
    """Antes de esta corrección, un primer verbo reconocido decidía
    ORDEN_INEQUIVOCA sin llegar nunca a comprobar exploración ni la
    interrogación final, porque el chequeo del verbo se había adelantado
    también por delante de esos dos (no solo de los marcadores de pasado,
    que es lo único que #324 decidió). Fallaba con
    ``AssertionError: assert <TipoIntencion.ORDEN_INEQUIVOCA> is <TipoIntencion.EXPLORAR>``.
    """
    signal = interpretar_intencion_v0(mensaje)
    assert signal.tipo is TipoIntencion.EXPLORAR


# --- CODEX-001: variantes flexionadas de marcadores sensibles ---------------
#
# Exigir frontera de palabra en ambos extremos (H-19) dejó de reconocer
# flexiones y enclíticos comunes -"credenciales", "contraseñas",
# "eliminarlo"- que antes activaban la barrera fail-closed. La corrección
# admite explícitamente esas variantes, sin volver a la búsqueda libre por
# subcadenas que confundía "estado de" con "estado del".


@pytest.mark.parametrize(
    ("mensaje", "causa_esperada"),
    (
        ("implementa autenticación usando credenciales de administrador", _CREDENCIALES),
        ("implementa esto guardando las contraseñas en texto plano", _CREDENCIALES),
        (
            "implementa este cambio para eliminarlo todo",
            CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE,
        ),
    ),
)
def test_variantes_flexionadas_de_marcadores_sensibles_escalan(
    mensaje: str, causa_esperada: CausaEscalado
) -> None:
    """Antes de esta corrección, estas frases contenían la flexión de un
    marcador sensible ("credenciales", "contraseñas", "eliminarlo") que la
    frontera de palabra en ambos extremos dejaba de reconocer, así que un
    primer verbo reconocido despachaba la orden como ORDEN_INEQUIVOCA sin
    pasar por el escalado fail-closed. Fallaba con ``AssertionError: assert
    <TipoIntencion.ORDEN_INEQUIVOCA> is <TipoIntencion.SENSIBLE_O_MATERIAL>``.
    """
    signal = interpretar_intencion_v0(mensaje)
    assert signal.tipo is TipoIntencion.SENSIBLE_O_MATERIAL
    assert signal.causa_sensibilidad is causa_esperada


def test_el_criterio_de_terminado_nombra_una_comprobacion_no_una_tautologia() -> None:
    datos = interpretar_intencion_v0("implementa el despachador").datos_trabajo
    assert datos is not None
    assert "satisface la orden original" not in datos.criterio_terminado
    # Para programación, la comprobación que este repositorio ya exige.
    assert "validaciones obligatorias" in datos.criterio_terminado
    assert "FALLAR" in datos.criterio_terminado
    assert "ADR-001" in datos.criterio_terminado
