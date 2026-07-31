"""Condiciones controladas de la repeticion unica del §6.8 (ADR002-TOL-208).

Este modulo CONGELA, antes de medir, las condiciones ambientales controladas
de la repeticion autorizada por el acta
``SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_REPETICION_68_v1.0.md``. No mide
ninguna operacion de T0, no abre bases de datos y no toca el arnes congelado:
solo materializa, comprueba y registra el entorno.

Las condiciones, y por que cada una es realizable en LAB-LINUX:

1. **Ausencia de tareas concurrentes evitables.** Ninguna bateria de pruebas,
   instalacion ni proceso pesado se lanza durante la ventana de medicion, y
   el arnes lo COMPRUEBA en lo observable: la carga media a un minuto debe
   caer por debajo de ``UMBRAL_CARGA_1M`` antes de abrir la primera ventana
   cronometrada. En la corrida v0.1 la carga arranco en 0,54 —residuo de la
   bateria de pruebas inmediatamente anterior— y subio hasta 1,01; el umbral
   de 0,35 con la maquina en reposo (~0,18 medido al congelar esto) obliga a
   que ese residuo se haya disipado.
2. **Asentamiento entre sesiones.** Antes de CADA sesion se espera a que la
   carga vuelva a caer bajo el umbral, con un plazo maximo por espera. Un
   plazo agotado a mitad de corrida NO aborta —abortar consumiria la
   repeticion sin evidencia—: se registra como incidencia y la corrida sigue.
3. **Misma maquina y mismo arranque durante toda la corrida.** El
   ``boot_id`` se captura antes y despues; un cambio a mitad de corrida
   invalida la repeticion (§6.9). La igualdad con el arranque de la corrida
   v0.1 **no es realizable**: el contenedor es efimero y aquel arranque
   (``fd0d2268…``) ya no existe; se registra el hecho, no se disimula.
4. **Carga registrada.** Ademas de la carga por sesion que ya registra el
   worker congelado, se registra la serie completa de esperas de
   asentamiento, con sus duraciones.

La repeticion se CONSUME al abrirse la primera ventana cronometrada. Un
bloqueo previo —precondiciones o asentamiento inicial no alcanzado— no la
consume, porque no mide nada.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from experiments.adr002.rederivation import rederivation_protocol as rp

#: Acta que autoriza EXACTAMENTE una repeticion. Sin ella, nada se ejecuta.
ACTA_REPETICION: Final = "SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_REPETICION_68_v1.0.md"

#: Umbral de carga media a 1 minuto exigido antes de medir y buscado entre
#: sesiones. Congelado ANTES de la corrida: reposo observado ~0,18 en una
#: maquina de 4 nucleos, muy por debajo del 0,54 inicial de la v0.1.
UMBRAL_CARGA_1M: Final = 0.35

#: Plazo maximo de la espera de asentamiento PREVIA a la primera sesion. Si
#: se agota, la corrida NO SE INICIA y la repeticion NO se consume.
PLAZO_ASENTAMIENTO_PREVIO_S: Final = 600

#: Plazo maximo de cada espera de asentamiento ENTRE sesiones. Si se agota,
#: se registra la incidencia y la corrida CONTINUA: abortar a mitad
#: consumiria la repeticion sin producir evidencia.
PLAZO_ASENTAMIENTO_ENTRE_SESIONES_S: Final = 120

#: Periodo de muestreo de la carga durante las esperas.
MUESTREO_S: Final = 5

#: Arranque bajo el que se midio la corrida v0.1. Ya no existe: el
#: contenedor se recicla, y la unica condicion realizable es la estabilidad
#: DENTRO de la corrida v0.2. Se congela aqui para registrar el contraste.
BOOT_ID_V01: Final = "fd0d2268-0abc-4037-8b2a-c0a91dade2ef"

#: Evidencia v0.1, intangible byte a byte. La repeticion no la sustituye ni
#: la corrige, y cualquier alteracion bloquea antes de medir.
EVIDENCIA_V01: Final[Mapping[str, str]] = {
    "artifacts/adr002_tolerances/rederivacion_t0_v0.1.json": (
        "781132bfe0365f6b7ebcb9139330d10dc76fd0db"
    ),
    "artifacts/adr002_tolerances/rederivacion_t0_v0.1_muestras.json": (
        "04cd805181f9067318adaf84aaa676df1eb52c7c"
    ),
    "artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.1_PROPUESTO.md": (
        "11d41f42838a3fb3512bfe32dcf9e35689980611"
    ),
}

#: Estados finales de estabilidad tras consumir la repeticion (§6.9).
#: INVALIDA no es publicable como estado definitivo: o pasa, o rendimiento
#: queda NO_EVALUABLE. Congelado ANTES de observar resultado alguno.
ESTADO_FINAL_VALIDA: Final = "VALIDA"
ESTADO_FINAL_NO_EVALUABLE: Final = "NO_EVALUABLE"


def estado_final_6_9(resultado_v02: str) -> str:
    """Estado definitivo de una magnitud tras la repeticion unica.

    Regla literal del acta, congelada antes de medir: si la magnitud pasa
    P50 y P95 en la repeticion, ``VALIDA``; cualquier otro resultado deja el
    rendimiento de esa magnitud ``NO_EVALUABLE`` conforme al §6.9, porque la
    repeticion queda consumida y no existe tercera corrida.
    """
    return ESTADO_FINAL_VALIDA if resultado_v02 == "VALIDA" else ESTADO_FINAL_NO_EVALUABLE


def fallos_de_acta_de_repeticion(entorno: rp.EntornoCustodia) -> tuple[str, ...]:
    """Sin acta de repeticion no hay repeticion. La guarda es el documento."""
    try:
        entorno.leer_bytes(f"docs/architecture/{ACTA_REPETICION}")
    except OSError:
        return (
            f"falta {ACTA_REPETICION}: la repeticion unica del §6.8 exige su "
            f"propia autorizacion expresa",
        )
    return ()


def fallos_de_evidencia_v01(entorno: rp.EntornoCustodia) -> tuple[str, ...]:
    """La evidencia v0.1 permanece valida, congelada e intacta."""
    fallos: list[str] = []
    for ruta, esperado in EVIDENCIA_V01.items():
        try:
            observado = rp.blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"evidencia v0.1 ilegible: {ruta}")
            continue
        if observado != esperado:
            fallos.append(f"evidencia v0.1 alterada: {ruta} ({observado} != {esperado})")
    return tuple(fallos)


def carga_1m() -> float:
    """Carga media del sistema a un minuto."""
    return os.getloadavg()[0]


@dataclass(frozen=True, slots=True)
class Espera:
    """Resultado de una espera de asentamiento, para el registro."""

    proposito: str
    umbral: float
    plazo_s: int
    alcanzado: bool
    duracion_s: float
    serie: tuple[float, ...]


def esperar_asentamiento(
    proposito: str,
    *,
    umbral: float = UMBRAL_CARGA_1M,
    plazo_s: int,
    leer_carga: Callable[[], float] = carga_1m,
    dormir: Callable[[float], None] = time.sleep,
    reloj: Callable[[], float] = time.monotonic,
) -> Espera:
    """Espera a que la carga caiga bajo ``umbral`` o a que venza ``plazo_s``.

    Muestrea la carga cada ``MUESTREO_S`` segundos y devuelve la serie
    completa observada: la espera es parte del registro ambiental, no un
    detalle interno. No cronometra ninguna operacion medida.
    """
    inicio = reloj()
    serie = [leer_carga()]
    while serie[-1] > umbral and reloj() - inicio < plazo_s:
        dormir(MUESTREO_S)
        serie.append(leer_carga())
    return Espera(
        proposito=proposito,
        umbral=umbral,
        plazo_s=plazo_s,
        alcanzado=serie[-1] <= umbral,
        duracion_s=round(reloj() - inicio, 3),
        serie=tuple(round(c, 3) for c in serie),
    )


@dataclass(slots=True)
class RegistroCondiciones:
    """Registro completo de las condiciones controladas de la corrida."""

    boot_id_v01: str = BOOT_ID_V01
    boot_id_inicio: str | None = None
    boot_id_final: str | None = None
    umbral_carga_1m: float = UMBRAL_CARGA_1M
    esperas: list[Espera] = field(default_factory=list)
    incidencias: list[str] = field(default_factory=list)

    @property
    def mismo_arranque_que_v01(self) -> bool:
        return self.boot_id_inicio == self.boot_id_v01

    @property
    def arranque_estable(self) -> bool:
        return self.boot_id_inicio is not None and self.boot_id_inicio == self.boot_id_final

    def como_dict(self) -> dict[str, Any]:
        return {
            "umbral_carga_1m": self.umbral_carga_1m,
            "plazo_asentamiento_previo_s": PLAZO_ASENTAMIENTO_PREVIO_S,
            "plazo_asentamiento_entre_sesiones_s": PLAZO_ASENTAMIENTO_ENTRE_SESIONES_S,
            "boot_id_v01": self.boot_id_v01,
            "boot_id_inicio": self.boot_id_inicio,
            "boot_id_final": self.boot_id_final,
            "arranque_estable_durante_la_corrida": self.arranque_estable,
            "mismo_arranque_que_v01": self.mismo_arranque_que_v01,
            "nota_de_arranque": (
                "el contenedor es efimero: el arranque de la v0.1 ya no existe y la "
                "condicion realizable es la estabilidad del boot_id durante la corrida "
                "v0.2, registrando ambos identificadores"
            ),
            "esperas_de_asentamiento": [
                {
                    "proposito": e.proposito,
                    "umbral": e.umbral,
                    "plazo_s": e.plazo_s,
                    "alcanzado": e.alcanzado,
                    "duracion_s": e.duracion_s,
                    "serie_de_carga_1m": list(e.serie),
                }
                for e in self.esperas
            ],
            "incidencias": list(self.incidencias),
        }


def boot_id_actual(ruta: Path = Path("/proc/sys/kernel/random/boot_id")) -> str | None:
    """Identificador de arranque de la maquina, si es legible."""
    try:
        return ruta.read_text().strip()
    except OSError:
        return None
