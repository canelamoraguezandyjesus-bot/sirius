"""Inventario de erratas de identidad Git y su verificador (ADR-002).

Un SHA citado en un documento de gobierno **es una afirmacion de identidad**:
dice «este objeto existe y es este». Una cita que no resuelve a ningun objeto
no es un detalle tipografico —es una afirmacion falsa dentro de la cadena de
custodia—, y hasta ahora nada la comprobaba. Este modulo lo comprueba.

La regla es simple y falla cerrado: **todo SHA de cuarenta caracteres citado
en `docs/architecture/` o en `artifacts/` debe resolver a un objeto del
repositorio**, salvo dos clases de excepcion, ambas inventariadas aqui con su
motivo:

1. **Hashes que por construccion no son objetos almacenados.** La huella
   canonica de una ficha es el SHA-1 del blob de su *forma canonica* —el JSON
   ordenado sin el campo de huella—, un contenido que nunca se escribe como
   fichero. Que Git no lo encuentre es lo correcto, y no exime de recomputarlo:
   eso lo comprueban las pruebas de la ficha.
2. **Erratas declaradas.** Una cita erronea publicada en evidencia
   **inmutable** no se puede corregir en el sitio sin reescribir la evidencia,
   que es justo lo que la custodia prohibe. Se corrige con una **fe de
   erratas** y un documento sucesor, y la excepcion queda **anclada al blob
   del documento afectado**: si alguien lo editara, su blob cambiaria, la
   excepcion caducaria y la comprobacion volveria a fallar.

Lo que este modulo NO hace: no reescribe evidencia, no mide, no toca el arnes
congelado y no exime a ninguna cita futura. Una errata nueva en un documento
nuevo falla, porque no esta inventariada.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

#: Un SHA-1 hexadecimal completo, aislado como palabra.
SHA40: Final = re.compile(r"\b[0-9a-f]{40}\b")

#: Donde se buscan citas de identidad: gobierno y evidencia.
AMBITOS: Final[tuple[str, ...]] = ("docs/architecture", "artifacts")
EXTENSIONES: Final[tuple[str, ...]] = (".md", ".json")

FE_DE_ERRATAS: Final = "SIRIUS_0.2_ADR_002_FE_DE_ERRATAS_01_IDENTIDAD_GIT_v1.0.md"


@dataclass(frozen=True, slots=True)
class ErrataDeIdentidad:
    """Una cita de identidad erronea, declarada y corregida sin reescribirla."""

    sha_erroneo: str
    sha_correcto: str
    #: Documento con la cita vinculante erronea. Inmutable: no se reescribe.
    documento_afectado: str
    #: Ancla de la excepcion. Si el documento cambia, la excepcion caduca.
    blob_del_documento: str
    #: Documentos cuya funcion es DECLARAR la errata; pueden nombrarla.
    documentos_que_la_declaran: tuple[str, ...]
    motivo: str


#: Errata 01: el informe humano v0.2 transcribio mal el SHA completo del
#: commit de ejecucion. Ambos comparten el prefijo abreviado `5797f52`, y por
#: eso ninguna lectura humana lo detecto; la identidad vinculante es el SHA
#: completo. El artefacto de muestras v0.2 lleva el SHA CORRECTO, porque lo
#: obtuvo de Git en tiempo de ejecucion en vez de transcribirlo.
ERRATAS: Final[tuple[ErrataDeIdentidad, ...]] = (
    ErrataDeIdentidad(
        sha_erroneo="5797f5205cdb3054921054461f77dbdb8f550af4",
        sha_correcto="5797f523c9d4f0e0d3f99599493b6e3167b29f9d",
        documento_afectado=(
            "artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.2_PROPUESTO.md"
        ),
        blob_del_documento="dac5155914d55b7e1e294ebca1d16f0ef6e6e656",
        documentos_que_la_declaran=(
            f"docs/architecture/{FE_DE_ERRATAS}",
            "artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.2.1_PROPUESTO.md",
            "experiments/adr002/rederivation/custody_errata.py",
            # El acta de aprobacion de TOL-208 cita la errata para dejar
            # constancia de que se corrigio: una aprobacion que no dijera QUE
            # cita era erronea obligaria a salir del acta para entenderla.
            "docs/architecture/SIRIUS_0.2_ADR_002_TOL_208_APROBACION_v1.0.md",
        ),
        motivo=(
            "transcripcion humana del SHA completo del commit de ejecucion de la "
            "repeticion unica del §6.8; no afecta muestras, cifras, metodo, blobs, "
            "veredictos ni el resultado del §6.9"
        ),
    ),
)


#: Hashes citados que NO son objetos del repositorio por construccion, con el
#: motivo por el que su ausencia es correcta y no una errata.
HASHES_NO_ALMACENADOS: Final[Mapping[str, str]] = {
    "d47a767e61b30729e15f48c9924413f6fddc9429": (
        "huella canonica de la ficha T0-control v1: SHA-1 del blob de la forma "
        "canonica de la ficha excluido el propio campo de huella, un contenido que "
        "nunca se escribe como fichero. Su correccion se comprueba recomputandola, "
        "no buscandola en el repositorio"
    ),
    "00571890294bcd18748e2ee600eb43bad1b92f80": (
        "huella canonica que la ficha ADR002-A v1 tuvo mientras estuvo CONGELADA: "
        "misma naturaleza que la anterior —SHA-1 de una forma canonica que nunca se "
        "escribe como fichero— y misma verificacion, recomputarla. Se conserva "
        "inventariada porque el paquete de correccion 01 la cita como la huella de la "
        "ficha que declara defectuosa, y esa cita es historia que no se reescribe"
    ),
    "8d8c21b6afd1d32ee612dd14199ab9c5605bfb96": (
        "huella canonica de la ficha ADR002-A v1 ya SUSTITUIDA. El estado forma parte "
        "de la forma canonica, de modo que marcarla sustituida —lo que el contrato "
        "obliga a hacer al emitir una sucesora— recomputa su huella. Ningun limite y "
        "ninguna declaracion de la v1 cambiaron: el contenido original sigue siendo el "
        "blob 1a96f535250bce643e8ccf2edb0362b3ec9320fe del commit b96e6ea"
    ),
    "4ed820fab545dd9154ce078349c214f870baecd1": (
        "huella canonica que la ficha ADR002-A v2 tuvo mientras estuvo CONGELADA: "
        "misma naturaleza y misma verificacion que las anteriores. La v2 quedo "
        "SUSTITUIDA por el paquete de correccion 02 y la vigente de ADR002-A es la "
        "v3; esta entrada se conserva porque el acta historica de preparacion de la "
        "v2 la cita, y esa cita es historia que no se reescribe"
    ),
    "c1ca17a7f5345b4cec2a0ea63dac6c8b1bb6e5fd": (
        "huella canonica que la ficha ADR002-B v1 tuvo mientras estuvo CONGELADA: SHA-1 "
        "del blob de la forma canonica excluido el propio campo de huella. Se conserva "
        "inventariada porque el paquete de correccion 02 y la fe de erratas 03 la citan "
        "como la huella de la ficha cuyo defecto declaran; esa cita es historia"
    ),
    "95be1370e8279eea76fd92ade2db0545e5a417dc": (
        "huella canonica de la ficha ADR002-A v2 ya SUSTITUIDA por el paquete de "
        "correccion 02: el estado forma parte de la forma canonica y marcarla "
        "sustituida recomputa la huella. Ningun limite ni declaracion de la v2 cambio; "
        "su contenido congelado sigue integro en el historial del repositorio"
    ),
    "427905a06f6c12666a09c73b8720e229f17eeef3": (
        "huella canonica de la ficha ADR002-A v3, la vigente tras la extension neutral "
        "del puerto comun del paquete de correccion 02: misma naturaleza y misma "
        "verificacion que las anteriores, recomputarla sobre la forma canonica"
    ),
    "351413b91dcb0d7b37d184bd7779fb2f6a56d0a5": (
        "huella canonica de la ficha ADR002-B v1 ya SUSTITUIDA por el paquete de "
        "correccion 02: solo su campo de estado cambio y la huella se recomputa de el; "
        "el contenido congelado original permanece integro en el historial"
    ),
    "c98ef457273055f1362d2939d48bba096f62cdc2": (
        "huella canonica que la ficha ADR002-B v2 tuvo mientras estuvo CONGELADA, "
        "tras la correccion de la materializacion por identidad: se conserva "
        "inventariada porque el acta de reaprobacion de A v3 y el paquete de "
        "correccion 03 la citan; esa cita es historia que no se reescribe"
    ),
    "11b2a881a1126e77fcd6196ba7837274ee426918": (
        "huella canonica de la ficha ADR002-B v2 ya SUSTITUIDA por el paquete de "
        "correccion 03: solo su campo de estado cambio y la huella se recomputa de "
        "el; el contenido congelado original permanece integro en el historial"
    ),
    "ef2bfb137c5d67450e7ade7b4a934e0a42744800": (
        "huella canonica que la ficha ADR002-B v3 tuvo mientras estuvo CONGELADA, "
        "tras la validacion logica del sidecar: se conserva inventariada porque el "
        "paquete de correccion 04 la cita como la huella de la ficha cuyo defecto "
        "de minimizacion declara; esa cita es historia que no se reescribe"
    ),
    "1c639d37ca6af5d5d6921c4695ba049325f01270": (
        "huella canonica de la ficha ADR002-B v3 ya SUSTITUIDA por el paquete de "
        "correccion 04: solo su campo de estado cambio y la huella se recomputa de "
        "el; el contenido congelado original permanece integro en el historial"
    ),
    "5c9eab540e74b4290635dc7c6d0b79daf76d86aa": (
        "huella canonica que la ficha ADR002-B v4 tuvo mientras estuvo CONGELADA, "
        "tras la minimizacion de los mensajes de apertura: se conserva "
        "inventariada porque la fe de erratas 04 la cita como la huella de la "
        "ficha cuyas declaraciones falsifica; esa cita es historia"
    ),
    "28017d9502ce9850071426329f0b2e75e2bd7826": (
        "huella canonica de la ficha ADR002-B v4 ya SUSTITUIDA por la fe de "
        "erratas 04: solo su campo de estado cambio y la huella se recomputa de "
        "el; el contenido congelado original permanece integro en el historial"
    ),
    "b27866b1278f37473fa6151ab7f26df7386bcd81": (
        "huella canonica de la ficha ADR002-B v5, la vigente tras las cotas de "
        "longitud y representabilidad que cierran los cuatro escapes sin tipar "
        "de la fe de erratas 04: misma naturaleza y misma verificacion que las "
        "anteriores, recomputarla sobre la forma canonica"
    ),
    "b57ad7b24c7f0232d45540cde73294e2d68e02ef": (
        "captura de entorno de ADR-001: HEAD observado de la rama historica "
        "fix/chat-history-layout al ejecutar los spikes, registrado como "
        "observacion ambiental y no como cita de identidad vinculante de ADR-002; "
        "esa rama no forma parte del historial de evidence/adr001-spikes"
    ),
}


def blob_git_de(ruta: Path) -> str:
    """Blob Git del fichero, para anclar la excepcion de una errata."""
    completado = subprocess.run(
        ["git", "hash-object", str(ruta)],
        capture_output=True,
        text=True,
        check=False,
    )
    return completado.stdout.strip()


def existencia_real(raiz: Path) -> Callable[[Sequence[str]], dict[str, bool]]:
    """Comprueba en UNA invocacion si cada SHA resuelve a un objeto Git."""

    def existen(shas: Sequence[str]) -> dict[str, bool]:
        if not shas:
            return {}
        completado = subprocess.run(
            ["git", "cat-file", "--batch-check"],
            input="\n".join(shas) + "\n",
            cwd=str(raiz),
            capture_output=True,
            text=True,
            check=False,
        )
        resultado: dict[str, bool] = {}
        for linea in completado.stdout.splitlines():
            partes = linea.split()
            if not partes:
                continue
            resultado[partes[0]] = len(partes) > 1 and partes[1] != "missing"
        return {sha: resultado.get(sha, False) for sha in shas}

    return existen


def citas_de_identidad(raiz: Path) -> dict[str, list[str]]:
    """``sha -> rutas`` de todo SHA completo citado en gobierno y evidencia."""
    citas: dict[str, list[str]] = {}
    for ambito in AMBITOS:
        for ruta in sorted((raiz / ambito).rglob("*")):
            if not ruta.is_file() or ruta.suffix not in EXTENSIONES:
                continue
            try:
                texto = ruta.read_text(encoding="utf-8")
            except OSError, UnicodeDecodeError:
                continue
            relativa = str(ruta.relative_to(raiz))
            for sha in sorted(set(SHA40.findall(texto))):
                citas.setdefault(sha, []).append(relativa)
    return citas


def _errata_de(sha: str) -> ErrataDeIdentidad | None:
    for errata in ERRATAS:
        if errata.sha_erroneo == sha:
            return errata
    return None


def fallos_de_identidad(
    raiz: Path,
    *,
    existen: Callable[[Sequence[str]], dict[str, bool]] | None = None,
) -> list[str]:
    """Toda cita de identidad resuelve, o esta inventariada. Falla cerrado."""
    citas = citas_de_identidad(raiz)
    comprobar = existencia_real(raiz) if existen is None else existen
    presencia = comprobar(sorted(citas))

    fallos: list[str] = []
    for sha, rutas in sorted(citas.items()):
        if presencia.get(sha):
            continue
        if sha in HASHES_NO_ALMACENADOS:
            continue
        errata = _errata_de(sha)
        if errata is None:
            fallos.append(
                f"cita de identidad que no resuelve a ningun objeto Git: {sha} "
                f"en {rutas}. Una cita rota es una afirmacion falsa de custodia: "
                f"corrijase la cita, o declarese como errata con su fe de erratas"
            )
            continue
        # La excepcion solo cubre el documento afectado —con su blob exacto— y
        # los documentos cuya funcion es declarar la errata.
        permitidas = {errata.documento_afectado, *errata.documentos_que_la_declaran}
        intrusas = [r for r in rutas if r not in permitidas]
        if intrusas:
            fallos.append(
                f"la errata declarada {sha} aparece en documentos no inventariados: "
                f"{intrusas}. Una excepcion de custodia no se hereda: declarese"
            )
        if errata.documento_afectado in rutas:
            observado = blob_git_de(raiz / errata.documento_afectado)
            if observado != errata.blob_del_documento:
                fallos.append(
                    f"el documento con la errata {sha} ha cambiado: "
                    f"{errata.documento_afectado} ({observado} != "
                    f"{errata.blob_del_documento}). La evidencia no se reescribe, y "
                    f"la excepcion queda anclada a su blob exacto"
                )
    return fallos


def fallos_de_las_erratas_declaradas(
    raiz: Path,
    *,
    existen: Callable[[Sequence[str]], dict[str, bool]] | None = None,
) -> list[str]:
    """Cada errata declara un SHA correcto que SI debe existir, y su rastro."""
    comprobar = existencia_real(raiz) if existen is None else existen
    presencia = comprobar([e.sha_correcto for e in ERRATAS])
    fallos: list[str] = []
    for errata in ERRATAS:
        if not presencia.get(errata.sha_correcto):
            fallos.append(f"el SHA correcto de una errata no existe: {errata.sha_correcto}")
        if errata.sha_erroneo == errata.sha_correcto:
            fallos.append(f"errata vacia: {errata.sha_erroneo}")
        for documento in (errata.documento_afectado, *errata.documentos_que_la_declaran):
            if not (raiz / documento).is_file():
                fallos.append(f"documento inventariado inexistente: {documento}")
    return fallos
