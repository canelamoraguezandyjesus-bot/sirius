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


def _detectar_sensibilidad(normalizado: str) -> tuple[CausaEscalado, str] | None:
    for marcadores, causa in _SENSIBILIDAD:
        for marcador in marcadores:
            if marcador in normalizado:
                return causa, f"el mensaje contiene {marcador!r}: causa {causa.value}"
    return None


def _primer_verbo(normalizado: str) -> str:
    return normalizado.split(" ", 1)[0] if normalizado else ""


def interpretar_intencion_v0(
    mensaje: str, *, limite_presupuesto: float = PRESUPUESTO_POR_DEFECTO
) -> IntentSignal:
    """Clasificar ``mensaje`` en una :class:`IntentSignal`. Determinista y sin red."""
    normalizado = _normalizar(mensaje)

    if not normalizado or normalizado in _MARCADORES_SALUDO:
        return IntentSignal(tipo=TipoIntencion.CONVERSAR, mensaje_original=mensaje)

    if any(marcador in normalizado for marcador in _MARCADORES_PASADO):
        return IntentSignal(
            tipo=TipoIntencion.CONSULTAR_PASADO, mensaje_original=mensaje, consulta=mensaje
        )

    if any(marcador in normalizado for marcador in _MARCADORES_EXPLORACION):
        return IntentSignal(tipo=TipoIntencion.EXPLORAR, mensaje_original=mensaje)

    if normalizado.endswith("?"):
        return IntentSignal(tipo=TipoIntencion.EXPLORAR, mensaje_original=mensaje)

    verbo = _primer_verbo(normalizado)
    clase = _VERBO_A_CLASE.get(verbo)
    sensibilidad = _detectar_sensibilidad(normalizado)
    # Una frase con un marcador de sensibilidad ES una orden, aunque su
    # primer verbo no esté en la tabla reconocida (p. ej. "borra la base de
    # producción"): la evidencia léxica de sensibilidad basta por sí sola,
    # y es preferible sobre-marcar como sensible que dejarlo pasar como
    # AMBIGUA sin más (fail-closed, mismo criterio que el egress de A4).
    es_orden = (
        clase is not None or verbo in _VERBOS_IMPERATIVOS_SIN_CLASE or sensibilidad is not None
    )
    if not es_orden:
        return IntentSignal(
            tipo=TipoIntencion.AMBIGUA,
            mensaje_original=mensaje,
            pregunta_aclaratoria=(
                "¿Qué debe existir al terminar, y qué comprobación lo dará por hecho?"
            ),
        )

    datos_trabajo = DatosNuevoTrabajo(
        objetivo=mensaje.strip(),
        entregable=f"lo que pide la orden: {mensaje.strip()}",
        criterio_terminado="el entregable descrito existe y satisface la orden original",
        clase=clase if clase is not None else WorkItemClass.CONSULTA_LARGA,
        limites={"presupuesto": {"limite": limite_presupuesto}},
        contexto_origen=("sesion-cli",),
    )

    if sensibilidad is not None:
        causa, motivo = sensibilidad
        return IntentSignal(
            tipo=TipoIntencion.SENSIBLE_O_MATERIAL,
            mensaje_original=mensaje,
            datos_trabajo=datos_trabajo,
            causa_sensibilidad=causa,
            motivo_sensibilidad=motivo,
        )

    return IntentSignal(
        tipo=TipoIntencion.ORDEN_INEQUIVOCA, mensaje_original=mensaje, datos_trabajo=datos_trabajo
    )
