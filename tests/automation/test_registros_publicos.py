"""Nada de lo que corre en Actions vuelca la transcripción del agente al log.

El repositorio es público (ADR-044), y los registros de ejecución de Actions de
un repositorio público los lee cualquiera, sin cuenta, durante toda la retención
configurada. `show_full_output: true` desactiva a propósito una protección de
`anthropics/claude-code-action` —el valor por defecto oculta ese volcado y el log
dice literalmente «full output hidden for security»— y publica la transcripción
íntegra: cada comando que el agente ejecutó y su salida cruda, cada fichero que
leyó y su razonamiento intermedio. En `implement` y `repair` ese paso lleva
además el PAT en el entorno y `Bash` sin acotar, así que lo que acaba en el log
no está limitado por ninguna lista de comandos previstos.

Estuvo en `true` mientras el repositorio era privado, con esa justificación
escrita en el propio fichero. Esta prueba existe para que nadie lo reponga con el
mismo argumento sin darse cuenta de que la premisa ya no es cierta.

Se comprueba sobre el YAML cargado, no con un `grep`: `show_full_output: "true"`
o una plantilla `${{ ... }}` no son la cadena `show_full_output: true` y un grep
las dejaría pasar.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def _pasos(documento: Any) -> list[dict[str, Any]]:
    """Todos los pasos de todos los jobs, sin suponer que hay uno por job."""
    pasos: list[dict[str, Any]] = []
    for job in (documento.get("jobs") or {}).values():
        if isinstance(job, dict):
            pasos.extend(paso for paso in (job.get("steps") or []) if isinstance(paso, dict))
    return pasos


def _volcados_de_transcripcion() -> list[str]:
    encontrados: list[str] = []
    for ruta in sorted(WORKFLOWS.glob("*.yml")):
        documento = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        if not isinstance(documento, dict):
            continue
        for paso in _pasos(documento):
            valor = (paso.get("with") or {}).get("show_full_output")
            if valor is None:
                continue
            # Verdadero en YAML es `true`; una cadena "true" o una plantilla que
            # la sesión no puede evaluar cuentan igual: lo que no es un `false`
            # inequívoco se trata como volcado.
            if valor is not False:
                encontrados.append(
                    f"{ruta.name}: {paso.get('name') or paso.get('uses')} -> {valor!r}"
                )
    return encontrados


def test_no_workflow_dumps_the_agent_transcript_to_a_public_log() -> None:
    volcados = _volcados_de_transcripcion()
    assert volcados == [], (
        "estos pasos publicarian la transcripcion completa del agente en un log que "
        "lee cualquiera (ADR-044). Para auditar una ejecucion estan el veredicto en "
        f"SIRIUS_VERDICT_FILE y el resumen del paso: {volcados}"
    )


def test_the_check_actually_looks_at_the_workflows_that_run_a_model() -> None:
    """Anti-vacua: si la prueba dejara de ver los ficheros, pasaria sola."""
    con_modelo = [
        ruta.name
        for ruta in sorted(WORKFLOWS.glob("*.yml"))
        if "anthropics/claude-code-action" in ruta.read_text(encoding="utf-8")
    ]
    assert len(con_modelo) >= 4, f"la prueba ya no encuentra los workflows con modelo: {con_modelo}"
    # Y los pasos que ejecutan el modelo tienen que ser visibles para _pasos().
    vistos = 0
    for ruta in sorted(WORKFLOWS.glob("*.yml")):
        documento = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        if isinstance(documento, dict):
            vistos += sum(
                1
                for paso in _pasos(documento)
                if "anthropics/claude-code-action" in str(paso.get("uses", ""))
            )
    assert vistos >= 4, f"_pasos() no llega a los pasos que ejecutan el modelo: {vistos}"
