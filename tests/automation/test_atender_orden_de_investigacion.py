"""B1 (ADR-099): el padre que atiende una orden de investigación.

Estas pruebas ejecutan `atender_orden.main` REAL con un hijo fingido, igual que
las del comparador: la propiedad importante no es que las funciones existan,
sino que el protocolo con el ciclo se cumpla —veredicto provisional ANTES de
tocar nada, definitivo al final, y un documento que su propio guardián de
caducidad no mate en Quality—.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
INVESTIGACION = RAIZ / "scripts" / "investigacion"


def _modulo(ruta: Path, nombre: str) -> Any:
    cacheado = sys.modules.get(nombre)
    if cacheado is not None:
        return cacheado
    if str(INVESTIGACION) not in sys.path:
        # `atender_orden` importa a su hermano `comparar_investigadores` por
        # nombre, como cuando corre de verdad (sys.path[0] es su carpeta).
        sys.path.insert(0, str(INVESTIGACION))
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _atendedor() -> Any:
    return _modulo(INVESTIGACION / "atender_orden.py", "atender_orden_bajo_prueba")


CUERPO = """## Work ID

WI-X

## Objetivo

Investiga cual es la ultima version estable de Python
y cuando salio.

## Alcance permitido

Nada mas.
"""


def test_extraer_pregunta_lee_el_objetivo_entero() -> None:
    a = _atendedor()
    pregunta = a.extraer_pregunta(CUERPO)
    assert "ultima version estable de Python" in pregunta
    assert "cuando salio" in pregunta
    assert "Alcance" not in pregunta, "se llevó la sección siguiente por delante"


def test_sin_objetivo_no_hay_pregunta() -> None:
    a = _atendedor()
    assert a.extraer_pregunta("## Work ID\n\nWI-X\n") == ""


def test_el_documento_pasa_el_guardian_de_caducidad() -> None:
    """Pregunta 3 de la nota de arranque: el guardián corre en Quality sobre la
    PR del propio informe. Se comprueba con el MISMO parser del guardián."""
    a = _atendedor()
    texto = a.componer_documento(
        pregunta="¿Cuál es la última versión estable de Python?",
        informe="# Informe\n\nPython 3.13 es la última estable.",
        fuentes=["https://python.org", "https://peps.python.org"],
        numero=555,
        fecha="2026-08-28",
    )
    assert texto.startswith("---\n")
    fin = texto.find("\n---\n", 4)
    cabecera = dict(yaml.safe_load(texto[4:fin]))
    for campo in ("titulo", "fecha", "pregunta", "caduca_con", "estado"):
        assert campo in cabecera, f"falta {campo}: el guardián mataría el informe en su PR"
    assert cabecera["estado"] == "VIGENTE"
    assert "https://python.org" in texto


def test_el_documento_declara_el_tipo_real_que_corrio() -> None:
    """CODEX-002 (revisión de la PR #393): la cabecera tiene que nombrar el
    `report_type` con el que corrió el hijo. `research_report` está reservado
    al banco (`medir_investigador.py`); declararlo para una orden que corrió en
    `deep` confunde la procedencia del documento con la del banco."""
    a = _atendedor()
    texto = a.componer_documento(
        pregunta="x",
        informe="# Informe\n\nx.",
        fuentes=["https://a.example"],
        numero=1,
        fecha="2026-08-28",
        tipo="deep",
    )
    assert "`deep`" in texto
    assert "`research_report`" not in texto


def _correr_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    cuerpo: str = CUERPO,
    guion_hijo: str | None = None,
) -> tuple[int, dict[str, Any], Path]:
    a = _atendedor()
    if guion_hijo is not None:
        hijo = tmp_path / "hijo.py"
        hijo.write_text(guion_hijo, encoding="utf-8")
        monkeypatch.setattr(a, "HIJO", hijo)
    monkeypatch.setenv("NVIDIA_API_KEY", "clave-falsa-de-prueba")
    fichero_cuerpo = tmp_path / "cuerpo.md"
    fichero_cuerpo.write_text(cuerpo, encoding="utf-8")
    veredicto = tmp_path / "veredicto.json"
    salida_dir = tmp_path / "investigaciones"
    salida_dir.mkdir()
    codigo = a.main(
        [
            "--cuerpo",
            str(fichero_cuerpo),
            "--numero",
            "555",
            "--veredicto",
            str(veredicto),
            "--plazo",
            "60",
            "--salida-dir",
            str(salida_dir),
        ]
    )
    return codigo, dict(json.loads(veredicto.read_text(encoding="utf-8"))), salida_dir


HIJO_QUE_INVESTIGA = """
import json, sys
salida = sys.argv[sys.argv.index("--salida") + 1]
json.dump({"pregunta": "x", "informe": "# Informe\\n\\nPython 3.13.",
           "fuentes": ["https://python.org"], "error": None,
           "cortada_por_plazo": False}, open(salida, "w", encoding="utf-8"))
sys.exit(0)
"""

HIJO_QUE_MUERE_SIN_ESCRIBIR = """
import sys
sys.exit(1)
"""


def test_con_informe_y_fuentes_el_veredicto_es_ready_y_el_documento_existe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codigo, veredicto, salida_dir = _correr_main(
        tmp_path, monkeypatch, guion_hijo=HIJO_QUE_INVESTIGA
    )
    assert codigo == 0
    assert veredicto["verdict"] == "READY_FOR_REVIEW", veredicto
    documentos = list(salida_dir.glob("*.md"))
    assert len(documentos) == 1, "el informe no se escribió"
    assert veredicto.get("ruta_informe"), "el workflow no sabría qué fichero confirmar"
    assert "orden-555" in documentos[0].name
    assert "`deep`" in documentos[0].read_text(encoding="utf-8"), (
        "el tipo por defecto de una orden es `deep`; el documento tiene que decirlo"
    )


def test_si_el_hijo_muere_queda_failed_safely_y_ningun_documento(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pregunta 4: si el proceso muere, el ciclo encuentra un veredicto, no un
    silencio. El hijo de esta prueba ni escribe su JSON."""
    codigo, veredicto, salida_dir = _correr_main(
        tmp_path, monkeypatch, guion_hijo=HIJO_QUE_MUERE_SIN_ESCRIBIR
    )
    assert codigo != 0
    assert veredicto["verdict"] == "FAILED_SAFELY"
    assert list(salida_dir.glob("*.md")) == [], "publicó un documento sin investigación"


def test_sin_objetivo_el_veredicto_lo_dice_sin_lanzar_al_hijo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codigo, veredicto, _salida = _correr_main(
        tmp_path,
        monkeypatch,
        cuerpo="## Work ID\n\nWI-X\n",
        guion_hijo="raise SystemExit('el hijo no debia arrancar')",
    )
    assert codigo != 0
    assert veredicto["verdict"] == "FAILED_SAFELY"
    assert "Objetivo" in veredicto["summary"]


def test_el_provisional_se_escribe_antes_de_nada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El hijo de esta prueba LEE el veredicto mientras corre: si el provisional
    no estuviera ya escrito, el ciclo se quedaría sin nada ante una muerte."""
    guion = """
import json, sys, os
veredicto = os.environ.get("RUTA_VEREDICTO_DE_PRUEBA")
contenido = json.load(open(veredicto, encoding="utf-8"))
assert contenido["verdict"] == "FAILED_SAFELY", contenido
salida = sys.argv[sys.argv.index("--salida") + 1]
json.dump({"pregunta": "x", "informe": "# I\\n\\nx.", "fuentes": ["https://a"],
           "error": None, "cortada_por_plazo": False},
          open(salida, "w", encoding="utf-8"))
sys.exit(0)
"""
    # El hijo corre con el entorno construido desde cero, así que la ruta se le
    # pasa por la única vía que ese entorno respeta: una variable declarada.
    a = _atendedor()
    original = a.entorno_desde_cero

    def _con_ruta(configuracion: Any, clave: str) -> dict[str, str]:
        entorno = dict(original(configuracion, clave))
        entorno["RUTA_VEREDICTO_DE_PRUEBA"] = str(tmp_path / "veredicto.json")
        return entorno

    monkeypatch.setattr(a, "entorno_desde_cero", _con_ruta)
    codigo, veredicto, _salida = _correr_main(tmp_path, monkeypatch, guion_hijo=guion)
    assert codigo == 0, veredicto
    assert veredicto["verdict"] == "READY_FOR_REVIEW"


def _hijo_real(monkeypatch: pytest.MonkeyPatch) -> Any:
    """El hijo DE VERDAD (`investigar_orden`), con la herramienta fingida.

    Las pruebas de arriba fingen al hijo entero, así que su regla «sin fuentes
    no se publica» quedaba sin ejecutar -la mutación M5 lo demostró pasando en
    verde-. Aquí se carga el módulo real y solo se finge `_investigar`.
    """
    hijo = _modulo(INVESTIGACION / "investigar_orden.py", "investigar_orden_bajo_prueba")
    monkeypatch.setattr(hijo, "_version_instalada", lambda: hijo.VERSION_EXIGIDA)
    return hijo


def test_el_hijo_no_publica_un_informe_sin_fuentes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La regla del banco aplicada a las órdenes (ADR-099, punto 5): cero
    fuentes es el modelo recitando, no una investigación."""
    hijo = _hijo_real(monkeypatch)

    async def _recita(_pregunta: str, _tipo: str = "research_report") -> tuple[str, list[str]]:
        return "# Informe precioso\n\nTodo de memoria.", []

    monkeypatch.setattr(hijo, "_investigar", _recita)
    salida = tmp_path / "resultado.json"
    codigo = hijo.main(["--pregunta", "x", "--salida", str(salida), "--plazo", "30"])
    assert codigo != 0, "un informe con cero fuentes salió en verde"
    resultado = json.loads(salida.read_text(encoding="utf-8"))
    assert "fuentes" in str(resultado["error"]).lower()


def test_el_hijo_no_publica_planificacion_sin_sintetizar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Revisión de la PR #393 (CODEX-001): la orden #392 publicó el borrador de
    razonamiento del modelo en inglés, con fuentes de verdad, así que la regla
    `fuentes > 0` no lo paró. Hace falta una regla propia."""
    hijo = _hijo_real(monkeypatch)

    async def _planifica(_pregunta: str, _tipo: str = "research_report") -> tuple[str, list[str]]:
        borrador = (
            "We need to produce a comprehensive research report in Spanish. "
            "We need to synthesize from the provided text. Let's extract info: "
            "NVIDIA NIM free tier is 40 RPM. We must be objective and impartial."
        )
        return borrador, ["https://a.example", "https://b.example"]

    monkeypatch.setattr(hijo, "_investigar", _planifica)
    salida = tmp_path / "resultado.json"
    codigo = hijo.main(["--pregunta", "x", "--salida", str(salida), "--plazo", "30"])
    assert codigo != 0, "un borrador de planificación sin sintetizar salió en verde"
    resultado = json.loads(salida.read_text(encoding="utf-8"))
    assert "sintetiz" in str(resultado["error"]).lower()


def test_el_hijo_con_fuentes_sale_en_verde_y_deja_todo_en_su_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Anti-vacua de la anterior: la regla no puede suspenderlo todo."""
    hijo = _hijo_real(monkeypatch)

    async def _investiga(_pregunta: str, _tipo: str = "research_report") -> tuple[str, list[str]]:
        return "# Informe\n\nCon fuentes.", ["https://a.example", "https://b.example"]

    monkeypatch.setattr(hijo, "_investigar", _investiga)
    salida = tmp_path / "resultado.json"
    codigo = hijo.main(["--pregunta", "x", "--salida", str(salida), "--plazo", "30"])
    assert codigo == 0
    resultado = json.loads(salida.read_text(encoding="utf-8"))
    assert resultado["error"] is None
    assert resultado["fuentes"] == ["https://a.example", "https://b.example"]


# --- Las tres palancas (28-08-2026): tipo por camino, idioma y palabras -------


def test_el_tipo_de_informe_llega_al_hijo_y_por_defecto_es_deep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pregunta 1 de la nota de arranque: `--tipo` DE VERDAD en el argv del hijo.

    El hijo de esta prueba retrata su argv en el JSON: si el padre no pasara el
    tipo, el modo profundo sería una opción que nadie usa —la pieza sin cable—.
    """
    guion = """
import json, sys
salida = sys.argv[sys.argv.index("--salida") + 1]
json.dump({"pregunta": "x", "informe": "# I\\n\\nx.", "fuentes": ["https://a"],
           "error": None, "cortada_por_plazo": False, "argv": sys.argv[1:]},
          open(salida, "w", encoding="utf-8"))
sys.exit(0)
"""
    codigo, veredicto, _salida = _correr_main(tmp_path, monkeypatch, guion_hijo=guion)
    assert codigo == 0, veredicto
    resultado = json.loads((tmp_path / "investigacion-555.json").read_text(encoding="utf-8"))
    argv = list(resultado["argv"])
    assert "--tipo" in argv, "el padre no pasa el tipo: el modo profundo no lo usa nadie"
    assert argv[argv.index("--tipo") + 1] == "deep", (
        "las órdenes tienen que ir en profundo por defecto (nota de arranque de "
        "las tres palancas); el banco es quien se queda en research_report"
    )


def test_el_banco_sigue_en_research_report() -> None:
    """Pregunta 2: si el banco se volviera profundo por accidente, sus 7
    preguntas costarían ~10x y el número cambiaría de significado sin que
    nadie lo decidiera."""
    medidor = (INVESTIGACION / "medir_investigador.py").read_text(encoding="utf-8")
    assert 'report_type="research_report"' in medidor, (
        "el banco ya no fija research_report: su número dejaría de ser comparable "
        "con las pasadas anteriores"
    )


def test_el_idioma_y_las_palabras_llegan_al_entorno_del_hijo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pregunta 3: la configuración declara español y 2500 palabras, y el hijo
    las RECIBE (retrato del entorno del subproceso real)."""
    c = _atendedor()
    configuraciones = c.cargar_configuraciones(INVESTIGACION / "configuraciones.yml")
    entorno = configuraciones[0].entorno
    assert entorno.get("LANGUAGE") == "spanish", (
        "el primer examen salió en inglés y la palanca del idioma no está echada"
    )
    assert entorno.get("TOTAL_WORDS") == "2500"
    monkeypatch.setenv(configuraciones[0].variable_de_clave, "clave-falsa-de-prueba")
    recibido = c.entorno_desde_cero(configuraciones[0], "clave-falsa-de-prueba")
    assert recibido.get("LANGUAGE") == "spanish"
    assert recibido.get("TOTAL_WORDS") == "2500"
