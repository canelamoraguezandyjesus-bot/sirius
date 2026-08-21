"""``GitHubWriterPort`` declara exactamente dos verbos de escritura (C2-P4, #240).

Si algún día se le añade un tercer método -comentar, cerrar, editar el
cuerpo, tocar una PR- esta prueba cae, y quien lo añadió tiene que
justificarlo explícitamente en vez de que se cuele "ya que estamos"
(alcance permitido de la incidencia #240: "la escritura es mínima y
enumerada").
"""

from __future__ import annotations

import inspect

from sirius_engine.ports.github_writer import GitHubWriterPort

ESCRITURAS_ENUMERADAS = frozenset({"crear_incidencia", "aplicar_etiqueta"})


def test_el_puerto_declara_exactamente_los_dos_verbos_enumerados() -> None:
    metodos_publicos = {
        nombre
        for nombre, miembro in inspect.getmembers(GitHubWriterPort)
        if inspect.isfunction(miembro) and not nombre.startswith("_")
    }
    assert metodos_publicos == ESCRITURAS_ENUMERADAS
