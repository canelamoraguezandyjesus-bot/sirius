"""La clasificacion de falsos negativos de la mina es una funcion pura y se prueba.

Lo que costo una ronda de Codex (PR #665): clasificar una incidencia por el
veredicto de su historial FINAL pierde la familia que un `continua` posterior
saca del tramo vigente. Aqui se fija lo contrario, con historiales sinteticos.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

RAIZ = Path(__file__).resolve().parents[2]
MINA = RAIZ / "scripts" / "mina"


def _cargar() -> ModuleType:
    sys.path.insert(0, str(MINA))
    spec = importlib.util.spec_from_file_location("falsos_negativos", MINA / "falsos_negativos.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    # Registrado ANTES de ejecutar: los dataclass buscan su modulo en sys.modules.
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


fn = _cargar()

FIN = "2026-09-30T23:59:59Z"


def _ronda(n: int, fichero: str, instante: str) -> dict[str, str]:
    cuerpo = (
        f"<!-- sirius-round:{n} -->\n\n## RONDA_HALLAZGOS\n```json\n"
        f'{{"round": {n}, "head": "h{n}", "findings": '
        f'[{{"fingerprint": "f{n}", "severity": "P2", "source": "CODEX", "file": "{fichero}"}}]}}\n'
        "```\n"
    )
    return {"body": cuerpo, "created_at": instante, "author_association": "OWNER"}


def _continua(instante: str) -> dict[str, str]:
    return {
        "body": "<!-- sirius-convergence-reset:abc123 -->\ncontinua",
        "created_at": instante,
        "author_association": "OWNER",
    }


def _aviso(instante: str, *evidencias: tuple[str, int, int]) -> dict[str, str]:
    """Un aviso tal como lo publica el motor: cabecera y una linea por evidencia."""
    lineas = "\n".join(
        f"- «{archivo}» recibe hallazgos en {hasta - desde + 1} rondas consecutivas "
        f"(rondas {desde}-{hasta}): la corrección de una ronda no está resolviendo lo que "
        "la revisión sigue encontrando en la siguiente."
        for archivo, desde, hasta in evidencias
    )
    return {
        "body": f"## AVISO_FAMILIA_REPETIDA\n{lineas}\n\nAviso informativo (ADR-078).",
        "created_at": instante,
        "author_association": "OWNER",
    }


_TRES_SOBRE_X = [
    _ronda(1, "src/x.py", "2026-09-10T10:00:00Z"),
    _ronda(2, "src/x.py", "2026-09-10T11:00:00Z"),
    _ronda(3, "src/x.py", "2026-09-10T12:00:00Z"),
]


def test_una_familia_borrada_por_un_continua_posterior_sigue_contando() -> None:
    historial = [
        *_TRES_SOBRE_X,
        _continua("2026-09-10T13:00:00Z"),
        _ronda(4, "src/y.py", "2026-09-10T14:00:00Z"),
    ]
    [c] = fn.clasificar({700: historial}, fin=FIN).values()
    assert fn.evidencias_de_hoy([h["body"] for h in historial]) == [], (
        "sobre el historial final el detector no marca..."
    )
    [tramo] = c.tramos
    assert tramo.archivo == "src/x.py" and tramo.primera_ronda == 3, (
        "...pero en la ronda 3 si marcaba"
    )
    assert c.estado == "falso_negativo" and c.rondas_evaluadas == 4


def test_un_aviso_publicado_en_la_ventana_la_saca_de_los_falsos_negativos() -> None:
    historial = [*_TRES_SOBRE_X, _aviso("2026-09-10T12:30:00Z", ("src/x.py", 1, 3))]
    [c] = fn.clasificar({700: historial}, fin=FIN).values()
    assert c.estado == "avisada" and c.avisos == 1


def test_lo_publicado_despues_de_la_ventana_no_entra() -> None:
    historial = [*_TRES_SOBRE_X[:2], _ronda(3, "src/x.py", "2026-10-02T09:00:00Z")]
    [c] = fn.clasificar({700: historial}, fin=FIN).values()
    assert c.estado == "sin_familia" and c.rondas_evaluadas == 2
    tardio = [*_TRES_SOBRE_X, _aviso("2026-10-02T09:00:00Z", ("src/x.py", 1, 3))]
    [d] = fn.clasificar({701: tardio}, fin=FIN).values()
    assert d.estado == "falso_negativo" and d.avisos == 0, (
        "un aviso de octubre no exculpa a septiembre"
    )


def test_sin_tres_rondas_sobre_el_mismo_fichero_no_hay_familia() -> None:
    historial = [
        _ronda(1, "src/a.py", "2026-09-10T10:00:00Z"),
        _ronda(2, "src/b.py", "2026-09-10T11:00:00Z"),
        _ronda(3, "src/c.py", "2026-09-10T12:00:00Z"),
    ]
    [c] = fn.clasificar({700: historial}, fin=FIN).values()
    assert c.estado == "sin_familia" and c.tramos == ()


def test_cada_tramo_cuenta_por_separado_y_un_aviso_solo_cubre_lo_que_publico() -> None:
    """#570 en la edicion del 14-09: dos tramos reales en una incidencia.

    El aviso llega cuando solo el primero esta marcado y lo lista a el; el
    segundo aparece despues y nadie vuelve a avisar: es un falso negativo
    aunque la incidencia «tuviera aviso».
    """
    historial = [
        *_TRES_SOBRE_X,
        _aviso("2026-09-10T12:30:00Z", ("src/x.py", 1, 3)),
        _ronda(4, "docs/adr.md", "2026-09-10T13:00:00Z"),
        _ronda(5, "docs/adr.md", "2026-09-10T14:00:00Z"),
        _ronda(6, "docs/adr.md", "2026-09-10T15:00:00Z"),
    ]
    [c] = fn.clasificar({570: historial}, fin=FIN).values()
    por_archivo = {t.archivo: t for t in c.tramos}
    assert set(por_archivo) == {"src/x.py", "docs/adr.md"}, "dos tramos, no un booleano"
    assert por_archivo["src/x.py"].cubierto_por_aviso and por_archivo["src/x.py"].primera_ronda == 3
    assert not por_archivo["docs/adr.md"].cubierto_por_aviso
    assert por_archivo["docs/adr.md"].primera_ronda == 6 and por_archivo["docs/adr.md"].rondas == (
        4,
        5,
        6,
    )
    assert c.estado == "falso_negativo" and len(c.sin_aviso) == 1


def test_el_mismo_fichero_en_dos_rachas_separadas_son_dos_tramos() -> None:
    """Codex, PR #665 ronda 4: indexar por fichero fundia las rondas 1-3 con las 5-7."""
    historial = [
        *_TRES_SOBRE_X,
        _aviso("2026-09-10T12:30:00Z", ("src/x.py", 1, 3)),
        _ronda(4, "src/y.py", "2026-09-10T13:00:00Z"),
        _ronda(5, "src/x.py", "2026-09-10T14:00:00Z"),
        _ronda(6, "src/x.py", "2026-09-10T15:00:00Z"),
        _ronda(7, "src/x.py", "2026-09-10T16:00:00Z"),
    ]
    [c] = fn.clasificar({700: historial}, fin=FIN).values()
    assert [(t.archivo, t.rondas) for t in c.tramos] == [
        ("src/x.py", (1, 2, 3)),
        ("src/x.py", (5, 6, 7)),
    ]
    primero, segundo = c.tramos
    assert primero.cubierto_por_aviso and primero.primera_ronda == 3
    assert not segundo.cubierto_por_aviso and segundo.primera_ronda == 7
    assert c.estado == "falso_negativo" and len(c.sin_aviso) == 1


def test_una_racha_que_crece_sigue_siendo_el_mismo_tramo() -> None:
    historial = [
        *_TRES_SOBRE_X,
        _aviso("2026-09-10T12:30:00Z", ("src/x.py", 1, 3)),
        _ronda(4, "src/x.py", "2026-09-10T13:00:00Z"),
    ]
    [c] = fn.clasificar({700: historial}, fin=FIN).values()
    [tramo] = c.tramos
    assert tramo.rondas == (1, 2, 3, 4) and tramo.primera_ronda == 3
    assert tramo.cubierto_por_aviso and c.estado == "avisada"


def test_un_aviso_por_otra_familia_tras_un_continua_no_cubre_el_tramo_anterior() -> None:
    """Codex, PR #665 ronda 4: comparar solo instantes convertia un falso negativo
    en avisado. El aviso posterior se publico tras un `continua`, asi que el
    detector que lo genero no pudo ver la familia anterior."""
    historial = [
        *_TRES_SOBRE_X,
        _continua("2026-09-10T13:00:00Z"),
        _ronda(4, "src/y.py", "2026-09-10T14:00:00Z"),
        _ronda(5, "src/y.py", "2026-09-10T15:00:00Z"),
        _ronda(6, "src/y.py", "2026-09-10T16:00:00Z"),
        _aviso("2026-09-10T16:30:00Z", ("src/y.py", 4, 6)),
    ]
    [c] = fn.clasificar({700: historial}, fin=FIN).values()
    por_archivo = {t.archivo: t for t in c.tramos}
    assert not por_archivo["src/x.py"].cubierto_por_aviso
    assert por_archivo["src/y.py"].cubierto_por_aviso
    assert c.estado == "falso_negativo" and c.avisos == 1


def test_una_mencion_en_prosa_no_es_un_aviso_y_un_aviso_se_lee_entero() -> None:
    """#520, 03-09 17:12 UTC: el propietario escribio «Sobre el AVISO_FAMILIA_REPETIDA:
    es exacto» y la busqueda por subcadena lo contaba como un aviso mas."""
    assert fn.evidencias_publicadas("Sobre el `AVISO_FAMILIA_REPETIDA`: es exacto.") is None
    aviso = _aviso("2026-09-10T12:30:00Z", ("src/x.py", 1, 3), ("docs/a.md", 2, 4))
    assert fn.evidencias_publicadas(aviso["body"]) == (
        ("src/x.py", (1, 2, 3)),
        ("docs/a.md", (2, 3, 4)),
    )
    mencion = {
        "body": "Sobre el `AVISO_FAMILIA_REPETIDA`: es exacto.",
        "created_at": "2026-09-10T12:30:00Z",
        "author_association": "OWNER",
    }
    [c] = fn.clasificar({520: [*_TRES_SOBRE_X, mencion]}, fin=FIN).values()
    assert c.avisos == 0 and c.estado == "falso_negativo"
