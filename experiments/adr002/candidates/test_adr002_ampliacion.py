"""La ampliacion de consulta: el puerto, la politica y el coste.

Corren en cualquier maquina: la fuente de modelo se prueba con un cliente
inyectado que devuelve lo que la prueba decida, de modo que se comprueba el
**cauce entero** —instruccion, lectura de la respuesta, depuracion, politica—
sin clave, sin red y sin gastar un centimo.

Lo que mas importa aqui es lo que **no** puede pasar: que una fuente cuele
palabras de mas, que la politica tardia amplie sin haber buscado antes, o que un
proveedor que se rompe degrade en silencio a «no amplio nada».
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.ampliacion import fuente as fu
from experiments.adr002.ampliacion.expansor import (
    Expansor,
    Politica,
    recuperar_con_ampliacion,
)
from experiments.adr002.ampliacion.modelo import INSTRUCCION, SinonimosDeModelo

# -- El puerto y la depuracion ---------------------------------------------


def test_la_fuente_nula_da_la_linea_base() -> None:
    """El control: sin fuente no hay ampliacion, y eso tiene que ser visible."""
    expansor = Expansor(fu.SinonimosNulos(), Politica.SIEMPRE)
    ampliacion = expansor.para("¿que restricciones tengo?")
    assert ampliacion.palabras_anadidas == ()
    assert ampliacion.consulta_final == "¿que restricciones tengo?"


def test_no_se_anade_una_palabra_que_ya_estaba_en_la_consulta() -> None:
    """Ampliar con lo que ya se busco no amplia: solo ensancha el ruido."""
    assert fu.depurar(["gasto", "presupuesto"], "limite de gasto") == ("presupuesto",)


def test_se_normaliza_como_lo_hace_el_indice() -> None:
    """Sin tildes y en minusculas, que es como el indice lexico guarda."""
    assert fu.depurar(["Presupuesto", "MÁXIMO"], "limite") == ("presupuesto", "maximo")


def test_el_tope_de_palabras_se_aplica_en_el_puerto() -> None:
    """La cota vive en un solo sitio: una fuente nueva no puede saltarsela."""
    muchas = [f"palabra{n}" for n in range(50)]
    assert len(fu.depurar(muchas, "consulta")) == fu.PALABRAS_MAXIMAS


def test_se_descartan_las_palabras_demasiado_cortas() -> None:
    assert fu.depurar(["de", "el", "presupuesto"], "consulta") == ("presupuesto",)


def test_no_se_repite_una_palabra_dentro_de_la_misma_ampliacion() -> None:
    assert fu.depurar(["tope", "tope", "TOPE"], "consulta") == ("tope",)


# -- La tabla de referencia -------------------------------------------------


def test_la_tabla_responde_por_texto_de_consulta_y_no_por_caso() -> None:
    """Indexada por caso solo serviria sobre el banco; por texto es comparable."""
    tabla = fu.SinonimosDeTabla({"limite de gasto": ["presupuesto", "tope"]})
    assert tabla.sinonimos("LIMITE DE GASTO") == ("presupuesto", "tope")
    assert tabla.sinonimos("otra cosa") == ()


def test_una_tabla_que_no_existe_falla_tipada_y_no_en_silencio(tmp_path: Any) -> None:
    with pytest.raises(fu.FuenteNoDisponibleError):
        fu.SinonimosDeTabla.desde_artefacto(tmp_path / "no_esta.json", {})


def test_el_tope_deja_pasar_la_tabla_de_referencia_entera() -> None:
    """El control tiene que reproducirse **intacto**, o no sirve para comparar.

    Con el tope en ocho —como estuvo primero— la tabla se mutilaba y sus
    omisiones criticas pasaban de 7 a 9, cortando justo las palabras de los tres
    casos que el artefacto senala como los que cargan el peso. Aqui se fija que
    ninguna ampliacion de la referencia se recorta, y se fija leyendo el fichero
    congelado en vez de repetir el numero a mano: si alguien anadiera manana una
    ampliacion mas larga, esta prueba lo dice en vez de degradar en silencio.
    """
    ruta = Path("artifacts/adr002_round/ampliacion_de_consulta_v0.1.json")
    if not ruta.exists():  # pragma: no cover - depende del arbol de trabajo
        pytest.skip("la tabla congelada no esta en este arbol")
    ampliaciones = json.loads(ruta.read_text(encoding="utf-8"))["ampliaciones"]
    mas_larga = max((len(v) for v in ampliaciones.values()), default=0)
    assert mas_larga <= fu.PALABRAS_MAXIMAS, (
        f"la tabla de referencia llega a {mas_larga} palabras y el tope es "
        f"{fu.PALABRAS_MAXIMAS}: el control se estaria midiendo recortado"
    )


# -- La fuente de modelo, sin red -------------------------------------------


@dataclass
class _RespuestaFalsa:
    contenido: str

    @property
    def choices(self) -> list[Any]:
        mensaje = type("M", (), {"content": self.contenido})()
        return [type("C", (), {"message": mensaje})()]


class _ClienteFalso:
    """Un cliente de mentira que registra **exactamente** que se le mando."""

    def __init__(self, contenido: str) -> None:
        self.contenido = contenido
        self.peticiones: list[dict[str, Any]] = []
        self.chat = type("Chat", (), {"completions": self})()

    def create(self, **kwargs: Any) -> _RespuestaFalsa:
        self.peticiones.append(kwargs)
        return _RespuestaFalsa(self.contenido)


def test_al_modelo_solo_se_le_manda_la_consulta() -> None:
    """La frontera que hace que un buen resultado signifique algo.

    Si algo del canon, del banco o de la respuesta esperada llegara al modelo,
    la medicion dejaria de medir una ampliacion para medir un oraculo. Aqui se
    comprueba sobre lo que de verdad se envia, no sobre lo que se promete.
    """
    cliente = _ClienteFalso('{"palabras": ["presupuesto"]}')
    modelo = SinonimosDeModelo(cliente=cliente)
    modelo.sinonimos("¿cual es el limite de gasto?")

    enviado = cliente.peticiones[0]
    contenidos = [m["content"] for m in enviado["messages"]]
    assert contenidos == [INSTRUCCION, "¿cual es el limite de gasto?"]
    assert enviado["temperature"] == 0, "sin determinismo, dos corridas no son comparables"


def test_una_respuesta_ilegible_falla_cerrado() -> None:
    """Nunca degradar en silencio a «no amplio nada»."""
    modelo = SinonimosDeModelo(cliente=_ClienteFalso("esto no es json"))
    with pytest.raises(fu.FuenteNoDisponibleError):
        modelo.sinonimos("consulta")


def test_una_respuesta_que_no_es_una_lista_falla_cerrado() -> None:
    modelo = SinonimosDeModelo(cliente=_ClienteFalso('{"palabras": "presupuesto"}'))
    with pytest.raises(fu.FuenteNoDisponibleError):
        modelo.sinonimos("consulta")


# -- La politica ------------------------------------------------------------


@dataclass
class _PeticionFalsa:
    consulta: str


@dataclass
class _ResultadoFalso:
    suficiencia: str


def test_ampliar_siempre_llama_a_la_fuente_una_vez_por_consulta() -> None:
    expansor = Expansor(fu.SinonimosDeTabla({"a": ["uno"], "b": ["dos"]}), Politica.SIEMPRE)
    busquedas: list[str] = []

    def buscar(peticion: _PeticionFalsa) -> _ResultadoFalso:
        busquedas.append(peticion.consulta)
        return _ResultadoFalso("COMPLETA")

    recuperar_con_ampliacion(_PeticionFalsa("a"), buscar, expansor)
    recuperar_con_ampliacion(_PeticionFalsa("b"), buscar, expansor)
    assert busquedas == ["a uno", "b dos"]
    assert expansor.llamadas_a_la_fuente == 2


def test_la_politica_tardia_no_llama_si_la_primera_busqueda_basto() -> None:
    """El punto entero de la politica tardia: no pagar lo que no hace falta."""
    expansor = Expansor(fu.SinonimosDeTabla({"a": ["uno"]}), Politica.SI_NO_BASTO)
    busquedas: list[str] = []

    def buscar(peticion: _PeticionFalsa) -> _ResultadoFalso:
        busquedas.append(peticion.consulta)
        return _ResultadoFalso("COMPLETA")

    recuperar_con_ampliacion(_PeticionFalsa("a"), buscar, expansor)
    assert busquedas == ["a"]
    assert expansor.llamadas_a_la_fuente == 0


def test_la_politica_tardia_si_llama_cuando_no_basto() -> None:
    expansor = Expansor(fu.SinonimosDeTabla({"a": ["uno"]}), Politica.SI_NO_BASTO)
    busquedas: list[str] = []

    def buscar(peticion: _PeticionFalsa) -> _ResultadoFalso:
        busquedas.append(peticion.consulta)
        return _ResultadoFalso("PARCIAL")

    recuperar_con_ampliacion(_PeticionFalsa("a"), buscar, expansor)
    assert busquedas == ["a", "a uno"]
    assert expansor.llamadas_a_la_fuente == 1


def test_la_misma_consulta_no_se_paga_dos_veces() -> None:
    expansor = Expansor(fu.SinonimosDeTabla({"a": ["uno"]}), Politica.SIEMPRE)
    expansor.para("a")
    expansor.para("a")
    expansor.para("a")
    assert expansor.llamadas_a_la_fuente == 1


def test_la_politica_nunca_no_toca_la_consulta() -> None:
    expansor = Expansor(fu.SinonimosDeTabla({"a": ["uno"]}), Politica.NUNCA)
    busquedas: list[str] = []

    def buscar(peticion: _PeticionFalsa) -> _ResultadoFalso:
        busquedas.append(peticion.consulta)
        return _ResultadoFalso("PARCIAL")

    recuperar_con_ampliacion(_PeticionFalsa("a"), buscar, expansor)
    assert busquedas == ["a"]
    assert expansor.llamadas_a_la_fuente == 0
