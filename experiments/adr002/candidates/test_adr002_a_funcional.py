"""Pruebas funcionales de ``ADR002-A`` — **suspendidas hasta la ficha v2**.

El prototipo cambio al corregir los tres defectos del paquete de correccion
01, y esos cambios afectan a fuentes incluidas en la huella del candidato. La
regla 3 de custodia del acta de ``ADR002-TOL-210`` es explicita: una sucesora
obliga a marcar ``SUSTITUIDA`` la anterior y a **repetir** las ejecuciones
hechas bajo ella.

Por tanto, mientras la ficha vigente no exista, ejecutar el candidato
corregido produciria resultados **no utilizables como evidencia**. No se
ejecutan: se suspenden, y el motivo queda escrito aqui en vez de en un
comentario que nadie lea.

Las pruebas funcionales corregidas —con el caso que solo ``E3`` alcanza y los
controles negativos de barrido— llegan en su propio commit, cuando el commit
de entrada de ``ficha_ADR002-A_v2.json`` sea ancestro estricto.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
FICHA_VIGENTE = RAIZ / "artifacts/adr002_cards/ficha_ADR002-A_v2.json"

pytestmark = pytest.mark.skipif(
    not FICHA_VIGENTE.is_file(),
    reason=(
        "el prototipo se corrigio y la ficha vigente v2 aun no existe: ejecutar el "
        "candidato ahora produciria evidencia no utilizable (TOL-210, regla 3)"
    ),
)


def test_la_suspension_es_temporal_y_esta_declarada() -> None:
    """Si esta prueba corre, la ficha v2 existe y la suspension caduco.

    No comprueba comportamiento del candidato: comprueba que la suspension no
    se quede olvidada. Las pruebas funcionales reales viven en su propio
    modulo, escrito despues de congelar la ficha v2.
    """
    assert FICHA_VIGENTE.is_file()
