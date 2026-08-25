"""Un bloque no puede darse por terminado sin decir qué lo demuestra.

El 25-08-2026 el propietario lo dijo con sus palabras: «empezamos construyendo
el bloque, diciendo que está terminado, hablando de bloques, y al final no está
terminado».

Y venía de un malentendido concreto que **no fue una mentira de nadie**: le
dijeron «están todos los bloques hechos» y era cierto —de los **16 bloques del
producto**, cerrados el 10-08-2026—. Él lo entendió como todo, porque nadie
dijo de qué lista se hablaba. Hay dos listas, se llaman igual, y hasta comparten
un identificador: ``B1`` es un bloque del producto **y** un bloque del motor,
dos cosas distintas.

Esta batería no comprueba que un bloque esté bien hecho —eso no lo hace una
lista—. Comprueba dos cosas que sí se pueden comprobar:

1. Que **nadie declare un bloque cerrado sin decir qué comprobación lo cierra**,
   igual que ADR-080 exige para un defecto.
2. Que un bloque abierto **diga qué lo cerraría**, para que «falta» nunca sea
   una palabra suelta.

Es determinista a propósito: lee un fichero y comprueba campos. No razona, no
llama a ningún modelo y cuesta milisegundos.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = RAIZ / "docs" / "implementation" / "bloques_del_motor.yml"

ESTADOS = frozenset({"cerrado", "en_curso", "pendiente", "fuera_de_alcance"})
CAMPOS_SIEMPRE = ("id", "titulo", "estado")

#: Los identificadores que existían el 25-08-2026. Que uno desaparezca del
#: registro no puede pasar en silencio: es exactamente cómo se pierde un bloque
#: de vista, y es el fallo que este fichero existe para impedir.
BLOQUES_CONOCIDOS = frozenset(
    {
        "E0",
        "A1",
        "S1",
        "A2",
        "A3",
        "A4",
        "E1a",
        "A5",
        "S2",
        "B1",
        "E1b",
        "S3",
        "C1",
        "C2",
        "C3",
        "C4",
        "D1",
        "D2",
        "D3",
        "D4",
    }
)


def _texto(valor: Any) -> str:
    """El texto útil de un campo, tratando el hueco como hueco.

    `str(bloque.get("evidencia", ""))` NO vale, y esta prueba nació con ese
    fallo dentro: un campo vacío en YAML se lee como ``None``, y ``str(None)``
    es ``"None"`` -cuatro caracteres que no están en blanco-. La guarda pasaba
    en verde sobre un bloque cerrado SIN evidencia, que es justo lo que existe
    para impedir. Lo cazó la prueba por mutación, no la lectura.
    """
    return "" if valor is None else str(valor).strip()


def _datos() -> dict[str, Any]:
    return dict(yaml.safe_load(REGISTRO.read_text(encoding="utf-8")))


def _bloques() -> list[dict[str, Any]]:
    return list(_datos()["bloques"])


def test_el_registro_existe_y_no_esta_vacio() -> None:
    """Anti-vacua: si alguien vacía el registro, las demás pruebas pasarían solas."""
    assert REGISTRO.is_file(), f"falta el registro de bloques: {REGISTRO}"
    assert _bloques(), "el registro no puede quedarse sin bloques"


def test_el_registro_dice_de_que_lista_habla() -> None:
    """La causa raíz del malentendido: dos listas llamadas «los bloques».

    Sin esta línea el fichero vuelve a ser ambiguo, y la ambigüedad es
    precisamente lo que costó que el propietario diera por terminado el motor
    cuando lo terminado era el producto.
    """
    datos = _datos()
    assert datos.get("lista") == "bloques-del-motor"
    aviso = str(datos.get("no_confundir_con", ""))
    assert "producto" in aviso.lower(), (
        "el registro tiene que decir explícitamente con qué otra lista no se le "
        "puede confundir; si no, «los bloques» vuelve a ser ambiguo"
    )


def test_cada_bloque_trae_sus_campos_y_un_estado_conocido() -> None:
    for bloque in _bloques():
        faltan = [campo for campo in CAMPOS_SIEMPRE if campo not in bloque]
        assert faltan == [], f"{bloque.get('id', '?')}: faltan campos {faltan}"
        assert bloque["estado"] in ESTADOS, (
            f"{bloque['id']}: estado desconocido {bloque['estado']!r}; "
            f"los válidos son {sorted(ESTADOS)}"
        )


def test_ningun_identificador_repetido() -> None:
    ids = [bloque["id"] for bloque in _bloques()]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    assert repetidos == [], f"identificadores repetidos en el registro: {repetidos}"


def test_todo_bloque_cerrado_dice_que_lo_demuestra() -> None:
    """La regla que da sentido a esta batería.

    «Cerrado» sin evidencia es la afirmación que el propietario lleva semanas
    recibiendo y que luego no se sostiene. Un bloque cerrado tiene que decir qué
    comprobación lo cierra, y esa comprobación tiene que poder repetirla otro.
    """
    sin_evidencia = [
        bloque["id"]
        for bloque in _bloques()
        if bloque["estado"] == "cerrado" and not _texto(bloque.get("evidencia"))
    ]
    assert sin_evidencia == [], (
        f"bloques declarados cerrados sin decir qué lo demuestra: {sin_evidencia}. "
        "Escribe la comprobación que lo cierra, o baja su estado."
    )


def test_todo_bloque_abierto_dice_que_lo_cerraria() -> None:
    """«Falta» no puede ser una palabra suelta.

    Un bloque pendiente o en curso sin criterio de cierre es un bloque que nadie
    sabe cuándo terminar, y por tanto uno que se declarará terminado por
    cansancio. `fuera_de_alcance` queda fuera: lo que no se va a hacer no
    necesita criterio para hacerse.
    """
    sin_criterio = [
        bloque["id"]
        for bloque in _bloques()
        if bloque["estado"] in {"pendiente", "en_curso"}
        and not _texto(bloque.get("que_lo_cerraria"))
    ]
    assert sin_criterio == [], (
        f"bloques abiertos sin decir qué los cerraría: {sin_criterio}. "
        "Sin criterio de cierre, «falta» no significa nada."
    )


def test_ningun_bloque_conocido_desaparece() -> None:
    """Borrar un bloque del registro no puede ser la forma de cerrarlo.

    Es la misma propiedad que `test_registro_de_defectos.py` protege para los
    defectos, y por el mismo motivo: lo que desaparece de la lista deja de
    contar sin que nadie lo decida.
    """
    presentes = {bloque["id"] for bloque in _bloques()}
    perdidos = sorted(BLOQUES_CONOCIDOS - presentes)
    assert perdidos == [], (
        f"bloques que estaban en el registro y ya no están: {perdidos}. "
        "Un bloque se cierra cambiando su estado, nunca borrándolo."
    )


# --- Anti-vacuas: los criterios no pueden quedarse inertes -------------------

_CERRADO_SIN_EVIDENCIA = {"id": "X1", "titulo": "t", "estado": "cerrado", "evidencia": "   "}
_CERRADO_CON_EVIDENCIA = {
    "id": "X2",
    "titulo": "t",
    "estado": "cerrado",
    "evidencia": "comando y salida",
}
_ABIERTO_SIN_CRITERIO = {"id": "X3", "titulo": "t", "estado": "pendiente"}
_FUERA = {"id": "X4", "titulo": "t", "estado": "fuera_de_alcance"}


def _cerrado_sin_evidencia(bloque: dict[str, Any]) -> bool:
    return bloque["estado"] == "cerrado" and not _texto(bloque.get("evidencia"))


def _abierto_sin_criterio(bloque: dict[str, Any]) -> bool:
    return bloque["estado"] in {"pendiente", "en_curso"} and not _texto(
        bloque.get("que_lo_cerraria")
    )


def test_el_criterio_de_evidencia_no_se_traga_un_hueco_en_blanco() -> None:
    """Una evidencia de solo espacios no es una evidencia."""
    assert _cerrado_sin_evidencia(_CERRADO_SIN_EVIDENCIA)
    assert not _cerrado_sin_evidencia(_CERRADO_CON_EVIDENCIA)


def test_el_criterio_de_evidencia_trata_el_hueco_de_yaml_como_hueco() -> None:
    """El fallo con el que nació esta prueba, fijado para que no vuelva.

    `evidencia:` sin nada detrás se lee como ``None``, no como cadena vacía. Con
    `str(None)` la guarda veía ``"None"`` y daba por buena la evidencia: pasaba
    en verde sobre un bloque cerrado sin nada que lo demostrara. Lo cazó la
    mutación, no la lectura, y por eso queda escrito aquí.
    """
    assert _cerrado_sin_evidencia(
        {"id": "X5", "titulo": "t", "estado": "cerrado", "evidencia": None}
    )
    assert _abierto_sin_criterio(
        {"id": "X6", "titulo": "t", "estado": "pendiente", "que_lo_cerraria": None}
    )


def test_el_criterio_de_cierre_no_aplica_a_lo_que_no_se_va_a_hacer() -> None:
    assert _abierto_sin_criterio(_ABIERTO_SIN_CRITERIO)
    assert not _abierto_sin_criterio(_FUERA)


@pytest.mark.parametrize("bloque", _bloques(), ids=lambda b: str(b["id"]))
def test_cada_bloque_del_registro_pasa_sus_dos_reglas(bloque: dict[str, Any]) -> None:
    """Una prueba por bloque, para que el fallo nombre cuál es el que falla."""
    assert not _cerrado_sin_evidencia(bloque), f"{bloque['id']}: cerrado sin evidencia"
    assert not _abierto_sin_criterio(bloque), f"{bloque['id']}: abierto sin criterio de cierre"
