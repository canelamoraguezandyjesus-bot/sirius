"""Verificacion de fichas de candidato (ADR002-TOL-210, paquete 09).

**No mide y no ejecuta ningun candidato.** Comprueba lo que TOL-210 exige y
que hasta ahora no comprobaba nadie:

    uv run python -m experiments.adr002.cards.verify_cards --check
    uv run python -m experiments.adr002.cards.verify_cards \\
        --check --execution <SHA> --candidate T1 --version 1

Sin ``--execution`` valida las fichas presentes y su congelacion. Con
``--execution`` decide ademas si una ejecucion concreta seria **utilizable
como evidencia**, contrastandola con la ficha que cita.

Lo que hace cumplir, en este orden y fallando cerrado:

1. las **plantillas anteriores** siguen intactas —se versionan, no se editan—;
2. cada ficha cumple el **contenido minimo** de TOL-210;
3. la **huella declarada** coincide con el blob real de la ficha;
4. la ficha esta **confirmada** en el commit que declara;
5. ese commit es **ancestro estricto** del commit que ejecuta.

El punto 5 es el que convierte «congelada antes de la primera ejecucion» en
algo comprobable. Una fecha escrita en el documento no prueba anterioridad;
una relacion de ancestro en el grafo de Git, si.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from experiments.adr002.cards import card_protocol as cp
from experiments.adr002.cards import schema_card_v0_1 as esquema

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

#: Donde viven las fichas. Una por candidato y version.
DIRECTORIO_FICHAS: Final = "artifacts/adr002_cards"

CODIGO_OK: Final = 0
CODIGO_BLOQUEADO: Final = 2
CODIGO_SIN_CHECK: Final = 3


class VerificacionBloqueadaError(RuntimeError):
    """Una precondicion de custodia no se cumple."""


# --------------------------------------------------------------------------
# Acceso a Git, aislado para poder inyectarlo en las pruebas
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DependenciasVerificacion:
    """Dependencias externas del recorrido, inyectables en las pruebas."""

    entorno_custodia: cp.EntornoCustodia
    listar_fichas: Callable[[], Sequence[str]]
    leer_ficha: Callable[[str], bytes]
    blob_en_commit: Callable[[str, str], str | None]


def _rc(orden: Sequence[str], raiz: Path) -> bool:
    return (
        subprocess.run(
            list(orden), cwd=str(raiz), capture_output=True, text=True, check=False
        ).returncode
        == 0
    )


def _git(argumentos: Sequence[str], raiz: Path) -> str:
    completado = subprocess.run(
        ["git", *argumentos], cwd=str(raiz), capture_output=True, text=True, check=False
    )
    if completado.returncode != 0:
        msg = f"git {' '.join(argumentos)} fallo: {completado.stderr.strip()}"
        raise VerificacionBloqueadaError(msg)
    return completado.stdout.strip()


def dependencias_reales(raiz: Path | None = None) -> DependenciasVerificacion:
    """Dependencias sobre el repositorio real."""
    destino = RAIZ_REPOSITORIO if raiz is None else raiz

    def leer_bytes(ruta: str) -> bytes:
        return (destino / ruta).read_bytes()

    def blob_en_commit(sha: str, ruta: str) -> str | None:
        completado = subprocess.run(
            ["git", "rev-parse", f"{sha}:{ruta}"],
            cwd=str(destino),
            capture_output=True,
            text=True,
            check=False,
        )
        if completado.returncode != 0:
            return None
        return completado.stdout.strip() or None

    def listar_fichas() -> Sequence[str]:
        carpeta = destino / DIRECTORIO_FICHAS
        if not carpeta.is_dir():
            return ()
        return tuple(sorted(f"{DIRECTORIO_FICHAS}/{p.name}" for p in carpeta.glob("*.json")))

    entorno = cp.EntornoCustodia(
        leer_bytes=leer_bytes,
        es_ancestro=lambda a, b: _rc(["git", "merge-base", "--is-ancestor", a, b], destino),
        existe_commit=lambda sha: _rc(["git", "cat-file", "-e", f"{sha}^{{commit}}"], destino),
        head=lambda: _git(["rev-parse", "HEAD"], destino),
        arbol_limpio=lambda: _git(["status", "--porcelain"], destino) == "",
        diff_vacio=lambda desde, hasta, rutas: _rc(
            ["git", "diff", "--quiet", f"{desde}..{hasta}", "--", *rutas], destino
        ),
        blob_en_commit=blob_en_commit,
    )
    return DependenciasVerificacion(
        entorno_custodia=entorno,
        listar_fichas=listar_fichas,
        leer_ficha=leer_bytes,
        blob_en_commit=blob_en_commit,
    )


# --------------------------------------------------------------------------
# Carga y comprobacion de una ficha
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FichaExaminada:
    """Una ficha leida del disco, con su blob real y sus fallos."""

    ruta: str
    documento: Mapping[str, Any] | None
    blob_real: str
    fallos: tuple[str, ...]

    @property
    def conforme(self) -> bool:
        return not self.fallos


def examinar_ficha(
    ruta: str, crudo: bytes, *, blob_en_commit: Callable[[str, str], str | None]
) -> FichaExaminada:
    """Valida una ficha y comprueba su congelacion. Falla cerrado."""
    blob_real = cp.blob_git(crudo)
    try:
        documento = json.loads(crudo.decode("utf-8"))
    except Exception as exc:
        return FichaExaminada(
            ruta=ruta,
            documento=None,
            blob_real=blob_real,
            fallos=(f"{ruta}: no es JSON valido ({type(exc).__name__})",),
        )
    if not isinstance(documento, dict):
        return FichaExaminada(
            ruta=ruta, documento=None, blob_real=blob_real, fallos=(f"{ruta}: no es un objeto",)
        )

    fallos = [f"{ruta}: {f}" for f in esquema.fallos_ficha(documento)]

    congelacion = documento.get("congelacion")
    if isinstance(congelacion, Mapping):
        declarada = congelacion.get("huella")
        # La huella no es un adorno: es lo que una ejecucion cita para
        # ampararse en esta ficha. Si no coincide con la recomputada sobre el
        # contenido normativo, la referencia apuntaria a otra cosa.
        esperada = cp.huella_canonica(documento)
        if declarada != esperada:
            fallos.append(
                f"{ruta}: la huella declarada ({declarada}) no recomputa sobre el contenido "
                f"normativo de la ficha ({esperada})"
            )
        if congelacion.get("ruta") != ruta:
            fallos.append(f"{ruta}: congelacion.ruta declara otra ubicacion")
        commit = congelacion.get("commit")
        if isinstance(commit, str):
            registrado = blob_en_commit(commit, ruta)
            if registrado is None:
                fallos.append(
                    f"{ruta}: la ficha no esta confirmada en el commit que declara ({commit})"
                )
            elif registrado != blob_real:
                fallos.append(
                    f"{ruta}: la ficha difiere de su version confirmada en {commit} "
                    f"(arbol {blob_real} != commit {registrado})"
                )

    return FichaExaminada(ruta=ruta, documento=documento, blob_real=blob_real, fallos=tuple(fallos))


def confirmadas_desde(examinadas: Sequence[FichaExaminada]) -> list[cp.FichaConfirmada]:
    """Convierte las fichas conformes en el registro que consulta la regla."""
    salida: list[cp.FichaConfirmada] = []
    for ficha in examinadas:
        if not ficha.conforme or ficha.documento is None:
            continue
        identidad = ficha.documento["identidad"]
        congelacion = ficha.documento["congelacion"]
        salida.append(
            cp.FichaConfirmada(
                candidato=str(identidad["candidato"]),
                version=int(identidad["version"]),
                huella=str(congelacion["huella"]),
                commit=str(congelacion["commit"]),
                estado=str(ficha.documento["estado"]),
            )
        )
    return salida


def fallos_de_unicidad(confirmadas: Sequence[cp.FichaConfirmada]) -> list[str]:
    """Una sola ficha CONGELADA por candidato, y versiones sin duplicar."""
    fallos: list[str] = []
    vistas: dict[tuple[str, int], int] = {}
    for ficha in confirmadas:
        clave = (ficha.candidato, ficha.version)
        vistas[clave] = vistas.get(clave, 0) + 1
    for (candidato, version), cuantas in sorted(vistas.items()):
        if cuantas > 1:
            fallos.append(f"{candidato}: {cuantas} fichas con la version {version}")
    for candidato in cp.CANDIDATOS:
        vigentes = [
            f for f in confirmadas if f.candidato == candidato and f.estado == cp.ESTADO_CONGELADA
        ]
        if len(vigentes) > 1:
            versiones = sorted(f.version for f in vigentes)
            fallos.append(
                f"{candidato}: {len(vigentes)} fichas CONGELADA a la vez (versiones "
                f"{versiones}); una version sucesora obliga a marcar SUSTITUIDA la anterior"
            )
    return fallos


# --------------------------------------------------------------------------
# Recorrido completo
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Resultado:
    """Resultado del recorrido completo de verificacion."""

    fallos: tuple[str, ...]
    fichas: tuple[FichaExaminada, ...]
    confirmadas: tuple[cp.FichaConfirmada, ...]
    veredicto: cp.Veredicto | None
    puertas: Mapping[str, bool]
    controles: Mapping[str, bool] | None

    @property
    def conforme(self) -> bool:
        return not self.fallos


def estado_de_controles(
    *,
    plantillas_intactas: bool,
    particion_acreditada: bool,
    fichas: Sequence[FichaExaminada],
    confirmadas: Sequence[cp.FichaConfirmada],
    veredicto: cp.Veredicto | None,
    es_ancestro: Callable[[str, str], bool],
) -> dict[str, bool]:
    """Deriva el estado de los controles bloqueantes desde lo observado.

    Los controles sobre el CONTENIDO de una ficha se derivan de que ninguna
    ficha presente haya producido fallos: el esquema es quien los comprueba
    uno a uno, y este recorrido recoge su veredicto. Los controles sobre la
    ANTERIORIDAD se sondean, porque no basta con que ninguna ficha falle: hay
    que comprobar que una referencia sin respaldo **si** falla.
    """
    conformes = all(f.conforme for f in fichas)

    # Sondeo del ultimo control: una ejecucion que cita una ficha inexistente
    # tiene que salir NO_UTILIZABLE. Sin este sondeo, «ninguna ficha fallo»
    # seria compatible con un verificador que nunca denuncia nada.
    sondeo = cp.admisibilidad(
        cp.ReferenciaEjecucion(
            candidato=cp.ALTERNATIVAS[0],
            version=0,
            huella="0" * 40,
            commit_de_ejecucion="0" * 40,
        ),
        confirmadas,
        es_ancestro=es_ancestro,
    )
    denuncia = sondeo.motivo == cp.MOTIVO_SIN_FICHA

    anterioridad = veredicto is None or veredicto.motivo != cp.MOTIVO_FICHA_POSTERIOR

    return {
        "plantilla_anterior_intacta": plantillas_intactas,
        "contenido_minimo_completo": conformes,
        "conjuntos_cerrados": conformes,
        "sin_marcadores_vacios": conformes,
        "presupuesto_de_tol207_citado": conformes,
        "perfil_de_tol209_citado": conformes,
        "once_sesiones_exigidas": conformes,
        "coste_local_coherente": conformes,
        "coste_externo_no_sumado": conformes,
        "puertas_previas_declaradas": conformes,
        "papel_de_control_reservado_a_t0": conformes and particion_acreditada,
        "senal_tardia_coherente_con_la_alternativa": conformes and particion_acreditada,
        "anterioridad_comprobada_contra_git": anterioridad,
        "ejecucion_sin_ficha_no_utilizable": denuncia,
    }


def verificar(
    dependencias: DependenciasVerificacion,
    *,
    referencia: cp.ReferenciaEjecucion | None = None,
) -> Resultado:
    """Recorrido completo. Falla cerrado y no modifica nada."""
    entorno = dependencias.entorno_custodia
    fallos_plantillas = cp.fallos_plantillas_anteriores(entorno)
    fallos_particion = cp.fallos_documentos_de_particion(entorno)
    fallos = [*fallos_plantillas, *fallos_particion]

    examinadas: list[FichaExaminada] = []
    for ruta in dependencias.listar_fichas():
        try:
            crudo = dependencias.leer_ficha(ruta)
        except OSError:
            fallos.append(f"{ruta}: ilegible")
            continue
        examinadas.append(examinar_ficha(ruta, crudo, blob_en_commit=dependencias.blob_en_commit))

    for ficha in examinadas:
        fallos.extend(ficha.fallos)

    confirmadas = confirmadas_desde(examinadas)
    fallos.extend(fallos_de_unicidad(confirmadas))

    # El estado de las puertas se DERIVA de las actas que existen, no se
    # declara. TOL-208 y TOL-210 salen False mientras no las apruebe la suya.
    puertas = cp.estado_de_las_puertas(entorno)

    veredicto: cp.Veredicto | None = None
    if referencia is not None:
        veredicto = cp.admisibilidad(referencia, confirmadas, es_ancestro=entorno.es_ancestro)
        if not veredicto.utilizable:
            fallos.append(
                f"la ejecucion {referencia.commit_de_ejecucion} no es utilizable como "
                f"evidencia: {veredicto.motivo}"
            )
        ejecutable = cp.ejecutabilidad(referencia.candidato, confirmadas, puertas=puertas)
        if not ejecutable.utilizable:
            fallos.append(f"{referencia.candidato} no es ejecutable: {ejecutable.motivo}")

    # Los controles se publican solo cuando hay algo que controlar. Con cero
    # fichas serian vacuamente ciertos, y publicar catorce True sin haber
    # mirado ninguna ficha seria justo el defecto que este paquete corrige.
    controles = (
        estado_de_controles(
            plantillas_intactas=not fallos_plantillas,
            particion_acreditada=not fallos_particion,
            fichas=examinadas,
            confirmadas=confirmadas,
            veredicto=veredicto,
            es_ancestro=entorno.es_ancestro,
        )
        if examinadas
        else None
    )
    if controles is not None:
        resultado_controles = cp.evaluar_controles(controles)
        if not resultado_controles.valido:
            fallos.append(f"controles bloqueantes fallidos: {sorted(resultado_controles.fallos)}")

    return Resultado(
        fallos=tuple(dict.fromkeys(fallos)),
        fichas=tuple(examinadas),
        confirmadas=tuple(confirmadas),
        veredicto=veredicto,
        puertas=puertas,
        controles=controles,
    )


# --------------------------------------------------------------------------
# Interfaz de linea de ordenes
# --------------------------------------------------------------------------


def construir_parser() -> argparse.ArgumentParser:
    """Parser sin efectos secundarios."""
    parser = argparse.ArgumentParser(
        prog="verify_cards",
        description=(
            "Verifica las fichas de candidato de ADR002-TOL-210. No mide, no ejecuta "
            "candidatos y no escribe nada."
        ),
    )
    parser.add_argument("--check", action="store_true", help="ejecuta la verificacion")
    parser.add_argument("--plan", action="store_true", help="imprime las reglas sin verificar")
    parser.add_argument("--execution", dest="execution", default=None, help="SHA de la ejecucion")
    parser.add_argument("--candidate", dest="candidate", default=None, help="ID del candidato")
    parser.add_argument("--version", dest="version", type=int, default=None, help="version citada")
    parser.add_argument("--fingerprint", dest="fingerprint", default=None, help="huella citada")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    dependencias: DependenciasVerificacion | None = None,
) -> int:
    """Punto de entrada. No escribe nada en ningun caso."""
    args = construir_parser().parse_args(argv)

    if args.plan and not args.check:
        print(f"plantilla vigente: {cp.PLANTILLA}")
        print(f"registro: {cp.REGISTRO}")
        print(f"protocolo: {cp.PROTOCOLO}")
        print(f"candidatos con ficha propia: {list(cp.CANDIDATOS)}")
        print(f"presupuesto TOL-207 citado: {cp.PRESUPUESTO_TOL207_B} B")
        print(f"perfil TOL-209 citado: SM={cp.SM_NS} ns · U50={cp.U50_NS} ns")
        print(f"sesiones exigidas: {cp.SESIONES_EXIGIDAS} (exactamente)")
        print(f"controles bloqueantes: {len(cp.CONTROLES_BLOQUEANTES)}")
        return CODIGO_OK

    if not args.check:
        print("verify_cards no verifica sin --check.")
        return CODIGO_SIN_CHECK

    referencia: cp.ReferenciaEjecucion | None = None
    if args.execution is not None:
        if not (args.candidate and args.version is not None and args.fingerprint):
            print("--execution exige ademas --candidate, --version y --fingerprint")
            return CODIGO_BLOQUEADO
        referencia = cp.ReferenciaEjecucion(
            candidato=args.candidate,
            version=args.version,
            huella=args.fingerprint,
            commit_de_ejecucion=args.execution,
        )

    deps = dependencias_reales() if dependencias is None else dependencias
    try:
        resultado = verificar(deps, referencia=referencia)
    except Exception as exc:
        print(f"verificacion bloqueada: {exc}")
        return CODIGO_BLOQUEADO

    if not resultado.conforme:
        print("verificacion de fichas BLOQUEADA:")
        for fallo in resultado.fallos:
            print(f"  - {fallo}")
        return CODIGO_BLOQUEADO

    print(f"fichas conformes: {len(resultado.fichas)}")
    for ficha in resultado.confirmadas:
        print(f"  · {ficha.candidato} v{ficha.version} · {ficha.estado} · {ficha.huella}")
    pendientes = sorted(p for p, ok in resultado.puertas.items() if not ok)
    print(f"puertas de arranque pendientes: {pendientes or 'ninguna'}")
    if resultado.controles is None:
        print("controles bloqueantes: sin fichas que controlar")
    else:
        print(
            f"controles bloqueantes: {sum(resultado.controles.values())}/{len(resultado.controles)}"
        )
    if resultado.veredicto is not None:
        print(f"ejecucion citada: {resultado.veredicto.resultado}")
    print("ADR002-TOL-210 no queda satisfecha por esta comprobacion: la satisface su acta.")
    return CODIGO_OK


if __name__ == "__main__":
    raise SystemExit(main())
