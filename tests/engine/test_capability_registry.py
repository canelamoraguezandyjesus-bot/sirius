"""Registro versionado de capacidades (arquitectura §6, incidencia #202)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius_engine.capability_registry import load_capability_registry


def test_carga_el_registro_real_y_conoce_las_capacidades_de_los_perfiles() -> None:
    registro = load_capability_registry()
    assert registro.version >= 1
    for nombre in (
        "incidencia.leer",
        "repo.leer",
        "repo.escribir",
        "pr.crear",
        "validaciones.ejecutar",
        "veredicto.escribir",
        "contexto.recuperar",
        "web.buscar",
    ):
        definicion = registro.obtener(nombre)
        assert definicion is not None, f"falta {nombre!r} en el registro real"
        assert definicion.nombre == nombre


def test_capacidad_ausente_devuelve_none_sin_lanzar() -> None:
    registro = load_capability_registry()
    assert registro.obtener("no.existe") is None


def test_web_buscar_es_la_unica_capacidad_de_red_del_registro_real() -> None:
    registro = load_capability_registry()
    con_red = {n for n, d in registro.capacidades.items() if d.red}
    assert con_red == {"web.buscar"}


def test_cargar_desde_un_fichero_explicito(tmp_path: Path) -> None:
    ruta = tmp_path / "registro.yml"
    ruta.write_text(
        "version: 7\ncapacidades:\n  x.y:\n"
        "    proveedor: funcion_local\n    red: false\n    escritura: true\n"
        "    ambitos_escritura: [ambito_x]\n",
        encoding="utf-8",
    )
    registro = load_capability_registry(ruta)
    assert registro.version == 7
    definicion = registro.obtener("x.y")
    assert definicion is not None
    assert definicion.proveedor == "funcion_local"
    assert definicion.escritura is True
    assert definicion.ambitos_escritura == frozenset({"ambito_x"})


@pytest.mark.parametrize(
    "contenido",
    [
        "version: 1\ncapacidades: no-es-un-mapeo\n",
        "no-es-un-mapeo",
        "capacidades:\n  x: {}\n",  # falta version
        "version: uno\ncapacidades: {}\n",  # version no es entero
        # CODEX-001 (ronda 5): 'escritura: true' sin ámbito declarado no debe
        # cargar -dejaría la capacidad sin ningún ámbito que la conceda
        # nunca, en vez de fallar explícito en el momento de definirla.
        "version: 1\ncapacidades:\n  x.y:\n"
        "    proveedor: funcion_local\n    red: false\n    escritura: true\n",
        # ... ni con la lista vacía explícita.
        "version: 1\ncapacidades:\n  x.y:\n"
        "    proveedor: funcion_local\n    red: false\n    escritura: true\n"
        "    ambitos_escritura: []\n",
        # 'escritura: false' con ámbitos declarados tampoco es válido: una
        # capacidad de solo lectura no tiene ámbito de escritura que cruzar.
        "version: 1\ncapacidades:\n  x.y:\n"
        "    proveedor: funcion_local\n    red: false\n    escritura: false\n"
        "    ambitos_escritura: [repo]\n",
    ],
)
def test_registro_malformado_lanza_error_explicito(tmp_path: Path, contenido: str) -> None:
    ruta = tmp_path / "registro.yml"
    ruta.write_text(contenido, encoding="utf-8")
    with pytest.raises(ValueError):
        load_capability_registry(ruta)
