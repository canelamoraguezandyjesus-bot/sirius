"""La matriz de trazabilidad PA/SP dice la verdad sobre las pruebas que nombra.

Una matriz de trazabilidad escrita a mano y no comprobada se pudre en cuanto
alguien renombra una prueba: sigue afirmando cobertura que ya no existe, y la
afirmación es peor que la ausencia porque nadie vuelve a mirar.

Estas pruebas verifican tres cosas sobre
`docs/implementation/TRAZABILIDAD_PA_SP.md`:

1. que estén los 40 identificadores del Plan de Pruebas aprobado, ni uno menos
   ni uno inventado;
2. que cada prueba nombrada exista de verdad, en su archivo y con su nombre;
3. que toda cobertura `parcial` o `manual` declare un motivo del vocabulario
   cerrado, para que «no se puede automatizar» sea siempre una afirmación
   concreta y no una excusa.

No comprueban que la cobertura declarada sea *suficiente*: eso no lo puede
comprobar una prueba. Comprueban que lo declarado sea cierto.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIZ = REPO_ROOT / "docs" / "implementation" / "TRAZABILIDAD_PA_SP.md"

# Identificadores del Plan de Pruebas y Trazabilidad 0.1 v1.0 aprobado,
# extraídos de `docs/canonical/SIRIUS_PLAN_PRUEBAS_TRAZABILIDAD_0.1_v1.0_PROPUESTO.docx`
# con `scripts/read_docx.py`. El conjunto es regular y cerrado: 25 pruebas de
# aceptación, la de extremo a extremo, 7 de personalidad y 7 de seguridad.
IDENTIFICADORES_DEL_PLAN = frozenset(
    [f"PA-{n:03d}" for n in range(1, 26)]
    + ["PA-E2E-01"]
    + [f"PS-{n:02d}" for n in range(1, 8)]
    + [f"SP-{n:02d}" for n in range(1, 8)]
)

COBERTURAS = frozenset({"automática", "parcial", "manual"})
MOTIVOS = frozenset({"proveedor-real", "windows-real", "evaluación-humana"})
SIN_MOTIVO = "—"
SIN_PRUEBAS = "hueco"

# `| PA-003 | Guardado previo | automática | — | `a::b`<br>`c::d` |`
FILA = re.compile(
    r"^\|\s*(?P<id>(?:PA|PS|SP)-[0-9A-Z-]+)\s*\|"
    r"[^|]*\|"
    r"\s*(?P<cobertura>[^|]+?)\s*\|"
    r"\s*(?P<motivo>[^|]+?)\s*\|"
    r"\s*(?P<pruebas>[^|]+?)\s*\|",
    re.MULTILINE,
)

REFERENCIA = re.compile(r"`([^`]+?)::([A-Za-z_][A-Za-z0-9_]*)`")


class Entrada:
    def __init__(self, identificador: str, cobertura: str, motivo: str, pruebas: str):
        self.identificador = identificador
        self.cobertura = cobertura
        self.motivo = motivo
        self.pruebas = pruebas

    @property
    def referencias(self) -> list[tuple[str, str]]:
        return REFERENCIA.findall(self.pruebas)


SEPARADOR_HUECOS = "## Huecos abiertos"


def _partes() -> tuple[str, str]:
    # La tabla de huecos tiene otras columnas y sus filas también empiezan por
    # un identificador, así que analizarla como si fuera la matriz produce
    # entradas fantasma. Se separan explícitamente.
    texto = MATRIZ.read_text(encoding="utf-8")
    matriz, _, huecos = texto.partition(SEPARADOR_HUECOS)
    assert huecos, f"Falta la sección '{SEPARADOR_HUECOS}' en la matriz."
    return matriz, huecos


def _entradas() -> list[Entrada]:
    matriz, _ = _partes()
    return [
        Entrada(m.group("id"), m.group("cobertura"), m.group("motivo"), m.group("pruebas"))
        for m in FILA.finditer(matriz)
    ]


ENTRADAS = _entradas()


def test_la_matriz_cubre_exactamente_los_identificadores_del_plan() -> None:
    declarados = {entrada.identificador for entrada in ENTRADAS}
    faltan = IDENTIFICADORES_DEL_PLAN - declarados
    sobran = declarados - IDENTIFICADORES_DEL_PLAN
    assert not faltan, (
        f"La matriz omite {len(faltan)} pruebas del plan aprobado: "
        f"{sorted(faltan)}. Omitir una es peor que declararla sin cubrir: "
        "desaparece del recuento y nadie la echa de menos."
    )
    assert not sobran, (
        f"La matriz declara identificadores que no están en el plan aprobado: {sorted(sobran)}."
    )


def test_ningun_identificador_aparece_dos_veces() -> None:
    declarados = [entrada.identificador for entrada in ENTRADAS]
    repetidos = sorted({i for i in declarados if declarados.count(i) > 1})
    assert not repetidos, (
        f"Identificadores duplicados en la matriz: {repetidos}. Dos filas para "
        "el mismo identificador vuelven a permitir que dos sitios digan cosas "
        "distintas del mismo hecho."
    )


@pytest.mark.parametrize("entrada", ENTRADAS, ids=lambda entrada: entrada.identificador)
def test_cada_entrada_declara_una_cobertura_y_un_motivo_validos(
    entrada: Entrada,
) -> None:
    assert entrada.cobertura in COBERTURAS, (
        f"{entrada.identificador}: cobertura '{entrada.cobertura}' no está en {sorted(COBERTURAS)}."
    )
    if entrada.cobertura == "automática":
        assert entrada.motivo == SIN_MOTIVO, (
            f"{entrada.identificador}: una cobertura automática no lleva motivo."
        )
    else:
        assert entrada.motivo in MOTIVOS, (
            f"{entrada.identificador}: cobertura '{entrada.cobertura}' exige un "
            f"motivo de {sorted(MOTIVOS)}, y declara '{entrada.motivo}'. Sin "
            "vocabulario cerrado, «no se puede automatizar» acaba tapando "
            "cualquier cosa."
        )


@pytest.mark.parametrize("entrada", ENTRADAS, ids=lambda entrada: entrada.identificador)
def test_cada_prueba_nombrada_existe_de_verdad(entrada: Entrada) -> None:
    if entrada.pruebas.strip() == SIN_PRUEBAS:
        return

    referencias = entrada.referencias
    assert referencias, (
        f"{entrada.identificador}: la celda de pruebas no está vacía pero no "
        f"contiene ninguna referencia `archivo::funcion`: {entrada.pruebas!r}. "
        f"Si no hay cobertura todavía, escríbase '{SIN_PRUEBAS}'."
    )

    for archivo, funcion in referencias:
        ruta = REPO_ROOT / archivo
        assert ruta.is_file(), (
            f"{entrada.identificador}: {archivo} no existe. La matriz afirma "
            "una cobertura que ya no está."
        )
        contenido = ruta.read_text(encoding="utf-8")
        assert re.search(rf"^def {re.escape(funcion)}\(", contenido, re.MULTILINE), (
            f"{entrada.identificador}: {archivo} existe pero no define "
            f"{funcion}. Probablemente se renombró la prueba y la matriz se "
            "quedó afirmando la cobertura antigua."
        )


@pytest.mark.parametrize("entrada", ENTRADAS, ids=lambda entrada: entrada.identificador)
def test_una_cobertura_automatica_o_parcial_nombra_al_menos_una_prueba(
    entrada: Entrada,
) -> None:
    if entrada.cobertura == "manual":
        return
    if entrada.pruebas.strip() == SIN_PRUEBAS:
        # Un hueco declarado es legítimo mientras esté en la tabla de huecos:
        # lo que no se admite es que desaparezca de la vista.
        _, huecos = _partes()
        assert entrada.identificador in huecos, (
            f"{entrada.identificador}: está declarado como '{entrada.cobertura}' "
            f"y sin pruebas, pero no aparece en la tabla de huecos abiertos. Un "
            "hueco que no se lista es un hueco que se olvida."
        )
        return
    assert entrada.referencias, (
        f"{entrada.identificador}: cobertura '{entrada.cobertura}' exige nombrar "
        "al menos una prueba."
    )
