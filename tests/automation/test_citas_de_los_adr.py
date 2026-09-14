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
_ADR_135 = (
    "ADR-135-el-corrector-actualiza-en-el-mismo-commit-el-papel-que-depende-de-su-correccion.md"
)
_ADR_139 = "ADR-139-la-reconciliacion-pasa-cada-hora-activa-en-vez-de-cada-seis.md"
_ADR_140 = "ADR-140-el-corrector-firma-su-run-y-demuestra-cada-mutacion.md"
_ADR_170 = (
    "ADR-170-dec-001-entra-por-pertenencia-a-su-lista-cerrada-portar-los-miembros-del-origen-"
    "y-que-g4-decida-por-pertenencia.md"
)
_ADR_177 = (
    "ADR-177-la-ampliacion-por-categoria-entra-por-una-senal-explicita-de-la-peticion-"
    "no-por-la-subcadena-contexto.md"
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
    # ADR-177 (H4 de ADR-148, incidencia #581) cita el mismo símbolo del
    # laboratorio para decir de dónde venía la regla de subcadena que retira
    # del dominio: la cita es histórica —cuenta qué se portó y por qué deja
    # de decidir— y el fichero de origen sigue sin fusionarse a Sirius.
    "experiments/adr002/lateral/categoria.py:_pide_contexto": [
        _ADR_112,
        _ADR_113,
        _ADR_115,
        _ADR_177,
    ],
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
    # ADR-135 (el prompt del corrector) cita el mismo informe como origen de
    # las dos familias que motivan su cambio (prosa desincronizada y cifras
    # a mano).
    "docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09.md": [_ADR_132, _ADR_134, _ADR_135],
    "docs/audits/mina-2026-09-medicion-de-guardianes.md": [_ADR_132, _ADR_134],
    # ADR-139 (el cron del reconciliador) cita el papel de cambios para el
    # propietario que salió de la misma mina: vive en la misma rama de
    # auditoría que nunca se fusiona entera.
    "docs/audits/mina-2026-09-cambios-para-el-propietario.md": [_ADR_139, _ADR_140],
    # ADR-170 (hueco H5 de ADR-148, incidencia #582) porta a la fixture del
    # banco la membresía de lista cerrada de `DEC-001` y cita el proyector
    # del laboratorio para documentar DÓNDE se perdió: es el fichero que no
    # exponía esa tabla de membresía como JSON. Vive en
    # `evidence/adr001-spikes`, que a propósito nunca se fusiona entera a
    # `main`; el porte cita su fuente, la fuente sigue sin fusionarse.
    "experiments/adr002/projection/build.py": [_ADR_170],
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


# --- Por qué esta guarda NO sale de `docs/decisions/` (ADR-190) ---------------
#
# ADR-177 dejó declarado el único hueco de la mina de lecciones: «lo hace
# cumplir: ninguna prueba … nada en este repositorio vigila la coherencia de la
# prosa de `docs/` con el árbol». La incidencia #619 encargó **medir antes de
# taparlo**, con el criterio que ADR-078 escribió para la incidencia #267: una
# comprobación entra solo si caza más defectos reales que falsos positivos.
#
# La medida, el 14-09-2026, ejecutando `citas_de` sobre los 132 documentos de
# `docs/` que quedan fuera de `docs/decisions/`: **590 citas reconocidas, 23
# rotas repartidas en 17 ficheros**. Clasificadas una a una abajo: **ninguna de
# las 23 es un defecto de este árbol**. Las 23 son prosa correcta sobre algo que
# no es este árbol en este commit —una rama, otro repositorio, una ruta elidida,
# una ruta propuesta, un directorio que solo existe durante una construcción—.
#
# Con cero defectos reales y 23 falsos, el criterio no se salva cambiándole la
# forma a la guarda: se puede escribir la regla que calla a cada familia, pero
# la cosecha sigue siendo cero. Por eso el barrido **se queda en
# `docs/decisions/`**, y las tres pruebas de abajo fijan esa decisión: que la
# medida siga siendo la que se midió, que ninguna categoría nueva entre sin
# veredicto, y que el barrido no se amplíe sin volver a medir.
#
# Lo que esta decisión acepta a cambio, escrito para que nadie lo descubra
# después: una cita que se rompa mañana en `docs/` fuera del registro **no la
# va a ver nadie**. Se aceptó con la medida delante, no por descuido.

CARPETA_DOCUMENTACION = RAIZ / "docs"

#: Las siete categorías con las que ADR-190 clasificó las 23. Todas significan
#: lo mismo para el saldo —«la prosa acierta, la que se equivoca es la guarda»—
#: y por eso el recuento de defectos reales es cero.
SIN_DEFECTO_DE_ESTE_ARBOL: dict[str, str] = {
    "rama-del-repositorio": (
        "la cita es el nombre de una RAMA que empieza por una raíz del "
        "repositorio (`docs/...`), no una ruta de fichero"
    ),
    "ruta-elidida": (
        "la prosa abrevió la ruta con `…` o `...` a propósito: no hay ninguna "
        "ruta concreta que abrir, igual que en un globo o una plantilla"
    ),
    "rama-de-origen-no-fusionada": (
        "el fichero existe hoy en otra rama que a propósito nunca se fusiona "
        "entera; es la categoría que ADR-105 ya reconoció para los ADR"
    ),
    "adr-citado-por-su-numero": (
        "`docs/decisions/ADR-002` sin el resto del nombre: el ADR existe, lo "
        "que la prosa escribe es su número, no su fichero"
    ),
    "ruta-propuesta-todavia-no-creada": (
        "un documento de propuesta nombra dónde IRÍA algo; la ausencia no "
        "invalida la frase, es la frase"
    ),
    "directorio-efimero-de-la-construccion": (
        "lo crea una herramienta durante el empaquetado dentro de un worktree "
        "temporal y se borra al terminar: nunca está en el árbol confirmado"
    ),
    "sustituido-a-proposito": (
        "el fichero se sustituyó por otro y el documento lo cita justo para "
        "pedir esa sustitución: exigir que exista sería exigir que no se hiciera"
    ),
}

#: Las 23, una a una: `(documento, cita, categoría)`. Es la tabla que sostiene
#: la decisión de ADR-190, y por eso se comprueba que siga reproduciéndose.
MEDICION_FUERA_DEL_REGISTRO: tuple[tuple[str, str, str], ...] = (
    (
        "docs/audits/AUDITORIA_INTEGRAL_INCORPORACION_CLAUDE_2026-07.md",
        "docs/claude-project-onboarding-20260720",
        "rama-del-repositorio",
    ),
    (
        "docs/audits/SIRIUS_AUDITORIA_MODEL_STUDIO_2026-08.md",
        "docs/model-studio-ui-001",
        "rama-del-repositorio",
    ),
    (
        "docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md",
        "tests/.../test_pa_0_2_rec_01_banco_evidencia.py",
        "ruta-elidida",
    ),
    (
        "docs/audits/evidencia-cerrar-b1.md",
        "docs/investigaciones/2026-08-28-orden-386-….md",
        "ruta-elidida",
    ),
    (
        "docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md",
        "docs/decisions/ADR-016-…md",
        "ruta-elidida",
    ),
    (
        "docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md",
        "docs/decisions/ADR-019-…md",
        "ruta-elidida",
    ),
    (
        "docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md",
        "docs/audits/SIRIUS_LEARNING_SEAM_AUDIT_2026-08.md",
        "rama-de-origen-no-fusionada",
    ),
    (
        "docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md",
        "experiments/adr002/modelo_local/",
        "rama-de-origen-no-fusionada",
    ),
    (
        "docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md",
        "experiments/adr002/lateral/categoria.py",
        "rama-de-origen-no-fusionada",
    ),
    (
        "docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md",
        "experiments/adr002/lateral/categoria.py",
        "rama-de-origen-no-fusionada",
    ),
    (
        "docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md",
        "docs/decisions/ADR-002",
        "adr-citado-por-su-numero",
    ),
    (
        "docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md",
        "docs/decisions/ADR-002",
        "adr-citado-por-su-numero",
    ),
    (
        "docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md",
        "docs/decisions/ADR-002",
        "adr-citado-por-su-numero",
    ),
    (
        "docs/implementation/AGENT_OPPORTUNITY_MATRIX.md",
        "docs/implementation/agent_runs/",
        "ruta-propuesta-todavia-no-creada",
    ),
    (
        "docs/implementation/SIRIUS_0.2_ADR001_PAQUETE_OPERATIVO_SPIKES_v1.0.md",
        "experiments/adr001/",
        "ruta-propuesta-todavia-no-creada",
    ),
    (
        "docs/implementation/B13_PACKAGING.md",
        "src/sirius/deployment/",
        "directorio-efimero-de-la-construccion",
    ),
    (
        "docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_RECONCILIACION_v1.0_PROPUESTA.md",
        "src/sirius/presentation/studio_mode_widget.py",
        "sustituido-a-proposito",
    ),
    (
        "docs/investigaciones/2026-09-11-flujos-reales-de-agentes-comparados-con-el-motor.md",
        "docs/architecture.md",
        "arbol-de-otro-proyecto",
    ),
    (
        "docs/investigaciones/2026-09-11-flujos-reales-de-agentes-comparados-con-el-motor.md",
        "docs/AGENT-SETUP.md",
        "arbol-de-otro-proyecto",
    ),
    (
        "docs/investigaciones/2026-09-11-flujos-reales-de-agentes-comparados-con-el-motor.md",
        "docs/intended-usage.md",
        "arbol-de-otro-proyecto",
    ),
    (
        "docs/investigaciones/2026-09-11-flujos-reales-de-agentes-comparados-con-el-motor.md",
        "docs/integrations/codex.mdx",
        "arbol-de-otro-proyecto",
    ),
    (
        "docs/investigaciones/2026-09-11-flujos-reales-de-agentes-comparados-con-el-motor.md",
        "docs/solutions/",
        "arbol-de-otro-proyecto",
    ),
    (
        "docs/investigaciones/2026-09-11-que-memoria-compartida-para-ias-existe-ya-hecha-y-probada.md",
        "docs/integrations/codex.mdx",
        "arbol-de-otro-proyecto",
    ),
)

#: `arbol-de-otro-proyecto` no está en `SIN_DEFECTO_DE_ESTE_ARBOL` por
#: comodidad: es la categoría que NO existe en `docs/decisions/` —un ADR cita
#: este árbol— y que aparece en cuanto la guarda sale a `docs/investigaciones/`,
#: donde una investigación compara repositorios ajenos y cita SUS rutas. Es la
#: que mejor explica por qué el criterio calibrado sobre los ADR no se traslada:
#: 6 de las 13 citas de esa carpeta son de otros árboles.
CATEGORIA_DE_OTRO_PROYECTO = "arbol-de-otro-proyecto"
CATEGORIAS_CLASIFICADAS = frozenset(SIN_DEFECTO_DE_ESTE_ARBOL) | {CATEGORIA_DE_OTRO_PROYECTO}


def documentos_de_docs_fuera_del_registro() -> list[Path]:
    """Los `.md` de `docs/` que esta guarda **no** mira, y no va a mirar."""
    return [
        documento
        for documento in sorted(CARPETA_DOCUMENTACION.rglob("*.md"))
        if documento.parent != REGISTRO
    ]


def citas_rotas_de(documento: Path) -> list[str]:
    """Las citas de un documento que hoy no se pueden abrir, sin excepciones."""
    return [
        ruta
        for ruta in citas_de(documento.read_text(encoding="utf-8"))
        if not (RAIZ / _ruta_de_fichero(ruta)).exists()
    ]


@pytest.mark.parametrize(
    ("documento", "cita", "categoria"),
    MEDICION_FUERA_DEL_REGISTRO,
    ids=lambda valor: str(valor),
)
def test_cada_cita_clasificada_por_adr_190_sigue_siendo_la_que_se_midio(
    documento: str, cita: str, categoria: str
) -> None:
    """La tabla que sostiene ADR-190 no puede quedarse vieja en silencio.

    Esto **no** es la guarda ampliada: no exige que la prosa de `docs/` sea
    correcta ni se rompe porque aparezca una cita rota nueva -eso es justo lo
    que ADR-190 decidió no vigilar-. Exige lo contrario: que las 23 que se
    clasificaron sigan siendo exactamente lo que el ADR dice que son.
    """
    ruta = RAIZ / documento
    assert ruta.is_file(), f"{documento} ya no existe: la tabla de ADR-190 apunta a la nada"
    assert cita in citas_de(ruta.read_text(encoding="utf-8")), (
        f"{documento} ya no cita `{cita}`. La medida de ADR-190 cambió: vuelve a medirla "
        "y re-decide si la ampliación sale a cuenta, en vez de retocar la tabla a ojo."
    )
    assert not (RAIZ / _ruta_de_fichero(cita)).exists(), (
        f"`{cita}` ya existe en el árbol, así que dejó de ser un falso positivo "
        f"de la categoría `{categoria}`: quita la fila de MEDICION_FUERA_DEL_REGISTRO."
    )


def test_la_medicion_no_admite_una_categoria_sin_veredicto() -> None:
    """Una fila con categoría nueva sería un veredicto que nadie escribió."""
    sin_veredicto = sorted(
        {categoria for _, _, categoria in MEDICION_FUERA_DEL_REGISTRO} - CATEGORIAS_CLASIFICADAS
    )
    assert sin_veredicto == [], (
        f"categorías sin veredicto escrito: {sin_veredicto}. Cada categoría de "
        "MEDICION_FUERA_DEL_REGISTRO explica por qué NO es un defecto de este árbol."
    )
    documentos = {documento for documento, _, _ in MEDICION_FUERA_DEL_REGISTRO}
    assert len(MEDICION_FUERA_DEL_REGISTRO) == 23, "ADR-190 midió 23 citas rotas"
    assert len(documentos) == 17, "ADR-190 las midió repartidas en 17 ficheros"


def test_la_guarda_sigue_barriendo_solo_el_registro_de_decisiones() -> None:
    """La decisión de ADR-190, fijada: el barrido no sale de `docs/decisions/`.

    Si alguien amplía `_adrs()` a `docs/`, esto se pone rojo y le manda a
    ADR-190 a volver a medir. No es una prohibición: es la exigencia de que la
    ampliación traiga su medida, que es lo que la incidencia #267 pide.
    """
    barridos = _adrs()
    assert len(barridos) >= 184, (
        f"solo {len(barridos)} ADR barridos; el 14-09-2026 eran 184 y el registro solo crece"
    )
    fuera = sorted(str(documento) for documento in barridos if documento.parent != REGISTRO)
    assert fuera == [], (
        f"el barrido salió de docs/decisions/: {fuera}. ADR-190 midió que ahí fuera la "
        "guarda caza 0 defectos reales y 23 falsos; para ampliarla, vuelve a medir."
    )


def test_el_corpus_de_fuera_del_registro_se_sigue_pudiendo_medir() -> None:
    """Anti-vacua de la medida: sin esto, un barrido roto la daría por buena.

    Suelos holgados y solo hacia abajo, como el resto de este fichero: el
    14-09-2026 eran 132 documentos y 590 citas.
    """
    documentos = documentos_de_docs_fuera_del_registro()
    assert len(documentos) >= 100, f"solo {len(documentos)} documentos: ¿se movió docs/?"
    total = sum(len(citas_de(documento.read_text(encoding="utf-8"))) for documento in documentos)
    assert total >= 400, f"solo {total} citas encontradas; el 14-09-2026 había 590 en 132 ficheros"


def test_la_guarda_sigue_cazando_una_cita_rota_sembrada_en_un_adr_de_verdad(
    tmp_path: Path,
) -> None:
    """«Que siguen cazando lo que cazaban», demostrado con una mutación.

    El corpus real está limpio, así que las 184 comprobaciones pasarían igual
    con la guarda desarmada. Aquí se siembra el defecto en el texto de un ADR
    de verdad -no en uno sintético- y se comprueba que `_rotas` lo ve, y que
    sin la siembra no ve nada.
    """
    original = REGISTRO / "ADR-052-una-ruta-citada-por-un-adr-existe-o-esta-fijada-como-historia.md"
    texto = original.read_text(encoding="utf-8")
    assert "tests/automation/test_citas_de_los_adr.py" in citas_de(texto), (
        "ADR-052 dejó de citar su propia prueba: elige otra semilla"
    )

    sano = tmp_path / original.name
    sano.write_text(texto, encoding="utf-8")
    assert _rotas(sano) == [], "el control falla: el ADR de verdad ya traía citas rotas"

    sembrado = tmp_path / "sembrado" / original.name
    sembrado.parent.mkdir()
    sembrado.write_text(
        texto.replace(
            "tests/automation/test_citas_de_los_adr.py",
            "tests/automation/test_no_existe_de_ninguna_manera.py",
        ),
        encoding="utf-8",
    )
    assert "tests/automation/test_no_existe_de_ninguna_manera.py" in _rotas(sembrado)
