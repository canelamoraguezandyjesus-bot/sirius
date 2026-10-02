"""Donde viven los datos de la mina: el volcado de `descargar.py` y lo que los guiones escriben.

El volcado no entra en el repositorio (376 incidencias y 233 PR en JSON, con
los comentarios enteros): se apunta con la variable de entorno `MINA_DATOS` y,
si no esta, es `scripts/mina/datos/` (ignorada por git). Todos los guiones de
esta carpeta leen y escriben ahi, y ninguno depende del directorio desde el que
se invoque ni de donde viva el clon.

Orden de la cadena, cada paso sobre lo que dejo el anterior:
`descargar.py` -> `descargar_pr.py` -> `analizar.py` -> `analizar_pr.py`,
`reproducir_avisos.py`, `falsos_negativos.py`; `cerrado_por_inalcanzable.py`
lee el registro de defectos del arbol, no el volcado.
"""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
_DECLARADO = os.environ.get("MINA_DATOS")
# Una ruta relativa en MINA_DATOS se ancla a la raiz del repositorio, no al
# directorio de invocacion: la misma cadena lee el mismo volcado desde la raiz
# y desde scripts/mina/ (Codex, PR #665 ronda 2).
DATOS = Path(_DECLARADO) if _DECLARADO else AQUI / "datos"
if not DATOS.is_absolute():
    DATOS = RAIZ / DATOS
DATOS = DATOS.resolve()
#: Los nombres LOGICOS de los volcados: lo que los descargadores publican.
RAW_LOGICO = DATOS / "raw"
PRDIR_LOGICO = DATOS / "raw_pr"
HISTORIALES = DATOS / "historiales"


def parcial_de(definitivo: Path) -> Path:
    """Donde se descarga ANTES de publicar: al lado del definitivo, con `.parcial`."""
    return definitivo.with_name(definitivo.name + ".parcial")


def selector_de(definitivo: Path) -> Path:
    """El fichero que nombra la foto publicada bajo el nombre logico `definitivo`."""
    return definitivo.with_name(definitivo.name + ".actual")


def volcado_actual(definitivo: Path) -> Path:
    """La foto publicada bajo el nombre logico `definitivo`: el directorio que
    nombra su selector o, si no hay selector, el propio `definitivo` (la foto
    heredada de antes del selector). Es lo que leen los analizadores."""
    try:
        nombre = selector_de(definitivo).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return definitivo
    return definitivo.with_name(nombre) if nombre else definitivo


#: Lo que leen los analizadores: la foto publicada en el momento de importar.
RAW = volcado_actual(RAW_LOGICO)
PRDIR = volcado_actual(PRDIR_LOGICO)


def publicar_volcado(parcial: Path, definitivo: Path) -> None:
    """Publica `parcial` como la foto de `definitivo` con UN cambio atomico.

    Sobrescribir cada fichero no daba atomicidad: una descarga que fallara a
    medias dejaba un indice nuevo con historiales viejos y `analizar.py`
    mezclaba las dos fotos sin aviso (Codex, PR #665, ronda 6). Apartar el
    definitivo y renombrar el parcial encima tampoco: entre los dos renombrados
    la foto visible no existia, y un `SIGKILL` o un corte en ese instante la
    dejaba ausente, con o sin vuelta atras en `except` (rondas 7 y 8). Asi que
    la foto visible no se retira nunca: el parcial se renombra a un directorio
    propio (`<nombre>.<marca>`; si el proceso muere antes, nada cambio; si
    muere despues, la nueva existe pero no esta seleccionada) y el selector
    (`<nombre>.actual`, el nombre de la foto publicada) se sustituye con
    `os.replace`, que es atomico en POSIX: el unico instante de cambio. Solo
    despues se borra la foto anterior. `volcado_actual` lee el selector; una
    foto heredada de antes del selector sigue leyendose mientras no se publique
    otra.
    """
    anterior = volcado_actual(definitivo)
    marca = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    nueva = definitivo.with_name(f"{definitivo.name}.{marca}")
    copia = 1
    while nueva.exists():
        nueva = definitivo.with_name(f"{definitivo.name}.{marca}-{copia}")
        copia += 1
    parcial.rename(nueva)
    selector = selector_de(definitivo)
    temporal = selector.with_name(selector.name + ".tmp")
    try:
        temporal.write_text(nueva.name + "\n", encoding="utf-8")
        os.replace(temporal, selector)
    except OSError:
        # La seleccion no se completo: la foto nueva vuelve a llamarse parcial
        # para que siga siendo una descarga interrumpida a la vista y no una
        # foto huerfana (Codex, PR #665, ronda 9). Si el proceso muere en medio
        # sin pasar por aqui, `fotos_huerfanas` la encuentra.
        if nueva.exists() and not parcial.exists():
            nueva.rename(parcial)
        raise
    if anterior != nueva and anterior.exists():
        shutil.rmtree(anterior, ignore_errors=True)


def fotos_huerfanas(definitivo: Path) -> list[Path]:
    """Las fotos publicadas a medias: directorios `<nombre>.<marca>` que no son la
    foto seleccionada. Quedan cuando el proceso muere entre el renombrado del
    parcial y la sustitucion del selector (Codex, PR #665, ronda 9): el selector
    sigue apuntando a la anterior y, sin esta busqueda, el analisis usaria datos
    viejos sin avisar."""
    seleccionada = volcado_actual(definitivo)
    prefijo = definitivo.name + "."
    return sorted(
        p
        for p in definitivo.parent.glob(prefijo + "*")
        if p.is_dir()
        and p != seleccionada
        and p.name != parcial_de(definitivo).name
        and p.name[len(prefijo) : len(prefijo) + 1].isdigit()
    )
