"""Una ruta citada por un ADR existe, o está fijada como historia (ADR-052).

El método de este repositorio (ADR-001) exige que cada afirmación traiga la
comprobación que la sostiene, y un ADR cumple esa regla **citando ficheros**.
Esa cita es el puente entre lo que se afirma y lo que lo prueba, y se cae solo:
cuando el código se mueve o un fichero se borra, nadie vuelve a los ADR. La
evidencia no se contradice, se pudre en silencio.

No es hipotético. En `bbfb625` había tres citas rotas, y una era del día
anterior: ADR-045 citaba un parte de auditoría que vivía en una rama sin
fusionar. Lo arregló por casualidad otra PR que traía ese fichero a `main` por
un motivo distinto.

**Esta prueba es conservadora a propósito, y esa es su decisión de diseño
principal.** Deja escapar citas rotas antes que señalar una sana: una prueba que
grita en falso se acaba ignorando, y entonces no protege de nada. Por eso solo
mira `código en línea` fuera de los bloques de código, exige un único token y
exige una raíz del repositorio delante. Lo que renuncia a mirar está medido y
escrito en ADR-052: sobre `main` renunciaba a mirar 18 citas de 156, y ninguna
de esas 18 estaba rota el día que se escribió esto.

Es determinista: lee ficheros y comprueba si una ruta existe. No razona, no
invoca ningún modelo, no sale a la red y cuesta milisegundos.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = RAIZ / "docs" / "decisions"

# Una cita solo cuenta si empieza por una de estas. Es el filtro que separa una
# RUTA de todo lo demás que lleva barra: ramas (`origin/main`, `feat/loquesea`),
# repositorios de terceros (`astral-sh/setup-uv`), rutas relativas al paquete
# (`domain/work_item.py`) y módulos de Python. Ninguno de esos se puede
# distinguir con certeza, así que no se miran.
RAICES_DEL_REPOSITORIO = (
    ".claude/",
    ".github/",
    "docs/",
    "experiments/",
    "migrations/",
    "scripts/",
    "src/",
    "tests/",
)

# Globos, URLs y plantillas de las APIs (`repos/{o}/{r}/...`) no son rutas que se
# puedan abrir: se descartan enteras en vez de intentar resolverlas.
NO_ES_UNA_RUTA_CONCRETA = ("://", "*", "{", "}", "<", ">")

CODIGO_EN_LINEA = re.compile(r"`([^`\n]+)`")
# `fichero.py:95`, `workflow.yml:67-81`, `test_x.py::test_caso`.
SUFIJO_DE_CITA = re.compile(r"::.*$|:\d[\d,\-]*$")

# --- La excepción, fijada por nombre -----------------------------------------
#
# Mismo patrón que `DUPLICADO_HISTORICO` en `test_registro_de_decisiones.py`:
# una ruta borrada A PROPÓSITO que un ADR cita como historia, con la lista
# cerrada de los ADR que pueden citarla. Un ADR nuevo que la cite rompe la
# prueba hasta que alguien venga aquí y explique por qué.
#
# `tests/automation/test_lectura_de_etiquetas.py` no se movió: se borró, y
# borrarlo ES la decisión que ADR-028 registra («Se borra
# tests/automation/test_lectura_de_etiquetas.py entero»). ADR-027 la creó, y
# ADR-028 decidió expresamente no reescribir ADR-027 porque «borrar el rastro
# eliminaría justo lo que sirve». Exigir que exista sería exigir que no se
# hubiera tomado la decisión. ADR-052 la cita al explicar esta excepción.
BORRADOS_A_PROPOSITO: dict[str, list[str]] = {
    "tests/automation/test_lectura_de_etiquetas.py": [
        "ADR-027-las-etiquetas-se-leen-del-objeto-de-la-incidencia.md",
        "ADR-028-una-averia-transitoria-no-justifica-una-invariante-permanente.md",
        "ADR-052-una-ruta-citada-por-un-adr-existe-o-esta-fijada-como-historia.md",
    ]
}

# La categoría espejo, que la primera versión de esta guarda no previó y que
# apareció el mismo día que se fusionó: una ruta citada **precisamente para
# decir que TODAVÍA NO existe**.
#
# ADR-055 escribe «no existe todavía ni la puerta que arranca un trabajador
# (`ports/worker.py` no está)» para explicar por qué el comando de consola no
# puede crear trabajo. Ahí la ausencia del fichero no invalida la afirmación:
# **es** la afirmación. Exigir que exista sería exigir que el ADR mintiera.
#
# Se separa de BORRADOS_A_PROPOSITO en vez de meterla ahí porque no es lo
# mismo: aquello es «existió y se borró a propósito», esto es «no ha existido
# nunca todavía». Confundirlas haría que el día en que `ports/worker.py` se
# cree, nadie se enterara de que esta excepción sobra.
TODAVIA_NO_EXISTEN: dict[str, list[str]] = {
    "src/sirius_engine/ports/worker.py": [
        "ADR-055-un-comando-de-consola-que-el-propietario-pueda-teclear-para-hablar-con-el-motor.md",
    ]
}

# Tercera categoría (ADR-105, incidencia #445): una ruta que existe, hoy mismo,
# en OTRA rama del repositorio — no en `main` ni antes ni después — porque el
# ADR la cita para contar de dónde vino un dato, no para exigir que ese dato
# viva en `main`. No es BORRADOS_A_PROPOSITO (nunca existió en `main`, así que
# no se «borró» de ningún sitio que este árbol conociera) ni TODAVIA_NO_EXISTEN
# (no describe una ausencia futura: describe una rama de origen que, a
# propósito, nunca se fusiona entera).
#
# ADR-104 porta, intocable por decisión D1, el banco de 47 casos de
# `evidence/adr001-spikes` a `tests/acceptance/fixtures/evidence_bank_47_casos.json`
# y documenta esa procedencia citando cuatro rutas de `experiments/adr002/` tal
# como existen en esa rama de origen — nunca se copian a `main`, porque el
# encargo prohíbe tocar producto en M7. Confundir esta categoría con las otras
# dos de arriba dejaría el aviso de "resucitó" mal etiquetado: estos ficheros
# no van a "volver" nunca a `main` — viven donde siempre vivieron.
#: ADR-109 (incidencia #455) y ADR-110 (incidencia #457) citan varias de las
#: mismas rutas de `evidence/adr001-spikes`: la segunda porta lo que la
#: primera diagnosticó como pendiente. Nombrar la constante evita repetir el
#: nombre de fichero completo (largo, y fácil de desalinear entre entradas)
#: en cada entrada que ambos ADR comparten.
_ADR_109 = (
    "ADR-109-el-tratamiento-lexico-portado-mejora-el-banco-de-1-47-a-10-47-pero-no-alcanza-"
    "el-suelo-d1-porque-la-precision-restante-vive-en-las-puertas-del-motor-por-etapas.md"
)
_ADR_110 = (
    "ADR-110-el-motor-por-etapas-portado-mejora-el-banco-a-11-47-pero-no-alcanza-el-suelo-"
    "d1-porque-la-peticion-por-caso-del-laboratorio-no-esta-autorizada-a-portarse.md"
)
_ADR_111 = (
    "ADR-111-la-peticion-por-caso-portada-mejora-el-banco-a-23-47-pero-d1-exige-ademas-"
    "el-indice-de-categoria-y-el-filtro-de-relevancia-ollama.md"
)
_ADR_112 = (
    "ADR-112-el-indice-de-categoria-y-el-filtro-de-relevancia-conectados-al-arnes-del-"
    "banco-incidencia-463-mejoran-cobertura-y-omisiones-criticas-pero-empeoran-los-"
    "elementos-de-mas-y-no-alcanzan-d1.md"
)
_ADR_113 = (
    "ADR-113-el-indice-de-categoria-buscable-la-regla-de-las-criticas-original-y-la-"
    "siembra-en-contexto-cierran-las-dos-causas-de-adr-112-pero-no-alcanzan-d1-"
    "incidencia-465.md"
)
_ADR_114 = (
    "ADR-114-la-restriccion-por-ambito-del-indice-de-categoria-baja-los-elementos-de-"
    "mas-de-110-a-62-pero-no-alcanza-d1-incidencia-467.md"
)
_ADR_115 = (
    "ADR-115-las-dos-puertas-que-la-ampliacion-del-arnes-no-heredaba-bajan-los-aciertos-"
    "exactos-a-29-47-y-elementos-de-mas-alcanza-d1-bajo-la-poblacion-del-umbral-publicado-"
    "incidencia-469.md"
)
_ADR_125 = (
    "ADR-125-suspender-el-limite-de-300-ms-de-rnf-003-en-el-camino-del-filtro-de-relevancia-"
    "mientras-se-mide-su-coste-real.md"
)
_ADR_127 = "ADR-127-m19a-el-indice-de-criticidad-en-la-busqueda.md"
_ADR_129 = "ADR-129-m20-la-siembra-en-contexto-por-criticidad.md"
_ADR_132 = (
    "ADR-132-el-guardian-del-contrato-local-de-ollama-convierte-adr-125-en-prueba-y-"
    "corrige-ollama-category-classifier.md"
)
_ADR_134 = (
    "ADR-134-el-guardian-del-suelo-de-prueba-muerto-retira-las-dos-cotas-tautologicas-"
    "del-banco-de-evidencia.md"
)

RAMA_DE_ORIGEN_NO_FUSIONADA: dict[str, list[str]] = {
    "experiments/adr002/round/cases.py": [
        "ADR-104-portar-el-banco-de-47-casos-de-evidence-adr001-spikes-al-modelo-real-de-sirius.md",
        _ADR_110,
        _ADR_111,
    ],
    "experiments/adr002/round/cases.py:_traducir": [
        "ADR-104-portar-el-banco-de-47-casos-de-evidence-adr001-spikes-al-modelo-real-de-sirius.md",
    ],
    "experiments/adr002/benchmark/cases_v0_5.json": [
        "ADR-104-portar-el-banco-de-47-casos-de-evidence-adr001-spikes-al-modelo-real-de-sirius.md",
        _ADR_110,
        # ADR-112 cita el mismo fichero para documentar el mapeo
        # `N1-NN -> identificador_canonico` que usó para portar el veredicto
        # congelado del filtro de relevancia (`nivel_1[].identificador_canonico`).
        _ADR_112,
    ],
    "experiments/adr002/projection/contracts.py:referencia_canonica": [
        "ADR-104-portar-el-banco-de-47-casos-de-evidence-adr001-spikes-al-modelo-real-de-sirius.md",
    ],
    # ADR-109 diagnostica por qué portar `lexical.py` (incidencia #455) no
    # basta para alcanzar el suelo D1, y para eso cita, tal como existen en
    # `evidence/adr001-spikes`, el módulo portado y las tres piezas del motor
    # por etapas que se quedan sin portar (puertas, agrupación, motor) — nunca
    # se copian a `main`, porque hacerlo sería el rediseño de B6a/B6b que el
    # alcance de la incidencia #455 que cierra con ADR-109 no autoriza.
    #
    # ADR-110 (incidencia #457) porta esas tres piezas de verdad
    # (`sirius.domain.staged_engine_gates`/`_grouping`/`sirius.domain.
    # staged_engine`) y cita las mismas rutas de origen para documentar de
    # dónde vino cada módulo — el porte cita su fuente; la fuente en sí
    # sigue sin fusionarse a `main`.
    "experiments/adr002/candidates/adr002_a/lexical.py": [_ADR_109, _ADR_110],
    "experiments/adr002/candidates/common/port.py": [_ADR_109, _ADR_110],
    "experiments/adr002/candidates/common/gates.py": [_ADR_109, _ADR_110, _ADR_115],
    "experiments/adr002/candidates/common/grouping.py": [_ADR_109, _ADR_110],
    "experiments/adr002/candidates/common/engine.py": [_ADR_109, _ADR_110],
    # Piezas que ADR-110 cita por primera vez: dependencias de origen del
    # motor por etapas (contracts/stops/trace) y la fuente de candidatas
    # léxico-estructurada (`adr002_a/candidate.py`), ninguna nombrada por
    # ADR-109 porque su diagnóstico se detuvo antes de portarlas.
    "experiments/adr002/candidates/common/contracts.py": [_ADR_110],
    "experiments/adr002/candidates/common/stops.py": [_ADR_110],
    "experiments/adr002/candidates/common/trace.py": [_ADR_110],
    "experiments/adr002/candidates/adr002_a/candidate.py": [_ADR_110],
    # El corpus congelado y los dos planos de proyección (property_key,
    # criticidad aplicada) que ADR-110 porta hacia
    # `tests/acceptance/fixtures/evidence_bank_47_casos.json` para que el
    # arnés del banco pueda declarar los ejes P2 que las puertas necesitan.
    "experiments/adr002/benchmark/conformance_corpus_v0_6.json": [_ADR_110],
    "experiments/adr002/benchmark/property_keys_v0_2.json": [_ADR_110],
    "experiments/adr002/benchmark/applied_criticality_v0_1.json": [_ADR_110],
    # Citado solo para documentar dónde vive la petición por caso que ADR-110
    # diagnostica como no portada (no se lee ni se porta ningún dato suyo).
    "experiments/adr002/benchmark/references_v0_5.json": [_ADR_110],
    # ADR-111 (incidencia #461) porta la petición por caso que ADR-110
    # diagnosticó y mide 23/47, todavía por debajo del suelo D1. Cita este
    # fichero —un experimento de filtro de relevancia con modelo local
    # completamente distinto del motor por etapas, nunca portado a
    # Sirius— para documentar dónde consta que el salto de 24/47 a 29/47
    # depende de ese filtro y no del motor de búsqueda.
    # ADR-125 porta a `src/sirius/adapters/ollama_relevance_filter.py` la
    # llamada exacta del laboratorio (extremo, esquema impuesto, `think`,
    # `keep_alive`, `temperature`, `num_ctx`) y cita los dos ficheros de
    # origen para documentar las seis diferencias con producción; el porte
    # cita su fuente, la fuente sigue sin fusionarse a `main`.
    "experiments/adr002/modelo_local/filtro.py": [_ADR_111, _ADR_125],
    "experiments/adr002/modelo_local/puerto.py": [_ADR_125],
    # ADR-112 (incidencia #463) conecta el índice de categoría y el filtro
    # de relevancia al arnés del banco, portando como fixture el veredicto
    # congelado de una corrida concreta del experimento del laboratorio —
    # ninguna de las dos rutas siguientes se copia a Sirius; el ADR las cita
    # solo para documentar de dónde salió cada dato portado.
    "experiments/adr002/modelo_local/filtro.py:filtrar": [_ADR_112, _ADR_113],
    # ADR-115 (incidencia #469, CODEX-001) cita el script de medición del
    # laboratorio para documentar que el ≤21 publicado para `elementos_de_
    # mas` lo fijó sumando solo sobre los 31 `casos_con_contenido`, nunca
    # sobre los 47 — nunca se copia el fichero a Sirius.
    "experiments/adr002/modelo_local/medir.py": [_ADR_115],
    # ADR-114 (incidencia #467) cita la misma fuente para justificar la
    # restricción por ámbito del índice de categoría del arnés: la cita
    # documenta de dónde sale la semántica portada, nunca se copia el
    # fichero a Sirius.
    "experiments/adr002/lateral/categoria.py": [
        _ADR_112,
        _ADR_113,
        _ADR_114,
        _ADR_127,
        # ADR-129 (M20, incidencia #516) porta pide_contexto/siembra_de_contexto
        # al dominio, réplica exacta del laboratorio — el fichero de origen
        # sigue sin fusionarse a Sirius.
        _ADR_129,
    ],
    "experiments/adr002/lateral/categoria.py:_pide_contexto": [_ADR_112, _ADR_113, _ADR_115],
    # ADR-132 (G1, incidencia #522) registra el guardián del contrato local de
    # Ollama y la corrección de ollama_category_classifier.py. Cita la mina de
    # aprendizaje operativo de 2026-09 que aprobó la propuesta y la nota de
    # medición del propietario que documentó la llamada partida en varias
    # líneas — ambas viven en la rama `claude/adr002-tol209-forensic-audit-
    # i0ui8k`, que a propósito nunca se fusiona entera a `main`; el ADR cita
    # su fuente, la fuente sigue sin fusionarse.
    # ADR-134 (G2, incidencia #526) registra el guardián del suelo de prueba
    # muerto y la retirada de los dos existentes en el banco de evidencia.
    # Cita las mismas dos rutas que ADR-132 (la mina que aprobó la propuesta
    # y la nota de medición del propietario), por el mismo motivo: ambas
    # viven solo en la rama `claude/adr002-tol209-forensic-audit-i0ui8k`, que
    # a propósito nunca se fusiona entera a `main`.
    "docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09.md": [_ADR_132, _ADR_134],
    "docs/audits/mina-2026-09-medicion-de-guardianes.md": [_ADR_132, _ADR_134],
}


def _fuera_de_los_bloques(texto: str) -> Iterator[str]:
    """Las líneas del documento que NO están dentro de un bloque de código.

    Ahí viven las salidas de comandos pegadas, los ejemplos y las rutas de otra
    máquina. Una valla sin cerrar deja dentro todo lo que queda: al dudar, no se
    mira.
    """
    dentro = False
    for linea in texto.splitlines():
        if linea.lstrip().startswith(("```", "~~~")):
            dentro = not dentro
            continue
        if not dentro:
            yield linea


def ruta_citada(bruto: str) -> str | None:
    """La ruta del repositorio que hay en un `código en línea`, o None.

    None significa «esto no lo sé juzgar», que es la respuesta por defecto.
    """
    texto = bruto.strip()
    if not texto or any(caracter.isspace() for caracter in texto):
        return None  # una orden entera, no una cita: `git checkout -- src/x.py`
    if any(marca in texto for marca in NO_ES_UNA_RUTA_CONCRETA):
        return None
    texto = SUFIJO_DE_CITA.sub("", texto.rstrip(".,;:)"))
    texto = texto.removeprefix("./")
    if not texto.startswith(RAICES_DEL_REPOSITORIO):
        return None
    return texto


def citas_de(texto: str) -> list[str]:
    """Todas las rutas del repositorio citadas por un documento, en orden."""
    vistas: dict[str, None] = {}
    for linea in _fuera_de_los_bloques(texto):
        for span in CODIGO_EN_LINEA.finditer(linea):
            ruta = ruta_citada(span.group(1))
            if ruta is not None:
                vistas[ruta] = None
    return list(vistas)


_SUFIJO_DE_SIMBOLO = re.compile(r":[A-Za-z_]\w*$")


def _ruta_de_fichero(ruta: str) -> str:
    """La parte de ``ruta`` que el sistema de archivos puede resolver.

    `ruta_citada()` no recorta un sufijo `:símbolo` (`:_traducir`,
    `:referencia_canonica`): solo recorta `:número` o `::algo`
    (`SUFIJO_DE_CITA`), a propósito, porque en `RAMA_DE_ORIGEN_NO_FUSIONADA`
    ese sufijo sigue haciendo falta en la clave para restringir qué símbolo
    exacto autoriza qué ADR. Pero un símbolo no es una ruta: comprobar la
    cadena tal cual contra el sistema de archivos nunca encuentra el fichero,
    ni aunque llegara a `main`. Esta función solo se usa para esa comprobación
    de archivos; la clave del diccionario no se toca."""
    return _SUFIJO_DE_SIMBOLO.sub("", ruta)


def _adrs() -> list[Path]:
    return sorted(REGISTRO.glob("ADR-*.md"))


def _rotas(adr: Path) -> list[str]:
    return [
        ruta
        for ruta in citas_de(adr.read_text(encoding="utf-8"))
        if not (RAIZ / ruta).exists()
        and adr.name not in BORRADOS_A_PROPOSITO.get(ruta, [])
        and adr.name not in TODAVIA_NO_EXISTEN.get(ruta, [])
        and adr.name not in RAMA_DE_ORIGEN_NO_FUSIONADA.get(ruta, [])
    ]


# --- La guarda ----------------------------------------------------------------


@pytest.mark.parametrize("adr", _adrs(), ids=lambda p: p.name)
def test_toda_ruta_citada_por_un_adr_existe(adr: Path) -> None:
    """El corazón: una comprobación que no se puede abrir no comprueba nada."""
    assert _rotas(adr) == [], (
        f"{adr.name} cita rutas que ya no existen: {_rotas(adr)}. "
        "Si el fichero solo se movió, actualiza el ADR. Si se borró a propósito y el ADR "
        "lo cita como historia, añádelo a BORRADOS_A_PROPOSITO explicando por qué. Si vive "
        "en otra rama que nunca se fusiona entera a propósito, añádelo a "
        "RAMA_DE_ORIGEN_NO_FUSIONADA explicando por qué."
    )


def test_lo_fijado_como_borrado_sigue_borrado_de_verdad() -> None:
    """Si el fichero vuelve, la excepción sobra y hay que quitarla de aquí."""
    resucitados = sorted(ruta for ruta in BORRADOS_A_PROPOSITO if (RAIZ / ruta).exists())
    assert resucitados == [], (
        f"estas rutas vuelven a existir: {resucitados}. Quítalas de BORRADOS_A_PROPOSITO: "
        "una excepción que ya no excepciona nada solo sirve para tapar la siguiente."
    )


def test_lo_fijado_como_borrado_lo_cita_de_verdad_quien_dice_citarlo() -> None:
    """Una excepción que nadie usa es un permiso abierto para el futuro."""
    sobrantes: list[str] = []
    for ruta, adrs in BORRADOS_A_PROPOSITO.items():
        for nombre in adrs:
            documento = REGISTRO / nombre
            if not documento.is_file() or ruta not in citas_de(
                documento.read_text(encoding="utf-8")
            ):
                sobrantes.append(f"{nombre} ya no cita {ruta}")
    assert sobrantes == [], f"excepciones que sobran: {sobrantes}"


def test_lo_fijado_como_rama_de_origen_no_fusionada_sigue_sin_existir_en_main() -> None:
    """Si el fichero llega a fusionarse a `main`, la excepción sobra y hay que quitarla."""
    fusionados = sorted(
        ruta for ruta in RAMA_DE_ORIGEN_NO_FUSIONADA if (RAIZ / _ruta_de_fichero(ruta)).exists()
    )
    assert fusionados == [], (
        f"estas rutas ya existen en main: {fusionados}. Quítalas de "
        "RAMA_DE_ORIGEN_NO_FUSIONADA: una excepción que ya no excepciona nada solo sirve "
        "para tapar la siguiente."
    )


def test_lo_fijado_como_rama_de_origen_no_fusionada_lo_cita_de_verdad_quien_dice_citarlo() -> None:
    """Una excepción que nadie usa es un permiso abierto para el futuro."""
    sobrantes: list[str] = []
    for ruta, adrs in RAMA_DE_ORIGEN_NO_FUSIONADA.items():
        for nombre in adrs:
            documento = REGISTRO / nombre
            if not documento.is_file() or ruta not in citas_de(
                documento.read_text(encoding="utf-8")
            ):
                sobrantes.append(f"{nombre} ya no cita {ruta}")
    assert sobrantes == [], f"excepciones que sobran: {sobrantes}"


# --- Anti-vacua ---------------------------------------------------------------
#
# El corpus real está limpio hoy, así que las pruebas de arriba pasarían igual
# con el extractor roto. Estas fijan el comportamiento con texto sintético, que
# es lo único que no depende de cómo esté el repositorio hoy.

_ADR_SINTETICO = """# ADR-999 — De mentira

Lo prueba `tests/automation/test_citas_de_los_adr.py`, y el fallo vivía en
`src/sirius_engine/governance.py:77`.

```
$ ls src/sirius_engine/esto_no_existe_y_esta_en_un_bloque.py
```
"""


def test_una_ruta_inventada_se_detecta() -> None:
    roto = _ADR_SINTETICO.replace("governance.py", "no_existe_de_ninguna_manera.py")
    citadas = citas_de(roto)
    assert "src/sirius_engine/no_existe_de_ninguna_manera.py" in citadas
    assert not (RAIZ / "src/sirius_engine/no_existe_de_ninguna_manera.py").exists()


def test_una_ruta_valida_no_se_señala() -> None:
    """La otra dirección: sin esto, «falla siempre» también pasaría la de arriba."""
    citadas = citas_de(_ADR_SINTETICO)
    assert "src/sirius_engine/governance.py" in citadas, "no recortó el sufijo `:77`"
    assert all((RAIZ / ruta).exists() for ruta in citadas), citadas


def test_una_ruta_dentro_de_un_bloque_de_codigo_no_se_mira() -> None:
    """Ahí hay salidas pegadas y ejemplos: es la fuente número uno de falso positivo."""
    assert "src/sirius_engine/esto_no_existe_y_esta_en_un_bloque.py" not in citas_de(_ADR_SINTETICO)


@pytest.mark.parametrize(
    "span",
    [
        "origin/main",  # una rama
        "feat/investigador-por-etiqueta",  # otra rama
        "astral-sh/setup-uv",  # un repositorio de terceros
        "https://github.com/x/y/pull/189",  # una URL
        ".github/**",  # un globo
        "scripts/automation/prompts/*.md",  # otro globo
        "repos/{o}/{r}/issues/{n}",  # una plantilla de la API
        "domain/work_item.py",  # relativa al paquete, sin `src/` delante
        "domain/escalation.CausaEscalado",  # un módulo, no un fichero
        "git checkout -- src/sirius_engine/gate.py",  # una orden entera
        "uv run pytest tests/engine/test_gate.py -q",  # otra orden
        "if/elif",  # prosa con barra
        "/root/.local/share/sirius",  # una ruta de fuera del repositorio
    ],
)
def test_lo_que_no_es_una_ruta_de_este_repositorio_se_ignora(span: str) -> None:
    """Cada uno de estos salió del corpus real y habría sido un grito en falso."""
    assert ruta_citada(span) is None


@pytest.mark.parametrize(
    ("span", "esperado"),
    [
        ("src/sirius_engine/context_recall.py:95", "src/sirius_engine/context_recall.py"),
        (
            ".github/workflows/repair-sirius-work.yml:67-81",
            ".github/workflows/repair-sirius-work.yml",
        ),
        ("tests/engine/test_gate.py::test_algo", "tests/engine/test_gate.py"),
        (
            "./tests/automation/test_citas_de_los_adr.py",
            "tests/automation/test_citas_de_los_adr.py",
        ),
        ("docs/decisions/", "docs/decisions/"),
    ],
)
def test_los_sufijos_de_cita_se_recortan(span: str, esperado: str) -> None:
    assert ruta_citada(span) == esperado


def test_el_barrido_encuentra_citas_de_verdad() -> None:
    """Si alguien rompe el extractor, la guarda pasaría en verde sin mirar nada.

    El suelo es holgado y solo hacia abajo: el registro crece, y una prueba con
    la cifra exacta de hoy caduca a la semana.
    """
    adrs = _adrs()
    assert len(adrs) >= 40, f"solo {len(adrs)} ADR leídos: ¿se movió docs/decisions/?"
    total = sum(len(citas_de(adr.read_text(encoding="utf-8"))) for adr in adrs)
    assert total >= 100, f"solo {total} citas encontradas; el 21-08-2026 había 153 en 46 ADR"


def test_las_raices_declaradas_son_directorios_de_verdad() -> None:
    """Una raíz que ya no existe deja de mirar sus citas sin que nadie se entere."""
    fantasmas = [raiz for raiz in RAICES_DEL_REPOSITORIO if not (RAIZ / raiz).is_dir()]
    assert fantasmas == [], f"raíces declaradas que ya no son directorios: {fantasmas}"


def test_ruta_de_fichero_recorta_el_sufijo_de_simbolo_para_el_sistema_de_archivos() -> None:
    """El defecto exacto (incidencia #445, hallazgo CODEX-002): comprobar la
    ruta con el sufijo de símbolo pegado nunca encuentra el fichero, así que
    `test_lo_fijado_como_rama_de_origen_no_fusionada_sigue_sin_existir_en_main`
    no detectaría jamás que el fichero llegó a `main`.

    Se reproduce con un fichero real (`context_recall.py`, existe en `src/`)
    en vez de con las cuatro rutas reales de `RAMA_DE_ORIGEN_NO_FUSIONADA`,
    que a propósito no existen en `main` hoy y no sirven para demostrar el
    caso "sí existe" sin fusionar nada de verdad.
    """
    con_simbolo = "src/sirius_engine/context_recall.py:una_funcion_cualquiera"
    assert not (RAIZ / con_simbolo).exists(), "una ruta con sufijo nunca es un fichero de verdad"
    assert (RAIZ / _ruta_de_fichero(con_simbolo)).exists()


@pytest.mark.parametrize(
    ("ruta", "esperado"),
    [
        ("experiments/adr002/round/cases.py", "experiments/adr002/round/cases.py"),
        (
            "experiments/adr002/round/cases.py:_traducir",
            "experiments/adr002/round/cases.py",
        ),
        (
            "experiments/adr002/projection/contracts.py:referencia_canonica",
            "experiments/adr002/projection/contracts.py",
        ),
    ],
)
def test_ruta_de_fichero_no_toca_rutas_sin_sufijo_de_simbolo(ruta: str, esperado: str) -> None:
    assert _ruta_de_fichero(ruta) == esperado


def test_una_excepcion_de_todavia_no_existe_se_retira_cuando_el_fichero_nace() -> None:
    """Si el fichero llega a existir, la excepción sobra y hay que quitarla.

    Sin esto, una excepción puesta para «todavía no existe» sobreviviría a la
    creación del fichero y la guarda dejaría de mirar esa ruta para siempre,
    en silencio. Es el mismo peligro que cualquier lista de excepciones que se
    queda obsoleta.
    """
    ya_existen = sorted(ruta for ruta in TODAVIA_NO_EXISTEN if (RAIZ / ruta).exists())
    assert ya_existen == [], (
        f"estas rutas ya existen: {ya_existen}. Quítalas de TODAVIA_NO_EXISTEN: "
        "la excepción se puso porque no existían, y ya no es cierto."
    )
