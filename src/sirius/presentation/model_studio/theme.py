"""Paleta y medidas de Model Studio.

Un único sitio donde vive el aspecto de la superficie, para que corregir un
color o un tamaño no obligue a tocar cinco archivos. Responde al criterio 12 de
``SIRIUS-MODEL-STUDIO-UI-001``: corregir un componente no debe rediseñar el
resto de la interfaz aprobada.

Paleta limitada a azules sobre negro (§3.1 de la especificación). El rojo
aparece exclusivamente en el indicador de grabación; no se usa para nada más.
"""

from __future__ import annotations

from typing import Final

# --- Fondo y texto -------------------------------------------------------

BACKGROUND: Final = "#000000"
"""Fondo completamente negro (§3.1). El chat comparte fondo con la presencia."""

SURFACE_RAISED: Final = "#0a0d14"
"""Elevación mínima para barras superior e inferior: separa sin dibujar líneas."""

HAIRLINE: Final = "#161c28"
"""Separador apenas perceptible entre zonas."""

TEXT_PRIMARY: Final = "#e9eff8"
TEXT_SECONDARY: Final = "#9aa7bb"
TEXT_MUTED: Final = "#5d6879"

ACCENT: Final = "#4c9bff"
"""Azul de acento: etiqueta SIRIUS, foco y estados activos."""

RECORDING: Final = "#ff3b30"
"""Rojo del indicador de grabación. Solo lo enciende ``GRABANDO`` confirmado."""

ERROR_TEXT: Final = "#ff8a80"

# --- Presencia de partículas ---------------------------------------------

PARTICLE_FAR: Final = "#16305c"
PARTICLE_MID: Final = "#2f6fd0"
PARTICLE_NEAR: Final = "#8cc4ff"
"""Tres azules: oscuro, medio y claro (§3.1). Sin ningún otro tono."""

# --- Tipografía ----------------------------------------------------------
#
# El usuario eligió el 7 de agosto de 2026 un cuerpo algo mayor que el normal
# de escritorio, pensado para que la conversación se lea al ver el vídeo en un
# móvil. Sigue siendo escala de chat de escritorio: §4 descarta los textos
# gigantes.

FONT_MESSAGE_PT: Final = 12
"""Cuerpo del mensaje."""

FONT_SPEAKER_PT: Final = 8
"""Etiquetas TÚ y SIRIUS: pequeñas, espaciadas y discretas."""

FONT_INPUT_PT: Final = 12
FONT_TOPBAR_TITLE_PT: Final = 11
FONT_TOPBAR_META_PT: Final = 9
FONT_STATE_PT: Final = 8
FONT_ASIDE_TITLE_PT: Final = 7
FONT_ASIDE_VALUE_PT: Final = 10

# --- Medidas -------------------------------------------------------------

LEFT_COLUMN_STRETCH: Final = 27
RIGHT_COLUMN_STRETCH: Final = 73
"""Reparto 27/73, dentro del 25-30 % / 70-75 % que fija la seccion 2.1."""

TOP_BAR_HEIGHT: Final = 54
BOTTOM_BAR_HEIGHT: Final = 58
ICON_BUTTON_SIZE: Final = 38
ICON_PIXELS: Final = 20

INPUT_MINIMUM_HEIGHT: Final = 46
INPUT_MAXIMUM_HEIGHT: Final = 168
"""La caja crece hasta esta altura y a partir de ahí se desplaza por dentro,
sin invadir el historial (§5)."""

CONTENT_MARGIN: Final = 22
MESSAGE_SPACING: Final = 18

MESSAGE_MAXIMUM_WIDTH: Final = 900
"""Ancho máximo de un turno de conversación.

Sin tope, a 1920 px cada línea mediría casi 1400 px y el ojo pierde el
principio del renglón al saltar de línea. Es lo que exige de verdad
"conservará legibilidad en 1080p" (seccion 4): no basta con que el texto quepa.
"""
