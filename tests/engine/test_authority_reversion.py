"""La reversión automática de autoridad (D1c, incidencia #276, contrato §11.4).

Orden de este fichero, calcado del de D1a/D1b: la prueba de terminado no es
"revierte" en abstracto, es **los dos "se ha visto"** de la nota de arranque:

1. Una `DIVERGENCIA` sembrada sobre una clase conmutada SÍ revierte
   (requisito 1).
2. Una tanda entera de `NO_COMPARABLE` NO revierte (requisito 2) -es el
   defecto concreto que este bloque podría introducir.

Después: una clase no conmutada no se toca (requisito 6), a la primera
divergencia basta (requisito 5), la reversión es idempotente (requisito 7),
el registro de conmutaciones es append-only y determinista (requisito 8), y
una clase `MOTOR` no puede alimentar nada de esto (requisito 4, ya cubierto
en `test_authority.py` a nivel de `EntradaConmutacion`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius_engine.authority_reversion import (
    anadir_entradas,
    evaluar_reversion,
    formatear_aviso_reversion,
    leer_registro_conmutaciones,
)
from sirius_engine.domain.authority import Autoridad, EntradaConmutacion, autoridad_de_clase
from sirius_engine.domain.work_item import WorkItemClass
from sirius_engine.projection_verifier import (
    EJE_ESTADO,
    EJE_FASE,
    LineaRegistro,
    ResultadoEje,
    VeredictoEje,
)

_CLASE = WorkItemClass.PROGRAMACION
_WORK_ID = "WI-D1C-1"


def _instante(dia: int, hora: int = 12) -> datetime:
    return datetime(2026, 8, dia, hora, tzinfo=UTC)


def _conmutacion_a_motor(dia: int, *, clase: WorkItemClass = _CLASE) -> EntradaConmutacion:
    return EntradaConmutacion(
        instante=_instante(dia),
        clase=clase,
        autoridad=Autoridad.MOTOR,
        motivo="conmutación de prueba",
    )


def _linea_verde(
    dia: int, *, clase: WorkItemClass = _CLASE, work_id: str = _WORK_ID
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
    dia: int, *, clase: WorkItemClass = _CLASE, work_id: str = _WORK_ID, eje: str = EJE_ESTADO
) -> LineaRegistro:
    otro = EJE_FASE if eje == EJE_ESTADO else EJE_ESTADO
    return LineaRegistro(
        instante=_instante(dia),
        clase=clase,
        work_id=work_id,
        veredictos=(
            VeredictoEje(eje=otro, resultado=ResultadoEje.COINCIDE),
            VeredictoEje(
                eje=eje, resultado=ResultadoEje.DIVERGENCIA, motivo="motor=X incidencia=Y"
            ),
        ),
    )


def _linea_no_comparable(
    dia: int, *, clase: WorkItemClass = _CLASE, work_id: str = _WORK_ID
) -> LineaRegistro:
    return LineaRegistro(
        instante=_instante(dia),
        clase=clase,
        work_id=work_id,
        veredictos=(
            VeredictoEje(
                eje=EJE_FASE, resultado=ResultadoEje.NO_COMPARABLE, motivo="residencia normal"
            ),
            VeredictoEje(
                eje=EJE_ESTADO, resultado=ResultadoEje.NO_COMPARABLE, motivo="residencia normal"
            ),
        ),
    )


# --- 1. Se ha visto revertir ------------------------------------------------


def test_una_divergencia_sembrada_revierte_la_clase_conmutada() -> None:
    registro = (_conmutacion_a_motor(1),)
    lineas = (_linea_verde(2), _linea_divergente(3))

    resultado = evaluar_reversion(
        clase=_CLASE,
        registro_conmutaciones=registro,
        lineas_verificador=lineas,
        instante=_instante(4),
    )

    assert resultado.revierte is True
    assert resultado.entrada is not None
    assert resultado.entrada.clase is _CLASE
    assert resultado.entrada.autoridad is Autoridad.INCIDENCIA
    assert resultado.entrada.instante == _instante(4)
    assert "eje" in resultado.motivo
    assert resultado.aviso is not None


def test_tras_revertir_la_autoridad_de_la_clase_vuelve_a_ser_incidencia() -> None:
    registro = (_conmutacion_a_motor(1),)
    lineas = (_linea_divergente(3),)
    resultado = evaluar_reversion(
        clase=_CLASE,
        registro_conmutaciones=registro,
        lineas_verificador=lineas,
        instante=_instante(4),
    )
    assert resultado.entrada is not None

    registro_tras_revertir = (*registro, resultado.entrada)
    assert autoridad_de_clase(_CLASE, registro=registro_tras_revertir) is Autoridad.INCIDENCIA


def test_tras_revertir_el_contador_de_siete_dias_vuelve_a_cero() -> None:
    """Requisito 1: 'pone su contador a cero' -consecuencia directa de D1b, sin tocarlo.

    La divergencia que provoca la reversión ya rompe `es_verde` para ese
    día en el registro que D1b lee: no hace falta ningún código nuevo para
    que el contador vuelva a cero, es una propiedad del diseño compartido.
    """
    from sirius_engine.seven_day_streak import evaluar_racha

    lineas = (_linea_verde(1), _linea_verde(2), _linea_divergente(3))
    evaluacion = evaluar_racha(lineas=lineas, eventos=(), clase=_CLASE, hoy=_instante(3).date())
    assert evaluacion.cumple is False
    assert evaluacion.dias_consecutivos == 0


# --- 2. Se ha visto NO revertir: NO_COMPARABLE nunca cuenta -----------------


def test_una_tanda_entera_de_no_comparable_no_revierte() -> None:
    registro = (_conmutacion_a_motor(1),)
    lineas = tuple(_linea_no_comparable(dia) for dia in range(2, 10))

    resultado = evaluar_reversion(
        clase=_CLASE,
        registro_conmutaciones=registro,
        lineas_verificador=lineas,
        instante=_instante(10),
    )

    assert resultado.revierte is False
    assert resultado.entrada is None
    assert resultado.aviso is None


def test_lineas_verdes_no_revierten() -> None:
    registro = (_conmutacion_a_motor(1),)
    lineas = tuple(_linea_verde(dia) for dia in range(2, 10))

    resultado = evaluar_reversion(
        clase=_CLASE,
        registro_conmutaciones=registro,
        lineas_verificador=lineas,
        instante=_instante(10),
    )

    assert resultado.revierte is False


# --- Una clase no conmutada no se toca (requisito 6) ------------------------


def test_una_clase_nunca_conmutada_no_aplica() -> None:
    lineas = (_linea_divergente(3),)

    resultado = evaluar_reversion(
        clase=_CLASE, registro_conmutaciones=(), lineas_verificador=lineas, instante=_instante(4)
    )

    assert resultado.revierte is False
    assert resultado.entrada is None
    assert resultado.aviso is None
    assert "no es hoy autoridad del motor" in resultado.motivo


def test_una_clase_ya_revertida_no_aplica_de_nuevo() -> None:
    registro = (
        _conmutacion_a_motor(1),
        EntradaConmutacion(
            instante=_instante(4),
            clase=_CLASE,
            autoridad=Autoridad.INCIDENCIA,
            motivo="reversión previa",
        ),
    )
    lineas = (_linea_divergente(3),)

    resultado = evaluar_reversion(
        clase=_CLASE,
        registro_conmutaciones=registro,
        lineas_verificador=lineas,
        instante=_instante(10),
    )

    assert resultado.revierte is False


def test_una_divergencia_anterior_a_la_conmutacion_no_cuenta() -> None:
    """Divergir mientras la incidencia YA era la autoridad no es un defecto del motor."""
    registro = (_conmutacion_a_motor(5),)
    lineas = (_linea_divergente(2),)  # antes de conmutar

    resultado = evaluar_reversion(
        clase=_CLASE,
        registro_conmutaciones=registro,
        lineas_verificador=lineas,
        instante=_instante(10),
    )

    assert resultado.revierte is False


# --- A la primera, no a la segunda (requisito 5) ----------------------------


def test_revierte_en_la_primera_divergencia_no_en_la_ultima() -> None:
    registro = (_conmutacion_a_motor(1),)
    lineas = (
        _linea_verde(2),
        _linea_divergente(3, eje=EJE_ESTADO),
        _linea_divergente(4, eje=EJE_FASE),
    )

    resultado = evaluar_reversion(
        clase=_CLASE,
        registro_conmutaciones=registro,
        lineas_verificador=lineas,
        instante=_instante(10),
    )

    assert resultado.revierte is True
    assert resultado.entrada is not None
    assert f"el {_instante(3).isoformat()}" in resultado.motivo


# --- Idempotencia (requisito 7) ---------------------------------------------


def test_dos_pasadas_sobre_la_misma_divergencia_no_duplican(tmp_path: Path) -> None:
    ruta = tmp_path / "conmutaciones.jsonl"
    registro_inicial = (_conmutacion_a_motor(1),)
    anadir_entradas(ruta, registro_inicial)
    lineas = (_linea_divergente(3),)

    # Primera pasada: revierte y escribe.
    registro_leido = leer_registro_conmutaciones(ruta)
    primero = evaluar_reversion(
        clase=_CLASE,
        registro_conmutaciones=registro_leido,
        lineas_verificador=lineas,
        instante=_instante(4),
    )
    assert primero.revierte is True
    assert primero.entrada is not None
    escritas_1 = anadir_entradas(ruta, (primero.entrada,))
    assert escritas_1 == 1

    # Segunda pasada, misma divergencia: ya no aplica -la autoridad ya volvió.
    registro_leido_2 = leer_registro_conmutaciones(ruta)
    segundo = evaluar_reversion(
        clase=_CLASE,
        registro_conmutaciones=registro_leido_2,
        lineas_verificador=lineas,
        instante=_instante(5),
    )
    assert segundo.revierte is False

    assert len(leer_registro_conmutaciones(ruta)) == 2  # conmutación + una única reversión


# --- El registro es append-only y determinista (requisito 8) ---------------


def test_anadir_entradas_no_duplica_texto_identico(tmp_path: Path) -> None:
    ruta = tmp_path / "conmutaciones.jsonl"
    entrada = _conmutacion_a_motor(1)

    assert anadir_entradas(ruta, (entrada,)) == 1
    assert anadir_entradas(ruta, (entrada,)) == 0
    assert leer_registro_conmutaciones(ruta) == (entrada,)


def test_leer_registro_inexistente_es_vacio(tmp_path: Path) -> None:
    assert leer_registro_conmutaciones(tmp_path / "no-existe.jsonl") == ()


def test_anadir_entradas_nunca_reescribe_lo_anterior(tmp_path: Path) -> None:
    ruta = tmp_path / "conmutaciones.jsonl"
    primera = _conmutacion_a_motor(1)
    segunda = EntradaConmutacion(
        instante=_instante(10), clase=_CLASE, autoridad=Autoridad.INCIDENCIA, motivo="reversión"
    )

    anadir_entradas(ruta, (primera,))
    texto_tras_primera = ruta.read_text(encoding="utf-8")
    anadir_entradas(ruta, (segunda,))
    texto_tras_segunda = ruta.read_text(encoding="utf-8")

    assert texto_tras_segunda.startswith(texto_tras_primera)
    assert leer_registro_conmutaciones(ruta) == (primera, segunda)


# --- El aviso: texto en español, sin red -----------------------------------


def test_el_aviso_menciona_la_clase_y_el_motivo() -> None:
    entrada = EntradaConmutacion(
        instante=_instante(4),
        clase=_CLASE,
        autoridad=Autoridad.INCIDENCIA,
        motivo="divergencia en fase",
    )
    aviso = formatear_aviso_reversion(entrada)
    assert _CLASE.value in aviso
    assert "divergencia en fase" in aviso
    assert "§11.4" in aviso


@pytest.mark.parametrize("clase", (WorkItemClass.PROGRAMACION, WorkItemClass.AUDITORIA))
def test_evaluar_reversion_es_determinista_sin_red(clase: WorkItemClass) -> None:
    """No hace ninguna llamada de red: solo recorre lo que ya recibió (requisito 9)."""
    registro = (_conmutacion_a_motor(1, clase=clase),)
    lineas = (_linea_divergente(3, clase=clase),)

    primero = evaluar_reversion(
        clase=clase,
        registro_conmutaciones=registro,
        lineas_verificador=lineas,
        instante=_instante(4),
    )
    segundo = evaluar_reversion(
        clase=clase,
        registro_conmutaciones=registro,
        lineas_verificador=lineas,
        instante=_instante(4),
    )
    assert primero == segundo
