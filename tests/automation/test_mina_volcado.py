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
    assert sorted(p.name for p in foto.iterdir()) == [
        "captura.txt",
        "indice.json",
        "issue_1.json",
        "issue_2.json",
    ]
    assert datos.captura_de(foto), "la foto publicada lleva su marca de captura (ronda 12)"
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


def test_los_avisos_del_volcado_valen_para_cualquier_nombre_logico(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    # Los dos analizadores avisan de TODOS los volcados, lean el que lean (ronda
    # 11: `analizar_pr.py` avisaba de `raw_pr` y leia tambien `raw` sin aviso), y
    # la lista cubre cada nombre logico que `datos` define.
    assert {logico for logico, _ in datos.VOLCADOS} == {datos.RAW_LOGICO, datos.PRDIR_LOGICO}
    for guion in ("analizar.py", "analizar_pr.py"):
        assert "avisos_de_los_volcados()" in (MINA / guion).read_text(encoding="utf-8")
    raw = tmp_path / "raw"
    _foto_anterior(raw)
    monkeypatch.setattr(datos, "VOLCADOS", ((raw, "descargar.py"), (raw_pr, "descargar_pr.py")))
    datos.marcar_captura(raw, "una")
    datos.marcar_captura(raw_pr, "una")
    assert datos.avisos_de_los_volcados() == avisos, "los dos de raw_pr; raw esta limpio"


def test_los_dos_volcados_tienen_que_ser_de_la_misma_captura(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ronda 12 de Codex en la PR #665: dos volcados sanos pueden ser de capturas
    distintas (la cadena murio entre `descargar.py` y `descargar_pr.py`) y las
    cifras que los cruzan saldrian mezcladas sin aviso. `descargar.py` marca la
    captura, `descargar_pr.py` la copia y los analizadores las comparan."""
    raw, raw_pr = tmp_path / "raw", tmp_path / "raw_pr"
    _foto_anterior(raw)
    _foto_anterior(raw_pr)
    monkeypatch.setattr(datos, "VOLCADOS", ((raw, "descargar.py"), (raw_pr, "descargar_pr.py")))
    [sin_marca] = datos.avisos_de_los_volcados()
    assert "sin marca de captura" in sin_marca and str(raw) in sin_marca

    marca = datos.marcar_captura(raw)
    assert datos.marca_de_captura_para_pr(raw, raw_pr) == marca
    datos.marcar_captura(raw_pr, marca)
    assert datos.avisos_de_los_volcados() == []

    # Rondas 14 a 16: una captura de raw empareja UN solo volcado de PR, y la
    # prueba es el propio volcado publicado con su marca, no una senal aparte que
    # pudiera quedarse sin consumir si el proceso muriera despues de publicar.
    # Con raw_pr publicado con la marca de raw, otro descargar_pr.py solo se
    # rechaza ANTES de crear el parcial: no queda ninguna descarga a medias.
    with pytest.raises(SystemExit, match=r"un solo volcado de PR"):
        datos.marca_de_captura_para_pr(raw, raw_pr)
    descargar_pr = _cargar("descargar_pr")
    with pytest.raises(SystemExit, match=r"un solo volcado de PR"):
        descargar_pr.main(prdir=raw_pr, raw=raw)
    assert not datos.parcial_de(raw_pr).exists(), "rechazado antes de crear el parcial"
    assert datos.avisos_de_los_volcados() == []

    datos.marcar_captura(raw, "otra")
    [distintas] = datos.avisos_de_los_volcados()
    assert "capturas distintas" in distintas and "otra" in distintas and marca in distintas

    with pytest.raises(SystemExit, match=r"repite descargar\.py"):
        datos.marca_de_captura_para_pr(tmp_path / "sin-marca", raw_pr)
    for guion, llamada in (
        ("descargar.py", "marcar_captura(parcial)"),
        ("descargar_pr.py", "marca_de_captura_para_pr(raw, prdir)"),
        ("descargar_pr.py", "marcar_captura(parcial, marca)"),
    ):
        assert llamada in (MINA / guion).read_text(encoding="utf-8")


def test_un_analizador_sin_su_volcado_se_detiene(tmp_path: Path) -> None:
    """Ronda 13 de Codex en la PR #665: en un `MINA_DATOS` nuevo, o con un selector
    que nombra una foto que ya no existe, la ausencia entera del volcado era «sin
    avisos» y `analizar_pr.py` publicaba cero PR y cero hallazgos como una
    medicion. La ausencia de lo que se va a medir detiene al analizador."""
    raw_pr = tmp_path / "raw_pr"
    [ausente] = datos.avisos_de_volcado(raw_pr, "descargar_pr.py")
    assert "no hay volcado publicado" in ausente and "descargar_pr.py" in ausente
    with pytest.raises(SystemExit, match=r"ejecuta descargar_pr\.py"):
        datos.exigir_volcado(raw_pr, "descargar_pr.py", "pr_*.json")

    raw_pr.mkdir()
    with pytest.raises(SystemExit, match=r"ningun pr_\*\.json"):
        datos.exigir_volcado(raw_pr, "descargar_pr.py", "pr_*.json"), "vacio tampoco vale"
    (raw_pr / "pr_2.json").write_text("{}", encoding="utf-8")
    (raw_pr / "pr_1.json").write_text("{}", encoding="utf-8")
    assert datos.exigir_volcado(raw_pr, "descargar_pr.py", "pr_*.json") == [
        raw_pr / "pr_1.json",
        raw_pr / "pr_2.json",
    ]
    assert datos.avisos_de_volcado(raw_pr, "descargar_pr.py") == []

    datos.selector_de(raw_pr).write_text("raw_pr.20260102T120000.000000Z\n", encoding="utf-8")
    [ausente] = datos.avisos_de_volcado(raw_pr, "descargar_pr.py")
    assert "raw_pr.20260102T120000.000000Z" in ausente
    with pytest.raises(SystemExit, match=r"raw_pr\.20260102T120000\.000000Z"):
        datos.exigir_volcado(raw_pr, "descargar_pr.py", "pr_*.json")

    # Los dos analizadores exigen lo que leen: `analizar_pr.py` lee los dos volcados.
    analizar = (MINA / "analizar.py").read_text(encoding="utf-8")
    analizar_pr = (MINA / "analizar_pr.py").read_text(encoding="utf-8")
    assert 'exigir_volcado(RAW, "descargar.py", "issue_*.json")' in analizar
    assert 'exigir_volcado(RAW, "descargar.py", "issue_*.json")' in analizar_pr
    assert 'exigir_volcado(PRDIR, "descargar_pr.py", "pr_*.json")' in analizar_pr
    assert "glob.glob(" not in analizar and "glob.glob(" not in analizar_pr


def test_un_comentario_editado_despues_de_la_ventana_no_es_evidencia_de_ella() -> None:
    """Ronda 13 de Codex en la PR #665: la API devuelve el cuerpo vigente con el
    `created_at` original. Un comentario de septiembre editado en octubre entraba
    como evidencia de septiembre y podia cambiar rondas, hallazgos o avisos al
    regenerar el volcado; su cuerpo historico no se puede reconstruir."""
    fin = "2026-09-30T23:59:59Z"
    editado = {"id": 1, "created_at": "2026-09-10T10:00:00Z", "updated_at": "2026-10-02T09:00:00Z"}
    intacto = {"id": 2, "created_at": "2026-09-10T10:00:00Z", "updated_at": "2026-09-10T10:00:00Z"}
    retocado = {"id": 3, "created_at": "2026-09-10T10:00:00Z", "updated_at": "2026-09-30T23:59:59Z"}
    sin_fecha = {"id": 4, "created_at": "2026-09-10T10:00:00Z"}
    assert datos.editado_tras(editado, fin) is True
    assert datos.editado_tras(intacto, fin) is False
    assert datos.editado_tras(retocado, fin) is False, "editado dentro de la ventana: vale"
    assert datos.editado_tras(sin_fecha, fin) is None, "sin updated_at no se puede saber"

    assert datos.avisos_de_editados("las incidencias", fin, [intacto, retocado]) == []
    fuera, sin = datos.avisos_de_editados("las incidencias", fin, [editado, intacto, sin_fecha])
    assert (
        "1 comentarios de las incidencias" in fuera
        and "(1)" in fuera
        and "no se puede reconstruir" in fuera
    )
    assert (
        "1 comentarios de las incidencias no guardan updated_at" in sin and "cadena entera" in sin
    )

    # Todos los lectores del volcado lo aplican y el descargador de PR guarda la fecha.
    for guion in ("analizar.py", "analizar_pr.py", "falsos_negativos.py", "reproducir_avisos.py"):
        assert "editado_tras(c, " in (MINA / guion).read_text(encoding="utf-8"), guion
    for guion in ("analizar.py", "analizar_pr.py"):
        assert "avisos_de_editados(" in (MINA / guion).read_text(encoding="utf-8"), guion
    assert '"updated_at": c.get("updated_at")' in (MINA / "descargar_pr.py").read_text(
        encoding="utf-8"
    )


def test_el_resumen_solo_vale_con_la_foto_de_la_que_salio(tmp_path: Path) -> None:
    """Ronda 16 de Codex en la PR #665: si `descargar.py` publica otra captura y la
    cadena se corta antes de repetir `analizar.py`, los consumidores de
    `resumen.json` leian las incidencias y las horas de una foto y los cuerpos
    de otra. El resumen lleva la marca de su captura y los dos la exigen."""
    raw = tmp_path / "raw"
    _foto_anterior(raw)
    [sin] = datos.exigir_misma_captura("resumen.json", None, raw)
    assert "sin marca de captura" in sin and "resumen.json" in sin
    marca = datos.marcar_captura(raw)
    assert datos.exigir_misma_captura("resumen.json", marca, raw) == []
    [sin] = datos.exigir_misma_captura("resumen.json", None, raw)
    assert "sin marca de captura en resumen.json:" in sin
    with pytest.raises(SystemExit, match=r"repite analizar\.py"):
        datos.exigir_misma_captura("resumen.json", "otra", raw)

    assert '"captura": captura_de(RAW)' in (MINA / "analizar.py").read_text(encoding="utf-8")
    for guion in ("falsos_negativos.py", "reproducir_avisos.py"):
        texto = (MINA / guion).read_text(encoding="utf-8")
        assert 'exigir_misma_captura("resumen.json", resumen.get("captura"), RAW)' in texto, guion
