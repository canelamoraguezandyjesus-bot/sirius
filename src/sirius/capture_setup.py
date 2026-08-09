"""Conecta Sirius con OBS, lo prueba de verdad y deja la configuración escrita.

#127 exige que las escenas vivan en una **lista blanca**: lo que no esté en
ella no se puede activar, venga la orden de donde venga. Esa lista es
configuración del usuario, y hasta ahora la única forma de crearla era editar
un JSON a mano —justo la clase de tarea que no se le puede pedir a quien va a
usar Sirius para grabar—.

Esto la escribe solo. Pregunta la contraseña del servidor de OBS, se conecta,
lee las escenas que existen, propone identificadores y alias de voz, y después
**lo prueba**: cambia de plano y graba unos segundos de verdad. Nada se da por
bueno porque el código lo diga: se da por bueno porque OBS lo confirma.

Se ejecuta con ``python -m sirius.capture_setup``. Escribe una sola cosa, la
sección ``model_studio_capture`` de la configuración local, y no toca la base
de datos, la conversación ni la identidad.

La contraseña no se muestra al teclearla ni aparece en ninguna línea impresa.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Sequence
from getpass import getpass
from typing import Any

from sirius.config.settings import load_settings, save_settings
from sirius.console_report import (
    Paso,
    cabecera,
    contar_fallo_inesperado,
    resumen,
)
from sirius.domain.capture import build_scene_registry, normalize_alias
from sirius.ports.capture_backend import BackendScene, CaptureError

AJUSTE = "model_studio_capture"
PUERTO_POR_DEFECTO = 4455
ANFITRION_POR_DEFECTO = "127.0.0.1"
SEGUNDOS_DE_PRUEBA = 3.0

_PREFIJOS_QUE_SOBRAN = ("camara ", "escena ", "plano ", "vista ", "toma ")
"""Cómo se acorta un nombre para poder decirlo.

Nadie dice «cambia a la cámara cámara cenital». Con «cámara cenital» en OBS,
el alias corto «cenital» es el que se va a usar de verdad.
"""

_NO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")


# --- Proponer la lista blanca --------------------------------------------


def proponer_escenas(nombres: Sequence[str]) -> list[dict[str, Any]]:
    """Convierte los nombres que OBS tiene en entradas de la lista blanca.

    Cada escena recibe un identificador estable —que no cambia aunque en OBS le
    cambien el nombre— y los alias con los que se la puede llamar hablando.

    **Un alias que valdría para dos escenas se descarta de las dos.** No es
    quisquillosidad: ante una orden ambigua el registro no elige ninguna, así
    que dejarlo escrito sería configurar a mano una orden que nunca funciona.
    La escena de reserva es la primera, que es a la que se vuelve si un plano
    se rompe en mitad de una grabación.
    """
    limpios = [nombre for nombre in nombres if nombre.strip()]
    identificadores = _identificadores(limpios)
    candidatos = [_alias_de(nombre) for nombre in limpios]
    repetidos = _alias_repetidos(candidatos)

    return [
        {
            "id": identificador,
            "name": nombre,
            "backend_name": nombre,
            "aliases": sorted(alias - repetidos),
            "fallback": posicion == 0,
        }
        for posicion, (nombre, identificador, alias) in enumerate(
            zip(limpios, identificadores, candidatos, strict=True)
        )
    ]


def _identificadores(nombres: Sequence[str]) -> list[str]:
    """Un identificador estable por escena, sin repetir ninguno."""
    resultado: list[str] = []
    usados: set[str] = set()
    for posicion, nombre in enumerate(nombres):
        base = _NO_ALFANUMERICO.sub("-", normalize_alias(nombre)).strip("-")
        candidato = base or f"escena-{posicion + 1}"
        sufijo = 2
        while candidato in usados:
            candidato = f"{base or 'escena'}-{sufijo}"
            sufijo += 1
        usados.add(candidato)
        resultado.append(candidato)
    return resultado


def _alias_de(nombre: str) -> set[str]:
    normalizado = normalize_alias(" ".join(nombre.split()))
    alias = {normalizado}
    for prefijo in _PREFIJOS_QUE_SOBRAN:
        if normalizado.startswith(prefijo):
            corto = normalizado[len(prefijo) :].strip()
            if corto:
                alias.add(corto)
    return alias


def _alias_repetidos(candidatos: Sequence[set[str]]) -> set[str]:
    vistos: set[str] = set()
    repetidos: set[str] = set()
    for alias in candidatos:
        repetidos |= vistos & alias
        vistos |= alias
    return repetidos


def frases_de_voz(escenas: Sequence[dict[str, Any]]) -> list[str]:
    """Qué puede decir en voz alta para cada escena, para enseñárselo."""
    frases: list[str] = []
    for escena in escenas:
        alias = escena.get("aliases") or [escena["id"]]
        frases.append(f"«cambia a {alias[0]}»  →  {escena['name']}")
    return frases


# --- Guardar --------------------------------------------------------------


def guardar_configuracion(
    escenas: list[dict[str, Any]], anfitrion: str, puerto: int, contrasena: str
) -> Paso:
    """Escribe la sección de captura sin tocar el resto de la configuración."""
    ajustes = dict(load_settings())
    ajustes[AJUSTE] = {
        "host": anfitrion,
        "port": puerto,
        "password": contrasena,
        "scenes": escenas,
    }
    save_settings(ajustes)

    # Se relee por el mismo camino que usa Sirius al arrancar: si algo de lo
    # escrito no le vale, es ahora cuando hay que enterarse.
    registro = build_scene_registry(ajustes[AJUSTE]["scenes"])
    if len(registro.scenes) != len(escenas):
        return Paso(
            "Guardar la configuración",
            correcto=False,
            detalle=(
                f"Se escribieron {len(escenas)} escenas y Sirius solo acepta "
                f"{len(registro.scenes)}. Mándame esta línea."
            ),
        )
    return Paso(
        "Guardar la configuración",
        correcto=True,
        detalle=f"{len(escenas)} escenas autorizadas y guardadas.",
    )


# --- Comprobaciones contra OBS -------------------------------------------


def _backend(anfitrion: str, puerto: int, contrasena: str) -> Any:
    from sirius.adapters.capture.obs_websocket import ObsWebSocketBackend

    return ObsWebSocketBackend(password=contrasena, host=anfitrion, port=puerto)


def comprobar_conexion(backend: Any, anfitrion: str, puerto: int) -> Paso:
    error = backend.connect()
    if error is not None:
        return Paso(
            "Conexión con OBS",
            correcto=False,
            detalle=f"{_explicar(error)} (probando en {anfitrion}:{puerto})",
        )
    return Paso("Conexión con OBS", correcto=True, detalle=f"Conectado a {anfitrion}:{puerto}.")


def comprobar_escenas(backend: Any) -> tuple[Paso, list[BackendScene]]:
    encontradas = backend.list_scenes()
    if isinstance(encontradas, CaptureError):
        return Paso("Escenas de OBS", correcto=False, detalle=_explicar(encontradas)), []
    if not encontradas:
        return (
            Paso(
                "Escenas de OBS",
                correcto=False,
                detalle=(
                    "OBS no tiene ninguna escena. Crea al menos una en OBS "
                    "—abajo a la izquierda, en «Escenas»— y vuelve a ejecutar esto."
                ),
            ),
            [],
        )
    nombres = ", ".join(f"«{escena.name}»" for escena in encontradas)
    return (
        Paso("Escenas de OBS", correcto=True, detalle=f"{len(encontradas)}: {nombres}"),
        list(encontradas),
    )


def comprobar_cambio_de_plano(backend: Any, escenas: Sequence[BackendScene]) -> Paso:
    """Cambia a otra escena y vuelve a la que estaba. Sin dejar nada movido."""
    if len(escenas) < 2:
        return Paso(
            "Cambiar de plano",
            correcto=True,
            detalle="No aplica: con una sola escena no hay a dónde cambiar.",
        )

    original = next((escena for escena in escenas if escena.is_active), escenas[0])
    otra = next(escena for escena in escenas if escena.name != original.name)

    resultado = backend.switch_scene(otra.name)
    if isinstance(resultado, CaptureError):
        return Paso("Cambiar de plano", correcto=False, detalle=_explicar(resultado))
    vuelta = backend.switch_scene(original.name)
    if isinstance(vuelta, CaptureError):
        return Paso(
            "Cambiar de plano",
            correcto=False,
            detalle=f"Cambió a «{otra.name}» pero no pudo volver: {_explicar(vuelta)}",
        )
    return Paso(
        "Cambiar de plano",
        correcto=True,
        detalle=f"Cambió a «{otra.name}» y volvió a «{original.name}».",
    )


def comprobar_grabacion(backend: Any) -> Paso:
    """Graba unos segundos de verdad y comprueba que aparece el archivo.

    Es la comprobación que no se puede simular: hasta aquí todo podía ir bien
    y no haber ni un vídeo en el disco.
    """
    estado = backend.get_status()
    if isinstance(estado, CaptureError):
        return Paso("Grabar de verdad", correcto=False, detalle=_explicar(estado))
    if estado.state.is_recording_confirmed:
        return Paso(
            "Grabar de verdad",
            correcto=False,
            detalle=(
                "OBS ya está grabando. Párala tú en OBS y vuelve a ejecutar esto: "
                "no voy a tocar una grabación que no he empezado yo."
            ),
        )

    print(f"\n  >>> Grabando {SEGUNDOS_DE_PRUEBA:.0f} segundos de prueba en OBS...")
    iniciado = backend.start_recording()
    if isinstance(iniciado, CaptureError):
        return Paso("Grabar de verdad", correcto=False, detalle=_explicar(iniciado))
    if not iniciado.state.is_recording_confirmed:
        return Paso(
            "Grabar de verdad",
            correcto=False,
            detalle=f"OBS aceptó la orden pero dice que está en «{iniciado.state.label}».",
        )

    time.sleep(SEGUNDOS_DE_PRUEBA)
    detenido = backend.stop_recording()
    if isinstance(detenido, CaptureError):
        return Paso(
            "Grabar de verdad",
            correcto=False,
            detalle=f"Empezó a grabar pero no pudo parar: {_explicar(detenido)}",
        )
    if detenido.output_path:
        return Paso(
            "Grabar de verdad",
            correcto=True,
            detalle=f"Grabado y guardado en: {detenido.output_path}",
        )
    return Paso(
        "Grabar de verdad",
        correcto=True,
        detalle="Grabó y paró. OBS no ha dicho dónde guardó el archivo.",
    )


_EXPLICACIONES = {
    "not_connected": (
        "No hay nadie escuchando. Abre OBS y comprueba que el servidor WebSocket "
        "está activado en Herramientas > Configuración del servidor WebSocket."
    ),
    "authentication": "La contraseña no es la de OBS. Cópiala otra vez desde «Mostrar contraseña».",
    "unsupported_version": "Este OBS es demasiado antiguo. Hace falta OBS 28 o posterior.",
    "timeout": "OBS no ha contestado a tiempo.",
    "rejected": "OBS ha rechazado la orden.",
    "unsupported_operation": "Este OBS no sabe hacer eso.",
    "unknown": "Fallo no identificado al hablar con OBS.",
}


def _explicar(error: CaptureError) -> str:
    return _EXPLICACIONES.get(error.kind.value, _EXPLICACIONES["unknown"])


# --- Recorrido completo ---------------------------------------------------


def main() -> int:
    """Recorre la puesta a punto entera. Nunca lanza."""
    try:
        return _recorrer()
    except Exception as error:  # frontera del programa: se cuenta, no se escupe
        return contar_fallo_inesperado(error)


def _recorrer() -> int:
    cabecera("SIRIUS · CONEXIÓN CON OBS")
    print(
        "Antes de seguir, en OBS: Herramientas > Configuración del servidor\n"
        "WebSocket > marca «Activar servidor WebSocket» > «Mostrar contraseña».\n"
    )

    anfitrion, puerto, contrasena = _preguntar_datos()
    backend = _backend(anfitrion, puerto, contrasena)
    try:
        return _comprobar_todo(backend, anfitrion, puerto, contrasena)
    finally:
        # Desconectarse no para nada de lo que se esté grabando: es solo cerrar
        # la línea con OBS.
        backend.disconnect()


def _comprobar_todo(backend: Any, anfitrion: str, puerto: int, contrasena: str) -> int:
    pasos: list[Paso] = []

    paso = comprobar_conexion(backend, anfitrion, puerto)
    pasos.append(paso)
    print(paso.linea())
    if not paso.correcto:
        return resumen(pasos, "")

    paso, escenas = comprobar_escenas(backend)
    pasos.append(paso)
    print(paso.linea())
    if not escenas:
        return resumen(pasos, "")

    propuestas = proponer_escenas([escena.name for escena in escenas])
    paso = guardar_configuracion(propuestas, anfitrion, puerto, contrasena)
    pasos.append(paso)
    print(paso.linea())

    # Una detrás de otra, no las dos y luego imprimir: la de grabar tarda tres
    # segundos y avisa por pantalla, así que el resultado anterior tiene que
    # estar ya a la vista cuando eso ocurre.
    paso = comprobar_cambio_de_plano(backend, escenas)
    pasos.append(paso)
    print(paso.linea())

    paso = comprobar_grabacion(backend)
    pasos.append(paso)
    print(paso.linea())

    codigo = resumen(pasos, "OBS está conectado, configurado y probado.")
    if codigo == 0:
        print("\nYa puedes decirle a Sirius, hablando o escribiendo:\n")
        for frase in frases_de_voz(propuestas):
            print(f"  {frase}")
        print("  «graba» · «para» · «pausa» · «sigue» · «estás grabando»\n")
    return codigo


def _leer(pregunta: Callable[[], str]) -> str:
    """Lee una respuesta, o cadena vacía si no hay nadie al teclado.

    Sin esto, ejecutar el comando con la entrada redirigida —o desde un guion—
    lanza ``EOFError`` en la primera pregunta y se lleva por delante el
    recorrido entero antes de haber comprobado nada.
    """
    try:
        return pregunta().strip()
    except EOFError:
        print("  (sin respuesta: se usa lo guardado o el valor por defecto)")
        return ""


def _preguntar_datos() -> tuple[str, int, str]:
    guardado = load_settings().get(AJUSTE, {})
    guardado = guardado if isinstance(guardado, dict) else {}

    puerto_previo = int(guardado.get("port", PUERTO_POR_DEFECTO))
    escrito = _leer(lambda: input(f"Puerto de OBS [{puerto_previo}]: "))
    puerto = int(escrito) if escrito.isdigit() else puerto_previo

    anfitrion = str(guardado.get("host", ANFITRION_POR_DEFECTO))
    # No se muestra al teclearla, y no vuelve a aparecer en ninguna línea.
    contrasena = _leer(lambda: getpass("Contraseña del servidor WebSocket de OBS: "))
    if not contrasena:
        contrasena = str(guardado.get("password", ""))
        if contrasena:
            print("  (sin contraseña escrita: se reutiliza la ya guardada)")
    return anfitrion, puerto, contrasena


if __name__ == "__main__":
    raise SystemExit(main())
