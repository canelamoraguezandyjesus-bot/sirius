"""Un turno programado del motor tiene que ACTUAR, no ensayar.

Este fichero nace de un fallo que estuvo a punto de entrar el 25-08-2026, al
darle horario al motor (D2, ADR-090). El paso «Dar el turno» decidía así:

    if [ "${{ inputs.ensayo }}" = "false" ]; then
      uv run sirius-supervisar
    else
      uv run sirius-supervisar --ensayo
    fi

En un evento ``schedule`` **no hay inputs**: ``inputs.ensayo`` se expande a la
cadena vacía, y ``"" = "false"`` es falso. Es decir, **todos** los turnos
programados se habrían ido por la rama del ensayo: el motor corriendo cada seis
horas para no hacer nada, en verde y para siempre.

Es exactamente la familia que este repositorio lleva semanas persiguiendo -un
verde que no significa «funciona» sino «no llegó a intentarlo»- y esta vez
habría quedado cableada a propósito.

La guarda no lee el YAML buscando una frase: **ejecuta el guión real** con los
cuatro eventos posibles y comprueba qué rama toma. Leerlo no habría bastado,
porque el fallo estaba en cómo bash trata una variable vacía, no en el texto.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / ".github" / "workflows" / "motor-sirius.yml"

#: Lo que cada combinación tiene que producir. La primera fila es la que motiva
#: este fichero: sin `EVENTO`, daba «ensayo».
CASOS = (
    ("schedule", "", "actua"),
    ("workflow_dispatch", "false", "actua"),
    ("workflow_dispatch", "true", "ensayo"),
    ("workflow_dispatch", "", "ensayo"),
)


def _workflow() -> dict[str, Any]:
    return dict(yaml.safe_load(MOTOR.read_text(encoding="utf-8")))


def _paso_del_turno() -> dict[str, Any]:
    for paso in _workflow()["jobs"]["turno"]["steps"]:
        if paso.get("name") == "Dar el turno":
            return dict(paso)
    raise AssertionError("no se encontró el paso «Dar el turno» en motor-sirius.yml")


def _guion_ejecutable() -> str:
    """El `run:` del paso, con las expansiones de GitHub ya resueltas.

    GitHub sustituye `${{ ... }}` ANTES de que bash lea nada. Aquí se hace lo
    mismo con los valores que importan, y se sustituye la invocación real del
    motor por un `echo`: lo que se comprueba es QUÉ RAMA se toma, no que el
    supervisor funcione -eso lo cubren sus propias pruebas-.
    """
    guion = str(_paso_del_turno()["run"])
    guion = re.sub(r"uv run sirius-supervisar --ensayo", "echo RAMA=ensayo", guion)
    guion = re.sub(r"uv run sirius-supervisar", "echo RAMA=actua", guion)
    return guion


def test_el_motor_tiene_horario() -> None:
    """Sin esto, las demás pruebas de este fichero validarían un motor que no corre solo."""
    disparadores = _workflow()[True]
    assert "schedule" in disparadores, (
        "el motor perdió su horario: si vuelve a dispararse solo a mano, "
        "D2 deja de estar cerrado y este fichero comprueba algo que ya no pasa"
    )
    crones = [str(entrada["cron"]) for entrada in disparadores["schedule"]]
    assert crones, "el horario existe pero no declara ningún cron"


def test_el_horario_no_pisa_al_reconciliador() -> None:
    """El reconciliador asienta el mundo; el motor lo mira después.

    No es estética: el reconciliador repara estados que ningún evento puede ya
    revivir, y que el motor razone sobre un estado que está a punto de cambiar
    es cómo se toman decisiones sobre información caduca.
    """
    reconciliador = yaml.safe_load(
        (RAIZ / ".github" / "workflows" / "reconcile-sirius-states.yml").read_text(
            encoding="utf-8"
        )
    )
    minuto_reconciliador = int(str(reconciliador[True]["schedule"][0]["cron"]).split()[0])
    minuto_motor = int(str(_workflow()[True]["schedule"][0]["cron"]).split()[0])

    assert minuto_motor != minuto_reconciliador, (
        "el motor y el reconciliador arrancarían a la vez, y no comparten grupo "
        "de concurrencia: nada los serializa"
    )
    assert minuto_motor > minuto_reconciliador, (
        f"el motor arranca en el minuto {minuto_motor} y el reconciliador en el "
        f"{minuto_reconciliador}: el orden previsto es al revés, primero asentar "
        "y después supervisar"
    )


@pytest.mark.parametrize(("evento", "ensayo", "esperado"), CASOS)
def test_el_guion_real_toma_la_rama_que_debe(evento: str, ensayo: str, esperado: str) -> None:
    """Se EJECUTA el guión del workflow, no se lee.

    El fallo que motiva este fichero no estaba en el texto: estaba en cómo bash
    trata una variable vacía. Una prueba que buscara una frase en el YAML habría
    pasado en verde con el defecto dentro.
    """
    proceso = subprocess.run(
        ["bash", "-c", _guion_ejecutable()],
        env={"EVENTO": evento, "ENSAYO_PEDIDO": ensayo, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert proceso.returncode == 0, f"el guión falló: {proceso.stderr}"
    assert f"RAMA={esperado}" in proceso.stdout, (
        f"evento={evento!r} ensayo={ensayo!r} tomó la rama equivocada.\n"
        f"esperado RAMA={esperado}, salida:\n{proceso.stdout}"
    )


def test_un_turno_programado_no_puede_decidirse_solo_por_el_input() -> None:
    """La mutación que hace inútil a este fichero, fijada.

    Si alguien vuelve a decidir la rama mirando únicamente `inputs.ensayo`, los
    turnos programados vuelven a ensayar en silencio. Esta prueba no lee el
    YAML: comprueba que el guión distingue el EVENTO, ejecutándolo con el input
    vacío que un `schedule` produce de verdad.
    """
    guion = _guion_ejecutable()
    assert "EVENTO" in guion, (
        "el guión ya no mira el evento; con `inputs.ensayo` vacío en un "
        "`schedule`, todos los turnos programados se irían al ensayo"
    )

    proceso = subprocess.run(
        ["bash", "-c", guion],
        env={"EVENTO": "schedule", "ENSAYO_PEDIDO": "", "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert "RAMA=actua" in proceso.stdout, (
        "un turno programado con el input vacío -que es lo que GitHub produce- "
        "tiene que ACTUAR. Si ensaya, el motor corre cada seis horas para no "
        "hacer nada, en verde y para siempre."
    )
