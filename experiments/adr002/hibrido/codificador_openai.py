"""Un ``CodificadorSemantico`` que pide los vectores a la API de OpenAI.

Es la tercera implementacion del mismo protocolo de tres miembros, junto al
determinista y al de ``spacy``. Que se pueda anadir sin tocar el sidecar, el
lector ni ningun candidato **es** la prueba de que el proveedor esta fuera:
``B04-RF-31`` pide exactamente eso.

QUE SALE DE LA MAQUINA, Y ADONDE
================================

Los textos del canon y las consultas del banco, a ``api.openai.com``. Nada mas:
ni identidades, ni criticidad, ni anotaciones del banco, ni el
``resultado_esperado``. El canon de este experimento es un corpus **inventado**
para medir —viajes, faros, presupuestos de proyectos que no existen—, de modo
que en esta corrida no sale ni un dato personal.

Sirius 0.1 ya habla con este mismo proveedor para generar texto, asi que el
destino no es nuevo. Lo que si es nuevo es **que** se le envia, y por eso queda
escrito aqui en vez de deducirse del codigo.

POR QUE ESTE MODULO NO CORRE EN EL CONTENEDOR DEL AGENTE
=======================================================

Porque no puede: la politica de red de este entorno no alcanza
``api.openai.com``. Corre en la maquina de quien tiene la clave, con el guion
``medir_con_openai.py`` de este mismo paquete, y devuelve un artefacto de
resultados que si se puede traer aqui.

EL COSTE, ANTES DE GASTARLO
===========================

Una corrida completa son 97 textos del canon mas una consulta por caso: menos
de 150 llamadas cortas, del orden de diez mil unidades de texto. Con el modelo
economico de vectores eso queda por debajo de un centimo. No hay bucle que
reintente sin cota ni nada que escale con el numero de casos al cuadrado.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Final

from experiments.adr002.candidates.adr002_b.semantica import (
    ESCALA_FIJA,
    CodificadorNoDisponibleError,
)

#: Modelo por defecto. Es el economico de la familia de vectores, y para este
#: banco la diferencia con el grande no esta demostrada: elegir el caro sin
#: medirlo seria pagar por una suposicion.
MODELO_POR_DEFECTO: Final = "text-embedding-3-small"

#: Cuantos textos por llamada. Agrupar reduce el numero de peticiones sin
#: cambiar ni un vector: el proveedor devuelve lo mismo texto a texto.
LOTE: Final = 64

#: Nombre de la variable de entorno de la que se toma la clave. Se lee de ahi y
#: **no se escribe en ningun sitio**: ni en el sidecar, ni en el artefacto de
#: resultados, ni en un mensaje de error.
VARIABLE_DE_CLAVE: Final = "OPENAI_API_KEY"


class CodificadorOpenAI:
    """Vectores de la API, entregados en punto fijo entero.

    Convierte a entero **aqui**, en la frontera, y no en el sidecar: asi el
    formato persistido sigue sin contener ni un flotante y dos corridas sobre
    el mismo canon producen el mismo fichero logico.
    """

    def __init__(
        self,
        *,
        modelo: str = MODELO_POR_DEFECTO,
        dimensiones: int = 512,
        clave: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as fallo:  # pragma: no cover - depende de la maquina
            msg = "falta el paquete 'openai'; instalalo antes de medir con este codificador"
            raise CodificadorNoDisponibleError(msg) from fallo

        secreto = clave or os.environ.get(VARIABLE_DE_CLAVE) or _de_sirius()
        if not secreto:
            msg = (
                f"no hay clave: exporta {VARIABLE_DE_CLAVE} o guarda la clave en "
                f"Sirius antes de medir. La clave no se escribe en ningun artefacto."
            )
            raise CodificadorNoDisponibleError(msg)

        self._modelo = modelo
        self._dimensiones = dimensiones
        self._cliente = OpenAI(api_key=secreto)

    @property
    def identificador(self) -> str:
        """Viaja al sidecar. Incluye las dimensiones porque recortarlas cambia
        los vectores, y un indice construido con 512 no se puede leer con 1536."""
        return f"openai:{self._modelo}:{self._dimensiones}"

    @property
    def dimensiones(self) -> int:
        return self._dimensiones

    def codificar(self, textos: Sequence[str]) -> tuple[tuple[int, ...], ...]:
        """Un vector entero por texto, en el mismo orden que entraron.

        El orden importa y no se confia en el proveedor: la respuesta trae un
        indice por elemento y aqui se reordena por el, en vez de suponer que
        llega igual que se pidio.
        """
        salida: list[tuple[int, ...]] = []
        for comienzo in range(0, len(textos), LOTE):
            lote = list(textos[comienzo : comienzo + LOTE])
            respuesta = self._cliente.embeddings.create(
                model=self._modelo, input=lote, dimensions=self._dimensiones
            )
            por_indice = sorted(respuesta.data, key=lambda d: d.index)
            if len(por_indice) != len(lote):
                msg = f"el proveedor devolvio {len(por_indice)} vectores para {len(lote)} textos"
                raise CodificadorNoDisponibleError(msg)
            for dato in por_indice:
                salida.append(tuple(round(v * ESCALA_FIJA) for v in dato.embedding))
        return tuple(salida)


def _de_sirius() -> str | None:
    """La clave que Sirius 0.1 ya guarda, si esta. Silencioso si no se puede.

    No es un acceso privilegiado: es el mismo almacen del sistema operativo que
    Sirius usa, leido con el mismo nombre de servicio que su propia
    configuracion declara.
    """
    try:
        import keyring

        # Sirius 0.1 no publica marcador de tipos; el import se anota como
        # externo en vez de relajar la comprobacion del paquete entero.
        from sirius.config.secrets_config import (  # type: ignore[import-untyped]
            OPENAI_API_KEY_SECRET_NAME,
            SIRIUS_KEYRING_SERVICE_NAME,
        )

        return keyring.get_password(SIRIUS_KEYRING_SERVICE_NAME, OPENAI_API_KEY_SECRET_NAME)
    except Exception:  # pragma: no cover - depende de la maquina
        # Sin almacen disponible se sigue sin clave, y quien llama lo dice con
        # su propio mensaje. Tragar el fallo aqui evita filtrar rutas del
        # sistema de quien mide en un rastro de excepcion.
        return None


__all__ = ["LOTE", "MODELO_POR_DEFECTO", "VARIABLE_DE_CLAVE", "CodificadorOpenAI"]
