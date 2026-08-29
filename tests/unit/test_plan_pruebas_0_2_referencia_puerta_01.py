"""La sección 11 de SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md citaba, para la
precondición 1 de PA-0.2-PUERTA-01, «líneas 306-311 de este mismo documento».
Esas líneas caen dentro de PA-0.2-HIST-01; la precondición 1 real vive en las
líneas 329-334, dentro de la sección 8. Un número de línea se desfasa en cada
edición del documento (incidencia #424); una referencia a la sección (§8) no.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTO = REPO_ROOT / "docs" / "evolution" / "SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md"

REFERENCIA_DESFASADA = re.compile(r"precondici[óo]n 1 de PA-0\.2-PUERTA-01,\s*l[íi]neas\s*\d+-\d+")

REFERENCIA_ESTABLE = re.compile(
    r"precondici[óo]n 1 de PA-0\.2-PUERTA-01,\s*§8 de\s+este mismo documento"
)


SECCION_11 = re.compile(
    r"^## 11\. Criterios de salida de este plan\n(?P<cuerpo>.*?)(?=\n## |\Z)",
    re.DOTALL | re.MULTILINE,
)


def _seccion_11() -> str:
    texto = DOCUMENTO.read_text(encoding="utf-8")
    coincidencia = SECCION_11.search(texto)
    assert coincidencia is not None, (
        "No se encontró el encabezado '## 11. Criterios de salida de este plan' en el documento."
    )
    return coincidencia.group("cuerpo")


def test_la_seccion_11_no_cita_un_numero_de_linea_para_la_precondicion_1() -> None:
    seccion_11 = _seccion_11()
    assert not REFERENCIA_DESFASADA.search(seccion_11), (
        "La sección 11 cita un número de línea para la precondición 1 de "
        "PA-0.2-PUERTA-01; ese número se desfasa en cada edición del documento "
        "(incidencia #424). Debe citar la sección (§8), no líneas."
    )


def test_la_seccion_11_cita_la_precondicion_1_por_seccion() -> None:
    assert REFERENCIA_ESTABLE.search(_seccion_11())
