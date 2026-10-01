"""La cola: una rama entra a revisión solo si `main` ya está dentro de ella.

Lo que estas pruebas fijan no es «el módulo devuelve lo que devuelve», sino la
propiedad que costó una noche en rojo: si la punta de `main` no está en la rama,
la combinación que aterrizaría no la ha probado nadie, y la rama espera.

Cada aserción de abajo se ha visto FALLAR contra una versión rota a propósito;
las mutaciones están en el ADR. Una guarda que nunca se vio caer no prueba nada
(ADR-172).
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
MODULO = RAIZ / "scripts" / "automation" / "sirius_cola.py"


def _cargar() -> ModuleType:
    """Se carga por ruta, como lo hará el runner: sin instalar nada."""
    spec = importlib.util.spec_from_file_location("sirius_cola", MODULO)
    assert spec is not None and spec.loader is not None, f"no se pudo cargar {MODULO}"
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


cola = _cargar()


def _comparacion(tmp_path: Path, cuerpo: object) -> Path:
    """Cada comparación en su propio fichero.

    La primera versión de este ayudante escribía siempre en `compare.json`, así
    que dos comparaciones dentro de la misma prueba se pisaban y la segunda
    decidía por las dos. Lo cazó `test_el_codigo_de_salida_distingue_pasar_de_esperar`,
    que es la única que usa dos a la vez.
    """
    ruta = tmp_path / f"compare-{abs(hash(json.dumps(cuerpo, sort_keys=True)))}.json"
    ruta.write_text(json.dumps(cuerpo), encoding="utf-8")
    return ruta


# --- Lo que deja pasar -------------------------------------------------------


@pytest.mark.parametrize("estado", ["identical", "ahead"])
def test_con_la_punta_de_main_dentro_la_rama_entra(tmp_path: Path, estado: str) -> None:
    """Los dos únicos estados que significan «main ya está aquí».

    `identical` es la rama que no ha divergido; `ahead`, la que tiene trabajo
    propio encima de esa punta. En los dos casos lo que se revise es lo que
    aterrizará.
    """
    veredicto = cola.puede_entrar_a_revision(_comparacion(tmp_path, {"status": estado}))
    assert veredicto.al_dia, f"con status {estado!r} la rama tiene la punta de main"


# --- Lo que hace esperar -----------------------------------------------------


@pytest.mark.parametrize("estado", ["behind", "diverged"])
def test_sin_la_punta_de_main_la_rama_espera(tmp_path: Path, estado: str) -> None:
    """El caso que dejó `main` en rojo: #611 entró sin tener #602."""
    ruta = _comparacion(tmp_path, {"status": estado, "behind_by": 1})
    assert not cola.puede_entrar_a_revision(ruta).al_dia, (
        f"con status {estado!r} hay commits en main que la rama no tiene: "
        "revisar aquí aprobaría una combinación que nadie ha probado"
    )


def test_la_espera_dice_cuanto_le_falta(tmp_path: Path) -> None:
    """Una espera que no se cuenta no se distingue de un atasco (ADR-183)."""
    ruta = _comparacion(tmp_path, {"status": "behind", "behind_by": 3})
    motivo = cola.puede_entrar_a_revision(ruta).motivo
    assert "3" in motivo and "detrás" in motivo, (
        f"el motivo tiene que decir cuánto le falta; salió {motivo!r}"
    )


def test_un_solo_commit_por_detras_se_dice_en_singular(tmp_path: Path) -> None:
    """Un mensaje que dice «1 commits» delata que nadie lo leyó nunca."""
    ruta = _comparacion(tmp_path, {"status": "behind", "behind_by": 1})
    motivo = cola.puede_entrar_a_revision(ruta).motivo
    assert "1 commit " in motivo and "commits" not in motivo, (
        f"con uno solo va en singular; salió {motivo!r}"
    )


# --- Fail-closed: todo lo que impida AFIRMAR que está al día ------------------


def test_sin_fichero_la_rama_espera(tmp_path: Path) -> None:
    assert not cola.puede_entrar_a_revision(tmp_path / "no-existe.json").al_dia


def test_con_json_roto_la_rama_espera(tmp_path: Path) -> None:
    ruta = tmp_path / "compare.json"
    ruta.write_text("{ esto no es json", encoding="utf-8")
    assert not cola.puede_entrar_a_revision(ruta).al_dia


@pytest.mark.parametrize("cuerpo", [[], "ahead", 7, None])
def test_si_la_comparacion_no_es_un_objeto_la_rama_espera(tmp_path: Path, cuerpo: object) -> None:
    """Una lista o una cadena no traen `status`; afirmar desde ahí sería inventar."""
    assert not cola.puede_entrar_a_revision(_comparacion(tmp_path, cuerpo)).al_dia


def test_sin_status_la_rama_espera(tmp_path: Path) -> None:
    ruta = _comparacion(tmp_path, {"behind_by": 0, "ahead_by": 2})
    assert not cola.puede_entrar_a_revision(ruta).al_dia


def test_con_un_status_desconocido_la_rama_espera(tmp_path: Path) -> None:
    """Si GitHub añadiera un estado nuevo, esperar es el error barato.

    Esperar se recupera solo: la condición se vuelve a evaluar. Dejar pasar de
    más mete en `main` algo que nadie probó, y eso se paga en rojo.
    """
    ruta = _comparacion(tmp_path, {"status": "estado-que-hoy-no-existe"})
    assert not cola.puede_entrar_a_revision(ruta).al_dia


@pytest.mark.parametrize("valor", [None, "1", 1.5, True])
def test_un_status_que_no_es_texto_hace_esperar(tmp_path: Path, valor: object) -> None:
    """`True` entra a propósito: en Python es `int`, y un `in` descuidado lo colaría."""
    assert not cola.puede_entrar_a_revision(_comparacion(tmp_path, {"status": valor})).al_dia


def test_una_comparacion_rota_no_afirma_que_la_rama_va_por_detras(tmp_path: Path) -> None:
    """Esperar por lo que no se pudo leer NO es lo mismo que ir por detrás.

    Con `status` ilegible pero `behind_by` presente, decir «vas 2 commits por
    detrás» es afirmar algo que el dato no sostiene, y manda a quien lo lea a
    ponerse al día de algo que quizá ya tiene. El motivo tiene que decir que no
    se pudo leer.

    Esta prueba existe porque la mutación M3 -quitar la comprobación de que
    `status` es texto- sobrevivió a la primera pasada: la garantía estaba en la
    prosa del módulo y en ninguna aserción.
    """
    ruta = _comparacion(tmp_path, {"status": None, "behind_by": 2})
    veredicto = cola.puede_entrar_a_revision(ruta)
    assert not veredicto.al_dia
    assert "detrás" not in veredicto.motivo, (
        f"no se puede afirmar que va por detrás con `status` ilegible; salió {veredicto.motivo!r}"
    )
    assert "status" in veredicto.motivo


# --- El código de salida ES la respuesta -------------------------------------


def test_el_codigo_de_salida_distingue_pasar_de_esperar(tmp_path: Path) -> None:
    """El workflow se ramifica por el código, no por el texto.

    Si se ramificara por el mensaje, cambiarle una palabra convertiría un
    «espera» en un «pasa» sin que ninguna prueba se enterara.
    """
    al_dia = _comparacion(tmp_path, {"status": "ahead"})
    detras = _comparacion(tmp_path, {"status": "behind", "behind_by": 2})
    assert cola.main([str(al_dia)]) == 0
    assert cola.main([str(detras)]) != 0


def test_el_motivo_sale_por_la_salida_estandar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Quien llama tiene que poder escribir la espera en la incidencia."""
    cola.main([str(_comparacion(tmp_path, {"status": "behind", "behind_by": 2}))])
    assert "detrás" in capsys.readouterr().out


def test_el_modulo_no_importa_nada_de_fuera_de_la_estandar() -> None:
    """Corre con el `python3` a secas del runner, sin `uv` ni dependencias."""
    fuente = MODULO.read_text(encoding="utf-8")
    importados = {
        linea.split()[1].split(".")[0]
        for linea in fuente.splitlines()
        if linea.startswith(("import ", "from ")) and "__future__" not in linea
    }
    assert importados <= set(sys.stdlib_module_names), (
        f"solo biblioteca estándar; sobran {importados - set(sys.stdlib_module_names)}"
    )


# --- La mitad que faltó las ocho veces: alguien que la llame -----------------

AVANCE = RAIZ / ".github" / "workflows" / "advance-sirius-after-quality.yml"


def _avance_sin_comentarios() -> str:
    """El workflow sin sus líneas de comentario.

    Buscar el nombre del módulo en el fichero entero no vale: la cabecera de
    este workflow y sus comentarios explican la historia, así que una mutación
    que quitara la llamada seguiría encontrando el nombre escrito. Es la misma
    lección que `_codigo_sin_comentarios` en test_reanudar_una_parada.py: una
    prueba que se conforma con que algo se MENCIONE certifica documentación.
    """
    return "\n".join(
        linea
        for linea in AVANCE.read_text(encoding="utf-8").splitlines()
        if not linea.lstrip().startswith("#")
    )


def test_el_avance_llama_a_la_cola() -> None:
    """ADR-191 construyó la condición y dejó escrito que NO la cableaba.

    Ocho veces ha pasado ya en esta casa que una pieza correcta se quedara sin
    llamante, con sus pruebas en verde vigilando código que no se ejecutaba.
    `tests/automation/test_piezas_con_llamante.py` cierra esa clase para los
    módulos de `src/sirius_engine`; `scripts/automation/` queda fuera de su
    inventario, y ahí es donde vive esta pieza. Así que aquí va su llamante.
    """
    assert "sirius_cola.py" in _avance_sin_comentarios(), (
        "`sirius_cola.py` decide si una rama puede entrar a revisión y el "
        "workflow que repone `sirius:review-requested` no lo llama: la "
        "condición existiría sin gobernar nada"
    )


def test_la_cola_se_consulta_antes_de_reponer_la_revision() -> None:
    """Preguntar después de haber repuesto la etiqueta no es preguntar.

    Sin esta, una mutación que dejara la llamada DESPUÉS de la transición
    pasaría la prueba de arriba en verde y la rama entraría a revisión igual.
    """
    texto = _avance_sin_comentarios()
    consulta = texto.find("sirius_cola.py")
    repone = texto.find('"sirius:review-requested"')
    assert consulta != -1, "no se encontró la llamada a la cola"
    assert repone != -1, "no se encontró la transición que repone la revisión"
    assert consulta < repone, (
        "la cola se consulta DESPUÉS de reponer `sirius:review-requested`: "
        "la rama ya habría entrado a revisión cuando se pregunta si podía"
    )


def test_la_puesta_al_dia_no_empuja_con_el_token_del_workflow() -> None:
    """Un push con `GITHUB_TOKEN` no dispara workflows (ADR-183).

    Si la rama se pusiera al día con él, Quality no volvería a correr y la rama
    quedaría esperando otra vez: el mismo atasco con otra cara. El PAT va en el
    `git push` fijo, construido en el propio paso, y en ningún otro sitio.
    """
    flujo = yaml.safe_load(AVANCE.read_text(encoding="utf-8"))
    pasos = [
        paso
        for trabajo in flujo["jobs"].values()
        for paso in trabajo.get("steps", [])
        if str(paso.get("uses", "")).startswith("actions/checkout")
    ]
    con_pat = [
        paso for paso in pasos if "SIRIUS_BOT_TOKEN" in str(paso.get("with", {}).get("token", ""))
    ]
    assert con_pat, "ningún checkout de este workflow trae la rama con el PAT"
    texto = _avance_sin_comentarios()
    assert "x-access-token:${SIRIUS_BOT_TOKEN}@github.com" in texto, (
        "el push de la puesta al día tiene que ir con el PAT: con `GITHUB_TOKEN` "
        "Quality no volvería a correr (ADR-183)"
    )
    assert "--force" not in texto, (
        "la puesta al día nunca reescribe la historia de una rama que no es suya"
    )


def test_el_codigo_de_la_rama_corre_sin_el_pat_al_alcance() -> None:
    """ADR-220, ronda 1 de Codex en la PR #667: desde ese checkout se ejecuta código
    de la rama (`uv sync`, el generador), que no ha pasado necesariamente la
    revisión dual. Ni en `.git/config` ni en su entorno puede estar el PAT."""
    flujo = yaml.safe_load(AVANCE.read_text(encoding="utf-8"))
    checkouts_de_rama = [
        paso
        for trabajo in flujo["jobs"].values()
        for paso in trabajo.get("steps", [])
        if str(paso.get("uses", "")).startswith("actions/checkout")
        and "SIRIUS_BOT_TOKEN" in str(paso.get("with", {}).get("token", ""))
    ]
    for paso in checkouts_de_rama:
        assert paso.get("with", {}).get("persist-credentials") is False, (
            "el checkout de la rama no puede persistir el PAT: el código de la rama "
            "lo leería de `.git/config`"
        )
    texto = _avance_sin_comentarios()
    assert "env -u SIRIUS_BOT_TOKEN -u GH_TOKEN uv run sirius-memoria conocimiento" in texto, (
        "el generador se ejecuta sin el PAT en su entorno"
    )
    for trabajo in flujo["jobs"].values():
        for paso in trabajo.get("steps", []):
            entorno = paso.get("env") or {}
            assert "SIRIUS_BOT_TOKEN" not in str(entorno.get("GH_TOKEN", "")), (
                f"el paso {paso.get('name')!r} exporta el PAT como GH_TOKEN a todo el paso: "
                "cualquier `gh` o `uv run` de la rama lo heredaría"
            )
    paso_fusion = _bash_del_paso(PASO_DE_FUSION)
    assert 'git push "$REMOTO_DE_EMPUJE"' in paso_fusion and "git push origin" not in paso_fusion, (
        "el push va por la URL construida con el PAT en el propio paso, no por `origin`"
    )
    assert 'GH_TOKEN="$SIRIUS_BOT_TOKEN" gh issue comment' in paso_fusion


# --- La puesta al día regenera las vistas generadas (ADR-220) -----------------
#
# Estas pruebas ejecutan el bash del paso «Fusionar la base y empujar» DE VERDAD,
# sobre un repositorio de prueba con su remoto y con dobles de `uv` y `gh` en el
# PATH. Una prueba que solo mirara que el texto del workflow «menciona»
# `sirius-memoria` certificaría documentación (la lección de `_avance_sin_comentarios`).

PASO_DE_FUSION = "Fusionar la base y empujar"
VISTAS = ("MEMORIA.md", "docs/audits/INDICE.md")
CONDICION_DE_PUESTA_AL_DIA = "steps.avanzar.outputs.ponerse_al_dia == 'true'"

_DOBLE_UV = """#!/bin/bash
# Doble de `uv run sirius-memoria conocimiento`: escribe las vistas A PARTIR DEL
# ÁRBOL, como el generador real, para que «regenerar» cambie el contenido cuando
# el árbol cambió y no cuando no.
set -u
printf '%s\n' "$*" >>"$DOBLES_LOG"
if [ -n "${SIRIUS_BOT_TOKEN:-}" ] || [ -n "${GH_TOKEN:-}" ]; then
  printf '%s\n' "EL GENERADOR VIO UN TOKEN" >>"$DOBLES_LOG"
fi
if [ "$1 $2 $3" != "run sirius-memoria conocimiento" ]; then
  echo "doble de uv: orden inesperada: $*" >&2
  exit 2
fi
ficheros="$(git ls-files | grep -v -e '^MEMORIA.md$' -e '^docs/audits/INDICE.md$' \
  | sort -u | tr '\n' ' ')"
printf 'vista de: %s\n' "$ficheros" >MEMORIA.md
mkdir -p docs/audits
printf 'indice de: %s\n' "$ficheros" >docs/audits/INDICE.md
"""

_DOBLE_GH = """#!/bin/bash
# Doble de `gh`: apunta la orden y el cuerpo que se publicaría.
set -u
printf 'gh %s\n' "$*" >>"$DOBLES_LOG"
while [ $# -gt 0 ]; do
  if [ "$1" = "--body-file" ]; then cat "$2" >>"$DOBLES_LOG"; shift; fi
  shift
done
"""


def _bash_del_paso(nombre: str) -> str:
    flujo = yaml.safe_load(AVANCE.read_text(encoding="utf-8"))
    for trabajo in flujo["jobs"].values():
        for paso in trabajo.get("steps", []):
            if paso.get("name") == nombre:
                return str(paso["run"])
    raise AssertionError(f"no hay un paso llamado {nombre!r} en {AVANCE.name}")


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _confirmar(cwd: Path, mensaje: str, **ficheros: str) -> None:
    for ruta, texto in ficheros.items():
        destino = cwd / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        _git(cwd, "add", ruta)
    _git(cwd, "commit", "-q", "-m", mensaje)


class _Escenario:
    """Un remoto, `main` y una rama `rama` que espera, y el clon del runner."""

    def __init__(self, tmp_path: Path) -> None:
        self.origen = tmp_path / "origen.git"
        _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(self.origen))
        self.taller = tmp_path / "taller"
        _git(tmp_path, "clone", "-q", str(self.origen), str(self.taller))
        _git(self.taller, "config", "user.name", "prueba")
        _git(self.taller, "config", "user.email", "prueba@example.invalid")
        _git(self.taller, "checkout", "-q", "-b", "main")
        _confirmar(
            self.taller,
            "base",
            **{"otro.txt": "base\n", "MEMORIA.md": "vista base\n", "docs/audits/INDICE.md": "x\n"},
        )
        _git(self.taller, "push", "-q", "origin", "main")
        _git(self.taller, "checkout", "-q", "-b", "rama")
        dobles = tmp_path / "dobles"
        dobles.mkdir()
        for nombre, texto in (("uv", _DOBLE_UV), ("gh", _DOBLE_GH)):
            doble = dobles / nombre
            doble.write_text(texto, encoding="utf-8")
            doble.chmod(doble.stat().st_mode | stat.S_IXUSR)
        self.dobles = dobles
        self.registro = tmp_path / "dobles.log"
        self.tmp_path = tmp_path

    def en_la_rama(self, mensaje: str, **ficheros: str) -> None:
        _git(self.taller, "checkout", "-q", "rama")
        _confirmar(self.taller, mensaje, **ficheros)
        _git(self.taller, "push", "-q", "origin", "rama")

    def en_main(self, mensaje: str, **ficheros: str) -> None:
        _git(self.taller, "checkout", "-q", "main")
        _confirmar(self.taller, mensaje, **ficheros)
        _git(self.taller, "push", "-q", "origin", "main")

    def punta(self, rama: str) -> str:
        return _git(self.origen, "rev-parse", rama)

    def ejecutar_el_paso(self) -> subprocess.CompletedProcess[str]:
        clon = self.tmp_path / "clon"
        _git(self.tmp_path, "clone", "-q", str(self.origen), str(clon))
        _git(clon, "checkout", "-q", "rama")
        # Como en el runner sin credenciales persistidas: por `origin` se puede
        # traer, pero NO empujar. El unico camino de vuelta es la URL con el PAT
        # (`SIRIUS_PUSH_URL` en las pruebas).
        _git(clon, "remote", "set-url", "--push", "origin", str(self.tmp_path / "no-se-empuja.git"))
        guion = self.tmp_path / "paso.sh"
        guion.write_text(_bash_del_paso(PASO_DE_FUSION), encoding="utf-8")
        entorno = {
            **os.environ,
            "PATH": f"{self.dobles}{os.pathsep}{os.environ['PATH']}",
            "DOBLES_LOG": str(self.registro),
            "SIRIUS_BOT_TOKEN": "pat-de-prueba",
            "SIRIUS_PUSH_URL": str(self.origen),
            "GH_REPO": "propietario/repo",
            "RAMA": "rama",
            "BASE": "main",
            "ISSUE": "7",
        }
        self.clon = clon
        return subprocess.run(
            ["bash", "--noprofile", "--norc", str(guion)],
            cwd=clon,
            env=entorno,
            capture_output=True,
            text=True,
            check=False,
        )

    def lo_publicado(self) -> str:
        return self.registro.read_text(encoding="utf-8") if self.registro.exists() else ""


def test_la_puesta_al_dia_regenera_las_vistas_y_las_confirma_antes_de_empujar(
    tmp_path: Path,
) -> None:
    """Fusión limpia, vista vieja: sin esto Quality caía por la memoria (#653, 25 min)."""
    escenario = _Escenario(tmp_path)
    escenario.en_la_rama("trabajo propio", **{"otro.txt": "rama\n"})
    escenario.en_main("main avanza", **{"docs/nuevo.md": "# Nuevo\n", "MEMORIA.md": "vista main\n"})
    resultado = escenario.ejecutar_el_paso()
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    asuntos = _git(escenario.origen, "log", "--format=%s", "-2", "rama").splitlines()
    assert asuntos[0] == "Regenera las vistas de la memoria tras traer main (ADR-220)", asuntos
    assert asuntos[1].startswith("Trae main a rama"), asuntos
    vista = _git(escenario.origen, "show", "rama:MEMORIA.md")
    assert vista.startswith("vista de:") and "docs/nuevo.md" in vista, (
        "la vista empujada tiene que ser la regenerada del árbol combinado, no la de `main`"
    )
    assert "sirius-cola:rama:conflicto" not in escenario.lo_publicado()
    assert "EL GENERADOR VIO UN TOKEN" not in escenario.lo_publicado(), (
        "el código de la rama no puede ver el PAT (ADR-220)"
    )


def test_un_conflicto_solo_en_las_vistas_generadas_se_resuelve_regenerando(
    tmp_path: Path,
) -> None:
    """Las dos partes regeneraron la vista: no hay nada que una persona deba decidir."""
    escenario = _Escenario(tmp_path)
    escenario.en_la_rama("trabajo propio", **{"MEMORIA.md": "vista rama\n"})
    escenario.en_main("main avanza", **{"docs/nuevo.md": "# Nuevo\n", "MEMORIA.md": "vista main\n"})
    antes = escenario.punta("rama")
    resultado = escenario.ejecutar_el_paso()
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert escenario.punta("rama") != antes, "la rama tenía que avanzar con la fusión"
    padres = _git(escenario.origen, "log", "--format=%P", "-1", "rama").split()
    assert len(padres) == 2, "la punta tiene que ser la fusión de la rama con main"
    assert _git(escenario.origen, "log", "--format=%s", "-1", "rama").startswith("Trae main a rama")
    vista = _git(escenario.origen, "show", "rama:MEMORIA.md")
    assert vista.startswith("vista de:") and "<<<<<<<" not in vista
    assert "sirius-cola:rama:conflicto" not in escenario.lo_publicado(), (
        "un conflicto solo en vistas generadas no es cosa de una persona"
    )


def test_un_conflicto_fuera_de_las_vistas_sigue_siendo_cosa_de_una_persona(
    tmp_path: Path,
) -> None:
    """Exactamente como antes: se deshace, la rama queda como estaba y se avisa (ADR-200)."""
    escenario = _Escenario(tmp_path)
    escenario.en_la_rama("trabajo propio", **{"otro.txt": "rama\n", "MEMORIA.md": "vista rama\n"})
    escenario.en_main("main avanza", **{"otro.txt": "main\n", "MEMORIA.md": "vista main\n"})
    antes = escenario.punta("rama")
    resultado = escenario.ejecutar_el_paso()
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert escenario.punta("rama") == antes, "la rama no puede moverse cuando el conflicto es real"
    assert not (escenario.clon / ".git" / "MERGE_HEAD").exists(), "la fusión tiene que deshacerse"
    publicado = escenario.lo_publicado()
    assert "sirius-cola:rama:conflicto" in publicado and "gh issue comment 7" in publicado
    assert "run sirius-memoria conocimiento" not in publicado, (
        "con un conflicto fuera de las vistas el paso no toca el árbol: ni regenera"
    )
    assert "<<<<<<<" not in _git(escenario.clon, "show", "HEAD:otro.txt")


def test_la_puesta_al_dia_tiene_con_que_regenerar() -> None:
    """Sin `uv` en el job, `sirius-memoria` no existe y el paso fallaría siempre."""
    flujo = yaml.safe_load(AVANCE.read_text(encoding="utf-8"))
    pasos = [paso for trabajo in flujo["jobs"].values() for paso in trabajo.get("steps", [])]
    nombres = [str(p.get("name", "")) for p in pasos]
    instala = [p for p in pasos if str(p.get("uses", "")).startswith("astral-sh/setup-uv@")]
    sincroniza = [p for p in pasos if "uv sync" in str(p.get("run", ""))]
    assert instala and sincroniza, "el job tiene que instalar uv y sincronizar el entorno"
    for paso in (*instala, *sincroniza):
        assert str(paso.get("if", "")).strip() == CONDICION_DE_PUESTA_AL_DIA, (
            "la preparación solo corre cuando hay puesta al día, como el paso que la usa"
        )
        assert nombres.index(str(paso["name"])) < nombres.index(PASO_DE_FUSION)
