"""Una skill no se pudre en silencio (ADR-211).

Las skills de `.claude/skills/` son el sitio donde este repositorio guarda lo
que ya costó averiguar dos veces. Tienen el mismo problema que cualquier
documento sin dueño: **nadie las lee para comprobarlas**. La medida está en
esta misma casa —la base de conocimiento de `docs/operations/` se quedó nueve
versiones de contrato por detrás sin que nadie lo notara (ficha PROC-010 de
`docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md`)—, y una skill caducada es
peor que ninguna: se cree.

QUÉ COMPRUEBA, Y NADA MÁS. Lo mecánico, que es lo único comprobable: que el
fichero existe y su cabecera se puede leer, que el nombre coincide con la
carpeta, que la descripción es lo bastante larga para decir CUÁNDO cargarla
—es lo único que se lee para decidir si se carga—, que declara sus límites, y
que toda ruta y todo ADR que cita existen.

QUÉ NO COMPRUEBA, y hay que decirlo para que nadie confunda verde con vigente:
**si el texto está al día**. Una skill puede tener todas sus rutas vivas y la
prosa caducada. Contra eso no hay prueba posible, solo la revisión trimestral
que declara `.claude/skills/disciplina-evidencia/patrones.md`.

Reutiliza el extractor de citas de `tests/automation/test_citas_de_los_adr.py`
en vez de copiarlo: es el que está medido (ADR-052), con su filtro conservador
de raíces del repositorio y su salto de los bloques de código. Copiarlo habría
creado dos criterios que se separan con el tiempo.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / ".claude" / "skills"
REGISTRO_DE_DECISIONES = RAIZ / "docs" / "decisions"

# El suelo de la descripción. No es un número redondo elegido a ojo: la más
# corta de las siete escritas con cuidado el 20-09-2026 tiene 304 caracteres, y
# este suelo queda deliberadamente MUY por debajo. Solo caza el caso que
# importa -una descripción de una línea que repite el título y que por eso no
# carga nadie-, y no obliga a estirar una descripción honesta.
SUELO_DE_LA_DESCRIPCION = 200

# Una sección que empiece por «Qué NO hace» en cualquiera de sus formas
# (`Qué NO hace esto`, `Qué NO hace este método`). Es la sección que impide que
# una skill se use como garantía de algo que no garantiza.
LIMITES = re.compile(r"^#{2,3}\s+Qu[ée] NO hace\b", re.MULTILINE)

CABECERA = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

# Solo tres dígitos: `ADR-NNN` de una plantilla no es una cita.
ADR_CITADO = re.compile(r"\bADR-(\d{3})\b")


def _citas() -> Any:
    """El módulo del extractor de citas, cargado por ruta.

    `tests/` no es un paquete y solo `scripts`, `tests/unit`, `tests/acceptance`
    y `tests/automation/fixtures` están en el `pythonpath`, así que no se puede
    importar una prueba desde otra por su nombre. Es el mismo patrón que usa
    `tests/automation/test_misma_obra.py`.
    """
    ruta = RAIZ / "tests" / "automation" / "test_citas_de_los_adr.py"
    nombre = "citas_de_los_adr_para_las_skills"
    especificacion = importlib.util.spec_from_file_location(nombre, ruta)
    assert especificacion is not None and especificacion.loader is not None
    modulo = importlib.util.module_from_spec(especificacion)
    sys.modules[nombre] = modulo
    especificacion.loader.exec_module(modulo)
    return modulo


CITAS = _citas()


def carpetas_de_skill() -> list[Path]:
    if not CARPETA.is_dir():
        return []
    return sorted(hijo for hijo in CARPETA.iterdir() if hijo.is_dir())


def cabecera_de(texto: str) -> dict[str, Any]:
    """La cabecera YAML de un `SKILL.md`, o `{}` si no la tiene."""
    encontrada = CABECERA.match(texto)
    if encontrada is None:
        return {}
    leida = yaml.safe_load(encontrada.group(1))
    return leida if isinstance(leida, dict) else {}


def rutas_rotas_de(texto: str) -> list[str]:
    """Las rutas del repositorio que cita `texto` y no existen."""
    return [
        cita for cita in CITAS.citas_de(texto) if not (RAIZ / CITAS._ruta_de_fichero(cita)).exists()
    ]


def adrs_rotos_de(texto: str) -> list[str]:
    """Los `ADR-NNN` que cita `texto` y para los que no hay ningún fichero."""
    rotos = []
    for numero in dict.fromkeys(ADR_CITADO.findall(texto)):
        if not list(REGISTRO_DE_DECISIONES.glob(f"ADR-{numero}-*.md")):
            rotos.append(f"ADR-{numero}")
    return rotos


def enlaces_hermanos_rotos_de(documento: Path) -> list[str]:
    """Los enlaces markdown a un fichero de al lado que no resuelven.

    Solo enlaces relativos sin barra ni esquema: `[patrones.md](patrones.md)`.
    Lo demás -URLs, rutas del repositorio- ya lo miran las otras dos.
    """
    texto = documento.read_text(encoding="utf-8")
    rotos = []
    for destino in re.findall(r"\]\(([^)\s]+)\)", texto):
        if "/" in destino or "://" in destino or destino.startswith("#"):
            continue
        if not (documento.parent / destino).exists():
            rotos.append(destino)
    return rotos


# --- Las reglas, una por skill -----------------------------------------------


def test_hay_skills_que_comprobar() -> None:
    """Sin esto, todo lo de abajo pasaría en verde sobre una carpeta vacía.

    Es el patrón «puerta global que se abre sola» del catálogo de
    `.claude/skills/disciplina-evidencia/patrones.md`: una prueba parametrizada
    sobre una lista vacía no ejecuta ni una aserción y nadie se entera.
    """
    assert carpetas_de_skill(), (
        f"no hay ninguna carpeta de skill en {CARPETA.relative_to(RAIZ)}: "
        "o se han borrado todas, o esta prueba ya no mira donde viven"
    )


@pytest.mark.parametrize("skill", carpetas_de_skill(), ids=lambda p: p.name)
def test_cada_skill_tiene_su_fichero(skill: Path) -> None:
    assert (skill / "SKILL.md").is_file(), (
        f"la carpeta {skill.name} no tiene SKILL.md: una skill sin fichero no la carga nadie"
    )


@pytest.mark.parametrize("skill", carpetas_de_skill(), ids=lambda p: p.name)
def test_el_nombre_declarado_es_el_de_la_carpeta(skill: Path) -> None:
    cabecera = cabecera_de((skill / "SKILL.md").read_text(encoding="utf-8"))
    assert cabecera.get("name") == skill.name, (
        f"{skill.name}/SKILL.md declara name={cabecera.get('name')!r}: "
        "el nombre y la carpeta tienen que coincidir o la skill no se resuelve"
    )


@pytest.mark.parametrize("skill", carpetas_de_skill(), ids=lambda p: p.name)
def test_la_descripcion_dice_cuando_cargarla(skill: Path) -> None:
    """La descripción es lo ÚNICO que se lee para decidir si se carga."""
    cabecera = cabecera_de((skill / "SKILL.md").read_text(encoding="utf-8"))
    descripcion = cabecera.get("description")
    assert isinstance(descripcion, str), f"{skill.name}: falta la descripción"
    largo = len(" ".join(descripcion.split()))
    assert largo >= SUELO_DE_LA_DESCRIPCION, (
        f"{skill.name}: la descripción tiene {largo} caracteres y el suelo es "
        f"{SUELO_DE_LA_DESCRIPCION}. Tiene que decir CUÁNDO cargarla, no de qué trata."
    )


@pytest.mark.parametrize("skill", carpetas_de_skill(), ids=lambda p: p.name)
def test_cada_skill_declara_sus_limites(skill: Path) -> None:
    texto = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert LIMITES.search(texto), (
        f"{skill.name}: falta la sección «Qué NO hace». Una skill sin límites "
        "declarados acaba usándose como garantía de algo que no garantiza."
    )


@pytest.mark.parametrize("skill", carpetas_de_skill(), ids=lambda p: p.name)
def test_toda_ruta_citada_por_una_skill_existe(skill: Path) -> None:
    """La comprobación que de verdad caza la podredumbre."""
    rotas = {
        documento.relative_to(RAIZ).as_posix(): rutas
        for documento in sorted(skill.glob("*.md"))
        if (rutas := rutas_rotas_de(documento.read_text(encoding="utf-8")))
    }
    assert rotas == {}, f"rutas citadas que ya no existen: {rotas}"


@pytest.mark.parametrize("skill", carpetas_de_skill(), ids=lambda p: p.name)
def test_todo_adr_citado_por_una_skill_existe(skill: Path) -> None:
    rotos = {
        documento.relative_to(RAIZ).as_posix(): adrs
        for documento in sorted(skill.glob("*.md"))
        if (adrs := adrs_rotos_de(documento.read_text(encoding="utf-8")))
    }
    assert rotos == {}, f"ADR citados que no están en el registro: {rotos}"


@pytest.mark.parametrize("skill", carpetas_de_skill(), ids=lambda p: p.name)
def test_los_enlaces_a_ficheros_de_al_lado_resuelven(skill: Path) -> None:
    rotos = {
        documento.relative_to(RAIZ).as_posix(): enlaces
        for documento in sorted(skill.glob("*.md"))
        if (enlaces := enlaces_hermanos_rotos_de(documento))
    }
    assert rotos == {}, f"enlaces a ficheros de al lado que no existen: {rotos}"


# --- Que los criterios muerdan, aunque el árbol esté limpio -------------------
#
# Cada aserción de arriba pasa hoy porque el árbol está sano. Si el criterio se
# rompiera -una expresión regular que deja de casar, un extractor que devuelve
# la lista vacía-, seguirían pasando exactamente igual. Estas siembran el
# defecto y exigen verlo.


def test_una_cabecera_sin_nombre_se_detecta() -> None:
    assert cabecera_de("---\ndescription: algo\n---\n").get("name") is None


def test_un_fichero_sin_cabecera_no_inventa_una() -> None:
    assert cabecera_de("# Una skill sin cabecera\n") == {}


def test_una_cabecera_que_no_es_un_mapa_no_pasa_por_una() -> None:
    assert cabecera_de("---\n- uno\n- dos\n---\n") == {}


def test_una_ruta_inventada_se_detecta() -> None:
    assert rutas_rotas_de("mira `src/sirius_engine/no_existe_jamas.py`, que no está") == [
        "src/sirius_engine/no_existe_jamas.py"
    ]


def test_una_ruta_viva_no_se_senala() -> None:
    assert rutas_rotas_de("mira `src/sirius_engine/memoria.py`") == []


def test_una_ruta_dentro_de_un_bloque_de_codigo_no_se_mira() -> None:
    texto = "```bash\ncat `src/sirius_engine/no_existe_jamas.py`\n```\n"
    assert rutas_rotas_de(texto) == []


def test_un_adr_inventado_se_detecta() -> None:
    assert adrs_rotos_de("como dice ADR-998, esto no existe") == ["ADR-998"]


def test_un_adr_vivo_no_se_senala() -> None:
    assert adrs_rotos_de("como dice ADR-001, nada se afirma sin comprobación") == []


def test_el_hueco_de_la_plantilla_no_cuenta_como_cita() -> None:
    assert adrs_rotos_de("SUPERADO por ADR-NNN") == []


def test_el_suelo_de_la_descripcion_caza_una_de_una_linea() -> None:
    """La forma exacta del defecto: una descripción que repite el título."""
    assert len("Crea un ADR nuevo.") < SUELO_DE_LA_DESCRIPCION


def test_la_seccion_de_limites_se_reconoce_en_sus_variantes() -> None:
    for encabezado in (
        "## Qué NO hace esto",
        "## Qué NO hace esta skill",
        "### Qué NO hace este método",
    ):
        assert LIMITES.search(f"{encabezado}\n\n- nada\n"), encabezado
    assert LIMITES.search("## Lo que hace\n") is None


def test_un_enlace_hermano_roto_se_detecta(tmp_path: Path) -> None:
    documento = tmp_path / "SKILL.md"
    documento.write_text("ver [patrones.md](patrones.md)\n", encoding="utf-8")
    assert enlaces_hermanos_rotos_de(documento) == ["patrones.md"]
    (tmp_path / "patrones.md").write_text("hola\n", encoding="utf-8")
    assert enlaces_hermanos_rotos_de(documento) == []


# --- Que la skill llegue al repositorio --------------------------------------
#
# El defecto que estrenó esta prueba, el 20-09-2026: `.gitignore` ignoraba
# `.claude/*` y solo volvía a admitir `settings.json` y dos ficheros de
# `commands/`. Las dos skills que existían estaban versionadas porque se
# añadieron con `git add -f`, y un `git add` normal de una skill NUEVA no
# añadía nada y no decía nada. Una skill perfecta que no sale del portátil no
# es una skill.


def test_ninguna_skill_esta_ignorada_por_git() -> None:
    ficheros = sorted(
        documento.relative_to(RAIZ).as_posix()
        for skill in carpetas_de_skill()
        for documento in skill.rglob("*")
        if documento.is_file()
    )
    assert ficheros, "no hay ni un fichero de skill que comprobar"
    consulta = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        cwd=RAIZ,
        input="\n".join(ficheros),
        capture_output=True,
        text=True,
        check=False,
    )
    # 0 = alguno está ignorado; 1 = ninguno lo está. Cualquier otro es un error
    # de git, y entonces esta prueba no puede afirmar nada: falla.
    assert consulta.returncode in (0, 1), (
        f"git check-ignore falló con código {consulta.returncode}: {consulta.stderr.strip()}"
    )
    ignorados = [linea for linea in consulta.stdout.splitlines() if linea.strip()]
    assert ignorados == [], (
        f"estas skills no llegarían al repositorio, `.gitignore` las descarta: {ignorados}. "
        "Añade la regla de admisión en `.gitignore`, no uses `git add -f`."
    )
