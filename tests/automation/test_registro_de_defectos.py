"""Un defecto encontrado no puede evaporarse.

El 20-08-2026 una auditoría encontró seis defectos y los dejó escritos en un
documento de una rama sin fusionar. El 21-08, **cuatro seguían vivos en
`main`**, sin ninguna incidencia que los siguiera, y la batería completa pasaba
en verde con ellos dentro: 2846 passed. Encontrarlos no sirvió de nada.

Esta prueba no encuentra defectos -eso no lo hace una lista-. Garantiza que uno
ya encontrado **no se pierda**: si un defecto abierto se queda sin incidencia, o
cita un fichero que ya no existe, o alguien lo borra del registro en vez de
cerrarlo, la batería se rompe.

Y garantiza, desde ADR-182, la mitad que faltaba: **que lo que pasó se
escriba**. Las ocho comprobaciones originales miraban la coherencia de lo ya
escrito, ninguna preguntaba si el registro seguía vivo, y por eso pasaron doce
días y 61 ADR en verde sobre un registro cuya última entrada era del 31-08-2026.
La segunda mitad DERIVA de `docs/decisions/` los ADR que declaran una lección
-que es como este repositorio dice «aquí mordió algo»- y exige que el registro
los acuse; lo escrito a mano es `SIN_DEFECTO_REGISTRADO`, lo que se RESTA.

Es determinista a propósito: lee dos ficheros del árbol y comprueba si una ruta
existe. No razona, no llama a ningún modelo y cuesta milisegundos. Sigue
funcionando igual el día en que el ciclo lo mueva un modelo pequeño y barato.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

from sirius_engine.memoria import PRIMER_ADR_CON_LECCION, leer_leccion

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = RAIZ / "docs" / "audits" / "registro_defectos.yml"

ESTADOS = frozenset({"abierto", "cerrado"})
CAMPOS_SIEMPRE = ("id", "titulo", "bloque", "gravedad", "estado", "ficheros")


def _defectos() -> list[dict[str, Any]]:
    datos = yaml.safe_load(REGISTRO.read_text(encoding="utf-8"))
    return list(datos["defectos"])


def test_el_registro_existe_y_no_esta_vacio() -> None:
    """Anti-vacua: si alguien vacía el registro, las demás pruebas pasarían solas."""
    assert REGISTRO.is_file(), f"falta el registro de defectos: {REGISTRO}"
    assert _defectos(), "el registro no puede quedarse sin defectos: uno cerrado se conserva"


def test_cada_defecto_trae_sus_campos_y_un_estado_conocido() -> None:
    for defecto in _defectos():
        faltan = [campo for campo in CAMPOS_SIEMPRE if campo not in defecto]
        assert faltan == [], f"{defecto.get('id', '?')}: faltan campos {faltan}"
        assert defecto["estado"] in ESTADOS, (
            f"{defecto['id']}: estado {defecto['estado']!r} desconocido; usa {sorted(ESTADOS)}"
        )


def test_ningun_identificador_repetido() -> None:
    ids = [defecto["id"] for defecto in _defectos()]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    assert repetidos == [], f"identificadores repetidos: {repetidos}"


def _abiertos_sin_incidencia(defectos: Iterable[Mapping[str, Any]]) -> list[str]:
    """EL criterio del corazón, en una función que se puede alimentar a mano.

    Vive aparte por lo que midió ADR-182: el 13-09-2026 los 32 defectos del
    registro estaban cerrados, así que la prueba de abajo filtraba por
    `abierto`, se quedaba con la lista vacía y aseveraba `[] == []`. Verde en
    vacío, y sin forma de distinguir «no hay ninguno suelto» de «el criterio ya
    no muerde». Con el criterio extraído, `test_el_criterio_del_corazon_...` lo
    ejerce sobre defectos sembrados y no depende de cómo esté el registro hoy.
    """
    return [
        defecto["id"]
        for defecto in defectos
        if defecto["estado"] == "abierto" and not isinstance(defecto.get("incidencia"), int)
    ]


def test_todo_defecto_abierto_tiene_una_incidencia_que_lo_siga() -> None:
    """El corazón de la prueba: sin incidencia, un defecto se olvida."""
    sin_incidencia = _abiertos_sin_incidencia(_defectos())
    assert sin_incidencia == [], (
        f"defectos abiertos sin incidencia que los siga: {sin_incidencia}. "
        "Abre una incidencia y pon su número, o ciérralo con `cerrado_por`."
    )


# Defectos sembrados, no leídos del registro: el criterio se ejerce sobre ellos
# aunque el registro no tenga ni un abierto. No se exige que lo tenga -que todo
# defecto conocido esté cerrado es un estado sano, no un fallo-; lo que se exige
# es que el criterio siga distinguiendo, que es lo que el conjunto vacío ocultó.
_SEMBRADO_SUELTO: dict[str, Any] = {"id": "S-1", "estado": "abierto"}
_SEMBRADO_SEGUIDO: dict[str, Any] = {"id": "S-2", "estado": "abierto", "incidencia": 597}
_SEMBRADO_CERRADO: dict[str, Any] = {"id": "S-3", "estado": "cerrado", "cerrado_por": "0" * 40}
_SEMBRADO_CON_INCIDENCIA_NO_NUMERICA: dict[str, Any] = {
    "id": "S-4",
    "estado": "abierto",
    "incidencia": "pronto",
}


def test_el_criterio_del_corazon_muerde_aunque_no_haya_ningun_abierto() -> None:
    """Anti-vacua que NO depende del registro: el corazón no puede quedarse inerte.

    Es la comprobación que faltaba. Las otras siete miran la coherencia de lo ya
    escrito, así que un registro dormido -o cerrado entero- las deja a todas en
    verde; esta mira el criterio en sí.
    """
    sembrados = [
        _SEMBRADO_SUELTO,
        _SEMBRADO_SEGUIDO,
        _SEMBRADO_CERRADO,
        _SEMBRADO_CON_INCIDENCIA_NO_NUMERICA,
    ]
    assert _abiertos_sin_incidencia(sembrados) == ["S-1", "S-4"], (
        "el criterio del corazón ya no distingue el defecto abierto que nadie "
        "sigue: tiene que cazar S-1 (sin incidencia) y S-4 (incidencia que no "
        "es un número), y dejar pasar S-2 (seguido) y S-3 (cerrado)."
    )
    assert _abiertos_sin_incidencia([]) == [], (
        "sobre nada, el criterio no puede inventarse un suelto"
    )


def test_todo_defecto_cerrado_dice_que_commit_lo_cerro() -> None:
    sin_commit = [
        defecto["id"]
        for defecto in _defectos()
        if defecto["estado"] == "cerrado" and not isinstance(defecto.get("cerrado_por"), str)
    ]
    assert sin_commit == [], f"defectos cerrados sin el commit que los cerró: {sin_commit}"


@pytest.mark.parametrize("defecto", _defectos(), ids=lambda d: str(d["id"]))
def test_los_ficheros_que_cita_un_defecto_existen(defecto: dict[str, Any]) -> None:
    """Un defecto que apunta a un fichero borrado ya no se puede ni comprobar."""
    ausentes = [ruta for ruta in defecto["ficheros"] if not (RAIZ / ruta).exists()]
    assert ausentes == [], (
        f"{defecto['id']} cita ficheros que ya no existen: {ausentes}. "
        "Si el código se movió, actualiza el registro; si el defecto ya no aplica, ciérralo."
    )


# Un defecto que ya existe no puede DESAPARECER del registro: se cierra, no se
# borra. Sin esto, la forma más fácil de poner el registro en verde sería
# borrar la fila incómoda, que es exactamente el fallo que esta prueba viene a
# impedir. Fijados por nombre, igual que `DUPLICADO_HISTORICO` en
# `test_registro_de_decisiones.py`.
#
# Añadir un defecto nuevo NO obliga a tocar esta lista. Borrar uno viejo sí, y
# ahí es donde toca pararse a pensar en vez de teclear.
IDS_QUE_NO_PUEDEN_DESAPARECER = frozenset(
    {"H-1", "H-2", "H-3", "H-4", "H-5", "H-6", "H-7", "H-8", "H-9", "H-10", "H-11", "H-12"}
)


def test_ningun_defecto_conocido_desaparece_del_registro() -> None:
    presentes = {defecto["id"] for defecto in _defectos()}
    desaparecidos = sorted(IDS_QUE_NO_PUEDEN_DESAPARECER - presentes)
    assert desaparecidos == [], (
        f"defectos borrados del registro en vez de cerrados: {desaparecidos}. "
        "Un defecto se cierra con `estado: cerrado` y el commit que lo cerró; "
        "borrarlo hace que se olvide, que es justo lo que este registro impide."
    )


# --- El defecto que sigue abierto aunque su arreglo ya está en main ----------
#
# Dos veces en doce horas: H-11 y H-13 se arreglaron, se fusionaron, y su
# entrada del registro se quedó en `abierto` porque cerrarla dependía de que
# alguien se acordara. La segunda la cometió la misma sesión que había
# corregido la primera, y sobre un defecto que ella misma había registrado.
#
# Esta guarda no depende de la red: mira el historial de git. Reconoce un
# arreglo por la convención que este repositorio ya usa —el asunto del commit
# empieza por el identificador del defecto y dos puntos, como
# `H-13: el motor deja de necesitar el árbol de código`—.
#
# **Su alcance, medido antes de fijarlo (23-08-2026):** sobre los 14 defectos
# del registro, la señal produce **cero falsos positivos**, y habría cazado los
# dos casos reales. Pero solo 4 de los 13 cerrados tienen un commit que siga esa
# convención: los otros nueve se arreglaron con asuntos que no empiezan por el
# identificador. Es decir, **precisión alta y alcance corto**: esta guarda no
# ve el arreglo que no se nombra así, y eso es una limitación conocida, no un
# descuido. Se prefiere de largo a una señal más laxa: un falso positivo aquí
# empujaría a cerrar un defecto que sigue vivo, que es peor que no avisar.

_ASUNTO_DE_ARREGLO = re.compile(r"^(?P<id>H-\d+)\s*:", re.IGNORECASE)

# Asuntos REALES de `main`, tomados el 23-08-2026. Los dos primeros arreglan un
# defecto; los dos últimos nombran un identificador SIN arreglarlo, y son el
# falso positivo que descartó el criterio ingenuo (ADR-080).
ASUNTOS_QUE_SON_ARREGLO = (
    "H-13: el motor deja de necesitar el árbol de código para ejecutar la proyección (#283)",
    "H-11: diario del despachador durable, hermano de ADR-061 (#248)",
)
ASUNTOS_QUE_SOLO_NOMBRAN = (
    "Cerrar H-13 en el registro y dar de alta H-14 (#286)",
    "El registro de defectos decía abierto lo que se cerró, y añade H-13 (#271)",
)

# La historia de `main` no siempre está a mano, y el 23-08-2026 se midió dónde
# no lo está: Quality clona con `actions/checkout` y la profundidad por defecto,
# así que en una PR el árbol NO tiene `origin/main` y `git log origin/main` sale
# con código 128 (ejecución 32633782403, dos pruebas rojas).
#
# Ahí esta guarda se salta y dice por qué. Lo que NO hace es apañarse con lo que
# haya: caer a `HEAD` leería una historia de UN commit, no encontraría ningún
# arreglo, y pasaría en verde sin haber comprobado nada. Un verde falso es peor
# que un salto declarado, y este repositorio ya lo ha pagado tres veces.
#
# Por el mismo motivo se salta cuando la referencia resuelve pero no deja ver
# ni un arreglo: en un `push` a `main` el clon por defecto trae un solo commit,
# y «no veo ninguno» sería indistinguible de «no hay ninguno».
_REFERENCIAS_DE_MAIN = ("origin/main", "main")

_SIN_HISTORIA = (
    "este árbol no deja leer la historia de `main`, así que no hay dónde buscar "
    "el arreglo: {motivo}. Pasa en Quality, que clona con la profundidad por "
    "defecto; ADR-080 lo explica y dice qué haría falta para que corra ahí. "
    "El criterio en sí sigue comprobado por "
    "test_el_criterio_reconoce_el_arreglo_y_no_la_mera_mencion, que no depende "
    "del entorno."
)


def _referencia_de_main() -> str | None:
    """La primera referencia a `main` que resuelva en este árbol, o None."""
    for referencia in _REFERENCIAS_DE_MAIN:
        hecho = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", referencia],
            capture_output=True,
            text=True,
            check=False,
            cwd=RAIZ,
        )
        if hecho.returncode == 0:
            return referencia
    return None


def _asuntos_de(referencia: str) -> list[str]:
    salida = subprocess.run(
        ["git", "log", referencia, "--format=%s"],
        capture_output=True,
        text=True,
        check=True,
        cwd=RAIZ,
    ).stdout
    return [linea for linea in salida.splitlines() if linea]


def _arreglos_en(asuntos: list[str]) -> dict[str, list[str]]:
    """Identificador -> asuntos que dicen arreglarlo."""
    encontrados: dict[str, list[str]] = {}
    for asunto in asuntos:
        casa = _ASUNTO_DE_ARREGLO.match(asunto)
        if casa:
            encontrados.setdefault(casa.group("id").upper(), []).append(asunto)
    return encontrados


def _arreglos_ya_en_main() -> tuple[dict[str, list[str]], str]:
    """Los arreglos visibles en `main`, o un motivo de por qué no se pueden ver."""
    referencia = _referencia_de_main()
    if referencia is None:
        return {}, "no resuelve ninguna de " + " ni ".join(_REFERENCIAS_DE_MAIN)
    arreglos = _arreglos_en(_asuntos_de(referencia))
    if not arreglos:
        return {}, f"{referencia} resuelve pero no deja ver ni un commit `H-N: ...`"
    return arreglos, ""


def test_el_criterio_reconoce_el_arreglo_y_no_la_mera_mencion() -> None:
    """Anti-vacua que NO depende del entorno: el criterio no puede quedarse inerte.

    La guarda de abajo se salta donde no hay historia de `main`, y un criterio
    roto ahí no se notaría. Esta corre siempre, y sobre asuntos reales del
    repositorio: si alguien deja la expresión sin morder, o la afloja hasta
    tragarse una simple mención, se rompe aquí.
    """
    for asunto in ASUNTOS_QUE_SON_ARREGLO:
        assert _arreglos_en([asunto]), f"el criterio ya no reconoce un arreglo: {asunto!r}"

    for asunto in ASUNTOS_QUE_SOLO_NOMBRAN:
        assert not _arreglos_en([asunto]), (
            f"el criterio confunde nombrar con arreglar: {asunto!r}. Ese es "
            "exactamente el falso positivo que ADR-080 descartó midiendo."
        )


def test_ningun_defecto_abierto_tiene_ya_su_arreglo_en_main() -> None:
    """Un defecto arreglado y fusionado no puede seguir marcado como abierto."""
    arreglos, motivo = _arreglos_ya_en_main()
    if motivo:
        pytest.skip(_SIN_HISTORIA.format(motivo=motivo))

    contradicciones = [
        (defecto["id"], arreglos[defecto["id"].upper()])
        for defecto in _defectos()
        if defecto.get("estado") == "abierto" and defecto["id"].upper() in arreglos
    ]
    assert not contradicciones, "\n".join(
        f"{hid} sigue como `abierto` pero main ya contiene su arreglo: "
        f"{asuntos}. Ciérralo con su `cerrado_por`, o renombra el commit si no "
        "era el arreglo."
        for hid, asuntos in contradicciones
    )


# --- La mitad que faltaba: ¿se ESCRIBIÓ lo que pasó? -------------------------
#
# Las ocho comprobaciones de arriba verifican la COHERENCIA DE LO YA ESCRITO.
# Ninguna pregunta si lo que pasó llegó a escribirse, y por eso el registro
# estuvo doce días y 61 ADR en verde estando dormido: la última entrada es del
# 31-08-2026 (`5cc3f18`) y entre medias entraron a `main` los ADR 116 a 180.
#
# El arreglo es el de ADR-179, aplicado aquí: **el inventario se DERIVA del
# repositorio y lo escrito a mano es lo que se RESTA**. A una lista de inclusión
# le puede faltar una entrada y sigue verde; a una de exclusión que sobra se la
# ve.
#
# La señal derivada, elegida midiendo tres candidatas (ADR-182): **un ADR que
# declara una lección con `familia:` corrige un defecto**. No es un criterio
# inventado aquí, es el que ADR-174 ya fijó -una lección se escribe *solo si sin
# ella alguien repetiría el error*-, lo emite el propio árbol y lo lee
# `sirius_engine.memoria.leer_leccion`, que su propia batería comprueba.
#
# Y no depende de git, a propósito: la comprobación de más arriba que sí depende
# (`test_ningun_defecto_abierto_tiene_ya_su_arreglo_en_main`) no llega a correr
# en Quality, que clona superficialmente. Esta lee dos ficheros del árbol.

DECISIONES = RAIZ / "docs" / "decisions"
_NOMBRE_DE_ADR = re.compile(r"^ADR-(\d{3})-")

#: Cómo una entrada del registro dice qué ADR corrigió su defecto. Es un campo
#: OPCIONAL: las 32 entradas anteriores al 13-09-2026 no lo traen y no se
#: reescriben -el registro conserva todo defecto pasado tal como se escribió-.
CAMPO_ADR = "adr"


def _adr_que_declaran_un_defecto() -> dict[int, str]:
    """Número de ADR -> familia de la lección que declara. EL inventario derivado.

    Se salta los anteriores a ``PRIMER_ADR_CON_LECCION`` porque ahí no hay
    bloque que leer: ADR-174 los eximió a propósito, y rellenarlos hoy sería
    escribir de memoria lo que en su día no se capturó.

    Con dos ficheros que compartan número -este registro tiene un `ADR-016`
    duplicado histórico- gana el primero por orden alfabético; los duplicados
    conocidos son muy anteriores a 174 y no declaran lección.
    """
    inventario: dict[int, str] = {}
    for ruta in sorted(DECISIONES.glob("ADR-*.md")):
        casa = _NOMBRE_DE_ADR.match(ruta.name)
        if casa is None or int(casa.group(1)) < PRIMER_ADR_CON_LECCION:
            continue
        leccion = leer_leccion(ruta.read_text(encoding="utf-8").splitlines())
        if leccion is not None and leccion.familia:
            inventario.setdefault(int(casa.group(1)), leccion.familia)
    return inventario


def _acuses_del_registro() -> dict[int, list[str]]:
    """Número de ADR -> los defectos del registro que dicen haberlo acusado."""
    acuses: dict[int, list[str]] = {}
    for defecto in _defectos():
        numero = defecto.get(CAMPO_ADR)
        if isinstance(numero, int) and not isinstance(numero, bool):
            acuses.setdefault(numero, []).append(defecto["id"])
    return acuses


def _numeros_de_adr_del_arbol() -> set[int]:
    return {
        int(casa.group(1))
        for ruta in DECISIONES.glob("ADR-*.md")
        if (casa := _NOMBRE_DE_ADR.match(ruta.name)) is not None
    }


# Lo escrito a mano, y es lo que se RESTA: los ADR que declaran un defecto y no
# tienen entrada en el registro, cada uno con su razón al lado. Añadir un ADR
# aquí es un gesto visible en el diff; olvidarse de él pone la batería en rojo.
#
# Los cinco de abajo son la sequía misma, medida el 13-09-2026 sobre `673b2f4`:
# son los ÚNICOS ADR de `main` que declaran lección -la obligación empezó en el
# 174, dos días antes- y ninguno dejó entrada. No se registran ahora por la
# misma razón por la que ADR-174 no rellenó los anteriores a él: hacerlo sería
# escribir hoy, de memoria, lo que en su día no se capturó. Y hay un impedimento
# medido además del principio: su `cerrado_por` es un commit de `main` que este
# árbol no tiene -Quality y este runner clonan con profundidad 1,
# `git rev-list --count HEAD` → `1`-, así que ni siquiera se puede citar.
SIN_DEFECTO_REGISTRADO: dict[int, str] = {
    174: (
        "la sequía que este mecanismo cierra: ADR-174 midió que los dos sitios de "
        "lecciones llevaban 48 ADR sin una entrada y dejó el registro de defectos "
        "FUERA DE ALCANCE por escrito. Registrar hoy su propio defecto sería "
        "reconstruirlo de memoria, que es lo que ese ADR declinó hacer (13-09-2026)"
    ),
    175: (
        "novena aparición de `pieza-sin-lector`, corregida y fusionada antes de que "
        "existiera esta guarda; su commit de cierre no está en este árbol "
        "(13-09-2026)"
    ),
    176: (
        "`plan-que-hay-que-terminar-de-una-sentada`, corregida y fusionada antes de "
        "que existiera esta guarda; su commit de cierre no está en este árbol "
        "(13-09-2026)"
    ),
    179: (
        "segunda aparición de `regla-que-depende-de-que-alguien-se-acuerde`, "
        "fusionada en `673b2f4` la madrugada del 13-09-2026, horas antes de esta "
        "guarda; su ADR declara las 46 piezas sin llamante que destapó y esas son "
        "deuda de otras incidencias, no defectos de este registro"
    ),
    180: (
        "`medir-lo-que-se-tiene-en-vez-de-lo-que-hay`, corregida y fusionada antes "
        "de que existiera esta guarda; su commit de cierre no está en este árbol "
        "(13-09-2026)"
    ),
}


def test_el_inventario_de_adr_con_defecto_se_deriva_y_no_esta_vacio() -> None:
    """Anti-vacua del inventario: sin ADR que mirar, todo lo de abajo pasaría solo.

    Y no basta con que no esté vacío: se fijan dos ADR que declaran lección de
    verdad, para que aflojar la derivación -leer otro encabezado, dejar de ver
    `familia:`- no se salde con un inventario pequeño pero no vacío.
    """
    inventario = _adr_que_declaran_un_defecto()
    assert inventario, (
        "ningún ADR del árbol declara una lección con `familia:`; o la "
        "derivación se rompió, o `docs/decisions/` no es lo que esta guarda cree"
    )
    for numero in (174, 179):
        assert numero in inventario, (
            f"ADR-{numero} declara una lección con familia y la derivación no la "
            "ve: el inventario dejó de derivarse de lo que hay escrito"
        )


def test_todo_adr_que_declara_un_defecto_deja_su_entrada_en_el_registro() -> None:
    """La comprobación que faltaba: lo que pasó tiene que estar escrito.

    Un ADR que declara una lección declara, por la definición de ADR-174, que
    algo mordió. Si eso no llega al registro, el registro se duerme y ninguna de
    las otras comprobaciones lo nota.
    """
    acusados = _acuses_del_registro()
    sin_escribir = sorted(
        numero
        for numero in _adr_que_declaran_un_defecto()
        if numero not in acusados and numero not in SIN_DEFECTO_REGISTRADO
    )
    assert sin_escribir == [], (
        f"estos ADR declaran una lección -o sea, un defecto que mordió- y el "
        f"registro no dice nada de ellos: {[f'ADR-{n}' for n in sin_escribir]}. "
        f"Da de alta el defecto en {REGISTRO.name} con `{CAMPO_ADR}: <número>`, o "
        "declara la excepción en SIN_DEFECTO_REGISTRADO con su razón escrita."
    )


@pytest.mark.parametrize("numero", sorted(SIN_DEFECTO_REGISTRADO), ids=lambda n: f"ADR-{n}")
def test_cada_excepcion_sigue_correspondiendo_a_un_adr_que_declara_un_defecto(
    numero: int,
) -> None:
    """Una excepción que ya no señala nada es una excepción que hay que borrar."""
    assert numero in _numeros_de_adr_del_arbol(), (
        f"SIN_DEFECTO_REGISTRADO exime a ADR-{numero} y ese ADR no está en "
        f"{DECISIONES.name}: bórralo de la lista"
    )
    assert numero in _adr_que_declaran_un_defecto(), (
        f"SIN_DEFECTO_REGISTRADO exime a ADR-{numero} y ese ADR ya no declara "
        "ninguna lección con `familia:`: no hay defecto que eximir, bórralo"
    )


@pytest.mark.parametrize("numero", sorted(SIN_DEFECTO_REGISTRADO), ids=lambda n: f"ADR-{n}")
def test_ninguna_excepcion_sobra(numero: int) -> None:
    """En cuanto el defecto se escribe, la excepción estorba y hay que quitarla.

    Es el cierre que impide que la lista de exclusión crezca y se quede: una
    excepción y una entrada del registro para el mismo ADR se contradicen.
    """
    acusado_por = _acuses_del_registro().get(numero, [])
    assert not acusado_por, (
        f"ADR-{numero} está exento en SIN_DEFECTO_REGISTRADO y el registro ya lo "
        f"acusa en {acusado_por}: la excepción sobra, bórrala"
    )


@pytest.mark.parametrize("numero", sorted(SIN_DEFECTO_REGISTRADO), ids=lambda n: f"ADR-{n}")
def test_cada_excepcion_declara_su_razon(numero: int) -> None:
    """Una excepción sin razón escrita es un agujero con permiso."""
    razon = SIN_DEFECTO_REGISTRADO[numero].strip()
    assert len(razon) >= 40, (
        f"ADR-{numero} está exento sin decir por qué (razón: {razon!r}). La razón "
        "es lo único que distingue una excepción medida de un agujero."
    )


def test_el_adr_que_un_defecto_acusa_existe_de_verdad() -> None:
    """Coherencia del campo nuevo: `adr: 999` no vale de acuse."""
    del_arbol = _numeros_de_adr_del_arbol()
    inventados = sorted(numero for numero in _acuses_del_registro() if numero not in del_arbol)
    assert inventados == [], (
        "defectos que dicen haber sido corregidos por un ADR que no existe: "
        f"{[f'ADR-{n}' for n in inventados]}"
    )
    mal_escrito = [
        defecto["id"]
        for defecto in _defectos()
        if CAMPO_ADR in defecto
        and not (isinstance(defecto[CAMPO_ADR], int) and not isinstance(defecto[CAMPO_ADR], bool))
    ]
    assert mal_escrito == [], (
        f"`{CAMPO_ADR}` tiene que ser el número del ADR, y en {mal_escrito} no lo es"
    )


def test_al_menos_un_defecto_acusa_el_adr_que_lo_corrigio() -> None:
    """Anti-vacua del enlace: eximirlo todo dejaría el mecanismo dormido otra vez.

    Sin esto, la salida fácil ante un rojo sería añadir una línea a
    SIN_DEFECTO_REGISTRADO hasta que la lista de exclusión cubriera el
    inventario entero, y el registro volvería a estar donde estaba: verde y
    vacío de novedades.
    """
    assert _acuses_del_registro(), (
        f"ninguna entrada de {REGISTRO.name} declara el ADR que la corrigió: el "
        f"enlace `{CAMPO_ADR}` no lo usa nadie y esta guarda no está comprobando nada"
    )
