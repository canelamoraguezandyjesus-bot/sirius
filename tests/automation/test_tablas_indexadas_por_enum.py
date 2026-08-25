"""Toda tabla `dict[Enum, X]` de `src/` cubre el enum entero, o lo declara (#287, ADR-079).

Una tabla indexada por un enum es una promesa de totalidad que nadie firma.
Cuando el enum crece y la tabla no, el resultado no es un error de
compilación: es un ``KeyError`` en tiempo de ejecución, o un valor por
defecto que devuelve algo plausible. Ya pasó una vez:
``LLMErrorKind.CONFIGURATION`` se añadió al enum, la tabla de presentación
(``sirius.presentation.error_messages._MESSAGES_BY_KIND``) lo recogió
porque tenía guarda (``tests/unit/test_error_messages.py``), y la del
adaptador (``sirius.adapters.llm.openai_responses._SAFE_MESSAGES``) no
porque no la tenía (PR #278).

La medición (ADR-079) recorrió todas las tablas `dict[Enum, X]` de `src/` y
encontró 15: 11 completas y 4 incompletas, y las 4 incompletas son
parcialidad legítima ya documentada en el propio código (una tabla cerrada
por contrato, o una tabla cuya clave nunca llega a las variantes que le
faltan) -no un defecto oculto-. Como la parcialidad legítima es la
excepción (4 de 15) y no la norma, la guarda entra: cualquier tabla que la
medición no señaló, y cualquier tabla nueva, tiene que cubrir el enum
entero o declararse aquí con su motivo.

Estática por diseño (RF/RNF de determinismo, requisito 3 de la incidencia
#287): recorre el árbol con ``ast``, sin importar ningún módulo de `src/`,
así que funciona sin pantalla, red ni dispositivos.

Lo que este criterio NO reconoce -escrito porque ADR-078 fijó el mismo
precedente para lo que su detector no atrapaba-:

- Tablas que no viven como constante de módulo (nivel superior del
  fichero): una tabla local a una función o anidada en una clase no se ve.
- Tablas sin la anotación explícita ``dict[UnEnum, X]``: un ``dict()``
  llamado, una comprensión, una tabla ``Dict[...]`` (de ``typing``, en vez
  de ``dict[...]``), o una fusionada con ``{**a, **b}`` no se reconocen.
- Tablas cuya clave es un tipo compuesto que incluye un enum sin ser
  únicamente el enum: ``dict[tuple[CaptureCommand, StudioCaptureState], X]``
  (``sirius.application.capture_replies._PHRASES``) no se mira, porque la
  clave no es el enum, es una tupla.
- Enums definidos con la API funcional (``Color = Enum("Color", [...])``)
  en vez de una ``class Color(Enum):``: no hay ninguno en `src/` hoy, y si
  apareciera esta guarda no lo vería.
- Dos enums con el mismo nombre en módulos distintos: la guarda lleva un
  registro global por nombre (no por módulo). No ocurre hoy en `src/` -hay
  37 clases de enum y ninguna colisión-, y si ocurriera esta misma prueba
  lo señala con un fallo explícito en vez de mezclar sus miembros en
  silencio.

Es determinista: solo lee ficheros y árboles de sintaxis.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SRC = RAIZ / "src"


@dataclass(frozen=True, slots=True)
class TablaEnum:
    """Una tabla `dict[Enum, X]` encontrada en `src/`."""

    archivo: str
    nombre: str
    enum: str
    claves: frozenset[str]


def _es_clase_enum(nodo: ast.ClassDef) -> bool:
    return any(ast.unparse(base).endswith("Enum") for base in nodo.bases)


def _miembros_de(nodo: ast.ClassDef) -> frozenset[str]:
    miembros: set[str] = set()
    for cuerpo in nodo.body:
        if (
            isinstance(cuerpo, ast.Assign)
            and len(cuerpo.targets) == 1
            and isinstance(cuerpo.targets[0], ast.Name)
        ):
            miembros.add(cuerpo.targets[0].id)
        elif isinstance(cuerpo, ast.AnnAssign) and isinstance(cuerpo.target, ast.Name):
            miembros.add(cuerpo.target.id)
    return frozenset(miembros)


def _tipo_de_clave(anotacion: ast.expr) -> str | None:
    if not (isinstance(anotacion, ast.Subscript) and ast.unparse(anotacion.value) == "dict"):
        return None
    indice = anotacion.slice
    primero = indice.elts[0] if isinstance(indice, ast.Tuple) else indice
    return ast.unparse(primero)


def _claves_de(tabla: ast.Dict, enum: str) -> frozenset[str]:
    return frozenset(
        clave.attr
        for clave in tabla.keys
        if isinstance(clave, ast.Attribute)
        and isinstance(clave.value, ast.Name)
        and clave.value.id == enum
    )


def _analizar(archivos: list[tuple[str, str]]) -> tuple[dict[str, frozenset[str]], list[TablaEnum]]:
    """``archivos``: pares (ruta relativa, código fuente). No toca el disco."""
    arboles = [(ruta, ast.parse(fuente, filename=ruta)) for ruta, fuente in archivos]

    enums: dict[str, frozenset[str]] = {}
    duplicados: list[str] = []
    for _, arbol in arboles:
        for sentencia in arbol.body:
            if isinstance(sentencia, ast.ClassDef) and _es_clase_enum(sentencia):
                if sentencia.name in enums:
                    duplicados.append(sentencia.name)
                enums[sentencia.name] = _miembros_de(sentencia)
    assert not duplicados, (
        "Nombres de enum duplicados en src/: el registro global de esta guarda "
        f"no puede distinguirlos: {sorted(set(duplicados))}"
    )

    tablas: list[TablaEnum] = []
    for ruta, arbol in arboles:
        for sentencia in arbol.body:
            if not (
                isinstance(sentencia, ast.AnnAssign) and isinstance(sentencia.target, ast.Name)
            ):
                continue
            if not isinstance(sentencia.value, ast.Dict):
                continue
            tipo_clave = _tipo_de_clave(sentencia.annotation)
            if tipo_clave is None or tipo_clave not in enums:
                continue
            tablas.append(
                TablaEnum(
                    archivo=ruta,
                    nombre=sentencia.target.id,
                    enum=tipo_clave,
                    claves=_claves_de(sentencia.value, tipo_clave),
                )
            )
    return enums, tablas


def _archivos_de_src() -> list[tuple[str, str]]:
    return [
        (str(archivo.relative_to(RAIZ)), archivo.read_text(encoding="utf-8"))
        for archivo in sorted(SRC.rglob("*.py"))
    ]


def _incompletas(
    enums: dict[str, frozenset[str]], tablas: list[TablaEnum]
) -> list[tuple[TablaEnum, frozenset[str]]]:
    resultado = []
    for tabla in tablas:
        faltan = enums[tabla.enum] - tabla.claves
        if faltan:
            resultado.append((tabla, faltan))
    return resultado


@dataclass(frozen=True, slots=True)
class ParcialidadDeclarada:
    """Cuánto de una tabla incompleta está autorizado, y por qué.

    ``ausentes`` fija el conjunto EXACTO de miembros cuya ausencia exime el
    motivo: no la tabla entera. Si aparece una ausencia nueva que este
    conjunto no cubre, la guarda tiene que señalarla igual que si la tabla no
    estuviera declarada -declarar dos de cuatro ausencias no exime una
    quinta que aparezca después (#288)."""

    motivo: str
    ausentes: frozenset[str]


# --- Parcialidad legítima, declarada por nombre y con motivo (ADR-079) ------
#
# La medición de la incidencia #287 recorrió las 15 tablas `dict[Enum, X]` de
# `src/` y encontró estas 4 incompletas. Las cuatro ya declaraban su
# parcialidad en un comentario junto a la propia tabla; esta lista solo la
# hace legible para la guarda. Una lista de excepciones vacía habría sido
# preferible a una inventada (requisito 4 de la incidencia); esta no está
# vacía porque la medición encontró parcialidad real, no porque se haya
# supuesto.
PARCIALIDAD_DECLARADA: dict[tuple[str, str], ParcialidadDeclarada] = {
    ("src/sirius_engine/dispatch_cli.py", "TABLA_PERFILES"): ParcialidadDeclarada(
        motivo=(
            "Solo cubre las cuatro clases despachables (programacion, auditoria, "
            "documentacion -ADR-088, incidencia #336- e investigacion -B1, "
            "incidencia #349-): dispatch_work_item rechaza cualquier otra clase "
            "antes de que el perfil llegue a leerse (contrato §12.4, comentario "
            "junto a la tabla)."
        ),
        ausentes=frozenset({"CONVERSACION_NO_APLICA", "CONSULTA_LARGA", "MIXTA"}),
    ),
    ("src/sirius_engine/dispatcher.py", "TABLA_ACTIVACION"): ParcialidadDeclarada(
        motivo=(
            "Tabla cerrada de cuatro filas fijada por el contrato §12.4 (ADR-068, "
            "ADR-088, incidencia #349): añadir una fila es una enmienda del "
            "contrato, no una decisión de implementación (comentario junto a la "
            "tabla)."
        ),
        ausentes=frozenset({"CONVERSACION_NO_APLICA", "CONSULTA_LARGA", "MIXTA"}),
    ),
    ("src/sirius_engine/intent_interpreter.py", "_ALCANCE_POR_CLASE"): ParcialidadDeclarada(
        motivo=(
            "clase_efectiva, en interpretar_intencion_v0, nunca vale "
            "CONVERSACION_NO_APLICA ni MIXTA: solo llega aquí una clase de "
            "_VERBO_A_CLASE (programacion/investigacion/documentacion/auditoria) "
            "o el valor por defecto CONSULTA_LARGA."
        ),
        ausentes=frozenset({"CONVERSACION_NO_APLICA", "MIXTA"}),
    ),
    ("src/sirius_engine/intent_interpreter.py", "_CRITERIO_POR_CLASE"): ParcialidadDeclarada(
        motivo=(
            "Misma clase_efectiva que _ALCANCE_POR_CLASE, justo arriba en el "
            "mismo fichero: comparten el mismo argumento."
        ),
        ausentes=frozenset({"CONVERSACION_NO_APLICA", "MIXTA"}),
    ),
}


def _declaraciones_no_coinciden(
    incompletas: list[tuple[TablaEnum, frozenset[str]]],
    declaradas: dict[tuple[str, str], ParcialidadDeclarada],
) -> list[tuple[TablaEnum, frozenset[str], frozenset[str]]]:
    """Tablas declaradas cuyo conjunto de ausentes actual ya no coincide con
    el declarado: apareció una ausencia nueva, o desapareció una declarada."""
    resultado = []
    for tabla, faltan in incompletas:
        declarada = declaradas.get((tabla.archivo, tabla.nombre))
        if declarada is not None and faltan != declarada.ausentes:
            resultado.append((tabla, faltan, declarada.ausentes))
    return resultado


def test_las_tablas_indexadas_por_enum_cubren_el_enum_o_estan_declaradas() -> None:
    enums, tablas = _analizar(_archivos_de_src())
    incompletas = _incompletas(enums, tablas)
    sin_declarar = [
        (tabla, faltan)
        for tabla, faltan in incompletas
        if (tabla.archivo, tabla.nombre) not in PARCIALIDAD_DECLARADA
    ]
    assert not sin_declarar, "\n".join(
        f"{tabla.archivo}:{tabla.nombre} (dict[{tabla.enum}, ...]) no cubre: "
        f"{sorted(faltan)}. Complétala, o declárala en PARCIALIDAD_DECLARADA "
        "con el motivo."
        for tabla, faltan in sin_declarar
    )

    no_coinciden = _declaraciones_no_coinciden(incompletas, PARCIALIDAD_DECLARADA)
    assert not no_coinciden, "\n".join(
        f"{tabla.archivo}:{tabla.nombre} (dict[{tabla.enum}, ...]) declaraba ausentes "
        f"{sorted(ausentes_declarados)} pero ahora faltan {sorted(faltan)}. Actualiza "
        "PARCIALIDAD_DECLARADA con el conjunto exacto, o completa la tabla."
        for tabla, faltan, ausentes_declarados in no_coinciden
    )


def test_la_parcialidad_declarada_sigue_siendo_incompleta() -> None:
    """Si una entrada declarada se completa, hay que borrarla de aquí: una
    excepción que ya no hace falta esconde tanto como una que falta."""
    enums, tablas = _analizar(_archivos_de_src())
    incompletas = {(tabla.archivo, tabla.nombre) for tabla, _ in _incompletas(enums, tablas)}
    obsoletas = set(PARCIALIDAD_DECLARADA) - incompletas
    assert not obsoletas, f"Declaradas como parciales pero ya completas: {sorted(obsoletas)}"


def test_la_parcialidad_declarada_sigue_existiendo_como_tabla() -> None:
    """Si una tabla declarada desaparece o cambia de nombre, la entrada
    correspondiente en ``PARCIALIDAD_DECLARADA`` queda huérfana."""
    _, tablas = _analizar(_archivos_de_src())
    existentes = {(tabla.archivo, tabla.nombre) for tabla in tablas}
    fantasmas = set(PARCIALIDAD_DECLARADA) - existentes
    assert not fantasmas, f"Declaradas pero ya no existen como tabla: {sorted(fantasmas)}"


# --- Pruebas de la guarda misma (requisitos 2 y 5 de la incidencia #287) ----

_ENUM_FIXTURE = """
from enum import StrEnum


class LLMErrorKind(StrEnum):
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RATE_LIMITED = "rate_limited"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"
    BUDGET_EXCEEDED = "budget_exceeded"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"
"""

# Reconstrucción equivalente (requisito 5) de la tabla real de
# `src/sirius/adapters/llm/openai_responses.py` tal y como estaba antes de la
# PR #278: exactamente las mismas claves, sin `CONFIGURATION`.
_TABLA_FIXTURE_ANTERIOR_A_LA_PR_278 = """
from sirius.ports.llm import LLMErrorKind

_SAFE_MESSAGES: dict[LLMErrorKind, str] = {
    LLMErrorKind.AUTHENTICATION: "x",
    LLMErrorKind.PERMISSION: "x",
    LLMErrorKind.RATE_LIMITED: "x",
    LLMErrorKind.CONNECTION: "x",
    LLMErrorKind.TIMEOUT: "x",
    LLMErrorKind.INVALID_RESPONSE: "x",
    LLMErrorKind.BUDGET_EXCEEDED: "x",
    LLMErrorKind.UNKNOWN: "x",
}
"""

_TABLA_FIXTURE_COMPLETA = _TABLA_FIXTURE_ANTERIOR_A_LA_PR_278.replace(
    '    LLMErrorKind.UNKNOWN: "x",\n}',
    '    LLMErrorKind.UNKNOWN: "x",\n    LLMErrorKind.CONFIGURATION: "x",\n}',
)


def test_la_guarda_encuentra_el_defecto_historico_de_la_pr_278() -> None:
    enums, tablas = _analizar(
        [
            ("fixture_enum.py", _ENUM_FIXTURE),
            ("fixture_tabla.py", _TABLA_FIXTURE_ANTERIOR_A_LA_PR_278),
        ]
    )
    (tabla,) = [t for t in tablas if t.nombre == "_SAFE_MESSAGES"]
    faltan = enums[tabla.enum] - tabla.claves
    assert faltan == {"CONFIGURATION"}


def test_la_guarda_no_senala_la_misma_tabla_ya_completa() -> None:
    enums, tablas = _analizar(
        [
            ("fixture_enum.py", _ENUM_FIXTURE),
            ("fixture_tabla.py", _TABLA_FIXTURE_COMPLETA),
        ]
    )
    (tabla,) = [t for t in tablas if t.nombre == "_SAFE_MESSAGES"]
    assert not (enums[tabla.enum] - tabla.claves)


_ENUM_FIXTURE_DECLARACION = """
from enum import StrEnum


class Perfil(StrEnum):
    PROGRAMACION = "programacion"
    AUDITORIA = "auditoria"
    DOCUMENTACION = "documentacion"
"""

#: Como TABLA_PERFILES real: cubre dos de las tres variantes, y la ausente
#: (DOCUMENTACION) es la única que la declaración de abajo autoriza.
_TABLA_FIXTURE_DECLARACION_ORIGINAL = """
from fixture_enum_declaracion import Perfil

TABLA_PERFILES: dict[Perfil, str] = {
    Perfil.PROGRAMACION: "x",
    Perfil.AUDITORIA: "x",
}
"""

#: Retira PROGRAMACION de la tabla, igual que el ejemplo del hallazgo
#: CODEX-001 (#288): la tabla sigue en PARCIALIDAD_DECLARADA por su clave
#: (archivo, nombre), pero ahora le falta una variante que la declaración
#: original no autorizaba.
_TABLA_FIXTURE_DECLARACION_NUEVA_OMISION = _TABLA_FIXTURE_DECLARACION_ORIGINAL.replace(
    '    Perfil.PROGRAMACION: "x",\n', ""
)


def test_la_declaracion_no_exime_una_omision_nueva_de_la_misma_tabla() -> None:
    """CODEX-001 (#288): antes, `(archivo, nombre) in PARCIALIDAD_DECLARADA`
    eximía la tabla entera, así que una omisión nueva -no la que motivó la
    declaración original- pasaba en silencio mientras la tabla siguiera
    incompleta. `_declaraciones_no_coinciden` compara el conjunto EXACTO de
    ausentes declarado contra el actual: una ausencia no autorizada tiene que
    seguir señalándose."""
    declarada = {
        ("fixture_tabla_declaracion.py", "TABLA_PERFILES"): ParcialidadDeclarada(
            motivo="Solo cubre las clases despachables (fixture).",
            ausentes=frozenset({"DOCUMENTACION"}),
        )
    }

    enums, tablas_original = _analizar(
        [
            ("fixture_enum_declaracion.py", _ENUM_FIXTURE_DECLARACION),
            ("fixture_tabla_declaracion.py", _TABLA_FIXTURE_DECLARACION_ORIGINAL),
        ]
    )
    incompletas_original = _incompletas(enums, tablas_original)
    assert not _declaraciones_no_coinciden(incompletas_original, declarada)

    enums, tablas_nueva = _analizar(
        [
            ("fixture_enum_declaracion.py", _ENUM_FIXTURE_DECLARACION),
            ("fixture_tabla_declaracion.py", _TABLA_FIXTURE_DECLARACION_NUEVA_OMISION),
        ]
    )
    incompletas_nueva = _incompletas(enums, tablas_nueva)
    no_coinciden = _declaraciones_no_coinciden(incompletas_nueva, declarada)

    assert len(no_coinciden) == 1
    tabla, faltan, ausentes_declarados = no_coinciden[0]
    assert tabla.nombre == "TABLA_PERFILES"
    assert faltan == {"DOCUMENTACION", "PROGRAMACION"}
    assert ausentes_declarados == {"DOCUMENTACION"}


def test_una_tabla_con_clave_compuesta_no_se_reconoce() -> None:
    """`_PHRASES` (`sirius.application.capture_replies`) usa una clave tupla:
    esta guarda declara por diseño que no la mira (ver docstring del módulo).
    """
    fuente = """
from enum import StrEnum


class Comando(StrEnum):
    A = "a"
    B = "b"


class Estado(StrEnum):
    X = "x"
    Y = "y"


_TABLA: dict[tuple[Comando, Estado], str] = {
    (Comando.A, Estado.X): "solo una combinacion",
}
"""
    _, tablas = _analizar([("fixture.py", fuente)])
    assert tablas == []


def test_una_tabla_local_a_una_funcion_no_se_reconoce() -> None:
    """Solo se miran constantes de módulo (nivel superior del fichero), tal y
    como declara el docstring del módulo."""
    fuente = """
from enum import StrEnum


class Estado(StrEnum):
    X = "x"
    Y = "y"


def construir() -> dict[Estado, str]:
    tabla: dict[Estado, str] = {Estado.X: "solo una variante"}
    return tabla
"""
    _, tablas = _analizar([("fixture.py", fuente)])
    assert tablas == []
