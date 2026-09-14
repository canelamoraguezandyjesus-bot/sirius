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
import json
import shlex
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any

import pytest

from sirius_engine import dispatch_cli
from sirius_engine import dispatch_cli as modulo_bajo_prueba
from sirius_engine import dispatcher as dispatcher_modulo
from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.carriles_retirados import carril_retirado as carril_retirado_real
from sirius_engine.dispatcher import dispatch_work_item as _dispatch_real

_AHORA = datetime(2026, 8, 21, 22, 30, tzinfo=UTC)
_ORDEN = "Corrige la referencia rota a la seccion 6.7 del contrato"


@pytest.fixture
def carril_activo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Describe el despacho **como si el carril no estuviera retirado**.

    Las pruebas que la usan fijan el diseño de los carriles de `auditoria` e
    `investigacion` -qué etiquetas reciben, qué perfil declaran, que sin orden
    enlazada no se despachan-. ADR-163 los desactiva, pero **no borra ese
    diseño**: `TABLA_ACTIVACION` conserva sus filas y el contrato §11.1 también,
    justamente para que reactivarlos sea quitar una línea del registro. Si estas
    pruebas se borraran, esa reversibilidad dejaría de estar cubierta y el día
    que el propietario reactivara un carril nadie sabría si seguía funcionando.

    No se falsea la función: se usa la de verdad contra un registro real y
    vacío, que es lo que habrá cuando el carril vuelva.
    """
    registro = tmp_path / "sin_carriles_retirados.json"
    registro.write_text(json.dumps({"version": 1, "carriles": {}}), encoding="utf-8")
    activo = partial(carril_retirado_real, registro=registro)
    # Dos sitios, porque hay dos comprobaciones: la del comando -que rechaza
    # antes de crear nada- y la del despachador, que es la defensa de fondo para
    # cualquier otro llamante. Parchear solo una dejaría la prueba describiendo
    # un mundo que no existe.
    monkeypatch.setattr(modulo_bajo_prueba, "carril_retirado", activo)
    monkeypatch.setattr(dispatcher_modulo, "carril_retirado", activo)


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

    Desde ADR-088 «documenta» tiene despachador, y desde ADR-099 (B1) también
    «investiga»: el intérprete v0 ya NO produce ninguna clase fuera de la tabla
    con texto real. La propiedad de H-17 sigue viva -la tabla es cerrada y
    consulta-larga/mixta siguen fuera-, así que la reproducción pasa a
    LABORATORIO: se fuerza la señal a clase consulta-larga y se comprueba lo
    mismo de siempre, que el rechazo ocurre antes de escribir nada.
    """
    from sirius_engine.domain.work_item import WorkItemClass as _Clase

    diario = tmp_path / "diario.jsonl"

    import dataclasses

    from sirius_engine.intent_interpreter import interpretar_intencion_v0 as señal_real

    def _consulta_larga(texto: str, **kwargs: Any) -> Any:
        señal = señal_real(texto, **kwargs)
        assert señal.datos_trabajo is not None
        return dataclasses.replace(
            señal,
            datos_trabajo=dataclasses.replace(señal.datos_trabajo, clase=_Clase.CONSULTA_LARGA),
        )

    import unittest.mock

    with unittest.mock.patch.object(dispatch_cli, "interpretar_intencion_v0", _consulta_larga):
        codigo, texto = _correr(
            ["Investiga el estado actual del motor", "--ejecutar"], diario=diario
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
            ["Investiga el estado actual del motor", "--ejecutar"], diario=diario
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


def test_una_auditoria_declara_el_perfil_auditor_y_no_el_implementador(
    tmp_path: Path, carril_activo: None
) -> None:
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
    assert "Perfil: implementer@" not in texto


def test_una_programacion_sigue_declarando_el_perfil_implementador(tmp_path: Path) -> None:
    """La otra fila de la tabla cerrada (§12.4): la clase «programacion» no cambia."""
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr([_ORDEN], diario=diario)

    assert codigo == 0, texto
    assert "clase «programacion»" in texto
    assert "Perfil: implementer@2" in texto


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

        def buscar_incidencia_por_work_id(self, *, repo: str, work_id: str) -> Any:
            return None

    monkeypatch.setattr(dispatch_cli, "GitHubCliWriter", lambda: _EscritorQueRegistra())

    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(["Documenta el estado actual del motor", "--ejecutar"], diario=diario)

    assert codigo == 0, texto
    assert "clase «documentacion»" in texto
    verbos = [nombre for nombre, _ in llamadas]
    assert verbos == ["crear_incidencia", "aplicar_etiqueta"]
    _, args_creacion = llamadas[0]
    assert "Perfil: documentalista@2" in args_creacion["cuerpo"]
    _, args_etiqueta = llamadas[1]
    assert args_etiqueta["etiqueta"] == ETIQUETA_ACTIVACION


def test_el_diario_del_despachador_es_hermano_del_diario_del_motor(tmp_path: Path) -> None:
    """Diario propio, no el del motor: el de eventos no tiene sitio para «qué incidencia»."""
    diario = tmp_path / "sub" / "motor.jsonl"
    assert dispatch_cli.diario_de_despacho(diario) == tmp_path / "sub" / "motor-despacho.jsonl"


def test_investiga_despacha_con_la_etiqueta_de_activacion_y_el_perfil_investigador(
    tmp_path: Path, monkeypatch: Any, carril_activo: None
) -> None:
    """B1 (ADR-099): una orden que empieza por «Investiga» da la vuelta
    completa -mismas etiquetas que programación y documentación- y declara
    ``Perfil: investigador@1`` en el cuerpo, que es lo que separa a su
    ejecutor (el investigador medido de ADR-098) del agente implementador.
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

        def buscar_incidencia_por_work_id(self, *, repo: str, work_id: str) -> Any:
            return None

    monkeypatch.setattr(dispatch_cli, "GitHubCliWriter", lambda: _EscritorQueRegistra())

    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(
        ["Investiga cual es la ultima version estable de Python", "--ejecutar"], diario=diario
    )

    assert codigo == 0, texto
    assert "clase «investigacion»" in texto
    verbos = [nombre for nombre, _ in llamadas]
    assert verbos == ["crear_incidencia", "aplicar_etiqueta"]
    _, args_creacion = llamadas[0]
    assert "Perfil: investigador@2" in args_creacion["cuerpo"]
    _, args_etiqueta = llamadas[1]
    assert args_etiqueta["etiqueta"] == ETIQUETA_ACTIVACION


def test_la_ruta_del_diario_sale_copiable_aunque_tenga_espacios(tmp_path: Path) -> None:
    """La instrucción de recuperación se copia y se pega: tiene que sobrevivir al
    intérprete de la consola. Con una ruta con espacios, sin entrecomillar, el
    comando se parte -«/tmp/Sirius» a `--diario` y el resto al `mensaje`
    posicional- y `sirius-motor` abre otro diario sin protestar (CODEX-001).

    Antes del cambio fallaba en la primera aserción: el texto llevaba la ruta
    desnuda, y `shlex.split` devolvía cinco argumentos en vez de tres.
    """
    directorio = tmp_path / "Sirius motor"
    directorio.mkdir()
    diario = directorio / "diario.jsonl"
    codigo, texto = _correr(["Borra la base de produccion", "--ejecutar"], diario=diario)

    assert codigo == 3, texto
    linea = next(fila for fila in texto.splitlines() if "sirius-motor --diario" in fila)
    comando = linea[linea.index("«") + 1 : linea.index("»")]
    assert shlex.split(comando) == ["sirius-motor", "--diario", str(diario)], (
        "la ruta tiene que llegar entera como valor de --diario, no partida en dos"
    )


def test_una_parada_dice_donde_queda_el_trabajo_y_como_volver_a_el(tmp_path: Path) -> None:
    """ADR-184. Una parada crea el trabajo en `needs_decision` y NO lo despacha,
    así que queda anotado en el diario sin incidencia detrás. Eso está bien -es
    su situación real, y el diario es append-only-, pero el mensaje solo daba el
    work_id y la causa: quien lo leía no sabía que el trabajo seguía ahí ni cómo
    volver a él, y por eso quedaban huérfanos. Tres hay hoy en el diario del
    motor (`WI-20260903-030529`, `WI-20260903-095428`, `WI-20260912-235558`).

    Antes del cambio fallaba con ``AssertionError`` en la primera aserción del
    bloque de recuperación: el texto no nombraba ni `needs_decision` ni
    `/trabajos`.
    """
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(["Borra la base de produccion", "--ejecutar"], diario=diario)

    assert codigo == 3, texto
    assert "NO lo he despachado" in texto
    assert "operacion_destructiva_o_irreversible" in texto
    assert "needs_decision" in texto, "quien lee tiene que saber en qué estado quedó"
    assert "/trabajos" in texto, "y por dónde volver a encontrarlo"
    # Y con la ruta del diario en el que está de verdad: `sirius-motor` sin
    # argumentos resuelve OTRO diario -el suyo por defecto, o el de
    # `SIRIUS_MOTOR_DIARIO`-, así que la instrucción sin ruta lleva a una
    # sesión vacía (`cli.resolver_diario`).
    assert f"sirius-motor --diario {shlex.quote(str(diario))}" in texto, (
        "el paso indicado tiene que abrir ESTE diario, no el que resuelva por defecto"
    )

    # Y el trabajo está de verdad ahí, en ese estado: el mensaje no promete un
    # sitio vacío.
    store = DurableWorkEngineStore(diario)
    work_item = store.get_work_item("WI-20260821-223000")
    assert work_item is not None
    assert work_item.estado.value == "needs_decision"


def test_una_parada_dice_con_que_orden_se_sale_de_ella(tmp_path: Path) -> None:
    """ADR-189. ADR-184 hizo que la parada dijera DÓNDE queda el trabajo; faltaba
    decir CÓMO sale de ahí, y no salía: de `needs_decision` solo sale
    `resolve_decision`, cuyo único llamante de producción era el reflector, que
    necesita una incidencia que mirar. Las cuatro paradas del diario del motor
    llevaban hasta diez días sin salida (medido el 13-09-2026).

    La orden sale con el work_id y la ruta del diario ya puestos: reconstruirla a
    mano es donde se pierde, y el diario que `sirius-decidir` resuelva por defecto
    no tiene por qué ser este.

    Antes del cambio fallaba en la primera aserción con ``AssertionError: la parada
    tiene que decir con qué orden se sale``: el texto no nombraba `sirius-decidir`.
    Y se la vio caer también con la orden a medias -dejando el bloque pero quitando
    `--diario` de la orden copiable-, en ``AssertionError: la orden tiene que poder
    copiarse tal cual; salió ['sirius-decidir', 'WI-20260821-223000', '--ejecutar',
    '--terminar']``.
    """
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(
        ["Corrige el arranque y borra la base de produccion", "--ejecutar"], diario=diario
    )

    assert codigo == 3, texto
    assert "sirius-decidir" in texto, "la parada tiene que decir con qué orden se sale"
    linea = next(
        fila for fila in texto.splitlines() if "sirius-decidir" in fila and "--terminar" in fila
    )
    orden = shlex.split(linea.split("#")[0])
    assert orden == [
        "sirius-decidir",
        "WI-20260821-223000",
        "--diario",
        str(diario),
        "--ejecutar",
        "--terminar",
    ], f"la orden tiene que poder copiarse tal cual; salió {orden}"
    assert "--continuar" in texto, "las dos mitades de la decisión, no solo una"


def test_la_orden_de_la_parada_arrastra_el_repo_y_el_bloque_de_la_orden_original(
    tmp_path: Path,
) -> None:
    """CLAUDE-R2-002: `--repo` y `--bloque` no los guarda nadie.

    El `WorkItem` no los persiste -`aplicar_decision` no los recibe- y el diario
    tampoco, así que el único sitio donde sobreviven es la orden que la parada
    imprime. Si no los arrastra, quien despachó contra `otra-org/otro-repo` con
    bloque `AUDITORIA` copia la orden tal cual -que es justo lo que el bloque
    promete- y `--continuar` crea la incidencia en el repositorio y con el
    encargo POR DEFECTO: una escritura externa e irreversible al destino
    equivocado, de la que cuelga un ciclo entero en cuanto le llega
    `sirius:implement-requested`.

    Antes del cambio fallaba con la orden a medias: ``['sirius-decidir',
    'WI-20260821-223000', '--diario', <ruta>, '--ejecutar', '--continuar']``.
    """
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(
        [
            "Corrige el arranque y borra la base de produccion",
            "--ejecutar",
            "--repo",
            "otra-org/otro-repo",
            "--bloque",
            "AUDITORIA",
        ],
        diario=diario,
    )

    assert codigo == 3, texto
    linea = next(
        fila for fila in texto.splitlines() if "sirius-decidir" in fila and "--continuar" in fila
    )
    orden = shlex.split(linea.split("#")[0])
    assert orden == [
        "sirius-decidir",
        "WI-20260821-223000",
        "--diario",
        str(diario),
        "--ejecutar",
        "--repo",
        "otra-org/otro-repo",
        "--bloque",
        "AUDITORIA",
        "--continuar",
    ], f"la orden tiene que despachar donde pidió la original; salió {orden}"


def test_con_repo_y_bloque_por_defecto_la_orden_de_la_parada_no_los_repite(
    tmp_path: Path,
) -> None:
    """La otra mitad de CLAUDE-R2-002: arrastrarlos es condicional.

    `sirius-decidir` comparte los valores por defecto de `sirius-despachar`
    (`REPO` y «ENCARGO»), así que repetirlos cuando nadie los cambió solo alarga
    la orden corriente sin decir nada. Esta prueba fija que el caso corriente
    sigue siendo el de `test_una_parada_dice_con_que_orden_se_sale_de_ella`.
    """
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(
        ["Corrige el arranque y borra la base de produccion", "--ejecutar"], diario=diario
    )

    assert codigo == 3, texto
    linea = next(
        fila for fila in texto.splitlines() if "sirius-decidir" in fila and "--continuar" in fila
    )
    orden = shlex.split(linea.split("#")[0])
    assert "--repo" not in orden and "--bloque" not in orden, (
        f"sin cambiarlos no se repiten los valores por defecto; salió {orden}"
    )


def test_una_parada_de_la_quinta_causa_no_ofrece_continuar(tmp_path: Path) -> None:
    """ADR-188 + ADR-189: ahí `--continuar` no existe, y ofrecerlo sería mentir.

    Continuar es despachar, y despachar esta orden la mata en el push: es la
    pérdida de la #607, que ADR-188 vino a impedir. La salida que sí tiene -la
    sesión interactiva, y `--terminar` cuando ya no haga falta- ya la dice el
    bloque de ADR-188.

    Antes del cambio fallaba en la segunda aserción: el bloque de la salida
    ofrecía `--continuar` sin condición, en una parada en la que no lleva a
    ninguna parte.
    """
    orden = "Implementa el aviso que falta en `.github/workflows/despachar-orden.yml`"
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr([orden, "--ejecutar"], diario=diario)

    assert codigo == 3, texto
    assert "sirius-decidir" in texto and "--terminar" in texto
    ofrecidas = [
        fila for fila in texto.splitlines() if "sirius-decidir" in fila and "--continuar" in fila
    ]
    assert ofrecidas == [], (
        f"ofrecer continuar aquí es prometer un despacho que muere en el push: {ofrecidas}"
    )
    assert "no está disponible en esta parada" in texto, "y hay que decir por qué no está"


def test_una_parada_de_una_clase_sin_despachador_tampoco_ofrece_continuar(
    tmp_path: Path,
) -> None:
    """La otra mitad de la anterior: la quinta causa no es el único «--continuar» muerto.

    «Borra la base de producción» para por la CUARTA causa -destructiva-, no por
    la quinta, así que `prefijo_vetado` es `None`; pero el intérprete v0 no la
    clasifica como programación y el trabajo nace con clase «consulta-larga»,
    que no está en `TABLA_ACTIVACION`. `sirius-decidir --continuar --ejecutar`
    sobre ese trabajo sale con código 5 -lo fija
    `test_decision_cli.py::test_una_clase_sin_despachador_no_se_reanuda`-, así
    que ofrecer aquí esa orden es prometer un despacho que no va a ocurrir: la
    misma familia que prometer un sitio vacío (ADR-184, ADR-188, ADR-189).

    Las dos mitades de la demostración estaban en esta PR y nadie las juntaba.
    Antes del cambio fallaba en `ofrecidas == []`: el bloque solo descartaba la
    quinta causa.
    """
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(["Borra la base de produccion", "--ejecutar"], diario=diario)

    assert codigo == 3, texto
    ofrecidas = [
        fila for fila in texto.splitlines() if "sirius-decidir" in fila and "--continuar" in fila
    ]
    assert ofrecidas == [], (
        f"«sirius-decidir --continuar» saldría con 5 sobre este trabajo: {ofrecidas}"
    )
    assert "--terminar" in texto, "la salida que sí tiene sigue ofreciéndose"
    assert "no tiene" in texto and "despachador" in texto, "y hay que decir por qué no está"


def test_una_parada_con_alcance_vetado_no_ofrece_continuar_aunque_parara_otra_causa(
    tmp_path: Path,
) -> None:
    """El ofrecimiento lo decide el ALCANCE, no la causa (CLAUDE-R3-001).

    «Corrige el arranque y borra `.github/workflows/quality.yml`» para por la
    CUARTA causa -el marcador «borra»-, así que `prefijo_vetado` es `None` y el
    bloque de atribución de ADR-188 no sale, que es lo correcto. Pero la clase es
    `programacion`, tiene despachador y su carril sigue vivo: nada impedía
    ofrecer `--continuar`. Y continuar es despachar una orden cuyo alcance cae
    bajo `.github/`, donde el motor no puede escribir (ADR-002): el ciclo haría
    el trabajo entero y lo perdería al empujar, la #607 otra vez.

    Mutación vista caer: devolviendo `alcance_vetado=prefijo_vetado` en la
    llamada a `_por_que_no_se_puede_continuar`, la prueba falla en
    ``ofrecidas == []`` con la línea «sirius-decidir ... --continuar    #
    continúa: crea la incidencia».
    """
    orden = "Corrige el arranque y borra `.github/workflows/quality.yml`"
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr([orden, "--ejecutar"], diario=diario)

    assert codigo == 3, texto
    ofrecidas = [
        fila for fila in texto.splitlines() if "sirius-decidir" in fila and "--continuar" in fila
    ]
    assert ofrecidas == [], f"despachar esta orden la mata en el push, como la #607: {ofrecidas}"
    assert "--terminar" in texto, "la salida que sí tiene sigue ofreciéndose"
    assert "no está disponible en esta parada" in texto, "y hay que decir por qué no está"
    assert "operacion_destructiva_o_irreversible" in texto, (
        "la atribución de la causa NO cambia: paró la cuarta, y eso es lo que se dice"
    )


def test_una_parada_en_ensayo_no_promete_un_sitio_donde_no_hay_nada(tmp_path: Path) -> None:
    """La gemela sin `--ejecutar` de la anterior, que es el modo POR DEFECTO.

    En ensayo el almacén es el de memoria: el trabajo NO queda anotado en
    ningún diario y muere con el proceso. El mensaje de recuperación decía lo
    contrario sin condición -«queda anotado en el diario en estado
    «needs_decision»», y abre `sirius-motor` y teclea `/trabajos`-, que es
    exactamente el sitio vacío que ADR-184 dice no prometer. Peor: el aviso
    «ENSAYO: no se ha escrito nada en GitHub» está DESPUÉS del `return 3` de
    esta rama, así que quien paraba en ensayo ni siquiera sabía que lo era.
    """
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr(["Borra la base de produccion"], diario=diario)

    assert codigo == 3, texto
    assert "NO lo he despachado" in texto
    assert "operacion_destructiva_o_irreversible" in texto
    assert "ENSAYO" in texto, "quien para en ensayo tiene que saber que es un ensayo"
    assert "--ejecutar" in texto, "y qué hacer para que el trabajo quede anotado de verdad"
    assert "/trabajos" not in texto, "no hay nada que listar: el trabajo no se ha anotado"
    assert not diario.exists(), (
        "un ensayo no escribe nada, así que el mensaje no puede remitir a un diario"
    )


# --- ADR-188: la parada ocurre ANTES de crear la incidencia ------------------


def test_un_encargo_con_alcance_vetado_para_antes_de_crear_la_incidencia(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """El sitio de la parada es el punto entero de ADR-188.

    La incidencia #607 se despachó, el ciclo arrancó, el encargo hizo el trabajo
    entero y GitHub rechazó el push: una hora de motor perdida por una regla que
    solo vivía en la cabeza de quien despacha. Parar DESPUÉS de crear la
    incidencia no habría servido de nada. Así que aquí se comprueba lo único
    que importa: que ni el escritor de GitHub ni el despachador llegan a
    tocarse, ni siquiera con `--ejecutar`.

    Antes del cambio fallaba -observado revirtiendo `dispatch_cli.py` e
    `intent_interpreter.py` a main- con ``AssertionError: no se puede construir
    el escritor de GitHub en esta parada``, levantada por `_escritor_prohibido`
    desde `writer = GitHubCliWriter()` (dispatch_cli.py:353 en main). La orden
    salía como orden inequívoca y el flujo llegaba al escritor; como el único
    try/except del módulo captura solo MissingCredentialError, la AssertionError
    se propagaba fuera de `main` y de `_correr`, así que la prueba no alcanzaba
    ninguna aserción y `llamadas` quedaba en ``['GitHubCliWriter']`` -una sola
    anotación, no las dos: `dispatch_work_item` nunca se llegaba a llamar-.
    """
    llamadas: list[str] = []

    def _escritor_prohibido() -> Any:
        llamadas.append("GitHubCliWriter")
        raise AssertionError("no se puede construir el escritor de GitHub en esta parada")

    def _despachador_prohibido(*_args: Any, **_kwargs: Any) -> Any:
        llamadas.append("dispatch_work_item")
        raise AssertionError("no se puede llegar al despachador en esta parada")

    monkeypatch.setattr(dispatch_cli, "GitHubCliWriter", _escritor_prohibido)
    monkeypatch.setattr(dispatch_cli, "dispatch_work_item", _despachador_prohibido)

    orden = (
        "Corrige que la puerta del corrector no confirme su etiqueta consumible "
        "contra el estado vigente, en .github/workflows/repair-sirius-work.yml"
    )
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr([orden, "--ejecutar"], diario=diario)

    assert codigo == 3, texto
    assert llamadas == [], (
        f"no se puede escribir nada en GitHub en esta parada; se hizo: {llamadas}"
    )
    assert "permisos_o_credenciales_sensibles" in texto

    # Y el trabajo queda donde el mensaje promete: `needs_decision`, sin
    # incidencia detrás. Es su situación real, no un residuo (ADR-184).
    store = DurableWorkEngineStore(diario)
    work_item = store.get_work_item("WI-20260821-223000")
    assert work_item is not None
    assert work_item.estado.value == "needs_decision"


def test_la_parada_dice_por_que_para_y_remite_a_la_sesion_interactiva(tmp_path: Path) -> None:
    """ADR-188 (c), al nivel de detalle que ADR-184 fijó: un mensaje que promete
    un sitio vacío es peor que ninguno.

    `permisos_o_credenciales_sensibles` a secas no le dice a nadie que el
    trabajo es legítimo y que solo cambia de sitio. El mensaje tiene que decir
    el alcance que lo paró, por qué el motor no llega ahí, a dónde va ese
    trabajo, y traer la orden lista para copiar -sin ella, quien lee tiene que
    reconstruirla a mano, que es justo donde se pierde-.

    Antes del cambio fallaba -observado revirtiendo `dispatch_cli.py` e
    `intent_interpreter.py` a main- en la PRIMERA aserción, la del código de
    salida (`assert codigo == 3`), con ``assert 4 == 3``: la orden salía como
    orden inequívoca, el comando construía el GitHubCliWriter real y sin
    SIRIUS_BOT_TOKEN salía por MissingCredentialError con código 4. Lo que
    fijan las aserciones SEGUNDA y TERCERA -que el texto nombre el alcance
    `.github/` y ADR-002- no llegaba a comprobarse; ese texto tampoco existía,
    pero el rojo que se ve al revertir es el del código de salida.
    """
    orden = "Implementa el aviso que falta en `.github/workflows/despachar-orden.yml`"
    diario = tmp_path / "diario.jsonl"
    codigo, texto = _correr([orden, "--ejecutar"], diario=diario)

    assert codigo == 3, texto
    assert ".github/" in texto, "el mensaje tiene que decir QUÉ alcance lo paró"
    assert "ADR-002" in texto, "y por qué el motor no puede escribir ahí"
    assert "sesión interactiva" in texto, "y a dónde va ese trabajo en vez del ciclo"
    assert orden in texto, "la orden tiene que salir entera y lista para copiar"
    # Lo de ADR-184 sigue: dónde queda el trabajo y cómo volver a él.
    assert "needs_decision" in texto
    assert f"sirius-motor --diario {shlex.quote(str(diario))}" in texto


def test_una_orden_que_no_toca_esa_carpeta_se_sigue_despachando_como_hoy(tmp_path: Path) -> None:
    """La otra mitad, exigida por el encargo: no debilitar lo que ya hay.

    Una orden legítima -incluida la que nombra la carpeta solo para excluirla,
    que es como están escritas 19 de las 29 del diario- tiene que llegar al
    despachador igual que antes.
    """
    orden = "Corrige la referencia rota a la seccion 6.7 del contrato. No toques `.github/**`."
    codigo, texto = _correr([orden], diario=tmp_path / "diario.jsonl")

    assert codigo == 0, texto
    assert "cuerpo que llevaría la incidencia" in texto
    assert "NO lo he despachado" not in texto


def test_una_parada_por_una_causa_anterior_no_promete_el_despacho_de_la_quinta(
    tmp_path: Path,
) -> None:
    """La quinta explica; las cuatro anteriores ganan. El bloque no puede hacer las dos cosas.

    Esta orden dispara las dos: es destructiva Y nombra la carpeta vetada. El
    intérprete consulta la quinta DESPUÉS, así que para por destructiva -lo fija
    `test_las_cuatro_causas_anteriores_siguen_ganando_a_la_quinta`-. El comando,
    en cambio, decidía mirando SOLO el texto de la orden, así que imprimía el
    bloque entero de ADR-188 encima de una causa que no era la suya: atribuía la
    parada al alcance («Por eso la parada ocurre AQUÍ») dos líneas después de
    haber anunciado otra causa, y remataba prometiendo que negando la mención de
    la carpeta la orden se despacharía. No se despacharía: volvería a parar por
    destructiva. Un mensaje que promete un despacho que no va a ocurrir es la
    misma familia que uno que promete un sitio vacío, que es la que ADR-184
    cerró para este mismo mensaje.

    Antes del cambio fallaba con ``AssertionError`` en la aserción de la
    promesa: el texto traía «vuelve a despachar» y el «no toques .github/**».
    """
    orden = "Borra la cola y arregla .github/workflows/quality.yml"
    codigo, texto = _correr([orden, "--ejecutar"], diario=tmp_path / "diario.jsonl")

    assert codigo == 3, texto
    assert "operacion_destructiva_o_irreversible" in texto, (
        "la causa que para sigue siendo la anterior, y es la que se anuncia"
    )
    assert "vuelve a despachar" not in texto, (
        "negando la carpeta esta orden NO se despacha: sigue parando por destructiva"
    )
    # CLAUDE-R3-001: lo que esta prueba fija es la ATRIBUCIÓN, y ahí «sesión
    # interactiva» sigue sin poder aparecer. Donde sí aparece -y tiene que
    # aparecer- es en el paréntesis que NIEGA «--continuar»: el alcance vetado
    # hace indespachable este trabajo pare por la causa que pare, y quitarle la
    # salida sin decir cuál le queda es el sitio vacío que ADR-184 cerró.
    fuera_del_rechazo = [
        fila for fila in texto.splitlines() if "sesión interactiva" in fila and "#607" not in fila
    ]
    assert fuera_del_rechazo == [], (
        f"la parada no la produjo el alcance: nada la remite a ADR-002 salvo el rechazo "
        f"de «--continuar»: {fuera_del_rechazo}"
    )
    assert "la parada ocurre AQUÍ" not in texto, (
        "la parada no la produjo el alcance, así que no puede atribuírsele"
    )


def test_la_quinta_causa_sigue_dando_su_bloque_cuando_es_ella_la_que_para(
    tmp_path: Path,
) -> None:
    """La otra mitad de la anterior, para que el arreglo no sea «no imprimir nunca».

    Sin esta, apagar el bloque entero dejaría la prueba de arriba en verde y
    borraría lo que ADR-188 vino a añadir.
    """
    orden = "Implementa el aviso que falta en `.github/workflows/despachar-orden.yml`"
    codigo, texto = _correr([orden, "--ejecutar"], diario=tmp_path / "diario.jsonl")

    assert codigo == 3, texto
    assert "sesión interactiva" in texto
    assert "vuelve a despachar" in texto
