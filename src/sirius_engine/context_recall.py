"""``contexto.recuperar`` v0: tres proveedores deterministas (A3, incidencia #193).

«¿Qué pasó con X?» se responde con **referencias** -ficheros, comentarios de
incidencia, commits-, nunca con una afirmación sintetizada: v0 no interpreta
ni resume, solo localiza y cita (requisito 4). Cada proveedor es una función
pura sobre datos ya leídos; la parte que sí toca el mundo (sistema de
ficheros, ``git log``, la vía GitHub) vive en adapters delgados e
inyectables, para que las pruebas puedan operar sobre datos fijos sin acceder
a la red (requisito 7).

Los tres proveedores:

1. **Árbol del repositorio** (:func:`buscar_en_arbol_repo`): ficheros, ADRs,
   documentación.
2. **Incidencias y PR** (:func:`buscar_en_incidencias`): reutiliza
   :class:`~sirius_engine.ports.github_mirror.GitHubMirrorPort` -el mismo
   puerto del espejo- y el filtro de autor de confianza de
   :mod:`sirius_engine.mirror_projection`, así que una respuesta de
   ``contexto.recuperar`` nunca cita un comentario que el espejo mismo
   descartaría por no confiable.
3. **Historial de git** (:func:`buscar_en_historial_git`).

Un fallo de lectura en un proveedor NUNCA se convierte en "no hay
referencias" (mismo requisito 2 que el espejo): se acumula en
``proveedores_fallidos`` y se devuelve junto a lo que sí se pudo encontrar,
para que quien reciba el contexto sepa que la cobertura es parcial.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sirius_engine.domain.mirror import EspejoIlegibleError, OrigenLectura
from sirius_engine.mirror_projection import es_autor_de_confianza
from sirius_engine.ports.github_mirror import GitHubMirrorPort, LecturaEstado

_EXTENSIONES_POR_DEFECTO: tuple[str, ...] = (".md", ".py", ".sh", ".yml", ".yaml")
_DIRECTORIOS_EXCLUIDOS = {".git", "__pycache__", "node_modules", ".venv", "dist", "build"}


@dataclass(frozen=True, slots=True)
class Referencia:
    """Una cita concreta que sostiene la respuesta: nunca una afirmación suelta."""

    tipo: str
    identificador: str
    fragmento: str


@dataclass(frozen=True, slots=True)
class ContextoRecuperado:
    consulta: str
    referencias: tuple[Referencia, ...]
    proveedores_fallidos: tuple[str, ...]
    origen: OrigenLectura


def _fragmento(texto: str, consulta_normalizada: str, *, contexto: int = 40) -> str:
    indice = texto.casefold().find(consulta_normalizada)
    if indice == -1:
        return texto.strip()[:80]
    inicio = max(0, indice - contexto)
    fin = min(len(texto), indice + len(consulta_normalizada) + contexto)
    return texto[inicio:fin].strip()


# --- Proveedor 1: árbol del repositorio -------------------------------------


def buscar_en_arbol_repo(
    raiz: Path, consulta: str, *, extensiones: tuple[str, ...] = _EXTENSIONES_POR_DEFECTO
) -> tuple[tuple[Referencia, ...], tuple[str, ...]]:
    """Búsqueda determinista de ``consulta`` en el árbol del repositorio.

    Un fichero elegible que no se puede leer (desaparece, pierde permisos,
    cualquier otro ``OSError``) no se salta en silencio: su ruta se acumula
    en el segundo elemento devuelto, para no convertir "no pude leer" en "no
    había nada" (mismo contrato que :func:`buscar_en_incidencias`).
    """
    consulta_normalizada = consulta.casefold()
    encontradas: list[Referencia] = []
    fallidas: list[str] = []
    for ruta in sorted(raiz.rglob("*")):
        relativa = ruta.relative_to(raiz)
        if _DIRECTORIOS_EXCLUIDOS & set(relativa.parts):
            continue
        if not ruta.is_file() or ruta.suffix not in extensiones:
            continue
        try:
            texto = ruta.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            fallidas.append(f"arbol:{relativa}")
            continue
        for numero_linea, linea in enumerate(texto.splitlines(), start=1):
            if consulta_normalizada in linea.casefold():
                encontradas.append(
                    Referencia(
                        tipo="fichero",
                        identificador=f"{relativa}:{numero_linea}",
                        fragmento=linea.strip(),
                    )
                )
    encontradas.sort(key=lambda r: r.identificador)
    fallidas.sort()
    return tuple(encontradas), tuple(fallidas)


# --- Proveedor 2: incidencias y PR ------------------------------------------


def buscar_en_incidencias(
    port: GitHubMirrorPort, *, repo: str, numeros: Sequence[int], consulta: str
) -> tuple[tuple[Referencia, ...], tuple[str, ...]]:
    """Busca ``consulta`` en el cuerpo y los comentarios de confianza de cada incidencia.

    Devuelve, junto a las referencias, la lista de proveedores que no se
    pudieron leer (``"incidencia:<numero>:cuerpo"``/``"...:comentarios"``):
    una lectura caída de una incidencia no reduce silenciosamente el
    resultado de las demás, pero tampoco se disfraza de "sin referencias
    aquí".
    """
    consulta_normalizada = consulta.casefold()
    encontradas: list[Referencia] = []
    fallidas: list[str] = []
    for numero in numeros:
        cuerpo = port.leer_cuerpo(repo=repo, numero=numero)
        if cuerpo.estado is not LecturaEstado.OK or cuerpo.cuerpo is None:
            fallidas.append(f"incidencia:{numero}:cuerpo")
        elif consulta_normalizada in cuerpo.cuerpo.casefold():
            encontradas.append(
                Referencia(
                    tipo="incidencia",
                    identificador=f"{repo}#{numero}:cuerpo",
                    fragmento=_fragmento(cuerpo.cuerpo, consulta_normalizada),
                )
            )

        comentarios = port.leer_comentarios(repo=repo, numero=numero)
        if comentarios.estado is not LecturaEstado.OK or comentarios.comentarios is None:
            fallidas.append(f"incidencia:{numero}:comentarios")
            continue
        for indice, comentario in enumerate(comentarios.comentarios):
            if not es_autor_de_confianza(comentario):
                continue
            if consulta_normalizada in comentario.cuerpo.casefold():
                encontradas.append(
                    Referencia(
                        tipo="incidencia",
                        identificador=f"{repo}#{numero}:comentario:{indice}",
                        fragmento=_fragmento(comentario.cuerpo, consulta_normalizada),
                    )
                )
    encontradas.sort(key=lambda r: r.identificador)
    return tuple(encontradas), tuple(fallidas)


# --- Proveedor 3: historial de git ------------------------------------------


@dataclass(frozen=True, slots=True)
class EntradaGitLog:
    sha: str
    asunto: str
    cuerpo: str


_REGISTRO_SEPARADOR = "\x1e"
_CAMPO_SEPARADOR = "\x1f"

EjecutorGit = Callable[[list[str], Path], "subprocess.CompletedProcess[str]"]


def _ejecutar_git(argv: list[str], raiz: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *argv], cwd=raiz, capture_output=True, text=True, check=False, timeout=30
    )


def leer_historial_git(
    raiz: Path, *, limite: int = 500, ejecutar: EjecutorGit = _ejecutar_git
) -> tuple[EntradaGitLog, ...]:
    """Adapter delgado: ``git log`` como fuente, sin interpretar nada aquí.

    ``ejecutar`` es inyectable para que las pruebas no dependan de invocar
    ``git`` de verdad ni de que el historial de este repositorio no cambie.
    """
    formato = f"%H{_CAMPO_SEPARADOR}%s{_CAMPO_SEPARADOR}%b{_REGISTRO_SEPARADOR}"
    try:
        proceso = ejecutar(["log", f"-n{limite}", f"--format={formato}"], raiz)
    except (OSError, subprocess.SubprocessError) as exc:
        raise EspejoIlegibleError("historial_git", str(exc)) from exc
    if proceso.returncode != 0:
        raise EspejoIlegibleError("historial_git", proceso.stderr.strip() or "git log falló")
    entradas: list[EntradaGitLog] = []
    for bruto in proceso.stdout.split(_REGISTRO_SEPARADOR):
        bruto = bruto.strip("\n")
        if not bruto:
            continue
        partes = bruto.split(_CAMPO_SEPARADOR)
        if len(partes) < 2:
            continue
        entradas.append(
            EntradaGitLog(
                sha=partes[0],
                asunto=partes[1],
                cuerpo=partes[2] if len(partes) > 2 else "",
            )
        )
    return tuple(entradas)


def buscar_en_historial_git(
    entradas: Sequence[EntradaGitLog], consulta: str
) -> tuple[Referencia, ...]:
    consulta_normalizada = consulta.casefold()
    encontradas: list[Referencia] = []
    for entrada in entradas:
        texto = f"{entrada.asunto}\n{entrada.cuerpo}"
        if consulta_normalizada in texto.casefold():
            if consulta_normalizada in entrada.asunto.casefold():
                fragmento = entrada.asunto.strip()
            else:
                fragmento = _fragmento(entrada.cuerpo, consulta_normalizada)
            encontradas.append(
                Referencia(tipo="commit", identificador=entrada.sha[:12], fragmento=fragmento)
            )
    encontradas.sort(key=lambda r: r.identificador)
    return tuple(encontradas)


# --- Orquestación ------------------------------------------------------------


def recuperar_contexto(
    consulta: str,
    *,
    raiz_repo: Path,
    port: GitHubMirrorPort,
    repo: str,
    numeros_incidencias: Sequence[int],
    entradas_git_log: Sequence[EntradaGitLog],
    ahora: datetime,
) -> ContextoRecuperado:
    """``contexto.recuperar`` v0: combina los tres proveedores deterministas.

    Misma entrada, misma salida (requisito 5): ninguno de los tres
    proveedores depende del orden de lectura ni de estado mutable
    compartido, y el resultado se ordena de forma estable dentro de cada
    proveedor.
    """
    referencias_arbol, fallidas_arbol = buscar_en_arbol_repo(raiz_repo, consulta)
    referencias_incidencias, fallidas_incidencias = buscar_en_incidencias(
        port, repo=repo, numeros=numeros_incidencias, consulta=consulta
    )
    referencias_git = buscar_en_historial_git(entradas_git_log, consulta)
    return ContextoRecuperado(
        consulta=consulta,
        referencias=referencias_arbol + referencias_incidencias + referencias_git,
        proveedores_fallidos=fallidas_arbol + fallidas_incidencias,
        origen=OrigenLectura(fuente=f"contexto.recuperar:{repo}", leido_en=ahora),
    )
