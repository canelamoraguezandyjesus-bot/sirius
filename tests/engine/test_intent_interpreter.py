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
_DESTRUCTIVO = CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE
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


def test_el_criterio_de_terminado_nombra_una_comprobacion_no_una_tautologia() -> None:
    datos = interpretar_intencion_v0("implementa el despachador").datos_trabajo
    assert datos is not None
    assert "satisface la orden original" not in datos.criterio_terminado
    # Para programación, la comprobación que este repositorio ya exige.
    assert "validaciones obligatorias" in datos.criterio_terminado
    assert "FALLAR" in datos.criterio_terminado
    assert "ADR-001" in datos.criterio_terminado


# --- ADR-184: una PROHIBICIÓN no es una PETICIÓN -------------------------------
#
# El detector comparaba el marcador contra el texto entero y respondía «¿aparece?»
# en vez de «¿la orden lo PIDE?». La frase que prohíbe la operación contiene
# exactamente el mismo marcador que la que la pide, así que el despachador paraba
# sobre salvaguardas. Reproducido el 12-09-2026: run 34726666071 de
# `despachar-orden.yml`, trabajo `WI-20260912-235558` anotado en el diario
# `estado-del-motor` (commit e51072e) sin incidencia detrás.
#
# Los dos textos de abajo son LITERALES del diario, no paráfrasis cómodas: son
# las dos únicas órdenes de las 82 que guarda el diario que cambian de
# clasificación con el criterio nuevo, y las dos prohibían la operación.

_SALVAGUARDA_DE_WI_20260912_235558 = (
    "No borres ni reescribas ninguna entrada historica del registro: un defecto "
    "nunca se borra, y las cifras fechadas de ADR-174 son evidencia y no se tocan."
)

_SALVAGUARDA_DE_WI_20260903_030529 = (
    "AÑADE al bloque :1744-1759 una nota BREVE (dos o tres frases, sin reescribir "
    "ni borrar el bloque) que registre que la precondición quedó resuelta"
)


@pytest.mark.parametrize(
    "mensaje",
    (
        _SALVAGUARDA_DE_WI_20260912_235558,
        _SALVAGUARDA_DE_WI_20260903_030529,
    ),
)
def test_una_salvaguarda_que_prohibe_la_operacion_no_es_una_orden_sensible(mensaje: str) -> None:
    """Antes del cambio las dos fallaban con ``assert <SENSIBLE_O_MATERIAL> is not
    <SENSIBLE_O_MATERIAL>``: el detector devolvía
    ``"el mensaje contiene 'borra'"`` sobre «un defecto nunca **se borra**» y
    ``"el mensaje contiene 'borrar'"`` sobre «sin reescribir ni **borrar** el
    bloque», que es justo lo contrario de pedirlo.
    """
    assert interpretar_intencion_v0(mensaje).tipo is not TipoIntencion.SENSIBLE_O_MATERIAL


@pytest.mark.parametrize(
    ("mensaje", "causa_esperada"),
    (
        # Las cuatro tuplas de _SENSIBILIDAD comparten el mismo detector, así que
        # el criterio las alcanza a las cuatro: prohibir no es pedir en ninguna.
        ("implementa el importador sin borrar la tabla de origen", None),
        ("implementa el importador y borra la tabla de origen", _DESTRUCTIVO),
        ("implementa esto sin gastar en una clave real de pago", None),
        ("implementa esto con una clave real de pago", CausaEscalado.GASTO_O_PRESUPUESTO),
        ("implementa esto sin pedir ninguna credencial", None),
        ("implementa esto con la credencial del administrador", _CREDENCIALES),
        ("implementa el informe sin publicar ningun dato personal", None),
        ("implementa el informe publicando el dato personal del cliente", _PRIVACIDAD),
    ),
)
def test_prohibir_no_es_pedir_en_ninguna_de_las_cuatro_tuplas(
    mensaje: str, causa_esperada: CausaEscalado | None
) -> None:
    signal = interpretar_intencion_v0(mensaje)
    assert signal.causa_sensibilidad is causa_esperada


@pytest.mark.parametrize(
    "mensaje",
    (
        # La negación de OTRA oración no gobierna al marcador: la puntuación corta.
        "no toques la cola. borra la tabla de usuarios",
        "no borres el historico: elimina la cola de reintentos",
        # Ni la de otra oración coordinada, aunque no haya puntuación.
        "no toques la cola y borra la tabla de usuarios",
        # «sin embargo» y «no solo» llevan dentro un negador que no niega nada.
        "revisa el esquema; sin embargo borra la tabla de usuarios",
        "no solo elimina la cola sino tambien el indice",
        # Una prohibición en una frase no tapa una petición en otra: basta UNA
        # aparición sin negar para que la puerta pare. La segunda línea repite
        # el MISMO marcador -negado y luego pedido-, que es el caso que
        # distingue «basta una sin negar» de «decide la primera»: sin ella, una
        # versión que se quedara con la primera aparición pasaba todas las
        # demás pruebas de este fichero (mutación M6, ADR-184).
        "no borres el registro historico, pero elimina la cola de reintentos",
        "no hay que borrar el historico; hay que borrar la cola de reintentos",
        # Un negador que NO gobierna al marcador tampoco puede callar la puerta:
        # lo que sobra en `_NEGADORES` es fail-OPEN, no fail-closed (ADR-184,
        # ronda 2). Las tres primeras son la subordinada final -«para
        # evitar/impedir X, haz Y»-, donde la negación gobierna el propósito y
        # el verbo principal SÍ se está pidiendo; las dos siguientes son
        # locuciones adverbiales con `sin` que afirman; las tres últimas, verbos
        # de doble negación, donde «no + verbo + marcador» pide el marcador.
        "implementa el purgador: para impedir que crezca borra los logs",
        "para evitar duplicados elimina la tabla de origen",
        "para evitar que se llene borra la tabla de origen",
        "implementa la limpieza sin falta borra la tabla de origen",
        "implementa esto y sin duda borra la tabla de produccion",
        "implementa esto, no olvides borrar la tabla de produccion",
        "implementa esto, no dudes en borrar la tabla de produccion",
        "implementa esto, no dejes de borrar la tabla de produccion",
        # La misma doble negación con el `sin` PEGADO al marcador: «no dejes X
        # sin borrar» pide borrarlo todo. El negador más cercano es ese `sin`,
        # y sin `_negacion_anulada` la mirada se paraba en él antes de ver el
        # corte `dejes` y la puerta callaba (CODEX-002).
        "implementa esto: no dejes ninguna fila sin borrar",
        "implementa esto: no dejes la cola sin borrar",
        # Y la petición desnuda de siempre, que nunca dejó de parar.
        "borra la base de produccion",
        "elimina el historico de la cola",
    ),
)
def test_la_puerta_sigue_parando_ante_una_peticion_destructiva_de_verdad(mensaje: str) -> None:
    """ADR-184 no debilita la puerta: solo calla cuando la ÚNICA evidencia
    léxica va negada. Si estas frases dejaran de parar, el criterio sería
    fail-open en una puerta que el propietario decidió fail-closed (#324).
    """
    signal = interpretar_intencion_v0(mensaje)
    assert signal.tipo is TipoIntencion.SENSIBLE_O_MATERIAL
    assert signal.causa_sensibilidad is _DESTRUCTIVO


def test_la_mencion_entre_comillas_sigue_parando_y_esta_declarado() -> None:
    """Límite DECLARADO de ADR-184: el criterio mira la negación, no la
    diferencia entre USAR la palabra y NOMBRARLA. Es el texto literal de
    `WI-20260903-095428`, que sigue parando -y debe seguir-, porque el lado
    seguro del error es parar de más. Esta prueba existe para que ese límite
    sea visible y deliberado, no un descubrimiento del próximo que lo pise.
    """
    mensaje = "su lista de marcadores contiene la palabra «borrar» y mi texto la usaba dentro"
    assert interpretar_intencion_v0(mensaje).tipo is TipoIntencion.SENSIBLE_O_MATERIAL
