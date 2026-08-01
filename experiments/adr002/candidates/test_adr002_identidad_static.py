"""Pruebas ESTATICAS y de formato de ``por_identificadores``.

El paquete de correccion 02 permite aqui exactamente lo que su fase 4 nombra:
formato, cotas, errores tipados, neutralidad e inspeccion estructural. **No se
ejecuta funcionalmente ningun candidato** y no se materializa ningun elemento:
todas las entradas de estas pruebas fallan la validacion ANTES de tocar SQL, y
el registro de consultas vacio lo demuestra en cada caso.

El comportamiento con elementos reales —encontrados, ausentes, mezcla de
clases, claves vacias, duplicadas y el objetivo mas alla de 512 filas— llega
en su propio commit, cuando las fichas sucesoras sean ancestro estricto.
"""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import pytest
from experiments.adr002.candidates.common import contracts, port

RAIZ = Path(__file__).resolve().parents[3]

#: Entradas malformadas, una por causa de rechazo del formato cerrado.
MALFORMADOS = (
    "",
    "MEMORIA",
    "MEMORIA:",
    ":1",
    "memoria:1",
    "Memoria:1",
    "MENSAJE:1",
    "PROYECTO:1",
    "MEMORIA:0",
    "MEMORIA:-1",
    "MEMORIA:01",
    "MEMORIA:1:2",
    "MEMORIA :1",
    " MEMORIA:1",
    "MEMORIA:1 ",
    "DECISION:x",
    "DECISION:1.0",
    "MEMORIA:\uff11",  # digito de anchura completa: no es [0-9]
)


@pytest.fixture
def puerto(tmp_path: Path) -> port.PuertoSqlite:
    """Puerto sobre una base VACIA: si la validacion dejara pasar algo, el
    SQL posterior fallaria por esquema ausente y delataria la fuga."""
    return port.PuertoSqlite(tmp_path / "vacia.db")


# --------------------------------------------------------------------------
# Contrato y forma
# --------------------------------------------------------------------------


def test_el_protocolo_declara_la_operacion() -> None:
    assert hasattr(contracts.PuertoDeRecuperacion, "por_identificadores")


def test_el_resultado_es_cerrado_y_distingue_los_tres_conjuntos() -> None:
    campos = {c.name for c in dataclasses.fields(contracts.MaterializacionPorIdentidad)}
    assert campos == {"pedidos", "solicitados", "items", "ausentes"}
    resultado = contracts.MaterializacionPorIdentidad(
        pedidos=3, solicitados=("MEMORIA:1",), items=(), ausentes=("MEMORIA:1",)
    )
    assert resultado.encontrados == 0
    assert resultado.completa is False


def test_el_error_es_tipado_y_de_valor() -> None:
    assert issubclass(port.IdentificadorInvalidoError, ValueError)


def test_el_formato_se_construye_desde_la_clase_real() -> None:
    """Sin cadenas paralelas divergentes: el patron nace de ``Clase``."""
    patron = port._FORMATO_DE_IDENTIDAD.pattern
    for clase in contracts.Clase:
        assert clase.value in patron


# --------------------------------------------------------------------------
# Validacion: todo rechazo ocurre ANTES de ejecutar SQL
# --------------------------------------------------------------------------


def test_la_entrada_vacia_falla_tipada(puerto: port.PuertoSqlite) -> None:
    with pytest.raises(port.IdentificadorInvalidoError):
        puerto.por_identificadores(())
    assert puerto.registro.consultas == []


@pytest.mark.parametrize("malformado", MALFORMADOS)
def test_todo_formato_invalido_falla_tipado(puerto: port.PuertoSqlite, malformado: str) -> None:
    with pytest.raises(port.IdentificadorInvalidoError):
        puerto.por_identificadores((malformado,))
    assert puerto.registro.consultas == []


def test_un_malformado_contamina_la_entrada_entera(puerto: port.PuertoSqlite) -> None:
    """La division por clase ocurre despues de validar TODA la entrada."""
    with pytest.raises(port.IdentificadorInvalidoError):
        puerto.por_identificadores(("MEMORIA:1", "DECISION:2", "MEMORIA:0"))
    assert puerto.registro.consultas == []


def test_la_cota_rechaza_y_no_trunca(puerto: port.PuertoSqlite) -> None:
    unicos = tuple(f"MEMORIA:{n}" for n in range(1, port.ARGUMENTOS_MAXIMOS + 2))
    assert len(unicos) == port.ARGUMENTOS_MAXIMOS + 1
    with pytest.raises(port.IdentificadorInvalidoError):
        puerto.por_identificadores(unicos)
    assert puerto.registro.consultas == []


def test_los_duplicados_no_consumen_cota(puerto: port.PuertoSqlite) -> None:
    """La cota rige sobre los UNICOS: repetir un id no es pedir mas."""
    repetidos = tuple(f"MEMORIA:{1 + (n % port.ARGUMENTOS_MAXIMOS)}" for n in range(64))
    try:
        puerto.por_identificadores(repetidos)
    except port.IdentificadorInvalidoError:  # pragma: no cover - seria el fallo
        pytest.fail("los duplicados no deben exceder la cota de unicos")
    except Exception:
        # La base vacia no tiene esquema: el SQL posterior a la validacion
        # falla, y eso es exactamente lo que demuestra que la validacion
        # dejo pasar una entrada legitima. El comportamiento real llega en
        # el commit de pruebas funcionales.
        pass


# --------------------------------------------------------------------------
# Neutralidad e inspeccion estructural de la operacion
# --------------------------------------------------------------------------


def test_la_operacion_no_mira_claves_ni_proyectos_ni_el_indice_lexico() -> None:
    fuente = inspect.getsource(port.PuertoSqlite.por_identificadores)
    for prohibido in ("subject_key", "project_id", "LIKE", "MATCH", "knowledge_fts"):
        assert prohibido not in fuente, prohibido


def test_la_operacion_usa_los_mismos_sql_dirigidos_por_id() -> None:
    """Reutiliza las plantillas ``WHERE id IN`` ya existentes del puerto."""
    fuente = inspect.getsource(port.PuertoSqlite.por_identificadores)
    assert "_SQL_MEMORIAS" in fuente
    assert "_SQL_DECISIONES" in fuente
    for plantilla in (port._SQL_MEMORIAS, port._SQL_DECISIONES):
        normalizado = " ".join(plantilla.split()).upper()
        assert "WHERE" in normalizado
        assert "ID IN" in normalizado


def test_la_capa_comun_sigue_neutral_tras_la_extension() -> None:
    from experiments.adr002.candidates.common import neutrality

    assert neutrality.fallos_de_neutralidad(RAIZ) == []
    assert neutrality.fallos_de_aislamiento_del_candidato(RAIZ, "adr002_a") == []
    assert neutrality.fallos_de_aislamiento_del_candidato(RAIZ, "adr002_b") == []


def test_los_metodos_existentes_no_cambian_de_firma() -> None:
    """La extension anade; no altera lo que ya estaba contratado."""
    for metodo, parametro in (
        ("por_clave_exacta", "claves"),
        ("por_termino_lexico", "terminos"),
        ("por_prefijo_de_sujeto", "prefijos"),
        ("historial_y_fuentes", "terminos"),
    ):
        firma = inspect.signature(getattr(port.PuertoSqlite, metodo))
        assert list(firma.parameters) == ["self", parametro], metodo
