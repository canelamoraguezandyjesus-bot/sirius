"""Contabilidad de almacenamiento y protocolo de pico — ADR002-TOL-207 v0.2.

Implementa el contrato de medición del anexo de pico:

1. inventario por inode con bloques asignados (``st_blocks * 512``), que
   falla cerrado: un error de lectura nunca se convierte en cero bytes
   válidos; el inventario queda marcado como incompleto y no puede sustentar
   un pico válido;
2. muestreador configurable con período predeterminado de 5 ms, hilo
   dedicado, timestamp monotónico por muestra, intervalos reales y ciclo de
   vida observable: las excepciones del hilo se capturan de forma
   estructurada y un hilo vivo tras el timeout invalida la medición;
3. checkpoints síncronos nombrados, con checkpoints materiales exigidos por
   tipo de operación (construcción, reconstrucción, borrado, purga, VACUUM)
   derivados del anexo §3;
4. doble contabilidad global/inventario con banda de ruido observada, nunca
   inventada; su invalidez invalida el veredicto global y el pico;
5. regla ``NO_EVALUABLE`` para operaciones más rápidas que la observación;
6. cota determinista de reconstrucción/VACUUM y publicación del mayor valor
   válido, sin sustituir nunca un máximo conocido por una muestra inferior.

La unidad primaria de consumo es ``st_blocks * 512``. ``st_size`` se registra
pero no se usa como almacenamiento consumido. Un inode físico se cuenta una
vez; los hard links no duplican consumo; las copias físicas distintas sí.

Veredicto global único: cualquier componente material inválido —resolución
temporal, checkpoints materiales, atribuibilidad, integridad de inventarios,
doble contabilidad, estado del hilo o cota determinista requerida— produce
``NO_EVALUABLE`` y ningún pico numérico se publica como válido. No existe
ninguna situación en la que un subcampo declare la medición inválida y el
pico global aparezca como válido.
"""

from __future__ import annotations

import itertools
import os
import stat as stat_mod
import threading
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Final

from experiments.adr002.storage import schema_storage_v0_1 as SS

# ---------------------------------------------------------------------------
# Inventario por inode · fail-closed
# ---------------------------------------------------------------------------


def inventario_por_inode(
    rutas: Iterable[Path],
    excluir: set[Path] | None = None,
) -> dict[str, Any]:
    """Inventario deduplicado por ``(st_dev, st_ino)`` de las rutas dadas.

    ``bytes_asignados`` suma ``st_blocks * 512`` una sola vez por inode
    físico; ``bytes_aparentes`` suma ``st_size`` con la misma deduplicación y
    se registra solo como dato, nunca como consumo. Los symlinks no se
    siguen: cuentan su propio inode y nunca su destino.

    Fail-closed: cualquier ``OSError`` durante el recorrido —``lstat``,
    iteración de directorio, desaparición de un objeto, acceso denegado—
    queda registrado en ``errores_inventario`` y marca
    ``inventario_completo = False``. Los datos parciales se conservan
    únicamente como diagnóstico: un inventario incompleto no puede sustentar
    un pico válido.
    """
    excluidas = {p.resolve() for p in (excluir or set())}
    vistos: set[tuple[int, int]] = set()
    bytes_asignados = 0
    bytes_aparentes = 0
    dispositivos: set[int] = set()
    errores: list[dict[str, str]] = []

    def registrar_error(ruta: Path, exc: OSError) -> None:
        errores.append(
            {
                "ruta": str(ruta),
                "tipo": type(exc).__name__,
                "mensaje": str(exc),
            }
        )

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
        try:
            if ruta.resolve() in excluidas:
                return
        except OSError as exc:
            registrar_error(ruta, exc)
            return
        try:
            st = ruta.lstat()
        except OSError as exc:
            registrar_error(ruta, exc)
            return
        acumular(st)
        # La decisión de descenso sale del propio lstat ya obtenido: una
        # segunda stat (is_dir/is_symlink) tragaría OSError y omitiría el
        # subárbol sin registrar el error. S_ISDIR sobre lstat nunca es
        # cierto para un symlink, así que los symlinks no se siguen.
        if stat_mod.S_ISDIR(st.st_mode):
            try:
                hijos = sorted(ruta.iterdir())
            except OSError as exc:
                registrar_error(ruta, exc)
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
        "inventario_completo": not errores,
        "errores_inventario": errores,
        "numero_errores": len(errores),
        "rutas_no_contabilizadas": [e["ruta"] for e in errores],
    }


# ---------------------------------------------------------------------------
# Muestreador dedicado · ciclo de vida observable
# ---------------------------------------------------------------------------


class MuestreadorAlmacenamiento:
    """Muestreador en hilo dedicado de ``f_bavail``/``f_favail`` e inventario.

    Cada muestra procede de una única llamada ``statvfs`` con timestamp
    monotónico propio. Se registran los intervalos reales entre muestras; la
    validez se juzga con el intervalo máximo observado, no con el solicitado.

    El ciclo de vida del hilo es observable y falla cerrado: una excepción
    dentro del hilo se captura de forma estructurada (tipo y mensaje, sin
    traceback), y ``detener`` comprueba ``is_alive`` tras el ``join``. Un
    hilo vivo tras el timeout, un hilo terminado por excepción o una muestra
    con inventario incompleto invalidan la medición.
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
        self.muestras: list[dict[str, Any]] = []
        self.error_hilo: dict[str, str] | None = None
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._bucle, name="muestreador-tol207", daemon=True)

    def _muestra(self) -> dict[str, Any]:
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
            "inventario_completo": inventario["inventario_completo"],
            "inventario_numero_errores": inventario["numero_errores"],
        }

    def _bucle(self) -> None:
        try:
            while not self._parar.is_set():
                self.muestras.append(self._muestra())
                self._parar.wait(self.periodo_solicitado_ns / 1_000_000_000)
        except Exception as exc:  # el hilo nunca muere en silencio
            self.error_hilo = {
                "tipo": type(exc).__name__,
                "mensaje": str(exc),
                "origen": "hilo",
            }

    def iniciar(self) -> None:
        self._hilo.start()

    def detener(self, timeout_join_s: float = 10.0) -> dict[str, Any]:
        self._parar.set()
        self._hilo.join(timeout=timeout_join_s)
        hilo_vivo_tras_timeout = self._hilo.is_alive()
        hilo_finalizado = not hilo_vivo_tras_timeout
        if hilo_finalizado and self.error_hilo is None:
            try:
                self.muestras.append(self._muestra())
            except OSError as exc:
                # La muestra final síncrona tampoco puede fallar en silencio;
                # se distingue su origen del de una excepción del propio hilo.
                self.error_hilo = {
                    "tipo": type(exc).__name__,
                    "mensaje": str(exc),
                    "origen": "muestra_final",
                }
        muestras = list(self.muestras)
        intervalos = [
            b["t_monotonico_ns"] - a["t_monotonico_ns"] for a, b in itertools.pairwise(muestras)
        ]
        muestras_incompletas = sum(1 for m in muestras if m.get("inventario_completo") is not True)
        return {
            "n_muestras": len(muestras),
            "periodo_solicitado_ns": self.periodo_solicitado_ns,
            "intervalos_reales_ns": intervalos,
            "intervalo_medio_ns": sum(intervalos) // len(intervalos) if intervalos else 0,
            "intervalo_maximo_ns": max(intervalos) if intervalos else 0,
            "hilo_finalizado": hilo_finalizado,
            "hilo_vivo_tras_timeout": hilo_vivo_tras_timeout,
            "error_hilo": self.error_hilo,
            "muestras_con_inventario_incompleto": muestras_incompletas,
            "muestreador_valido": (
                hilo_finalizado and self.error_hilo is None and muestras_incompletas == 0
            ),
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
    inválida; esa invalidez invalida el veredicto global y el pico, y la
    escritura externa se conserva únicamente como diagnóstico.
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
# Checkpoints materiales por tipo de operación · anexo de pico §3
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

TIPOS_OPERACION: Final[tuple[str, ...]] = (
    "construccion",
    "reconstruccion",
    "borrado",
    "purga",
    "vacuum",
)

# Derivación del anexo §3: (1) y (7) son universales; (2) y (4) aplican a
# toda operación que crea y borra temporales (construcción y
# reconstrucción); (3) al intercambio viejo/nuevo de una reconstrucción;
# (5) al ciclo de checkpoint/journal de una purga; (6) a VACUUM —
# ``durante_vacuum`` queda permitido pero no exigido porque el anexo lo
# condiciona a «cuando sea instrumentable».
CHECKPOINTS_MATERIALES_POR_TIPO: Final[dict[str, tuple[str, ...]]] = {
    "construccion": (
        "antes_de_la_operacion",
        "despues_de_crear_temporales",
        "antes_de_borrar_temporales",
        "final",
    ),
    "reconstruccion": (
        "antes_de_la_operacion",
        "despues_de_crear_temporales",
        "antes_de_intercambiar_viejo_nuevo",
        "antes_de_borrar_temporales",
        "final",
    ),
    "borrado": (
        "antes_de_la_operacion",
        "final",
    ),
    "purga": (
        "antes_de_la_operacion",
        "antes_de_checkpoint_journal",
        "despues_de_checkpoint_journal",
        "final",
    ),
    "vacuum": (
        "antes_de_la_operacion",
        "antes_de_vacuum",
        "final",
    ),
}


def fallos_checkpoints_materiales(tipo_operacion: str, checkpoints: list[str]) -> list[str]:
    """Valida los checkpoints materiales exigidos por tipo de operación.

    Comprueba que todos los checkpoints materiales requeridos para el tipo
    declarado fueron registrados, que pertenecen al vocabulario canónico y
    que aparecen en un orden compatible con la operación. Un nombre
    arbitrario nunca satisface el contrato; una lista no vacía tampoco basta
    por sí sola.
    """
    if tipo_operacion not in CHECKPOINTS_MATERIALES_POR_TIPO:
        return [f"tipo de operacion no contemplado: {tipo_operacion!r}"]
    fallos: list[str] = []
    desconocidos = sorted(set(checkpoints) - set(CHECKPOINTS_CANONICOS))
    if desconocidos:
        fallos.append(f"checkpoints fuera del vocabulario canonico: {desconocidos}")
    requeridos = CHECKPOINTS_MATERIALES_POR_TIPO[tipo_operacion]
    ausentes = [c for c in requeridos if c not in checkpoints]
    if ausentes:
        fallos.append(f"checkpoints materiales ausentes para {tipo_operacion}: {ausentes}")
    indices = [CHECKPOINTS_CANONICOS.index(c) for c in checkpoints if c in CHECKPOINTS_CANONICOS]
    if indices != sorted(indices):
        fallos.append("checkpoints registrados en orden incompatible con la operacion")
    return fallos


# ---------------------------------------------------------------------------
# Validez del pico y publicación
# ---------------------------------------------------------------------------


def evaluar_validez_pico(
    resumen_muestreo: dict[str, Any],
    duracion_operacion_ns: int,
    checkpoints: list[str],
    rutas_atribuibles: bool,
    cota_determinista_calculable: bool,
    *,
    tipo_operacion: str | None = None,
    doble_contabilidad_valida: bool,
    inventarios_completos: bool,
) -> dict[str, Any]:
    """Regla ``NO_EVALUABLE`` del protocolo de pico · veredicto único.

    No se publica pico numérico como válido si la operación dura menos de
    tres intervalos reales, si la pausa máxima del muestreador es
    incompatible con la duración, si hubo creación y borrado sin observación
    ni checkpoint, si faltan los checkpoints materiales del tipo de
    operación declarado, si hay rutas no atribuibles, si no puede calcularse
    una cota determinista, si la doble contabilidad es inválida, si algún
    inventario quedó incompleto o si el hilo del muestreador no finalizó de
    forma válida. Cero intervalos observados nunca es resolución válida.
    """
    motivos: list[str] = []
    intervalos = resumen_muestreo.get("intervalos_reales_ns", [])
    dentro = [
        i for i in intervalos if i <= duracion_operacion_ns
    ]  # aproximación conservadora: intervalos completos observados
    if len(dentro) < SS.MINIMO_INTERVALOS_OPERACION:
        motivos.append("la operacion dura menos de tres intervalos reales del muestreador")
    maximo = resumen_muestreo.get("intervalo_maximo_ns", 0)
    if duracion_operacion_ns > 0 and maximo * SS.MINIMO_INTERVALOS_OPERACION > (
        duracion_operacion_ns * 2
    ):
        motivos.append("pausa maxima del muestreador incompatible con la duracion de la operacion")
    if not checkpoints:
        motivos.append("objetos creados y borrados sin observacion ni checkpoint")
    if tipo_operacion is None:
        motivos.append("tipo de operacion no declarado para validar checkpoints materiales")
    else:
        motivos.extend(fallos_checkpoints_materiales(tipo_operacion, checkpoints))
    if not rutas_atribuibles:
        motivos.append("rutas no atribuibles al objeto medido")
    if not cota_determinista_calculable:
        motivos.append("no puede calcularse una cota determinista")
    if not doble_contabilidad_valida:
        motivos.append("doble contabilidad invalida: diferencia global/inventario fuera de banda")
    if not inventarios_completos:
        motivos.append("inventario de checkpoints incompleto: errores de lectura en el recorrido")
    if resumen_muestreo.get("hilo_finalizado") is not True:
        motivos.append("muestreador sin finalizacion confirmada del hilo")
    if resumen_muestreo.get("hilo_vivo_tras_timeout") is True:
        motivos.append("hilo del muestreador vivo tras el timeout de join")
    error_hilo = resumen_muestreo.get("error_hilo")
    if error_hilo:
        motivos.append(
            f"excepcion en el hilo del muestreador: {error_hilo.get('tipo', 'desconocida')}"
        )
    if resumen_muestreo.get("muestras_con_inventario_incompleto", 0):
        motivos.append("muestras del muestreador con inventario incompleto")
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
    ``NO_EVALUABLE``, ``pico_publicado_bytes`` es ``None`` y la cota
    determinista queda como único dato utilizable cuando existe (anexo §5),
    nunca como pico publicado.
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


class ContabilidadOperacion:
    """Orquesta banda de ruido, muestreo, checkpoints y doble contabilidad.

    El tipo de operación se declara explícitamente al crearla y determina
    los checkpoints materiales exigidos. La atribuibilidad no se presume:
    se deriva de inventarios completos, de la doble contabilidad válida y de
    la ausencia de dispositivos no autorizados. Cualquier componente
    material inválido produce ``NO_EVALUABLE`` sin pico numérico.
    """

    def __init__(
        self,
        ruta_observada: Path,
        rutas_atribuibles: Iterable[Path],
        tipo_operacion: str,
        periodo_ns: int = SS.PERIODO_MUESTREO_NS,
        duracion_ventana_inactiva_ns: int = 200_000_000,
        timeout_join_s: float = 10.0,
    ) -> None:
        self._ruta = Path(ruta_observada)
        self._atribuibles = [Path(p) for p in rutas_atribuibles]
        self.tipo_operacion = tipo_operacion
        self._timeout_join_s = timeout_join_s
        self._st_dev_autorizado = os.stat(self._ruta).st_dev
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
        resumen = self._muestreador.detener(timeout_join_s=self._timeout_join_s)
        muestras = list(self._muestreador.muestras)
        duracion = time.monotonic_ns() - self._inicio_ns
        primero = self.checkpoints[0]
        ultimo = self.checkpoints[-1]
        variacion_global = primero["f_bavail_bytes"] - ultimo["f_bavail_bytes"]
        variacion_inventario = (
            ultimo["inventario"]["bytes_asignados"] - primero["inventario"]["bytes_asignados"]
        )
        contabilidad = doble_contabilidad(variacion_global, variacion_inventario, self.banda_ruido)
        inventarios_checkpoints = [c["inventario"] for c in self.checkpoints]
        checkpoints_completos = all(
            i.get("inventario_completo") is True for i in inventarios_checkpoints
        )
        errores_inventario_checkpoints = sum(
            int(i.get("numero_errores", 0)) for i in inventarios_checkpoints
        )
        inventarios_completos = (
            checkpoints_completos and resumen["muestras_con_inventario_incompleto"] == 0
        )
        dispositivos_observados = sorted(
            {d for i in inventarios_checkpoints for d in i.get("dispositivos", [])}
        )
        dispositivos_autorizados = all(
            d == self._st_dev_autorizado for d in dispositivos_observados
        )
        hilo_valido = resumen["hilo_finalizado"] and resumen["error_hilo"] is None
        rutas_atribuibles = (
            inventarios_completos and dispositivos_autorizados and contabilidad["medida_valida"]
        )
        validez = evaluar_validez_pico(
            resumen,
            duracion,
            [c["checkpoint"] for c in self.checkpoints],
            rutas_atribuibles,
            cota_determinista_calculable=bool(cotas_deterministas_bytes),
            tipo_operacion=self.tipo_operacion,
            doble_contabilidad_valida=contabilidad["medida_valida"],
            inventarios_completos=checkpoints_completos,
        )
        pico_muestreado = max(
            (m["inventario_bytes_asignados"] for m in muestras),
            default=None,
        )
        publicacion = publicar_pico(pico_muestreado, list(cotas_deterministas_bytes or []), validez)
        return {
            "tipo_operacion": self.tipo_operacion,
            "duracion_operacion_ns": duracion,
            "muestreo": resumen,
            "checkpoints": [c["checkpoint"] for c in self.checkpoints],
            "doble_contabilidad": contabilidad,
            "atribuibilidad": {
                "rutas_atribuibles": rutas_atribuibles,
                "inventarios_completos": inventarios_completos,
                "errores_inventario_checkpoints": errores_inventario_checkpoints,
                "muestras_con_inventario_incompleto": resumen["muestras_con_inventario_incompleto"],
                "dispositivos_observados": dispositivos_observados,
                "dispositivo_autorizado": self._st_dev_autorizado,
                "doble_contabilidad_valida": contabilidad["medida_valida"],
                "hilo_valido": hilo_valido,
            },
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
