"""La mina en dos pasadas: que la lección no dependa de que alguien se acuerde (ADR-174).

Por qué existe, medido el 12-09-2026 antes de escribir una línea: este
repositorio tiene DOS sitios donde debería caer una lección —el catálogo
`patrones.md` de la skill y `docs/audits/registro_defectos.yml`—, los dos con
su regla de entrada escrita dentro, y los dos se tocaron por última vez el
mismo día y en el mismo commit (`5cc3f18`, 31-08-2026). Desde entonces nacieron
**48 ADR** y no entró ni una lección ni un defecto. Mientras tanto la familia
más vieja de la casa —una pieza correcta a la que no llama nadie— mordió su
octava vez (`MirroredWorkItem.cerrada`, ADR-173) con `AGENTS.md` diciendo
todavía «seis veces» a mano.

Esta batería no comprueba que una lección sea buena: eso no lo puede hacer una
máquina, y ADR-174 lo declara. Comprueba que **esté**, que su familia se pueda
contar y que la prueba que dice hacerla cumplir exista de verdad.

Y ejecuta el detector de verdad. La lección de ADR-172 costó tres rondas: una
guardia que solo compara cadenas y nunca llama a la función que dice probar no
prueba nada. Por eso `problemas_de_la_leccion` vive en
`sirius_engine.memoria` —lo usan la vista generada y esta batería— y aquí se
rompe a propósito de siete maneras para verlo caer.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sirius_engine.memoria import (
    CARPETA_DE_PRUEBAS,
    CLAVE_FAMILIA,
    CLAVE_GUARDIAN,
    CLAVE_REPETIRIA,
    CLAVE_SIN_LECCION,
    PRIMER_ADR_CON_LECCION,
    SIN_GUARDIAN,
    TITULO_LECCION,
    leer_leccion,
    problemas_de_la_leccion,
)

RAIZ = Path(__file__).resolve().parents[2]
DECISIONES = RAIZ / "docs" / "decisions"
_NUMERO = re.compile(r"^ADR-(\d{3})-")


def _adr_obligados() -> list[Path]:
    """Los ADR a los que la obligación alcanza: del PRIMER_ADR_CON_LECCION en adelante."""
    obligados = []
    for ruta in sorted(DECISIONES.glob("ADR-*.md")):
        if (m := _NUMERO.match(ruta.name)) and int(m.group(1)) >= PRIMER_ADR_CON_LECCION:
            obligados.append(ruta)
    return obligados


LECCION_BUENA = f"""# ADR-999 — Una cosa

## Decisión

Se decide algo.

{TITULO_LECCION}

- {CLAVE_FAMILIA}: `pieza-sin-lector`
- {CLAVE_REPETIRIA}: construir una pieza correcta y no llamarla desde ningún sitio.
- {CLAVE_GUARDIAN}: `tests/automation/test_piezas_con_llamante.py`
"""


# --- Lo que la obligación alcanza de verdad ---------------------------------


def test_hay_al_menos_un_adr_obligado() -> None:
    """Si no hubiera ninguno, las pruebas de abajo pasarían en vacío.

    Es la cuarta forma de prueba vacua que recoge `patrones.md`: una puerta
    parametrizada sobre una lista vacía está siempre verde.
    """
    assert _adr_obligados(), (
        f"no hay ningún ADR con número >= {PRIMER_ADR_CON_LECCION}: esta batería "
        "estaría pasando en vacío"
    )


@pytest.mark.parametrize("ruta", _adr_obligados(), ids=lambda r: r.name[:11])
def test_todo_adr_obligado_declara_su_leccion(ruta: Path) -> None:
    problemas = problemas_de_la_leccion(ruta.read_text(encoding="utf-8"), raiz=RAIZ)
    assert not problemas, f"{ruta.name}: " + "; ".join(problemas)


def test_los_adr_anteriores_quedan_exentos() -> None:
    """La obligación empieza en ADR-174 y no se aplica hacia atrás (ADR-174, límite 2).

    Rellenar los 173 anteriores hoy sería escribir de memoria lo que en su día
    no se capturó. Esta prueba fija esa exención: si alguien bajara el corte,
    la batería entera se pondría roja y esto lo dice antes.
    """
    anteriores = [
        r
        for r in DECISIONES.glob("ADR-*.md")
        if (m := _NUMERO.match(r.name)) and int(m.group(1)) < PRIMER_ADR_CON_LECCION
    ]
    assert anteriores, "no hay ADR anteriores: el corte no separa nada"
    sin_leccion = [
        r for r in anteriores if problemas_de_la_leccion(r.read_text(encoding="utf-8"), raiz=RAIZ)
    ]
    assert sin_leccion, (
        "todos los ADR anteriores al corte declaran ya su lección: entonces el "
        "corte sobra y hay que bajarlo"
    )


# --- El detector, roto a propósito de siete maneras --------------------------


def test_una_leccion_bien_formada_no_se_senala() -> None:
    """El control positivo: sin él, un detector que señale SIEMPRE pasaría las de abajo."""
    assert problemas_de_la_leccion(LECCION_BUENA, raiz=RAIZ) == ()


def test_sin_bloque_no_hay_leccion() -> None:
    roto = LECCION_BUENA.split(TITULO_LECCION)[0]
    problemas = problemas_de_la_leccion(roto, raiz=RAIZ)
    assert problemas and TITULO_LECCION in problemas[0]


@pytest.mark.parametrize("clave", [CLAVE_FAMILIA, CLAVE_REPETIRIA, CLAVE_GUARDIAN])
def test_cada_una_de_las_tres_lineas_es_imprescindible(clave: str) -> None:
    """Quitar cualquiera de las tres tiene que caer, y nombrando cuál falta."""
    roto = "\n".join(
        linea for linea in LECCION_BUENA.splitlines() if not linea.startswith(f"- {clave}:")
    )
    problemas = problemas_de_la_leccion(roto, raiz=RAIZ)
    assert any(clave in problema for problema in problemas), (
        f"quitar «{clave}» no se señaló: {problemas}"
    )


def test_una_familia_que_no_es_identificador_estable_se_senala() -> None:
    """«Pieza Sin Lector» y `pieza-sin-lector` no se contarían juntas, y esa es la gracia."""
    roto = LECCION_BUENA.replace("`pieza-sin-lector`", "Pieza Sin Lector, más o menos")
    problemas = problemas_de_la_leccion(roto, raiz=RAIZ)
    assert any("identificador estable" in problema for problema in problemas)


def test_una_prueba_que_no_existe_se_senala() -> None:
    """Decir que una prueba lo hace cumplir sin que exista es peor que no decir nada."""
    roto = LECCION_BUENA.replace(
        "tests/automation/test_piezas_con_llamante.py",
        "tests/automation/test_que_no_existe_en_este_arbol.py",
    )
    problemas = problemas_de_la_leccion(roto, raiz=RAIZ)
    assert any("no es un fichero" in problema for problema in problemas), problemas


def test_declarar_que_no_hay_leccion_vale_y_exige_razon() -> None:
    sin_leccion = LECCION_BUENA.split(TITULO_LECCION)[0] + (
        f"{TITULO_LECCION}\n\n- {CLAVE_SIN_LECCION}: es una elección entre dos "
        "diseños igual de válidos; no hay error que repetir.\n"
    )
    assert problemas_de_la_leccion(sin_leccion, raiz=RAIZ) == ()
    vacia = sin_leccion.replace(
        "es una elección entre dos diseños igual de válidos; no hay error que repetir.", ""
    )
    assert problemas_de_la_leccion(vacia, raiz=RAIZ)


def test_declarar_las_dos_cosas_a_la_vez_se_senala() -> None:
    """O hay lección o no la hay: las dos juntas dejarían la cuenta a gusto del lector."""
    roto = LECCION_BUENA + f"- {CLAVE_SIN_LECCION}: pero tampoco, vete a saber.\n"
    problemas = problemas_de_la_leccion(roto, raiz=RAIZ)
    assert any("a la vez" in problema for problema in problemas)


def test_la_leccion_escrita_fuera_de_su_seccion_no_cuenta() -> None:
    """El agujero exacto que ADR-172 encontró en su propia guardia, cerrado aquí.

    Si el detector buscara las tres claves por todo el fichero, escribirlas en
    cualquier párrafo bastaría para pasar. Se buscan DENTRO de la sección.
    """
    fuera = (
        "# ADR-999 — Una cosa\n\n## Decisión\n\n"
        f"- {CLAVE_FAMILIA}: `pieza-sin-lector`\n"
        f"- {CLAVE_REPETIRIA}: algo.\n"
        f"- {CLAVE_GUARDIAN}: `tests/automation/test_piezas_con_llamante.py`\n"
    )
    problemas = problemas_de_la_leccion(fuera, raiz=RAIZ)
    assert problemas and TITULO_LECCION in problemas[0]


# --- Que la vista y el detector no se separen --------------------------------


def test_toda_leccion_declarada_aparece_en_la_vista() -> None:
    """`MEMORIA.md` es donde se lee la cuenta: una lección que no llegue ahí no existe."""
    memoria = (RAIZ / "MEMORIA.md").read_text(encoding="utf-8")
    for ruta in _adr_obligados():
        leccion = leer_leccion(ruta.read_text(encoding="utf-8").splitlines())
        if leccion is None or not leccion.familia:
            continue
        assert f"`{leccion.familia}`" in memoria, (
            f"{ruta.name} declara la familia «{leccion.familia}» y la vista no la "
            "recoge; regenera con `uv run sirius-memoria conocimiento`"
        )


def test_sin_prueba_que_lo_haga_cumplir_es_una_respuesta_valida() -> None:
    """Una lección que todavía es solo prosa se declara como tal, con su razón."""
    solo_prosa = LECCION_BUENA.replace(
        "`tests/automation/test_piezas_con_llamante.py`",
        f"{SIN_GUARDIAN}: exigiría un analizador estático que hoy daría falsos positivos",
    )
    assert problemas_de_la_leccion(solo_prosa, raiz=RAIZ) == ()
    leccion = leer_leccion(solo_prosa.splitlines())
    assert leccion is not None and not leccion.tiene_guardian


# --- Lo que la revisión del 12-09-2026 encontró que se colaba ---------------


def test_una_carpeta_que_existe_no_es_una_prueba() -> None:
    """«lo hace cumplir: tests/automation» pasaba, y la vista decía que tenía prueba.

    Comprobar que la RUTA existe es más débil de lo que la línea promete: una
    carpeta existe siempre. Y el daño no es cosmético: la columna «hay prueba
    que la haga cumplir» de `MEMORIA.md` salía en «sí» para una lección que no
    tiene ninguna, que es justo el dato para el que esa columna existe.
    """
    roto = LECCION_BUENA.replace(
        "`tests/automation/test_piezas_con_llamante.py`", "`tests/automation`"
    )
    problemas = problemas_de_la_leccion(roto, raiz=RAIZ)
    assert any("no es un fichero" in problema for problema in problemas), problemas


def test_lo_que_hace_cumplir_una_leccion_vive_entre_las_pruebas() -> None:
    """Un módulo de producción no hace cumplir nada: lo hace la prueba que lo fija."""
    roto = LECCION_BUENA.replace(
        "`tests/automation/test_piezas_con_llamante.py`", "`src/sirius_engine/memoria.py`"
    )
    problemas = problemas_de_la_leccion(roto, raiz=RAIZ)
    assert any(CARPETA_DE_PRUEBAS in problema for problema in problemas), problemas


def test_declarar_que_no_hay_prueba_exige_decir_por_que() -> None:
    """«ninguna prueba» a secas pasaba, y no se puede revisar después.

    Una lección sin prueba es legítima -no todo se puede hacer imposible con
    una-, pero entonces la razón es lo único que permite volver dentro de un
    mes y decidir si ya se puede.
    """
    sin_razon = LECCION_BUENA.replace(
        "`tests/automation/test_piezas_con_llamante.py`", SIN_GUARDIAN
    )
    problemas = problemas_de_la_leccion(sin_razon, raiz=RAIZ)
    assert any("sin decir por qué" in problema for problema in problemas), problemas

    con_razon = LECCION_BUENA.replace(
        "`tests/automation/test_piezas_con_llamante.py`",
        f"{SIN_GUARDIAN}: exigiría un analizador estático que hoy daría falsos positivos",
    )
    assert problemas_de_la_leccion(con_razon, raiz=RAIZ) == ()
