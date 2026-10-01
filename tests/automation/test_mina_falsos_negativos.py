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


def _aviso(instante: str) -> dict[str, str]:
    return {
        "body": "## AVISO_FAMILIA_REPETIDA\nx",
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
    [c] = fn.clasificar({700: historial}, [], fin=FIN).values()
    assert fn.evidencias_de_hoy([h["body"] for h in historial]) == [], (
        "sobre el historial final el detector no marca..."
    )
    [tramo] = c.tramos
    assert tramo.archivo == "src/x.py" and tramo.primera_ronda == 3, (
        "...pero en la ronda 3 si marcaba"
    )
    assert c.estado == "falso_negativo" and c.rondas_evaluadas == 4


def test_un_aviso_publicado_en_la_ventana_la_saca_de_los_falsos_negativos() -> None:
    historial = [*_TRES_SOBRE_X, _aviso("2026-09-10T12:30:00Z")]
    [c] = fn.clasificar({700: historial}, [(700, "2026-09-10T12:30:00Z")], fin=FIN).values()
    assert c.estado == "avisada" and c.avisos == 1


def test_lo_publicado_despues_de_la_ventana_no_entra() -> None:
    historial = [*_TRES_SOBRE_X[:2], _ronda(3, "src/x.py", "2026-10-02T09:00:00Z")]
    [c] = fn.clasificar({700: historial}, [], fin=FIN).values()
    assert c.estado == "sin_familia" and c.rondas_evaluadas == 2
    [d] = fn.clasificar({701: _TRES_SOBRE_X}, [(701, "2026-10-02T09:00:00Z")], fin=FIN).values()
    assert d.estado == "falso_negativo", "un aviso de octubre no exculpa a septiembre"


def test_sin_tres_rondas_sobre_el_mismo_fichero_no_hay_familia() -> None:
    historial = [
        _ronda(1, "src/a.py", "2026-09-10T10:00:00Z"),
        _ronda(2, "src/b.py", "2026-09-10T11:00:00Z"),
        _ronda(3, "src/c.py", "2026-09-10T12:00:00Z"),
    ]
    [c] = fn.clasificar({700: historial}, [], fin=FIN).values()
    assert c.estado == "sin_familia" and c.tramos == ()


def test_cada_tramo_cuenta_por_separado_y_un_aviso_solo_cubre_lo_marcado_hasta_su_instante() -> (
    None
):
    """#570 en la edicion del 14-09: dos tramos reales (1-3 y 2-4) en una incidencia.

    El aviso llega cuando solo el primero esta marcado; el segundo aparece despues
    y nadie vuelve a avisar: es un falso negativo aunque la incidencia «tuviera aviso».
    """
    historial = [
        _ronda(1, "src/x.py", "2026-09-10T10:00:00Z"),
        _ronda(2, "src/x.py", "2026-09-10T11:00:00Z"),
        _ronda(3, "src/x.py", "2026-09-10T12:00:00Z"),
        _aviso("2026-09-10T12:30:00Z"),
        _ronda(4, "docs/adr.md", "2026-09-10T13:00:00Z"),
        _ronda(5, "docs/adr.md", "2026-09-10T14:00:00Z"),
        _ronda(6, "docs/adr.md", "2026-09-10T15:00:00Z"),
    ]
    [c] = fn.clasificar({570: historial}, [(570, "2026-09-10T12:30:00Z")], fin=FIN).values()
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
