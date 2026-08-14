"""Indicación efímera de extensión para las respuestas dentro de Model Studio.

#126 la pide con estas palabras: *«Instrucción efímera al modelo para respuestas
normalmente de una a cuatro frases, sin alterar la identidad canónica»*. Y §4.1
de ``SIRIUS-MODEL-STUDIO-UI-001`` la razona: grabando, una explicación de tres
párrafos es un vídeo que nadie termina de ver.

**Efímera** quiere decir tres cosas, y las tres importan:

- no se guarda en la memoria ni en el historial;
- no crea una versión nueva de la identidad;
- solo acompaña a los mensajes enviados desde Model Studio. En la interfaz
  técnica Sirius responde con la extensión que el tema pida, como siempre.

Es una indicación de **extensión**, no de carácter. No toca el criterio, ni la
honestidad, ni los límites, ni el humor: la identidad sigue viniendo entera del
perfil versionado.
"""

from __future__ import annotations

MODEL_STUDIO_BRIEF = (
    "Contexto de esta respuesta: la conversación ocurre en Model Studio, la "
    "superficie audiovisual que se está grabando en vídeo.\n"
    "Responde normalmente en una a cuatro frases. Si el asunto no cabe ahí, di "
    "lo esencial en esas frases y deja claro que el detalle queda escrito en "
    "pantalla, en vez de recitarlo entero.\n"
    "Esto afecta únicamente a la extensión de esta respuesta. No cambia tu "
    "identidad, tu criterio, tu honestidad ni tus límites, y no es motivo para "
    "omitir un riesgo, una incertidumbre o una corrección que haya que decir."
)
"""Lo último es lo que evita el efecto secundario peligroso de pedir brevedad:
que el modelo se calle un riesgo por no alargarse."""
