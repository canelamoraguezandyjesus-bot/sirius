"""`sirius_comment_upsert`: mantener UN comentario al día sin acabar con dos (ADR-175).

El tablero de una incidencia es un comentario que se reescribe. La operación no
existía en esta biblioteca: `sirius_comment_once` publica un HECHO, que ocurre
una vez y no se vuelve a tocar. Un ESTADO cambia, y eso es otra cosa.

Lo que esta batería fija es lo único que puede salir realmente mal: que la
incidencia acabe con una colección de tableros en vez de con uno.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BIBLIOTECA = RAIZ / "scripts" / "automation" / "sirius_issue.sh"
MARCADOR = "<!-- sirius-tablero -->"


def _bash_sirve() -> bool:
    return shutil.which("bash") is not None and shutil.which("jq") is not None


pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or not _bash_sirve(),
    reason="hace falta bash y jq para ejercitar la biblioteca de shell",
)

# El `gh` falso aplica el `--jq` REAL del llamador sobre el JSON de
# comentarios: un filtro de confianza equivocado no puede pasar en verde aquí.
_GH_FALSO = r"""#!/usr/bin/env bash
D="$GH_MOCK_DIR"
echo "gh $*" >> "$D/calls.log"
sub="$1"; shift || true
case "$sub" in
  api)
    if [ "${MOCK_API_FALLA:-0}" = "1" ]; then echo "api caida" >&2; exit 1; fi
    metodo=""; prev=""; filtro=""; entrada=""
    for a in "$@"; do
      [ "$prev" = "--method" ] && metodo="$a"
      [ "$prev" = "--jq" ] && filtro="$a"
      [ "$prev" = "--input" ] && entrada="$a"
      prev="$a"
    done
    if [ "$metodo" = "PATCH" ]; then
      for a in "$@"; do
        case "$a" in repos/*/issues/comments/*) echo "${a##*/}" > "$D/editado.txt";; esac
      done
      cp "$entrada" "$D/cuerpo_editado.json"
      echo '{}'
      exit 0
    fi
    jq -r "$filtro" < "$D/comentarios.json"
    exit 0
    ;;
  issue)
    accion="$1"; shift || true
    if [ "$accion" = "comment" ]; then
      prev=""
      for a in "$@"; do
        [ "$prev" = "--body-file" ] && cp "$a" "$D/cuerpo_creado.txt"
        prev="$a"
      done
      echo "creado" >> "$D/creados.txt"
      exit 0
    fi
    exit 0
    ;;
esac
exit 0
"""

_GUION = """
set -u
source "{biblioteca}"
sirius_comment_upsert owner/repo 508 '{marcador}' "$1"
"""


def _entorno(tmp_path: Path, comentarios: list[dict[str, object]]) -> dict[str, str]:
    md = tmp_path / "mock"
    md.mkdir()
    (md / "comentarios.json").write_text(json.dumps(comentarios), encoding="utf-8")
    gh = md / "gh"
    gh.write_text(_GH_FALSO, encoding="utf-8")
    gh.chmod(0o755)
    entorno = dict(os.environ)
    entorno["PATH"] = f"{md}{os.pathsep}{entorno['PATH']}"
    entorno["GH_MOCK_DIR"] = str(md)
    entorno["SIRIUS_RETRY_BASE_DELAY"] = "0"
    return entorno


def _correr(
    tmp_path: Path, entorno: dict[str, str], cuerpo: str
) -> subprocess.CompletedProcess[str]:
    fichero = tmp_path / "tablero.md"
    fichero.write_text(cuerpo, encoding="utf-8")
    guion = tmp_path / "guion.sh"
    guion.write_text(
        _GUION.format(biblioteca=BIBLIOTECA.as_posix(), marcador=MARCADOR), encoding="utf-8"
    )
    return subprocess.run(
        ["bash", str(guion), str(fichero)],
        capture_output=True,
        text=True,
        env=entorno,
        check=False,
    )


def _mock(entorno: dict[str, str]) -> Path:
    return Path(entorno["GH_MOCK_DIR"])


_CUERPO = f"{MARCADOR}\n\n## Tablero\n\nEstado: «trabajando»\n"


def test_sin_tablero_previo_lo_crea(tmp_path: Path) -> None:
    entorno = _entorno(
        tmp_path, [{"id": 1, "user": {"login": "github-actions[bot]"}, "body": "hola"}]
    )
    resultado = _correr(tmp_path, entorno, _CUERPO)
    assert resultado.returncode == 0, resultado.stderr
    assert (_mock(entorno) / "creados.txt").exists()
    assert not (_mock(entorno) / "editado.txt").exists()


def test_con_tablero_previo_lo_edita_y_no_crea_otro(tmp_path: Path) -> None:
    entorno = _entorno(
        tmp_path,
        [
            {"id": 1, "user": {"login": "github-actions[bot]"}, "body": "hola"},
            {"id": 77, "user": {"login": "github-actions[bot]"}, "body": f"{MARCADOR}\nviejo"},
        ],
    )
    resultado = _correr(tmp_path, entorno, _CUERPO)
    assert resultado.returncode == 0, resultado.stderr
    assert (_mock(entorno) / "editado.txt").read_text(encoding="utf-8").strip() == "77"
    assert not (_mock(entorno) / "creados.txt").exists()


def test_con_dos_tableros_edita_siempre_el_mas_antiguo(tmp_path: Path) -> None:
    """Si alguna vez llegaran a existir dos, todas las pasadas convergen en uno.

    Editar «el último» haría que un duplicado nacido de una respuesta perdida
    se quedara vivo y alternando; editar el primero lo deja quieto.
    """
    entorno = _entorno(
        tmp_path,
        [
            {"id": 10, "user": {"login": "github-actions[bot]"}, "body": f"{MARCADOR}\nprimero"},
            {"id": 20, "user": {"login": "github-actions[bot]"}, "body": f"{MARCADOR}\nsegundo"},
        ],
    )
    resultado = _correr(tmp_path, entorno, _CUERPO)
    assert resultado.returncode == 0, resultado.stderr
    assert (_mock(entorno) / "editado.txt").read_text(encoding="utf-8").strip() == "10"


def test_un_marcador_sembrado_por_un_tercero_no_se_reescribe(tmp_path: Path) -> None:
    """La frontera de confianza: el motor no edita el comentario de un extraño."""
    entorno = _entorno(
        tmp_path,
        [{"id": 99, "user": {"login": "un-tercero"}, "body": f"{MARCADOR}\nsoy un extraño"}],
    )
    resultado = _correr(tmp_path, entorno, _CUERPO)
    assert resultado.returncode == 0, resultado.stderr
    assert not (_mock(entorno) / "editado.txt").exists()
    assert (_mock(entorno) / "creados.txt").exists()


def test_si_el_historial_no_se_puede_leer_no_publica_nada(tmp_path: Path) -> None:
    """Crear a ciegas sería un tablero de más por cada mal minuto de la API."""
    entorno = _entorno(tmp_path, [])
    entorno["MOCK_API_FALLA"] = "1"
    resultado = _correr(tmp_path, entorno, _CUERPO)
    assert resultado.returncode != 0
    assert not (_mock(entorno) / "creados.txt").exists()
    assert not (_mock(entorno) / "editado.txt").exists()
    assert "historial ilegible" in resultado.stderr


def test_un_cuerpo_vacio_no_publica_nada(tmp_path: Path) -> None:
    entorno = _entorno(tmp_path, [])
    resultado = _correr(tmp_path, entorno, "")
    assert resultado.returncode != 0
    assert not (_mock(entorno) / "creados.txt").exists()


def test_el_cuerpo_llega_intacto_aunque_lleve_comillas_acentos_y_saltos(tmp_path: Path) -> None:
    """Un tablero lleva todo eso; armar el JSON a mano lo habría roto."""
    dificil = f'{MARCADOR}\n\n## «Tablero»\n\nDijo: "así" y \\ también\n- línea\n'
    entorno = _entorno(
        tmp_path,
        [{"id": 5, "user": {"login": "github-actions[bot]"}, "body": f"{MARCADOR}\nviejo"}],
    )
    resultado = _correr(tmp_path, entorno, dificil)
    assert resultado.returncode == 0, resultado.stderr
    enviado = json.loads((_mock(entorno) / "cuerpo_editado.json").read_text(encoding="utf-8"))
    assert enviado["body"] == dificil


def test_una_nota_del_propietario_que_cita_el_marcador_no_se_reescribe(tmp_path: Path) -> None:
    """El hallazgo de la revisión del 12-09-2026, cerrado y con su prueba.

    El propietario es autor DE CONFIANZA: el filtro ancho lo incluía, así que
    bastaba con que una nota suya MENCIONARA el marcador para que el tablero se
    publicara encima y la borrara. Reproducido antes de arreglarlo: el
    publicador editó su comentario 4242 en vez de crear el suyo.
    """
    # El marcador va AL PRINCIPIO de su nota, que es el caso que de verdad
    # ejercita el filtro de autor: pegar el tablero para comentarlo encima es
    # lo más natural del mundo. Con el marcador en medio lo rechazaría la otra
    # condición y esta prueba no probaría nada -la mutación lo enseñó-.
    nota = MARCADOR + "\n\nEste tablero está mal, el estado no es ese. No lo pises."
    entorno = _entorno(
        tmp_path,
        [{"id": 4242, "author_association": "OWNER", "user": {"login": "andy"}, "body": nota}],
    )
    resultado = _correr(tmp_path, entorno, _CUERPO)
    assert resultado.returncode == 0, resultado.stderr
    assert not (_mock(entorno) / "editado.txt").exists(), (
        "se reescribió un comentario del propietario"
    )
    assert (_mock(entorno) / "creados.txt").exists()


def test_un_comentario_del_bot_que_solo_menciona_el_marcador_no_es_el_tablero(
    tmp_path: Path,
) -> None:
    """La segunda condición: el marcador ABRE el tablero, no aparece en él.

    Sin esto, cualquier aviso del propio bot que citara el marcador -una
    explicación, un ejemplo- se convertiría en el tablero y sería sustituido.
    """
    entorno = _entorno(
        tmp_path,
        [
            {
                "id": 31,
                "user": {"login": "github-actions[bot]"},
                "body": "Aviso: el tablero se reconoce por " + MARCADOR + " en su cabecera.",
            }
        ],
    )
    resultado = _correr(tmp_path, entorno, _CUERPO)
    assert resultado.returncode == 0, resultado.stderr
    assert not (_mock(entorno) / "editado.txt").exists()
    assert (_mock(entorno) / "creados.txt").exists()
