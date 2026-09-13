"""``sirius-decidir``: la salida que a una parada de la puerta le faltaba (ADR-189).

Lo que estas pruebas fijan no son las piezas -el dominio, la puerta y el
despachador ya tienen las suyas- sino las dos propiedades de la salida:

1. **Una parada sin incidencia puede salir**, y la saca una orden del
   propietario: hasta ahora `NEEDS_DECISION` era un estado en el que el motor
   entraba solo y del que nadie podía sacarlo, porque su única arista
   -`resolve_decision`- solo la llamaba el reflector, y el reflector necesita
   una incidencia que mirar.
2. **Reanudar es despachar en el mismo gesto.** Ninguna ruta del comando puede
   dejar un trabajo en `active` sin incidencia detrás por una razón que se
   pudiera saber antes: eso sería cambiar una fuga por otra.

Cada prueba dice en su docstring la mutación con la que se la vio caer
(ADR-001 §3).
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from sirius_engine import decision_cli, dispatch_cli
from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.adapters.github_cli_writer import GitHubWriteError, MissingCredentialError
from sirius_engine.carriles_retirados import CarrilRetirado
from sirius_engine.dispatcher import dispatch_work_item as _dispatch_real
from sirius_engine.domain.work_item import WorkItemClass
from sirius_engine.ports.github_writer import IncidenciaCreada

_AHORA = datetime(2026, 8, 21, 22, 30, tzinfo=UTC)
_WORK_ID = f"WI-{_AHORA.strftime('%Y%m%d-%H%M%S')}"

#: Una orden que la puerta para por la CUARTA causa (operación destructiva) y
#: cuya clase es `programacion`, que es la de las cuatro paradas que el diario
#: real contiene. No es la quinta a propósito: la quinta tiene su propia prueba y
#: su propio desenlace.
_ORDEN_QUE_PARA = "Corrige el arranque y borra la base de produccion"

#: Una orden sensible cuya clase NO tiene despachador: el verbo «borra» no es
#: ninguno de los que el intérprete v0 reconoce como programación, así que sale
#: `consulta-larga`. No hace falta forzar nada para reproducir el caso.
_ORDEN_SIN_DESPACHADOR = "Borra la base de produccion"

#: Una orden que la puerta para por la QUINTA causa (ADR-188): el alcance cae
#: donde la credencial del motor no llega.
_ORDEN_DE_LA_QUINTA = "Implementa el aviso que falta en `.github/workflows/despachar-orden.yml`"


class _EscritorQueCrea:
    """Escritor de GitHub falso: cuenta lo que se le pide y no toca la red."""

    def __init__(self, numero: int = 777) -> None:
        self.numero = numero
        self.llamadas: list[str] = []

    def crear_incidencia(
        self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
    ) -> IncidenciaCreada:
        self.llamadas.append("crear_incidencia")
        self.titulo = titulo
        self.cuerpo = cuerpo
        return IncidenciaCreada(
            numero=self.numero, url=f"https://github.com/{repo}/issues/{self.numero}"
        )

    def aplicar_etiqueta(self, *, repo: str, numero: int, etiqueta: str) -> None:
        self.llamadas.append("aplicar_etiqueta")
        self.etiqueta = etiqueta

    def buscar_incidencia_por_work_id(self, *, repo: str, work_id: str) -> IncidenciaCreada | None:
        self.llamadas.append("buscar_incidencia_por_work_id")
        return None


class _EscritorQueFalla:
    """Escritor que revienta al crear: el corte entre las dos escrituras."""

    def crear_incidencia(
        self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
    ) -> IncidenciaCreada:
        raise GitHubWriteError(["gh", "issue", "create"], "la red se fue")

    def aplicar_etiqueta(self, *, repo: str, numero: int, etiqueta: str) -> None:
        raise AssertionError("no se llega a etiquetar si no se creó nada")

    def buscar_incidencia_por_work_id(self, *, repo: str, work_id: str) -> IncidenciaCreada | None:
        return None


def _parar(diario: Path, orden: str = _ORDEN_QUE_PARA) -> None:
    """Dejar en ``diario`` una parada de verdad, por el camino de producción.

    No se construye a mano: se ejecuta ``sirius-despachar`` con una orden que la
    puerta para. Así el trabajo de partida es exactamente el que el diario real
    contiene -``needs_decision``, un solo suceso, sin incidencia detrás- y no una
    aproximación de laboratorio.
    """
    salida = io.StringIO()
    codigo = dispatch_cli.main(
        [orden, "--ejecutar", "--diario", str(diario)], entorno={}, salida=salida, ahora=_AHORA
    )
    assert codigo == 3, salida.getvalue()


def _decidir(argv: list[str], *, diario: Path) -> tuple[int, str]:
    salida = io.StringIO()
    codigo = decision_cli.main(
        [*argv, "--diario", str(diario)], entorno={}, salida=salida, ahora=_AHORA
    )
    return codigo, salida.getvalue()


def _estado(diario: Path, work_id: str = _WORK_ID) -> str:
    item = DurableWorkEngineStore(diario).get_work_item(work_id)
    assert item is not None
    return item.estado.value


def _hay_episodio(diario: Path, work_id: str = _WORK_ID) -> bool:
    from sirius_engine.adapters.durable.dispatch_journal import DurableDispatchJournal

    return (
        DurableDispatchJournal(dispatch_cli.diario_de_despacho(diario)).episode_for(work_id)
        is not None
    )


# --- La salida existe --------------------------------------------------------


def test_una_parada_sin_incidencia_se_da_por_terminada_por_orden_del_propietario(
    tmp_path: Path,
) -> None:
    """La propiedad entera de ADR-189: de `needs_decision` ya se puede salir.

    Antes de este comando no había ninguna vía: medido el 13-09-2026 sobre el
    diario de `estado-del-motor`, las cuatro paradas que existen seguían las
    cuatro ahí, con un solo suceso en su historia y sin incidencia detrás, la
    más antigua desde hacía diez días.

    Mutación vista caer: cambiando `continuar=False` por `continuar=True` en
    `_terminar`, la prueba falla en la última aserción con
    ``AssertionError: assert 'active' == 'cancelled'``.
    """
    diario = tmp_path / "diario.jsonl"
    _parar(diario)
    assert _estado(diario) == "needs_decision"

    codigo, texto = _decidir([_WORK_ID, "--terminar", "--ejecutar"], diario=diario)

    assert codigo == 0, texto
    assert "Terminado" in texto
    assert _estado(diario) == "cancelled", "cancelled es terminal: la parada ya no espera nada"


def test_terminar_dos_veces_no_es_un_error_ni_cambia_nada(tmp_path: Path) -> None:
    """Repetir la orden es idempotente: el estado ya es terminal y se dice.

    Mutación vista caer: quitando la rama `estado is CANCELLED` de `_terminar`,
    la segunda invocación sale con 4 y la prueba falla en ``assert codigo == 0``,
    con el texto «no está en «needs_decision», sino en «cancelled»».
    """
    diario = tmp_path / "diario.jsonl"
    _parar(diario)
    _decidir([_WORK_ID, "--terminar", "--ejecutar"], diario=diario)

    codigo, texto = _decidir([_WORK_ID, "--terminar", "--ejecutar"], diario=diario)

    assert codigo == 0, texto
    assert "ya estaba terminado" in texto
    assert _estado(diario) == "cancelled"


def test_el_ensayo_es_lo_que_sale_por_defecto_y_no_aplica_nada(tmp_path: Path) -> None:
    """Sin `--ejecutar` no se toca el almacén, en las dos decisiones.

    Mismo criterio que `sirius-despachar`: una decisión sobre el identificador
    equivocado no es barata, y de `cancelled` no se vuelve.

    Mutación vista caer: quitando la guarda `if not ejecutar` de `_terminar`, la
    prueba falla en ``assert "ENSAYO" in texto`` -la salida dice «Terminado:
    queda en cancelled»- y el trabajo queda cancelado sin habérselo pedido.
    """
    diario = tmp_path / "diario.jsonl"
    _parar(diario)

    codigo, texto = _decidir([_WORK_ID, "--terminar"], diario=diario)
    assert codigo == 0, texto
    assert "ENSAYO" in texto
    assert _estado(diario) == "needs_decision"

    codigo, texto = _decidir([_WORK_ID, "--continuar"], diario=diario)
    assert codigo == 0, texto
    assert "ENSAYO" in texto
    assert _estado(diario) == "needs_decision"
    assert not _hay_episodio(diario)


def test_el_ensayo_de_continuar_atraviesa_el_despachador_de_verdad(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """H-12 otra vez: un ensayo que se corta antes de las guardas no ensaya nada.

    Si el ensayo no pasara por `dispatch_work_item`, diría «esto se despacharía»
    de un trabajo que el despachador rechazaría, y el rechazo aparecería al
    ejecutar de verdad -el momento en que ya no quieres enterarte-.

    Mutación vista caer: devolviendo el ensayo antes de llamar al despachador, la
    prueba falla en ``AssertionError: assert [] == ['_EscritorDeEnsayo']``.
    """
    visto: list[str] = []
    real = _dispatch_real

    def _espia(work_item: Any, **kwargs: Any) -> Any:
        visto.append(type(kwargs["writer"]).__name__)
        return real(work_item, **kwargs)

    monkeypatch.setattr(decision_cli, "dispatch_work_item", _espia)
    diario = tmp_path / "diario.jsonl"
    _parar(diario)

    codigo, texto = _decidir([_WORK_ID, "--continuar"], diario=diario)

    assert codigo == 0, texto
    assert visto == ["_EscritorDeEnsayo"], "el ensayo tiene que pasar por el despachador"
    assert "sirius:implement-requested" in texto


# --- Reanudar es despachar en el mismo gesto ---------------------------------


def test_continuar_reanuda_y_despacha_en_el_mismo_gesto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El punto (b) del encargo: al reanudar, el trabajo NO queda sin incidencia.

    `resolve_decision(continuar=True)` a secas deja el trabajo en `active` sin
    nada detrás, y ahí nadie lo atiende -el reflector se lo salta por no
    constar despachado-. Así que las dos cosas ocurren en la misma invocación.

    Mutación vista caer: quitando la llamada a `dispatch_work_item` de
    `_continuar`, la prueba falla en ``assert "#901" in texto`` y el trabajo queda
    en `active` sin episodio -la fuga exacta que ADR-189 cierra-.
    """
    escritor = _EscritorQueCrea(numero=901)
    monkeypatch.setattr(decision_cli, "GitHubCliWriter", lambda: escritor)
    diario = tmp_path / "diario.jsonl"
    _parar(diario)

    codigo, texto = _decidir([_WORK_ID, "--continuar", "--ejecutar"], diario=diario)

    assert codigo == 0, texto
    assert "#901" in texto
    assert _estado(diario) == "active"
    assert escritor.llamadas == ["crear_incidencia", "aplicar_etiqueta"]
    assert _hay_episodio(diario), (
        "reanudado sin incidencia detrás: esa es la fuga que ADR-189 cierra"
    )


def test_sin_credencial_no_se_reanuda_nada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """La misma propiedad por el camino que más fácil se olvida.

    Si el escritor se construyera DESPUÉS de la transición, una credencial que
    falta -el caso corriente en una máquina recién montada- dejaría el trabajo
    en `active` sin incidencia y sin salida. Se comprueba antes.

    Mutación vista caer: moviendo la construcción de `GitHubCliWriter` a después
    de `resolve_work_item_decision`, la prueba falla en
    ``AssertionError: assert 'active' == 'needs_decision'``.
    """

    def _sin_credencial() -> Any:
        raise MissingCredentialError("SIRIUS_BOT_TOKEN")

    monkeypatch.setattr(decision_cli, "GitHubCliWriter", _sin_credencial)
    diario = tmp_path / "diario.jsonl"
    _parar(diario)

    codigo, texto = _decidir([_WORK_ID, "--continuar", "--ejecutar"], diario=diario)

    assert codigo == 6, texto
    assert "NO he reanudado" in texto
    assert _estado(diario) == "needs_decision"
    assert not _hay_episodio(diario)


def test_una_clase_sin_despachador_no_se_reanuda(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reanudar lo que nadie va a atender es la misma fuga con otra cara.

    La comprobación de clase de `sirius-despachar` (H-17) solo cubre el camino
    `CREAR_Y_ACTIVAR`: por el de la parada no pasa, así que el diario puede
    contener -y contiene, en cuanto la orden no empieza por un verbo de
    programación- paradas de una clase que ningún despachador atiende.
    Reanudarlas las dejaría `active` sin nada detrás.

    El escritor falso está puesto a propósito: sin él, quitar la comprobación
    haría caer la prueba por la credencial que falta, y eso no demostraría nada
    sobre la clase.

    Mutación vista caer: quitando la comprobación de clase de
    `_no_se_puede_despachar`, la prueba falla con ``ClaseNoDespachableError: work
    item 'WI-20260821-223000' has class 'consulta-larga'; the dispatcher only
    handles...``, levantada por `dispatch_work_item` SIN capturar y con el trabajo
    ya reanudado a `active` sin incidencia detrás.
    """
    monkeypatch.setattr(decision_cli, "GitHubCliWriter", lambda: _EscritorQueCrea(numero=904))
    diario = tmp_path / "diario.jsonl"
    _parar(diario, _ORDEN_SIN_DESPACHADOR)

    codigo, texto = _decidir([_WORK_ID, "--continuar", "--ejecutar"], diario=diario)

    assert codigo == 5, texto
    assert "consulta-larga" in texto
    assert "--terminar" in texto, "la salida que sí tiene tiene que estar dicha"
    assert _estado(diario) == "needs_decision"


def test_una_parada_sin_orden_enlazada_no_se_reanuda(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Contrato §12.1 sin excepción: sin orden enlazada el despachador no activa.

    Laboratorio a propósito: `sirius-despachar` siempre enlaza la orden, así que
    la parada se construye contra el almacén para reproducir un diario que no lo
    hiciera -o un trabajo nacido por otra vía-.

    Mutación vista caer: quitando la comprobación de `orden_enlazada` de
    `_no_se_puede_despachar`, la prueba falla con ``OrdenNoEnlazadaError: work item
    'WI-SIN-ORDEN' has no owner order linked in its evidence`` -el comando reanuda
    y el despachador la levanta sin capturar-.
    """
    monkeypatch.setattr(decision_cli, "GitHubCliWriter", lambda: _EscritorQueCrea(numero=905))
    diario = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(diario)
    store.create_and_escalate_work_item(
        work_id="WI-SIN-ORDEN",
        peticion_original="Corrige lo que sea",
        objetivo="Corrige lo que sea",
        contexto_origen=("sesion-cli",),
        entregable="El cambio",
        criterio_terminado="Las validaciones en verde",
        limites={},
        prioridad=3,
        clase=WorkItemClass.PROGRAMACION,
        now=_AHORA,
        evidencia=(),
    )

    codigo, texto = _decidir(["WI-SIN-ORDEN", "--continuar", "--ejecutar"], diario=diario)

    assert codigo == 5, texto
    assert "§12.1" in texto
    assert _estado(diario, "WI-SIN-ORDEN") == "needs_decision"


# --- ADR-188: la quinta causa no sale por aquí -------------------------------


def test_una_parada_de_la_quinta_causa_no_se_reanuda_y_remite_a_la_sesion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reanudar la quinta causa sería repetir la pérdida de la #607 (ADR-188).

    El alcance de la orden cae donde la credencial del motor no llega (ADR-002):
    despacharla crea la incidencia, el ciclo hace el trabajo entero y GitHub
    rechaza el push. La parada de ADR-188 ocurre ANTES de crear la incidencia
    justo por eso, y `--continuar` es literalmente despachar.

    Mutación vista caer: quitando la llamada a `_bloque_de_la_quinta_causa` de
    `_continuar`, la prueba falla en ``assert codigo == 5`` con el texto de un
    despacho consumado -«queda en active y despachado. Incidencia #999»-: el
    comando despacha justo la orden que ADR-188 declaró indespachable.
    """
    monkeypatch.setattr(decision_cli, "GitHubCliWriter", lambda: _EscritorQueCrea(numero=999))
    diario = tmp_path / "diario.jsonl"
    _parar(diario, _ORDEN_DE_LA_QUINTA)

    codigo, texto = _decidir([_WORK_ID, "--continuar", "--ejecutar"], diario=diario)

    assert codigo == 5, texto
    assert ".github/" in texto, "tiene que decir QUÉ alcance lo impide"
    assert "ADR-002" in texto
    assert "sesión interactiva" in texto, "y a dónde va ese trabajo"
    assert _ORDEN_DE_LA_QUINTA in texto, "la orden, lista para copiar"
    assert _estado(diario) == "needs_decision"
    assert not _hay_episodio(diario)


def test_una_parada_de_la_quinta_causa_si_se_puede_terminar(tmp_path: Path) -> None:
    """La otra mitad: que no se pueda reanudar no la deja otra vez sin salida.

    Mutación vista caer: haciendo que `_terminar` consulte también
    `_bloque_de_la_quinta_causa` y rechace, la prueba falla en ``assert 5 == 0``
    y el trabajo se queda en `needs_decision` para siempre, que es exactamente el
    defecto que ADR-189 arregla.
    """
    diario = tmp_path / "diario.jsonl"
    _parar(diario, _ORDEN_DE_LA_QUINTA)

    codigo, texto = _decidir([_WORK_ID, "--terminar", "--ejecutar"], diario=diario)

    assert codigo == 0, texto
    assert _estado(diario) == "cancelled"


# --- El despacho a medias se retoma (la lección de ADR-176) ------------------


def test_un_despacho_cortado_a_la_mitad_se_retoma_en_la_invocacion_siguiente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El único hueco que queda no deja otro trabajo inmortal.

    La transición y la escritura en GitHub son dos escrituras y no se pueden
    hacer atómicas. Si la segunda falla, el trabajo queda `active` sin
    incidencia -el estado del que nadie sale-, así que repetir la MISMA orden
    retoma el despacho desde el estado en el que el motor ESTÁ (ADR-176), en vez
    de rechazarlo por no estar ya en `needs_decision`.

    Mutación vista caer: quitando `ACTIVE` de `_ESTADOS_QUE_CONTINUAN`, la
    segunda invocación sale con 4 («no está en needs_decision») y la prueba
    falla en ``assert 4 == 0``, con el trabajo varado en `active` sin incidencia.
    """
    monkeypatch.setattr(decision_cli, "GitHubCliWriter", lambda: _EscritorQueFalla())
    diario = tmp_path / "diario.jsonl"
    _parar(diario)

    codigo, texto = _decidir([_WORK_ID, "--continuar", "--ejecutar"], diario=diario)
    assert codigo == 7, texto
    assert "el despacho FALLÓ" in texto
    assert _estado(diario) == "active"
    assert not _hay_episodio(diario), "la escritura no llegó a grabarse"

    escritor = _EscritorQueCrea(numero=902)
    monkeypatch.setattr(decision_cli, "GitHubCliWriter", lambda: escritor)
    codigo, texto = _decidir([_WORK_ID, "--continuar", "--ejecutar"], diario=diario)

    assert codigo == 0, texto
    assert "#902" in texto
    assert _hay_episodio(diario), "el despacho tiene que retomarse, no atascarse"
    assert _estado(diario) == "active"
    assert "buscar_incidencia_por_work_id" in escritor.llamadas, (
        "con intención pendiente se adopta por work_id antes de crear otra (H-29)"
    )


# --- Lo que este comando NO resuelve ----------------------------------------


def test_un_trabajo_con_incidencia_detras_no_lo_decide_este_comando(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Con incidencia detrás, el desenlace lo acredita GitHub, no esta orden.

    El caso no es hipotético: el reflector escala a `needs_decision` un encargo
    YA despachado como primer paso del cierre que ADR-173 aplica -`escalate` y
    después `resolve_decision(continuar=False)`-, y ADR-176 cuenta que la pasada
    se puede cortar justo entre los dos. Ese trabajo está en `needs_decision` CON
    incidencia: decidirlo aquí dejaría la incidencia abierta contando otra cosa y
    pisaría el cierre que el reflector sabe retomar.

    Mutación vista caer: quitando la guarda de `episodio_previo`, la prueba falla
    en ``assert codigo == 3`` con el texto «Terminado: … queda en «cancelled»»: el
    comando cancela en el almacén un trabajo cuya incidencia #903 sigue abierta.
    """
    escritor = _EscritorQueCrea(numero=903)
    monkeypatch.setattr(dispatch_cli, "GitHubCliWriter", lambda: escritor)
    diario = tmp_path / "diario.jsonl"
    salida = io.StringIO()
    codigo = dispatch_cli.main(
        [
            "Corrige la referencia rota a la seccion 6.7 del contrato",
            "--ejecutar",
            "--diario",
            str(diario),
        ],
        entorno={},
        salida=salida,
        ahora=_AHORA,
    )
    assert codigo == 0, salida.getvalue()
    # El primer paso del cierre de ADR-173, sin el segundo: el estado en el que
    # una pasada cortada deja al encargo.
    DurableWorkEngineStore(diario).escalate_work_item(_WORK_ID, now=_AHORA)
    assert _estado(diario) == "needs_decision"

    codigo, texto = _decidir([_WORK_ID, "--terminar", "--ejecutar"], diario=diario)

    assert codigo == 3, texto
    assert "#903" in texto
    assert "sirius-reflejar" in texto, "hay que decir quién sí lo resuelve"
    assert _estado(diario) == "needs_decision", "no se toca nada: el cierre lo retoma el reflector"


def test_un_identificador_que_no_existe_no_inventa_nada(tmp_path: Path) -> None:
    """Un work_id mal teclado no crea ni cambia nada, y dice dónde mirar.

    Mutación vista caer: devolviendo 0 en vez de 2 cuando el trabajo no existe,
    la prueba falla en ``assert 0 == 2`` y el comando daría por hecho algo que
    no ocurrió.
    """
    diario = tmp_path / "diario.jsonl"
    _parar(diario)

    codigo, texto = _decidir(["WI-NO-EXISTE", "--terminar", "--ejecutar"], diario=diario)

    assert codigo == 2, texto
    assert "/trabajos" in texto, "hay que decir dónde se ven los que sí hay"
    assert _estado(diario) == "needs_decision", "el que sí existe no se toca"


def test_hay_que_decir_que_se_decide(tmp_path: Path) -> None:
    """Ni `--continuar` ni `--terminar` por defecto: la decisión se dice.

    Un valor por defecto aquí sería el motor decidiendo por el propietario, que
    es justo lo que la puerta se negó a hacer.
    """
    with pytest.raises(SystemExit) as error:
        _decidir([_WORK_ID], diario=tmp_path / "diario.jsonl")
    assert error.value.code == 2


def test_sin_credencial_al_retomar_no_dice_needs_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLAUDE-R1-002: el estado se nombra, no se fija en el texto.

    Este comando admite DOS estados de partida (`_ESTADOS_QUE_CONTINUAN`), y al
    retomar un despacho cortado el trabajo está en `active`. El mensaje de la
    credencial que falta afirmaba en literal «sigue en «needs_decision»,
    intacto», que ahí es falso justo cuando el propietario necesita saber dónde
    quedó el trabajo -la familia que abrió ADR-184-.

    Antes del cambio fallaba en la última aserción: el texto traía
    «needs_decision» sobre un trabajo que el diario tiene en «active».
    """
    monkeypatch.setattr(decision_cli, "GitHubCliWriter", lambda: _EscritorQueFalla())
    diario = tmp_path / "diario.jsonl"
    _parar(diario)
    codigo, _ = _decidir([_WORK_ID, "--continuar", "--ejecutar"], diario=diario)
    assert codigo == 7
    assert _estado(diario) == "active"

    def _sin_credencial() -> Any:
        raise MissingCredentialError("SIRIUS_BOT_TOKEN")

    monkeypatch.setattr(decision_cli, "GitHubCliWriter", _sin_credencial)
    codigo, texto = _decidir([_WORK_ID, "--continuar", "--ejecutar"], diario=diario)

    assert codigo == 6, texto
    assert _estado(diario) == "active", "sin credencial no se toca nada"
    assert "«active»" in texto, "el estado que se nombra es el real"
    assert "needs_decision" not in texto, texto


def test_un_trabajo_active_rechazado_no_ofrece_terminar_que_no_existe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLAUDE-R1-003: `--terminar` solo es salida desde `needs_decision`.

    `_terminar` exige ese estado y sale con 4 sin tocar nada, porque el dominio
    no tiene arista `ACTIVE -> CANCELLED` (§3.2). Un trabajo `active` sin
    incidencia cuyo carril se retire después -`carriles_retirados.json` es un
    dato que se cambia fusionando- tiene `--continuar` rechazado con 5 y
    `--terminar` rechazado con 4: ofrecerle «--terminar» es prometer una salida
    que no existe. El dominio NO se toca: lo que se corrige es el texto.

    Antes del cambio fallaba en la aserción de «--terminar»: el rechazo lo
    ofrecía sin mirar el estado.
    """
    monkeypatch.setattr(decision_cli, "GitHubCliWriter", lambda: _EscritorQueFalla())
    diario = tmp_path / "diario.jsonl"
    _parar(diario)
    codigo, _ = _decidir([_WORK_ID, "--continuar", "--ejecutar"], diario=diario)
    assert codigo == 7
    assert _estado(diario) == "active"

    retirado = CarrilRetirado(
        clase="programacion",
        retirado_por="ADR-999",
        ejecutado_por="la prueba",
        fecha="2026-09-13",
        motivo="el carril se retiró después de reanudar este trabajo",
        a_donde_va="a sesión interactiva",
    )
    monkeypatch.setattr(decision_cli, "carril_retirado", lambda clase: retirado)

    codigo, texto = _decidir([_WORK_ID, "--continuar", "--ejecutar"], diario=diario)
    assert codigo == 5, texto
    assert "«--terminar» tampoco" in texto, texto
    assert "§3.2" in texto, "y por qué no: el dominio no admite cancelar desde active"

    # La otra mitad: el texto no miente, `--terminar` de verdad sale con 4.
    monkeypatch.undo()
    codigo, texto = _decidir([_WORK_ID, "--terminar", "--ejecutar"], diario=diario)
    assert codigo == 4, texto
    assert _estado(diario) == "active"
