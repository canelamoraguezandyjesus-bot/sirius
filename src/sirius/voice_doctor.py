"""Prueba de voz paso a paso, con veredicto en castellano llano.

Existe porque diagnosticar el sonido a distancia, a base de pedirle a alguien
que copie líneas de consola, no funciona: cada intento cuesta una ronda entera
y la mitad de las veces lo que hace falta se ha quedado fuera del copiar y
pegar. Esto lo recorre todo de una vez —qué versión estás ejecutando, si hay
clave, si el proveedor devuelve audio, si el archivo está bien formado y si
suena por cada uno de los dos caminos— y dice en qué paso exacto se rompe.

Se ejecuta con ``uv run sirius-voz``. No toca la base de datos, no cambia
ninguna configuración y no deja nada instalado: crea un WAV temporal, lo
reproduce y lo borra. Lo único que gasta es una síntesis de una frase corta,
del orden de una milésima de euro.

No arregla nada a propósito. Es un termómetro: mide y lo dice.
"""

from __future__ import annotations

import platform
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

FRASE_DE_PRUEBA = "Uno, dos, tres. Si oyes esto, la voz funciona."
"""Corta a propósito: la prueba tiene que durar poco y costar menos."""

_SEPARADOR = "=" * 62

AUDIO_ILEGIBLE = OSError, wave.Error, EOFError
"""Un archivo cortado a medias lanza ``EOFError``, que no es un ``OSError``."""


@dataclass(frozen=True, slots=True)
class Paso:
    """El resultado de una comprobación, listo para imprimir y para copiar."""

    titulo: str
    correcto: bool
    detalle: str

    def linea(self) -> str:
        marca = "OK  " if self.correcto else "FALLA"
        return f"[{marca}] {self.titulo}\n        {self.detalle}"


# --- 1. Qué versión se está ejecutando -----------------------------------


def comprobar_version() -> Paso:
    """Si el código que corre incluye los arreglos del sonido.

    Se mira el código cargado, no el historial de git: da igual en qué rama
    creas que estás si lo que se ejecuta es otra cosa. Esta comprobación
    responde a la pregunta de verdad, que es «¿tengo los arreglos o no?».
    """
    from sirius.adapters.audio import openai_speech, qt_playback

    arreglos = {
        "reparación del encabezado WAV": hasattr(openai_speech, "repair_wav_sizes"),
        "reproducción en el hilo correcto": hasattr(qt_playback, "multimedia_is_available"),
        "reproductor de Windows": _hay_reproductor_de_windows(),
    }
    faltan = [nombre for nombre, presente in arreglos.items() if not presente]
    if faltan:
        return Paso(
            "Versión que estás ejecutando",
            correcto=False,
            detalle=(
                f"Falta: {', '.join(faltan)}. Estás ejecutando código antiguo. "
                "Cambia de rama y vuelve a probar antes de seguir."
            ),
        )
    return Paso(
        "Versión que estás ejecutando",
        correcto=True,
        detalle="Incluye los tres arreglos del sonido.",
    )


def _hay_reproductor_de_windows() -> bool:
    try:
        import sirius.adapters.audio.winsound_playback  # noqa: F401
    except ImportError:
        return False
    return True


# --- 2. Qué máquina es esta ----------------------------------------------


def comprobar_sistema() -> Paso:
    from sirius.composition_root import build_audio_playback

    elegido = type(build_audio_playback()).__name__
    nombres = {
        "WinsoundAudioPlayback": "el reproductor de Windows (winsound)",
        "QtAudioPlayback": "el reproductor de Qt (QtMultimedia)",
    }
    return Paso(
        "Sistema y reproductor elegido",
        correcto=True,
        detalle=(
            f"{platform.system()} {platform.release()} · Python "
            f"{platform.python_version()} · usará {nombres.get(elegido, elegido)}"
        ),
    )


# --- 3. ¿Hay clave? -------------------------------------------------------


def comprobar_clave() -> tuple[Paso, str]:
    """Devuelve el paso y la clave, o una cadena vacía si no hay."""
    from sirius.adapters.secrets.keyring_store import build_keyring_secret_store
    from sirius.config.llm_provider_settings import (
        LLMProviderConfigurationError,
        resolve_openai_api_key,
    )
    from sirius.ports.secrets import SecretStoreError

    clave_inaccesible = LLMProviderConfigurationError, SecretStoreError
    try:
        clave = resolve_openai_api_key(build_keyring_secret_store())
    except clave_inaccesible as error:
        return (
            Paso("Clave del proveedor", correcto=False, detalle=str(error)),
            "",
        )
    if not clave:
        return (
            Paso(
                "Clave del proveedor",
                correcto=False,
                detalle=(
                    "No hay ninguna clave guardada. Añádela en la pestaña "
                    "Configuración de Sirius y vuelve a ejecutar esto."
                ),
            ),
            "",
        )
    return (
        Paso("Clave del proveedor", correcto=True, detalle="Guardada y accesible."),
        clave,
    )


# --- 4. ¿El proveedor devuelve audio? ------------------------------------


def comprobar_sintesis(clave: str, directorio: Path) -> tuple[Paso, Path | None]:
    import openai

    from sirius.adapters.audio.openai_speech import DEFAULT_VOICE, OpenAISpeech
    from sirius.ports.text_to_speech import SpeechError, SpeechRequest

    adaptador = OpenAISpeech(openai.OpenAI(api_key=clave, max_retries=0), directorio)
    resultado = adaptador.synthesize(
        SpeechRequest(text=FRASE_DE_PRUEBA, voice=DEFAULT_VOICE, instructions="")
    )
    if isinstance(resultado, SpeechError):
        return (
            Paso(
                "Fabricar la voz",
                correcto=False,
                detalle=(
                    f"El proveedor no ha devuelto audio ({resultado.kind.value}). "
                    "Aquí no llega a haber sonido que reproducir."
                ),
            ),
            None,
        )
    tamano = resultado.audio_path.stat().st_size
    return (
        Paso(
            "Fabricar la voz",
            correcto=True,
            detalle=f"Recibido: {tamano:,} bytes con la voz «{DEFAULT_VOICE}».",
        ),
        resultado.audio_path,
    )


# --- 5. ¿El archivo está bien formado? -----------------------------------


def comprobar_archivo(audio: Path) -> Paso:
    """Que el WAV se pueda leer entero, que es lo que fallaba en Windows.

    Un encabezado con tamaños de relleno hace que el descodificador tire los
    paquetes —«Packet corrupt»— y no salga sonido por ninguna parte.
    """
    try:
        with wave.open(str(audio), "rb") as handle:
            canales = handle.getnchannels()
            frecuencia = handle.getframerate()
            fotogramas = handle.getnframes()
            handle.readframes(fotogramas)
    except AUDIO_ILEGIBLE as error:
        return Paso(
            "Estado del archivo de audio",
            correcto=False,
            detalle=f"El WAV no se puede leer entero: {error}",
        )

    segundos = fotogramas / frecuencia if frecuencia else 0.0
    en_disco = audio.stat().st_size
    esperado = 44 + fotogramas * canales * 2
    coherente = abs(en_disco - esperado) <= 4096
    return Paso(
        "Estado del archivo de audio",
        correcto=coherente,
        detalle=(
            f"{frecuencia} Hz, {canales} canal(es), {segundos:.1f} s. "
            + (
                "El encabezado concuerda con lo que hay en disco."
                if coherente
                else f"El encabezado dice {esperado:,} bytes y en disco hay {en_disco:,}: "
                "por eso el descodificador descarta el sonido."
            )
        ),
    )


# --- 6 y 7. ¿Suena? -------------------------------------------------------


def probar_con_windows(audio: Path) -> Paso:
    from sirius.adapters.audio.winsound_playback import (
        audio_seconds,
        play_wav_file,
        stop_all_sounds,
        winsound_is_available,
    )

    if not winsound_is_available():
        return Paso(
            "Sonar por el reproductor de Windows",
            correcto=True,
            detalle="No aplica: este sistema no es Windows.",
        )

    print("\n  >>> Escucha. Reproduciendo por el reproductor de Windows...")
    try:
        play_wav_file(str(audio))
    except RuntimeError as error:
        return Paso(
            "Sonar por el reproductor de Windows",
            correcto=False,
            detalle=f"Windows ha rechazado el archivo: {error}",
        )
    _esperar(audio_seconds(audio) + 0.5)
    stop_all_sounds()
    return Paso(
        "Sonar por el reproductor de Windows",
        correcto=_preguntar("  ¿Has oído la frase por los altavoces?"),
        detalle="Respuesta del usuario.",
    )


def probar_con_qt(audio: Path) -> Paso:
    from PySide6.QtCore import QEventLoop, QTimer

    from sirius.adapters.audio.qt_playback import QtAudioPlayback, multimedia_is_available

    if not multimedia_is_available():
        return Paso(
            "Sonar por el reproductor de Qt",
            correcto=False,
            detalle="QtMultimedia no está disponible en este sistema.",
        )

    print("\n  >>> Escucha otra vez. Reproduciendo por el reproductor de Qt...")
    reproductor = QtAudioPlayback()
    bucle = QEventLoop()
    error = reproductor.play(audio, bucle.quit)
    if error is not None:
        return Paso(
            "Sonar por el reproductor de Qt",
            correcto=False,
            detalle=f"No ha llegado a reproducir: {error.message}",
        )
    # Tope por si el final no llega nunca, que es justo lo que pasaba antes.
    QTimer.singleShot(15_000, bucle.quit)
    bucle.exec()
    reproductor.stop()
    return Paso(
        "Sonar por el reproductor de Qt",
        correcto=_preguntar("  ¿Has oído la frase por los altavoces?"),
        detalle="Respuesta del usuario.",
    )


def _esperar(segundos: float) -> None:
    """Espera sin congelar Qt, que puede estar reproduciendo por debajo."""
    from PySide6.QtCore import QEventLoop, QTimer

    bucle = QEventLoop()
    QTimer.singleShot(int(segundos * 1000), bucle.quit)
    bucle.exec()


def _preguntar(pregunta: str) -> bool:
    """Pregunta y da por no oído si nadie contesta.

    Sin la salvaguarda, ejecutar esto con la entrada redirigida lanzaría
    ``EOFError`` y se llevaría por delante el resumen, que es lo único que de
    verdad importa de todo el recorrido.
    """
    try:
        respuesta = input(f"{pregunta} (s/n): ").strip().lower()
    except EOFError:
        print("  (sin respuesta: se anota como no oído)")
        return False
    return respuesta.startswith("s")


# --- Recorrido completo ---------------------------------------------------


def main() -> int:
    """Recorre la prueba entera. Nunca lanza: un fallo también es un resultado."""
    try:
        return _recorrer()
    except Exception as error:  # frontera del programa: se cuenta, no se escupe
        print(
            f"\n[FALLA] La prueba se ha interrumpido: {type(error).__name__}: {error}\n"
            "Copia esta línea y mándamela: dice exactamente dónde se paró."
        )
        return 1


def _recorrer() -> int:
    from PySide6.QtWidgets import QApplication

    # Hace falta una aplicación de Qt para los temporizadores y el sonido de
    # Qt. No se abre ninguna ventana.
    aplicacion = QApplication.instance() or QApplication(sys.argv)
    del aplicacion

    print(f"\n{_SEPARADOR}\nSIRIUS · PRUEBA DE VOZ\n{_SEPARADOR}\n")

    pasos: list[Paso] = [comprobar_version(), comprobar_sistema()]
    for paso in pasos:
        print(paso.linea())

    paso_clave, clave = comprobar_clave()
    pasos.append(paso_clave)
    print(paso_clave.linea())
    if not clave:
        return _resumen(pasos)

    with TemporaryDirectory(prefix="sirius-prueba-voz-") as carpeta:
        print("\n  ... pidiendo la voz al proveedor, esto tarda unos segundos ...\n")
        paso_sintesis, audio = comprobar_sintesis(clave, Path(carpeta))
        pasos.append(paso_sintesis)
        print(paso_sintesis.linea())
        if audio is None:
            return _resumen(pasos)

        paso_archivo = comprobar_archivo(audio)
        pasos.append(paso_archivo)
        print(paso_archivo.linea())

        for prueba in (probar_con_windows, probar_con_qt):
            paso = prueba(audio)
            pasos.append(paso)
            print(paso.linea())

    return _resumen(pasos)


def _resumen(pasos: list[Paso]) -> int:
    print(f"\n{_SEPARADOR}\nRESUMEN · copia esto entero y mándamelo\n{_SEPARADOR}")
    for paso in pasos:
        marca = "OK  " if paso.correcto else "FALLA"
        print(f"[{marca}] {paso.titulo} — {paso.detalle}")

    fallos = [paso for paso in pasos if not paso.correcto]
    if not fallos:
        print("\nTodo correcto: la voz funciona por los dos caminos.")
        return 0
    print(f"\nPrimer punto que falla: {fallos[0].titulo}.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
