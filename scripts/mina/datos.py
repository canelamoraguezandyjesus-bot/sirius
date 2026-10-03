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
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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


def avisos_de_volcado(logico: Path, descargador: str) -> list[str]:
    """Lo que un analizador tiene que decir ANTES de leer un volcado: si hay una
    descarga interrumpida (`<nombre>.parcial`) y si hay fotos publicadas a medias
    (`fotos_huerfanas`). Es una funcion del nombre logico para que valga igual
    para `raw` (`descargar.py`) y para `raw_pr` (`descargar_pr.py`): las
    comprobaciones vivian solo en `analizar.py` y `analizar_pr.py` leia `raw_pr`
    sin ellas (Codex, PR #665, rondas 6, 9 y 10)."""
    seleccionada = volcado_actual(logico)
    avisos: list[str] = []
    if not seleccionada.is_dir():
        # Un MINA_DATOS nuevo, o un selector que nombra una foto que ya no esta:
        # sin esto la ausencia entera del volcado era «sin avisos» y el analizador
        # que lo lee publicaba cero filas como una medicion (Codex, PR #665,
        # ronda 13). `exigir_volcado` detiene a ese analizador.
        avisos.append(
            f"AVISO: no hay volcado publicado en {seleccionada}; el analizador que lo lee se "
            f"detiene. Ejecuta {descargador}."
        )
    parcial = parcial_de(logico)
    if parcial.exists():
        avisos.append(
            f"AVISO: hay una descarga interrumpida en {parcial}; los analizadores usan el "
            f"volcado completo anterior, {seleccionada}. Repite {descargador} para refrescarlo."
        )
    huerfanas = fotos_huerfanas(logico)
    if huerfanas:
        nombres = ", ".join(p.name for p in huerfanas)
        avisos.append(
            f"AVISO: hay fotos descargadas sin seleccionar ({nombres}): una publicacion murio "
            f"entre el renombrado y el selector. Los analizadores usan la seleccionada, "
            f"{seleccionada}. Repite {descargador} para refrescarla."
        )
    return avisos


#: Todos los volcados que publica un descargador, con el guion que los refresca.
#: Los analizadores avisan de TODOS antes de leer nada, lean el que lean, para
#: que ninguno pueda olvidar uno de los que lee (Codex, PR #665, ronda 11:
#: `analizar_pr.py` avisaba de `raw_pr` y leia tambien `raw` sin aviso).
VOLCADOS: tuple[tuple[Path, str], ...] = (
    (RAW_LOGICO, "descargar.py"),
    (PRDIR_LOGICO, "descargar_pr.py"),
)


def avisos_de_los_volcados() -> list[str]:
    """Los avisos de todos los volcados conocidos (:data:`VOLCADOS`), en su orden, y
    el de la captura compartida entre los dos primeros (raw y raw_pr)."""
    avisos = [
        aviso
        for logico, descargador in VOLCADOS
        for aviso in avisos_de_volcado(logico, descargador)
    ]
    (raw_logico, _), (pr_logico, _) = VOLCADOS[0], VOLCADOS[1]
    return avisos + avisos_de_captura(volcado_actual(raw_logico), volcado_actual(pr_logico))


#: Los dos volcados de una edicion tienen que ser de la MISMA captura:
#: `descargar.py` escribe esta marca en `raw` y `descargar_pr.py` la copia a
#: `raw_pr`. Si la cadena muere entre los dos, los selectores estan sanos y las
#: cifras que los cruzan (las rondas limpias de §5) saldrian mezcladas sin
#: aviso (Codex, PR #665, ronda 12).
MARCA_DE_CAPTURA = "captura.txt"


def marcar_captura(volcado: Path, marca: str | None = None) -> str:
    """Escribe la marca de captura en un volcado (el parcial, antes de publicarlo)."""
    marca = marca or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    (volcado / MARCA_DE_CAPTURA).write_text(marca + "\n", encoding="utf-8")
    return marca


def captura_de(volcado: Path) -> str | None:
    fichero = volcado / MARCA_DE_CAPTURA
    if not fichero.is_file():
        return None
    return fichero.read_text(encoding="utf-8").strip() or None


def marca_de_captura_para_pr(desde: Path, publicado: Path) -> str:
    """La marca que llevara el volcado de PR: la de `desde` (el `raw` seleccionado).

    Se comprueba ANTES de crear el parcial y de descargar nada (Codex, PR #665,
    ronda 16: comprobarlo despues dejaba un `raw_pr.parcial` lleno al rechazar,
    los analizadores avisaban de una descarga interrumpida y cada repeticion
    volvia a dejar el mismo parcial). Sin marca en `desde` no hay captura que
    compartir. Y una captura empareja UN solo volcado de PR: si la foto
    publicada bajo el nombre logico `publicado` ya lleva esa marca, no se
    descarga otro, porque un `descargar_pr.py` ejecutado solo heredaria la marca
    de una captura anterior y los dos volcados pasarian por la misma sin serlo
    (ronda 14). La prueba del emparejamiento es el propio volcado publicado, que
    se publica en un solo paso atomico (ronda 15). Un volcado de PR interrumpido
    antes de publicar se puede repetir.
    """
    marca = captura_de(desde)
    if marca is None:
        raise SystemExit(
            f"{desde} no lleva {MARCA_DE_CAPTURA}: repite descargar.py antes de descargar las PR"
        )
    emparejado = volcado_actual(publicado)
    if captura_de(emparejado) == marca:
        raise SystemExit(
            f"la captura {marca} de {desde} ya tiene su volcado de PR en {emparejado}, y una "
            "captura empareja un solo volcado de PR: repite descargar.py y despues descargar_pr.py"
        )
    return marca


def exigir_misma_captura(producto: str, marca_producto: str | None, raw: Path) -> None:
    """Un producto de la cadena (`resumen.json`, o el volcado de PR) solo vale con
    la foto de `raw` de la que salio: si `descargar.py` publica otra captura y la
    cadena se corta antes de repetir el paso siguiente, los lectores mezclaban las
    incidencias y las horas de una foto con los cuerpos de otra (Codex, PR #665,
    ronda 16). Marcas distintas: parar. Sin marca en alguno de los dos tampoco se
    puede medir: tambien se para (ronda 17; avisar y seguir era aceptar la mezcla
    que no se puede descartar)."""
    de_raw = captura_de(raw)
    if marca_producto is None or de_raw is None:
        sin = ", ".join(n for n, m in ((producto, marca_producto), (str(raw), de_raw)) if m is None)
        raise SystemExit(
            f"sin marca de captura en {sin}: no se puede saber si {producto} salio de la foto "
            f"{raw}; repite la cadena entera (descargar.py, descargar_pr.py y analizar.py)"
        )
    if marca_producto != de_raw:
        raise SystemExit(
            f"{producto} es de la captura {marca_producto} y {raw} de la {de_raw}: repite la "
            "cadena desde el paso que falta (descargar_pr.py o analizar.py) antes de medir"
        )


def avisos_de_captura(raw: Path, pr: Path) -> list[str]:
    """Si `raw` y `raw_pr` no son de la misma captura, o no se puede saber."""
    if not pr.exists():
        return []
    de_raw, de_pr = captura_de(raw), captura_de(pr)
    if de_raw is None or de_pr is None:
        sin = ", ".join(str(v) for v, m in ((raw, de_raw), (pr, de_pr)) if m is None)
        return [
            f"AVISO: sin marca de captura en {sin}: no se puede saber si {raw.name} y {pr.name} "
            "son de la misma captura y las cifras que los cruzan (§5) podrian salir mezcladas. "
            "Repite descargar.py y descargar_pr.py."
        ]
    if de_raw != de_pr:
        return [
            f"AVISO: {pr.name} es de la captura {de_pr} y {raw.name} de la {de_raw}: capturas "
            "distintas, y las cifras que los cruzan (§5) saldrian mezcladas. "
            "Repite descargar_pr.py."
        ]
    return []


def exigir_volcado(logico: Path, descargador: str, patron: str) -> list[Path]:
    """Los ficheros `patron` de la foto publicada bajo `logico`, o parar.

    Un analizador que recorre un volcado con `glob` sobre un directorio que no
    existe (MINA_DATOS nuevo, selector que nombra una foto borrada) o que esta
    vacio no falla: publica cero filas y cero hallazgos como si fueran una
    medicion (Codex, PR #665, ronda 13). La ausencia de lo que se va a medir
    detiene al analizador que lo necesita; nunca es una captura sana.
    """
    seleccionada = volcado_actual(logico)
    ficheros = sorted(seleccionada.glob(patron)) if seleccionada.is_dir() else []
    if not ficheros:
        raise SystemExit(
            f"no hay volcado que analizar en {seleccionada} (ningun {patron}): "
            f"ejecuta {descargador} antes"
        )
    return ficheros


def editado_tras(comentario: Mapping[str, Any], fin: str) -> bool | None:
    """Si un comentario se edito despues de `fin`; `None` si no se puede saber.

    La API devuelve el cuerpo VIGENTE con el `created_at` original: un
    comentario creado en la ventana y editado despues tiene un cuerpo que no es
    de la ventana y que no se puede reconstruir, asi que no vale como evidencia
    de ella (Codex, PR #665, ronda 13). Sin `updated_at` (los volcados de PR
    anteriores a esta edicion no lo guardaban) no se puede juzgar, y
    `avisos_de_editados` lo dice.
    """
    editado = comentario.get("updated_at")
    if not editado:
        return None
    return str(editado) > fin


def avisos_de_editados(que: str, fin: str, comentarios: Sequence[Mapping[str, Any]]) -> list[str]:
    """Lo que un analizador tiene que decir de los comentarios que juzga (creados
    hasta `fin`): cuantos se editaron despues y quedan fuera, con sus ids, y
    cuantos no se pueden juzgar porque el volcado no guarda `updated_at`."""
    fuera = [c for c in comentarios if editado_tras(c, fin)]
    sin_fecha = [c for c in comentarios if editado_tras(c, fin) is None]
    avisos: list[str] = []
    if fuera:
        ids = ", ".join(str(c.get("id")) for c in fuera[:20]) + (" ..." if len(fuera) > 20 else "")
        avisos.append(
            f"AVISO: {len(fuera)} comentarios de {que} creados hasta {fin} se editaron despues y "
            f"quedan fuera de la evidencia: su cuerpo ya no es el de la ventana y no se puede "
            f"reconstruir ({ids})."
        )
    if sin_fecha:
        avisos.append(
            f"AVISO: {len(sin_fecha)} comentarios de {que} no guardan updated_at: no se puede "
            f"saber si se editaron despues de {fin}; se usan tal cual. Para guardarlo repite "
            "la cadena entera, descargar.py y despues descargar_pr.py: un volcado de PR "
            "descargado solo no se empareja con una captura anterior."
        )
    return avisos
