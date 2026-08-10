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
from experiments.adr002.modelo_local.filtro import ESQUEMA, INSTRUCCION, Filtrado, filtrar


class _Transporte:
    """Transporte de mentira que anota **exactamente** que se pidio."""

    def __init__(self, *respuestas: object) -> None:
        self._respuestas = list(respuestas)
        self.peticiones: list[tuple[str, dict[str, Any], float]] = []

    def __call__(self, ruta: str, cuerpo: Any, espera: float) -> dict[str, Any]:
        self.peticiones.append((ruta, dict(cuerpo), espera))
        if not self._respuestas:
            return {"message": {"content": "{}"}}
        siguiente = self._respuestas.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        if ruta == "/api/show":
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


def test_la_huella_del_modelo_se_pregunta_al_servidor_y_se_recuerda() -> None:
    """`TOL-207` exige regenerar derivados; para eso hay que saber con que."""
    transporte = _Transporte({"digest": "sha256:abc123"}, {"digest": "sha256:otro"})
    proveedor = _con(transporte)
    primera = proveedor.info_modelo()
    segunda = proveedor.info_modelo()
    assert primera.huella == "sha256:abc123"
    assert segunda == primera, "preguntarla por cada dato seria una peticion por elemento"
    assert len(transporte.peticiones) == 1
    assert transporte.peticiones[0][0] == "/api/show"
    assert primera.completo.startswith("ollama:")


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
    salida = ingesta.preguntas_que_responde(
        "un dato",
        _proveedor({"preguntas": ["¿que?"]}, {"responden": [1]}, {"digest": "sha256:ff"}),
    )
    assert salida.procedencia == {
        "proveedor": "ollama",
        "modelo": puerto.MODELO_POR_DEFECTO,
        "huella": "sha256:ff",
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
