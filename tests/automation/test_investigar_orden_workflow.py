"""La costura de B1: dos workflows, una etiqueta, y el perfil como llave.

El riesgo de este diseño no está en ninguno de los dos ficheros por separado:
está en que DIVERJAN -que los dos atiendan la misma incidencia, o ninguno-. Por
eso estas pruebas leen los DOS YAML y comprueban el reparto, no la prosa.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
IMPLEMENTADOR = RAIZ / ".github" / "workflows" / "implement-sirius-work.yml"
INVESTIGADOR = RAIZ / ".github" / "workflows" / "investigar-orden.yml"


def _doc(ruta: Path) -> dict[str, Any]:
    return dict(yaml.safe_load(ruta.read_text(encoding="utf-8")))


def _trabajo_unico(ruta: Path) -> dict[str, Any]:
    trabajos = _doc(ruta).get("jobs") or {}
    assert len(trabajos) == 1, f"{ruta.name}: se esperaba un solo trabajo"
    (trabajo,) = trabajos.values()
    return dict(trabajo)


def _pasos(ruta: Path) -> list[dict[str, Any]]:
    return [dict(p) for p in _trabajo_unico(ruta).get("steps") or []]


def _paso_puerta(ruta: Path) -> dict[str, Any]:
    for paso in _pasos(ruta):
        if paso.get("id") == "gate":
            return paso
    raise AssertionError(f"{ruta.name}: no hay paso con id 'gate'")


def test_los_dos_escuchan_la_misma_etiqueta_de_activacion() -> None:
    """Si escucharan etiquetas distintas, el reparto por perfil no repartiría
    nada: una de las dos clases se quedaría sin dueño en silencio."""
    for ruta in (IMPLEMENTADOR, INVESTIGADOR):
        trabajo = _trabajo_unico(ruta)
        assert "sirius:implement-requested" in str(trabajo.get("if", "")), (
            f"{ruta.name}: su trabajo no filtra por la etiqueta de activación"
        )


def test_el_implementador_excluye_al_investigador_antes_de_consumir() -> None:
    """Pregunta 2 de la nota de arranque, y la mitad que más costaría ver rota:
    si la exclusión fuera después de consumir, las etiquetas ya estarían
    movidas y NADIE atendería la orden."""
    pasos = _pasos(IMPLEMENTADOR)
    indice_puerta = next(i for i, p in enumerate(pasos) if p.get("id") == "gate")
    puerta = pasos[indice_puerta]
    assert "investigador" in str(puerta.get("run", "")), (
        "la puerta del implementador no menciona el perfil investigador: "
        "los dos workflows atenderían la misma incidencia a la vez"
    )
    indice_consumo = next(
        i for i, p in enumerate(pasos) if "Consumir el evento" in str(p.get("name", ""))
    )
    assert indice_puerta < indice_consumo, (
        "la exclusión va DESPUÉS de consumir el evento: la incidencia quedaría "
        "en sirius:implementing sin que nadie la atienda"
    )


def test_el_investigador_exige_su_perfil_y_valida_la_activacion() -> None:
    puerta = _paso_puerta(INVESTIGADOR)
    orden = str(puerta.get("run", ""))
    assert '"$perfil" != "investigador"' in orden, (
        "la puerta del investigador no exige el perfil: atendería encargos del implementador"
    )
    assert "sirius_validate_activation.sh" in orden, (
        "no valida la activación: la etiqueta sola no basta, es la misma regla que el implementador"
    )


def test_el_ejecutor_corre_al_guion_real_y_aplica_el_veredicto_del_ciclo() -> None:
    pasos = _pasos(INVESTIGADOR)
    ordenes = "\n".join(str(p.get("run", "")) for p in pasos)
    assert "scripts/investigacion/atender_orden.py" in ordenes, (
        "el workflow no llama al guion que atiende la orden: pieza sin llamante"
    )
    assert "sirius_apply_verdict.sh" in ordenes, "no aplica el veredicto al ciclo"
    assert '"implementer"' in ordenes, (
        "el veredicto no se aplica con el rol implementer, que es el único rol "
        "de productor de entregable que ese guion entiende (criterio (a): "
        "hablar el idioma del ciclo, no enseñarle otro)"
    )
    assert "PR abierta: ${url}" in ordenes, (
        "no publica el comentario literal `PR abierta:` que el ciclo usa para resolver la PR"
    )


def test_el_veredicto_se_aplica_siempre_que_la_puerta_dejara_pasar() -> None:
    """Si el paso del veredicto no fuera `always()`, una investigación muerta a
    mitad dejaría la incidencia en implementing para siempre: exactamente el
    silencio que el veredicto provisional existe para impedir."""
    pasos = _pasos(INVESTIGADOR)
    # Se busca la INVOCACIÓN, no el nombre: un comentario de otro paso que cite
    # el guion no es una llamada -el guardián vacuo de esta casa ya mordió una
    # vez dentro de esta misma prueba, confundiendo el paso de la PR (cuyo
    # comentario nombra al guion) con el paso que lo ejecuta-.
    # Desde ADR-152 la invocación va contra la copia congelada de `main`.
    veredicto = next(
        p
        for p in pasos
        if 'bash "${RUNNER_TEMP}/automation-de-main/sirius_apply_verdict.sh"'
        in str(p.get("run", ""))
    )
    assert "always()" in str(veredicto.get("if", "")), (
        "el veredicto solo se aplicaría en el camino feliz"
    )


def test_las_claves_del_ejecutor_son_las_de_la_configuracion_elegida() -> None:
    """NVIDIA obligatoria y Tavily opcional (ADR-098/PR #380): las mismas del
    banco, ninguna de OpenAI ni Anthropic (criterio de parada (c))."""
    pasos = _pasos(INVESTIGADOR)
    entradas: set[str] = set()
    for paso in pasos:
        for variable, valor in (paso.get("env") or {}).items():
            if "secrets." in str(valor):
                entradas.add(str(variable))
    claves_api = {v for v in entradas if v.endswith("_API_KEY")}
    assert claves_api == {"NVIDIA_API_KEY", "TAVILY_API_KEY"}, claves_api
    assert not any("OPENAI" in v or "ANTHROPIC" in v for v in entradas), (
        f"el ejecutor pide claves prohibidas: {sorted(entradas)}"
    )


def test_el_tope_del_ejecutor_respeta_la_ventana_del_contador() -> None:
    """Criterio de parada (b): por encima de 85 se rompe la tolerancia del
    contador de los siete días (§11.2, medido)."""
    tope = _trabajo_unico(INVESTIGADOR).get("timeout-minutes")
    assert isinstance(tope, int) and tope <= 85, f"timeout-minutes={tope}"


def test_el_ejecutor_deja_que_el_texto_decida_la_profundidad() -> None:
    """El interruptor del propietario (28-08-2026): el workflow pasa `--tipo
    auto` y es el TEXTO de la orden quien decide. Si volviera a clavar `deep`,
    toda orden costaría ~40-60 créditos del buscador y ~25 minutos aunque
    pidiera cómo conectar un Arduino —que es exactamente lo que el propietario
    pidió poder evitar—. La mutación que clava `deep` pasó en verde sin esta
    prueba."""
    pasos = _pasos(INVESTIGADOR)
    atiende = next(
        p for p in pasos if "scripts/investigacion/atender_orden.py" in str(p.get("run", ""))
    )
    # SIN los comentarios del bloque `run:`: la primera versión de esta prueba
    # y su mutación se aprobaron mutuamente contra el comentario del paso, que
    # contiene la misma cadena. Es la tercera vez HOY que esta familia muerde;
    # la receta de la casa es mirar solo el código.
    codigo_del_paso = "\n".join(
        linea
        for linea in str(atiende.get("run", "")).splitlines()
        if not linea.strip().startswith("#")
    )
    assert "--tipo auto" in codigo_del_paso, (
        "el COMANDO del workflow no pasa `--tipo auto`: el interruptor de "
        "profundidad quedaría sin llamante y todas las órdenes irían al precio caro"
    )
