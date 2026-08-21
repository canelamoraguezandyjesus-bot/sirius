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
