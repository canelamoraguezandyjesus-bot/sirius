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


# --------------------------------------------------------------------------- #
# «Ocupado» no es «muerto»
# --------------------------------------------------------------------------- #
#
# MEDIDO EN LA PRIMERA PASADA REAL DEL BANCO, el 27-08-2026. `gemini-3.5-flash`
# contestó:
#
#     HTTP 503: "This model is currently experiencing high demand."
#
# y el guardián lo marcó NO RESPONDE, negándose a medir. Que se negara está
# bien —no se mide lo que no contesta—, pero el mensaje habría hecho **cambiar un
# modelo que está perfectamente vivo**.
#
# Es el defecto de esta casa visto del revés: en vez de un verde que miente, un
# ROJO que miente. Y cuesta lo mismo: mandar a buscar un sustituto que no hacía
# falta es exactamente como se perdió una noche.


def test_un_503_no_se_confunde_con_un_modelo_muerto() -> None:
    """Un 503 es «vuelve luego»; un 404 es «no existe». No son lo mismo."""
    modulo = _preflight()
    assert 503 in modulo.CODIGOS_TRANSITORIOS
    assert 429 in modulo.CODIGOS_TRANSITORIOS, "un límite de ritmo también es transitorio"
    assert 404 not in modulo.CODIGOS_TRANSITORIOS, (
        "un 404 se daría por transitorio y se reintentaría para siempre un modelo "
        "que de verdad no existe"
    )
    assert 401 not in modulo.CODIGOS_TRANSITORIOS, (
        "una clave mala no se arregla esperando, y reintentarla esconde el motivo"
    )


def test_lo_transitorio_se_reintenta_y_lo_definitivo_no(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reintentar un 404 sería insistir en algo que no va a cambiar.

    Se ejecuta el `_pedir` real con el intento sustituido, y se cuenta cuántas
    veces llama: es la diferencia entre comprobar la constante y comprobar el
    comportamiento.
    """
    modulo = _preflight()
    monkeypatch.setattr(modulo, "REINTENTOS", 3)
    monkeypatch.setattr(
        modulo.time if hasattr(modulo, "time") else modulo, "sleep", lambda _s: None, raising=False
    )

    for codigo, esperados in ((503, 3), (404, 1), (200, 1)):
        llamadas = {"n": 0}

        def _falso(
            *_a: object,
            _c: int = codigo,
            _cuenta: dict[str, int] = llamadas,
            **_k: object,
        ) -> tuple[int, object, str]:
            # Se atan `codigo` y `llamadas` por valor por defecto: capturarlas del
            # bucle haría que las tres vueltas compartieran la última, y la prueba
            # mediría siempre el mismo caso creyendo que mide tres.
            _cuenta["n"] += 1
            return _c, {"ok": True}, ""

        monkeypatch.setattr(modulo, "_una_peticion", _falso)
        import time as _t

        monkeypatch.setattr(_t, "sleep", lambda _s: None)
        modulo._pedir("https://ejemplo.invalido", "clave", "Authorization", "Bearer ")
        assert llamadas["n"] == esperados, (
            f"con HTTP {codigo} se llamó {llamadas['n']} veces y debían ser {esperados}"
        )


def test_el_informe_distingue_tres_estados_y_no_dos() -> None:
    """Decir «no sirve» cuando es «vuelve luego» manda a cambiar lo que está bien.

    El resumen tiene que ofrecer un tercer estado y, además, decir en voz alta
    que NO se cambie el modelo: sin esa frase, quien lea el rojo hará lo de
    siempre y buscará un sustituto.
    """
    fuente = Path(_preflight().__file__).read_text(encoding="utf-8")
    assert "sin_comprobar" in fuente, "el informe no distingue «ocupado» de «no sirve»"
    assert "NO cambies el modelo" in fuente, (
        "el aviso no dice lo único que hay que hacer ante un transitorio: esperar"
    )


# --- El atestado del buscador: la tercera pregunta de la escalera -------------
#
# Pasada 4 del banco (28-08-2026): la clave de Tavily estaba puesta y llegaba al
# subproceso, y las fuentes siguieron a cero, identico a la pasada sin clave.
# Nadie podia distinguir clave mala / forma de llamada rechazada / vacio por
# otra causa, porque nadie le hacia al servidor la pregunta exacta: ¿respondes a
# LA LLAMADA QUE HACE LA HERRAMIENTA (clave en el cuerpo, sin Authorization)?


def _atestado_de_buscador_con(
    monkeypatch: pytest.MonkeyPatch, *, codigo: int, datos: object, error: str = ""
) -> dict[str, object]:
    modulo = _preflight()
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-clave-de-prueba-larga")
    capturas: list[tuple[str, str]] = []

    def _falso(
        url: str, clave: str, cabecera: str, prefijo: str, cuerpo: object = None
    ) -> tuple[int, object, str]:
        capturas.append((cabecera, str(cuerpo)))
        return codigo, datos, error

    monkeypatch.setattr(modulo, "_pedir", _falso)
    informe = modulo.atestar_buscador()
    # La forma de la llamada es la mitad del atestado: sin cabecera de
    # autorizacion y con la clave en el cuerpo, como la 0.15.1. Atestar otra
    # llamada seria medir otra cosa.
    cabecera, cuerpo = capturas[0]
    assert cabecera == "", f"el atestado manda cabecera de autorizacion: {cabecera!r}"
    assert "api_key" in cuerpo, "el atestado no manda la clave en el cuerpo"
    return dict(informe)


def test_el_buscador_con_resultados_es_usable(monkeypatch: pytest.MonkeyPatch) -> None:
    informe = _atestado_de_buscador_con(
        monkeypatch, codigo=200, datos={"results": [{"url": "a"}, {"url": "b"}]}
    )
    assert informe["estado"] == "usable", informe


def test_un_transitorio_del_buscador_es_ocupado_y_no_muerto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La leccion de la PR #374, aplicada aqui desde el dia uno."""
    informe = _atestado_de_buscador_con(
        monkeypatch, codigo=503, datos=None, error="HTTP 503: high demand"
    )
    assert informe["estado"] == "ocupado", informe
    assert "vuelve a probar" in str(informe["detalle"])


def test_un_rechazo_del_buscador_ensena_la_respuesta_del_servidor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El detalle ES lo que se busca: distingue clave mala de forma rechazada."""
    informe = _atestado_de_buscador_con(
        monkeypatch,
        codigo=401,
        datos=None,
        error='HTTP 401: {"detail": "Missing Authorization header"}',
    )
    assert informe["estado"] == "no_responde", informe
    assert "Missing Authorization header" in str(informe["detalle"]), (
        "el cuerpo de la respuesta no llega al informe, y ese texto es "
        "exactamente la respuesta que el atestado existe para traer"
    )


def test_un_200_sin_resultados_no_es_usable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un buscador que contesta bien y no trae nada para una pregunta trivial
    no puede dar verde: seria el buscador muerto de siempre con otro codigo."""
    informe = _atestado_de_buscador_con(monkeypatch, codigo=200, datos={"results": []})
    assert informe["estado"] == "no_responde", informe


def test_sin_clave_el_buscador_no_se_comprueba_ni_falla(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Criterio de parada (b): la clave es opcional en todo el diseno (PR #380)."""
    modulo = _preflight()
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    def _nunca(*_a: object, **_k: object) -> tuple[int, object, str]:
        raise AssertionError("sin clave no se hace ninguna peticion")

    monkeypatch.setattr(modulo, "_pedir", _nunca)
    informe = modulo.atestar_buscador()
    assert informe["estado"] == "sin_clave"


def test_el_veredicto_del_preflight_escucha_al_buscador(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pregunta 4: la pieza sin cable es la enfermedad de esta casa.

    Se ejecuta `main` REAL con los proveedores en verde fingido y el buscador
    caido: si el codigo de salida no se pone a 1, el banco gastaria sus 25
    minutos con el buscador muerto y el atestado seria un adorno.
    """
    modulo = _preflight()
    informe_verde = {
        "proveedor": "nvidia",
        "atestado": True,
        "configurados": {"m": True},
        "prueba_de_vida": {"m": {"usable": True}},
        "modelos": ["m"],
        "cuantos_modelos": 1,
    }
    monkeypatch.setattr(modulo, "revisar", lambda _p: dict(informe_verde))
    monkeypatch.setattr(
        modulo,
        "atestar_buscador",
        lambda: {"buscador": "tavily", "estado": "no_responde", "detalle": "HTTP 401"},
    )
    codigo = modulo.main(["nvidia"])
    assert codigo == 1, (
        "el preflight salio en verde con el buscador NO RESPONDE: el banco "
        "gastaria la cuota entera midiendo sin fuentes."
    )
    assert "NO_RESPONDE" in capsys.readouterr().out
    # Y con el buscador sin clave, el mismo verde fingido tiene que PASAR.
    monkeypatch.setattr(
        modulo,
        "atestar_buscador",
        lambda: {"buscador": "tavily", "estado": "sin_clave", "detalle": "sin clave"},
    )
    assert modulo.main(["nvidia"]) == 0, (
        "sin clave el preflight se puso rojo: la clave del buscador es opcional "
        "y esto la volveria obligatoria por la puerta de atras"
    )
