"""El modelo local: el filtro que elige y la ingesta que escribe preguntas.

Corren en cualquier maquina. El transporte HTTP se inyecta y devuelve lo que la
prueba decida, de modo que se comprueba el **cauce entero** —cuerpo de la
peticion, esquema pedido, lectura, fallo, reintento, criba— sin servidor, sin
descargar pesos y sin gastar nada.

Lo que mas importa aqui es lo que **no** puede pasar:

* que el filtro descarte algo porque el modelo se cayo o contesto raro;
* que el modelo cuele una identidad que no estaba entre los candidatos;
* que se pida la respuesta sin esquema, o con el modo razonador encendido;
* que el limite de tiempo se salte justo en el camino que se prueba;
* que una pregunta alucinada entre en el indice sin pasar la criba;
* que la criba tire una parafrasis legitima por no compartir palabras.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from experiments.adr002.modelo_local import ingesta, puerto
from experiments.adr002.modelo_local.filtro import (
    ESQUEMA,
    ESQUEMA_COMPUERTA,
    INSTRUCCION,
    INSTRUCCION_COMPUERTA,
    Filtrado,
    compuerta,
    filtrar,
)


class _Transporte:
    """Transporte de mentira que anota **exactamente** que se pidio."""

    def __init__(self, *respuestas: object) -> None:
        self._respuestas = list(respuestas)
        self.peticiones: list[tuple[str, dict[str, Any], float]] = []

    def __call__(self, ruta: str, cuerpo: Any, espera: float) -> dict[str, Any]:
        # `cuerpo` es `None` en `/api/tags`, que va por GET y no admite cuerpo.
        self.peticiones.append((ruta, dict(cuerpo) if cuerpo is not None else {}, espera))
        if not self._respuestas:
            return {"message": {"content": "{}"}}
        siguiente = self._respuestas.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        if ruta in {"/api/show", "/api/tags"}:
            return dict(siguiente)  # type: ignore[arg-type]
        return {"message": {"content": json.dumps(siguiente)}}


def _proveedor(*respuestas: object) -> puerto.ProveedorOllama:
    return puerto.ProveedorOllama(transporte=_Transporte(*respuestas))


def _con(transporte: _Transporte) -> puerto.ProveedorOllama:
    return puerto.ProveedorOllama(transporte=transporte)


CANDIDATOS = (
    ("MEMORIA:14", "No uses opciones de vuelo con escala."),
    ("MEMORIA:16", "Acepta escala solo si ahorra mas de 200 EUR."),
    ("DECISION:3", "El presupuesto maximo del proyecto es 1.500 EUR."),
)


# -- El puerto: lo que se le pide al servidor -------------------------------


def test_se_pide_por_la_api_nativa_con_esquema_y_sin_razonar() -> None:
    """Las tres garantias del adaptador, comprobadas sobre la peticion real.

    El esquema es lo que hace que un JSON invalido sea imposible en vez de
    improbable; `think` apagado es lo que separa segundos de minutos; y la ruta
    nativa es la unica que acepta las dos cosas.
    """
    transporte = _Transporte({"responden": [1]})
    filtrar("¿acepto escalas?", CANDIDATOS, _con(transporte))
    ruta, cuerpo, espera = transporte.peticiones[0]
    assert ruta == "/api/chat"
    assert cuerpo["format"] == dict(ESQUEMA)
    assert cuerpo["think"] is False
    assert cuerpo["stream"] is False
    assert cuerpo["keep_alive"] == puerto.PERMANENCIA_POR_DEFECTO
    assert cuerpo["options"]["num_ctx"] == puerto.CONTEXTO_POR_DEFECTO
    assert cuerpo["messages"][0]["content"] == INSTRUCCION
    assert espera == puerto.ESPERA_FILTRO


def test_el_modelo_por_defecto_cabe_en_una_grafica_de_portatil() -> None:
    """Catorce mil millones de parametros no caben en 6 GB y se parten."""
    assert "4b" in puerto.MODELO_POR_DEFECTO


def test_hay_un_reintento_y_solo_uno() -> None:
    transporte = _Transporte(TimeoutError("lento"), {"responden": [2]})
    salida = filtrar("lo que sea", CANDIDATOS, _con(transporte))
    assert len(transporte.peticiones) == 2
    assert salida.actuo
    assert salida.identidades == ("MEMORIA:16",)


def test_agotados_los_intentos_el_error_es_tipado_y_en_castellano() -> None:
    proveedor = _proveedor(TimeoutError("uno"), TimeoutError("dos"))
    with pytest.raises(puerto.ModeloNoDisponibleError, match="Ollama"):
        proveedor.responder_json("i", "e", ESQUEMA, espera=1.0)


def test_la_espera_llega_al_transporte_tambien_en_las_pruebas() -> None:
    """En la version anterior el limite de tiempo se saltaba al inyectar, de
    modo que lo unico comprobado era el camino que en produccion no se usa."""
    transporte = _Transporte({"responden": []})
    _con(transporte).responder_json("i", "e", ESQUEMA, espera=3.5)
    assert transporte.peticiones[0][2] == 3.5


def test_una_respuesta_vacia_o_ilegible_es_error_tipado() -> None:
    proveedor = puerto.ProveedorOllama(
        transporte=lambda ruta, cuerpo, espera: {"message": {"content": "   "}}
    )
    with pytest.raises(puerto.RespuestaInvalidaError):
        proveedor.responder_json("i", "e", ESQUEMA, espera=1.0)


_CATALOGO = {
    "models": [
        {"name": "otro:8b", "model": "otro:8b", "digest": "ffffffffffff0000"},
        {"name": "qwen3:4b-instruct", "model": "qwen3:4b-instruct", "digest": "0edcdef34593aa"},
    ]
}


def test_la_huella_sale_del_catalogo_y_se_recuerda() -> None:
    """`TOL-207` exige regenerar derivados; para eso hay que saber con que.

    Correccion medida: se pedia a ``/api/show``, que **no trae el digest**, y la
    corrida publicada salio con huella «desconocida». Vive en ``/api/tags``.
    """
    transporte = _Transporte(_CATALOGO, {"models": []})
    proveedor = puerto.ProveedorOllama(modelo="qwen3:4b-instruct", transporte=transporte)
    primera = proveedor.info_modelo()
    segunda = proveedor.info_modelo()

    assert primera.huella == "0edcdef34593aa", "el digest del modelo pedido, no el del vecino"
    assert segunda == primera, "preguntarla por cada dato seria una peticion por elemento"
    assert len(transporte.peticiones) == 1
    assert transporte.peticiones[0][0] == "/api/tags"


def test_el_catalogo_se_pide_por_get_y_sin_cuerpo() -> None:
    """`/api/tags` no admite cuerpo: mandarselo devuelve 405 y no habria huella."""
    registradas: list[tuple[str, Any]] = []

    def transporte(ruta: str, cuerpo: Any, espera: float) -> dict[str, Any]:
        registradas.append((ruta, cuerpo))
        return dict(_CATALOGO)

    puerto.ProveedorOllama(modelo="qwen3:4b-instruct", transporte=transporte).info_modelo()
    assert registradas == [("/api/tags", None)]


def test_un_modelo_sin_etiqueta_se_encuentra_como_latest() -> None:
    """Ollama resuelve «qwen3» a «qwen3:latest»; el catalogo lo lista asi."""
    catalogo = {
        "models": [{"name": "qwen3:latest", "model": "qwen3:latest", "digest": "abc123def456"}]
    }
    proveedor = puerto.ProveedorOllama(modelo="qwen3", transporte=_Transporte(catalogo))
    assert proveedor.info_modelo().huella == "abc123def456"


def test_sin_digest_se_describe_pero_no_se_inventa_una_huella() -> None:
    """Confesar que no se sabe es mejor que un identificador falso.

    Lo que no puede pasar es que la descripcion **parezca** un digest: quien lea
    el artefacto tiene que ver de un golpe que ahi no hay identidad de pesos.
    """
    transporte = _Transporte(
        {"models": [{"name": "otro:8b", "digest": "no-es-el-mio"}]},
        {"details": {"family": "qwen3", "parameter_size": "4.0B", "quantization_level": "Q4_K_M"}},
    )
    proveedor = puerto.ProveedorOllama(modelo="qwen3:4b-instruct", transporte=transporte)
    huella = proveedor.info_modelo().huella

    assert huella == "sin-digest(qwen3/4.0B/Q4_K_M)"
    assert huella == proveedor.info_modelo().huella_corta, "no se acorta lo que no es un digest"
    assert [p[0] for p in transporte.peticiones] == ["/api/tags", "/api/show"]


def test_si_el_servidor_no_esta_la_huella_no_se_inventa_sino_que_avisa() -> None:
    """«Sin digest» y «Ollama apagado» no pueden verse igual.

    Si el fallo se tragase aqui, el arnes imprimiria una huella tranquilizadora
    y el responsable descubriria a los diez minutos —por un contador de fallo
    abierto— que no estaba midiendo nada. Quien llama ya sabe degradar.
    """
    proveedor = puerto.ProveedorOllama(transporte=_Transporte(*[TimeoutError("lento")] * 4))
    with pytest.raises(puerto.ModeloNoDisponibleError):
        proveedor.info_modelo()


def test_y_aun_asi_guardar_un_dato_no_revienta() -> None:
    """La otra mitad del trato: la ingesta absorbe ese error y sigue."""
    salida = ingesta.preguntas_que_responde(
        "un dato",
        _proveedor(*[TimeoutError("lento")] * 8),
        vocabulario_de_categoria=("esencial",),
    )
    assert salida.preguntas == ()
    assert salida.texto_para_indexar == "esencial"
    assert "no se genero nada" in salida.razon


def test_la_huella_se_acorta_a_doce_solo_si_es_un_digest() -> None:
    """Doce es lo que imprime ``ollama ps``: asi se comparan de un vistazo.

    Y «desconocida» recortada daria «desconocid», que parece un identificador.
    """
    largo = puerto.InfoModelo("ollama", "m", "sha256:" + "0123456789abcdef" * 4)
    assert largo.huella_corta == "0123456789ab"
    assert largo.completo == "ollama:m@0123456789ab"
    assert puerto.InfoModelo("ollama", "m", "desconocida").huella_corta == "desconocida"


def test_los_numeros_fuera_de_rango_no_pasan_la_lectura() -> None:
    assert puerto.enteros_validos({"responden": [1, 5]}, "responden", tope=3) == (1,)
    assert puerto.enteros_validos({"responden": []}, "responden", tope=3) == ()
    assert puerto.enteros_validos({}, "responden", tope=3) is None
    assert puerto.enteros_validos({"responden": "uno"}, "responden", tope=3) is None
    assert puerto.enteros_validos({"responden": [True]}, "responden", tope=3) is None


# -- El filtro --------------------------------------------------------------


def test_el_filtro_elige_y_conserva_el_orden_de_la_busqueda() -> None:
    """Decide QUE sale, no en que orden: mezclarlo haria inatribuible la medida."""
    salida = filtrar("¿cual es el limite de gasto?", CANDIDATOS, _proveedor({"responden": [3, 1]}))
    assert salida.actuo
    assert salida.identidades == ("MEMORIA:14", "DECISION:3")


def test_si_el_modelo_se_cae_no_se_descarta_nada() -> None:
    """Falla ABIERTO. `RF-24` prohibe perder un critico en silencio.

    Este modulo solo puede quitar, asi que un fallo que quita de mas produce
    justo la perdida que la norma prohibe. Un fallo que no quita nada deja el
    sistema ruidoso pero completo.
    """
    salida = filtrar("lo que sea", CANDIDATOS, _proveedor(TimeoutError("x"), TimeoutError("y")))
    assert salida.identidades == tuple(i for i, _ in CANDIDATOS)
    assert not salida.actuo
    assert "no decidio" in salida.razon


def test_una_respuesta_sin_lista_de_numeros_tampoco_descarta_nada() -> None:
    salida = filtrar("lo que sea", CANDIDATOS, _proveedor({"otra_cosa": [1]}))
    assert salida.identidades == tuple(i for i, _ in CANDIDATOS)
    assert not salida.actuo
    assert "lista de numeros" in salida.razon


def test_ninguno_responde_es_una_respuesta_valida_y_se_respeta() -> None:
    """Es como Sirius llega a decir «no tengo eso», y no puede confundirse con
    un fallo de formato."""
    salida = filtrar("¿de que color es el cielo?", CANDIDATOS, _proveedor({"responden": []}))
    assert salida.identidades == ()
    assert salida.actuo


def test_el_modelo_no_puede_colar_algo_que_no_estaba() -> None:
    salida = filtrar("lo que sea", CANDIDATOS, _proveedor({"responden": [1, 99, -3, 2]}))
    assert set(salida.identidades) <= {i for i, _ in CANDIDATOS}
    assert salida.identidades == ("MEMORIA:14", "MEMORIA:16")


def test_con_mas_candidatos_que_el_tope_el_resto_pasa_intacto() -> None:
    """Recortar la cola seria descartar sin que nadie lo mirase."""
    muchos = tuple((f"MEMORIA:{n}", f"dato {n}") for n in range(1, 8))
    salida = filtrar("lo que sea", muchos, _proveedor({"responden": [1]}), tope=3)
    assert salida.identidades == ("MEMORIA:1", "MEMORIA:4", "MEMORIA:5", "MEMORIA:6", "MEMORIA:7")


def test_sin_candidatos_no_se_llama_al_servidor() -> None:
    transporte = _Transporte({"responden": [1]})
    salida = filtrar("lo que sea", (), _con(transporte))
    assert salida == Filtrado((), False, "no habia candidatos")
    assert transporte.peticiones == []


# -- La ingesta -------------------------------------------------------------


def test_la_criba_conserva_una_parafrasis_que_no_comparte_palabras() -> None:
    """El caso que justifica todo esto.

    «¿cual es el limite de gasto?» no comparte ni una palabra significativa con
    «El presupuesto maximo del proyecto es 1.500 EUR», y es justo la pregunta
    que hay que conservar. Un filtro por vocabulario la tiraria.
    """
    salida = ingesta.preguntas_que_responde(
        "El presupuesto maximo del proyecto es 1.500 EUR.",
        _proveedor(
            {"preguntas": ["¿cual es el limite de gasto?", "¿cuanto cuesta el vuelo?"]},
            {"responden": [1]},
            {"digest": "sha256:abc"},
        ),
    )
    assert salida.preguntas == ("¿cual es el limite de gasto?",)
    assert salida.aportes_descartados == ("¿cuanto cuesta el vuelo?",)


def test_una_pregunta_alucinada_no_supera_su_propio_examen() -> None:
    salida = ingesta.preguntas_que_responde(
        "El presupuesto maximo es 1.500 EUR.",
        _proveedor(
            {"preguntas": ["¿cuanto cuesta el vuelo a Madrid?"]},
            {"responden": []},
            {"digest": "sha256:abc"},
        ),
    )
    assert salida.preguntas == ()
    assert salida.aportes_descartados == ("¿cuanto cuesta el vuelo a Madrid?",)


def test_lo_generado_guarda_con_que_modelo_se_genero() -> None:
    """Sin procedencia, al cambiar de modelo no se sabe que hay que regenerar."""
    catalogo = {"models": [{"name": puerto.MODELO_POR_DEFECTO, "digest": "aabbccddeeff00"}]}
    salida = ingesta.preguntas_que_responde(
        "un dato",
        _proveedor({"preguntas": ["¿que?"]}, {"responden": [1]}, catalogo),
    )
    assert salida.procedencia == {
        "proveedor": "ollama",
        "modelo": puerto.MODELO_POR_DEFECTO,
        "huella": "aabbccddeeff00",
    }


def test_sin_modelo_no_se_indexa_ninguna_pregunta_pero_no_revienta() -> None:
    """Al reves que el filtro: aqui fallar cerrado SI es lo correcto.

    No ampliar un dato lo deja como estaba; indexar sin cribar mete vocabulario
    alucinado y contamina busquedas ajenas.
    """
    salida = ingesta.preguntas_que_responde(
        "un dato", _proveedor(TimeoutError("x"), TimeoutError("y"))
    )
    assert salida.preguntas == ()
    assert "no se genero nada" in salida.razon
    assert salida.info_modelo is None


def test_el_vocabulario_de_categoria_sobrevive_aunque_el_modelo_falle() -> None:
    """Viene del canon, no del modelo, y por eso no depende de que responda.

    Es lo ya medido: solo con ese vocabulario, los casos en que lo correcto
    entra entero pasan de 24 a 26 y los elementos hallados del 79% al 86%.
    """
    salida = ingesta.preguntas_que_responde(
        "No usar PostgreSQL en este proyecto.",
        _proveedor(TimeoutError("x"), TimeoutError("y")),
        vocabulario_de_categoria=("esencial", "restriccion"),
    )
    assert salida.texto_para_indexar == "esencial restriccion"


def test_el_texto_para_indexar_junta_categoria_y_preguntas() -> None:
    salida = ingesta.preguntas_que_responde(
        "El presupuesto maximo es 1.500 EUR.",
        _proveedor(
            {"preguntas": ["¿cual es el limite de gasto?"]},
            {"responden": [1]},
            {"digest": "sha256:abc"},
        ),
        vocabulario_de_categoria=("esencial",),
    )
    assert salida.texto_para_indexar == "esencial ¿cual es el limite de gasto?"


# -- Que ningun proveedor pueda tumbar la busqueda ni el guardado ------------


class _ProveedorAjeno:
    """Un proveedor de otra familia que levanta SUS errores, no los de aqui.

    Es el caso real de una API: sin conexion, cuota agotada, clave invalida o
    demasiadas peticiones llegan como excepciones de su propia libreria. Si el
    filtro solo supiera capturar los dos errores de este paquete, cualquiera de
    esas reventaria la busqueda entera.
    """

    def __init__(self, fallo: Exception) -> None:
        self._fallo = fallo

    def info_modelo(self) -> puerto.InfoModelo:
        raise self._fallo

    def responder_json(self, instruccion, entrada, esquema, *, espera):  # type: ignore[no-untyped-def]
        raise self._fallo


@pytest.mark.parametrize(
    "fallo",
    [
        ConnectionError("no hay red"),
        RuntimeError("cuota agotada"),
        PermissionError("clave invalida"),
        ValueError("demasiadas peticiones"),
    ],
)
def test_ningun_error_de_proveedor_tumba_la_busqueda(fallo: Exception) -> None:
    """Falla ABIERTO ante CUALQUIER error, no solo ante los dos de casa."""
    salida = filtrar("lo que sea", CANDIDATOS, _ProveedorAjeno(fallo))
    assert salida.identidades == tuple(i for i, _ in CANDIDATOS)
    assert not salida.actuo
    assert type(fallo).__name__ in salida.razon, "la razon debe decir QUE fallo"


@pytest.mark.parametrize(
    "fallo",
    [ConnectionError("no hay red"), RuntimeError("cuota agotada"), PermissionError("clave")],
)
def test_ningun_error_de_proveedor_tumba_el_guardado(fallo: Exception) -> None:
    """Guardar un dato no puede romperse por no poder adornarlo."""
    salida = ingesta.preguntas_que_responde(
        "un dato", _ProveedorAjeno(fallo), vocabulario_de_categoria=("esencial",)
    )
    assert salida.preguntas == ()
    assert salida.texto_para_indexar == "esencial"
    assert type(fallo).__name__ in salida.razon


def test_una_interrupcion_del_usuario_sigue_interrumpiendo() -> None:
    """`BaseException` no se captura: parar tiene que parar de verdad."""
    with pytest.raises(KeyboardInterrupt):
        filtrar("lo que sea", CANDIDATOS, _ProveedorAjeno(KeyboardInterrupt()))


# -- La polaridad: distinguir no es excluir ---------------------------------


def _banco() -> tuple[dict[str, str], dict[str, str], list[Any]]:
    """El banco de verdad. Estas pruebas no valen sobre datos inventados."""
    from experiments.adr002.projection import contracts as pc
    from experiments.adr002.round import cases as cs

    artefactos = cs.cargar_artefactos()
    polaridad, texto = {}, {}
    for item in artefactos[cs.CORPUS]["items"]:
        identidad = pc.referencia_canonica(str(item["id"]))
        if identidad:
            polaridad[identidad] = str(item["polaridad"])
            texto[identidad] = str(item["text"])
    return polaridad, texto, list(cs.casos_ejecutables(artefactos))


def test_el_banco_espera_prohibiciones_como_respuesta_a_preguntas_de_permiso() -> None:
    """El hecho medido que obliga a la regla del filtro. Leido del banco.

    Si algun dia el banco deja de tener estos casos, esta prueba cae y la regla
    se vuelve a discutir con datos. Mientras los tenga, excluir por polaridad es
    tirar la respuesta correcta.
    """
    polaridad, _texto, casos = _banco()
    con_negativa = [
        caso
        for caso in casos
        if caso.adjudicable
        and caso.resultado_esperado
        and any(polaridad.get(e) == "NEGATIVA" for e in caso.resultado_esperado)
    ]
    assert len(con_negativa) >= 5, "el banco espera prohibiciones en varios casos"

    por_identificador = {c.identificador: c for c in con_negativa}
    escalas = por_identificador["N1-20"]
    assert "puedo usar" in escalas.peticion.consulta.lower(), "es una pregunta de permiso"
    assert "MEMORIA:14" in escalas.resultado_esperado, "y espera la prohibicion"


def test_los_elementos_negativos_esperados_son_criticos() -> None:
    """Por eso la regla mala costaba una omision critica: `B04-RF-24`."""
    from experiments.adr002.projection import build
    from experiments.adr002.round.execute_round import _criticos_del_canon

    familia = build.cargar_familia()
    criticos = set(_criticos_del_canon(familia["applied_criticality_v0_1.json"]["valores"]))
    assert {"MEMORIA:2", "MEMORIA:14", "DECISION:10"} <= criticos


def test_la_instruccion_del_filtro_no_manda_excluir_por_polaridad() -> None:
    """Guarda contra reponer la regla que perdia lo critico.

    El §6.1, citado en `round/metrics.py`: «Fundir ambas es fallo; recuperarlas
    marcadas y distinguidas es correcto». Marcado, no exclusion.
    """
    assert "no responde a una pregunta sobre lo que si se hace" not in INSTRUCCION
    assert "SI responde a una pregunta sobre si algo se puede hacer" in INSTRUCCION
    assert "devuelve LAS DOS" in INSTRUCCION
    assert "Respeta el tiempo" in INSTRUCCION, "la regla temporal si es correcta y se queda"


def test_la_criba_de_ingesta_tampoco_excluye_por_polaridad() -> None:
    """Mismo error, mismo sitio: dejaba los datos negativos sin vocabulario."""
    assert "no responde a una pregunta sobre lo que si se permite" not in (
        ingesta.INSTRUCCION_DE_CRIBA
    )
    assert "SI responde a la pregunta de si eso se puede hacer" in ingesta.INSTRUCCION_DE_CRIBA


# -- El arnes: que se publica y que no se pisa ------------------------------


class _Caso:
    """Lo minimo que `_detalle` mira de un caso."""

    def __init__(self, esperado: tuple[str, ...]) -> None:
        self.identificador = "N1-20"
        self.resultado_esperado = esperado
        self.peticion = type("P", (), {"consulta": "¿Puedo usar vuelos con escala?"})()


def test_el_detalle_separa_lo_que_el_filtro_tiro_en_bueno_y_malo() -> None:
    """Sin esto solo hay totales, y con totales no se diagnostica nada.

    El defecto de polaridad costo una lectura del banco a mano porque el
    artefacto no decia **cuales** elementos correctos se perdian.
    """
    from experiments.adr002.modelo_local import medir

    caso = _Caso(("MEMORIA:14", "DECISION:3"))
    detalle = medir._detalle(
        caso,
        antes=("MEMORIA:14", "DECISION:3", "MEMORIA:917"),
        despues=("DECISION:3",),
        filtrado=Filtrado(("DECISION:3",), True),
        criticos=frozenset({"MEMORIA:14", "MEMORIA:2"}),
    )

    assert detalle["quitados"] == ["MEMORIA:14", "MEMORIA:917"]
    assert detalle["quitados_correctos"] == ["MEMORIA:14"], "lo que no debio irse"
    assert detalle["quitados_criticos"] == ["MEMORIA:14"], "y ademas era critico"
    assert detalle["filtro_actuo"] is True


def test_un_critico_que_el_caso_no_esperaba_no_cuenta_como_perdida() -> None:
    """Quitar un critico ajeno al caso es limpiar ruido, no perder nada."""
    from experiments.adr002.modelo_local import medir

    detalle = medir._detalle(
        _Caso(("DECISION:3",)),
        antes=("DECISION:3", "MEMORIA:2"),
        despues=("DECISION:3",),
        filtrado=Filtrado(("DECISION:3",), True),
        criticos=frozenset({"MEMORIA:2"}),
    )
    assert detalle["quitados"] == ["MEMORIA:2"]
    assert detalle["quitados_criticos"] == []


def test_sin_filtro_el_detalle_no_habla_de_lo_quitado() -> None:
    """Una corrida sin filtro no quita nada: inventarse la columna confundiria."""
    from experiments.adr002.modelo_local import medir

    detalle = medir._detalle(
        _Caso(("DECISION:3",)),
        antes=("DECISION:3",),
        despues=("DECISION:3",),
        filtrado=None,
        criticos=frozenset(),
    )
    assert "quitados" not in detalle
    assert detalle["obtenido"] == ["DECISION:3"]


def test_no_se_pisa_un_artefacto_ya_medido(tmp_path: Any, monkeypatch: Any) -> None:
    """Los artefactos medidos se conservan. Y se comprueba **antes** de medir:
    negarse al final tiraria minutos de grafica del responsable."""
    import sys

    from experiments.adr002.modelo_local import medir

    ya = tmp_path / "resultado.json"
    ya.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["medir", "--salida", str(ya)])

    assert medir.main() == 2
    assert ya.read_text(encoding="utf-8") == "{}", "intacto"


# -- La compuerta: todo o nada, medida contra el que elige -------------------


def test_la_compuerta_pregunta_si_o_no_y_no_elige() -> None:
    """Un booleano, no una lista de numeros. Es toda la diferencia."""
    transporte = _Transporte({"hay_respuesta": True})
    salida = compuerta("¿acepto escalas?", CANDIDATOS, _con(transporte))

    _ruta, cuerpo, _espera = transporte.peticiones[0]
    assert cuerpo["format"] == dict(ESQUEMA_COMPUERTA)
    assert cuerpo["messages"][0]["content"] == INSTRUCCION_COMPUERTA
    assert salida.identidades == tuple(i for i, _ in CANDIDATOS), "entrega la lista entera"
    assert salida.actuo


def test_la_compuerta_no_puede_truncar_una_respuesta_larga() -> None:
    """La propiedad por la que existe.

    El que elige se quedo con una de las cinco restricciones de `N1-44` y con
    tres de los diez elementos de `N1-34`. Esta no puede: no decide elemento a
    elemento, de modo que o van todas o no va ninguna.
    """
    cinco = tuple((f"MEMORIA:{100 + n}", f"Restriccion esencial numero {n}.") for n in range(1, 6))
    salida = compuerta(
        "Restricciones esenciales, maximo duro 5.", cinco, _proveedor({"hay_respuesta": True})
    )
    assert salida.identidades == tuple(i for i, _ in cinco), "las cinco, no la que mas se parece"


def test_la_compuerta_respeta_el_no_del_modelo() -> None:
    """Decir «no tengo eso» es de donde sale su ganancia: `RF-25` y `RF-26`."""
    salida = compuerta(
        "¿cual es la capital de Francia?", CANDIDATOS, _proveedor({"hay_respuesta": False})
    )
    assert salida.identidades == ()
    assert salida.actuo


def test_un_no_sobre_la_cabeza_no_descarta_la_cola_sin_mirar() -> None:
    """Misma disciplina que el que elige: lo no juzgado no se tira."""
    muchos = tuple((f"MEMORIA:{n}", f"frase {n}") for n in range(1, 6))
    salida = compuerta("lo que sea", muchos, _proveedor({"hay_respuesta": False}), tope=3)
    assert salida.identidades == ("MEMORIA:4", "MEMORIA:5"), "la cola no la vio nadie"


def test_la_compuerta_tambien_falla_abierto() -> None:
    """Un modulo que solo puede quitar degrada a «no quito nada». `RF-24`."""
    for fallo in (ConnectionError("sin red"), RuntimeError("cuota"), TimeoutError("lento")):
        salida = compuerta("lo que sea", CANDIDATOS, _ProveedorAjeno(fallo))
        assert salida.identidades == tuple(i for i, _ in CANDIDATOS)
        assert not salida.actuo
        assert type(fallo).__name__ in salida.razon


def test_una_respuesta_que_no_es_si_ni_no_deja_todo_pasar() -> None:
    """Sin un booleano de verdad no hay veredicto, y sin veredicto no se quita."""
    salida = compuerta("lo que sea", CANDIDATOS, _proveedor({"hay_respuesta": "puede"}))
    assert salida.identidades == tuple(i for i, _ in CANDIDATOS)
    assert not salida.actuo


def test_el_arnes_sabe_llamar_a_las_dos() -> None:
    """Si `_correr` no distingue el modo, la comparacion no mide dos cosas."""
    from experiments.adr002.modelo_local import filtro as fl
    from experiments.adr002.modelo_local import medir

    assert medir.fl.compuerta is fl.compuerta
    assert medir.fl.filtrar is fl.filtrar


def test_la_estimacion_de_la_compuerta_se_recomputa_del_artefacto_congelado() -> None:
    """La cifra que justifica la compuerta, rehecha desde la corrida v0.2.

    **No es una medicion**: replica los veredictos que el modelo dio con la
    instruccion del que elige. Se guarda como prueba para que la cifra publicada
    no pueda desviarse de la evidencia sin que algo se rompa, y para que quien la
    lea vea de donde sale.
    """
    import json
    from pathlib import Path

    from experiments.adr002.projection import build
    from experiments.adr002.round import cases as cs
    from experiments.adr002.round.execute_round import _criticos_del_canon

    artefacto = Path("resultado_modelo_local_v0.2.json")
    if not artefacto.exists():  # pragma: no cover - solo si alguien borra la evidencia
        pytest.skip("no esta la corrida v0.2")

    casos = {c.identificador: c for c in cs.casos_ejecutables(cs.cargar_artefactos())}
    criticos = set(
        _criticos_del_canon(build.cargar_familia()["applied_criticality_v0_1.json"]["valores"])
    )
    det = json.loads(artefacto.read_text(encoding="utf-8"))["detalle_por_caso"]

    exacto = omisiones = 0
    for c in det["4. solo filtro, sin ampliacion"]:
        caso = casos[c["caso"]]
        if not caso.adjudicable:
            continue
        entraron = c.get("entraron_al_filtro", c["obtenido"])
        dijo_nada = c.get("filtro_actuo") and not c["obtenido"] and entraron
        obtenido = set(() if dijo_nada else entraron)
        esperado = set(caso.resultado_esperado)
        exacto += sorted(obtenido) == sorted(esperado)
        omisiones += len(
            [
                i
                for i in criticos
                if i in esperado and i not in obtenido and i not in set(caso.pendientes_por_limite)
            ]
        )

    assert (exacto, omisiones) == (27, 11), "27/47 sin anadir ni una omision critica"


# -- La regla: si elige algunas, no puede tirar una critica -----------------


CRITICAS = frozenset({"MEMORIA:14", "DECISION:3"})


def test_si_el_modelo_elige_algunas_no_puede_tirar_una_critica() -> None:
    """`B04-RF-24`, garantizado por el codigo y no por la instruccion.

    Medido sobre la corrida v0.3: el modelo tiraba cuatro criticas que hacian
    falta. Pedirselo por escrito ya se intento dos veces y las dos fallo.
    """
    salida = filtrar(
        "¿acepto escalas?", CANDIDATOS, _proveedor({"responden": [2]}), criticos=CRITICAS
    )
    assert salida.identidades == ("MEMORIA:14", "MEMORIA:16", "DECISION:3")
    assert salida.rescatados == ("MEMORIA:14", "DECISION:3")
    assert salida.actuo


def test_el_orden_sigue_siendo_el_de_la_busqueda() -> None:
    """Las rescatadas vuelven a su sitio, no al final.

    Si volviesen pegadas al final, el orden dejaria de ser el de la busqueda y
    pasaria a ser una mezcla de dos criterios que nadie podria atribuir.
    """
    salida = filtrar("lo que sea", CANDIDATOS, _proveedor({"responden": [3]}), criticos=CRITICAS)
    assert salida.identidades == ("MEMORIA:14", "DECISION:3")


def test_un_no_rotundo_se_respeta_entero_y_no_rescata_nada() -> None:
    """La otra mitad de la regla, y la que la hace salir a cuenta.

    Decir «no tengo eso» no es truncar una respuesta: `RF-25` y `RF-26` lo
    permiten. Medido: proteger tambien aqui baja los aciertos de 30 a 27,
    porque rompe justo los casos de ausencia que el filtro acierta.
    """
    salida = filtrar(
        "¿cual es la capital de Francia?",
        CANDIDATOS,
        _proveedor({"responden": []}),
        criticos=CRITICAS,
    )
    assert salida.identidades == ()
    assert salida.rescatados == ()
    assert salida.actuo


def test_sin_lista_de_criticas_se_comporta_como_antes() -> None:
    """La regla es opcional: sin canon que consultar, no inventa proteccion."""
    salida = filtrar("lo que sea", CANDIDATOS, _proveedor({"responden": [2]}))
    assert salida.identidades == ("MEMORIA:16",)
    assert salida.rescatados == ()


def test_se_puede_reconstruir_lo_que_decidio_el_modelo_a_solas() -> None:
    """Sin esto, una corrida no permite separar al modelo del codigo."""
    salida = filtrar("lo que sea", CANDIDATOS, _proveedor({"responden": [2]}), criticos=CRITICAS)
    assert salida.sin_proteccion == ("MEMORIA:16",), "lo que habria salido sin la regla"


def test_la_cola_no_juzgada_conserva_las_rescatadas() -> None:
    """Con mas candidatos que el tope, la regla no se pierde por el camino."""
    muchos = tuple((f"MEMORIA:{n}", f"frase {n}") for n in range(1, 6))
    salida = filtrar(
        "lo que sea",
        muchos,
        _proveedor({"responden": [1]}),
        criticos=frozenset({"MEMORIA:2"}),
        tope=3,
    )
    assert salida.identidades == ("MEMORIA:1", "MEMORIA:2", "MEMORIA:4", "MEMORIA:5")
    assert salida.rescatados == ("MEMORIA:2",)


def test_la_compuerta_no_lleva_la_regla_porque_no_la_necesita() -> None:
    """No decide elemento a elemento, de modo que no hay nada que proteger."""
    from experiments.adr002.modelo_local import medir

    assert "criticos" not in medir.fl.compuerta.__code__.co_varnames


def test_el_nombre_de_salida_avanza_solo_hasta_el_primero_libre(tmp_path: Any) -> None:
    """La regla «no se pisa» se conserva; lo que se quita es pensar el nombre.

    Con un nombre fijo, toda corrida a partir de la segunda moria en un error
    que habia que leer y resolver a mano justo al ir a medir.
    """
    from experiments.adr002.modelo_local import medir

    assert medir.siguiente_salida(tmp_path).name == "resultado_modelo_local_v0.2.json"
    (tmp_path / "resultado_modelo_local_v0.2.json").write_text("{}", encoding="utf-8")
    (tmp_path / "resultado_modelo_local_v0.3.json").write_text("{}", encoding="utf-8")
    assert medir.siguiente_salida(tmp_path).name == "resultado_modelo_local_v0.4.json"


def test_al_negarse_a_pisar_dice_exactamente_que_escribir(
    tmp_path: Any, monkeypatch: Any, capsys: Any
) -> None:
    """Un error que no dice como salir de el hace perder una corrida entera."""
    import sys

    from experiments.adr002.modelo_local import medir

    ya = tmp_path / "resultado_modelo_local_v0.2.json"
    ya.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["medir", "--salida", str(ya)])

    assert medir.main() == 2
    assert "--salida" in capsys.readouterr().out
    assert ya.read_text(encoding="utf-8") == "{}", "intacto"
