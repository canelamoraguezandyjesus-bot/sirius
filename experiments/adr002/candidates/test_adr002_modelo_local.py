"""El modelo local: el filtro que elige y la ingesta que escribe preguntas.

Corren en cualquier maquina. El modelo se inyecta y devuelve lo que la prueba
decida, de modo que se comprueba el **cauce entero** —instruccion, lectura de la
respuesta, fallo, criba— sin servidor, sin descargar pesos y sin gastar nada.

Lo que mas importa aqui es lo que **no** puede pasar:

* que el filtro descarte algo porque el modelo se cayo o contesto raro;
* que el modelo cuele una identidad que no estaba entre los candidatos;
* que una pregunta alucinada entre en el indice sin pasar la criba;
* que la criba tire una parafrasis legitima por no compartir palabras.
"""

from __future__ import annotations

from experiments.adr002.modelo_local import ingesta, puerto
from experiments.adr002.modelo_local.filtro import INSTRUCCION, Filtrado, filtrar


class _ModeloFalso:
    """Devuelve respuestas guionizadas y anota exactamente que se le mando."""

    identificador = "falso:para-pruebas"

    def __init__(self, *respuestas: str) -> None:
        self._respuestas = list(respuestas)
        self.recibido: list[tuple[str, str]] = []

    def preguntar(self, instruccion: str, entrada: str) -> str:
        self.recibido.append((instruccion, entrada))
        return self._respuestas.pop(0) if self._respuestas else "{}"


class _ModeloCaido:
    identificador = "falso:caido"

    def preguntar(self, instruccion: str, entrada: str) -> str:
        raise puerto.ModeloNoDisponibleError("apagado")


CANDIDATOS = (
    ("MEMORIA:14", "No uses opciones de vuelo con escala."),
    ("MEMORIA:16", "Acepta escala solo si ahorra mas de 200 EUR."),
    ("DECISION:3", "El presupuesto maximo del proyecto es 1.500 EUR."),
)


# -- El filtro --------------------------------------------------------------


def test_el_filtro_elige_y_conserva_el_orden_de_la_busqueda() -> None:
    """Decide QUE sale, no en que orden: mezclarlo haria inatribuible la medida."""
    modelo = _ModeloFalso('{"responden": [3, 1]}')
    salida = filtrar("¿cual es el limite de gasto?", CANDIDATOS, modelo)
    assert salida.actuo
    assert salida.identidades == ("MEMORIA:14", "DECISION:3")


def test_si_el_modelo_se_cae_no_se_descarta_nada() -> None:
    """Falla ABIERTO. `RF-24` prohibe perder un critico en silencio.

    Este modulo solo puede quitar, asi que un fallo que quita de mas produce
    justo la perdida que la norma prohibe. Un fallo que no quita nada deja el
    sistema ruidoso pero completo.
    """
    salida = filtrar("lo que sea", CANDIDATOS, _ModeloCaido())
    assert salida.identidades == tuple(i for i, _ in CANDIDATOS)
    assert not salida.actuo
    assert "no respondio" in salida.razon


def test_una_respuesta_ilegible_tampoco_descarta_nada() -> None:
    salida = filtrar("lo que sea", CANDIDATOS, _ModeloFalso("me apetece charlar"))
    assert salida.identidades == tuple(i for i, _ in CANDIDATOS)
    assert not salida.actuo


def test_ninguno_responde_es_una_respuesta_valida_y_se_respeta() -> None:
    """Es como Sirius llega a decir «no tengo eso», y no puede confundirse con
    un fallo de formato."""
    salida = filtrar("¿de que color es el cielo?", CANDIDATOS, _ModeloFalso('{"responden": []}'))
    assert salida.identidades == ()
    assert salida.actuo


def test_el_modelo_no_puede_colar_algo_que_no_estaba() -> None:
    """Numeros fuera de rango se descartan al leerlos: la salida es siempre un
    subconjunto de la entrada."""
    modelo = _ModeloFalso('{"responden": [1, 99, -3, 2]}')
    salida = filtrar("lo que sea", CANDIDATOS, modelo)
    assert set(salida.identidades) <= {i for i, _ in CANDIDATOS}
    assert salida.identidades == ("MEMORIA:14", "MEMORIA:16")


def test_al_modelo_se_le_manda_la_instruccion_y_los_candidatos_numerados() -> None:
    modelo = _ModeloFalso('{"responden": [1]}')
    filtrar("¿acepto escalas?", CANDIDATOS, modelo)
    instruccion, entrada = modelo.recibido[0]
    assert instruccion == INSTRUCCION
    assert "¿acepto escalas?" in entrada
    assert "1. No uses opciones de vuelo con escala." in entrada
    assert "3. El presupuesto maximo" in entrada


def test_con_mas_candidatos_que_el_tope_el_resto_pasa_intacto() -> None:
    """Recortar la cola seria descartar sin que nadie lo mirase.

    El modelo solo juzga los primeros; los demas salen **enteros y en su orden**,
    y despues los recortan las puertas, que es a quien le toca.
    """
    muchos = tuple((f"MEMORIA:{n}", f"dato {n}") for n in range(1, 8))
    modelo = _ModeloFalso('{"responden": [1]}')
    salida = filtrar("lo que sea", muchos, modelo, tope=3)
    assert salida.identidades == ("MEMORIA:1", "MEMORIA:4", "MEMORIA:5", "MEMORIA:6", "MEMORIA:7")


def test_sin_candidatos_no_se_llama_al_modelo() -> None:
    modelo = _ModeloFalso('{"responden": [1]}')
    salida = filtrar("lo que sea", (), modelo)
    assert salida == Filtrado((), False, "no habia candidatos")
    assert modelo.recibido == []


# -- La ingesta -------------------------------------------------------------


def test_la_criba_conserva_una_parafrasis_que_no_comparte_palabras() -> None:
    """El caso que justifica todo esto.

    «¿cual es el limite de gasto?» no comparte ni una palabra significativa con
    «El presupuesto maximo del proyecto es 1.500 EUR», y es justo la pregunta
    que hay que conservar. Un filtro por vocabulario la tiraria.
    """
    modelo = _ModeloFalso(
        '{"preguntas": ["¿cual es el limite de gasto?", "¿cuanto cuesta el vuelo?"]}',
        '{"responden": [1]}',
    )
    salida = ingesta.preguntas_que_responde(
        "El presupuesto maximo del proyecto es 1.500 EUR.", modelo
    )
    assert salida == ("¿cual es el limite de gasto?",)


def test_una_pregunta_alucinada_no_supera_su_propio_examen() -> None:
    modelo = _ModeloFalso(
        '{"preguntas": ["¿cuanto cuesta el vuelo a Madrid?"]}',
        '{"responden": []}',
    )
    assert ingesta.preguntas_que_responde("El presupuesto maximo es 1.500 EUR.", modelo) == ()


def test_si_no_se_puede_cribar_no_se_indexa_nada() -> None:
    """Al reves que el filtro: aqui fallar cerrado SI es lo correcto.

    No ampliar un dato lo deja como estaba; indexar sin cribar mete vocabulario
    alucinado y contamina busquedas ajenas.
    """
    modelo = _ModeloFalso('{"preguntas": ["¿algo?"]}', "no es json")
    assert ingesta.preguntas_que_responde("un dato", modelo) == ()


def test_sin_modelo_la_ingesta_no_revienta() -> None:
    assert ingesta.preguntas_que_responde("un dato", _ModeloCaido()) == ()


def test_el_vocabulario_de_categoria_entra_aunque_el_modelo_falle() -> None:
    """Viene del canon, no del modelo, y por eso no depende de que responda.

    Es lo que ya esta medido: solo con ese vocabulario, los casos en que lo
    correcto entra entero pasan de 24 a 26.
    """
    salida = ingesta.terminos_para_indexar(
        "No usar PostgreSQL en este proyecto.",
        _ModeloCaido(),
        vocabulario_de_categoria=("esencial", "restriccion"),
    )
    assert salida == "esencial restriccion"


def test_los_numeros_fuera_de_rango_no_pasan_la_lectura() -> None:
    assert puerto.numeros_de('{"responden": [1, 5]}', tope=3) == (1,)
    assert puerto.numeros_de('{"responden": []}', tope=3) == ()
    assert puerto.numeros_de("no es json", tope=3) is None
    assert puerto.numeros_de('{"responden": "uno"}', tope=3) is None
    assert puerto.numeros_de('{"responden": [true]}', tope=3) is None
