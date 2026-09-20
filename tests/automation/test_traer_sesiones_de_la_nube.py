"""Lo que el guion que trae las sesiones de la nube tiene que hacer (ADR-001).

El 20-09-2026 se intentaron traer las 34 sesiones de Claude Code que viven en
la nube y **bajaron 6**. No se supo por qué, y ese es el defecto de verdad: el
intento fue un bucle sin registro, así que no quedó rastro de cuál falló, con
qué error, ni por dónde iba cuando se cortó. Sin eso, el segundo intento
empieza de cero y vuelve a no enterarse.

`scripts/traer_sesiones_de_la_nube.ps1` existe para arreglar eso, y estas son
las cuatro propiedades que lo hacen útil en vez de un bucle más bonito:
apuntar cada resultado, comprobar el código de salida de cada llamada, saltarse
lo ya hecho al reanudar, y no borrar nada.

**Aquí no hay PowerShell que ejecutar**, así que se afirma sobre el texto, con
el ayudante `tests/unit/_powershell_text.py`: `executable_text` quita
comentarios y literales para que una afirmación no se cumpla por una frase de
la documentación. Es el límite de estas pruebas y se dice: comprueban que el
guion **dice hacer** lo que debe, no que PowerShell lo ejecute bien.
"""

from __future__ import annotations

import re
from pathlib import Path

from _powershell_text import executable_text

RAIZ = Path(__file__).resolve().parents[2]
GUION = RAIZ / "scripts" / "traer_sesiones_de_la_nube.ps1"

TEXTO = GUION.read_text(encoding="utf-8")
EJECUTABLE = executable_text(TEXTO)

# Un identificador de sesión tal y como el guion lo declara: entrecomillado y
# entero. Sin las comillas, `session_[A-Za-z0-9]{N}` casaría un PREFIJO de cada
# identificador, y entonces la comprobación de duplicados compararía trozos en
# vez de identificadores: pasaría en verde con dos sesiones que solo se
# diferencian en el último carácter.
_SESION = re.compile(r'"(session_[A-Za-z0-9]+)"')


def test_el_guion_existe_y_no_esta_vacio() -> None:
    assert GUION.is_file(), f"falta {GUION.relative_to(RAIZ)}"
    assert len(TEXTO.splitlines()) > 50


def test_trae_las_sesiones_de_la_nube_del_indice_sin_repetir_ninguna() -> None:
    """El índice del 19-09-2026 tiene 35 sesiones en el entorno de la nube."""
    ids = _SESION.findall(TEXTO)
    assert len(ids) == 35, f"el guion lleva {len(ids)} identificadores y el índice tiene 35"
    assert len(set(ids)) == len(ids), "hay identificadores repetidos en la lista"


def test_apunta_el_resultado_de_cada_sesion() -> None:
    """Sin registro, el intento siguiente vuelve a no saber cuál falló."""
    assert "Add-Content $Registro" in EJECUTABLE, (
        "el guion no apunta el resultado de cada sesión: es el defecto que vino a arreglar"
    )


def test_comprueba_el_codigo_de_salida_de_cada_llamada() -> None:
    """La lección de ADR-153: en PowerShell un comando nativo se comprueba.

    `$ErrorActionPreference` no alcanza a los ejecutables nativos. Un bucle que
    no mira `$LASTEXITCODE` cuenta como traídas las que fallaron, que es
    exactamente cómo «bajaron 6» pudo pasar desapercibido.
    """
    assert "$LASTEXITCODE" in EJECUTABLE
    assert re.search(r"\$codigo\s+-eq\s+0", EJECUTABLE), (
        "el guion no decide OK/FALLO comparando el código de salida"
    )


def test_se_puede_reanudar_sin_repetir_lo_ya_traido() -> None:
    """Se cortó una vez; se va a cortar otra. Reanudar no puede costar 35."""
    assert "$YaHechas" in EJECUTABLE and "$Pendientes" in EJECUTABLE
    assert re.search(r"\$YaHechas\s+-notcontains", EJECUTABLE), (
        "el guion no filtra las sesiones ya traídas: al reanudar las pediría todas otra vez"
    )


def test_no_borra_nada_en_la_maquina_del_propietario() -> None:
    """Es una herramienta de traer, no de limpiar. Corre en su ordenador."""
    prohibidos = [
        orden for orden in ("Remove-Item", "rm -", "del ", "rmdir") if orden in EJECUTABLE
    ]
    assert prohibidos == [], f"el guion ejecuta órdenes de borrado: {prohibidos}"


def test_se_detiene_si_falta_lo_que_necesita() -> None:
    """Fallar pronto y diciéndolo, en vez de a mitad y sin explicar."""
    for orden in ("claude", "git"):
        assert f"Get-Command {orden}" in EJECUTABLE, (
            f"el guion no comprueba que `{orden}` esté disponible antes de empezar"
        )
    assert "exit 1" in EJECUTABLE


def test_tiene_un_modo_que_no_trae_nada() -> None:
    """Poder mirar qué haría antes de lanzarlo es lo que permite dirigirlo."""
    assert "$SoloEnsenar" in EJECUTABLE


# --- Que el ayudante no se coma la afirmación --------------------------------


def test_lo_que_solo_esta_en_un_comentario_no_cuenta() -> None:
    """La forma exacta en que dos pruebas de B13 pasaron sin deber pasar."""
    assert "Remove-Item" not in executable_text("# Remove-Item algo\n")
    assert "Remove-Item" in executable_text("Remove-Item algo\n")
