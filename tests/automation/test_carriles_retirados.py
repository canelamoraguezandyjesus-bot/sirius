"""Las entradas de un carril retirado quedan cerradas, y las de los vivos no (ADR-163).

Lo que estas pruebas existen para impedir es el defecto que el inventario de
ADR-163 encontró: **una entrada retirada que se queda esperando, o que acaba en
programación por otra ruta**. Investigación comparte la etiqueta de activación
con programación y se reparte por el campo ``Perfil:``; si se desactivara solo
``investigar-orden.yml`` la activación quedaría colgada, y si se quitara la
puerta del implementador se implementaría como programación.

CÓMO PRUEBAN, tras ADR-167: las puertas se **ejecutan**. La revisión de ADR-163
encontró cinco fallos que ninguna prueba de este fichero vio porque comprobaban
que el guion *mencionaba* ``sirius_comment_once`` o ``sirius:failed-safely``, no
lo que pasaba al correrlo. Ahora el arnés
(``tests/automation/fixtures/carriles_retirados/``) extrae el guion real del
paso, lo corre con ``bash`` contra un ``gh`` doble —sin red ni credenciales— y
devuelve lo observable: **código de salida, comentarios publicados, etiquetas
finales y la lista de llamadas**. Una puerta que dijera «hecho» sin haberlo
hecho cae aquí.

La prueba que ata las entradas es
:func:`test_toda_entrada_de_un_carril_retirado_esta_cubierta`: **enumera los
disparadores desde el árbol**, no de una lista escrita a mano, así que un
workflow nuevo que reaccione a esas etiquetas y no consulte el registro la hace
caer.

Deterministas: leen ficheros y ejecutan guiones de shell contra dobles
explícitos. No lanzan ningún agente, no tocan el registro real y no gastan
ninguna API.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from carriles_retirados.arnes import (
    Resultado,
    cuerpo_de_orden,
    ejecutar_paso,
    incidencia_activa,
)

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = RAIZ / "docs" / "implementation" / "work_engine" / "carriles_retirados.json"
LECTOR = RAIZ / "scripts" / "automation" / "sirius_carril_retirado.py"
WORKFLOWS = RAIZ / ".github" / "workflows"

#: Los carriles que ADR-161 AUTORIZA retirar, y la etiqueta por la que entra cada
#: uno. Autorizar no es obligar: el registro puede tener los dos, uno o ninguno
#: -eso es lo que significa que la retirada sea reversible-, pero no puede tener
#: uno que ADR-161 no cubra.
CARRILES = {"investigacion": "sirius:implement-requested", "auditoria": "auditoria:solicitada"}

#: Los campos que toda entrada del registro debe traer, esté quien esté.
CAMPOS = ("retirado_por", "ejecutado_por", "fecha", "motivo", "a_donde_va")

#: El marcador de idempotencia del comentario de la puerta de investigación.
#: Tiene que estar EN el cuerpo publicado: `sirius_comment_once` deduplica
#: buscándolo en los comentarios ya existentes, así que un marcador que solo
#: viviera en la llamada no deduplicaría nada (hallazgo 4 de ADR-167).
MARCADOR = "<!-- sirius-carril-retirado:investigacion -->"

TERMINALES = ("sirius:completed", "sirius:failed-safely", "sirius:blocked-decision")


def _registro() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(REGISTRO.read_text(encoding="utf-8"))
    return datos


def _workflow(nombre: str) -> dict[str, Any]:
    datos: dict[str, Any] = yaml.safe_load((WORKFLOWS / nombre).read_text(encoding="utf-8"))
    return datos


def _pasos(nombre: str, job: str) -> list[dict[str, Any]]:
    pasos: list[dict[str, Any]] = _workflow(nombre)["jobs"][job]["steps"]
    return pasos


def _guion(nombre: str, job: str, step_id: str) -> str:
    for paso in _pasos(nombre, job):
        if paso.get("id") == step_id:
            return str(paso["run"])
    raise AssertionError(f"{nombre}: no existe el paso {step_id!r} en {job!r}")


def _entrada(clase: str) -> dict[str, str]:
    return {
        "retirado_por": "ADR-161",
        "ejecutado_por": "ADR-163",
        "fecha": "2026-09-07",
        "motivo": f"prueba del carril {clase}",
        "a_donde_va": "a la memoria común",
    }


def _registro_controlado(tmp_path: Path, *clases: str, nombre: str = "registro.json") -> Path:
    """Un registro de prueba con exactamente las clases pedidas. Nunca el real."""
    ruta = tmp_path / nombre
    ruta.write_text(
        json.dumps({"carriles": {clase: _entrada(clase) for clase in clases}}, ensure_ascii=False),
        encoding="utf-8",
    )
    return ruta


def _validar_registro(datos: dict[str, Any]) -> list[str]:
    """Las comprobaciones de formato y seguridad del registro, en un solo sitio.

    Se aplican igual al registro real y a cualquier configuración de prueba: es
    lo que permite demostrar que una reactivación válida las pasa sin tener que
    tocar el registro de verdad. Devuelve la lista de defectos; vacía es válido.
    """
    fallos: list[str] = []
    carriles = datos.get("carriles")
    if not isinstance(carriles, dict):
        return ["el registro no declara un objeto «carriles»"]
    for clase, fila in carriles.items():
        if clase not in CARRILES:
            fallos.append(f"{clase}: ADR-161 no autoriza retirar esta clase")
            continue
        if not isinstance(fila, dict):
            fallos.append(f"{clase}: la entrada no es un objeto")
            continue
        for campo in CAMPOS:
            if not str(fila.get(campo, "")).strip():
                fallos.append(f"{clase}: falta el campo {campo!r}")
    return fallos


def _incidencia_de(resultado: Resultado, **cambios: Any) -> dict[str, Any]:
    """El estado que dejó una ejecución, como entrada de la siguiente.

    Es lo que hace comprobable la CONVERGENCIA: la segunda pasada no parte de
    una incidencia limpia, sino exactamente de lo que quedó tras la primera.
    """
    incidencia: dict[str, Any] = {
        "labels": list(resultado.etiquetas),
        "comments": list(resultado.comentarios),
        "state": resultado.estado_incidencia,
        "body": cuerpo_de_orden(),
    }
    incidencia.update(cambios)
    return incidencia


def _puerta_investigacion(tmp_path: Path, **kwargs: Any) -> Resultado:
    return ejecutar_paso("investigar-orden.yml", "investigar", "gate", tmp_path=tmp_path, **kwargs)


def _puerta_auditoria(tmp_path: Path, **kwargs: Any) -> Resultado:
    kwargs.setdefault("incidencia", {"labels": ["auditoria:solicitada"], "comments": []})
    return ejecutar_paso(
        "audit-sirius-repository.yml", "auditar", "retirada", tmp_path=tmp_path, **kwargs
    )


# --------------------------------------------------------------------------
# El registro: formato y seguridad, sin congelar el estado de hoy
# --------------------------------------------------------------------------


def test_el_registro_real_es_valido() -> None:
    """Lo que haya declarado tiene que estar bien declarado.

    Esta prueba NO exige que los dos carriles consten retirados. Exigirlo -como
    hacía antes de ADR-167- convertía la reactivación documentada, que es quitar
    una entrada y fusionar, en una prueba roja: la propiedad reversible que
    ADR-161 pedía quedaba prohibida por su propia suite. Lo que sí se sostiene
    en cualquier configuración es esto: solo clases autorizadas, y con todos sus
    campos.
    """
    assert _validar_registro(_registro()) == []


@pytest.mark.parametrize(
    "clases",
    [
        pytest.param(("investigacion", "auditoria"), id="los-dos-retirados-como-hoy"),
        pytest.param(("auditoria",), id="investigacion-reactivada"),
        pytest.param(("investigacion",), id="auditoria-reactivada"),
        pytest.param((), id="los-dos-reactivados"),
    ],
)
def test_toda_reactivacion_documentada_es_una_configuracion_valida(
    tmp_path: Path, clases: tuple[str, ...]
) -> None:
    """Las cuatro configuraciones posibles pasan las comprobaciones del registro."""
    datos = json.loads(_registro_controlado(tmp_path, *clases).read_text(encoding="utf-8"))
    assert _validar_registro(datos) == []


@pytest.mark.parametrize(
    ("roto", "esperado"),
    [
        ({"carriles": {"investigacion": {"retirado_por": "ADR-161"}}}, "falta el campo"),
        ({"carriles": {"programacion": _entrada("programacion")}}, "no autoriza"),
        ({"carriles": []}, "no declara un objeto"),
    ],
)
def test_las_comprobaciones_del_registro_de_verdad_rechazan(
    roto: dict[str, Any], esperado: str
) -> None:
    """La validación se ve FALLAR: si no, no prueba nada de la de arriba."""
    fallos = _validar_registro(roto)
    assert fallos, "un registro mal formado tenía que dar defectos"
    assert any(esperado in f for f in fallos), fallos


def test_la_clase_sigue_en_la_tabla_de_activacion_y_en_el_contrato() -> None:
    """Retirar no es borrar: la fila se conserva, y por eso reactivar es una línea.

    Si alguien 'limpiara' `TABLA_ACTIVACION`, el rechazo pasaría a ser
    `ClaseNoDespachableError` -«esta clase nunca tuvo despachador»- y se
    perdería la distinción que ADR-163 existe para conservar.
    """
    from sirius_engine.dispatcher import TABLA_ACTIVACION
    from sirius_engine.domain.work_item import WorkItemClass

    assert WorkItemClass.INVESTIGACION in TABLA_ACTIVACION
    assert WorkItemClass.AUDITORIA in TABLA_ACTIVACION


# --------------------------------------------------------------------------
# El despachador
# --------------------------------------------------------------------------


@pytest.mark.parametrize("clase", sorted(CARRILES))
def test_el_despachador_rechaza_un_carril_retirado_con_su_explicacion(
    tmp_path: Path, clase: str
) -> None:
    from sirius_engine.carriles_retirados import carril_retirado

    entrada = carril_retirado(clase, registro=_registro_controlado(tmp_path, clase))
    assert entrada is not None, f"{clase} debería constar como retirado"
    explicacion = entrada.explicacion()
    assert "retirado" in explicacion
    assert "A dónde va ahora" in explicacion, "quien lo pide tiene que saber a dónde ir"
    assert "carriles_retirados.json" in explicacion, "y cómo se revierte"


@pytest.mark.parametrize("clase", ["programacion", "documentacion"])
def test_las_clases_vivas_no_constan_retiradas(clase: str) -> None:
    from sirius_engine.carriles_retirados import carril_retirado

    assert carril_retirado(clase) is None


def test_el_rechazo_del_despachador_es_un_error_propio_y_no_el_generico() -> None:
    """`nunca tuvo despachador` y `lo tuvo y se retiró` no son lo mismo."""
    from sirius_engine.domain.errors import CarrilRetiradoError, ClaseNoDespachableError

    assert issubclass(CarrilRetiradoError, Exception)
    # Que mypy sepa que son tipos distintos es justo lo que se quiere: la prueba
    # fija que el despachador NO reutiliza el error genérico, y por eso compara
    # los nombres -comparar los tipos sería una identidad que el comprobador ya
    # resuelve, y no probaría nada en ejecución-.
    assert CarrilRetiradoError.__name__ != ClaseNoDespachableError.__name__
    assert not issubclass(CarrilRetiradoError, ClaseNoDespachableError)


# --------------------------------------------------------------------------
# El lector que usan los workflows: contrato de códigos (hallazgo 3)
# --------------------------------------------------------------------------


def _leer(clase: str, *, registro: Path | None = None) -> subprocess.CompletedProcess[str]:
    orden = [sys.executable, str(LECTOR), clase]
    if registro is not None:
        orden += ["--registro", str(registro)]
    return subprocess.run(orden, capture_output=True, text=True, cwd=RAIZ)


@pytest.mark.parametrize("clase", sorted(CARRILES))
def test_el_lector_dice_retirado_con_codigo_cero(tmp_path: Path, clase: str) -> None:
    proceso = _leer(clase, registro=_registro_controlado(tmp_path, clase))
    assert proceso.returncode == 0, proceso.stderr
    assert "retirado" in proceso.stdout


def test_el_lector_dice_activo_con_codigo_uno(tmp_path: Path) -> None:
    proceso = _leer("investigacion", registro=_registro_controlado(tmp_path, "auditoria"))
    assert proceso.returncode == 1
    assert proceso.stdout.strip() == "", "un carril activo no lleva explicación"


def test_un_registro_ilegible_no_se_lee_como_carril_activo(tmp_path: Path) -> None:
    """Fail-closed en la afirmación: no poder leer no es «está activo».

    Si un registro roto devolviera 1, el workflow concluiría que el carril sigue
    vivo y dejaría pasar el trabajo por un carril retirado.
    """
    roto = tmp_path / "roto.json"
    roto.write_text("{esto no es json", encoding="utf-8")
    assert _leer("auditoria", registro=roto).returncode == 2


# --------------------------------------------------------------------------
# Las entradas reales, enumeradas desde el árbol
# --------------------------------------------------------------------------


def test_toda_entrada_de_un_carril_retirado_esta_cubierta() -> None:
    """La guarda que no envejece: enumera los disparadores, no los da por sabidos.

    Cualquier workflow que reaccione a la etiqueta de entrada de un carril **que
    conste retirado** tiene que consultar el registro, o declarar por qué no le
    hace falta. Añadir uno nuevo sin cerrarlo hace caer esta prueba.

    Se recorre el REGISTRO, no la lista de clases autorizadas: si un carril se
    reactiva, su entrada vuelve a ser una entrada normal y ya no hay nada que
    cerrar.
    """
    # El implementador reacciona a la etiqueta compartida y NO consulta el
    # registro a propósito: su papel es declinar el perfil para que el carril
    # retirado lo atienda quien sabe responderlo. Se declara aquí, con su
    # motivo, en vez de dejarlo como un hueco silencioso.
    exentos = {
        # Declina el perfil `investigador` ANTES de consumir el evento: no
        # atiende el carril, lo aparta para que lo atienda quien sabe cerrarlo.
        "implement-sirius-work.yml": "declina el perfil investigador; no lo atiende",
        # Solo valida que la activación sea legítima y retira el evento si no lo
        # es. No ejecuta ningún carril, así que no tiene nada que cerrar. Lo
        # encontró esta misma prueba, que por eso enumera en vez de suponer.
        "validate-sirius-activation.yml": "valida la activación; no atiende ningún carril",
    }

    retirados = set(_registro().get("carriles", {}))
    for ruta in sorted(WORKFLOWS.glob("*.yml")):
        texto = ruta.read_text(encoding="utf-8")
        datos = yaml.safe_load(texto)
        # `on` lo lee PyYAML como el booleano True: es la trampa de YAML 1.1.
        disparadores = datos.get("on", datos.get(True, {})) if isinstance(datos, dict) else {}
        if not isinstance(disparadores, dict) or "issues" not in disparadores:
            continue
        for clase in sorted(retirados):
            etiqueta = CARRILES[clase]
            if etiqueta not in texto or ruta.name in exentos:
                continue
            assert "sirius_carril_retirado.py" in texto, (
                f"{ruta.name} reacciona a {etiqueta!r} (carril {clase!r}, retirado) y no "
                "consulta el registro de carriles retirados: una activación por ahí se "
                "quedaría esperando"
            )


def test_la_puerta_del_implementador_sigue_declinando_el_perfil_investigador() -> None:
    """Sin ella, una activación de investigación se implementaría como programación.

    Es la decisión que ADR-161 dejó pendiente y que ADR-163 resuelve: la puerta
    se conserva. Esta prueba impide que una limpieza futura la quite.
    """
    guion = _guion("implement-sirius-work.yml", "implement", "gate")
    assert 'if [ "$perfil" = "investigador" ]' in guion
    assert "valid=false" in guion


# --------------------------------------------------------------------------
# La puerta de investigación, EJECUTADA (ADR-167)
# --------------------------------------------------------------------------


def test_el_camino_bueno_explica_y_cierra_en_un_estado_terminal(tmp_path: Path) -> None:
    """Lo que tiene que pasar cuando todo va bien, comprobado en lo observable."""
    r = _puerta_investigacion(tmp_path, incidencia=incidencia_activa())

    assert r.codigo == 0, r.stderr
    assert r.valid == "false", "ningún paso que gaste el investigador puede correr"
    assert len(r.comentarios) == 1, r.comentarios
    assert MARCADOR in r.comentarios[0], "sin el marcador EN el cuerpo no hay deduplicación"
    assert "retirado" in r.comentarios[0]
    assert "A dónde va ahora" in r.comentarios[0]
    assert r.etiquetas == ["sirius:failed-safely"], r.etiquetas
    assert not any("gpt-researcher" in ll or "atender_orden" in ll for ll in r.llamadas_gh)


def test_si_fallan_las_etiquetas_el_paso_termina_en_rojo(tmp_path: Path) -> None:
    """Hallazgo 1: antes esto salía con 0.

    Un `::error::` seguido de `exit 0` es un job VERDE: nadie se entera, y la
    incidencia se queda en `implement-requested` esperando a un carril que ya no
    existe. La explicación sí está publicada, así que quien mire la incidencia
    ve la verdad; lo que faltaba era que el run lo dijera.
    """
    r = _puerta_investigacion(tmp_path, incidencia=incidencia_activa(), fallar="issue edit")

    assert r.codigo != 0, "una transición que no se pudo confirmar no puede salir verde"
    assert len(r.comentarios) == 1, "la explicación se publica primero, y se queda"
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"], r.etiquetas


def test_si_falla_el_comentario_no_se_toca_ninguna_etiqueta(tmp_path: Path) -> None:
    """Hallazgo 1, la otra mitad: antes era un `warning` y seguía a cerrar.

    Cerrar en `failed-safely` sin haber podido explicar por qué deja una
    incidencia terminada y muda: quien la abrió no tiene forma de saber que su
    carril está retirado ni a dónde ir. Ahora el orden lo impide -el comentario
    primero- y el fallo termina el paso en rojo.
    """
    r = _puerta_investigacion(tmp_path, incidencia=incidencia_activa(), fallar="issue comment")

    assert r.codigo != 0
    assert r.comentarios == []
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"], (
        "sin explicación publicada, la incidencia se queda donde estaba"
    )
    assert not any(ll.startswith("issue edit") for ll in r.llamadas_gh)


def test_reejecutar_tras_un_fallo_de_etiquetas_converge(tmp_path: Path) -> None:
    """La recuperación es reejecutar, y hay que demostrarlo, no suponerlo.

    ADR-167 comprobó que el reconciliador NO repara este estado: para
    `planned + implement-requested` no hace nada, y `completed + failed-safely`
    lo reporta como CONTRADICCIÓN que exige revisión humana (contrato §9.1). Así
    que la convergencia tiene que estar aquí: la segunda pasada parte del estado
    que dejó la primera, no republica -el marcador ya está- y termina la
    transición.
    """
    primera = _puerta_investigacion(
        tmp_path / "1", incidencia=incidencia_activa(), fallar="issue edit"
    )
    assert primera.codigo != 0 and len(primera.comentarios) == 1

    segunda = _puerta_investigacion(tmp_path / "2", incidencia=_incidencia_de(primera))

    assert segunda.codigo == 0, segunda.stderr
    assert len(segunda.comentarios) == 1, "el marcador tiene que evitar el duplicado"
    assert segunda.etiquetas == ["sirius:failed-safely"], segunda.etiquetas


def test_dos_activaciones_iguales_dejan_un_solo_comentario(tmp_path: Path) -> None:
    """Hallazgo 4: antes dejaban dos.

    Aquí la segunda activación se para antes, en la comprobación de estado: la
    incidencia ya está en `sirius:failed-safely`. Es el desenlace que ve quien
    la abrió -un comentario, no dos-, y por eso se comprueba así.

    El marcador, que es la otra mitad del arreglo, se prueba donde de verdad
    entra en juego: en :func:`test_reejecutar_tras_un_fallo_de_etiquetas_converge`
    y en :func:`test_una_respuesta_ambigua_no_acaba_en_comentario_duplicado`,
    donde la primera pasada dejó el comentario publicado **sin** llegar a la
    etiqueta terminal. Ahí no hay estado que frene la segunda: si el marcador no
    estuviera en el cuerpo publicado -que es el defecto de ADR-163-, se
    publicaría un duplicado.
    """
    primera = _puerta_investigacion(tmp_path / "1", incidencia=incidencia_activa())
    assert len(primera.comentarios) == 1

    segunda = _puerta_investigacion(tmp_path / "2", incidencia=_incidencia_de(primera))

    assert len(segunda.comentarios) == 1, segunda.comentarios
    assert segunda.codigo == 0


def test_una_respuesta_ambigua_no_acaba_en_comentario_duplicado(tmp_path: Path) -> None:
    """GitHub acepta el POST y la respuesta se pierde: publicado y en error.

    Ninguna API lo puede descartar. Lo que sí se puede exigir es que la segunda
    pasada no vuelva a publicar: el marcador ya está en el cuerpo del primero.
    """
    primera = _puerta_investigacion(tmp_path / "1", incidencia=incidencia_activa(), ambiguo=True)
    assert len(primera.comentarios) == 1, "el doble publica y además devuelve error"

    segunda = _puerta_investigacion(tmp_path / "2", incidencia=_incidencia_de(primera))

    assert len(segunda.comentarios) == 1, segunda.comentarios
    assert segunda.etiquetas == ["sirius:failed-safely"]


@pytest.mark.parametrize(
    ("descripcion", "incidencia"),
    [
        pytest.param(
            "ya completada",
            incidencia_activa(labels=["sirius:completed"], state="closed"),
            id="evento-atrasado-sobre-incidencia-completada",
        ),
        pytest.param(
            "cerrada",
            incidencia_activa(state="closed"),
            id="incidencia-cerrada",
        ),
        pytest.param(
            "sin la etiqueta de activación",
            incidencia_activa(labels=["sirius:planned"]),
            id="carrera-con-el-validador",
        ),
        pytest.param(
            "ya cerrada por una pasada anterior",
            incidencia_activa(labels=["sirius:failed-safely"]),
            id="evento-repetido",
        ),
    ],
)
def test_no_se_toca_una_incidencia_que_ya_no_esta_esperando(
    tmp_path: Path, descripcion: str, incidencia: dict[str, Any]
) -> None:
    """Hallazgo 2: la puerta decidía con el cuerpo del EVENTO, sin mirar el estado.

    Un evento atrasado sobre una incidencia ya completada acababa poniéndole
    `sirius:failed-safely` **encima** de `sirius:completed`: los dos a la vez,
    que es justo lo que el reconciliador reporta como CONTRADICCIÓN. Ahora la
    puerta relee estado, etiquetas y cuerpo de la API en UNA instantánea y no
    toca nada que no siga esperando.
    """
    etiquetas_antes = list(incidencia["labels"])

    r = _puerta_investigacion(tmp_path, incidencia=incidencia)

    assert r.codigo == 0, f"{descripcion}: no tocar no es fallar"
    assert r.valid == "false"
    assert r.etiquetas == etiquetas_antes, f"{descripcion}: {r.etiquetas}"
    assert r.comentarios == [], f"{descripcion}: no hay nada que explicar dos veces"
    assert not any(ll.startswith("issue edit") for ll in r.llamadas_gh)


def test_manda_el_perfil_del_cuerpo_actual_y_no_el_del_evento(tmp_path: Path) -> None:
    """Si el cuerpo cambió de perfil desde el evento, la puerta no es la suya.

    Actuar con el perfil del evento significaría cerrar como «carril retirado»
    una orden que ahora es de programación, y que el implementador sí atiende.
    """
    r = _puerta_investigacion(
        tmp_path,
        incidencia=incidencia_activa(body=cuerpo_de_orden("programador")),
        cuerpo_del_evento=cuerpo_de_orden("investigador"),
    )

    assert r.codigo == 0
    assert r.valid == "false"
    assert r.comentarios == []
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"]


@pytest.mark.parametrize(
    ("como", "kwargs"),
    [
        pytest.param("la llamada falla", {"fallar": "api"}, id="la-api-no-responde"),
        pytest.param("la respuesta no es la incidencia", {"basura": True}, id="respuesta-ilegible"),
    ],
)
def test_si_no_se_puede_leer_la_incidencia_no_se_toca(
    tmp_path: Path, como: str, kwargs: dict[str, Any]
) -> None:
    """Corolario del hallazgo 2: sin estado no hay decisión.

    Una instantánea que no se deja leer no es «la incidencia está rara»: es que
    no sabemos nada de ella. Actuar igualmente sería la misma clase de
    afirmación sin comprobar que ADR-167 corrige.
    """
    r = _puerta_investigacion(tmp_path, incidencia=incidencia_activa(), **kwargs)

    assert r.codigo != 0, como
    assert r.comentarios == []
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"]
    assert not any(ll.startswith("issue edit") for ll in r.llamadas_gh)


@pytest.mark.parametrize("codigo", [2, 3, 127])
def test_un_codigo_inesperado_del_lector_detiene_la_puerta(tmp_path: Path, codigo: int) -> None:
    """Hallazgo 3: solo el 2 se trataba como error; cualquier otro seguía en verde.

    Un 127 -`python3` no está, la ruta cambió- caía en la rama «carril activo» y
    la orden seguía hacia el investigador. El contrato ahora es explícito: 0
    retirado, 1 activo, y todo lo demás para el paso con diagnóstico.
    """
    r = _puerta_investigacion(tmp_path, incidencia=incidencia_activa(), codigo_del_lector=codigo)

    assert r.codigo != 0, "lo que no se puede afirmar no se afirma"
    assert r.valid != "true", "y desde luego no se ejecuta el carril"
    assert r.comentarios == []
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"]


def test_una_reactivacion_deja_la_puerta_abierta(tmp_path: Path) -> None:
    """Hallazgo 5, la otra mitad: reactivar tiene que SERVIR, no solo validar.

    Con un registro controlado en el que investigación ya no consta retirada, la
    misma puerta no publica explicación, no cierra nada, y deja pasar la orden a
    la validación de activación de siempre. El registro real no se toca.
    """
    r = _puerta_investigacion(
        tmp_path,
        incidencia=incidencia_activa(),
        registro=_registro_controlado(tmp_path, "auditoria"),
    )

    assert r.comentarios == [], "un carril vivo no explica que esté retirado"
    assert "sirius:failed-safely" not in r.etiquetas
    assert r.valid == "true", r.github_output + r.stderr
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"]


def test_los_pasos_que_gastan_el_investigador_dependen_de_la_puerta(tmp_path: Path) -> None:
    """`valid=false` es lo que apaga el gasto; esto comprueba que apaga TODO.

    La ejecución de arriba prueba que la puerta emite `valid=false`; esto prueba
    que ese `false` alcanza a cada paso caro. Un paso nuevo sin la condición cae
    aquí.
    """
    pasos = _pasos("investigar-orden.yml", "investigar")
    caros = [
        p
        for p in pasos
        if p.get("id") in {"atender", "abrir_pr"} or "Atender" in str(p.get("name", ""))
    ]
    assert caros, "se esperaba encontrar los pasos que ejecutan al investigador"
    for paso in caros:
        assert "valid == 'true'" in str(paso.get("if", "")), (
            f"el paso {paso.get('name')!r} correría con el carril retirado"
        )


# --------------------------------------------------------------------------
# La puerta de auditoría, EJECUTADA
# --------------------------------------------------------------------------


def test_el_auditor_no_ejecuta_el_modelo_y_publica_la_explicacion(tmp_path: Path) -> None:
    r = _puerta_auditoria(tmp_path)

    assert r.codigo == 0, r.stderr
    assert r.retirado == "true"
    informe = (tmp_path / "sirius_audit_report.md").read_text(encoding="utf-8")
    assert "retirado" in informe
    assert "No se ha ejecutado ningun modelo" in informe

    # Y el paso que gasta el modelo queda condicionado a que NO esté retirado.
    pasos = _pasos("audit-sirius-repository.yml", "auditar")
    claude = [p for p in pasos if p.get("id") == "claude"]
    assert claude, "se esperaba el paso que ejecuta Claude"
    assert "retirada.outputs.retirado != 'true'" in str(claude[0].get("if", ""))


@pytest.mark.parametrize("codigo", [2, 3, 127])
def test_un_codigo_inesperado_del_lector_detiene_al_auditor(tmp_path: Path, codigo: int) -> None:
    """Hallazgo 3 en el auditor: un 127 daba `retirado=false` y seguía al modelo."""
    r = _puerta_auditoria(tmp_path, codigo_del_lector=codigo)

    assert r.codigo != 0
    assert r.retirado != "false", r.github_output
    assert not (tmp_path / "sirius_audit_report.md").exists()


def test_con_el_carril_de_auditoria_reactivado_el_auditor_sigue_su_camino(
    tmp_path: Path,
) -> None:
    r = _puerta_auditoria(tmp_path, registro=_registro_controlado(tmp_path, "investigacion"))

    assert r.codigo == 0, r.stderr
    assert r.retirado == "false"
    assert not (tmp_path / "sirius_audit_report.md").exists(), (
        "un carril vivo no escribe un informe de carril retirado"
    )


# --------------------------------------------------------------------------
# Lo que NO se toca
# --------------------------------------------------------------------------


def test_los_revisores_el_corrector_y_quality_siguen_intactos() -> None:
    """El encargo los conserva, y ninguno menciona el registro de retirados."""
    for nombre in (
        "review-sirius-work.yml",
        "repair-sirius-work.yml",
        "quality.yml",
        "advance-sirius-after-quality.yml",
    ):
        texto = (WORKFLOWS / nombre).read_text(encoding="utf-8")
        assert "sirius_carril_retirado" not in texto, f"{nombre} no debería haberse tocado"


def test_no_se_ha_borrado_nada_de_los_carriles_retirados() -> None:
    """Desactivar es reversible; borrar no. Estas piezas se conservan enteras."""
    conservados = [
        ".github/workflows/investigar-orden.yml",
        ".github/workflows/audit-sirius-repository.yml",
        "docs/implementation/AUDITOR_AGENT_V0.md",
        "docs/implementation/work_engine/perfiles/auditor.yml",
        "scripts/investigacion/investigar_orden.py",
        "scripts/investigacion/atender_orden.py",
        "docs/investigaciones/README.md",
    ]
    faltan = [ruta for ruta in conservados if not (RAIZ / ruta).exists()]
    assert faltan == [], f"la desactivación no puede borrar: faltan {faltan}"
