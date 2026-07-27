"""Contabilidad de almacenamiento y protocolo de pico — ADR002-TOL-207 v0.2.

Implementa el contrato de medición del anexo de pico:

1. inventario por inode con bloques asignados (``st_blocks * 512``);
2. muestreador configurable con período predeterminado de 5 ms, hilo
   dedicado, timestamp monotónico por muestra e intervalos reales;
3. checkpoints síncronos nombrados;
4. doble contabilidad global/inventario con banda de ruido observada, nunca
   inventada;
5. regla ``NO_EVALUABLE`` para operaciones más rápidas que la observación;
6. cota determinista de reconstrucción/VACUUM y publicación del mayor valor
   válido, sin sustituir nunca un máximo conocido por una muestra inferior.

La unidad primaria de consumo es ``st_blocks * 512``. ``st_size`` se registra
pero no se usa como almacenamiento consumido. Un inode físico se cuenta una
vez; los hard links no duplican consumo; las copias físicas distintas sí.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from experiments.adr002.storage import schema_storage_v0_1 as SS

# ---------------------------------------------------------------------------
# Inventario por inode
# ---------------------------------------------------------------------------


def inventario_por_inode(
    rutas: Iterable[Path],
    excluir: set[Path] | None = None,
) -> dict[str, Any]:
    """Inventario deduplicado por ``(st_dev, st_ino)`` de las rutas dadas.

    ``bytes_asignados`` suma ``st_blocks * 512`` una sola vez por inode
    físico; ``bytes_aparentes`` suma ``st_size`` con la misma deduplicación y
    se registra solo como dato, nunca como consumo.
    """
    excluidas = {p.resolve() for p in (excluir or set())}
    vistos: set[tuple[int, int]] = set()
    bytes_asignados = 0
    bytes_aparentes = 0
    dispositivos: set[int] = set()

    def acumular(st: os.stat_result) -> None:
        nonlocal bytes_asignados, bytes_aparentes
        clave = (st.st_dev, st.st_ino)
        if clave in vistos:
            return
        vistos.add(clave)
        dispositivos.add(st.st_dev)
        bytes_asignados += st.st_blocks * SS.BYTES_POR_BLOQUE_ST_BLOCKS
        bytes_aparentes += st.st_size

    def recorrer(ruta: Path) -> None:
        if ruta.resolve() in excluidas:
            return
        try:
            st = ruta.lstat()
        except OSError:
            return
        acumular(st)
        if ruta.is_dir() and not ruta.is_symlink():
            try:
                hijos = sorted(ruta.iterdir())
            except OSError:
                return
            for hijo in hijos:
                recorrer(hijo)

    for ruta in rutas:
        recorrer(Path(ruta))
    return {
        "unidad": "st_blocks*512",
        "bytes_asignados": bytes_asignados,
        "bytes_aparentes": bytes_aparentes,
        "inodos": len(vistos),
        "dispositivos": sorted(dispositivos),
    }


# ---------------------------------------------------------------------------
# Muestreador dedicado
# ---------------------------------------------------------------------------


class MuestreadorAlmacenamiento:
    """Muestreador en hilo dedicado de ``f_bavail``/``f_favail`` e inventario.

    Cada muestra procede de una única llamada ``statvfs`` con timestamp
    monotónico propio. Se registran los intervalos reales entre muestras; la
    validez se juzga con el intervalo máximo observado, no con el solicitado.
    """

    def __init__(
        self,
        ruta_observada: Path,
        rutas_atribuibles: Iterable[Path],
        periodo_ns: int = SS.PERIODO_MUESTREO_NS,
    ) -> None:
        self._ruta = Path(ruta_observada)
        self._atribuibles = [Path(p) for p in rutas_atribuibles]
        self.periodo_solicitado_ns = periodo_ns
        self.muestras: list[dict[str, int]] = []
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._bucle, name="muestreador-tol207", daemon=True)

    def _muestra(self) -> dict[str, int]:
        t = time.monotonic_ns()
        vfs = os.statvfs(self._ruta)
        inventario = inventario_por_inode(self._atribuibles)
        return {
            "t_monotonico_ns": t,
            "f_bavail": vfs.f_bavail,
            "f_favail": vfs.f_favail,
            "f_frsize": vfs.f_frsize,
            "inventario_bytes_asignados": inventario["bytes_asignados"],
            "inventario_inodos": inventario["inodos"],
        }

    def _bucle(self) -> None:
        while not self._parar.is_set():
            self.muestras.append(self._muestra())
            self._parar.wait(self.periodo_solicitado_ns / 1_000_000_000)

    def iniciar(self) -> None:
        self._hilo.start()

    def detener(self) -> dict[str, Any]:
        self._parar.set()
        self._hilo.join(timeout=10)
        self.muestras.append(self._muestra())
        intervalos = [
            b["t_monotonico_ns"] - a["t_monotonico_ns"]
            for a, b in zip(self.muestras, self.muestras[1:], strict=False)
        ]
        return {
            "n_muestras": len(self.muestras),
            "periodo_solicitado_ns": self.periodo_solicitado_ns,
            "intervalos_reales_ns": intervalos,
            "intervalo_medio_ns": sum(intervalos) // len(intervalos) if intervalos else 0,
            "intervalo_maximo_ns": max(intervalos) if intervalos else 0,
        }


# ---------------------------------------------------------------------------
# Banda de ruido y doble contabilidad
# ---------------------------------------------------------------------------


def medir_banda_ruido(
    ruta: Path, duracion_ns: int = 200_000_000, periodo_ns: int = SS.PERIODO_MUESTREO_NS
) -> dict[str, int]:
    """Banda de ruido de una ventana inactiva previa a la operación.

    Se observa ``f_bavail`` sin actividad propia y se registran mínimo,
    máximo, rango y granularidad. La banda nunca se inventa: sale de esta
    observación.
    """
    limite = time.monotonic_ns() + duracion_ns
    valores: list[int] = []
    frsize = 0
    while time.monotonic_ns() < limite:
        vfs = os.statvfs(ruta)
        frsize = vfs.f_frsize
        valores.append(vfs.f_bavail * vfs.f_frsize)
        time.sleep(periodo_ns / 1_000_000_000)
    return {
        "n_observaciones": len(valores),
        "minimo_bytes": min(valores),
        "maximo_bytes": max(valores),
        "rango_bytes": max(valores) - min(valores),
        "granularidad_bytes": frsize,
    }


def doble_contabilidad(
    variacion_global_bytes: int,
    variacion_inventario_bytes: int,
    banda_ruido: dict[str, int],
) -> dict[str, Any]:
    """Compara la variación global de ``f_bavail`` con la del inventario.

    Toda diferencia no explicada se registra como escritura externa. Si la
    diferencia supera la banda observada más la granularidad, la medida es
    inválida.
    """
    diferencia = abs(variacion_global_bytes - variacion_inventario_bytes)
    tolerancia = banda_ruido["rango_bytes"] + banda_ruido["granularidad_bytes"]
    return {
        "variacion_global_bytes": variacion_global_bytes,
        "variacion_inventario_bytes": variacion_inventario_bytes,
        "diferencia_no_explicada_bytes": diferencia,
        "escritura_externa_bytes": diferencia,
        "banda_ruido": dict(banda_ruido),
        "tolerancia_bytes": tolerancia,
        "dentro_de_banda": diferencia <= tolerancia,
        "medida_valida": diferencia <= tolerancia,
    }


# ---------------------------------------------------------------------------
# Validez del pico y publicación
# ---------------------------------------------------------------------------


def evaluar_validez_pico(
    resumen_muestreo: dict[str, Any],
    duracion_operacion_ns: int,
    checkpoints: list[str],
    rutas_atribuibles: bool,
    cota_determinista_calculable: bool,
) -> dict[str, Any]:
    """Regla ``NO_EVALUABLE`` del protocolo de pico.

    No se publica pico numérico como válido si la operación dura menos de
    tres intervalos reales, si la pausa máxima del muestreador es
    incompatible con la duración, si hubo creación y borrado sin observación
    ni checkpoint, si hay rutas no atribuibles o si no puede calcularse una
    cota determinista.
    """
    motivos: list[str] = []
    intervalos = resumen_muestreo.get("intervalos_reales_ns", [])
    dentro = [
        i for i in intervalos if i <= duracion_operacion_ns
    ]  # aproximación conservadora: intervalos completos observados
    if len(dentro) < SS.MINIMO_INTERVALOS_OPERACION and (
        duracion_operacion_ns
        < SS.MINIMO_INTERVALOS_OPERACION * max(resumen_muestreo.get("intervalo_medio_ns", 1), 1)
    ):
        motivos.append("la operacion dura menos de tres intervalos reales del muestreador")
    maximo = resumen_muestreo.get("intervalo_maximo_ns", 0)
    if duracion_operacion_ns > 0 and maximo * SS.MINIMO_INTERVALOS_OPERACION > (
        duracion_operacion_ns * 2
    ):
        motivos.append("pausa maxima del muestreador incompatible con la duracion de la operacion")
    if not checkpoints:
        motivos.append("objetos creados y borrados sin observacion ni checkpoint")
    if not rutas_atribuibles:
        motivos.append("rutas no atribuibles al objeto medido")
    if not cota_determinista_calculable:
        motivos.append("no puede calcularse una cota determinista")
    if motivos:
        return {"resultado": SS.NO_EVALUABLE, "motivos": motivos}
    return {"resultado": "VALIDO", "motivos": []}


def cota_determinista_reconstruccion(
    inventario_viejo_bytes: int, inventario_nuevo_bytes: int
) -> int:
    """Cota determinista viejo + nuevo (u original + copia en VACUUM)."""
    return inventario_viejo_bytes + inventario_nuevo_bytes


def publicar_pico(
    pico_muestreado_bytes: int | None,
    cotas_deterministas_bytes: list[int],
    validez: dict[str, Any],
) -> dict[str, Any]:
    """Publica el mayor valor válido entre muestreo y cotas deterministas.

    Nunca sustituye un máximo conocido por una muestra inferior. Si la
    resolución no es válida, no se publica pico numérico: el resultado es
    ``NO_EVALUABLE`` y la cota determinista queda como único dato utilizable
    cuando existe.
    """
    if validez.get("resultado") != "VALIDO":
        cota = max(cotas_deterministas_bytes) if cotas_deterministas_bytes else None
        return {
            "resultado": SS.NO_EVALUABLE,
            "pico_publicado_bytes": None,
            "cota_determinista_bytes": cota,
            "motivos": list(validez.get("motivos", [])),
        }
    candidatos = list(cotas_deterministas_bytes)
    if pico_muestreado_bytes is not None:
        candidatos.append(pico_muestreado_bytes)
    if not candidatos:
        return {
            "resultado": SS.NO_EVALUABLE,
            "pico_publicado_bytes": None,
            "cota_determinista_bytes": None,
            "motivos": ["sin muestreo valido ni cota determinista"],
        }
    pico = max(candidatos)
    fuente = (
        "muestreo"
        if pico_muestreado_bytes is not None and pico == pico_muestreado_bytes
        else "cota_determinista"
    )
    return {
        "resultado": "VALIDO",
        "pico_publicado_bytes": pico,
        "fuente": fuente,
        "pico_muestreado_bytes": pico_muestreado_bytes,
        "cotas_deterministas_bytes": sorted(cotas_deterministas_bytes),
    }


# ---------------------------------------------------------------------------
# Contabilidad de una operación con checkpoints síncronos
# ---------------------------------------------------------------------------

CHECKPOINTS_CANONICOS: tuple[str, ...] = (
    "antes_de_la_operacion",
    "despues_de_crear_temporales",
    "antes_de_intercambiar_viejo_nuevo",
    "antes_de_borrar_temporales",
    "antes_de_checkpoint_journal",
    "despues_de_checkpoint_journal",
    "antes_de_vacuum",
    "durante_vacuum",
    "final",
)


class ContabilidadOperacion:
    """Orquesta banda de ruido, muestreo, checkpoints y doble contabilidad."""

    def __init__(
        self,
        ruta_observada: Path,
        rutas_atribuibles: Iterable[Path],
        periodo_ns: int = SS.PERIODO_MUESTREO_NS,
        duracion_ventana_inactiva_ns: int = 200_000_000,
    ) -> None:
        self._ruta = Path(ruta_observada)
        self._atribuibles = [Path(p) for p in rutas_atribuibles]
        self.banda_ruido = medir_banda_ruido(
            self._ruta, duracion_ns=duracion_ventana_inactiva_ns, periodo_ns=periodo_ns
        )
        self._muestreador = MuestreadorAlmacenamiento(
            self._ruta, self._atribuibles, periodo_ns=periodo_ns
        )
        self.checkpoints: list[dict[str, Any]] = []
        self._inicio_ns = 0

    def _instantanea(self, nombre: str) -> dict[str, Any]:
        t = time.monotonic_ns()
        vfs = os.statvfs(self._ruta)
        inventario = inventario_por_inode(self._atribuibles)
        return {
            "checkpoint": nombre,
            "t_monotonico_ns": t,
            "f_bavail_bytes": vfs.f_bavail * vfs.f_frsize,
            "f_favail": vfs.f_favail,
            "inventario": inventario,
        }

    def iniciar(self) -> None:
        self._inicio_ns = time.monotonic_ns()
        self.checkpoint("antes_de_la_operacion")
        self._muestreador.iniciar()

    def checkpoint(self, nombre: str) -> dict[str, Any]:
        instantanea = self._instantanea(nombre)
        self.checkpoints.append(instantanea)
        return instantanea

    def cerrar(self, cotas_deterministas_bytes: list[int] | None = None) -> dict[str, Any]:
        self.checkpoint("final")
        resumen = self._muestreador.detener()
        duracion = time.monotonic_ns() - self._inicio_ns
        primero = self.checkpoints[0]
        ultimo = self.checkpoints[-1]
        variacion_global = primero["f_bavail_bytes"] - ultimo["f_bavail_bytes"]
        variacion_inventario = (
            ultimo["inventario"]["bytes_asignados"] - primero["inventario"]["bytes_asignados"]
        )
        contabilidad = doble_contabilidad(variacion_global, variacion_inventario, self.banda_ruido)
        pico_muestreado = max(
            (m["inventario_bytes_asignados"] for m in self._muestreador.muestras),
            default=None,
        )
        validez = evaluar_validez_pico(
            resumen,
            duracion,
            [c["checkpoint"] for c in self.checkpoints],
            rutas_atribuibles=True,
            cota_determinista_calculable=bool(cotas_deterministas_bytes),
        )
        publicacion = publicar_pico(pico_muestreado, list(cotas_deterministas_bytes or []), validez)
        return {
            "duracion_operacion_ns": duracion,
            "muestreo": resumen,
            "checkpoints": [c["checkpoint"] for c in self.checkpoints],
            "doble_contabilidad": contabilidad,
            "validez": validez,
            "pico": publicacion,
        }


# ---------------------------------------------------------------------------
# Declaración de partidas atribuibles a un candidato
# ---------------------------------------------------------------------------


def fallos_declaracion_candidato(declaracion: dict[str, Any]) -> list[str]:
    """Valida la declaración de partidas atribuibles de un candidato.

    El presupuesto por candidato se aplica al máximo simultáneo de todos los
    objetos atribuibles durante reposo, construcción, reconstrucción,
    borrado, purga y VACUUM. Los modelos locales compartidos no consumen
    presupuesto individual: pertenecen a la reserva operativa.
    """
    fallos: list[str] = []
    partidas = declaracion.get("partidas")
    if not isinstance(partidas, dict):
        return ["declaracion sin partidas atribuibles"]
    for partida in SS.PARTIDAS_OBLIGATORIAS_CANDIDATO:
        if partida not in partidas:
            fallos.append(f"partida atribuible omitida: {partida}")
    fases = declaracion.get("fases_maximo_simultaneo")
    if fases != list(SS.FASES_MAXIMO_SIMULTANEO):
        fallos.append("fases del maximo simultaneo distintas de las del contrato")
    if "modelos_locales_compartidos" in partidas:
        fallos.append("modelo compartido cargado a un candidato: pertenece a la reserva operativa")
    if declaracion.get("unidad") != "st_blocks*512":
        fallos.append("declaracion que no contabiliza por st_blocks*512")
    if declaracion.get("hard_links_deduplicados") is not True:
        fallos.append("hard links sin deduplicar por inode fisico")
    return fallos
