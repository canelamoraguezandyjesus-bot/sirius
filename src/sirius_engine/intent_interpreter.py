"""``interpretar_intencion_v0``: heurística determinista de texto libre a intención.

Arquitectura §11 marca "interpretar intención y estructurar borradores" como
algo que **necesita modelo** [M]. Este módulo NO es ese intérprete: es un
marcador de posición v0, deliberadamente pequeño (patrones léxicos, sin
dependencia nueva), documentado como tal (ADR-043). Existe para que la
interfaz v0 (:mod:`sirius_engine.session`) pueda demostrarse con texto libre
hoy; el día que exista un intérprete real con modelo, sustituye a esta
función sin que :mod:`sirius_engine.gate` -que solo conoce
:class:`~sirius_engine.domain.intent.IntentSignal`- tenga que cambiar una
línea.

Determinista: el mismo texto produce siempre la misma
:class:`~sirius_engine.domain.intent.IntentSignal` (ninguna rama depende de
un reloj, de aleatoriedad ni de red).
"""

from __future__ import annotations

import re

from sirius_engine.domain.escalation import CausaEscalado
from sirius_engine.domain.intent import DatosNuevoTrabajo, IntentSignal, TipoIntencion
from sirius_engine.domain.work_item import WorkItemClass

#: Presupuesto por defecto asignado a una orden inequívoca cuando el
#: llamador no impone uno propio (ver ``interpretar_intencion_v0(limite_presupuesto=...)``).
PRESUPUESTO_POR_DEFECTO = 10.0

_MARCADORES_SALUDO = frozenset(
    {"hola", "buenos dias", "buenas tardes", "buenas noches", "gracias", "vale", "ok", "adios"}
)

_MARCADORES_EXPLORACION = (
    "quiza",
    "tal vez",
    "podriamos",
    "seria bueno",
    "no se si",
    "a lo mejor",
    "estoy pensando",
    "que te parece",
    "convendria",
)

_MARCADORES_PASADO = ("paso con", "estado de", "que hay de", "como va", "que se hizo")

_VERBO_A_CLASE: dict[str, WorkItemClass] = {
    "implementa": WorkItemClass.PROGRAMACION,
    "implementar": WorkItemClass.PROGRAMACION,
    "corrige": WorkItemClass.PROGRAMACION,
    "corregir": WorkItemClass.PROGRAMACION,
    "investiga": WorkItemClass.INVESTIGACION,
    "investigar": WorkItemClass.INVESTIGACION,
    "documenta": WorkItemClass.DOCUMENTACION,
    "documentar": WorkItemClass.DOCUMENTACION,
    "escribe": WorkItemClass.DOCUMENTACION,
    "redacta": WorkItemClass.DOCUMENTACION,
    "audita": WorkItemClass.AUDITORIA,
    "auditar": WorkItemClass.AUDITORIA,
}

_VERBOS_IMPERATIVOS_SIN_CLASE = ("crea", "prepara", "genera", "responde")

#: Qué queda autorizado a cambiar, por clase. Va a la sección "Alcance
#: permitido" del cuerpo de la incidencia, que es la ÚNICA de las dos secciones
#: derivadas que alguien obedece: al implementador se le ordena hacer solo lo
#: que autorice y detenerse con ``BLOCKED_BY_DECISION`` si necesita salirse
#: (``scripts/automation/prompts/implementer.md``). Antes iba ahí un eco literal
#: de la orden -que ya está completa en "Objetivo", justo encima-: repetirla no
#: acotaba nada. Estas frases acotan, y no dicen nada que la orden no diga: no
#: describen QUÉ hay que hacer -eso es el objetivo- sino QUÉ TIPO de cambio
#: queda autorizado, que se sigue de la clase y de nada más.
_ALCANCE_POR_CLASE: dict[WorkItemClass, str] = {
    WorkItemClass.PROGRAMACION: (
        "El cambio en el código que pide el objetivo, con sus pruebas, y nada más."
    ),
    WorkItemClass.DOCUMENTACION: (
        "El documento o el pasaje que pide el objetivo, y nada más. "
        "Sin cambios de comportamiento en el código."
    ),
    WorkItemClass.INVESTIGACION: (
        "Averiguar y escribir lo que pide el objetivo. "
        "Sin cambios en el código ni en la configuración del proyecto."
    ),
    WorkItemClass.AUDITORIA: (
        "Examinar y reportar lo que pide el objetivo. "
        "Sin arreglar por el camino lo que se encuentre: un hallazgo se reporta, no se parchea."
    ),
    WorkItemClass.CONSULTA_LARGA: (
        "Responder lo que pide el objetivo. Sin cambios en el árbol del repositorio."
    ),
}

#: Qué comprobación declara el trabajo terminado, por clase. La arquitectura
#: pide de este campo "qué comprobación lo declara terminado"; el v0 ponía una
#: tautología -"el entregable existe y satisface la orden"- que ninguna
#: comprobación puede falsar, que es justo la familia de defecto que ADR-001
#: nombra: una garantía puesta donde no puede cumplirse.
#:
#: Estas frases NO inventan un criterio para cada orden -derivar eso del
#: lenguaje natural necesita modelo, y este intérprete es un apaño (ADR-043)-.
#: Citan la disciplina que ya rige en este repositorio para esa clase de
#: trabajo. Citar una regla existente no es afirmar de más.
_CRITERIO_POR_CLASE: dict[WorkItemClass, str] = {
    WorkItemClass.PROGRAMACION: (
        "Las validaciones obligatorias de esta incidencia, en verde, y al menos una prueba "
        "que fije lo que el objetivo pide y que se haya visto FALLAR antes del cambio "
        "(ADR-001). Si el objetivo describe un fallo concreto, esa prueba lo reproduce."
    ),
    WorkItemClass.DOCUMENTACION: (
        "El texto existe en el árbol y cada afirmación comprobable que hace cita el fichero "
        "y la línea que la sostiene (ADR-001). Lo que no quede demostrado se dice aparte."
    ),
    WorkItemClass.INVESTIGACION: (
        "El resultado está escrito con el método y los datos que lo sostienen, y con un "
        "apartado explícito de lo que NO queda demostrado (ADR-001)."
    ),
    WorkItemClass.AUDITORIA: (
        "Cada hallazgo llega con su evidencia reproducible -fichero:línea o comprobación "
        "ejecutable- y su gravedad. Lo que no tenga evidencia se declara como sospecha, "
        "no como hallazgo (ADR-001)."
    ),
    WorkItemClass.CONSULTA_LARGA: (
        "La respuesta existe y dice de dónde sale cada dato. Lo que no se haya podido "
        "comprobar se dice, en vez de rellenarse (ADR-001)."
    ),
}

_MARCADORES_DESTRUCTIVO = ("borra", "borrar", "elimina", "eliminar", "destruye", "resetea todo")
_MARCADORES_GASTO = ("clave real", "usa una clave de pago", "aumenta el presupuesto", "gasta")
_MARCADORES_CREDENCIALES = ("credencial", "clave api", "contraseña", "permiso de administrador")
_MARCADORES_PRIVACIDAD = ("dato personal", "informacion sensible", "publica los datos")

_SENSIBILIDAD: tuple[tuple[tuple[str, ...], CausaEscalado], ...] = (
    (_MARCADORES_DESTRUCTIVO, CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE),
    (_MARCADORES_GASTO, CausaEscalado.GASTO_O_PRESUPUESTO),
    (_MARCADORES_CREDENCIALES, CausaEscalado.PERMISOS_O_CREDENCIALES_SENSIBLES),
    (_MARCADORES_PRIVACIDAD, CausaEscalado.PRIVACIDAD_O_INFORMACION_SENSIBLE),
)

#: La QUINTA causa (ADR-188): los prefijos de ruta que el motor NO puede
#: escribir. ADR-002 decidió no darle a la credencial de la automatización el
#: alcance sobre los ficheros de workflow, y dejó escrito que los encargos con
#: ese alcance se hagan en sesión interactiva -avisando él mismo de que eso era
#: «un procedimiento operativo manual, no una garantía»-. La incidencia #607
#: cobró el aviso: se despachó al ciclo automático, el encargo hizo el trabajo
#: entero y GitHub rechazó el push. La lista es cerrada y vive aquí, con sus
#: cuatro hermanas, porque esta causa es de la misma forma que ellas: la orden
#: pide tocar algo que el motor no puede escribir, así que no se despacha, se
#: escala.
PREFIJOS_QUE_EL_MOTOR_NO_PUEDE_ESCRIBIR: tuple[str, ...] = (".github/",)

#: La palabra por la que se sustituye una ruta bajo un prefijo vetado antes de
#: pasarla por :func:`_marcador_pedido`. Es un rodeo con un motivo medido: esa
#: función parte el texto en oraciones por la puntuación
#: (:data:`_SEPARADOR_DE_ORACION`) y saca las palabras con ``\w+``, así que una
#: ruta -que empieza por un punto y lleva barras, asteriscos y puntos dentro- no
#: es UNA palabra para ella, sino un montón de cortes de oración. Sustituida por
#: una palabra corriente, la ruta atraviesa intacta la misma maquinaria que ya
#: distingue pedir de prohibir (ADR-184), sin duplicar ni una línea de ella.
_MARCADOR_DE_RUTA_VETADA = "rutabajounprefijovetado"

#: Lo que se traga la sustitución ALREDEDOR de la ruta: las comillas y los
#: acentos graves que la citan. No es cosmético. Si el acento grave de «no
#: toques `.github/**`» se quedara donde está, partiría la oración justo entre
#: el negador y la ruta, el negador quedaría al otro lado y la puerta pararía
#: sobre una frase que dice exactamente lo contrario. Los paréntesis y los
#: corchetes NO entran: ahí sí son puntuación de la oración, y tragárselos
#: uniría dos oraciones que el castellano tiene separadas.
_COMILLAS_QUE_CITAN_UNA_RUTA = "[`'\"«»]*"

#: El resto de la ruta tras el prefijo: lo que un camino de fichero puede
#: llevar, comodines incluidos, porque «.github/**» nombra el mismo sitio que
#: «.github/workflows/x.yml».
_RESTO_DE_LA_RUTA = r"[\w./*?+-]*"


def _patron_de_ruta_vetada(prefijo: str) -> re.Pattern[str]:
    r"""El patrón que reconoce una ruta bajo ``prefijo``, derivado del propio prefijo.

    Derivado y no escrito aparte, para que añadir un prefijo a
    :data:`PREFIJOS_QUE_EL_MOTOR_NO_PUEDE_ESCRIBIR` no exija acordarse de
    escribir también su expresión -que es la familia de defecto que este ADR
    viene a cerrar-.

    ``(?!\w)`` es la frontera que hace falta: sin ella ``.github`` casaba dentro
    de ``sirius_engine.ports.github_mirror``, que es un módulo de Python y no una
    carpeta de workflows. Salió midiendo, no razonando: era 1 de los 29 encargos
    del diario que nombran la carpeta (ADR-188).
    """
    carpeta = prefijo.rstrip("/")
    return re.compile(
        f"{_COMILLAS_QUE_CITAN_UNA_RUTA}{re.escape(carpeta)}"
        f"(?!\\w){_RESTO_DE_LA_RUTA}{_COMILLAS_QUE_CITAN_UNA_RUTA}"
    )


_RUTAS_VETADAS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (prefijo, _patron_de_ruta_vetada(prefijo))
    for prefijo in PREFIJOS_QUE_EL_MOTOR_NO_PUEDE_ESCRIBIR
)

#: Lo que, delante de un marcador y dentro de su misma oración, lo convierte en
#: una PROHIBICIÓN o una NEGACIÓN en vez de una petición (ADR-184). La lista es
#: CERRADA y está declarada: lo que FALTE aquí no silencia nada, así que una
#: lista incompleta sigue parando -fail-closed, el mismo criterio del
#: propietario en #324 (H-19)-.
#:
#: Lo que SOBRA, en cambio, sí es fail-open: una palabra que aparece delante
#: del marcador sin negarlo silencia una petición de verdad. Por eso NO están
#: los infinitivos `evitar` e `impedir`: en castellano encabezan la subordinada
#: final «para evitar/impedir X, borra Y», donde la negación gobierna el
#: propósito y NO al verbo principal, que sí se está pidiendo. Por el mismo
#: motivo NO están las formas de subjuntivo -`evites`, `eviten`, `impidas`,
#: `impidan`-: son las que selecciona «para que», y «para que impidan que
#: crezca borra los logs» es el MISMO giro final con otro sujeto
#: (CLAUDE-R2-001). Se quedan solo las formas que no lo encabezan: el
#: imperativo y el presente de indicativo -«evita borrar», «impide que se
#: borre»-. El resto de giros con negador que no niega se corta desde
#: :data:`_CORTES_DE_ORACION`.
_NEGADORES = frozenset(
    {
        "no",
        "ni",
        "nunca",
        "jamas",
        "tampoco",
        "sin",
        "ningun",
        "ninguna",
        "ninguno",
        "ningunos",
        "ningunas",
        "prohibido",
        "prohibida",
        "prohibidos",
        "prohibidas",
        "prohibe",
        "prohiben",
        "prohibir",
        "evita",
        "impide",
    }
)

#: Verbos que, precedidos de un negador, PIDEN el marcador en vez de
#: prohibirlo: «no olvides borrar», «no dudes en borrar», «no dejes de
#: borrar». Cortan la mirada hacia atrás como cualquier otro corte y, además,
#: ANULAN al negador que quede entre ellos y el marcador: «no dejes ninguna
#: fila sin borrar» PIDE borrarlas todas, aunque el `sin` esté pegado al
#: marcador y la mirada se pare en él antes de llegar al corte (CODEX-002).
_VERBOS_DE_DOBLE_NEGACION = frozenset(
    {
        "olvides",
        "olvide",
        "olviden",
        "olvidar",
        "dudes",
        "dude",
        "duden",
        "dudar",
        "dejes",
        "deje",
        "dejen",
        "dejar",
    }
)

#: Palabras que CORTAN la mirada hacia atrás: si aparecen entre el negador y el
#: marcador, el negador ya no gobierna al marcador. Sin ellas, «no toques la
#: cola y borra la tabla» quedaría silenciado por el «no» de la otra oración
#: coordinada, y «sin embargo borra la tabla» o «no solo borra X sino Y» lo
#: quedarían por un «sin» y un «no» que no niegan nada. Cortar es la dirección
#: SEGURA: un corte de más hace que la puerta pare, no que deje pasar.
#:
#: Van aquí tres familias, y las tres por el mismo motivo -el negador que las
#: precede no niega al marcador-:
#:
#: * los nexos que abren otra oración coordinada o adversativa (`y`, `pero`,
#:   `sino`, `embargo`…);
#: * el sustantivo de las locuciones adverbiales con `sin` que afirman en vez
#:   de negar: «sin duda borra la tabla», «sin falta borra la tabla». Ahí `sin`
#:   gobierna al sustantivo, no al marcador. `falta` solo corta PEGADO a ese
#:   `sin` -:data:`_CORTES_TRAS_SIN`-, porque fuera de la locución es el
#:   sustantivo de «no hace falta borrar», que es una prohibición y volvía a
#:   parar la puerta (CODEX-003). `duda` corta en cualquier posición porque
#:   fuera de la locución es la forma verbal de «no duda en borrar», que
#:   también pide el marcador;
#: * los verbos de doble negación, de :data:`_VERBOS_DE_DOBLE_NEGACION`.
_CORTES_DE_ORACION = (
    frozenset(
        {
            "y",
            "e",
            "o",
            "u",
            "pero",
            "sino",
            "aunque",
            "mas",
            "embargo",
            "solo",
            "solamente",
            "duda",
        }
    )
    | _VERBOS_DE_DOBLE_NEGACION
)

#: Cortes que solo valen dentro de su locución, es decir con `sin`
#: inmediatamente delante. En cualquier otra posición NO cortan: «no hace
#: falta borrar la tabla» es una prohibición, y un corte incondicional en
#: `falta` dejaba el `no` sin ver y hacía parar a la puerta sobre una frase
#: que dice justo lo contrario (CODEX-003).
_CORTES_TRAS_SIN = frozenset({"falta"})

#: Cuántas palabras hacia atrás se busca el negador. Cuatro cubre las formas
#: perifrásticas del castellano -«no se puede borrar», «no hay que eliminar»,
#: «un defecto nunca se borra»- sin llegar a la oración anterior, que ya está
#: cortada por la puntuación.
_VENTANA_DE_NEGACION = 4

#: La puntuación separa oraciones: lo que hay al otro lado no gobierna al
#: marcador. Es lo que hace que «no borres nada: elimina la cola» siga parando.
_SEPARADOR_DE_ORACION = re.compile(r"[^\w\s]+")

_PALABRA = re.compile(r"\w+")


def _normalizar(mensaje: str) -> str:
    sin_acentos = (
        mensaje.casefold()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("¿", "")
        .replace("¡", "")
    )
    return re.sub(r"\s+", " ", sin_acentos).strip()


def _marcador_presente(normalizado: str, marcador: str) -> bool:
    """``True`` si ``marcador`` aparece en ``normalizado`` como palabra completa.

    ``in`` por sí solo compara subcadenas: un marcador de dos palabras como
    "estado de" casa dentro de "estado del" porque lo contiene por
    casualidad (H-19). La frontera de palabra evita ese falso positivo sin
    dejar de reconocer el marcador cuando de verdad aparece.
    """
    return re.search(rf"\b{re.escape(marcador)}\b", normalizado) is not None


def _va_negado(palabras: list[str], indice: int) -> bool:
    """``True`` si un negador gobierna a la palabra ``indice`` de ``palabras``.

    Se mira hacia atrás y solo hacia atrás, hasta
    :data:`_VENTANA_DE_NEGACION` palabras, y la mirada se detiene en el primer
    corte de oración. Solo hacia atrás porque en castellano la negación y la
    prohibición preceden al verbo ("no borres", "queda prohibido eliminar",
    "un defecto nunca se borra"); la pospuesta -"eliminar esto queda
    prohibido"- NO se detecta a propósito, y su consecuencia es que la puerta
    para de más, que es el lado seguro.
    """
    for desplazamiento, palabra in enumerate(
        reversed(palabras[max(0, indice - _VENTANA_DE_NEGACION) : indice]), start=1
    ):
        posicion = indice - desplazamiento
        if palabra in _CORTES_TRAS_SIN:
            if posicion > 0 and palabras[posicion - 1] == "sin":
                return False
            continue
        if palabra in _CORTES_DE_ORACION:
            return False
        if palabra in _NEGADORES:
            return not _negacion_anulada(palabras, posicion)
    return False


def _negacion_anulada(palabras: list[str], indice_negador: int) -> bool:
    """``True`` si el negador de ``indice_negador`` va dentro de una doble negación.

    «no dejes ninguna fila SIN borrar» PIDE borrar todas las filas: el `sin`
    que precede al marcador no lo prohíbe, porque a su vez está gobernado por
    «no dejes». Sin esta comprobación la mirada hacia atrás se paraba en ese
    `sin` -el negador más cercano- y silenciaba la puerta antes de llegar al
    corte `dejes` (CODEX-002).

    Solo anulan los verbos de :data:`_VERBOS_DE_DOBLE_NEGACION`, y solo si
    ellos mismos van precedidos de un negador: es la estructura «no + verbo +
    … + negador + marcador» y ninguna otra. El sustantivo de las locuciones
    («sin duda no hay que borrar») queda fuera a propósito, porque ahí la
    negación posterior sí prohíbe.
    """
    ventana = palabras[max(0, indice_negador - _VENTANA_DE_NEGACION) : indice_negador]
    for desplazamiento, palabra in enumerate(reversed(ventana), start=1):
        if palabra not in _VERBOS_DE_DOBLE_NEGACION:
            continue
        indice_verbo = indice_negador - desplazamiento
        previas = palabras[max(0, indice_verbo - _VENTANA_DE_NEGACION) : indice_verbo]
        return any(previa in _NEGADORES for previa in previas)
    return False


def _marcador_pedido(normalizado: str, marcador: str) -> bool:
    """``True`` si ``marcador`` aparece PIDIENDO la operación, no prohibiéndola.

    La presencia por sí sola no distingue una orden de su salvaguarda: la
    frase que PROHIBE la operación contiene exactamente el mismo marcador que
    la que la PIDE, así que ``_marcador_presente`` clasificaba como petición
    la salvaguarda "un defecto nunca se borra" (ADR-184; reproducido en
    ``WI-20260912-235558``, run 34726666071). Aquí una aparición cuenta solo
    si NO va negada, y basta UNA sin negar para que cuente: una orden que
    prohíbe algo en una frase y lo pide en otra sigue parando.
    """
    palabras_marcador = marcador.split(" ")
    largo = len(palabras_marcador)
    for oracion in _SEPARADOR_DE_ORACION.split(normalizado):
        palabras = _PALABRA.findall(oracion)
        for indice in range(len(palabras) - largo + 1):
            if palabras[indice : indice + largo] != palabras_marcador:
                continue
            if not _va_negado(palabras, indice):
                return True
    return False


def _prefijo_vetado_pedido(normalizado: str) -> str | None:
    """El prefijo que ``normalizado`` PIDE tocar y el motor no puede escribir, o ``None``.

    La QUINTA causa (ADR-188). Es de la misma forma que las otras cuatro y usa
    exactamente su maquinaria: la ruta se sustituye por
    :data:`_MARCADOR_DE_RUTA_VETADA` -una palabra corriente- y se pregunta por
    ella a :func:`_marcador_pedido`, que ya sabe que una aparición NEGADA
    prohíbe en vez de pedir (ADR-184).

    Que la reutilice no es ahorro de líneas, es lo que hace utilizable la
    puerta. De los 29 encargos del diario del motor que nombran la carpeta, 28
    la nombran para EXCLUIRLA -«no toques `.github/**` (ADR-002)»- y uno solo
    declaró alcance sobre ella. Sin la negación, la puerta pararía las 29; con
    ella para 9. La medida entera está en ADR-188, incluido lo que sigue
    parando de más y por qué se acepta.
    """
    for prefijo, patron in _RUTAS_VETADAS:
        sustituido = patron.sub(f" {_MARCADOR_DE_RUTA_VETADA} ", normalizado)
        if _marcador_pedido(sustituido, _MARCADOR_DE_RUTA_VETADA):
            return prefijo
    return None


def alcance_que_el_motor_no_puede_escribir(mensaje: str) -> str | None:
    """El prefijo vetado que ``mensaje`` pide tocar, o ``None`` si no pide ninguno.

    Público a propósito: ``sirius-despachar`` lo necesita para dar la parada con
    su motivo real -la credencial del motor no llega ahí, ADR-002- y remitir a
    la sesión interactiva. La causa por sí sola no bastaría para distinguirlo:
    ``permisos_o_credenciales_sensibles`` la comparte con la tercera causa, que
    es léxica y no tiene nada que ver con rutas.
    """
    return _prefijo_vetado_pedido(_normalizar(mensaje))


def _detectar_sensibilidad(normalizado: str) -> tuple[CausaEscalado, str] | None:
    for marcadores, causa in _SENSIBILIDAD:
        for marcador in marcadores:
            if _marcador_pedido(normalizado, marcador):
                return causa, f"el mensaje pide {marcador!r}: causa {causa.value}"
    # La quinta se consulta DESPUÉS de las cuatro, y el orden es la garantía de
    # que no las toca: ninguna entrada que antes daba una de ellas puede dar
    # otra cosa ahora, porque para llegar aquí las cuatro han dicho que no.
    prefijo = _prefijo_vetado_pedido(normalizado)
    if prefijo is not None:
        causa = CausaEscalado.PERMISOS_O_CREDENCIALES_SENSIBLES
        return causa, (
            f"el alcance declarado cae bajo {prefijo!r}, donde el motor no puede escribir "
            f"(ADR-002): causa {causa.value}"
        )
    return None


_PUNTUACION_DE_BORDE = re.compile(r"^[^\w]+|[^\w]+$")


def _primer_verbo(normalizado: str) -> str:
    """Primer token de ``normalizado``, sin la puntuación que lo rodea.

    El propio ``--help`` propone el formato con el verbo entre comillas
    angulares como ejemplo; sin quitar la puntuación de borde ese formato
    -y una coma tras el verbo, u otras comillas- salía sin reconocer (H-19).
    """
    if not normalizado:
        return ""
    primer_token = normalizado.split(" ", 1)[0]
    return _PUNTUACION_DE_BORDE.sub("", primer_token)


def _construir_datos_trabajo(
    mensaje: str, clase: WorkItemClass | None, limite_presupuesto: float
) -> DatosNuevoTrabajo:
    clase_efectiva = clase if clase is not None else WorkItemClass.CONSULTA_LARGA
    return DatosNuevoTrabajo(
        objetivo=mensaje.strip(),
        entregable=_ALCANCE_POR_CLASE[clase_efectiva],
        criterio_terminado=_CRITERIO_POR_CLASE[clase_efectiva],
        clase=clase_efectiva,
        limites={"presupuesto": {"limite": limite_presupuesto}},
        contexto_origen=("sesion-cli",),
    )


def interpretar_intencion_v0(
    mensaje: str, *, limite_presupuesto: float = PRESUPUESTO_POR_DEFECTO
) -> IntentSignal:
    """Clasificar ``mensaje`` en una :class:`IntentSignal`. Determinista y sin red."""
    normalizado = _normalizar(mensaje)

    if not normalizado or normalizado in _MARCADORES_SALUDO:
        return IntentSignal(tipo=TipoIntencion.CONVERSAR, mensaje_original=mensaje)

    verbo = _primer_verbo(normalizado)
    clase = _VERBO_A_CLASE.get(verbo)

    # La sensibilidad se comprueba ANTES que cualquier otra clasificación
    # -incluida la de marcadores de pasado- por decisión del propietario
    # (#324): fail-closed, que avise siempre aunque a veces avise de más,
    # nunca que una orden sensible se escape por otra rama (H-19). Una frase
    # que PIDE una operación sensible ES una orden aunque su primer verbo no
    # esté en la tabla reconocida (p. ej. "borra la base de producción"): la
    # evidencia léxica de sensibilidad basta por sí sola. Lo que ya no basta
    # es que el marcador APAREZCA: si va negado, la frase lo prohíbe en vez de
    # pedirlo, y prohibir una operación no es pedirla (ADR-184).
    sensibilidad = _detectar_sensibilidad(normalizado)
    if sensibilidad is not None:
        causa, motivo = sensibilidad
        datos_trabajo = _construir_datos_trabajo(mensaje, clase, limite_presupuesto)
        return IntentSignal(
            tipo=TipoIntencion.SENSIBLE_O_MATERIAL,
            mensaje_original=mensaje,
            datos_trabajo=datos_trabajo,
            causa_sensibilidad=causa,
            motivo_sensibilidad=motivo,
        )

    # Un primer verbo reconocido hace inequívoca la orden por sí solo, así que
    # se decide ANTES que los marcadores de pasado/exploración: si no, una
    # orden legítima sobre la situación actual de un módulo ("audita el
    # estado de las pruebas") se confunde con una consulta sobre esa misma
    # situación en el pasado, porque el marcador aparece de verdad en el
    # texto -no por una colisión de subcadena que la frontera de palabra
    # pueda resolver- (H-19, fallo b). Es la misma familia de raíz que la
    # sensibilidad: el orden de las comprobaciones, no solo la comparación.
    es_orden_por_verbo = clase is not None or verbo in _VERBOS_IMPERATIVOS_SIN_CLASE
    if es_orden_por_verbo:
        datos_trabajo = _construir_datos_trabajo(mensaje, clase, limite_presupuesto)
        return IntentSignal(
            tipo=TipoIntencion.ORDEN_INEQUIVOCA,
            mensaje_original=mensaje,
            datos_trabajo=datos_trabajo,
        )

    if any(_marcador_presente(normalizado, marcador) for marcador in _MARCADORES_PASADO):
        return IntentSignal(
            tipo=TipoIntencion.CONSULTAR_PASADO, mensaje_original=mensaje, consulta=mensaje
        )

    if any(_marcador_presente(normalizado, marcador) for marcador in _MARCADORES_EXPLORACION):
        return IntentSignal(tipo=TipoIntencion.EXPLORAR, mensaje_original=mensaje)

    if normalizado.endswith("?"):
        return IntentSignal(tipo=TipoIntencion.EXPLORAR, mensaje_original=mensaje)

    return IntentSignal(
        tipo=TipoIntencion.AMBIGUA,
        mensaje_original=mensaje,
        pregunta_aclaratoria=(
            "¿Qué debe existir al terminar, y qué comprobación lo dará por hecho?"
        ),
    )
