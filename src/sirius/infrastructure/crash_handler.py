"""Manejador global de excepciones no capturadas, a prueba de fallo recursivo.

Sirius no instalaba ninguno. Cuando una excepción escapaba del bucle de
eventos de Qt, quien informaba era el manejador por omisión de CPython, y en
el caso concreto de un ``RecursionError`` ese camino falla dos veces seguidas:

1. La excepción llega arriba con la pila prácticamente agotada.
2. Para informar hay que formatear la traza, y formatearla consume más pila,
   así que el propio manejador vuelve a chocar contra el mismo límite y lanza
   otro ``RecursionError``. CPython lo anuncia con ``Error in sys.excepthook``.
3. Al intentar escribir el aviso, si ``sys.stderr`` no es utilizable —lo normal
   en un ejecutable de Windows compilado sin consola, donde vale ``None``—
   CPython remata con ``lost sys.stderr``.

El resultado era el peor posible: la aplicación se cerraba sin dejar ni una
línea en el registro. Este manejador corrige las tres cosas:

- **No puede reentrar.** Un indicador impide que un fallo mientras se informa
  vuelva a entrar aquí; en ese caso se abandona en silencio en vez de recursar.
- **Se da margen de pila.** Antes de formatear sube temporalmente el límite de
  recursión, que es justo lo que le faltaba al manejador por omisión, y además
  recorta la traza a las últimas llamadas, que son las que interesan.
- **No depende de stderr.** ``stderr`` es solo una salida secundaria de mejor
  esfuerzo: se escribe únicamente si existe y es utilizable.

Contrato exacto — lo que este módulo garantiza y lo que no:

- **Después de ``configure_logging``**, el destino principal de un fallo no
  capturado es el registro rotatorio ``logs/application.log``.
- **Antes de configurar el registro** (la ventana entre el arranque del
  proceso y la resolución del directorio de datos), el logger de Sirius aún
  no tiene manejador de fichero: la persistencia NO está garantizada y solo
  queda el mejor esfuerzo sobre ``stderr``, si existe.
- Los fallos del propio logging y las reentradas se cortan deliberadamente
  para impedir una segunda recursión; en esos casos el informe puede
  perderse. Este manejador NO garantiza que todo fallo imaginable quede
  persistido: garantiza que informar de un fallo nunca tumba el proceso por
  segunda vez ni deja el doble error ``Error in sys.excepthook`` /
  ``lost sys.stderr``.

No oculta nada de lo que puede registrar. Tampoco sustituye al manejo de
errores de cada operación, que sigue siendo el camino normal; esto es la
última red antes de que el proceso muera.
"""

from __future__ import annotations

import contextlib
import sys
import threading
import traceback
from types import TracebackType

from sirius.infrastructure.logging import get_logger

__all__ = ["format_crash", "install_crash_handler"]

#: Margen de pila que se concede para poder formatear la traza de un
#: ``RecursionError`` sin volver a agotarla.
_RECURSION_HEADROOM = 500

#: Cuántos marcos FINALES de la traza se conservan (los más recientes, los
#: más cercanos al punto del fallo). ``traceback.format_exception`` con
#: límite positivo conserva los N primeros marcos —los más antiguos—, así
#: que hay que pasarlo en negativo; con el signo equivocado, una recursión
#: desbocada mostraría solo el arranque de la aplicación y ni un marco del
#: ciclo que la causó.
_MAX_TRACEBACK_FRAMES = 40

_reporting = threading.local()


def _is_reporting() -> bool:
    return bool(getattr(_reporting, "active", False))


def format_crash(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> str:
    """Formatea la traza sin poder agotar la pila por segunda vez.

    Conserva los últimos ``_MAX_TRACEBACK_FRAMES`` marcos —los más cercanos
    al fallo—, que en una recursión desbocada son los únicos que enseñan el
    ciclo. El límite se pasa en NEGATIVO: en positivo,
    ``traceback.format_exception`` conserva los primeros marcos (los más
    antiguos) y descarta justo la parte útil.
    """
    previous_limit = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(previous_limit + _RECURSION_HEADROOM)
        lines = traceback.format_exception(
            exc_type, exc_value, exc_traceback, limit=-_MAX_TRACEBACK_FRAMES
        )
        return "".join(lines)
    except Exception:
        # Último recurso: sin traza, pero con el tipo, que es lo que permite
        # saber qué pasó.
        return f"{exc_type.__name__}: no se pudo formatear la traza\n"
    finally:
        sys.setrecursionlimit(previous_limit)


def _write_to_stderr(text: str) -> None:
    """Escribe en stderr solo si de verdad se puede.

    En el ejecutable de Windows compilado sin consola ``sys.stderr`` es
    ``None``; intentarlo a ciegas es lo que acababa en ``lost sys.stderr``.
    """
    stream = getattr(sys, "stderr", None)
    if stream is None:
        return
    try:
        stream.write(text)
        stream.flush()
    except Exception:
        return


def _report(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
    *,
    origin: str,
) -> None:
    if _is_reporting():
        # Ya estábamos informando de otro fallo: seguir sería exactamente la
        # recursión que este módulo existe para impedir.
        return
    _reporting.active = True
    try:
        details = format_crash(exc_type, exc_value, exc_traceback)
        # Si el registro falla, todavía queda stderr; nunca al revés.
        with contextlib.suppress(Exception):
            get_logger(__name__).critical("Excepción no capturada (%s): %s", origin, details)
        _write_to_stderr(details)
    finally:
        _reporting.active = False


def install_crash_handler() -> None:
    """Instala el manejador para el hilo principal y para los hilos secundarios.

    Es idempotente: volver a llamarla deja el mismo manejador puesto.
    """

    def _excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        _report(exc_type, exc_value, exc_traceback, origin="hilo principal")

    def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is SystemExit:
            return
        _report(
            args.exc_type,
            args.exc_value if args.exc_value is not None else args.exc_type(),
            args.exc_traceback,
            origin=f"hilo {args.thread.name if args.thread else 'desconocido'}",
        )

    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook
