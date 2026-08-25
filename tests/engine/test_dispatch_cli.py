"""``sirius-despachar``: la costura entre una orden y la vía GitHub.

Las tres piezas existían y ninguna llamaba a la siguiente. Estas pruebas fijan
las propiedades de la costura, no las de las piezas -que ya tienen las suyas-.

La que más importa: **un ensayo no deja rastro**. Ni en GitHub ni en el diario
del motor. Un ensayo que persistiera un WorkItem ACTIVE sin despachar dejaría
trabajo activo que nadie atiende, que es justo el estado inconsistente del que
el resto del motor se cuida.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sirius_engine import dispatch_cli
from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.dispatcher import dispatch_work_item as _dispatch_real

_AHORA = datetime(2026, 8, 21, 22, 30, tzinfo=UTC)
_ORDEN = "Corrige la referencia rota a la seccion 6.7 del contrato"


def _correr(
    argv: list[str], *, diario: Path, entorno: dict[str, str] | None = None
) -> tuple[int, str]:
    salida = io.StringIO()
    codigo = dispatch_cli.main(
        [*argv, "--diario", str(diario)],
        entorno=entorno if entorno is not None else {},
        salida=salida,
        ahora=_AHORA,
    )
    return codigo, salida.getvalue()


def test_un_ensayo_no_escribe_en_github_ni_deja_rastro_en_el_diario(tmp_path: Path) -> None:
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr([_ORDEN], diario=diario)

    assert codigo == 0
    assert "ENSAYO" in texto
    assert "no se ha escrito nada en GitHub" in texto
    assert not diario.exists(), (
        "un ensayo que persiste el WorkItem deja trabajo ACTIVE que nadie va a "
        "despachar: el ensayo enseña qué pasaría, no lo hace a medias"
    )


def test_una_clase_no_despachable_no_crea_ningun_work_item(tmp_path: Path) -> None:
    """H-17: el rechazo por clase no despachable ocurre ANTES de crear el WorkItem.

    Antes, «documenta»/«investiga» pasaban la puerta como ORDEN_INEQUIVOCA
    (clase «documentacion»/«investigacion»), ``aplicar_decision`` creaba y
    activaba el WorkItem, y solo entonces ``dispatch_work_item`` levantaba
    ``ClaseNoDespachableError`` -sin capturar, así que el proceso terminaba con
    una traza y el WorkItem quedaba ACTIVE en el diario durable para un
    trabajo que ningún despachador va a atender nunca. Repetir la orden no
    idempotía nada -el work_id se deriva del instante, así que cada intento
    escribía OTRO WorkItem huérfano- y las entradas se acumulaban sin límite
    en un diario append-only.

    Desde la incidencia #336 (ADR-088) «documenta» sí tiene despachador -ver
    ``test_documenta_despacha_con_la_etiqueta_de_activacion_y_el_perfil_documentalista``-
    y desde la incidencia #349 (B1) «investiga» también -ver
    ``test_investiga_despacha_con_la_etiqueta_de_activacion_y_el_perfil_investigador``-,
    así que esta reproducción usa «prepara», que produce la clase
    «consulta-larga» y se queda fuera de la tabla cerrada de §12.4.
    """
    diario = tmp_path / "diario.jsonl"

    codigo, texto = _correr(
        ["Prepara un resumen del estado actual del motor", "--ejecutar"], diario=diario
    )

    assert codigo == 5, texto
    assert "No he creado nada" in texto
    assert "consulta-larga" in texto
    assert not diario.exists(), (
        "un WorkItem de clase no despachable no puede quedar escrito en el diario "
        "durable como ACTIVE: el rechazo tiene que ocurrir antes de crearlo"
    )

    # Repetir la misma orden no debe acumular una segunda entrada huérfana.
    codigo_2, texto_2 = _correr(
        ["Prepara un resumen del estado actual del motor", "--ejecutar"], diario=diario
    )
    assert codigo_2 == 5, texto_2
    assert not diario.exists()


def test_una_orden_ambigua_no_crea_nada_y_lo_explica(tmp_path: Path) -> None:
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(["Arregla eso cuando puedas"], diario=diario)

    assert codigo == 2
    assert "No he creado nada" in texto
    # Y dice POR QUÉ en términos que una persona pueda usar: el intérprete v0
    # reconoce pocos verbos, y no saberlo hace parecer roto lo que es limitado.
    assert "corrige" in texto and "implementa" in texto
    assert not diario.exists()


def test_ejecutar_sin_credencial_falla_pronto_y_dice_que_falta(tmp_path: Path) -> None:
    """C2-P5 en la costura: el fallo llega ANTES de tocar nada, no a mitad."""
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr([_ORDEN, "--ejecutar"], diario=diario, entorno={})

    assert codigo == 4
    assert "No puedo escribir en GitHub" in texto
    assert "SIRIUS_BOT_TOKEN" in texto


def test_ejecutar_despacha_y_solo_hace_las_dos_escrituras_enumeradas(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """La escritura es exactamente la enumerada: crear incidencia y etiquetar."""
    llamadas: list[str] = []

    class _EscritorDoble:
        def crear_incidencia(
            self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
        ) -> Any:
            llamadas.append("crear_incidencia")
            from sirius_engine.ports.github_writer import IncidenciaCreada

            return IncidenciaCreada(numero=4242, url=f"https://github.com/{repo}/issues/4242")

        def aplicar_etiqueta(self, *, repo: str, numero: int, etiqueta: str) -> None:
            llamadas.append("aplicar_etiqueta")

    monkeypatch.setattr(dispatch_cli, "GitHubCliWriter", lambda: _EscritorDoble())

    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr([_ORDEN, "--ejecutar"], diario=diario)

    assert codigo == 0, texto
    assert "4242" in texto
    assert llamadas == ["crear_incidencia", "aplicar_etiqueta"], (
        f"la escritura tiene que ser exactamente la enumerada; se hizo: {llamadas}"
    )
    # Al ejecutar de verdad SÍ persiste: el trabajo existe y hay que poder
    # reconstruir el episodio después sin preguntarle a GitHub.
    assert diario.exists()


def test_el_ensayo_atraviesa_el_despachador_de_verdad(tmp_path: Path, monkeypatch: Any) -> None:
    """H-12: un ensayo que se corta antes de las guardas no ensaya nada.

    Cuando el ensayo se detenía justo antes de ``dispatch_work_item`` decía
    «esto saldría» de un trabajo que el despachador rechazaba -y el rechazo
    solo aparecía al ejecutar de verdad, que es el momento en que ya no
    quieres enterarte-.
    """
    visto: list[str] = []
    real = _dispatch_real

    def _espia(work_item: Any, **kwargs: Any) -> Any:
        visto.append(type(kwargs["writer"]).__name__)
        return real(work_item, **kwargs)

    monkeypatch.setattr(dispatch_cli, "dispatch_work_item", _espia)

    codigo, texto = _correr([_ORDEN], diario=tmp_path / "diario.jsonl")

    assert codigo == 0
    assert visto == ["_EscritorDeEnsayo"], "el ensayo tiene que pasar por el despachador"
    assert "cuerpo que llevaría la incidencia" in texto


def test_la_orden_queda_enlazada_en_el_work_item_creado(tmp_path: Path) -> None:
    """Sin este enlace el despachador se niega a activar (contrato §12.1)."""
    from sirius_engine.domain.dispatch import MARCADOR_ORDEN_PROPIETARIO, orden_enlazada

    codigo, _ = _correr(
        [_ORDEN, "--ejecutar", "--orden-ref", "https://github.com/acme/repo/issues/9#c1"],
        diario=tmp_path / "diario.jsonl",
    )
    assert codigo == 4  # sin credencial no llega a escribir, pero ya creó el trabajo

    store = DurableWorkEngineStore(tmp_path / "diario.jsonl")
    work_item = store.get_work_item(f"WI-{_AHORA.strftime('%Y%m%d-%H%M%S')}")
    assert work_item is not None
    assert orden_enlazada(work_item) == "https://github.com/acme/repo/issues/9#c1"
    assert any(e.startswith(MARCADOR_ORDEN_PROPIETARIO) for e in work_item.evidencia)


# --- El despacho sobrevive al proceso (H-B de la incidencia #250) --------------


def test_repetir_la_misma_orden_no_crea_una_segunda_incidencia(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """C2-P3 entre procesos, no solo dentro de uno.

    El diario del despachador estaba cableado en memoria, así que cada
    invocación nacía sin memoria de lo ya despachado: repetir la orden creaba
    una SEGUNDA incidencia para el mismo trabajo, y de una incidencia cuelga un
    ciclo entero -implementador, Quality, dos revisores- sobre trabajo que ya
    estaba en marcha.

    Cada llamada a ``main`` construye sus adaptadores desde cero, igual que
    haría un proceso nuevo: es el reinicio que la prueba necesita.
    """
    creadas: list[str] = []

    class _EscritorQueCuenta:
        def crear_incidencia(
            self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
        ) -> Any:
            from sirius_engine.ports.github_writer import IncidenciaCreada

            creadas.append(titulo)
            return IncidenciaCreada(
                numero=100 + len(creadas),
                url=f"https://github.com/{repo}/issues/{100 + len(creadas)}",
            )

        def aplicar_etiqueta(self, *, repo: str, numero: int, etiqueta: str) -> None:
            return None

    monkeypatch.setattr(dispatch_cli, "GitHubCliWriter", lambda: _EscritorQueCuenta())
    diario = tmp_path / "diario.jsonl"

    primero, salida_1 = _correr([_ORDEN, "--ejecutar"], diario=diario)
    segundo, salida_2 = _correr([_ORDEN, "--ejecutar"], diario=diario)

    assert primero == 0, salida_1
    assert segundo == 0, salida_2
    assert len(creadas) == 1, (
        f"se crearon {len(creadas)} incidencias para el mismo trabajo; la garantía "
        "«una sola activación por WorkItem» no cruzó el proceso"
    )
    assert "Ya estaba despachado" in salida_2


def test_una_auditoria_declara_el_perfil_auditor_y_no_el_implementador(tmp_path: Path) -> None:
    """CODEX-001 (#256, ronda 2): el perfil declarado depende de la clase despachada.

    Antes ``PERFIL_POR_DEFECTO`` era ``implementer@1`` sin condición: una orden
    de auditoría se activaba por el carril del Auditor (``auditoria:solicitada``)
    mientras el cuerpo declaraba un perfil con permisos de implementación.
    Repite la reproducción exacta del hallazgo con la clase «auditoria».
    """
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(["Audita el repositorio buscando defectos concretos"], diario=diario)

    assert codigo == 0, texto
    assert "clase «auditoria»" in texto
    assert "Perfil: auditor@1" in texto
    assert "Perfil: implementer@1" not in texto


def test_una_programacion_sigue_declarando_el_perfil_implementador(tmp_path: Path) -> None:
    """La otra fila de la tabla cerrada (§12.4): la clase «programacion» no cambia."""
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr([_ORDEN], diario=diario)

    assert codigo == 0, texto
    assert "clase «programacion»" in texto
    assert "Perfil: implementer@1" in texto


def test_documenta_despacha_con_la_etiqueta_de_activacion_y_el_perfil_documentalista(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Requisito de la incidencia #336: una orden que empieza por «Documenta»
    da la vuelta completa del ciclo -misma etiqueta de activación que
    programación (ADR-088)- y declara ``Perfil: documentalista@1`` en el
    cuerpo, para que los workflows (ADR-088) elijan el prompt documental.
    """
    from sirius_engine.dispatcher import ETIQUETA_ACTIVACION

    llamadas: list[tuple[str, dict[str, Any]]] = []

    class _EscritorQueRegistra:
        def crear_incidencia(
            self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
        ) -> Any:
            from sirius_engine.ports.github_writer import IncidenciaCreada

            llamadas.append(("crear_incidencia", {"cuerpo": cuerpo, "etiquetas": etiquetas}))
            return IncidenciaCreada(numero=555, url=f"https://github.com/{repo}/issues/555")

        def aplicar_etiqueta(self, *, repo: str, numero: int, etiqueta: str) -> None:
            llamadas.append(("aplicar_etiqueta", {"etiqueta": etiqueta}))

    monkeypatch.setattr(dispatch_cli, "GitHubCliWriter", lambda: _EscritorQueRegistra())

    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(["Documenta el estado actual del motor", "--ejecutar"], diario=diario)

    assert codigo == 0, texto
    assert "clase «documentacion»" in texto
    verbos = [nombre for nombre, _ in llamadas]
    assert verbos == ["crear_incidencia", "aplicar_etiqueta"]
    _, args_creacion = llamadas[0]
    assert "Perfil: documentalista@1" in args_creacion["cuerpo"]
    _, args_etiqueta = llamadas[1]
    assert args_etiqueta["etiqueta"] == ETIQUETA_ACTIVACION


def test_investiga_despacha_con_la_etiqueta_de_activacion_y_el_perfil_investigador(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Requisito de la incidencia #349 (B1): una orden que empieza por
    «Investiga» da la vuelta completa del ciclo -misma etiqueta de activación
    que programación y documentación (ADR-088)- y declara
    ``Perfil: investigador@1`` en el cuerpo, para que los workflows elijan el
    prompt investigador.
    """
    from sirius_engine.dispatcher import ETIQUETA_ACTIVACION

    llamadas: list[tuple[str, dict[str, Any]]] = []

    class _EscritorQueRegistra:
        def crear_incidencia(
            self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
        ) -> Any:
            from sirius_engine.ports.github_writer import IncidenciaCreada

            llamadas.append(("crear_incidencia", {"cuerpo": cuerpo, "etiquetas": etiquetas}))
            return IncidenciaCreada(numero=556, url=f"https://github.com/{repo}/issues/556")

        def aplicar_etiqueta(self, *, repo: str, numero: int, etiqueta: str) -> None:
            llamadas.append(("aplicar_etiqueta", {"etiqueta": etiqueta}))

    monkeypatch.setattr(dispatch_cli, "GitHubCliWriter", lambda: _EscritorQueRegistra())

    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(["Investiga el estado actual del motor", "--ejecutar"], diario=diario)

    assert codigo == 0, texto
    assert "clase «investigacion»" in texto
    verbos = [nombre for nombre, _ in llamadas]
    assert verbos == ["crear_incidencia", "aplicar_etiqueta"]
    _, args_creacion = llamadas[0]
    assert "Perfil: investigador@1" in args_creacion["cuerpo"]
    _, args_etiqueta = llamadas[1]
    assert args_etiqueta["etiqueta"] == ETIQUETA_ACTIVACION


def test_el_diario_del_despachador_es_hermano_del_diario_del_motor(tmp_path: Path) -> None:
    """Diario propio, no el del motor: el de eventos no tiene sitio para «qué incidencia»."""
    diario = tmp_path / "sub" / "motor.jsonl"
    assert dispatch_cli._diario_de_despacho(diario) == tmp_path / "sub" / "motor-despacho.jsonl"
