"""El verificador de proyección (D1a, incidencia #265).

La prueba de terminado de este bloque no es "está en verde": es "se ha visto
ponerse rojo con una divergencia sembrada" (nota de arranque de la
incidencia). Por eso la estructura de este fichero es, en este orden:

1. Cada eje declarado (:data:`EJES_DECLARADOS`) tiene su caso rojo -y la
   prueba que lo exige recorre la lista declarada, no una copia escrita a
   mano (requisito 1).
2. Ningún eje es ``f(x) == f(x)``: cada uno tiene un par que diverge y un par
   que coincide (requisito 2).
3. Las cuatro ventanas no comparables, cada una con su caso, cada una
   produciendo ``NO_COMPARABLE`` -nunca ``COINCIDE``- con su motivo
   (requisito 3).
4. La ventana de tolerancia se deriva del YAML real, nunca escrita a mano
   (requisito 4).
5. Un día con ventanas no comparables no cuenta como verde (requisito 5).
6. Determinismo y ausencia de red (requisito 6).
7. La fidelidad de la proyección detecta un cuerpo publicado con otro
   ``work_id``, objetivo o alcance (requisito 7).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from sirius_engine.domain.mirror import MirroredWorkItem, OrigenLectura
from sirius_engine.domain.work_item import (
    WorkItem,
    WorkItemClass,
    WorkItemPhase,
    WorkItemState,
    create_work_item,
)
from sirius_engine.issue_body_parsing import CuerpoDeclarado
from sirius_engine.projection_verifier import (
    EJE_ESTADO,
    EJE_FASE,
    EJE_FIDELIDAD_PROYECCION,
    EJES_DECLARADOS,
    ContextoEjesDiarios,
    LineaRegistro,
    ResultadoEje,
    VeredictoEje,
    formatear_linea,
    ventana_tolerancia_etiqueta_maquina,
    verificar_despacho,
    verificar_dia,
    verificar_eje_estado,
    verificar_eje_fase,
    verificar_fidelidad_proyeccion,
)

_AHORA = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SIN_VENTANA = ContextoEjesDiarios()
#: Un valor de tolerancia fijo para las pruebas: no depende de leer el YAML
#: real, así que un cambio en `.github/workflows/*.yml` no puede volver
#: frágiles estas pruebas.
_TOLERANCIA = timedelta(minutes=170)


def _motor(**overrides: object) -> WorkItem:
    base = create_work_item(
        work_id="canelamoraguezandyjesus-bot/sirius#265",
        peticion_original="texto literal de la petición",
        objetivo="objetivo real del WorkItem",
        contexto_origen=("incidencia:265",),
        entregable="alcance real del WorkItem",
        criterio_terminado="criterio de terminado",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_AHORA,
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def _espejo(
    *, estado: WorkItemState | None, fase: WorkItemPhase | None, **overrides: object
) -> MirroredWorkItem:
    base = MirroredWorkItem(
        work_id="canelamoraguezandyjesus-bot/sirius#265",
        estado=estado,
        fase=fase,
        etiquetas=(),
        etiquetas_contradictorias=False,
        cerrada=False,
        pr_url=None,
        head_sha=None,
        rondas=(),
        veredictos=(),
        eventos_quality=(),
        fallos_quality_consecutivos=0,
        origen=OrigenLectura(fuente="test", leido_en=_AHORA),
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


# --- 1. Cada eje declarado tiene su caso rojo -------------------------------

#: Un generador de caso rojo por eje declarado. Si se añade un eje a
#: `EJES_DECLARADOS` sin sumar su entrada aquí, `test_cada_eje_declarado_...`
#: falla: un eje sin su caso rojo no cuenta como cobertura (requisito 1).
_CASOS_ROJOS: dict[str, object] = {
    EJE_FASE: lambda: verificar_eje_fase(motor=WorkItemPhase.REVISAR, espejo=WorkItemPhase.REPARAR),
    EJE_ESTADO: lambda: verificar_eje_estado(
        motor=WorkItemState.ACTIVE, espejo=WorkItemState.PAUSED
    ),
    EJE_FIDELIDAD_PROYECCION: lambda: verificar_fidelidad_proyeccion(
        despachado=_motor(),
        declarado=CuerpoDeclarado(
            work_id="otro-work-id", objetivo=_motor().objetivo, entregable=_motor().entregable
        ),
    ),
}


def test_cada_eje_declarado_tiene_su_caso_rojo() -> None:
    assert set(_CASOS_ROJOS) == set(EJES_DECLARADOS), (
        "un eje declarado sin caso rojo, o un caso rojo de un eje no declarado, "
        "no es cobertura verificada"
    )
    for eje in EJES_DECLARADOS:
        veredicto = _CASOS_ROJOS[eje]()  # type: ignore[operator]
        assert veredicto.resultado is ResultadoEje.DIVERGENCIA, (
            f"el caso rojo declarado para {eje!r} no dio DIVERGENCIA: no demuestra que sepa fallar"
        )


# --- 2. Ningún eje es f(x) == f(x) ------------------------------------------


def test_eje_fase_diverge_y_coincide() -> None:
    diverge = verificar_eje_fase(motor=WorkItemPhase.COMPROBAR, espejo=WorkItemPhase.REVISAR)
    coincide = verificar_eje_fase(motor=WorkItemPhase.COMPROBAR, espejo=WorkItemPhase.COMPROBAR)
    assert diverge.resultado is ResultadoEje.DIVERGENCIA
    assert coincide.resultado is ResultadoEje.COINCIDE
    assert coincide.motivo is None


def test_eje_estado_diverge_y_coincide() -> None:
    diverge = verificar_eje_estado(motor=WorkItemState.ACTIVE, espejo=WorkItemState.NEEDS_DECISION)
    coincide = verificar_eje_estado(motor=WorkItemState.ACTIVE, espejo=WorkItemState.ACTIVE)
    assert diverge.resultado is ResultadoEje.DIVERGENCIA
    assert coincide.resultado is ResultadoEje.COINCIDE
    assert coincide.motivo is None


def test_eje_fidelidad_diverge_y_coincide() -> None:
    motor = _motor()
    declarado_igual = CuerpoDeclarado(
        work_id=motor.work_id, objetivo=motor.objetivo, entregable=motor.entregable
    )
    declarado_distinto = CuerpoDeclarado(
        work_id=motor.work_id, objetivo="otro objetivo por completo", entregable=motor.entregable
    )
    coincide = verificar_fidelidad_proyeccion(despachado=motor, declarado=declarado_igual)
    diverge = verificar_fidelidad_proyeccion(despachado=motor, declarado=declarado_distinto)
    assert coincide.resultado is ResultadoEje.COINCIDE
    assert diverge.resultado is ResultadoEje.DIVERGENCIA
    assert "objetivo" in (diverge.motivo or "")


# --- 3. Las cuatro ventanas no comparables -----------------------------------


def test_ventana_1_despacho_reciente_no_es_divergencia() -> None:
    """Motor forzado ACTIVE, incidencia recién creada aún proyectando PLANNED.

    La edad de la etiqueta de máquina es conocida y reciente: solo una edad
    conocida y por debajo de la tolerancia abre esta ventana.
    """
    motor = _motor(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.PREPARAR)
    espejo = _espejo(estado=WorkItemState.PLANNED, fase=WorkItemPhase.PREPARAR)
    contexto = ContextoEjesDiarios(edad_etiqueta_maquina=timedelta(minutes=1))
    linea = verificar_dia(
        motor=motor,
        espejo=espejo,
        contexto=contexto,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
    )
    veredicto_estado = next(v for v in linea.veredictos if v.eje == EJE_ESTADO)
    assert veredicto_estado.resultado is ResultadoEje.NO_COMPARABLE
    assert "despacho" in (veredicto_estado.motivo or "")


def test_ventana_1_edad_desconocida_no_protege_el_despacho_indefinidamente() -> None:
    """Sin edad de etiqueta de máquina, no hay lectura que sostenga "reciente".

    Un despacho ACTIVE/PLANNED con `edad_etiqueta_maquina is None` no puede
    quedar `NO_COMPARABLE` para siempre: cae en comparación normal, igual
    que ya hace la ventana 4 cuando la edad se desconoce (ver
    `ContextoEjesDiarios`).
    """
    motor = _motor(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.PREPARAR)
    espejo = _espejo(estado=WorkItemState.PLANNED, fase=WorkItemPhase.PREPARAR)
    linea = verificar_dia(
        motor=motor,
        espejo=espejo,
        contexto=_SIN_VENTANA,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
    )
    veredicto_estado = next(v for v in linea.veredictos if v.eje == EJE_ESTADO)
    assert veredicto_estado.resultado is ResultadoEje.DIVERGENCIA


def test_ventana_1_despacho_reciente_vence_y_pasa_a_divergencia() -> None:
    """Superada la tolerancia, un despacho que sigue en PLANNED ya es un defecto real."""
    motor = _motor(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.PREPARAR)
    espejo = _espejo(estado=WorkItemState.PLANNED, fase=WorkItemPhase.PREPARAR)
    contexto = ContextoEjesDiarios(edad_etiqueta_maquina=timedelta(minutes=200))
    linea = verificar_dia(
        motor=motor,
        espejo=espejo,
        contexto=contexto,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
    )
    veredicto_estado = next(v for v in linea.veredictos if v.eje == EJE_ESTADO)
    assert veredicto_estado.resultado is ResultadoEje.DIVERGENCIA


@pytest.mark.parametrize(
    "estado_motor", [WorkItemState.WAITING, WorkItemState.PAUSED, WorkItemState.CANCELLED]
)
def test_ventana_2_estados_sin_etiqueta(estado_motor: WorkItemState) -> None:
    """El vocabulario de etiquetas no puede expresar WAITING/PAUSED/CANCELLED.

    La fase, en cambio, no la toca ni `pause()` ni el despacho asíncrono: si
    coincide con la última etiqueta de máquina vigente, sigue siendo
    comparable -esta ventana es de `estado`, no un apagón general del día.
    """
    motor = _motor(estado=estado_motor, fase=WorkItemPhase.REVISAR)
    espejo = _espejo(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.REVISAR)
    linea = verificar_dia(
        motor=motor,
        espejo=espejo,
        contexto=_SIN_VENTANA,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
    )
    veredicto_estado = next(v for v in linea.veredictos if v.eje == EJE_ESTADO)
    veredicto_fase = next(v for v in linea.veredictos if v.eje == EJE_FASE)
    assert veredicto_estado.resultado is ResultadoEje.NO_COMPARABLE
    assert estado_motor.value in (veredicto_estado.motivo or "")
    assert veredicto_fase.resultado is ResultadoEje.COINCIDE


def test_ventana_3_fusion_sin_ready_for_merge() -> None:
    """`sirius:completed` se aplica desde donde esté; el motor no llama entregado a eso."""
    motor = _motor(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.REVISAR)
    espejo = _espejo(estado=WorkItemState.DELIVERED, fase=WorkItemPhase.ENTREGAR)
    linea = verificar_dia(
        motor=motor,
        espejo=espejo,
        contexto=_SIN_VENTANA,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
    )
    for veredicto in linea.veredictos:
        assert veredicto.resultado is ResultadoEje.NO_COMPARABLE, veredicto
        assert "revisión" in (veredicto.motivo or "") or "ready-for-merge" in (
            veredicto.motivo or ""
        )


def test_ventana_4_residencia_normal_de_etiqueta_de_maquina() -> None:
    """Recién movida la etiqueta, el motor todavía no la ha observado: se tolera."""
    motor = _motor(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.COMPROBAR)
    espejo = _espejo(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.REPARAR)
    contexto = ContextoEjesDiarios(edad_etiqueta_maquina=timedelta(minutes=5))
    linea = verificar_dia(
        motor=motor,
        espejo=espejo,
        contexto=contexto,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
    )
    veredicto_fase = next(v for v in linea.veredictos if v.eje == EJE_FASE)
    assert veredicto_fase.resultado is ResultadoEje.NO_COMPARABLE
    assert "residencia" in (veredicto_fase.motivo or "")


def test_fuera_de_la_ventana_4_la_divergencia_es_real() -> None:
    """Pasada la tolerancia, el mismo desfase ya es un defecto, no una espera legítima."""
    motor = _motor(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.COMPROBAR)
    espejo = _espejo(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.REPARAR)
    contexto = ContextoEjesDiarios(edad_etiqueta_maquina=timedelta(minutes=200))
    linea = verificar_dia(
        motor=motor,
        espejo=espejo,
        contexto=contexto,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
    )
    veredicto_fase = next(v for v in linea.veredictos if v.eje == EJE_FASE)
    assert veredicto_fase.resultado is ResultadoEje.DIVERGENCIA


# --- 4. La ventana de tolerancia se deriva, nunca se escribe a mano ---------


def test_ventana_tolerancia_no_esta_escrita_a_mano(tmp_path: Path) -> None:
    """Cambiar el `timeout-minutes` del YAML cambia la ventana: no es una constante fija."""
    corto = tmp_path / "corto"
    corto.mkdir()
    (corto / "un-workflow.yml").write_text(
        yaml.safe_dump({"jobs": {"job": {"timeout-minutes": 10}}}), encoding="utf-8"
    )
    largo = tmp_path / "largo"
    largo.mkdir()
    (largo / "un-workflow.yml").write_text(
        yaml.safe_dump({"jobs": {"job": {"timeout-minutes": 90}}}), encoding="utf-8"
    )
    assert ventana_tolerancia_etiqueta_maquina(corto) == timedelta(minutes=20)
    assert ventana_tolerancia_etiqueta_maquina(largo) == timedelta(minutes=180)


def test_ventana_tolerancia_sin_topes_no_finge_un_numero(tmp_path: Path) -> None:
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    with pytest.raises(ValueError, match="no hay de qué derivar"):
        ventana_tolerancia_etiqueta_maquina(vacio)


def test_ventana_tolerancia_atada_al_yaml_real_del_repositorio() -> None:
    """Misma derivación que RECON-STUCK-006, leída de forma independiente aquí.

    Si esta prueba llamara a la propia función para calcular el valor
    esperado, sería comparar la función consigo misma (criterio de parada
    (a)): en vez de eso, recorre el YAML real con su propio bucle, igual que
    hace ``test_recon_stuck_006_...`` en ``test_sirius_reconcile.py``.
    """
    topes: list[int] = []
    for wf in sorted((_REPO_ROOT / ".github" / "workflows").glob("*.yml")):
        doc = yaml.safe_load(wf.read_text(encoding="utf-8"))
        for job in (doc.get("jobs") or {}).values():
            if isinstance(job, dict) and isinstance(job.get("timeout-minutes"), int):
                topes.append(job["timeout-minutes"])
    assert topes, "no encontré ningún tope de job: la comparación no mediría nada"
    esperado = timedelta(minutes=max(topes) * 2)
    assert ventana_tolerancia_etiqueta_maquina() == esperado


# --- 5. Un día con ventanas no comparables no cuenta como verde -------------


def test_linea_es_verde_solo_si_todos_los_ejes_coinciden() -> None:
    todo_coincide = LineaRegistro(
        instante=_AHORA,
        clase=WorkItemClass.PROGRAMACION,
        work_id="WI-1",
        veredictos=(
            VeredictoEje(eje=EJE_FASE, resultado=ResultadoEje.COINCIDE),
            VeredictoEje(eje=EJE_ESTADO, resultado=ResultadoEje.COINCIDE),
        ),
    )
    con_no_comparable = LineaRegistro(
        instante=_AHORA,
        clase=WorkItemClass.PROGRAMACION,
        work_id="WI-1",
        veredictos=(
            VeredictoEje(eje=EJE_FASE, resultado=ResultadoEje.COINCIDE),
            VeredictoEje(eje=EJE_ESTADO, resultado=ResultadoEje.NO_COMPARABLE, motivo="ventana X"),
        ),
    )
    con_divergencia = LineaRegistro(
        instante=_AHORA,
        clase=WorkItemClass.PROGRAMACION,
        work_id="WI-1",
        veredictos=(
            VeredictoEje(eje=EJE_FASE, resultado=ResultadoEje.DIVERGENCIA, motivo="difieren"),
            VeredictoEje(eje=EJE_ESTADO, resultado=ResultadoEje.COINCIDE),
        ),
    )
    assert todo_coincide.es_verde is True
    assert con_no_comparable.es_verde is False
    assert con_divergencia.es_verde is False


def test_veredicto_no_comparable_o_divergencia_exige_motivo() -> None:
    """Sin motivo, un NO_COMPARABLE o una DIVERGENCIA no serían auditables después."""
    with pytest.raises(ValueError, match="no es auditable"):
        VeredictoEje(eje=EJE_FASE, resultado=ResultadoEje.NO_COMPARABLE, motivo=None)
    with pytest.raises(ValueError, match="no es auditable"):
        VeredictoEje(eje=EJE_FASE, resultado=ResultadoEje.DIVERGENCIA, motivo=None)


# --- 6. Determinismo y ausencia de red --------------------------------------


def test_verificar_dia_es_determinista() -> None:
    motor = _motor(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.REVISAR)
    espejo = _espejo(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.REVISAR)
    contexto = ContextoEjesDiarios(edad_etiqueta_maquina=timedelta(minutes=1))
    primera = verificar_dia(
        motor=motor,
        espejo=espejo,
        contexto=contexto,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
    )
    segunda = verificar_dia(
        motor=motor,
        espejo=espejo,
        contexto=contexto,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
    )
    assert primera == segunda
    assert formatear_linea(primera) == formatear_linea(segunda)


def test_formatear_linea_incluye_instante_clase_work_id_y_ejes() -> None:
    linea = verificar_despacho(
        despachado=_motor(),
        declarado=CuerpoDeclarado(
            work_id=_motor().work_id, objetivo=_motor().objetivo, entregable=_motor().entregable
        ),
        instante=_AHORA,
    )
    texto = formatear_linea(linea)
    assert _AHORA.isoformat() in texto
    assert WorkItemClass.PROGRAMACION.value in texto
    assert _motor().work_id in texto
    assert EJE_FIDELIDAD_PROYECCION in texto


# --- 7. Fidelidad de la proyección: work_id, objetivo, alcance -------------


def test_fidelidad_detecta_otro_work_id() -> None:
    motor = _motor()
    declarado = CuerpoDeclarado(
        work_id="otro-repo#999", objetivo=motor.objetivo, entregable=motor.entregable
    )
    veredicto = verificar_fidelidad_proyeccion(despachado=motor, declarado=declarado)
    assert veredicto.resultado is ResultadoEje.DIVERGENCIA
    assert "work_id" in (veredicto.motivo or "")


def test_fidelidad_detecta_otro_objetivo() -> None:
    motor = _motor()
    declarado = CuerpoDeclarado(
        work_id=motor.work_id,
        objetivo="un objetivo que no es el real",
        entregable=motor.entregable,
    )
    veredicto = verificar_fidelidad_proyeccion(despachado=motor, declarado=declarado)
    assert veredicto.resultado is ResultadoEje.DIVERGENCIA
    assert "objetivo" in (veredicto.motivo or "")


def test_fidelidad_detecta_otro_alcance() -> None:
    motor = _motor()
    declarado = CuerpoDeclarado(
        work_id=motor.work_id,
        objetivo=motor.objetivo,
        entregable="otro alcance permitido distinto",
    )
    veredicto = verificar_fidelidad_proyeccion(despachado=motor, declarado=declarado)
    assert veredicto.resultado is ResultadoEje.DIVERGENCIA
    assert "alcance" in (veredicto.motivo or "")


def test_fidelidad_campos_ausentes_no_se_comparan() -> None:
    """Una fidelidad parcial no declara verde: falta objetivo y alcance, no hay verdicto."""
    motor = _motor()
    declarado = CuerpoDeclarado(work_id=motor.work_id)  # objetivo y entregable ausentes
    veredicto = verificar_fidelidad_proyeccion(despachado=motor, declarado=declarado)
    assert veredicto.resultado is ResultadoEje.NO_COMPARABLE
    assert "objetivo" in (veredicto.motivo or "")
    assert "alcance" in (veredicto.motivo or "")


def test_fidelidad_un_solo_campo_ausente_tambien_es_no_comparable() -> None:
    """Basta con que falte UNO de los tres para que no haya verdicto (CODEX-001)."""
    motor = _motor()
    declarado = CuerpoDeclarado(work_id=motor.work_id, objetivo=motor.objetivo)  # sin alcance
    veredicto = verificar_fidelidad_proyeccion(despachado=motor, declarado=declarado)
    assert veredicto.resultado is ResultadoEje.NO_COMPARABLE
    assert "alcance" in (veredicto.motivo or "")


def test_fidelidad_sin_ningun_campo_leido_es_no_comparable() -> None:
    motor = _motor()
    declarado = CuerpoDeclarado()
    veredicto = verificar_fidelidad_proyeccion(despachado=motor, declarado=declarado)
    assert veredicto.resultado is ResultadoEje.NO_COMPARABLE


# --- Una contradicción de etiquetas no es una divergencia -------------------
#
# MEDIDO EN PRODUCCIÓN, no supuesto. Las seis líneas de la única pasada real del
# contador (rama `estado-del-motor`, 2026-08-26) dicen todas lo mismo:
#
#   {"eje": "estado", "motivo": "motor=<WorkItemState.ACTIVE> incidencia=None",
#    "resultado": "divergencia"}
#
# Una de ellas es la incidencia #353, que lleva `sirius:failed-safely` **y**
# `sirius:completed` a la vez. El espejo hace lo correcto: no elige ganadora, y
# marca `etiquetas_contradictorias`. El verificador no lo miraba, así que una
# incidencia mal etiquetada se registraba como si el motor estuviera
# desincronizado.
#
# El precio no es cosmético: `authority_reversion` revierte la autoridad de una
# clase a la PRIMERA divergencia tras la conmutación, sin esperar (§11.4). Dos
# etiquetas pegadas a mano devolverían el mando a GitHub, con un aviso que
# culpa al motor.

_ETIQUETAS_CONTRADICTORIAS = ("sirius:failed-safely", "sirius:completed")


def _linea_con_contradiccion() -> object:
    return verificar_dia(
        motor=_motor(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.PREPARAR),
        espejo=_espejo(
            estado=None,
            fase=None,
            etiquetas=_ETIQUETAS_CONTRADICTORIAS,
            etiquetas_contradictorias=True,
        ),
        contexto=_SIN_VENTANA,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
    )


def test_etiquetas_contradictorias_no_se_registran_como_divergencia() -> None:
    """Pregunta 1: no se puede comparar contra una incidencia que se contradice."""
    linea = _linea_con_contradiccion()
    for veredicto in linea.veredictos:
        assert veredicto.resultado is ResultadoEje.NO_COMPARABLE, (
            f"el eje {veredicto.eje} dio {veredicto.resultado.value} con etiquetas "
            f"contradictorias: {veredicto.motivo}. No hay nada contra lo que comparar."
        )
        # El motivo tiene que NOMBRAR las etiquetas: un «no comparable» sin
        # decir cuáles chocan obliga a quien lo lea a ir a mirar la incidencia.
        for etiqueta in _ETIQUETAS_CONTRADICTORIAS:
            assert etiqueta in veredicto.motivo, (
                f"el motivo no nombra `{etiqueta}`: {veredicto.motivo!r}"
            )


def test_una_incidencia_sin_etiquetas_sigue_siendo_divergencia() -> None:
    """Pregunta 2: lo que NO puede cambiar.

    Una incidencia sin ninguna etiqueta `sirius:*` es un hecho observado -así lo
    dice el dominio-, no una lectura fallida. Si este arreglo también la
    silenciara, taparía el caso que de verdad hay que ver.
    """
    linea = verificar_dia(
        motor=_motor(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.PREPARAR),
        espejo=_espejo(estado=None, fase=None, etiquetas=(), etiquetas_contradictorias=False),
        contexto=_SIN_VENTANA,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
    )
    for veredicto in linea.veredictos:
        assert veredicto.resultado is ResultadoEje.DIVERGENCIA, (
            f"el eje {veredicto.eje} dejó de ver una incidencia SIN etiquetas: "
            f"{veredicto.resultado.value}. Eso sí es una divergencia observada."
        )


def test_una_contradiccion_tampoco_pinta_el_dia_de_verde() -> None:
    """Pregunta 3: cambiar un rojo que miente por un verde que miente sería peor."""
    assert not _linea_con_contradiccion().es_verde, (
        "un día con la incidencia contradictoria salió VERDE: `NO_COMPARABLE` "
        "estaría contando como evidencia de que las dos fuentes coinciden, y la "
        "racha de los siete días avanzaría sobre nada."
    )
