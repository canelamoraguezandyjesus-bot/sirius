"""El volcado de la mina se publica entero o no se publica (Codex, PR #665, rondas 6 a 8).

Sobrescribir cada fichero no daba atomicidad: una descarga que fallara a medias
dejaba un indice nuevo con historiales viejos y el analisis mezclaba dos fotos
sin aviso. `descargar.py` escribe en `raw.parcial` y `publicar_volcado` lo
publica entero al terminar con UN cambio atomico: el parcial pasa a un
directorio propio y el selector `raw.actual` se sustituye con `os.replace`; la
foto visible no se retira nunca antes de que la nueva este seleccionada. Si la
descarga muere antes, la foto publicada sigue siendo la ultima completa y el
parcial queda a la vista.
"""

from __future__ import annotations

import importlib.util
import json
import os
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

    foto = datos.volcado_actual(raw)
    assert foto != raw and foto.parent == raw.parent and foto.name.startswith("raw.")
    assert sorted(p.name for p in foto.iterdir()) == ["indice.json", "issue_1.json"], (
        "el fichero viejo `issue_9.json` no puede sobrevivir a una foto nueva"
    )
    assert (foto / "indice.json").read_text(encoding="utf-8") == "[1]"
    assert not parcial.exists()
    assert not raw.exists(), "la foto heredada se borra DESPUES de seleccionar la nueva"

    # Una segunda publicacion sustituye el selector y borra la foto anterior.
    parcial.mkdir()
    (parcial / "indice.json").write_text("[2]", encoding="utf-8")
    datos.publicar_volcado(parcial, raw)
    segunda = datos.volcado_actual(raw)
    assert segunda != foto and not foto.exists()
    assert (segunda / "indice.json").read_text(encoding="utf-8") == "[2]"


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

    foto = datos.volcado_actual(raw)
    assert sorted(p.name for p in foto.iterdir()) == ["indice.json", "issue_1.json", "issue_2.json"]
    assert not datos.parcial_de(raw).exists()
    publicado = json.loads((foto / "issue_2.json").read_text(encoding="utf-8"))
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
    assert datos.volcado_actual(raw) == raw and not datos.selector_de(raw).exists()


def test_la_foto_visible_no_se_retira_antes_de_seleccionar_la_nueva(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ronda 8 de Codex en la PR #665: apartar el definitivo y renombrar el parcial
    encima dejaba la foto visible AUSENTE entre los dos pasos, y un `SIGKILL` ahi
    no tiene `except` que lo arregle. Ahora el unico instante de cambio es el
    `os.replace` del selector: si falla (o el proceso muere antes), la foto
    anterior sigue publicada intacta y la nueva queda a la vista sin seleccionar."""
    raw = tmp_path / "raw"
    _foto_anterior(raw)
    antes = {p.name: p.read_text(encoding="utf-8") for p in raw.iterdir()}
    parcial = datos.parcial_de(raw)
    parcial.mkdir()
    (parcial / "indice.json").write_text("[1]", encoding="utf-8")

    reemplazar = os.replace

    def reemplazar_salvo_el_selector(origen: object, destino: object) -> None:
        if str(destino).endswith(".actual"):
            raise OSError("sin espacio al seleccionar")
        reemplazar(origen, destino)  # type: ignore[arg-type]

    monkeypatch.setattr(datos.os, "replace", reemplazar_salvo_el_selector)
    with pytest.raises(OSError, match="al seleccionar"):
        datos.publicar_volcado(parcial, raw)

    assert datos.volcado_actual(raw) == raw
    assert {p.name: p.read_text(encoding="utf-8") for p in raw.iterdir()} == antes, (
        "la foto visible no se toca hasta que la nueva esta seleccionada"
    )
    # Ronda 9 de Codex: la foto nueva vuelve a ser el parcial, para que siga
    # siendo una descarga interrumpida a la vista y no una foto huerfana.
    assert parcial.exists() and (parcial / "indice.json").read_text(encoding="utf-8") == "[1]"
    assert datos.fotos_huerfanas(raw) == []


def test_una_foto_que_quedo_sin_seleccionar_se_detecta(tmp_path: Path) -> None:
    """Si el proceso muere entre el renombrado y el selector no hay `except` que
    devuelva nada: queda un directorio `raw.<marca>` que no es la foto
    seleccionada. `fotos_huerfanas` lo encuentra y `analizar.py` avisa en vez de
    usar datos viejos en silencio (Codex, PR #665, ronda 9)."""
    raw = tmp_path / "raw"
    _foto_anterior(raw)
    huerfana = tmp_path / "raw.20260102T120000.000000Z"
    huerfana.mkdir()
    (huerfana / "indice.json").write_text("[1]", encoding="utf-8")
    assert datos.fotos_huerfanas(raw) == [huerfana]

    # Una publicacion completa despues la deja como huerfana y la nueva seleccionada
    parcial = datos.parcial_de(raw)
    parcial.mkdir()
    (parcial / "indice.json").write_text("[2]", encoding="utf-8")
    datos.publicar_volcado(parcial, raw)
    assert datos.fotos_huerfanas(raw) == [huerfana]
    assert (datos.volcado_actual(raw) / "indice.json").read_text(encoding="utf-8") == "[2]"
    # y ni el parcial ni la seleccionada cuentan como huerfanas
    datos.parcial_de(raw).mkdir()
    assert datos.fotos_huerfanas(raw) == [huerfana]


def test_los_avisos_del_volcado_valen_para_cualquier_nombre_logico(tmp_path: Path) -> None:
    """Ronda 10 de Codex en la PR #665: las comprobaciones de descarga interrumpida
    y de foto sin seleccionar valian solo para `raw`; `analizar_pr.py` leia
    `raw_pr` sin ellas. Son una funcion del nombre logico, y los dos analizadores
    la llaman."""
    raw_pr = tmp_path / "raw_pr"
    _foto_anterior(raw_pr)
    assert datos.avisos_de_volcado(raw_pr, "descargar_pr.py") == []

    datos.parcial_de(raw_pr).mkdir()
    (tmp_path / "raw_pr.20260102T120000.000000Z").mkdir()
    avisos = datos.avisos_de_volcado(raw_pr, "descargar_pr.py")
    assert len(avisos) == 2
    assert "descarga interrumpida" in avisos[0] and "descargar_pr.py" in avisos[0]
    assert "sin seleccionar" in avisos[1] and "raw_pr.20260102T120000.000000Z" in avisos[1]

    assert "avisos_de_volcado(RAW_LOGICO" in (MINA / "analizar.py").read_text(encoding="utf-8")
    assert "avisos_de_volcado(PRDIR_LOGICO" in (MINA / "analizar_pr.py").read_text(encoding="utf-8")
