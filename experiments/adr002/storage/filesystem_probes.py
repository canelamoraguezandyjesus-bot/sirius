"""Sondas del filesystem del laboratorio — ADR002-TOL-207 v0.2.

Las sondas trabajan exclusivamente en un directorio temporal fuera del
repositorio y en el mismo filesystem. El tamaño simultáneo máximo asignado
físicamente es 64 MiB. Comprueban escritura densa, tamaño aparente frente a
bloques asignados, ficheros sparse, reflink/FICLONE, COW, compresión o
deduplicación aparente, creación y liberación de inodos, liberación de
bloques tras borrado, residuo y comportamiento de la ruta de error.

Todo se borra mediante ``finally`` incluso si una sonda falla. El residuo
máximo admisible tras la limpieza es 65.536 B; por encima, la medición es
inválida, se permite una única repetición controlada y un segundo fallo
produce ``NO_EVALUABLE``.
"""

from __future__ import annotations

import errno
import fcntl
import os
import shutil
import time
from pathlib import Path
from typing import Any

from experiments.adr002.storage import schema_storage_v0_1 as SS

_FICLONE = 0x40049409
_MIB = 1_048_576

_bytes_asignados_ahora = 0


def _statvfs_bytes(ruta: Path) -> tuple[int, int, int]:
    """Una observación: (bytes disponibles, inodos libres, granularidad)."""
    vfs = os.statvfs(ruta)
    return vfs.f_bavail * vfs.f_frsize, vfs.f_favail, vfs.f_frsize


def _asignado(ruta: Path) -> int:
    return ruta.lstat().st_blocks * SS.BYTES_POR_BLOQUE_ST_BLOCKS


def _reservar(planificado: int) -> None:
    global _bytes_asignados_ahora
    if _bytes_asignados_ahora + planificado > SS.SONDAS_MAX_SIMULTANEO_BYTES:
        raise RuntimeError(
            "la sonda superaria el maximo simultaneo de 64 MiB asignados fisicamente"
        )
    _bytes_asignados_ahora += planificado


def _liberar(planificado: int) -> None:
    global _bytes_asignados_ahora
    _bytes_asignados_ahora = max(0, _bytes_asignados_ahora - planificado)


def _escribir_denso(ruta: Path, tamano: int, patron: bytes | None = None) -> None:
    _reservar(tamano)
    with open(ruta, "wb") as fh:
        restante = tamano
        bloque = patron if patron is not None else os.urandom(_MIB)
        while restante > 0:
            trozo = bloque[: min(len(bloque), restante)]
            fh.write(trozo)
            restante -= len(trozo)
        fh.flush()
        os.fsync(fh.fileno())


def _borrar(ruta: Path, tamano_planificado: int) -> None:
    try:
        ruta.unlink(missing_ok=True)
    finally:
        _liberar(tamano_planificado)


def _sonda_escritura_densa(directorio: Path) -> dict[str, Any]:
    tamano = 32 * _MIB
    fichero = directorio / "densa.bin"
    disponible_antes, _, _ = _statvfs_bytes(directorio)
    try:
        _escribir_denso(fichero, tamano)
        st = fichero.lstat()
        disponible_con_fichero, _, _ = _statvfs_bytes(directorio)
        return {
            "tamano_escrito_bytes": tamano,
            "tamano_aparente_bytes": st.st_size,
            "bloques_asignados_bytes": st.st_blocks * SS.BYTES_POR_BLOQUE_ST_BLOCKS,
            "asignacion_completa": st.st_blocks * SS.BYTES_POR_BLOQUE_ST_BLOCKS >= tamano,
            "delta_f_bavail_bytes": disponible_antes - disponible_con_fichero,
            "contabilizacion": "st_blocks*512",
        }
    finally:
        _borrar(fichero, tamano)


def _sonda_sparse(directorio: Path) -> dict[str, Any]:
    aparente = 64 * _MIB
    fichero = directorio / "sparse.bin"
    _reservar(_MIB)  # asignación física real esperada: pocos KiB.
    try:
        with open(fichero, "wb") as fh:
            fh.truncate(aparente)
            fh.seek(aparente - 4_096)
            fh.write(b"S" * 4_096)
            fh.flush()
            os.fsync(fh.fileno())
        st = fichero.lstat()
        asignado = st.st_blocks * SS.BYTES_POR_BLOQUE_ST_BLOCKS
        return {
            "tamano_aparente_bytes": st.st_size,
            "bloques_asignados_bytes": asignado,
            "sparse_soportado": asignado < st.st_size,
            "contabilizacion": "st_blocks*512",
            "nota": "st_size se registra pero no se usa como consumo",
        }
    finally:
        _borrar(fichero, _MIB)


def _sonda_reflink(directorio: Path) -> dict[str, Any]:
    tamano = 4 * _MIB
    origen = directorio / "reflink_origen.bin"
    destino = directorio / "reflink_destino.bin"
    try:
        _escribir_denso(origen, tamano, patron=b"R" * _MIB)
        _reservar(tamano)
        try:
            with open(origen, "rb") as src, open(destino, "wb") as dst:
                fcntl.ioctl(dst.fileno(), _FICLONE, src.fileno())
            soportado = True
            detalle = "FICLONE aceptado"
        except OSError as exc:
            soportado = False
            detalle = errno.errorcode.get(exc.errno or 0, str(exc.errno))
        return {"soportado": soportado, "detalle": detalle}
    finally:
        _borrar(destino, tamano)
        _borrar(origen, tamano)


def _sonda_cow(directorio: Path, reflink: dict[str, Any]) -> dict[str, Any]:
    tamano = 8 * _MIB
    fichero = directorio / "cow.bin"
    try:
        _escribir_denso(fichero, tamano, patron=b"C" * _MIB)
        antes = fichero.lstat()
        with open(fichero, "r+b") as fh:
            fh.write(b"X" * _MIB)
            fh.flush()
            os.fsync(fh.fileno())
        despues = fichero.lstat()
        sobrescritura_en_sitio = (
            antes.st_ino == despues.st_ino and antes.st_blocks == despues.st_blocks
        )
        return {
            "reflink_soportado": reflink["soportado"],
            "sobrescritura_en_sitio": sobrescritura_en_sitio,
            "observado": reflink["soportado"] or not sobrescritura_en_sitio,
            "nota": "sin reflink y con sobrescritura en sitio no se observa COW",
        }
    finally:
        _borrar(fichero, tamano)


def _sonda_compresion(directorio: Path) -> dict[str, Any]:
    tamano = 32 * _MIB
    comprimible = directorio / "ceros.bin"
    duplicado_a = directorio / "dedup_a.bin"
    duplicado_b = directorio / "dedup_b.bin"
    tamano_dup = 8 * _MIB
    try:
        _escribir_denso(comprimible, tamano, patron=b"\x00" * _MIB)
        asignado_ceros = _asignado(comprimible)
        _borrar(comprimible, tamano)
        _escribir_denso(duplicado_a, tamano_dup, patron=b"D" * _MIB)
        _escribir_denso(duplicado_b, tamano_dup, patron=b"D" * _MIB)
        asignado_dup = _asignado(duplicado_a) + _asignado(duplicado_b)
        compresion_aparente = asignado_ceros < (tamano * 9) // 10
        deduplicacion_aparente = asignado_dup < (2 * tamano_dup * 9) // 10
        return {
            "ceros_escritos_bytes": tamano,
            "ceros_asignados_bytes": asignado_ceros,
            "compresion_aparente": compresion_aparente,
            "duplicados_escritos_bytes": 2 * tamano_dup,
            "duplicados_asignados_bytes": asignado_dup,
            "deduplicacion_aparente": deduplicacion_aparente,
            "observada": compresion_aparente or deduplicacion_aparente,
        }
    finally:
        _borrar(comprimible, tamano)
        _borrar(duplicado_a, tamano_dup)
        _borrar(duplicado_b, tamano_dup)


def _sonda_inodos(directorio: Path) -> dict[str, Any]:
    n = 256
    subdir = directorio / "inodos"
    _, inodos_antes, _ = _statvfs_bytes(directorio)
    try:
        subdir.mkdir()
        for i in range(n):
            (subdir / f"i{i:04d}").touch()
        _, inodos_con_ficheros, _ = _statvfs_bytes(directorio)
        creados_observados = inodos_antes - inodos_con_ficheros
    finally:
        shutil.rmtree(subdir, ignore_errors=True)
    _, inodos_despues, _ = _statvfs_bytes(directorio)
    return {
        "inodos_creados": n,
        "delta_f_favail_observado": creados_observados,
        "creacion_observable": creados_observados >= n // 2,
        "liberacion_observada": inodos_despues >= inodos_con_ficheros + n // 2,
        "f_favail_antes": inodos_antes,
        "f_favail_despues": inodos_despues,
    }


def _sonda_liberacion(directorio: Path) -> dict[str, Any]:
    tamano = 16 * _MIB
    fichero = directorio / "liberacion.bin"
    disponible_antes, _, granularidad = _statvfs_bytes(directorio)
    try:
        _escribir_denso(fichero, tamano)
        disponible_con_fichero, _, _ = _statvfs_bytes(directorio)
    finally:
        _borrar(fichero, tamano)
    os.sync()
    disponible_despues, _, _ = _statvfs_bytes(directorio)
    recuperado = disponible_despues - disponible_con_fichero
    return {
        "tamano_bytes": tamano,
        "delta_al_escribir_bytes": disponible_antes - disponible_con_fichero,
        "recuperado_al_borrar_bytes": recuperado,
        "liberacion_observada": recuperado >= (tamano * 9) // 10,
        "granularidad_bytes": granularidad,
    }


def _sonda_ruta_error(directorio: Path) -> dict[str, Any]:
    tamano = _MIB
    fichero = directorio / "error.bin"
    excepcion_propagada = False
    try:
        try:
            _escribir_denso(fichero, tamano)
            raise RuntimeError("fallo provocado por la sonda de ruta de error")
        finally:
            _borrar(fichero, tamano)
    except RuntimeError:
        excepcion_propagada = True
    return {
        "excepcion_provocada": excepcion_propagada,
        "fichero_residual": fichero.exists(),
        "limpieza_tras_excepcion": excepcion_propagada and not fichero.exists(),
    }


def _medir_residuo(
    directorio_padre: Path, disponible_antes: int, inodos_antes: int
) -> dict[str, Any]:
    """Residuo tras la limpieza, con ventana de asentamiento."""
    residuo = None
    residuo_inodos = None
    for _ in range(20):
        os.sync()
        disponible, inodos, _ = _statvfs_bytes(directorio_padre)
        residuo_actual = max(0, disponible_antes - disponible)
        residuo_inodos_actual = max(0, inodos_antes - inodos)
        if residuo is None or residuo_actual < residuo:
            residuo = residuo_actual
            residuo_inodos = residuo_inodos_actual
        if residuo <= SS.RESIDUO_MAXIMO_BYTES:
            break
        time.sleep(0.1)
    return {
        "residuo_bytes": residuo if residuo is not None else 0,
        "residuo_inodos": residuo_inodos if residuo_inodos is not None else 0,
        "maximo_admisible_bytes": SS.RESIDUO_MAXIMO_BYTES,
        "valida": (residuo if residuo is not None else 0) <= SS.RESIDUO_MAXIMO_BYTES,
    }


def _una_pasada(directorio_base: Path, ruta_repositorio: Path) -> dict[str, Any]:
    st_repo = os.stat(ruta_repositorio)
    st_base = os.stat(directorio_base)
    if st_repo.st_dev != st_base.st_dev:
        raise RuntimeError(
            "el repositorio y el directorio temporal de sondas estan en filesystems distintos"
        )
    if str(directorio_base.resolve()).startswith(str(ruta_repositorio.resolve()) + os.sep):
        raise RuntimeError("las sondas deben trabajar fuera del repositorio")
    directorio = directorio_base / "sondas_tol207"
    disponible_antes, inodos_antes, _ = _statvfs_bytes(directorio_base)
    try:
        directorio.mkdir(parents=True, exist_ok=False)
        escritura_densa = _sonda_escritura_densa(directorio)
        fichero_sparse = _sonda_sparse(directorio)
        reflink = _sonda_reflink(directorio)
        cow = _sonda_cow(directorio, reflink)
        compresion = _sonda_compresion(directorio)
        inodos = _sonda_inodos(directorio)
        liberacion = _sonda_liberacion(directorio)
        ruta_error = _sonda_ruta_error(directorio)
    finally:
        shutil.rmtree(directorio, ignore_errors=True)
    limpieza = _medir_residuo(directorio_base, disponible_antes, inodos_antes)
    return {
        "directorio": str(directorio),
        "mismo_filesystem_que_repositorio": True,
        "st_dev_repositorio": st_repo.st_dev,
        "st_dev_sondas": st_base.st_dev,
        "tamano_maximo_simultaneo_bytes": SS.SONDAS_MAX_SIMULTANEO_BYTES,
        "escritura_densa": escritura_densa,
        "fichero_sparse": fichero_sparse,
        "reflink_ficlone": reflink,
        "cow": cow,
        "compresion_o_dedup_aparente": compresion,
        "inodos": inodos,
        "liberacion_bloques_tras_borrado": liberacion,
        "ruta_error": ruta_error,
        "limpieza": limpieza,
    }


def ejecutar_sondas(directorio_base: Path, ruta_repositorio: Path) -> dict[str, Any]:
    """Ejecuta la batería de sondas con una única repetición controlada.

    Si la limpieza deja un residuo superior a 65.536 B la pasada es inválida
    y se repite una sola vez; un segundo fallo produce ``NO_EVALUABLE``.
    """
    primera = _una_pasada(directorio_base, ruta_repositorio)
    if primera["limpieza"]["valida"]:
        return {**primera, "resultado": "VALIDA", "pasadas": 1}
    segunda = _una_pasada(directorio_base, ruta_repositorio)
    if segunda["limpieza"]["valida"]:
        return {**segunda, "resultado": "VALIDA", "pasadas": 2, "primera_pasada_invalida": True}
    return {
        **segunda,
        "resultado": SS.NO_EVALUABLE,
        "pasadas": 2,
        "motivo": "residuo superior a 65.536 B en dos pasadas",
    }
