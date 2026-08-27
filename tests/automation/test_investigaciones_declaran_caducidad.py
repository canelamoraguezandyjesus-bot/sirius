"""Una investigación sin fecha de caducidad es un fósil que se lee como fuente.

El propietario pidió que las investigaciones no se pierdan. Guardarlas no basta:
la noche del 26 al 27 de agosto de 2026 se configuraron **cuatro veces** modelos
que ya no existían, y tres de los nombres salieron de documentos que **eran
correctos el día que se escribieron** (ADR-095).

Una investigación sobre algo que cambia es una **foto con fecha**. Tratarla como
fuente es el defecto entero, y por eso esta batería exige que cada una diga
cuándo se hizo y **de qué depende para envejecer**.

Determinista: solo lee ficheros.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "docs" / "investigaciones"

CAMPOS = ("titulo", "fecha", "pregunta", "caduca_con", "estado")
ESTADOS = frozenset({"VIGENTE", "PARCIALMENTE CADUCADA", "CADUCADA"})


def _investigaciones() -> list[Path]:
    if not CARPETA.is_dir():
        return []
    return sorted(p for p in CARPETA.glob("*.md") if p.name != "README.md")


def _cabecera(ruta: Path) -> dict[str, Any]:
    """La cabecera YAML de una investigación, o vacío si no la tiene."""
    texto = ruta.read_text(encoding="utf-8")
    if not texto.startswith("---\n"):
        return {}
    fin = texto.find("\n---\n", 4)
    if fin < 0:
        return {}
    return dict(yaml.safe_load(texto[4:fin]) or {})


def test_la_carpeta_existe_y_tiene_su_regla_escrita() -> None:
    """Anti-vacua: sin carpeta, todo lo demás pasaría sin comprobar nada."""
    assert CARPETA.is_dir(), (
        "no existe docs/investigaciones/: las investigaciones se pierden, que es "
        "justo lo que el propietario pidió que no pasara"
    )
    readme = CARPETA / "README.md"
    assert readme.is_file(), "la carpeta no explica su propia regla"
    assert "caduca_con" in readme.read_text(encoding="utf-8"), (
        "el README no nombra el campo que hace útil todo esto"
    )


def test_hay_al_menos_una_investigacion_guardada() -> None:
    """Una carpeta vacía cumpliría todas las demás pruebas sin mérito."""
    assert _investigaciones(), "la carpeta está vacía: no se está guardando nada"


@pytest.mark.parametrize("ruta", _investigaciones(), ids=lambda p: p.name)
def test_cada_investigacion_declara_de_que_depende_para_caducar(ruta: Path) -> None:
    """El campo que separa una fuente de un fósil.

    Sin `caduca_con`, quien la lea dentro de tres meses no tiene forma de saber si
    sigue valiendo, y la creerá. Así se configuraron tres modelos muertos.
    """
    cabecera = _cabecera(ruta)
    faltan = [campo for campo in CAMPOS if not cabecera.get(campo)]
    assert faltan == [], f"{ruta.name}: le faltan {faltan} en su cabecera"
    assert isinstance(cabecera["fecha"], date), (
        f"{ruta.name}: la fecha no es una fecha; sin ella no se puede juzgar si vale"
    )
    assert isinstance(cabecera["caduca_con"], list) and cabecera["caduca_con"], (
        f"{ruta.name}: `caduca_con` tiene que decir de QUÉ depende para envejecer"
    )
    assert cabecera["estado"] in ESTADOS, (
        f"{ruta.name}: estado {cabecera['estado']!r}; los válidos son {sorted(ESTADOS)}"
    )


@pytest.mark.parametrize("ruta", _investigaciones(), ids=lambda p: p.name)
def test_una_investigacion_caducada_avisa_antes_de_su_primera_linea(ruta: Path) -> None:
    """Un documento caducado sin aviso es peor que no tenerlo: se lee y se cree.

    El aviso va ARRIBA, no en un apéndice: quien abre el fichero tiene que
    tropezar con él antes que con las conclusiones.
    """
    cabecera = _cabecera(ruta)
    if cabecera.get("estado") == "VIGENTE":
        return
    texto = ruta.read_text(encoding="utf-8")
    cuerpo = texto[texto.find("\n---\n", 4) + 5 :].lstrip()
    assert cuerpo.startswith(">"), (
        f"{ruta.name} está marcada como {cabecera.get('estado')} y su cuerpo no "
        "empieza por un aviso: se leería como si siguiera valiendo"
    )
    assert "caduc" in cuerpo[:1200].lower(), f"{ruta.name}: el aviso no dice que haya caducado"
