"""Un defecto encontrado no puede evaporarse.

El 20-08-2026 una auditoría encontró seis defectos y los dejó escritos en un
documento de una rama sin fusionar. El 21-08, **cuatro seguían vivos en
`main`**, sin ninguna incidencia que los siguiera, y la batería completa pasaba
en verde con ellos dentro: 2846 passed. Encontrarlos no sirvió de nada.

Esta prueba no encuentra defectos -eso no lo hace una lista-. Garantiza que uno
ya encontrado **no se pierda**: si un defecto abierto se queda sin incidencia, o
cita un fichero que ya no existe, o alguien lo borra del registro en vez de
cerrarlo, la batería se rompe.

Es deterministaa propósito: lee un fichero y comprueba si una ruta existe. No
razona, no llama a ningún modelo y cuesta milisegundos. Sigue funcionando igual
el día en que el ciclo lo mueva un modelo pequeño y barato.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = RAIZ / "docs" / "audits" / "registro_defectos.yml"

ESTADOS = frozenset({"abierto", "cerrado"})
CAMPOS_SIEMPRE = ("id", "titulo", "bloque", "gravedad", "estado", "ficheros")


def _defectos() -> list[dict[str, Any]]:
    datos = yaml.safe_load(REGISTRO.read_text(encoding="utf-8"))
    return list(datos["defectos"])


def test_el_registro_existe_y_no_esta_vacio() -> None:
    """Anti-vacua: si alguien vacía el registro, las demás pruebas pasarían solas."""
    assert REGISTRO.is_file(), f"falta el registro de defectos: {REGISTRO}"
    assert _defectos(), "el registro no puede quedarse sin defectos: uno cerrado se conserva"


def test_cada_defecto_trae_sus_campos_y_un_estado_conocido() -> None:
    for defecto in _defectos():
        faltan = [campo for campo in CAMPOS_SIEMPRE if campo not in defecto]
        assert faltan == [], f"{defecto.get('id', '?')}: faltan campos {faltan}"
        assert defecto["estado"] in ESTADOS, (
            f"{defecto['id']}: estado {defecto['estado']!r} desconocido; usa {sorted(ESTADOS)}"
        )


def test_ningun_identificador_repetido() -> None:
    ids = [defecto["id"] for defecto in _defectos()]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    assert repetidos == [], f"identificadores repetidos: {repetidos}"


def test_todo_defecto_abierto_tiene_una_incidencia_que_lo_siga() -> None:
    """El corazón de la prueba: sin incidencia, un defecto se olvida."""
    sin_incidencia = [
        defecto["id"]
        for defecto in _defectos()
        if defecto["estado"] == "abierto" and not isinstance(defecto.get("incidencia"), int)
    ]
    assert sin_incidencia == [], (
        f"defectos abiertos sin incidencia que los siga: {sin_incidencia}. "
        "Abre una incidencia y pon su número, o ciérralo con `cerrado_por`."
    )


def test_todo_defecto_cerrado_dice_que_commit_lo_cerro() -> None:
    sin_commit = [
        defecto["id"]
        for defecto in _defectos()
        if defecto["estado"] == "cerrado" and not isinstance(defecto.get("cerrado_por"), str)
    ]
    assert sin_commit == [], f"defectos cerrados sin el commit que los cerró: {sin_commit}"


@pytest.mark.parametrize("defecto", _defectos(), ids=lambda d: str(d["id"]))
def test_los_ficheros_que_cita_un_defecto_existen(defecto: dict[str, Any]) -> None:
    """Un defecto que apunta a un fichero borrado ya no se puede ni comprobar."""
    ausentes = [ruta for ruta in defecto["ficheros"] if not (RAIZ / ruta).exists()]
    assert ausentes == [], (
        f"{defecto['id']} cita ficheros que ya no existen: {ausentes}. "
        "Si el código se movió, actualiza el registro; si el defecto ya no aplica, ciérralo."
    )


# Un defecto que ya existe no puede DESAPARECER del registro: se cierra, no se
# borra. Sin esto, la forma más fácil de poner el registro en verde sería
# borrar la fila incómoda, que es exactamente el fallo que esta prueba viene a
# impedir. Fijados por nombre, igual que `DUPLICADO_HISTORICO` en
# `test_registro_de_decisiones.py`.
#
# Añadir un defecto nuevo NO obliga a tocar esta lista. Borrar uno viejo sí, y
# ahí es donde toca pararse a pensar en vez de teclear.
IDS_QUE_NO_PUEDEN_DESAPARECER = frozenset(
    {"H-1", "H-2", "H-3", "H-4", "H-5", "H-6", "H-7", "H-8", "H-9", "H-10", "H-11", "H-12"}
)


def test_ningun_defecto_conocido_desaparece_del_registro() -> None:
    presentes = {defecto["id"] for defecto in _defectos()}
    desaparecidos = sorted(IDS_QUE_NO_PUEDEN_DESAPARECER - presentes)
    assert desaparecidos == [], (
        f"defectos borrados del registro en vez de cerrados: {desaparecidos}. "
        "Un defecto se cierra con `estado: cerrado` y el commit que lo cerró; "
        "borrarlo hace que se olvide, que es justo lo que este registro impide."
    )


# --- El defecto que sigue abierto aunque su arreglo ya está en main ----------
#
# Dos veces en doce horas: H-11 y H-13 se arreglaron, se fusionaron, y su
# entrada del registro se quedó en `abierto` porque cerrarla dependía de que
# alguien se acordara. La segunda la cometió la misma sesión que había
# corregido la primera, y sobre un defecto que ella misma había registrado.
#
# Esta guarda no depende de la red: mira el historial de git. Reconoce un
# arreglo por la convención que este repositorio ya usa —el asunto del commit
# empieza por el identificador del defecto y dos puntos, como
# `H-13: el motor deja de necesitar el árbol de código`—.
#
# **Su alcance, medido antes de fijarlo (23-08-2026):** sobre los 14 defectos
# del registro, la señal produce **cero falsos positivos**, y habría cazado los
# dos casos reales. Pero solo 4 de los 13 cerrados tienen un commit que siga esa
# convención: los otros nueve se arreglaron con asuntos que no empiezan por el
# identificador. Es decir, **precisión alta y alcance corto**: esta guarda no
# ve el arreglo que no se nombra así, y eso es una limitación conocida, no un
# descuido. Se prefiere de largo a una señal más laxa: un falso positivo aquí
# empujaría a cerrar un defecto que sigue vivo, que es peor que no avisar.

_ASUNTO_DE_ARREGLO = re.compile(r"^(?P<id>H-\d+)\s*:", re.IGNORECASE)


def _asuntos_de_main() -> list[str]:
    salida = subprocess.run(
        ["git", "log", "origin/main", "--format=%s"],
        capture_output=True,
        text=True,
        check=True,
        cwd=RAIZ,
    ).stdout
    return [linea for linea in salida.splitlines() if linea]


def _arreglos_ya_en_main() -> dict[str, list[str]]:
    """Identificador -> asuntos de `main` que dicen arreglarlo."""
    encontrados: dict[str, list[str]] = {}
    for asunto in _asuntos_de_main():
        casa = _ASUNTO_DE_ARREGLO.match(asunto)
        if casa:
            encontrados.setdefault(casa.group("id").upper(), []).append(asunto)
    return encontrados


def test_la_lectura_del_historial_encuentra_algo() -> None:
    """Anti-vacua: sin esto, un `git log` que fallara dejaría la guarda siempre verde."""
    assert _asuntos_de_main(), "no se leyó ningún asunto de main: la guarda no comprobaría nada"
    assert _arreglos_ya_en_main(), (
        "ningún commit de main sigue la convención `H-N: ...`; si de verdad "
        "desapareció, esta guarda dejó de tener entradas y hay que decidir si sobra"
    )


def test_ningun_defecto_abierto_tiene_ya_su_arreglo_en_main() -> None:
    """Un defecto arreglado y fusionado no puede seguir marcado como abierto."""
    arreglos = _arreglos_ya_en_main()
    contradicciones = [
        (defecto["id"], arreglos[defecto["id"].upper()])
        for defecto in _defectos()
        if defecto.get("estado") == "abierto" and defecto["id"].upper() in arreglos
    ]
    assert not contradicciones, "\n".join(
        f"{hid} sigue como `abierto` pero main ya contiene su arreglo: "
        f"{asuntos}. Ciérralo con su `cerrado_por`, o renombra el commit si no "
        "era el arreglo."
        for hid, asuntos in contradicciones
    )
