"""La fuente que se inventa las palabras: un modelo, viendo **solo** la consulta.

ESTO ES LO QUE LA TABLA PROMETIA Y NO ERA
=========================================

El artefacto de la ampliacion escrita a mano declara su propia limitacion sin
adornos: «quien las escribio ya habia visto las respuestas esperadas de rondas
anteriores; no es una ampliacion ciega». Y anade la hipotesis que quedaba por
comprobar: «en produccion las escribiria el modelo de Sirius, que no ve el
banco».

Este modulo es esa hipotesis, hecha ejecutable. Si un modelo que **solo ve el
texto de la pregunta** produce palabras que recuperan las mismas cuatro
omisiones, la tabla se puede tirar y la ampliacion deja de ser un truco de
laboratorio. Si no las produce, la diferencia entre lo que consigue y el 26/47
de la tabla mide exactamente cuanto de aquel resultado venia de que yo ya sabia
la respuesta.

QUE VE Y QUE NO VE
==================

Ve: el texto de la consulta. Nada mas.

No ve: el canon, el corpus, los identificadores, la criticidad, las respuestas
esperadas, los resultados de ninguna corrida anterior, ni las palabras que yo
escribi a mano. No se le dice que existe un banco, ni cuantos casos hay, ni que
se le va a puntuar.

Esa frontera no es una promesa del docstring: el unico argumento que entra en
la peticion es ``consulta``, y se puede leer abajo en cinco lineas.

POR QUE SE PIDE VOCABULARIO Y NO UNA RESPUESTA
==============================================

Al modelo se le pide **palabras sueltas**, no que conteste. Un modelo que
contestara estaria inventando memoria, que es exactamente lo que Sirius no
puede hacer: lo que se recupera tiene que salir del canon. Aqui el modelo
aporta lengua —como se dice esto de otra manera—, y quien decide que existe y
que no sigue siendo el canon a traves de las puertas.
"""

from __future__ import annotations

import json
import os
from typing import Any, Final

from experiments.adr002.ampliacion.fuente import FuenteNoDisponibleError

MODELO_POR_DEFECTO: Final = "gpt-4.1-mini"

VARIABLE_DE_CLAVE: Final = "OPENAI_API_KEY"

#: La instruccion, entera y en el codigo. No se construye por concatenacion ni
#: se lee de un fichero: quien audite esto tiene que poder ver de una vez todo
#: lo que se le dice al modelo, porque cualquier pista de mas invalidaria la
#: medicion sin dejar rastro.
INSTRUCCION: Final = (
    "Eres un ampliador de consultas de un buscador en espanol. Recibes una "
    "pregunta y devuelves palabras sueltas con las que un hispanohablante "
    "podria haber expresado lo mismo: sinonimos, terminos mas generales o mas "
    "concretos, y palabras estrechamente asociadas.\n\n"
    "Reglas:\n"
    "- Devuelve entre 3 y 8 palabras.\n"
    "- Palabras sueltas en minusculas, sin tildes, sin frases.\n"
    "- No repitas palabras que ya estan en la pregunta.\n"
    "- No incluyas variantes de la misma palabra (plural, conjugaciones): esas "
    "el buscador ya las encuentra solo. Aporta OTRAS palabras.\n"
    "- No respondas la pregunta. No inventes datos. No expliques nada.\n\n"
    'Responde solo con un objeto JSON: {"palabras": ["...", "..."]}'
)


class SinonimosDeModelo:
    """Pide vocabulario a un modelo. Falla cerrado y no guarda la clave."""

    def __init__(
        self,
        *,
        modelo: str = MODELO_POR_DEFECTO,
        clave: str | None = None,
        cliente: Any | None = None,
    ) -> None:
        self._modelo = modelo
        if cliente is not None:
            # Inyectable para poder probar el modulo entero sin red ni clave.
            self._cliente = cliente
            return
        try:
            from openai import OpenAI
        except ImportError as fallo:  # pragma: no cover - depende de la maquina
            msg = "falta el paquete 'openai'; instalalo antes de usar esta fuente"
            raise FuenteNoDisponibleError(msg) from fallo
        secreto = clave or os.environ.get(VARIABLE_DE_CLAVE) or _de_sirius()
        if not secreto:
            msg = (
                f"no hay clave: exporta {VARIABLE_DE_CLAVE} o guarda la clave en "
                f"Sirius. La clave no se escribe en ningun artefacto."
            )
            raise FuenteNoDisponibleError(msg)
        self._cliente = OpenAI(api_key=secreto)

    @property
    def identificador(self) -> str:
        return f"modelo:{self._modelo}"

    def sinonimos(self, consulta: str) -> tuple[str, ...]:
        """Vocabulario para esta consulta. El unico dato que sale es la consulta."""
        respuesta = self._cliente.chat.completions.create(
            model=self._modelo,
            messages=[
                {"role": "system", "content": INSTRUCCION},
                {"role": "user", "content": consulta},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        crudo = respuesta.choices[0].message.content or "{}"
        try:
            palabras = json.loads(crudo).get("palabras", [])
        except json.JSONDecodeError as fallo:
            msg = "el modelo no devolvio JSON legible; no se amplia a ciegas"
            raise FuenteNoDisponibleError(msg) from fallo
        if not isinstance(palabras, list):
            msg = "el modelo devolvio algo que no es una lista de palabras"
            raise FuenteNoDisponibleError(msg)
        # El recorte y la limpieza los aplica ``depurar`` en el puerto, comun a
        # todas las fuentes: aqui solo se entrega lo que el modelo dijo.
        return tuple(str(p) for p in palabras)


def _de_sirius() -> str | None:
    """La clave que Sirius 0.1 ya guarda, si esta. Silencioso si no se puede."""
    try:
        import keyring

        from sirius.config.secrets_config import (  # type: ignore[import-untyped]
            OPENAI_API_KEY_SECRET_NAME,
            SIRIUS_KEYRING_SERVICE_NAME,
        )

        return keyring.get_password(SIRIUS_KEYRING_SERVICE_NAME, OPENAI_API_KEY_SECRET_NAME)
    except Exception:  # pragma: no cover - depende de la maquina
        return None


__all__ = ["INSTRUCCION", "MODELO_POR_DEFECTO", "VARIABLE_DE_CLAVE", "SinonimosDeModelo"]
