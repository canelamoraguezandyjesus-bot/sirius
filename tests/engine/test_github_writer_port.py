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

# H-29 (auditoría #396) añadió la ÚNICA lectura del puerto, con justificación
# escrita en su docstring: la adopción tras una caída necesita localizar la
# incidencia por su work_id, o el reintento solo puede duplicar o quedarse
# parado. Sigue sin haber tercer verbo de ESCRITURA.
ESCRITURAS_ENUMERADAS = frozenset(
    {"crear_incidencia", "aplicar_etiqueta", "buscar_incidencia_por_work_id"}
)


def test_el_puerto_declara_exactamente_los_dos_verbos_enumerados() -> None:
    metodos_publicos = {
        nombre
        for nombre, miembro in inspect.getmembers(GitHubWriterPort)
        if inspect.isfunction(miembro) and not nombre.startswith("_")
    }
    assert metodos_publicos == ESCRITURAS_ENUMERADAS
