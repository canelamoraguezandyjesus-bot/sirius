"""H-14: un fallo de Quality no trae observaciones, y eso no puede matar al bloque.

El corrector exigía observaciones estructuradas **sin excepción** antes de mirar
nada más. Un `CI_FAILURE` no trae ninguna: el fallo ES la observación, y vive en
los logs del run, no en un bloque JSON de la incidencia. Así que la puerta se
cerraba y el bloque moría en `sirius:failed-safely`.

Le pasó a **H-13 (#275)** el 23-08-2026, por una prueba de una línea con su
mensaje de error ya explicado. El corrector se activó, no encontró observaciones
y paró; el bloque quedó muerto hasta que una sesión interactiva lo arregló a
mano.

Y el prompt del corrector prometía exactamente lo que su propia maquinaria le
impedía:

    Confirma que existe una causa corregible:
    - hallazgos CHANGES_REQUESTED publicados por la Routine revisora; **o**
    - un resultado fallido de Quality ligado al head actual.

La segunda mitad era inalcanzable.

**Esta batería ejecuta la función REAL** (`sirius_ronda_disparada_por_ci`, en
`scripts/automation/sirius_issue.sh`), no una copia de su lógica: una copia se
queda atrás en cuanto alguien toca el original, y entonces la prueba pasa
mientras producción falla.

Y comprueba además que el workflow **la llama**, porque este repositorio ya lleva
cuatro casos de una pieza correcta a la que no llamaba nadie: el despachador,
H-13, el supervisor y el contador de los siete días.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
LIBRERIA = RAIZ / "scripts" / "automation" / "sirius_issue.sh"
CORRECTOR = RAIZ / ".github" / "workflows" / "repair-sirius-work.yml"

FUNCION = "sirius_ronda_disparada_por_ci"

HEAD = "3f9a1c2d4e5b6a7c8d9e0f1a2b3c4d5e6f7a8b9c"
OTRO_HEAD = "0011223344556677889900112233445566778899"


def _con_volcado(tmp_path: Path, texto: str, head: str) -> int:
    volcado = tmp_path / "comentarios.txt"
    volcado.write_text(texto, encoding="utf-8")
    completado = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            f'source "{LIBRERIA}" >/dev/null 2>&1; {FUNCION} "$1" "$2"',
            "bash",
            str(volcado),
            head,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return completado.returncode


def test_la_funcion_existe_en_la_libreria_de_produccion() -> None:
    """Anti-vacua: sin la función, todo lo demás mediría un bash que no hace nada."""
    assert LIBRERIA.is_file(), f"falta {LIBRERIA}"
    assert FUNCION in LIBRERIA.read_text(encoding="utf-8"), (
        f"`{FUNCION}` desapareció de la librería: el corrector volvería a morir "
        "ante cualquier fallo de Quality (H-14)"
    )


def test_un_fallo_de_quality_sobre_el_head_actual_abre_la_puerta(tmp_path: Path) -> None:
    """El caso de H-13 (#275), que es el que costó una noche."""
    volcado = f"## CI_FAILURE\nQuality falló.\n<!-- sirius-quality:{HEAD}:failure -->\n"
    assert _con_volcado(tmp_path, volcado, HEAD) == 0


def test_un_timeout_de_quality_cuenta_igual(tmp_path: Path) -> None:
    """`timed_out` es un fallo de CI como cualquier otro, y ya lo trata así apply_verdict."""
    volcado = f"<!-- sirius-quality:{HEAD}:timed_out -->\n"
    assert _con_volcado(tmp_path, volcado, HEAD) == 0


def test_un_fallo_de_OTRO_head_no_abre_la_puerta(tmp_path: Path) -> None:
    """La propiedad que impide que la puerta quede abierta para siempre.

    Si bastara con «hubo un CI_FAILURE alguna vez», una incidencia que falló CI
    una sola vez aceptaría después cualquier ronda de revisión sin observaciones
    como si fuera un fallo de CI. La pregunta es por el head que hay AHORA.
    """
    volcado = f"<!-- sirius-quality:{OTRO_HEAD}:failure -->\n"
    assert _con_volcado(tmp_path, volcado, HEAD) == 1


def test_un_exito_de_quality_no_abre_la_puerta(tmp_path: Path) -> None:
    volcado = f"<!-- sirius-quality:{HEAD}:success -->\n"
    assert _con_volcado(tmp_path, volcado, HEAD) == 1


def test_sin_ningun_marcador_la_puerta_sigue_cerrada(tmp_path: Path) -> None:
    """El comportamiento de siempre, que NO se quería cambiar."""
    volcado = "## OBSERVACIONES_ESTRUCTURADAS\nnada que ver\n"
    assert _con_volcado(tmp_path, volcado, HEAD) == 1


def test_sin_head_la_puerta_se_cierra(tmp_path: Path) -> None:
    """Ante la duda, se para. No poder comprobarlo es el peor motivo para abrir."""
    volcado = f"<!-- sirius-quality:{HEAD}:failure -->\n"
    assert _con_volcado(tmp_path, volcado, "") == 1


def test_un_volcado_vacio_cierra_la_puerta(tmp_path: Path) -> None:
    """Una lectura caída deja el volcado vacío: eso no es «no hubo fallo de CI»."""
    assert _con_volcado(tmp_path, "", HEAD) == 1


# --- Que la función no se quede sin llamante, que es la enfermedad de esta casa ---


def _doc() -> dict[Any, Any]:
    return dict(yaml.safe_load(CORRECTOR.read_text(encoding="utf-8")))


def _paso_de_la_puerta() -> str:
    for job in (_doc().get("jobs") or {}).values():
        for paso in job.get("steps") or []:
            if paso.get("id") == "gate":
                return str(paso.get("run", ""))
    raise AssertionError("no encontré el paso `id: gate` en repair-sirius-work.yml")


def _sin_comentarios(guion: str) -> str:
    """El guion sin sus líneas de comentario.

    ESTA FUNCIÓN NACIÓ DE UNA MUTACIÓN QUE NO FALLÓ. La primera versión de
    `test_el_corrector_llama_a_la_funcion` buscaba el nombre de la función en el
    texto del paso, y el nombre **también aparece en el comentario** que explica
    el arreglo. Al sustituir la llamada real por `if false; then`, la prueba
    siguió en verde: era vacua. Un guardián que se conforma con que algo esté
    NOMBRADO no comprueba que esté LLAMADO, y esa diferencia es justo la
    enfermedad que este fichero existe para vigilar.
    """
    return "\n".join(linea for linea in guion.splitlines() if not linea.lstrip().startswith("#"))


def test_el_corrector_llama_a_la_funcion() -> None:
    """La cuarta pieza sin llamante de este repositorio no va a ser la quinta."""
    assert FUNCION in _sin_comentarios(_paso_de_la_puerta()), (
        f"la puerta del corrector no llama a `{FUNCION}`: la función estaría bien "
        "escrita y H-14 seguiría abierto igual, que es exactamente cómo llevaban "
        "semanas el despachador, el supervisor y el contador"
    )


def test_el_volcado_sigue_vivo_cuando_se_le_pregunta() -> None:
    """El orden importa, y romperlo no daría error: daría un `1` silencioso.

    `sirius_ronda_disparada_por_ci` recibe el volcado de comentarios. Si alguien
    vuelve a borrarlo antes de la comprobación de observaciones, la función leería
    un fichero inexistente, devolvería 1 y el corrector pararía **igual que
    antes** — con H-14 reabierto y sin un solo mensaje de error que lo delatara.
    """
    guion = _paso_de_la_puerta()
    llamada = _paso_de_la_puerta().index(FUNCION)
    borrados = [
        pos
        for pos in range(len(guion))
        if guion.startswith('rm -f "$comments_file"', pos)
        or guion.startswith('rm -f "$body_file" "$comments_file"', pos)
    ]
    prematuros = [pos for pos in borrados if pos < llamada]
    # Los borrados de las salidas tempranas (sin-pr, varias-pr) SÍ preceden a la
    # llamada en el texto, pero cada uno va seguido de `exit 0`: ese camino no
    # llega nunca a preguntar. Se exige que todo borrado anterior salga del paso.
    for pos in prematuros:
        cola = guion[pos : pos + 200]
        assert "exit 0" in cola, (
            'hay un `rm -f "$comments_file"` antes de la comprobación de H-14 que '
            "NO termina en `exit 0`: la función recibiría un fichero borrado, "
            "devolvería 1 en silencio y el corrector volvería a morir ante cada "
            "fallo de Quality"
        )
