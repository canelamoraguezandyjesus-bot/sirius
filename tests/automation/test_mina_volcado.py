"""El volcado de la mina se publica entero o no se publica (Codex, PR #665, ronda 6).

Sobrescribir cada fichero no daba atomicidad: una descarga que fallara a medias
dejaba un indice nuevo con historiales viejos y el analisis mezclaba dos fotos
sin aviso. `descargar.py` escribe en `raw.parcial` y `publicar_volcado` lo
sustituye entero al terminar; si muere antes, el definitivo sigue siendo la
ultima foto completa y el parcial queda a la vista.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MINA = RAIZ / "scripts" / "mina"


def _cargar(nombre: str) -> ModuleType:
    if str(MINA) not in sys.path:
        sys.path.insert(0, str(MINA))
    spec = importlib.util.spec_from_file_location(nombre, MINA / f"{nombre}.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


datos = _cargar("datos")
descargar = _cargar("descargar")


def _foto_anterior(raw: Path) -> None:
    raw.mkdir(parents=True)
    (raw / "indice.json").write_text("[]", encoding="utf-8")
    (raw / "issue_9.json").write_text('{"issue": {"number": 9}, "comments": []}', encoding="utf-8")


def test_publicar_volcado_sustituye_entero_el_anterior(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    _foto_anterior(raw)
    parcial = datos.parcial_de(raw)
    parcial.mkdir()
    (parcial / "indice.json").write_text("[1]", encoding="utf-8")
    (parcial / "issue_1.json").write_text("{}", encoding="utf-8")

    datos.publicar_volcado(parcial, raw)

    assert sorted(p.name for p in raw.iterdir()) == ["indice.json", "issue_1.json"], (
        "el fichero viejo `issue_9.json` no puede sobrevivir a una foto nueva"
    )
    assert (raw / "indice.json").read_text(encoding="utf-8") == "[1]"
    assert not parcial.exists() and not raw.with_name("raw.anterior").exists()


def _incidencia(numero: int) -> dict[str, object]:
    return {
        "number": numero,
        "title": f"#{numero}",
        "state": "closed",
        "created_at": "2026-09-01T00:00:00Z",
        "updated_at": "2026-09-02T00:00:00Z",
        "closed_at": None,
        "comments": 1,
        "labels": [],
    }


def _comentario(numero: int) -> dict[str, object]:
    return {
        "id": numero,
        "user": {"login": "sirius-motor"},
        "author_association": "OWNER",
        "created_at": "2026-09-01T10:00:00Z",
        "updated_at": None,
        "body": f"comentario de #{numero}",
    }


def test_una_descarga_completa_publica_la_foto_nueva(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = tmp_path / "raw"
    _foto_anterior(raw)

    def paginar(url: str) -> list[dict[str, object]]:
        if "/issues?" in url:
            return [_incidencia(1), _incidencia(2)]
        numero = int(url.rsplit("/issues/", 1)[1].split("/")[0])
        return [_comentario(numero)]

    monkeypatch.setattr(descargar, "paginar", paginar)
    assert descargar.main(raw=raw) == 0

    assert sorted(p.name for p in raw.iterdir()) == ["indice.json", "issue_1.json", "issue_2.json"]
    assert not datos.parcial_de(raw).exists()
    publicado = json.loads((raw / "issue_2.json").read_text(encoding="utf-8"))
    assert publicado["comments"][0]["body"] == "comentario de #2"


def test_una_descarga_interrumpida_no_toca_la_foto_anterior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El caso de la ronda 6: la segunda incidencia falla. El indice nuevo y la
    primera incidencia NO se publican: el definitivo sigue siendo la foto
    anterior completa y el parcial queda a la vista para `analizar.py`."""
    raw = tmp_path / "raw"
    _foto_anterior(raw)
    antes = {p.name: p.read_text(encoding="utf-8") for p in raw.iterdir()}

    def paginar(url: str) -> list[dict[str, object]]:
        if "/issues?" in url:
            return [_incidencia(1), _incidencia(2)]
        if "/issues/2/" in url:
            raise RuntimeError("la API se cayo a mitad del volcado")
        return [_comentario(1)]

    monkeypatch.setattr(descargar, "paginar", paginar)
    with pytest.raises(RuntimeError, match="a mitad"):
        descargar.main(raw=raw)

    assert {p.name: p.read_text(encoding="utf-8") for p in raw.iterdir()} == antes, (
        "una descarga a medias no puede mezclar un indice nuevo con historiales viejos"
    )
    parcial = datos.parcial_de(raw)
    assert parcial.exists() and (parcial / "issue_1.json").exists()
    assert not (parcial / "issue_2.json").exists()


def test_si_el_segundo_renombrado_falla_el_anterior_vuelve_a_su_sitio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ronda 7 de Codex en la PR #665: dos renombrados sin vuelta atras dejaban el
    definitivo AUSENTE si el segundo fallaba. El anterior vuelve, el parcial sigue
    a la vista y el error se propaga."""
    raw = tmp_path / "raw"
    _foto_anterior(raw)
    antes = {p.name: p.read_text(encoding="utf-8") for p in raw.iterdir()}
    parcial = datos.parcial_de(raw)
    parcial.mkdir()
    (parcial / "indice.json").write_text("[1]", encoding="utf-8")

    renombrar = Path.rename

    def renombrar_salvo_el_parcial(self: Path, destino: Path) -> Path:
        if self == parcial:
            raise OSError("sin espacio al publicar")
        return renombrar(self, destino)

    monkeypatch.setattr(Path, "rename", renombrar_salvo_el_parcial)
    with pytest.raises(OSError, match="sin espacio"):
        datos.publicar_volcado(parcial, raw)

    assert {p.name: p.read_text(encoding="utf-8") for p in raw.iterdir()} == antes, (
        "la foto anterior tiene que volver a ser el definitivo"
    )
    assert parcial.exists() and not raw.with_name("raw.anterior").exists()
