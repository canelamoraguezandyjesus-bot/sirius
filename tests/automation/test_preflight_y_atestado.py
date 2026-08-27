"""El instrumento del que cuelga todo, que hasta hoy no tenía ni un guardián.

`preflight.py` es lo único que separa «este nombre lo saqué de un papel» de «este
nombre me contestó hace un rato». Y estaba **sin una sola prueba**: comprobado el
27-08-2026 con `grep -rln preflight tests/`, vacío.

Eso no es un descuido menor. Es la pieza que ADR-095 pone en el centro para que
no vuelva a pasar lo de la noche del 26: cuatro rondas configurando modelos
muertos, con 33 guardianes en verde vigilando el arnés equivocado.

Las tres propiedades que se fijan aquí son las tres que fallaron esa noche:

1. **El instrumento recuerda.** Sin memoria volvía a gastar su tope probando
   cadáveres que el propio servidor ya había descartado.
2. **Lo nuevo va antes que lo viejo.** El orden alfabético pone `gemini-2.5`
   delante de `gemini-3.5`, y la generación 2.5 entera estaba muerta: ordenar por
   texto es ordenar por antigüedad, al revés de lo que interesa.
3. **Sin atestado no se mide.** Un número medido sobre un modelo muerto es peor
   que no tener número, porque se cree.

Todo determinista: sin red, sin claves, sin llamar a ningún modelo.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PREFLIGHT = RAIZ / "scripts" / "investigacion" / "preflight.py"
COMPARADOR = RAIZ / "scripts" / "investigacion" / "comparar_investigadores.py"


def _modulo(ruta: Path, nombre: str) -> Any:
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    assert spec and spec.loader, f"no se pudo cargar {ruta}"
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _preflight() -> Any:
    return _modulo(PREFLIGHT, "_preflight_bajo_prueba")


def _comparador() -> Any:
    return _modulo(COMPARADOR, "_comparador_bajo_prueba")


def _atestado(tmp_path: Path, cuerpo: str) -> Path:
    ruta = tmp_path / "modelos_atestiguados.yml"
    ruta.write_text(cuerpo, encoding="utf-8")
    return ruta


# --------------------------------------------------------------------------- #
# 1. El instrumento recuerda
# --------------------------------------------------------------------------- #


def test_no_vuelve_a_proponer_un_modelo_que_ya_dijo_que_no_sirve(tmp_path: Path) -> None:
    """La cuarta ronda del 26-08, fijada.

    El servidor ya había contestado que `gemini-2.5-flash` no está disponible. Sin
    memoria, el instrumento volvía a proponerlo, y probar dos veces lo mismo no es
    probar: es repetir.
    """
    modulo = _preflight()
    ruta = _atestado(
        tmp_path,
        """
version: 1
proveedores:
  google:
    modelos:
      "models/gemini-2.5-flash":
        existe: true
        usable: false
""",
    )
    assert "models/gemini-2.5-flash" in modulo._muertos_conocidos(ruta)

    # Y AHORA LO QUE DE VERDAD IMPORTA: que `_candidatos` la USE.
    #
    # ESTA MITAD NACIÓ DE UNA MUTACIÓN QUE NO FALLÓ. La primera versión de esta
    # prueba se quedaba en la línea de arriba, y al sustituir la llamada real por
    # `muertos = set()` seguía en verde: comprobaba que la memoria EXISTIERA, no
    # que estuviera CONECTADA. Es el tercer guardián vacuo de la misma noche y
    # exactamente la raíz que ADR-095 nombra —probar la pieza en vez del cable—.
    monkeypatch = None  # se apaña sin fixture: se sustituye el módulo entero
    original = modulo.ATESTADO
    try:
        modulo.ATESTADO = ruta
        catalogo = ["models/gemini-2.5-flash", "models/gemini-3.5-flash"]
        propuestos = modulo._candidatos("google", catalogo, "gemini", 2)
        assert "models/gemini-2.5-flash" not in propuestos, (
            f"`_candidatos` propone un modelo que el atestado da por muerto: "
            f"{propuestos}. La memoria existe pero no está conectada."
        )
        assert propuestos == ["models/gemini-3.5-flash"]
    finally:
        modulo.ATESTADO = original
    assert monkeypatch is None


def test_no_saber_no_es_lo_mismo_que_saber_que_esta_muerto(tmp_path: Path) -> None:
    """Anti-vacua, y una garantía por sí misma.

    Si `_muertos_conocidos` devolviera cualquier cosa ante un atestado ausente o
    ilegible, descartaría modelos buenos sin ninguna prueba. Ante la duda no se
    descarta nada: lo contrario sería inventar un veredicto.
    """
    modulo = _preflight()
    assert modulo._muertos_conocidos(tmp_path / "no-existe.yml") == set()
    assert modulo._muertos_conocidos(_atestado(tmp_path, "esto: [no es, valido")) == set()


def test_un_modelo_usable_no_cuenta_como_muerto(tmp_path: Path) -> None:
    """Anti-vacua: un `return todos` pasaría la primera prueba sin mérito."""
    modulo = _preflight()
    ruta = _atestado(
        tmp_path,
        """
version: 1
proveedores:
  google:
    modelos:
      "models/gemini-3.5-flash":
        existe: true
        usable: true
""",
    )
    assert "models/gemini-3.5-flash" not in modulo._muertos_conocidos(ruta)


# --------------------------------------------------------------------------- #
# 2. Lo nuevo antes que lo viejo
# --------------------------------------------------------------------------- #


def test_lo_nuevo_va_antes_que_lo_viejo() -> None:
    """El orden alfabético es orden de antigüedad, justo al revés de lo útil.

    MEDIDO el 27-08: con el orden por texto, `_candidatos(..., tope=4)` devolvía
    tres modelos de la generación 2.5 —declarada muerta una hora antes— y solo uno
    de la 3.x.
    """
    modulo = _preflight()
    catalogo = [
        "models/gemini-2.5-flash",
        "models/gemini-2.5-pro",
        "models/gemini-3-flash",
        "models/gemini-3.5-flash",
        "models/gemini-3.7-flash",
    ]
    orden = modulo._candidatos("google", catalogo, "gemini", 3)
    assert orden[0] == "models/gemini-3.7-flash", (
        f"el primer candidato es {orden[0]}: se sigue probando lo viejo primero"
    )
    assert not any("2.5" in m for m in orden), (
        f"la generación vieja se cuela en los tres primeros: {orden}"
    )


def test_lo_especial_y_las_previews_van_al_final() -> None:
    """Audio, imagen y previews no son modelos de trabajo diario.

    Y una preview puede desaparecer sin aviso: elegirla sería volver a atarse a
    algo perecedero, que es la raíz que ADR-095 nombra.
    """
    modulo = _preflight()
    catalogo = [
        "models/gemini-3.5-flash-image",
        "models/gemini-3.5-flash-preview",
        "models/gemini-3.5-flash",
    ]
    orden = modulo._candidatos("google", catalogo, "gemini", 3)
    assert orden[0] == "models/gemini-3.5-flash"
    assert orden[-1] == "models/gemini-3.5-flash-image"


# --------------------------------------------------------------------------- #
# 3. Sin atestado no se mide
# --------------------------------------------------------------------------- #


class _Config:
    def __init__(self, entorno: dict[str, str]) -> None:
        self.entorno = entorno


def test_sin_atestado_no_se_mide(tmp_path: Path) -> None:
    """La pieza que hace IMPOSIBLE lo que casi pasa cuatro veces.

    Medir con guardianes en verde sobre un modelo que el proveedor ya retiró. Un
    número sobre un cadáver es peor que no tener número, porque se cree.
    """
    modulo = _comparador()
    config = _Config({"FAST_LLM": "google_genai:gemini-3.5-flash"})
    faltan = modulo.modelos_sin_atestado([config], tmp_path / "no-existe.yml")
    assert faltan == ["gemini-3.5-flash"], (
        f"sin fichero de atestado el guardián deja pasar la medición: devolvió {faltan}"
    )


def test_un_atestado_caducado_no_vale(tmp_path: Path) -> None:
    """Un catálogo se pudre en semanas: la familia `gemini-2.5` entera murió así.

    Por eso el atestado tiene fecha y caduca. Sin caducidad volvería a ser un
    documento, que es de donde venían los cuatro nombres muertos.
    """
    modulo = _comparador()
    ruta = _atestado(
        tmp_path,
        """
version: 1
proveedores:
  google:
    modelos:
      "gemini-3.5-flash":
        existe: true
        usable: true
        fecha_utc: 2020-01-01T00:00:00Z
""",
    )
    config = _Config({"FAST_LLM": "google_genai:gemini-3.5-flash"})
    faltan = modulo.modelos_sin_atestado([config], ruta, ahora="2026-08-27T00:00:00+00:00")
    assert faltan == ["gemini-3.5-flash"], "un atestado de 2020 se dio por bueno"


def test_un_atestado_fresco_y_usable_si_deja_medir(tmp_path: Path) -> None:
    """Anti-vacua: un guardián que siempre dice que no también pasaría las de arriba."""
    modulo = _comparador()
    ruta = _atestado(
        tmp_path,
        """
version: 1
proveedores:
  google:
    modelos:
      "gemini-3.5-flash":
        existe: true
        usable: true
        fecha_utc: 2026-08-26T12:00:00Z
""",
    )
    config = _Config({"FAST_LLM": "google_genai:gemini-3.5-flash"})
    assert modulo.modelos_sin_atestado([config], ruta, ahora="2026-08-27T00:00:00+00:00") == []


def test_un_modelo_que_existe_pero_no_responde_no_deja_medir(tmp_path: Path) -> None:
    """`usable: false` es el caso de los tres 404 de la noche.

    Existir en el catálogo y responder son dos cosas distintas, y el guardián
    tiene que exigir la segunda.
    """
    modulo = _comparador()
    ruta = _atestado(
        tmp_path,
        """
version: 1
proveedores:
  google:
    modelos:
      "gemini-2.5-flash":
        existe: true
        usable: false
        fecha_utc: 2026-08-26T12:00:00Z
""",
    )
    config = _Config({"FAST_LLM": "google_genai:gemini-2.5-flash"})
    assert modulo.modelos_sin_atestado([config], ruta, ahora="2026-08-27T00:00:00+00:00") == [
        "gemini-2.5-flash"
    ]


def test_un_atestado_ilegible_no_deja_medir(tmp_path: Path) -> None:
    """Ante la duda se para. No poder comprobarlo es el peor motivo para seguir."""
    modulo = _comparador()
    ruta = _atestado(tmp_path, "esto: [no cierra")
    config = _Config({"FAST_LLM": "google_genai:gemini-3.5-flash"})
    assert modulo.modelos_sin_atestado([config], ruta) == ["gemini-3.5-flash"]


# --------------------------------------------------------------------------- #
# 4. Ninguna clave sale de aquí
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("texto", "clave", "esperado"),
    [
        ("HTTP 401 con Bearer abc12345secreta", "abc12345secreta", False),
        ("sin claves dentro", "abc12345secreta", True),
    ],
)
def test_ninguna_clave_sobrevive_al_tapado(texto: str, clave: str, esperado: bool) -> None:
    """El texto de una excepción HTTP puede traer dentro la cabecera de auth.

    Y ese texto acaba en el JSON que se sube como artefacto.
    """
    modulo = _preflight()
    tapado = modulo._sin_clave(texto, clave)
    assert (clave not in tapado) is True
    assert (tapado == texto) is esperado


# --------------------------------------------------------------------------- #
# El banco de preguntas: lo perecedero se declara perecedero
# --------------------------------------------------------------------------- #
#
# Un refutador señaló que ninguna de las cinco preguntas originales obliga a
# buscar: son hechos estables que cualquier modelo útil recita. Con el buscador
# muerto habrían dado 100 %.
#
# La primera mitad del arreglo fue estructural (`fuentes > 0`). La segunda son
# preguntas cuya respuesta CAMBIA, y por eso caducan: si nadie las revisa, dentro
# de unos meses su respuesta correcta será otra y el banco suspenderá informes
# buenos. Es la misma lección que ADR-095 sacó de los modelos.


def _banco() -> dict[str, Any]:
    import yaml

    ruta = RAIZ / "scripts" / "investigacion" / "preguntas.yml"
    return dict(yaml.safe_load(ruta.read_text(encoding="utf-8")))


def test_hay_preguntas_que_un_modelo_no_puede_recitar() -> None:
    """Sin alguna perecedera, un buscador muerto puede sacar buena nota."""
    obligadas = [q for q in _banco()["preguntas"] if q.get("tipo") == "busqueda_obligada"]
    assert obligadas, (
        "el banco no tiene ninguna pregunta cuya respuesta cambie con el tiempo: "
        "todas se pueden contestar de memoria, y entonces mide al modelo y no al "
        "investigador"
    )


def test_toda_pregunta_perecedera_declara_cuando_caduca() -> None:
    """Lo perecedero se declara perecedero, o se pudre en silencio.

    Una pregunta cuya respuesta cambia y NO dice cuándo revisarla es una trampa
    con fecha de explosión: llegará el día en que suspenda informes correctos y
    nadie sabrá por qué.
    """
    from datetime import date

    sin_fecha = [
        q["id"]
        for q in _banco()["preguntas"]
        if q.get("tipo") == "busqueda_obligada" and not isinstance(q.get("revisar_antes_de"), date)
    ]
    assert sin_fecha == [], (
        f"preguntas perecederas sin fecha de revisión: {sin_fecha}. "
        "Su respuesta correcta cambiará y el banco empezará a suspender informes buenos."
    )


def test_toda_pregunta_tiene_algo_que_corregir() -> None:
    """Una pregunta sin cadenas obligatorias es un aprobado automático.

    `_corrige(texto, [])` devuelve True: bastaría una clave mal escrita en el YAML
    para regalar un punto.
    """
    vacias = [q["id"] for q in _banco()["preguntas"] if not q.get("obligatorias")]
    assert vacias == [], f"preguntas sin nada que corregir, o sea aprobado gratis: {vacias}"
