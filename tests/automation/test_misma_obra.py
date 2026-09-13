"""`sirius_misma_obra.py`: ¿el trabajo propio de la rama es el mismo? (#608, parte 2).

El coste que esto quita, en palabras del propietario: «cada vez que fusiono, se
mueve main, y entonces tengo que actualizar la otra, que pase por Quality y que
tenga que revisar otra vez. O sea, otra ronda más solo por fusionar una cosa».

`advance-sirius-after-quality.yml` ya sabe (ADR-142) que un re-run de Quality
sobre el head YA APROBADO no debe reponer `sirius:review-requested`. Pero exige
que el head sea EXACTAMENTE el aprobado, así que ponerse al día con `main`
-que mueve el head sin tocar el trabajo- tira la aprobación y cuesta una ronda
entera de revisión.

Este módulo decide lo único que falta para distinguir los dos casos: si el
trabajo PROPIO de la rama (su diff contra la base de mezcla, que es lo que
`gh api repos/X/compare/BASE...SHA` devuelve) es el mismo en el head aprobado y
en el vigente. No lee red ni git: recibe las dos comparaciones ya leídas, que es
lo que lo hace comprobable aquí.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "automation" / "sirius_misma_obra.py"


def _cargar() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sirius_misma_obra", SCRIPT)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def misma_obra() -> ModuleType:
    return _cargar()


def _comparacion(*ficheros: tuple[str, str]) -> dict[str, object]:
    """La forma que devuelve `gh api repos/X/compare/BASE...SHA`, recortada."""
    return {
        "status": "ahead",
        "files": [{"filename": nombre, "patch": parche} for nombre, parche in ficheros],
    }


def _escribir(tmp_path: Path, nombre: str, datos: dict[str, object]) -> Path:
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return ruta


# --- lo que tiene que reconocer ------------------------------------------------------


def test_el_mismo_trabajo_en_dos_heads_distintos_es_la_misma_obra(
    misma_obra: ModuleType, tmp_path: Path
) -> None:
    """EL caso de #608: el push solo trajo `main`, el trabajo propio no cambió."""
    obra = _comparacion(("src/a.py", "@@ -1 +1 @@\n-viejo\n+nuevo"))
    aprobado = _escribir(tmp_path, "aprobado.json", obra)
    vigente = _escribir(tmp_path, "vigente.json", obra)

    assert misma_obra.es_la_misma_obra(aprobado, vigente) is True


def test_una_linea_distinta_ya_no_es_la_misma_obra(misma_obra: ModuleType, tmp_path: Path) -> None:
    """La pregunta que decide si esto es una mejora o un agujero: un cambio real,
    aunque sea de una línea, tiene que volver a abrir ronda de revisión."""
    aprobado = _escribir(
        tmp_path, "aprobado.json", _comparacion(("src/a.py", "@@ -1 +1 @@\n-viejo\n+nuevo"))
    )
    vigente = _escribir(
        tmp_path, "vigente.json", _comparacion(("src/a.py", "@@ -1 +1 @@\n-viejo\n+otro"))
    )

    assert misma_obra.es_la_misma_obra(aprobado, vigente) is False


def test_un_fichero_de_mas_no_es_la_misma_obra(misma_obra: ModuleType, tmp_path: Path) -> None:
    aprobado = _escribir(tmp_path, "aprobado.json", _comparacion(("src/a.py", "@@ -1 +1 @@\n+x")))
    vigente = _escribir(
        tmp_path,
        "vigente.json",
        _comparacion(("src/a.py", "@@ -1 +1 @@\n+x"), ("src/b.py", "@@ -0,0 +1 @@\n+y")),
    )

    assert misma_obra.es_la_misma_obra(aprobado, vigente) is False


def test_el_orden_de_los_ficheros_no_cambia_la_respuesta(
    misma_obra: ModuleType, tmp_path: Path
) -> None:
    """GitHub no promete orden estable en `files`, y un orden distinto no es
    trabajo distinto: compararlo sin ordenar daría rondas de más por nada."""
    a = ("src/a.py", "@@ -1 +1 @@\n+x")
    b = ("src/b.py", "@@ -1 +1 @@\n+y")
    aprobado = _escribir(tmp_path, "aprobado.json", _comparacion(a, b))
    vigente = _escribir(tmp_path, "vigente.json", _comparacion(b, a))

    assert misma_obra.es_la_misma_obra(aprobado, vigente) is True


# --- fail-closed: si no se puede afirmar, no se afirma ---------------------------------


def test_sin_la_clave_files_no_se_afirma_nada(misma_obra: ModuleType, tmp_path: Path) -> None:
    """Pregunta 3 de la nota de arranque: si la comparación no se puede leer, la
    respuesta es NO -se abre ronda, como hoy-, nunca un sí por defecto."""
    aprobado = _escribir(tmp_path, "aprobado.json", {"status": "ahead"})
    vigente = _escribir(tmp_path, "vigente.json", _comparacion(("src/a.py", "@@ -1 +1 @@\n+x")))

    assert misma_obra.es_la_misma_obra(aprobado, vigente) is False


def test_un_fichero_que_no_existe_no_es_la_misma_obra(
    misma_obra: ModuleType, tmp_path: Path
) -> None:
    vigente = _escribir(tmp_path, "vigente.json", _comparacion(("src/a.py", "@@ -1 +1 @@\n+x")))

    assert misma_obra.es_la_misma_obra(tmp_path / "no-existe.json", vigente) is False


def test_un_json_roto_no_es_la_misma_obra(misma_obra: ModuleType, tmp_path: Path) -> None:
    roto = tmp_path / "roto.json"
    roto.write_text("{esto no es json", encoding="utf-8")
    vigente = _escribir(tmp_path, "vigente.json", _comparacion(("src/a.py", "@@ -1 +1 @@\n+x")))

    assert misma_obra.es_la_misma_obra(roto, vigente) is False


def test_dos_comparaciones_vacias_no_son_la_misma_obra(
    misma_obra: ModuleType, tmp_path: Path
) -> None:
    """Una rama sin trabajo propio no es un caso que este atajo deba cubrir: si
    las dos comparaciones vienen sin ficheros, lo honesto es abrir ronda."""
    aprobado = _escribir(tmp_path, "aprobado.json", _comparacion())
    vigente = _escribir(tmp_path, "vigente.json", _comparacion())

    assert misma_obra.es_la_misma_obra(aprobado, vigente) is False


# --- el CLI que invoca el workflow -----------------------------------------------------


def test_el_cli_sale_cero_solo_si_es_la_misma_obra(misma_obra: ModuleType, tmp_path: Path) -> None:
    obra = _comparacion(("src/a.py", "@@ -1 +1 @@\n+x"))
    iguales = (
        _escribir(tmp_path, "a.json", obra),
        _escribir(tmp_path, "b.json", obra),
    )
    distinta = _escribir(tmp_path, "c.json", _comparacion(("src/a.py", "@@ -1 +1 @@\n+z")))

    assert misma_obra.main([str(iguales[0]), str(iguales[1])]) == 0
    assert misma_obra.main([str(iguales[0]), str(distinta)]) == 1


# --- el cableado: que el workflow lo llame de verdad ------------------------------------

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "advance-sirius-after-quality.yml"


def _lineas_de_codigo(texto: str) -> list[str]:
    """Solo líneas que no son comentarios: la familia vacua ha mordido cuatro
    veces en este repositorio por contar patrones dentro de comentarios."""
    return [linea for linea in texto.splitlines() if not linea.strip().startswith("#")]


def test_el_workflow_invoca_la_decision_exactamente_una_vez() -> None:
    codigo = "\n".join(_lineas_de_codigo(WORKFLOW.read_text(encoding="utf-8")))
    invocaciones = codigo.count("python3 scripts/automation/sirius_misma_obra.py")
    assert invocaciones == 1, (
        f"esperaba exactamente 1 invocación de la decisión en {WORKFLOW.name}, hay {invocaciones}"
    )


def test_la_decision_se_consulta_dentro_de_la_guarda_de_adr_142() -> None:
    """No puede consultarse en cualquier rama: solo DENTRO de la guarda que ya
    protege una aprobación registrada -origen `ready-for-merge` y Quality en
    verde-. Fuera de ella, saltarse la reposición de `review-requested` sería
    aprobar trabajo sin revisar.

    Comprueba ANIDAMIENTO, no posición en el fichero: la primera versión de esta
    prueba solo miraba que la invocación apareciera DESPUÉS de la guarda, y una
    mutación que la sacaba del bloque pasaba en verde. Es la familia vacua, que
    en este repositorio ha mordido cinco veces.
    """
    lineas = WORKFLOW.read_text(encoding="utf-8").splitlines()
    apertura = next(
        i
        for i, linea in enumerate(lineas)
        if 'origen_de[$issue_number]}" = "sirius:ready-for-merge"' in linea
        and linea.lstrip().startswith("if [")
    )
    # El `fi` a la sangría de la guarda (diez espacios) es el que la cierra; los
    # de dentro llevan más.
    cierre = next(
        i for i, linea in enumerate(lineas[apertura + 1 :], apertura + 1) if linea == "          fi"
    )
    invocacion = next(
        i
        for i, linea in enumerate(lineas)
        if "python3 scripts/automation/sirius_misma_obra.py" in linea
        and not linea.strip().startswith("#")
    )
    assert apertura < invocacion < cierre, (
        f"la decisión (línea {invocacion + 1}) tiene que quedar DENTRO de la guarda de "
        f"ADR-142 (líneas {apertura + 1}-{cierre + 1})"
    )


def test_la_base_de_la_pr_se_lee_de_la_propia_pr() -> None:
    """El diff propio se mide contra la base de mezcla de ESA PR. Clavar `main`
    a mano haría que una PR con otra base midiera contra algo que no es suya."""
    codigo = "\n".join(_lineas_de_codigo(WORKFLOW.read_text(encoding="utf-8")))
    assert "base: .base.ref" in codigo, (
        "la base tiene que salir de la lectura de la PR, no de una constante"
    )
