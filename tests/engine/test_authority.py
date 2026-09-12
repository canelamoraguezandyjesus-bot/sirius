"""autoridad_de_clase: función total sobre WorkItemClass (contrato §11.1, ADR-041).

D1c (incidencia #276, contrato §11.3) añade el segundo término: la tabla
estática más lo que diga un registro fechado de conmutaciones
(:class:`EntradaConmutacion`). Las pruebas de esta segunda mitad viven en la
sección propia más abajo; las de la tabla estática, arriba, no cambian -es
exactamente la garantía que este bloque no puede romper.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius_engine.domain import authority
from sirius_engine.domain.authority import (
    CLASES_CON_VIA_GITHUB,
    CLASES_SIN_VIA_GITHUB,
    Autoridad,
    EntradaConmutacion,
    autoridad_de_clase,
    formatear_entrada_conmutacion,
    parsear_entrada_conmutacion,
)
from sirius_engine.domain.work_item import WorkItemClass

# Hasta ADR-177 estas dos tuplas ponían DOCUMENTACION e INVESTIGACION del lado
# MOTOR: fijaban la copia de la tabla, no la relación con la vía GitHub, y por
# eso el defecto que ADR-177 corrige pasó dos semanas en verde.
_CLASES_MOTOR = (
    WorkItemClass.CONVERSACION_NO_APLICA,
    WorkItemClass.CONSULTA_LARGA,
    WorkItemClass.MIXTA,
)
_CLASES_INCIDENCIA = (
    WorkItemClass.PROGRAMACION,
    WorkItemClass.AUDITORIA,
    WorkItemClass.DOCUMENTACION,
    WorkItemClass.INVESTIGACION,
)


def _instante(dia: int = 1) -> datetime:
    return datetime(2026, 8, dia, tzinfo=UTC)


@pytest.mark.parametrize("clase", _CLASES_MOTOR)
def test_clases_nativas_sin_proyeccion_github_son_autoridad_motor(clase: WorkItemClass) -> None:
    assert autoridad_de_clase(clase) is Autoridad.MOTOR


@pytest.mark.parametrize("clase", _CLASES_INCIDENCIA)
def test_clases_con_proyeccion_github_son_autoridad_incidencia(clase: WorkItemClass) -> None:
    assert autoridad_de_clase(clase) is Autoridad.INCIDENCIA


def test_ninguna_clase_de_workitemclass_se_queda_sin_autoridad() -> None:
    """Función total: sin huecos (requisito 'un WorkItem nace siempre con autoridad')."""
    for clase in WorkItemClass:
        assert autoridad_de_clase(clase) in (Autoridad.MOTOR, Autoridad.INCIDENCIA)


# --- D1c: el registro de conmutaciones, segundo término de la función -----


def test_ninguna_clase_se_queda_sin_autoridad_con_registro_no_vacio() -> None:
    """La misma totalidad, ahora con un registro no vacío -para TODO WorkItemClass.

    Requisito 3 de la incidencia #276: una prueba recorre `WorkItemClass`
    entero y exige respuesta con y sin registro.
    """
    registro = (
        EntradaConmutacion(
            instante=_instante(),
            clase=WorkItemClass.PROGRAMACION,
            autoridad=Autoridad.MOTOR,
            motivo="conmutación de prueba",
        ),
    )
    for clase in WorkItemClass:
        assert autoridad_de_clase(clase, registro=registro) in (
            Autoridad.MOTOR,
            Autoridad.INCIDENCIA,
        )


def test_clase_sin_fila_en_la_tabla_revienta_explicito_con_y_sin_registro(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simula un `WorkItemClass` nuevo sin fila: sigue reventando, nunca asume nada.

    Requisito 3: la propiedad de ADR-041 -función total, sin valor por
    defecto, `KeyError` explícito- sobrevive al segundo término añadido por
    D1c, tanto si se pasa `registro` como si no.
    """
    tabla_incompleta = {
        clase: valor
        for clase, valor in authority._TABLA_AUTORIDAD.items()
        if clase is not WorkItemClass.PROGRAMACION
    }
    monkeypatch.setattr(authority, "_TABLA_AUTORIDAD", tabla_incompleta)

    with pytest.raises(KeyError):
        autoridad_de_clase(WorkItemClass.PROGRAMACION)

    registro_de_otra_clase = (
        EntradaConmutacion(
            instante=_instante(),
            clase=WorkItemClass.AUDITORIA,
            autoridad=Autoridad.MOTOR,
            motivo="otra clase, no protege a la que perdió su fila",
        ),
    )
    with pytest.raises(KeyError):
        autoridad_de_clase(WorkItemClass.PROGRAMACION, registro=registro_de_otra_clase)


@pytest.mark.parametrize("clase", _CLASES_MOTOR)
def test_una_clase_motor_no_puede_entrar_en_el_registro(clase: WorkItemClass) -> None:
    """Requisito 4: nacieron canónicas y no conmutan; intentarlo falla ruidosamente."""
    with pytest.raises(ValueError, match="no conmuta"):
        EntradaConmutacion(
            instante=_instante(),
            clase=clase,
            autoridad=Autoridad.INCIDENCIA,
            motivo="intento inválido",
        )


@pytest.mark.parametrize("clase", _CLASES_INCIDENCIA)
def test_una_clase_con_proyeccion_github_si_puede_entrar_en_el_registro(
    clase: WorkItemClass,
) -> None:
    entrada = EntradaConmutacion(
        instante=_instante(), clase=clase, autoridad=Autoridad.MOTOR, motivo="conmutación válida"
    )
    assert entrada.clase is clase


def test_sin_entradas_para_la_clase_el_registro_no_cambia_nada() -> None:
    """Un registro no vacío pero de OTRA clase no afecta a la consultada."""
    registro = (
        EntradaConmutacion(
            instante=_instante(),
            clase=WorkItemClass.AUDITORIA,
            autoridad=Autoridad.MOTOR,
            motivo="conmutación de AUDITORIA",
        ),
    )
    assert autoridad_de_clase(WorkItemClass.PROGRAMACION, registro=registro) is Autoridad.INCIDENCIA


def test_la_entrada_mas_reciente_manda() -> None:
    """Dos entradas de la misma clase: manda la de mayor `instante`, no el orden de la lista."""
    conmuta = EntradaConmutacion(
        instante=_instante(1),
        clase=WorkItemClass.PROGRAMACION,
        autoridad=Autoridad.MOTOR,
        motivo="conmuta",
    )
    revierte = EntradaConmutacion(
        instante=_instante(10),
        clase=WorkItemClass.PROGRAMACION,
        autoridad=Autoridad.INCIDENCIA,
        motivo="revierte",
    )
    assert (
        autoridad_de_clase(WorkItemClass.PROGRAMACION, registro=(revierte, conmuta))
        is Autoridad.INCIDENCIA
    )
    assert autoridad_de_clase(WorkItemClass.PROGRAMACION, registro=(conmuta,)) is Autoridad.MOTOR


def test_conmutaciones_con_el_mismo_instante_desempatan_por_orden_de_registro() -> None:
    """Mismo `instante`: gana la añadida después al registro, no la primera de la lista.

    Reproduce CODEX-001: una reversión con el mismo instante que la
    conmutación anterior debe dejar la clase en INCIDENCIA, no en MOTOR -que
    es lo que `max()` sin desempate devolvía al conservar la primera entrada
    con el máximo `instante` empatado.
    """
    mismo_instante = _instante(1)
    conmuta = EntradaConmutacion(
        instante=mismo_instante,
        clase=WorkItemClass.PROGRAMACION,
        autoridad=Autoridad.MOTOR,
        motivo="conmuta",
    )
    revierte = EntradaConmutacion(
        instante=mismo_instante,
        clase=WorkItemClass.PROGRAMACION,
        autoridad=Autoridad.INCIDENCIA,
        motivo="revierte con el mismo instante, añadida después",
    )
    assert (
        autoridad_de_clase(WorkItemClass.PROGRAMACION, registro=(conmuta, revierte))
        is Autoridad.INCIDENCIA
    )


def test_formatear_y_parsear_una_entrada_es_la_identidad() -> None:
    entrada = EntradaConmutacion(
        instante=_instante(3),
        clase=WorkItemClass.AUDITORIA,
        autoridad=Autoridad.INCIDENCIA,
        motivo="divergencia en el eje fase",
    )
    assert parsear_entrada_conmutacion(formatear_entrada_conmutacion(entrada)) == entrada


def test_formatear_es_deterministico() -> None:
    """Misma entrada, mismo texto exacto -condición del registro append-only (requisito 8)."""
    entrada = EntradaConmutacion(
        instante=_instante(3),
        clase=WorkItemClass.PROGRAMACION,
        autoridad=Autoridad.MOTOR,
        motivo="x",
    )
    assert formatear_entrada_conmutacion(entrada) == formatear_entrada_conmutacion(entrada)


# --- ADR-177: la autoridad se deriva de la vía GitHub, y el contrato se lee como dato ---


def test_la_autoridad_se_deriva_de_la_via_github_y_es_total() -> None:
    """La propiedad entera: con vía GitHub, INCIDENCIA; sin ella, MOTOR; y sin huecos."""
    assert CLASES_CON_VIA_GITHUB.isdisjoint(CLASES_SIN_VIA_GITHUB)
    assert frozenset(WorkItemClass) == CLASES_CON_VIA_GITHUB | CLASES_SIN_VIA_GITHUB, (
        "una clase de WorkItemClass no está declarada en ninguno de los dos lados: "
        "la función dejó de ser total"
    )
    for clase in WorkItemClass:
        esperada = Autoridad.INCIDENCIA if clase in CLASES_CON_VIA_GITHUB else Autoridad.MOTOR
        assert autoridad_de_clase(clase) is esperada, clase


def test_documentacion_e_investigacion_nacen_con_autoridad_incidencia() -> None:
    """El defecto de ADR-177, con sus dos clases exactas.

    Están en la vía GitHub desde ADR-088 y ADR-099 -quince encargos reales
    corrieron enteros en ella- y la tabla de autoridad seguía diciendo MOTOR.
    """
    assert autoridad_de_clase(WorkItemClass.DOCUMENTACION) is Autoridad.INCIDENCIA
    assert autoridad_de_clase(WorkItemClass.INVESTIGACION) is Autoridad.INCIDENCIA


def test_la_via_github_del_despachador_es_exactamente_la_de_la_autoridad() -> None:
    """La guarda que faltó dos semanas: las dos tablas hablan del mismo hecho.

    `TABLA_ACTIVACION` decide qué clases se despachan a GitHub; la autoridad se
    deriva de ese mismo hecho. Si alguien añade una clase a una y no a la
    otra, esto cae, que es justo lo que ADR-088 y ADR-099 hicieron sin que
    nada cayera.
    """
    from sirius_engine.dispatcher import TABLA_ACTIVACION

    assert set(TABLA_ACTIVACION) == set(CLASES_CON_VIA_GITHUB)


_CONTRATO = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "implementation"
    / "AUTOMATION_OPERATING_CONTRACT.md"
)

#: Qué fila de la tabla §11.1 del contrato es qué clase del motor. Las filas
#: que no están aquí no tienen clase en el motor, y se comprueba que sean
#: exactamente las esperadas para que un cambio en la tabla no pase en vacío.
_FILAS_CON_CLASE: dict[str, WorkItemClass] = {
    "conversación / exploración / consulta": WorkItemClass.CONVERSACION_NO_APLICA,
    "investigación": WorkItemClass.INVESTIGACION,
    "documental publicada (PR en el repo)": WorkItemClass.DOCUMENTACION,
    "programación": WorkItemClass.PROGRAMACION,
    "auditoría": WorkItemClass.AUDITORIA,
}
_FILAS_SIN_CLASE = frozenset({"documental no publicada", "reparación / espera / cancelación"})


def _filas_de_la_tabla(texto: str) -> dict[str, str]:
    """{clase de trabajo: la fila entera}, para lo que no cabe en una celda concreta."""
    seccion = texto.split("### 11.1 Tabla de autoridad", 1)[1].split("### 11.2", 1)[0]
    filas: dict[str, str] = {}
    for linea in seccion.splitlines():
        if not linea.startswith("|") or set(linea) <= set("-| "):
            continue
        primera = linea.strip().strip("|").split("|")[0].strip()
        if primera and primera != "Clase de trabajo":
            filas[primera] = linea
    return filas


def _tabla_de_autoridad_del_contrato(texto: str) -> dict[str, tuple[str, str]]:
    """{clase de trabajo: (¿existe en la vía GitHub?, autoridad)}, tal como está escrita."""
    seccion = texto.split("### 11.1 Tabla de autoridad", 1)[1].split("### 11.2", 1)[0]
    filas: dict[str, tuple[str, str]] = {}
    for linea in seccion.splitlines():
        if not linea.startswith("|") or set(linea) <= set("-| "):
            continue
        celdas = [celda.strip() for celda in linea.strip().strip("|").split("|")]
        if len(celdas) < 3 or celdas[0] == "Clase de trabajo":
            continue
        filas[celdas[0]] = (celdas[1], celdas[2])
    return filas


def _existe_en_la_via_github(celda: str) -> bool:
    limpio = celda.replace("*", "").strip().lower()
    if limpio.startswith("sí"):
        return True
    if limpio.startswith("no"):
        return False
    raise AssertionError(f"la celda «¿Existe en la vía GitHub?» no empieza por sí/no: {celda!r}")


def _autoridad_escrita(celda: str) -> Autoridad:
    limpio = celda.replace("*", "").strip().lower()
    palabra = re.match(r"[a-záéíóúñ]+", limpio)
    assert palabra is not None, f"la celda de autoridad no empieza por una palabra: {celda!r}"
    return Autoridad(palabra.group(0))


def test_la_tabla_del_contrato_y_el_codigo_dicen_lo_mismo() -> None:
    """El contrato §11.1 leído como dato, fila a fila, contra el código.

    Es lo que hace imposible -no improbable- la divergencia que ADR-177
    encontró: la tabla del contrato decía «documental publicada: sí,
    incidencia» y el código decía MOTOR, y las dos cosas convivieron desde
    ADR-088 sin que nada las enfrentara.
    """
    filas = _tabla_de_autoridad_del_contrato(_CONTRATO.read_text(encoding="utf-8"))

    # Anti-vacua: la tabla entera está cartografiada, fila por fila.
    assert set(filas) == set(_FILAS_CON_CLASE) | _FILAS_SIN_CLASE, sorted(filas)
    # Toda clase con vía GitHub tiene su fila; si mañana entra una nueva, hay
    # que escribir su fila en el contrato ANTES de poder fusionar.
    assert frozenset(_FILAS_CON_CLASE.values()) >= CLASES_CON_VIA_GITHUB

    for etiqueta, clase in _FILAS_CON_CLASE.items():
        via_github, autoridad = filas[etiqueta]
        assert _existe_en_la_via_github(via_github) == (clase in CLASES_CON_VIA_GITHUB), (
            f"§11.1 «{etiqueta}»: el contrato dice {via_github!r} y el código "
            f"{'sí' if clase in CLASES_CON_VIA_GITHUB else 'no'}"
        )
        assert _autoridad_escrita(autoridad) is autoridad_de_clase(clase), (
            f"§11.1 «{etiqueta}»: el contrato dice {autoridad!r} y el código "
            f"{autoridad_de_clase(clase).value}"
        )


def test_el_lector_de_la_tabla_del_contrato_distingue_una_fila_cambiada() -> None:
    """Mutación del contrato: un «no» donde el código dice sí no pasa desapercibido."""
    texto = _CONTRATO.read_text(encoding="utf-8")
    fila = "| documental publicada (PR en el repo) | sí"
    assert texto.count(fila) == 1
    filas = _tabla_de_autoridad_del_contrato(
        texto.replace(fila, "| documental publicada (PR en el repo) | no", 1)
    )
    assert _existe_en_la_via_github(filas["documental publicada (PR en el repo)"][0]) is False
    # Y con el texto real, dice sí.
    assert _existe_en_la_via_github(
        _tabla_de_autoridad_del_contrato(texto)["documental publicada (PR en el repo)"][0]
    )


# --- ADR-177, primera ronda de revisión: la retirada de un carril, leída del dato ---
#
# La primera versión de ADR-177 escribió que la retirada de los carriles de
# investigación y auditoría estaba PENDIENTE y que consistía en quitar esas
# clases de `TABLA_ACTIVACION`. Las dos cosas eran falsas, y la segunda es lo
# CONTRARIO de lo que el contrato manda (§13.2). El error no salió de la nada:
# las dos filas de §11.1 decían «EJECUCIÓN PENDIENTE» mientras §13.2 decía que
# ADR-163 la había ejecutado. El contrato se contradecía a sí mismo, y el ADR
# copió la mitad equivocada.
#
# Misma familia que el defecto que ADR-177 arregla -dos sitios que hablan del
# mismo hecho y divergen-, así que se cierra igual: derivando del dato que el
# propio contrato declara fuente de verdad.


def test_una_clase_con_el_carril_retirado_sigue_en_la_via_github() -> None:
    """§13.2, con sus palabras: `TABLA_ACTIVACION` **sigue conteniendo** esas clases.

    Es la guarda contra el cambio que el ADR equivocado invitaba a hacer.
    Retirar un carril y quitar la clase de la vía GitHub no son lo mismo: lo
    primero está hecho, lo segundo el contrato lo prohíbe, porque dejaría la
    retirada sin vuelta atrás y al registro describiendo una clase que el
    contrato declararía inexistente.
    """
    from sirius_engine.carriles_retirados import carriles_retirados
    from sirius_engine.dispatcher import TABLA_ACTIVACION

    retiradas = {WorkItemClass(valor) for valor in carriles_retirados()}
    assert retiradas, "el registro de carriles retirados está vacío: esta prueba no mide nada"
    for clase in retiradas:
        assert clase in CLASES_CON_VIA_GITHUB, clase
        assert clase in TABLA_ACTIVACION, clase


def test_la_tabla_del_contrato_no_da_por_pendiente_una_retirada_ya_ejecutada() -> None:
    """El texto de la fila, contra el registro de carriles que §13.2 declara fuente de verdad."""
    from sirius_engine.carriles_retirados import carriles_retirados

    filas = _filas_de_la_tabla(_CONTRATO.read_text(encoding="utf-8"))
    por_clase = {clase: etiqueta for etiqueta, clase in _FILAS_CON_CLASE.items()}
    retiradas = {WorkItemClass(valor) for valor in carriles_retirados()}
    assert retiradas, "el registro de carriles retirados está vacío: esta prueba no mide nada"

    for clase in retiradas:
        etiqueta = por_clase[clase]
        fila = filas[etiqueta]
        assert "RETIRAD" in fila.upper(), (
            f"§11.1 «{etiqueta}»: el carril está retirado en carriles_retirados.json y la "
            "fila no lo dice"
        )
        assert "PENDIENTE" not in fila.upper(), (
            f"§11.1 «{etiqueta}»: la fila da la retirada por pendiente y "
            "carriles_retirados.json dice que está ejecutada (§13.2)"
        )
