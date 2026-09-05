"""El contador de los siete días (D1b, incidencia #268).

La prueba de terminado de este bloque, igual que la de D1a, no es "llega a
siete": es "se ha visto volver a cero" (nota de arranque). Por eso el orden
de este fichero es:

1. El registro: solo crece, y dos pasadas idénticas no duplican ni pierden
   líneas (requisito 6).
2. El contador vuelve a cero por CADA camino declarado -un día no verde y
   una corrección manual detectada-, cada uno con su prueba sembrada
   (requisito 1).
3. Un día sin línea, y un registro vacío, no cumplen la condición 1
   (requisito 2).
4. Un día entero de ``NO_COMPARABLE`` no cuenta como verde (requisito 4).
5. El contador informa por clase y dice por qué NO se cumple (requisito 7).
6. Ninguna ruta del contador conmuta nada (requisito 8).
7. La hora de la pasada se deriva del ``schedule: cron:`` real, nunca a ojo
   (requisito 5).
8. Los dos lectores de ``cron`` del repositorio -el del motor y el minilector
   de este fichero, independiente a propósito- hablan el MISMO dialecto, y una
   tabla de equivalencia impide que vuelvan a divergir en silencio (ADR-143).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import pytest
import yaml

from sirius_engine.domain.authority import Autoridad, autoridad_de_clase
from sirius_engine.domain.events import AggregateType, Event
from sirius_engine.domain.work_item import WorkItemClass, create_work_item
from sirius_engine.projection_verifier import (
    EJE_ESTADO,
    EJE_FASE,
    LineaRegistro,
    ResultadoEje,
    VeredictoEje,
    formatear_linea,
)
from sirius_engine.seven_day_streak import (
    _expandir_campo,
    anadir_lineas,
    detectar_correcciones_manuales,
    evaluar_racha,
    hora_recomendada_pasada,
    leer_registro,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOY = date(2026, 8, 22)
_WORK_ID = "WI-D1B-1"
_CLASE = WorkItemClass.PROGRAMACION


def _instante(dia: date, hora: int = 12) -> datetime:
    return datetime(dia.year, dia.month, dia.day, hora, tzinfo=UTC)


def _linea_verde(
    dia: date, *, work_id: str = _WORK_ID, clase: WorkItemClass = _CLASE
) -> LineaRegistro:
    return LineaRegistro(
        instante=_instante(dia),
        clase=clase,
        work_id=work_id,
        veredictos=(
            VeredictoEje(eje=EJE_FASE, resultado=ResultadoEje.COINCIDE),
            VeredictoEje(eje=EJE_ESTADO, resultado=ResultadoEje.COINCIDE),
        ),
    )


def _linea_divergente(
    dia: date, *, work_id: str = _WORK_ID, clase: WorkItemClass = _CLASE, eje: str = EJE_ESTADO
) -> LineaRegistro:
    otros = EJE_FASE if eje == EJE_ESTADO else EJE_ESTADO
    return LineaRegistro(
        instante=_instante(dia),
        clase=clase,
        work_id=work_id,
        veredictos=(
            VeredictoEje(eje=otros, resultado=ResultadoEje.COINCIDE),
            VeredictoEje(
                eje=eje,
                resultado=ResultadoEje.DIVERGENCIA,
                motivo="motor=<WorkItemState.ACTIVE> incidencia=<WorkItemState.PLANNED>",
            ),
        ),
    )


def _rango(inicio: date, fin: date) -> list[date]:
    dias = []
    cursor = inicio
    while cursor <= fin:
        dias.append(cursor)
        cursor += timedelta(days=1)
    return dias


def _evento(
    work_id: str,
    *,
    dia: date,
    hora: int = 6,
    kind: str = "work_item_activated",
    aggregate_type: AggregateType = AggregateType.WORK_ITEM,
) -> Event:
    motor = create_work_item(
        work_id=work_id,
        peticion_original="texto",
        objetivo="objetivo",
        contexto_origen=("incidencia:1",),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=_CLASE,
        now=_instante(dia, hora),
    )
    return Event(
        sequence=1,
        occurred_at=_instante(dia, hora),
        aggregate_type=aggregate_type,
        aggregate_id=work_id,
        kind=kind,
        entity=motor,
    )


# --- 1. El registro: solo crece, sin duplicar --------------------------------


def test_anadir_lineas_dos_pasadas_identicas_no_duplican(tmp_path: Path) -> None:
    ruta = tmp_path / "registro.jsonl"
    lineas = (_linea_verde(_HOY),)
    primera = anadir_lineas(ruta, lineas)
    segunda = anadir_lineas(ruta, lineas)
    assert primera == 1
    assert segunda == 0
    assert leer_registro(ruta) == lineas


def test_anadir_lineas_solo_crece_no_reordena_lo_anterior(tmp_path: Path) -> None:
    ruta = tmp_path / "registro.jsonl"
    anadir_lineas(ruta, (_linea_verde(date(2026, 8, 1)),))
    texto_tras_primera = ruta.read_text(encoding="utf-8")
    anadir_lineas(ruta, (_linea_verde(date(2026, 8, 2)),))
    texto_tras_segunda = ruta.read_text(encoding="utf-8")
    assert texto_tras_segunda.startswith(texto_tras_primera)


def test_leer_registro_de_fichero_inexistente_es_vacio(tmp_path: Path) -> None:
    assert leer_registro(tmp_path / "no-existe.jsonl") == ()


def test_leer_registro_invierte_formatear_linea(tmp_path: Path) -> None:
    ruta = tmp_path / "registro.jsonl"
    original = _linea_divergente(_HOY)
    anadir_lineas(ruta, (original,))
    (leida,) = leer_registro(ruta)
    assert formatear_linea(leida) == formatear_linea(original)


# --- 2. El contador vuelve a cero: los dos caminos, cada uno sembrado -------


def test_racha_vuelve_a_cero_por_un_dia_no_verde_en_medio_de_la_racha() -> None:
    """Tres días verdes, un día divergente, tres días verdes más: la racha NO suma los siete.

    Lleva un evento del motor que explica la resolución del día divergente al
    siguiente (índice 3 -> índice 4), para aislar ESTE camino de reinicio -un
    día no verde- del otro (corrección manual, probado aparte): sin ese
    evento, la resolución sin explicación sería TAMBIÉN una huella de
    corrección, y esta prueba dejaría de medir un solo camino.
    """
    dias = _rango(_HOY - timedelta(days=6), _HOY)
    lineas = []
    for indice, dia in enumerate(dias):
        if indice == 3:  # el cuarto día de siete, en medio, se siembra rojo.
            lineas.append(_linea_divergente(dia))
        else:
            lineas.append(_linea_verde(dia))
    eventos = (_evento(_WORK_ID, dia=dias[3], hora=18),)

    evaluacion = evaluar_racha(lineas=lineas, eventos=eventos, clase=_CLASE, hoy=_HOY)

    assert evaluacion.cumple is False
    assert evaluacion.dias_consecutivos == 3, (
        "solo los tres días verdes DESPUÉS del día rojo cuentan: la racha se rompió ahí, "
        "y los tres verdes de antes no la resucitan"
    )
    assert "día no verde" in evaluacion.motivo
    assert dias[3].isoformat() in evaluacion.motivo


def test_racha_vuelve_a_cero_por_correccion_manual_detectada_en_medio_de_la_racha() -> None:
    """Una DIVERGENCIA que se resuelve a COINCIDE sin transición del motor rompe la racha ahí.

    Sembrado: el día 4 (de siete) tiene DIVERGENCIA en estado; el día 5 esa
    misma línea pasa a COINCIDE, pero el diario de eventos del motor no
    registra NINGUNA transición de ``_WORK_ID`` entre esos dos instantes. Es
    exactamente la huella que la nota de arranque de la incidencia pide: la
    incidencia (o el almacén) cambiaron sin que el motor lo hiciera.
    """
    dias = _rango(_HOY - timedelta(days=6), _HOY)
    lineas = []
    for indice, dia in enumerate(dias):
        if indice == 3:
            lineas.append(_linea_divergente(dia))
        else:
            lineas.append(_linea_verde(dia))
    # Sin eventos del motor: nada explica que el día 4 (índice 3, DIVERGENCIA)
    # pasara a día 5 (índice 4, COINCIDE) en la lista `lineas` de arriba.

    evaluacion = evaluar_racha(lineas=lineas, eventos=(), clase=_CLASE, hoy=_HOY)

    assert evaluacion.cumple is False
    # El día divergente (índice 3) YA rompe la racha por sí solo (camino 1);
    # esta prueba fija además que, aunque ese día individual fuera verde por
    # descuido de otro cambio, la corrección manual detectada al resolverse
    # seguiría rompiéndola: se comprueba directamente sobre el detector.
    huellas = detectar_correcciones_manuales(lineas, ())
    assert len(huellas) == 1
    assert huellas[0].work_id == _WORK_ID
    assert huellas[0].eje == EJE_ESTADO
    assert huellas[0].dia == dias[4]


def test_correccion_manual_no_se_detecta_si_el_motor_registra_una_transicion() -> None:
    """La MISMA resolución, pero con un evento del motor de por medio: no deja huella."""
    dia_divergencia = _HOY - timedelta(days=1)
    dia_coincide = _HOY
    lineas = (_linea_divergente(dia_divergencia), _linea_verde(dia_coincide))
    eventos = (_evento(_WORK_ID, dia=dia_divergencia, hora=18),)

    huellas = detectar_correcciones_manuales(lineas, eventos)

    assert huellas == ()


def test_correccion_manual_se_detecta_pese_a_un_evento_ajeno_al_eje_resuelto() -> None:
    """CODEX-001 (ronda 2): una repriorización entre las dos líneas no explica nada.

    ``reprioritize`` (``work_item_reprioritized``) no toca ni fase ni estado
    (:mod:`sirius_engine.domain.work_item`): es exactamente el evento "ajeno"
    del hallazgo -sin comprobar el eje que de verdad se resolvió, cualquier
    evento del ``work_id`` ocultaba la corrección-. Con el eje ya comprobado,
    esta repriorización no puede explicar que ``estado`` pasara de
    DIVERGENCIA a COINCIDE: la huella se registra igual.
    """
    dia_divergencia = _HOY - timedelta(days=1)
    dia_coincide = _HOY
    lineas = (_linea_divergente(dia_divergencia), _linea_verde(dia_coincide))
    eventos = (_evento(_WORK_ID, dia=dia_divergencia, hora=18, kind="work_item_reprioritized"),)

    huellas = detectar_correcciones_manuales(lineas, eventos)

    assert len(huellas) == 1
    assert huellas[0].eje == EJE_ESTADO


def test_correccion_manual_no_se_detecta_si_el_evento_toca_el_eje_de_fase() -> None:
    """La misma resolución, pero de ``fase``: solo un ``kind`` que toque fase la explica."""
    dia_divergencia = _HOY - timedelta(days=1)
    dia_coincide = _HOY
    lineas = (
        _linea_divergente(dia_divergencia, eje=EJE_FASE),
        _linea_verde(dia_coincide),
    )
    eventos = (_evento(_WORK_ID, dia=dia_divergencia, hora=18, kind="work_item_execution_started"),)

    huellas = detectar_correcciones_manuales(lineas, eventos)

    assert huellas == ()


def test_evento_de_un_run_con_el_mismo_aggregate_id_no_explica_nada() -> None:
    """CODEX-001: un evento que no es del ``WorkItem`` (``aggregate_type`` distinto) no cuenta.

    Aunque su ``kind`` fuera uno que normalmente explica ``estado`` y su
    ``aggregate_id`` coincidiera con el ``work_id``, un evento de ``RUN`` no es
    una transición del ``WorkItem``: no puede ser la explicación de que su
    eje pasara de DIVERGENCIA a COINCIDE.
    """
    dia_divergencia = _HOY - timedelta(days=1)
    dia_coincide = _HOY
    lineas = (_linea_divergente(dia_divergencia), _linea_verde(dia_coincide))
    eventos = (
        _evento(
            _WORK_ID,
            dia=dia_divergencia,
            hora=18,
            kind="work_item_activated",
            aggregate_type=AggregateType.RUN,
        ),
    )

    huellas = detectar_correcciones_manuales(lineas, eventos)

    assert len(huellas) == 1
    assert huellas[0].eje == EJE_ESTADO


def test_correccion_manual_rompe_la_racha_aunque_ambos_dias_individualmente_fueran_verdes() -> None:
    """Fija que la condición 2 rompe la racha incluso cuando la condición 1 no lo haría.

    Construye una racha de siete días TODOS verdes (condición 1 se cumpliría
    sola), pero con una corrección manual sembrada en dos líneas del mismo
    work_id que, aisladas, también leen verde/verde-tras-no-comparable: el
    contador tiene que romperse por la corrección, no solo por un día rojo.
    """
    dias = _rango(_HOY - timedelta(days=6), _HOY)
    lineas: list[LineaRegistro] = [_linea_verde(dia) for dia in dias]
    # Sustituye el día 3 (índice 2) por una DIVERGENCIA que en el índice 3 se
    # resuelve a COINCIDE sin ningún evento del motor: los siete días,
    # tomados uno a uno, solo tienen UN no-verde (índice 2), pero la
    # corrección manual detectada en el índice 3 debe romper la racha
    # también ahí, no solo en el índice 2.
    lineas[2] = _linea_divergente(dias[2])

    evaluacion = evaluar_racha(lineas=lineas, eventos=(), clase=_CLASE, hoy=_HOY)

    assert evaluacion.cumple is False
    assert evaluacion.dias_consecutivos == 3, "solo los tres días tras la corrección cuentan"
    assert "corrección manual" in evaluacion.motivo


# --- 3. Un día sin línea, y un registro vacío, no cumplen la condición 1 ----


def test_registro_vacio_no_cumple() -> None:
    evaluacion = evaluar_racha(lineas=(), eventos=(), clase=_CLASE, hoy=_HOY)
    assert evaluacion.cumple is False
    assert evaluacion.dias_consecutivos == 0
    assert "sin línea" in evaluacion.motivo or "sin ninguna línea" in evaluacion.motivo


def test_seis_dias_verdes_y_un_hueco_no_cumple() -> None:
    """Siete días exige días PRESENTES y consecutivos: un hueco no es rojo, pero tampoco cuenta."""
    dias = _rango(_HOY - timedelta(days=6), _HOY)
    lineas = [
        _linea_verde(dia) for indice, dia in enumerate(dias) if indice != 2
    ]  # hueco en el día 3

    evaluacion = evaluar_racha(lineas=lineas, eventos=(), clase=_CLASE, hoy=_HOY)

    assert evaluacion.cumple is False
    assert evaluacion.dias_consecutivos == 4, "solo los cuatro días tras el hueco cuentan"
    assert "sin línea registrada" in evaluacion.motivo


# --- 4. Un día entero de NO_COMPARABLE no cuenta como verde -----------------


def test_dia_no_comparable_no_cuenta_como_verde_y_conserva_el_motivo() -> None:
    dia_no_comparable = _HOY
    linea_no_comparable = LineaRegistro(
        instante=_instante(dia_no_comparable),
        clase=_CLASE,
        work_id=_WORK_ID,
        veredictos=(
            VeredictoEje(eje=EJE_FASE, resultado=ResultadoEje.COINCIDE),
            VeredictoEje(
                eje=EJE_ESTADO,
                resultado=ResultadoEje.NO_COMPARABLE,
                motivo="residencia normal de etiqueta de máquina",
            ),
        ),
    )
    lineas = [_linea_verde(_HOY - timedelta(days=1)), linea_no_comparable]

    evaluacion = evaluar_racha(lineas=lineas, eventos=(), clase=_CLASE, hoy=_HOY)

    assert evaluacion.cumple is False
    assert evaluacion.dias_consecutivos == 0, (
        "el día no comparable rompe la racha en el primer paso"
    )
    assert "no_comparable" in evaluacion.motivo
    assert "residencia normal de etiqueta de máquina" in evaluacion.motivo


# --- 5. El contador informa por clase y dice por qué NO se cumple ----------


def test_evaluacion_distingue_clases_y_no_mezcla_sus_lineas() -> None:
    dias = _rango(_HOY - timedelta(days=6), _HOY)
    lineas = [_linea_verde(dia, clase=WorkItemClass.PROGRAMACION) for dia in dias]
    lineas += [_linea_divergente(dias[-1], work_id="WI-AUDITORIA-1", clase=WorkItemClass.AUDITORIA)]

    programacion = evaluar_racha(
        lineas=lineas, eventos=(), clase=WorkItemClass.PROGRAMACION, hoy=_HOY
    )
    auditoria = evaluar_racha(lineas=lineas, eventos=(), clase=WorkItemClass.AUDITORIA, hoy=_HOY)

    assert programacion.cumple is True
    assert programacion.dias_consecutivos == 7
    assert auditoria.cumple is False
    assert auditoria.dias_consecutivos == 0


def test_motivo_de_incumplimiento_es_especifico_no_un_booleano_suelto() -> None:
    evaluacion = evaluar_racha(lineas=(), eventos=(), clase=_CLASE, hoy=_HOY)
    assert evaluacion.motivo != ""
    assert str(evaluacion.cumple) not in evaluacion.motivo  # no es solo "False" repetido


def test_evaluar_racha_declara_lecturas_caidas_hoy_sin_interrumpir_el_contador() -> None:
    """Incidencia #313: una lectura caída de esta pasada no rompe una racha ya registrada.

    El contrato §11.2 clasifica un fallo de un servicio externo como avería
    operativa, no como discrepancia -lo único que la condición mide-, así que
    no interrumpe el contador (ADR-084). Pero el motivo tiene que declararlo:
    callarlo es el falso verde silencioso que motivó la incidencia.
    """
    dias = _rango(_HOY - timedelta(days=6), _HOY)
    lineas = [_linea_verde(dia) for dia in dias]

    evaluacion = evaluar_racha(
        lineas=lineas,
        eventos=(),
        clase=_CLASE,
        hoy=_HOY,
        lecturas_caidas_hoy=("WI-B (incidencia #402)",),
    )

    assert evaluacion.cumple is True, (
        "el contrato §11.2 no deja que una avería operativa rompa el contador"
    )
    assert evaluacion.dias_consecutivos == 7
    assert "WI-B (incidencia #402)" in evaluacion.motivo
    assert "no interrumpe el contador" in evaluacion.motivo


def test_evaluar_racha_sin_lecturas_caidas_no_menciona_ningun_aviso() -> None:
    dias = _rango(_HOY - timedelta(days=6), _HOY)
    lineas = [_linea_verde(dia) for dia in dias]

    evaluacion = evaluar_racha(lineas=lineas, eventos=(), clase=_CLASE, hoy=_HOY)

    assert "no interrumpe el contador" not in evaluacion.motivo


# --- 6. Ninguna ruta del contador conmuta nada ------------------------------


def test_evaluar_una_racha_completa_no_cambia_la_autoridad_de_ninguna_clase() -> None:
    dias = _rango(_HOY - timedelta(days=6), _HOY)
    lineas = [_linea_verde(dia) for dia in dias]
    autoridad_antes = {clase: autoridad_de_clase(clase) for clase in WorkItemClass}

    evaluacion = evaluar_racha(lineas=lineas, eventos=(), clase=_CLASE, hoy=_HOY)

    assert evaluacion.cumple is True  # la racha llegó a siete: el caso que más tentaría a conmutar
    autoridad_despues = {clase: autoridad_de_clase(clase) for clase in WorkItemClass}
    assert autoridad_antes == autoridad_despues
    assert autoridad_de_clase(_CLASE) is Autoridad.INCIDENCIA  # sigue sin conmutar


# --- 7. La hora de la pasada se deriva, nunca a ojo -------------------------


def test_hora_recomendada_es_el_punto_medio_del_mayor_hueco(tmp_path: Path) -> None:
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    (workflows / "reconciliar.yml").write_text(
        yaml.safe_dump({"on": {"schedule": [{"cron": "17 */6 * * *"}]}}), encoding="utf-8"
    )
    (workflows / "otro.yml").write_text(
        yaml.safe_dump({"on": {"push": None}, "jobs": {"j": {"timeout-minutes": 30}}}),
        encoding="utf-8",
    )

    hora, motivo = hora_recomendada_pasada(workflows)

    assert hora == time(3, 17)
    assert "hueco" in motivo


def test_hora_recomendada_sin_schedule_no_inventa_nada(tmp_path: Path) -> None:
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    (workflows / "solo-push.yml").write_text(
        yaml.safe_dump({"on": {"push": None}}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="no hay de qué derivar"):
        hora_recomendada_pasada(workflows)


def test_hora_recomendada_para_si_ningun_hueco_deja_ventana_tranquila(tmp_path: Path) -> None:
    """Disparos cada 30 minutos: ningún punto del día queda a 2h50m del más cercano."""
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    (workflows / "muy-frecuente.yml").write_text(
        yaml.safe_dump({"on": {"schedule": [{"cron": "*/30 * * * *"}]}}), encoding="utf-8"
    )
    (workflows / "otro.yml").write_text(
        yaml.safe_dump({"jobs": {"j": {"timeout-minutes": 60}}}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="ninguna hora produciría días verdes"):
        hora_recomendada_pasada(workflows)


# --- 7 bis. El derivador no se cuenta a sí mismo (ADR-144) ------------------
#
# La pregunta que `hora_recomendada_pasada` responde es «¿cuál es la hora más
# tranquila para la PASADA del contador?», y la propia pasada no puede
# estorbarse a sí misma. Hasta ADR-144 sí lo hacía: al cablear en
# `contador-siete-dias.yml` la hora derivada el 25-08-2026 (03:24 UTC, punto
# medio de un hueco de 345 min), su propio disparo partió ese hueco y la
# derivación saltó al siguiente hueco de 345, las 09:24 (medido en ADR-143).
#
# El nombre del fichero se escribe aquí a mano, sin importar la constante del
# motor: si alguien renombra el workflow y no toca el motor -o al revés-, estas
# pruebas lo dicen en vez de seguir de acuerdo consigo mismas.

_CONTADOR_PARA_LAS_PRUEBAS = "contador-siete-dias.yml"


def _arbol_con_un_solo_disparo(tmp_path: Path) -> Path:
    """Un directorio de workflows con UN disparo a medianoche y un tope de job.

    Con un solo disparo, el mayor hueco libre es el día entero y su punto medio
    cae a las 12:00. Un segundo disparo justo ahí lo parte en dos mitades de
    720 min y mueve la derivación a las 06:00: el mismo mecanismo, en pequeño,
    con el que el cron del contador movió la hora real de las 03:24 a las
    09:24. El `timeout-minutes` existe porque la ventana de tolerancia también
    se deriva, y sin ningún tope no habría de qué.
    """
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    (workflows / "otro.yml").write_text(
        yaml.safe_dump(
            {"on": {"schedule": [{"cron": "0 0 * * *"}]}, "jobs": {"j": {"timeout-minutes": 30}}}
        ),
        encoding="utf-8",
    )
    return workflows


def _escribir_disparo_de_mediodia(ruta: Path) -> None:
    ruta.write_text(
        yaml.safe_dump({"on": {"schedule": [{"cron": "0 12 * * *"}]}}), encoding="utf-8"
    )


def test_hora_recomendada_no_cuenta_los_disparos_del_workflow_del_contador(
    tmp_path: Path,
) -> None:
    """Con el fichero del contador presente, sus disparos no parten ningún hueco."""
    workflows = _arbol_con_un_solo_disparo(tmp_path)
    _escribir_disparo_de_mediodia(workflows / _CONTADOR_PARA_LAS_PRUEBAS)

    hora, motivo = hora_recomendada_pasada(workflows)

    assert hora == time(12, 0), (
        "el disparo del propio contador partió el hueco del que sale su hora: "
        "es exactamente la autoinclusión que ADR-144 retira"
    )
    assert "1440 min" in motivo


def test_hora_recomendada_deriva_sobre_lo_que_hay_si_el_contador_no_esta(
    tmp_path: Path,
) -> None:
    """El otro lado: la exclusión es una resta, no un requisito de que el fichero exista."""
    workflows = _arbol_con_un_solo_disparo(tmp_path)
    assert not (workflows / _CONTADOR_PARA_LAS_PRUEBAS).exists()

    hora, _motivo = hora_recomendada_pasada(workflows)

    assert hora == time(12, 0)


def test_si_el_unico_cron_es_el_del_contador_el_error_nombra_la_exclusion(
    tmp_path: Path,
) -> None:
    """Un directorio donde el ÚNICO `schedule: cron:` es el del contador.

    Con la exclusión de ADR-144 no queda ningún disparo que contar, así que la
    función tiene que parar -eso no cambia-. Lo que no puede hacer es afirmar
    que no encontró ningún `schedule: cron:` en el directorio: sí lo hay, y es
    justo el que ella se salta. El error tiene que nombrar la exclusión para
    que la causa se lea en el propio mensaje, en vez de mandar a buscar un
    disparador ausente que en realidad está escrito.
    """
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    (workflows / _CONTADOR_PARA_LAS_PRUEBAS).write_text(
        yaml.safe_dump(
            {"on": {"schedule": [{"cron": "24 3 * * *"}]}, "jobs": {"j": {"timeout-minutes": 30}}}
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=_CONTADOR_PARA_LAS_PRUEBAS) as error:
        hora_recomendada_pasada(workflows)

    assert "no encontré ningún `schedule: cron:`" not in str(error.value), (
        "el mensaje sigue afirmando que el directorio no tiene ningún `schedule: cron:`, "
        "cuando lo que ocurre es que el único que hay se excluye a propósito"
    )


def test_un_contador_renombrado_vuelve_a_contarse_sin_reventar(tmp_path: Path) -> None:
    """Un renombrado accidental degrada a «como antes de ADR-144», nunca a un error.

    La exclusión es NOMBRADA a propósito (ADR-144): no adivina quién consume la
    hora. El precio, declarado aquí, es que un fichero con otro nombre vuelve a
    contarse -y esta prueba es la que lo hace visible en vez de silencioso-.
    """
    workflows = _arbol_con_un_solo_disparo(tmp_path)
    _escribir_disparo_de_mediodia(workflows / "contador-siete-dias-viejo.yml")

    hora, _motivo = hora_recomendada_pasada(workflows)

    assert hora == time(6, 0)


def test_hora_recomendada_del_arbol_real_no_cuenta_el_cron_del_propio_contador() -> None:
    """El pin MEDIDO del árbol real: 03:24 UTC, 345 min tras las 00:32 (ADR-143/ADR-144).

    No es un número elegido: es el que la derivación daba el 25-08-2026, cuando
    `contador-siete-dias.yml` todavía no existía, y el que ADR-143 volvió a
    medir el 05-09-2026 sobre el mismo árbol sin ese fichero. Contra el
    derivador autoincluyente esta prueba falla con 09:24, que es la medida que
    ADR-143 registró y que este encargo desmiente como derivación correcta.
    """
    hora, motivo = hora_recomendada_pasada()

    assert hora == time(3, 24), (
        "la derivación del árbol real dejó de dar 03:24 UTC. Si acabas de mover "
        "un `schedule:`, la cabecera de `contador-siete-dias.yml` ya no dice la "
        "verdad y hay que volver a derivar la hora; si acabas de tocar el "
        "derivador, comprueba que sigue sin contarse a sí mismo (ADR-144)"
    )
    assert "345 min, tras las 00:32" in motivo


# El minilector de `cron` del guardián-oráculo. Vive aquí, a nivel de módulo y
# no dentro de la prueba, por dos razones: para poder ejercitarlo solo (la
# tabla de equivalencia de más abajo) y porque un lector escondido dentro de
# un `for` es exactamente el que divergió sin que nadie lo viera.
#
# Es una SEGUNDA implementación, deliberadamente independiente, del mismo
# dialecto que documenta `seven_day_streak._expandir_campo` (ADR-143): no
# importa nada del motor -esa es la disciplina «YAML aparte» que este guardián
# cita-, y por eso no puede compartir con él ni el código ni sus errores. Lo
# que impide que los dos vuelvan a divergir en silencio no es este comentario,
# es `test_los_dos_lectores_de_cron_expanden_y_rechazan_igual`.

_ENTERO_CRON_ORACULO = re.compile(r"[0-9]+")
_RANGO_CRON_ORACULO = re.compile(r"([0-9]+)-([0-9]+)")
_PASO_CRON_ORACULO = re.compile(r"\*/([0-9]+)")


def expandir_campo_del_oraculo(campo: str, tope: int, nombre: str) -> list[int]:
    """Los enteros de ``[0, tope)`` que denota un campo minuto/hora del dialecto.

    Las cinco formas admitidas -``*``, ``*/N``, entero, rango ``a-b`` y listas
    por comas de enteros o rangos- y el rechazo ruidoso de todo lo demás, con
    el campo nombrado en el mensaje: nunca un ``int()`` pelado, que es como
    llegaron los rojos 2 y 3 de ADR-139.
    """

    def fuera_del_dialecto(forma: str) -> ValueError:
        return ValueError(
            f"campo {nombre} de cron: forma no admitida {forma!r} en la expresión {campo!r}"
        )

    if campo == "*":
        return list(range(tope))
    paso = _PASO_CRON_ORACULO.fullmatch(campo)
    if paso is not None:
        salto = int(paso.group(1))
        if not 1 <= salto <= tope:
            raise fuera_del_dialecto(campo)
        return list(range(0, tope, salto))
    if campo.startswith("*") or "/" in campo:
        raise fuera_del_dialecto(campo)

    valores: set[int] = set()
    for elemento in campo.split(","):
        rango = _RANGO_CRON_ORACULO.fullmatch(elemento)
        entero = _ENTERO_CRON_ORACULO.fullmatch(elemento)
        if rango is not None:
            inicio, fin = int(rango.group(1)), int(rango.group(2))
            if inicio > fin or fin >= tope:
                raise fuera_del_dialecto(elemento)
            valores.update(range(inicio, fin + 1))
        elif entero is not None:
            valor = int(entero.group())
            if valor >= tope:
                raise fuera_del_dialecto(elemento)
            valores.add(valor)
        else:
            raise fuera_del_dialecto(elemento)
    return sorted(valores)


def test_hora_recomendada_atada_al_schedule_real_del_repositorio() -> None:
    """Misma disciplina que ``test_ventana_tolerancia_atada_al_yaml_real...``: YAML aparte."""
    minutos_disparo = set()
    for wf in sorted((_REPO_ROOT / ".github" / "workflows").glob("*.yml")):
        if wf.name == _CONTADOR_PARA_LAS_PRUEBAS:
            # ADR-144: la hora que se compara es la de la PASADA del contador,
            # y la propia pasada no se estorba a sí misma. La exclusión se
            # escribe aquí otra vez, con el nombre a mano y sin importar la
            # constante del motor: el «YAML aparte» de ADR-143 vale también
            # para esto, o el oráculo dejaría de medir por su cuenta.
            continue
        doc = yaml.safe_load(wf.read_text(encoding="utf-8"))
        activadores = doc.get("on") if isinstance(doc, dict) else None
        if activadores is None and isinstance(doc, dict):
            activadores = doc.get(True)
        if not isinstance(activadores, dict):
            continue
        for entrada in activadores.get("schedule") or []:
            expresion = entrada.get("cron")
            campos = expresion.split()
            for hora_campo in expandir_campo_del_oraculo(campos[1], 24, "hora"):
                for minuto in expandir_campo_del_oraculo(campos[0], 60, "minuto"):
                    minutos_disparo.add(hora_campo * 60 + minuto)
    assert minutos_disparo, "no encontré ningún schedule real: la comparación no mediría nada"

    ordenados = sorted(minutos_disparo)
    huecos = []
    for indice, inicio in enumerate(ordenados):
        siguiente = ordenados[(indice + 1) % len(ordenados)]
        duracion = (siguiente - inicio) % (24 * 60)
        huecos.append((duracion or 24 * 60, inicio))
    duracion_max = max(duracion for duracion, _inicio in huecos)
    inicio_max = min(inicio for duracion, inicio in huecos if duracion == duracion_max)
    punto_medio = (inicio_max + duracion_max // 2) % (24 * 60)
    esperado = time(hour=punto_medio // 60, minute=punto_medio % 60)

    hora, _motivo = hora_recomendada_pasada()
    assert hora == esperado


# --- 8. Los dos lectores de cron hablan el mismo dialecto (ADR-143) ---------
#
# Ningún lector puede observar que diverge del otro: por eso el guardián es un
# tercero. La tabla es la unidad de medida -todas las formas admitidas, las
# mixtas incluidas, y una colección de rechazadas- y los dos lectores tienen
# que estar de acuerdo en TODAS, tanto en lo que expanden como en lo que
# rechazan. Cada forma de aquí se vio fallar antes del arreglo en al menos uno
# de los dos lectores (ADR-143, «Comprobación que la sostiene»).

_FORMAS_ADMITIDAS: tuple[str, ...] = (
    "*",
    "*/2",
    "*/6",
    "*/15",
    "0",
    "17",
    "23",
    "4-23",
    "0-0",
    "0,4-23",  # la mixta que quemó los rojos 2 y 3 de ADR-139
    "1-3,5,7-9",
    "0,15,30",
    "0,30",
    "3,3",
    "01",
)

_FORMAS_RECHAZADAS: tuple[str, ...] = (
    "",
    " 1",
    "8-18/2",  # paso sobre rango: GitHub lo admite, este dialecto no
    "0-23/2",
    "*/0",
    "*/99",
    "*/x",
    "*/",
    "**",
    "*,1",
    "0,*/2",
    "3-1",
    "1-",
    "-3",
    "1-2-3",
    "1,,2",
    "a",
    "JAN",
    "?",
    "60",
    "1;2",
    "+1",
    "\u0661\u0665",  # dígitos árabo-índicos: `str.isdigit()` los daría por buenos
)

_TABLA_DEL_DIALECTO: tuple[str, ...] = _FORMAS_ADMITIDAS + _FORMAS_RECHAZADAS

#: Los dos campos reales, con su tope y el nombre que el rechazo debe decir.
_CAMPOS_DEL_DIALECTO: tuple[tuple[int, str], ...] = ((60, "minuto"), (24, "hora"))


def _leer_campo(
    lector: Callable[[str, int, str], list[int]], campo: str, tope: int, nombre: str
) -> tuple[list[int] | None, str | None]:
    """La lectura de un campo como dato comparable: o los valores, o el rechazo."""
    try:
        return sorted(set(lector(campo, tope, nombre))), None
    except ValueError as error:
        return None, str(error)


@pytest.mark.parametrize(("tope", "nombre"), _CAMPOS_DEL_DIALECTO)
@pytest.mark.parametrize("campo", _TABLA_DEL_DIALECTO)
def test_los_dos_lectores_de_cron_expanden_y_rechazan_igual(
    campo: str, tope: int, nombre: str
) -> None:
    valores_motor, rechazo_motor = _leer_campo(_expandir_campo, campo, tope, nombre)
    valores_oraculo, rechazo_oraculo = _leer_campo(expandir_campo_del_oraculo, campo, tope, nombre)

    assert (rechazo_motor is None) == (rechazo_oraculo is None), (
        f"los dos lectores discrepan sobre si {campo!r} pertenece al dialecto en el campo "
        f"{nombre}: motor={rechazo_motor or valores_motor}, "
        f"oráculo={rechazo_oraculo or valores_oraculo}"
    )
    assert valores_motor == valores_oraculo, (
        f"{campo!r} expande distinto en el campo {nombre}: motor={valores_motor}, "
        f"oráculo={valores_oraculo}"
    )


@pytest.mark.parametrize("campo", _FORMAS_ADMITIDAS)
def test_toda_forma_admitida_del_dialecto_la_digieren_los_dos(campo: str) -> None:
    """La mitad que hace la tabla no vacua: sin esto, «rechazar todo» la pasaría entera."""
    assert _expandir_campo(campo, 60, "minuto")
    assert expandir_campo_del_oraculo(campo, 60, "minuto")


@pytest.mark.parametrize(("tope", "nombre"), _CAMPOS_DEL_DIALECTO)
@pytest.mark.parametrize("campo", _FORMAS_RECHAZADAS)
def test_toda_forma_fuera_del_dialecto_la_rechazan_los_dos_con_el_campo_nombrado(
    campo: str, tope: int, nombre: str
) -> None:
    """Rechazo RUIDOSO: el mensaje dice el campo y la forma, nunca un ``int()`` pelado."""
    for lector in (_expandir_campo, expandir_campo_del_oraculo):
        with pytest.raises(ValueError) as excepcion:
            lector(campo, tope, nombre)
        mensaje = str(excepcion.value)
        assert nombre in mensaje, f"{lector.__name__} no dice qué campo falló: {mensaje}"
        assert "invalid literal for int()" not in mensaje


def test_la_lista_con_rango_expande_igual_en_los_dos_lectores() -> None:
    """``0,4-23``: la expresión exacta del rojo 2 de ADR-139."""
    esperado = [0, *range(4, 24)]
    assert _expandir_campo("0,4-23", 24, "hora") == esperado
    assert expandir_campo_del_oraculo("0,4-23", 24, "hora") == esperado


def test_el_paso_sobre_rango_lo_rechazan_los_dos_con_el_campo_en_el_mensaje() -> None:
    """``8-18/2`` es válido para GitHub y está fuera de este dialecto: se dice, no se adivina."""
    for lector in (_expandir_campo, expandir_campo_del_oraculo):
        with pytest.raises(ValueError, match="hora"):
            lector("8-18/2", 24, "hora")


def test_el_comodin_en_minuto_expande_a_los_sesenta_en_los_dos() -> None:
    assert _expandir_campo("*", 60, "minuto") == list(range(60))
    assert expandir_campo_del_oraculo("*", 60, "minuto") == list(range(60))
