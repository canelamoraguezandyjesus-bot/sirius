"""Las marcas de una grabación, en un archivo de texto junto al vídeo.

Sin esto, decir «marca esto como el primer led» y oír *«Marcado. Ya lo
encontrarás luego»* era una promesa que no se cumplía: la marca no llegaba a
ningún sitio. Sirius diciendo algo que no es verdad es peor que Sirius sin
marcas.

El archivo se llama como el vídeo y vive en su misma carpeta —``toma-3.mp4``
deja ``toma-3.marcas.txt``—, así que al ir a montar se abre al lado sin buscar
nada y sin abrir Sirius.

**Nada se pierde si algo falla.** Mientras se graba, las marcas se van
escribiendo en un archivo provisional dentro de la carpeta de Sirius. Al parar,
ese archivo se convierte en el definitivo junto al vídeo. Si no se llega a
saber dónde quedó el vídeo —o si no se puede escribir en su carpeta—, el
provisional se queda con la fecha en el nombre en vez de borrarse.

Solo texto corto: etiqueta y minuto. Ni vídeo, ni audio, ni transcripciones,
que #127 prohíbe expresamente.
"""

from __future__ import annotations

from pathlib import Path

from sirius.infrastructure.logging import get_logger
from sirius.ports.clock import Clock

_logger = get_logger(__name__)

SUFIJO_MARCAS = ".marcas.txt"
ARCHIVO_EN_CURSO = "marcas-en-curso.txt"
ARCHIVO_DIARIO = "diario-captura.txt"

_CABECERA = "MARCAS DE LA GRABACIÓN"


def formatear_tiempo(segundos: float) -> str:
    """``02:31`` para tomas cortas, ``1:04:12`` cuando pasa de la hora."""
    total = max(0, int(segundos))
    horas, resto = divmod(total, 3600)
    minutos, segundos_restantes = divmod(resto, 60)
    if horas:
        return f"{horas}:{minutos:02d}:{segundos_restantes:02d}"
    return f"{minutos:02d}:{segundos_restantes:02d}"


class FileCaptureJournal:
    """Diario de captura en archivos de texto, junto al vídeo y en local."""

    def __init__(self, directorio_de_trabajo: Path, clock: Clock) -> None:
        self._directorio = directorio_de_trabajo
        self._clock = clock
        self._marcas: list[tuple[str, float]] = []

    # --- Puerto ----------------------------------------------------------

    def begin_take(self) -> None:
        self._marcas = []
        self._escribir_en_curso()

    def record_mark(self, label: str, elapsed_seconds: float) -> None:
        self._marcas.append((label, elapsed_seconds))
        self._escribir_en_curso()

    def end_take(self, output_path: str | None) -> None:
        """Deja las marcas junto al vídeo y retira el provisional.

        Sin marcas no se deja ningún archivo: un ``.txt`` vacío al lado de cada
        vídeo es ruido, y hace dudar de si se marcó algo y se perdió.
        """
        marcas, self._marcas = self._marcas, []
        provisional = self._directorio / ARCHIVO_EN_CURSO
        if not marcas:
            self._borrar(provisional)
            return

        video = Path(output_path) if output_path else None
        destino = self._destino_para(video)
        if (
            destino is not None
            and video is not None
            and self._escribir(destino, self._contenido(marcas, video))
        ):
            self._borrar(provisional)
            _logger.info("Marcas de la grabación guardadas junto al vídeo")
            return

        # No se pudo dejar junto al vídeo: el provisional se queda, con fecha,
        # antes que perder lo que el usuario marcó mientras grababa.
        self._conservar(provisional, marcas)

    def record(self, command: str, result: str, detail: str = "") -> None:
        """Una línea por orden, en un diario local. Nunca contenido grabado."""
        momento = self._clock.utc_now().isoformat(timespec="seconds")
        linea = f"{momento}\t{command}\t{result}\t{detail}".rstrip("\t")
        self._anexar(self._directorio / ARCHIVO_DIARIO, f"{linea}\n")

    # --- Interior --------------------------------------------------------

    def _destino_para(self, video: Path | None) -> Path | None:
        if video is None or not video.name:
            return None
        return video.with_name(f"{video.stem}{SUFIJO_MARCAS}")

    def _contenido(self, marcas: list[tuple[str, float]], video: Path) -> str:
        # Con extensión y todo: es el nombre que se busca en la carpeta al ir
        # a montar, y medio nombre obliga a adivinar cuál de los archivos es.
        lineas = [_CABECERA, f"Vídeo: {video.name}", ""]
        lineas += [f"{formatear_tiempo(segundos)}\t{etiqueta}" for etiqueta, segundos in marcas]
        return "\n".join(lineas) + "\n"

    def _escribir_en_curso(self) -> None:
        cuerpo = [_CABECERA, "Grabación en curso.", ""]
        cuerpo += [f"{formatear_tiempo(s)}\t{etiqueta}" for etiqueta, s in self._marcas]
        self._escribir(self._directorio / ARCHIVO_EN_CURSO, "\n".join(cuerpo) + "\n")

    def _conservar(self, provisional: Path, marcas: list[tuple[str, float]]) -> None:
        sello = self._clock.utc_now().strftime("%Y-%m-%d-%H%M%S")
        guardado = self._directorio / f"marcas-{sello}.txt"
        cuerpo = [_CABECERA, "Sin saber a qué vídeo pertenecen.", ""]
        cuerpo += [f"{formatear_tiempo(s)}\t{etiqueta}" for etiqueta, s in marcas]
        if self._escribir(guardado, "\n".join(cuerpo) + "\n"):
            self._borrar(provisional)
            _logger.warning("Marcas guardadas sin vídeo asociado: %s", guardado.name)

    def _escribir(self, destino: Path, contenido: str) -> bool:
        """Escribe y dice si pudo. **Nunca lanza**: se está grabando."""
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(contenido, encoding="utf-8")
        except OSError:
            _logger.warning("No se pudo escribir %s", destino.name)
            return False
        return True

    def _anexar(self, destino: Path, linea: str) -> None:
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            with destino.open("a", encoding="utf-8") as archivo:
                archivo.write(linea)
        except OSError:
            _logger.warning("No se pudo anotar en el diario de captura")

    def _borrar(self, archivo: Path) -> None:
        try:
            archivo.unlink(missing_ok=True)
        except OSError:
            _logger.warning("No se pudo retirar %s", archivo.name)


def build_file_capture_journal(directorio_de_trabajo: Path, clock: Clock) -> FileCaptureJournal:
    return FileCaptureJournal(directorio_de_trabajo, clock)


__all__ = [
    "ARCHIVO_DIARIO",
    "ARCHIVO_EN_CURSO",
    "SUFIJO_MARCAS",
    "FileCaptureJournal",
    "build_file_capture_journal",
    "formatear_tiempo",
]
