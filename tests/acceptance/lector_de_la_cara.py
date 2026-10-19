"""La cara de Sirius leída de los píxeles de la ventana (piezas B y C de la 0.4, ADR-260 y
ADR-261; ronda 1 de Codex sobre la PR #702).

Las pruebas de aceptación no le preguntan a la cara qué dice que dibujó: miran la imagen que
pinta, como la vería el propietario, y de ella sacan cómo tiene los ojos, adónde mira, las
cejas, la boca, lo que sube al respirar y el gesto que hace. Una cara que no pinte lo que
dice, o que no pinte nada, no pasa.

- **Por sus colores**: cada parte se pinta con uno de ``PALETTE``, el de la cara de verdad,
  y solo cuentan los píxeles de ese color exacto: los bordes suavizados se dejan, igual a
  un lado que a otro.
- **Con las proporciones del dibujo**, escritas aquí: dónde van los ojos, las cejas y la
  boca desde el centro de la cara, y cuánto se mueve cada cosa de 0 a 1. Con ellas se sabe
  dónde mirar y se pasa a números lo que se ve; el centro de la cara, que se mueve al
  respirar y con la cabeza, se mide en cada imagen. Si la cara cambia de proporciones, se
  cambian aquí: lo que no se puede es que pinte una cosa y diga otra.
- **Lo que no se ve no se lee**: con los ojos cerrados no se sabe adónde miran.
- **La mirada va con la izquierda y la derecha de la cámara**, y la cámara no es un espejo:
  desde la pieza D (ADR-262), la cara dibuja la pupila al revés en horizontal, y así se lee.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from sirius.presentation.face_widget import PALETTE

# --- Las proporciones del dibujo --------------------------------------------------------

#: El lado de la cara: el menor entre el ancho del panel y 1,6 veces su alto. La cara mide
#: 0,9 altos de alto: al asentir se sale un poco del panel, y entonces su centro se mide
#: desde el borde que se ve.
LADO_POR_ALTO = 1.6
CARA_POR_ALTO = 0.9
#: Los ojos: sus centros, a 0,17 lados del centro de la cara a cada lado y 0,08 altos por
#: encima; su radio, 0,13 altos; el iris, la mitad del ojo, y llega hasta el borde cuando la
#: mirada vale 1.
OJOS_A_LOS_LADOS = 0.17
OJOS_ENCIMA = 0.08
RADIO_DEL_OJO = 0.13
IRIS_POR_OJO = 0.5
#: La pupila se dibuja al revés en horizontal (ADR-262): hacia la derecha de la cámara es
#: hacia la izquierda de la pantalla.
ESPEJO = -1
#: Las cejas: en reposo, a 1,45 radios del ojo por encima de su centro; suben 0,35 radios de
#: 0 a 1.
CEJA_EN_REPOSO = 1.45
CEJA_POR_UNIDAD = 0.35
#: La boca: su centro, a 0,22 altos por debajo del de la cara; mide 0,22 lados de ancho;
#: abierta del todo, 0,16 altos, con un borde de 0,02; y al sonreír de 0 a 1, su centro baja
#: 0,05 altos más que sus puntas.
BOCA_DEBAJO = 0.22
ANCHO_DE_LA_BOCA = 0.22
BOCA_ABIERTA_DEL_TODO = 0.16
BORDE_DE_LA_BOCA = 0.02
SONRISA_POR_UNIDAD = 0.05
#: Lo que sube la cara al respirar de 0 a 1, en altos; y lo que se mueve la cabeza de 0 a
#: 1, a lo ancho en lados y a lo alto en altos.
RESPIRA_POR_UNIDAD = 0.012
CABEZA_A_LO_ANCHO = 0.05
CABEZA_A_LO_ALTO = 0.06

#: Desde cuánto se ve un gesto, en las unidades de arriba. En reposo, lo que más se mueve
#: queda muy por debajo: la mirada, hasta 0,18 a un lado y 0,12 arriba; las cejas y la
#: sonrisa, nada; y lo que sube la cara al respirar, 0,012 altos.
UMBRAL_DEL_GESTO = 0.4
#: Lo que sube o baja la cara para ver que asiente, en altos: el doble de lo que respira.
ASIENTE_DESDE = 0.025
#: El guiño: el ojo de la derecha de la pantalla, abierto menos que esto, y el otro, más
#: que esto.
GUINO_CERRADO = 0.4
GUINO_ABIERTO = 0.75
#: Los ojos en blanco: la mirada, más arriba que esto.
OJOS_EN_BLANCO = 0.5
#: Con los ojos así de abiertos, o menos, se ve el párpado.
SE_VE_EL_PARPADO = 0.9

#: Las partes que se pueden ver.
PARTES = frozenset({"ojos", "párpados", "cejas", "boca"})


def _rgb32(color: str) -> bytes:
    """``color``, «#rrggbb», como lo guarda una imagen RGB32: azul, verde, rojo y opaco."""
    rojo, verde, azul = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return bytes((azul, verde, rojo, 0xFF))


_CARA = _rgb32(PALETTE["cara"])
_OJO = _rgb32(PALETTE["ojo"])
_IRIS = _rgb32(PALETTE["iris"])
_PUPILA = _rgb32(PALETTE["pupila"])
_TRAZO = _rgb32(PALETTE["trazo"])


@dataclass(frozen=True, slots=True)
class Dibujo:
    """La cara de Sirius en un instante, leída de los píxeles de la ventana.

    ``ojos`` va de 0, cerrados, a 1, abiertos: lo que se ve de los dos, de media.
    ``mirada`` es hacia dónde miran, de -1 a 1 en cada eje, con la misma izquierda y derecha
    que ve la cámara; (0, 0) es al frente; ``None`` si no se ve ningún iris. ``cejas`` va de
    -1, fruncidas, a 1, arriba: la de la izquierda de la pantalla, que no sube sola.
    ``boca``, de 0, cerrada, a 1, abierta del todo; ``respira`` es lo que sube la cara, en lo
    que sube al respirar. ``gesto`` es el de la lista que se le ve hacer, si se le ve alguno.
    Lo que no se ve, ``nan``.
    """

    momento: float
    ojos: float
    mirada: tuple[float, float] | None
    cejas: float
    boca: float
    respira: float
    gesto: str | None = None


class _Imagen:
    """Una imagen de Qt, en RGB32, con lo que hace falta para buscar colores por filas."""

    def __init__(self, imagen: Any) -> None:
        from PySide6.QtGui import QImage

        rgb = imagen.convertToFormat(QImage.Format.Format_RGB32)
        self.ancho, self.alto = rgb.width(), rgb.height()
        self._paso = rgb.bytesPerLine()
        self._datos = bytes(rgb.constBits())[: self._paso * self.alto]

    def extremos(
        self, y: int, colores: tuple[bytes, ...], desde: int = 0, hasta: int | None = None
    ) -> tuple[int, int] | None:
        """La primera y la última columna de la fila ``y`` con alguno de ``colores``, de la
        columna ``desde`` a la ``hasta``, sin incluirla; ``None`` si no hay ninguna."""
        if not 0 <= y < self.alto:
            return None
        desde = max(desde, 0)
        hasta = self.ancho if hasta is None else min(hasta, self.ancho)
        if desde >= hasta:
            return None
        inicio, fin = y * self._paso + desde * 4, y * self._paso + hasta * 4
        primera: int | None = None
        ultima = 0
        for color in colores:
            i = self._datos.find(color, inicio, fin)
            while i != -1 and (i - inicio) % 4:
                i = self._datos.find(color, i + 1, fin)
            if i == -1:
                continue
            j = self._datos.rfind(color, inicio, fin)
            while (j - inicio) % 4:
                j = self._datos.rfind(color, inicio, j + 3)
            x0, x1 = desde + (i - inicio) // 4, desde + (j - inicio) // 4
            primera = x0 if primera is None else min(primera, x0)
            ultima = max(ultima, x1)
        return None if primera is None else (primera, ultima)

    def es(self, x: int, y: int, color: bytes) -> bool:
        """Si el píxel de ``x`` e ``y`` es de ``color``."""
        if not (0 <= x < self.ancho and 0 <= y < self.alto):
            return False
        sitio = y * self._paso + x * 4
        return self._datos[sitio : sitio + 4] == color

    def filas(
        self, colores: tuple[bytes, ...], y0: float, y1: float, x0: float, x1: float
    ) -> list[tuple[int, int, int]]:
        """Las filas de ``y0`` a ``y1`` con alguno de ``colores`` entre las columnas ``x0`` y
        ``x1``: cada una, con su primera y su última columna."""
        encontradas: list[tuple[int, int, int]] = []
        for y in range(max(math.floor(y0), 0), min(math.ceil(y1), self.alto)):
            extremos = self.extremos(y, colores, math.floor(x0), math.ceil(x1))
            if extremos is not None:
                encontradas.append((y, *extremos))
        return encontradas


@dataclass(frozen=True, slots=True)
class _Ojo:
    """Lo que se ve de un ojo: lo abierto que está y adónde mira, si se ve su iris."""

    abierto: float
    mirada: tuple[float, float] | None
    se_ve: bool


@dataclass(frozen=True, slots=True)
class Lectura:
    """Todo lo que se ve de la cara en una imagen."""

    dibujo: Dibujo
    partes: frozenset[str]


def lee(imagen_de_qt: Any, momento: float) -> Lectura | None:
    """Lo que se ve de la cara en ``imagen_de_qt``, el panel de la cara tal como se pintó;
    ``None`` si no hay una cara, ni imagen: la pantalla puede no tener aún nada pintado."""
    if imagen_de_qt.isNull():
        return None
    imagen = _Imagen(imagen_de_qt)
    ancho, alto = imagen.ancho, imagen.alto
    caras = imagen.filas((_CARA,), 0, alto, 0, ancho)
    if not caras:
        return None
    arriba, abajo = caras[0][0], caras[-1][0]
    izquierda = min(fila[1] for fila in caras)
    derecha = max(fila[2] for fila in caras)
    centro_x = (izquierda + derecha + 1) / 2
    if abajo >= alto - 1 and arriba > 0:
        centro_y = arriba - 0.5 + alto * CARA_POR_ALTO / 2
    elif arriba <= 0 and abajo < alto - 1:
        centro_y = abajo + 1.5 - alto * CARA_POR_ALTO / 2
    else:
        centro_y = (arriba + abajo + 1) / 2
    lado = min(ancho, alto * LADO_POR_ALTO)
    radio = alto * RADIO_DEL_OJO
    ojo_y = centro_y - alto * OJOS_ENCIMA
    ojos = [
        _ojo(imagen, centro_x + lado_x * lado * OJOS_A_LOS_LADOS, ojo_y, radio)
        for lado_x in (-1, 1)
    ]
    cejas = [
        _ceja(imagen, centro_x + lado_x * lado * OJOS_A_LOS_LADOS, ojo_y, radio)
        for lado_x in (-1, 1)
    ]
    boca, sonrisa, hay_boca = _boca(imagen, centro_x, centro_y + alto * BOCA_DEBAJO, lado, alto)
    miradas = [ojo.mirada for ojo in ojos if ojo.mirada is not None]
    mirada = (
        (sum(m[0] for m in miradas) / len(miradas), sum(m[1] for m in miradas) / len(miradas))
        if miradas
        else None
    )
    cabeza_x = (centro_x - ancho / 2) / (lado * CABEZA_A_LO_ANCHO)
    subida = (alto / 2 - centro_y) / alto
    dibujo = Dibujo(
        momento=momento,
        ojos=(ojos[0].abierto + ojos[1].abierto) / 2,
        mirada=mirada,
        cejas=cejas[0],
        boca=boca,
        respira=subida / RESPIRA_POR_UNIDAD,
        gesto=_gesto(ojos, mirada, cejas, sonrisa, cabeza_x, subida),
    )
    partes: set[str] = set()
    if all(ojo.se_ve for ojo in ojos):
        partes.add("ojos")
        if any(ojo.abierto <= SE_VE_EL_PARPADO for ojo in ojos):
            partes.add("párpados")
    if not any(math.isnan(ceja) for ceja in cejas):
        partes.add("cejas")
    if hay_boca:
        partes.add("boca")
    return Lectura(dibujo, frozenset(partes))


def _ojo(imagen: _Imagen, x: float, y: float, radio: float) -> _Ojo:
    """El ojo con centro en ``x`` e ``y``: lo que se ve de él desde abajo, que el párpado
    baja desde arriba, y el centro de su iris, que se sabe por lo que se ve de él: una
    cuerda de un círculo tiene su centro a plomo con el del círculo, y por abajo el iris
    siempre se ve, si se ve algo."""
    blanco = imagen.filas((_OJO, _IRIS), y - radio, y + radio + 1, x - radio, x + radio)
    if not blanco:
        # Cerrado del todo: se ve la raya de las pestañas, si está.
        raya = imagen.filas((_TRAZO,), y - radio * 0.2, y + radio * 0.4, x - radio, x + radio)
        return _Ojo(abierto=0.0, mirada=None, se_ve=bool(raya))
    abierto = min(max((y + radio - blanco[0][0]) / (2 * radio), 0.0), 1.0)
    iris = imagen.filas((_IRIS, _PUPILA), blanco[0][0], blanco[-1][0] + 1, x - radio, x + radio)
    if not iris:
        return _Ojo(abierto=abierto, mirada=None, se_ve=True)
    iris_x = (min(f[1] for f in iris) + max(f[2] for f in iris) + 1) / 2
    radio_del_iris = radio * IRIS_POR_OJO
    # El borde de abajo cae a media fila de la última que es toda del iris.
    iris_y = iris[-1][0] + 1.5 - radio_del_iris
    recorrido = radio - radio_del_iris
    return _Ojo(
        abierto=abierto,
        mirada=(ESPEJO * (iris_x - x) / recorrido, (y - iris_y) / recorrido),
        se_ve=True,
    )


def _ceja(imagen: _Imagen, x: float, y: float, radio: float) -> float:
    """Lo alta que está la ceja del ojo con centro en ``x`` e ``y``, de -1 a 1; ``nan`` si no
    se ve. Se busca por encima del ojo, donde no llega nada más que se pinte con su color."""
    # Hasta 0,6 radios encima del centro del ojo: fruncida, la punta de dentro baja más que
    # el ojo, y la raya de las pestañas, la única que se pinta con su color allí, va más abajo.
    trazo = imagen.filas(
        (_TRAZO,),
        y - radio * (CEJA_EN_REPOSO + 2 * CEJA_POR_UNIDAD),
        y - radio * 0.6,
        x - radio,
        x + radio,
    )
    if not trazo:
        return math.nan
    altura = (trazo[0][0] + trazo[-1][0] + 1) / 2
    return ((y - altura) / radio - CEJA_EN_REPOSO) / CEJA_POR_UNIDAD


def _boca(
    imagen: _Imagen, x: float, y: float, lado: float, alto: float
) -> tuple[float, float, bool]:
    """La boca con centro en ``x`` e ``y``: lo abierta que está, de 0 a 1; lo que sonríe
    cerrada, de 0 a 1; y si se ve. Abierta tan poco que el borde le tapa el dentro, menos de
    lo que mide el borde, se lee cerrada."""
    media = lado * ANCHO_DE_LA_BOCA / 2 + alto * BORDE_DE_LA_BOCA
    alta = alto * (BOCA_ABIERTA_DEL_TODO / 2 + BORDE_DE_LA_BOCA + SONRISA_POR_UNIDAD)
    dentro = imagen.filas((_PUPILA,), y - alta, y + alta, x - media, x + media)
    if dentro:
        abierta = dentro[-1][0] - dentro[0][0] + 1 + alto * BORDE_DE_LA_BOCA
        return min(abierta / (alto * BOCA_ABIERTA_DEL_TODO), 1.0), 0.0, True
    trazo = imagen.filas((_TRAZO,), y - alta, y + alta, x - media, x + media)
    if not trazo:
        return math.nan, math.nan, False
    izquierda = min(fila[1] for fila in trazo)
    derecha = max(fila[2] for fila in trazo)
    grueso = alto * BORDE_DE_LA_BOCA

    def altura(columna: int) -> float | None:
        filas = [y for y, _, _ in trazo if imagen.es(columna, y, _TRAZO)]
        return (filas[0] + filas[-1] + 1) / 2 if filas else None

    medio = altura(round((izquierda + derecha) / 2))
    puntas = [altura(round(izquierda + grueso)), altura(round(derecha - grueso))]
    if medio is None or None in puntas:
        return 0.0, 0.0, True
    baja = medio - sum(p for p in puntas if p is not None) / 2
    return 0.0, max(baja / (alto * SONRISA_POR_UNIDAD), 0.0), True


def _gesto(
    ojos: list[_Ojo],
    mirada: tuple[float, float] | None,
    cejas: list[float],
    sonrisa: float,
    cabeza_x: float,
    subida: float,
) -> str | None:
    """El gesto de la lista que se ve en la cara, si se ve alguno: cada uno tiene su señal,
    y en reposo no se ve ninguna."""
    izquierdo, derecho = ojos
    if derecho.abierto < GUINO_CERRADO and izquierdo.abierto > GUINO_ABIERTO:
        return "guino"
    if mirada is not None and mirada[1] > OJOS_EN_BLANCO:
        return "ojos_en_blanco"
    ceja_izquierda, ceja_derecha = cejas
    if not (math.isnan(ceja_izquierda) or math.isnan(ceja_derecha)):
        if ceja_derecha - ceja_izquierda > UMBRAL_DEL_GESTO:
            return "ceja_arriba"
        if min(ceja_izquierda, ceja_derecha) > UMBRAL_DEL_GESTO:
            return "cejas_arriba"
        if max(ceja_izquierda, ceja_derecha) < -UMBRAL_DEL_GESTO:
            return "cejas_fruncidas"
    if sonrisa > UMBRAL_DEL_GESTO:
        return "sonrisa"
    if abs(cabeza_x) > UMBRAL_DEL_GESTO / 2:
        return "niega"
    if abs(subida) > ASIENTE_DESDE:
        return "asiente"
    return None
