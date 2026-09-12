"""Las entradas de un carril retirado quedan cerradas, y las de los vivos no (ADR-163).

Lo que estas pruebas existen para impedir es el defecto que el inventario de
ADR-163 encontró: **una entrada retirada que se queda esperando, o que acaba en
programación por otra ruta**. Investigación comparte la etiqueta de activación
con programación y se reparte por el campo ``Perfil:``.

CÓMO PRUEBAN, tras ADR-167: las puertas se **ejecutan**. El arnés
(``tests/automation/fixtures/carriles_retirados/``) extrae el guion real del
paso, lo corre con ``bash`` contra un ``gh`` doble —sin red ni credenciales— y
devuelve lo observable: **código de salida, comentarios publicados, etiquetas
finales y la lista de llamadas**. Una puerta que dijera «hecho» sin haberlo
hecho cae aquí.

DOS COSAS QUE LA SEGUNDA RONDA DE ADR-167 CAMBIÓ, y conviene leer antes de
tocar nada:

1. **Ninguna prueba de comportamiento lee el registro real.** Todas reciben un
   registro controlado. Antes no era así, y por eso reactivar un carril —que el
   contrato promete que es quitar una entrada y fusionar— dejaba seis pruebas en
   rojo. El registro real solo se usa para comprobar que es válido.
2. **Las dos puertas se prueban juntas y encadenadas**, sobre la misma
   incidencia. Dos ejecuciones aisladas no pueden mostrar ni que una activación
   se quede sin dueña ni que la atiendan las dos, que son exactamente los dos
   desenlaces que el reparto tuvo que arreglar.

Deterministas: leen ficheros y ejecutan guiones de shell contra dobles
explícitos. No lanzan ningún agente, no tocan el registro real y no gastan
ninguna API.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml
from carriles_retirados.arnes import (
    Resultado,
    cuerpo_de_orden,
    ejecutar_paso,
    estado_tras,
    incidencia_activa,
)

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = RAIZ / "docs" / "implementation" / "work_engine" / "carriles_retirados.json"
LECTOR = RAIZ / "scripts" / "automation" / "sirius_carril_retirado.py"
REPARTO = RAIZ / "scripts" / "automation" / "sirius_reparto_activacion.sh"
VALIDADOR = RAIZ / "scripts" / "automation" / "sirius_validate_activation.sh"
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
#: buscándolo en los comentarios ya existentes.
MARCADOR = "<!-- sirius-carril-retirado:investigacion -->"


#: Los estados incompatibles con una activación nueva, **leídos de su dueño** y
#: no copiados aquí. Copiar esta lista fue el hallazgo 2 de la segunda ronda: la
#: puerta se escribió una versión de cuatro y dejó fuera `implementing`,
#: `reviewing`, `repairing`, `ci-pending` y los dos `*-requested`.
def _estados_incompatibles() -> tuple[str, ...]:
    texto = VALIDADOR.read_text(encoding="utf-8")
    match = re.search(r'INCOMPATIBLE_STATES="([^"]+)"', texto)
    assert match, f"no se encontró INCOMPATIBLE_STATES en {VALIDADOR.name}"
    return tuple(match.group(1).split())


INCOMPATIBLES = _estados_incompatibles()


def _registro() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(REGISTRO.read_text(encoding="utf-8"))
    return datos


def _workflow(nombre: str) -> dict[str, Any]:
    datos: dict[str, Any] = yaml.safe_load((WORKFLOWS / nombre).read_text(encoding="utf-8"))
    return datos


def _pasos(nombre: str, job: str) -> list[dict[str, Any]]:
    pasos: list[dict[str, Any]] = _workflow(nombre)["jobs"][job]["steps"]
    return pasos


def _entrada(clase: str) -> dict[str, str]:
    return {
        "retirado_por": "ADR-161",
        "ejecutado_por": "ADR-163",
        "fecha": "2026-09-07",
        "motivo": f"prueba del carril {clase}",
        "a_donde_va": "a la memoria común",
    }


def _registro_controlado(tmp_path: Path, *clases: str) -> Path:
    """Un registro de prueba con exactamente las clases pedidas. Nunca el real."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    ruta = tmp_path / "registro_de_prueba.json"
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


# --------------------------------------------------------------------------
# Ejecutar las puertas. SIEMPRE con registro controlado.
# --------------------------------------------------------------------------

PUERTAS = {
    "investigacion": ("investigar-orden.yml", "investigar"),
    "implementacion": ("implement-sirius-work.yml", "implement"),
    "auditoria": ("audit-sirius-repository.yml", "auditar"),
}


def _puerta(cual: str, tmp_path: Path, *, registro: Path | None = None, **kwargs: Any) -> Resultado:
    workflow, job = PUERTAS[cual]
    paso = "retirada" if cual == "auditoria" else "gate"
    if registro is None:
        # Por defecto, los DOS retirados: es la configuración que la mayoría de
        # estas pruebas describe. Pero sale de un fichero controlado, no del
        # registro real, así que reactivar en el registro real no las mueve.
        registro = _registro_controlado(tmp_path / "reg", "investigacion", "auditoria")
    if cual == "auditoria":
        kwargs.setdefault("incidencia", {"labels": ["auditoria:solicitada"], "comments": []})
    return ejecutar_paso(workflow, job, paso, tmp_path=tmp_path, registro=registro, **kwargs)


@dataclass(frozen=True, slots=True)
class Paso:
    """Una puerta de la cadena: qué encontró y qué dejó."""

    cual: str
    antes: list[str]
    resultado: Resultado


def _encadenar(
    tmp_path: Path,
    orden: tuple[str, ...],
    *,
    perfil_evento: str,
    perfil_actual: str,
    labels: list[str] | None = None,
    registro: Path | None = None,
) -> tuple[list[Paso], dict[str, Any]]:
    """Las puertas de `orden`, una tras otra, sobre la MISMA incidencia."""
    cuerpo = cuerpo_de_orden(perfil_actual)
    incidencia = incidencia_activa(body=cuerpo)
    if labels is not None:
        incidencia["labels"] = list(labels)
    if registro is None:
        registro = _registro_controlado(tmp_path / "reg", "investigacion", "auditoria")
    resultados: list[Paso] = []
    for i, cual in enumerate(orden):
        # El estado de ENTRADA se conserva: sin él no se puede distinguir «la
        # atendió» de «se la encontró atendida».
        antes = list(incidencia["labels"])
        r = _puerta(
            cual,
            tmp_path / f"{i}",
            registro=registro,
            incidencia=incidencia,
            cuerpo_del_evento=cuerpo_de_orden(perfil_evento),
        )
        resultados.append(Paso(cual=cual, antes=antes, resultado=r))
        incidencia = estado_tras(r, cuerpo)
    return resultados, incidencia


def _atendio(paso: Paso) -> bool:
    """¿Esta puerta se hizo cargo del encargo?

    Dos formas de hacerse cargo, y contar solo una fue un error de esta misma
    prueba: **ejecutar** (`valid=true`, el modelo va a correr) y **retirar**
    (dejar la incidencia en `sirius:failed-safely`). Contando solo la primera, el
    caso en que una puerta retiraba y la otra ejecutaba la MISMA orden salía como
    «una sola dueña», que es justo el defecto.
    """
    if paso.resultado.valid == "true":
        return True
    return (
        "sirius:failed-safely" in paso.resultado.etiquetas
        and "sirius:failed-safely" not in paso.antes
    )


# --------------------------------------------------------------------------
# El registro: formato y seguridad, sin congelar el estado de hoy
# --------------------------------------------------------------------------


def test_el_registro_real_es_valido() -> None:
    """Lo que haya declarado tiene que estar bien declarado.

    Esta prueba NO exige que los dos carriles consten retirados, y es la ÚNICA
    que mira el registro real. Exigirlo convertía la reactivación documentada
    —quitar una entrada y fusionar— en una prueba roja.
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
    """Retirar no es borrar: la fila se conserva, y por eso reactivar es una línea."""
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
def test_las_clases_vivas_no_constan_retiradas(tmp_path: Path, clase: str) -> None:
    """Ni siquiera en un registro con los dos carriles retirados."""
    from sirius_engine.carriles_retirados import carril_retirado

    registro = _registro_controlado(tmp_path, *CARRILES)
    assert carril_retirado(clase, registro=registro) is None


def test_el_rechazo_del_despachador_es_un_error_propio_y_no_el_generico() -> None:
    """`nunca tuvo despachador` y `lo tuvo y se retiró` no son lo mismo."""
    from sirius_engine.domain.errors import CarrilRetiradoError, ClaseNoDespachableError

    assert issubclass(CarrilRetiradoError, Exception)
    assert CarrilRetiradoError.__name__ != ClaseNoDespachableError.__name__
    assert not issubclass(CarrilRetiradoError, ClaseNoDespachableError)


# --------------------------------------------------------------------------
# El lector que usan los workflows: contrato de códigos
# --------------------------------------------------------------------------


def _leer(clase: str, *, registro: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LECTOR), clase, "--registro", str(registro)],
        capture_output=True,
        text=True,
        cwd=RAIZ,
    )


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
    """Fail-closed en la afirmación: no poder leer no es «está activo»."""
    roto = tmp_path / "roto.json"
    roto.write_text("{esto no es json", encoding="utf-8")
    assert _leer("auditoria", registro=roto).returncode == 2


# --------------------------------------------------------------------------
# Las entradas reales, enumeradas desde el árbol
# --------------------------------------------------------------------------


def test_toda_entrada_de_un_carril_retirado_esta_cubierta() -> None:
    """La guarda que no envejece: enumera los disparadores, no los da por sabidos.

    Se recorre el REGISTRO real, no la lista de clases autorizadas: si un carril
    se reactiva, su entrada vuelve a ser una entrada normal y no hay nada que
    cerrar. Con el registro vacío esta prueba no comprueba nada, y es correcto.
    """
    exentos = {
        # No atiende el carril: el reparto le dice que la orden no es suya y la
        # aparta para que la atienda quien sabe cerrarla.
        "implement-sirius-work.yml": "el reparto la declina; no atiende el carril",
        # Solo valida que la activación sea legítima. No ejecuta ningún carril.
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


# --------------------------------------------------------------------------
# La puerta de investigación: el camino bueno y los fallos de la primera ronda
# --------------------------------------------------------------------------


def test_el_camino_bueno_explica_y_cierra_en_un_estado_terminal(tmp_path: Path) -> None:
    """Lo que tiene que pasar cuando todo va bien, comprobado en lo observable."""
    r = _puerta("investigacion", tmp_path, incidencia=incidencia_activa())

    assert r.codigo == 0, r.stderr
    assert r.valid == "false", "ningún paso que gaste el investigador puede correr"
    assert len(r.comentarios) == 1, r.comentarios
    assert MARCADOR in r.comentarios[0], "sin el marcador EN el cuerpo no hay deduplicación"
    assert "retirado" in r.comentarios[0]
    assert "A dónde va ahora" in r.comentarios[0]
    assert r.etiquetas == ["sirius:failed-safely"], r.etiquetas


def test_si_fallan_las_etiquetas_el_paso_termina_en_rojo(tmp_path: Path) -> None:
    """Primera ronda, hallazgo 1: antes esto salía con 0 y el job iba verde."""
    r = _puerta("investigacion", tmp_path, incidencia=incidencia_activa(), fallar="issue edit")

    assert r.codigo != 0, "una transición que no se pudo confirmar no puede salir verde"
    assert len(r.comentarios) == 1, "la explicación se publica primero, y se queda"
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"], r.etiquetas


def test_si_falla_el_comentario_no_se_toca_ninguna_etiqueta(tmp_path: Path) -> None:
    """Primera ronda, hallazgo 1, la otra mitad: antes era un `warning` y seguía."""
    r = _puerta("investigacion", tmp_path, incidencia=incidencia_activa(), fallar="issue comment")

    assert r.codigo != 0
    assert r.comentarios == []
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"], (
        "sin explicación publicada, la incidencia se queda donde estaba"
    )
    assert not any(ll.startswith("issue edit") for ll in r.llamadas_gh)


def test_dos_activaciones_iguales_dejan_un_solo_comentario(tmp_path: Path) -> None:
    """Primera ronda, hallazgo 4: antes dejaban dos.

    Aquí la segunda activación se para antes, porque la incidencia ya está en
    `sirius:failed-safely`. El marcador —la otra mitad del arreglo— se prueba
    donde de verdad entra en juego: en las dos pruebas de convergencia de abajo,
    donde la primera pasada dejó el comentario publicado SIN llegar a la etiqueta
    terminal.
    """
    primera = _puerta("investigacion", tmp_path / "1", incidencia=incidencia_activa())
    assert len(primera.comentarios) == 1

    segunda = _puerta(
        "investigacion", tmp_path / "2", incidencia=estado_tras(primera, cuerpo_de_orden())
    )

    assert len(segunda.comentarios) == 1, segunda.comentarios
    assert segunda.codigo == 0


def test_una_respuesta_ambigua_no_acaba_en_comentario_duplicado(tmp_path: Path) -> None:
    """GitHub acepta el POST y la respuesta se pierde: publicado y en error."""
    primera = _puerta("investigacion", tmp_path / "1", incidencia=incidencia_activa(), ambiguo=True)
    assert len(primera.comentarios) == 1, "el doble publica y además devuelve error"

    segunda = _puerta(
        "investigacion", tmp_path / "2", incidencia=estado_tras(primera, cuerpo_de_orden())
    )

    assert len(segunda.comentarios) == 1, segunda.comentarios
    assert segunda.etiquetas == ["sirius:failed-safely"]


def test_si_no_se_puede_leer_la_incidencia_no_se_toca(tmp_path: Path) -> None:
    """Sin estado no hay decisión: se termina en rojo sin tocar nada."""
    r = _puerta("investigacion", tmp_path, incidencia=incidencia_activa(), fallar="api")

    assert r.codigo != 0
    assert r.comentarios == []
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"]
    assert not any(ll.startswith("issue edit") for ll in r.llamadas_gh)


@pytest.mark.parametrize("codigo", [2, 3, 127])
def test_un_codigo_inesperado_del_lector_detiene_la_puerta(tmp_path: Path, codigo: int) -> None:
    """Primera ronda, hallazgo 3: solo el 2 se trataba como error."""
    r = _puerta("investigacion", tmp_path, incidencia=incidencia_activa(), codigo_del_lector=codigo)

    assert r.codigo != 0, "lo que no se puede afirmar no se afirma"
    assert r.valid != "true", "y desde luego no se ejecuta el carril"
    assert r.comentarios == []
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"]


# --------------------------------------------------------------------------
# Segunda ronda, hallazgo 1: la transición se aplica en VARIAS escrituras
# --------------------------------------------------------------------------


#: Las tres escrituras independientes de la transición de retirada, en el orden
#: en que `sirius_set_issue_labels` las hace.
ESCRITURAS = (
    "--add-label sirius:failed-safely",
    "--remove-label sirius:implement-requested",
    "--remove-label sirius:planned",
)
_CORTO = {ESCRITURAS[0]: "+FS", ESCRITURAS[1]: "-IR", ESCRITURAS[2]: "-PL"}


def _las_ocho_combinaciones() -> list[Any]:
    casos: list[Any] = []
    for n in range(8):
        fallan = tuple(e for i, e in enumerate(ESCRITURAS) if n >> i & 1)
        casos.append(
            pytest.param(fallan, id="+".join(_CORTO[e] for e in fallan) or "ninguna-falla")
        )
    return casos


@pytest.mark.parametrize("fallan", _las_ocho_combinaciones())
def test_las_ocho_combinaciones_de_escritura_convergen(
    tmp_path: Path, fallan: tuple[str, ...]
) -> None:
    """La reejecución converge al estado final, venga de donde venga.

    La segunda ronda intentó **reconocer** una «retirada a medias» por su firma
    —`failed-safely` junto a otra etiqueta, o ninguna etiqueta— y se le
    escaparon dos de las ocho combinaciones: con solo `planned` la reejecución
    salía en verde sin completar, y con solo `implement-requested` terminaba sin
    etiquetas **y con un segundo comentario**.

    La regla correcta ya estaba en el repositorio, en `sirius_transition`
    (incidencia #50): el marcador no basta; se verifica el **estado final** y se
    completa sin duplicar el comentario. Por eso esta prueba no tiene casos
    especiales: las ocho terminan igual.
    """
    primera = _puerta(
        "investigacion", tmp_path / "1", incidencia=incidencia_activa(), fallar=",".join(fallan)
    )
    assert (primera.codigo == 0) is (not fallan), "solo el caso sin fallos sale verde"
    assert len(primera.comentarios) == 1, "la explicación se publica antes de escribir"

    segunda = _puerta(
        "investigacion", tmp_path / "2", incidencia=estado_tras(primera, cuerpo_de_orden())
    )

    assert segunda.codigo == 0, segunda.stderr
    assert segunda.etiquetas == ["sirius:failed-safely"], segunda.etiquetas
    assert len(segunda.comentarios) == 1, "y sin republicar la explicación"


@pytest.mark.parametrize(
    ("descripcion", "cambio"),
    [
        pytest.param("el propietario la cierra", {"state": "closed"}, id="cerrada-despues"),
        pytest.param(
            "el ciclo avanza el trabajo",
            {"labels": ["sirius:planned", "sirius:implementing"]},
            id="trabajo-avanzado-despues",
        ),
    ],
)
def test_una_intervencion_posterior_detiene_la_recuperacion(
    tmp_path: Path, descripcion: str, cambio: dict[str, Any]
) -> None:
    """Un comentario antiguo y unas etiquetas no prueban que siga pendiente lo mismo.

    Entre la pasada que falló y el reintento puede haber pasado cualquier cosa.
    Reproducido: la retirada publica su comentario, falla al añadir
    `failed-safely`, el propietario **cierra** la incidencia, se reejecuta el
    job — y la recuperación le ponía `failed-safely` a una incidencia cerrada.

    Ahora, ante cualquier señal de intervención posterior, se para en **rojo sin
    escribir**. Es lo contrario de adivinar.
    """
    primera = _puerta(
        "investigacion",
        tmp_path / "1",
        incidencia=incidencia_activa(),
        fallar="--add-label sirius:failed-safely",
    )
    despues = estado_tras(primera, cuerpo_de_orden())
    despues.update(cambio)

    segunda = _puerta("investigacion", tmp_path / "2", incidencia=despues)

    assert segunda.codigo != 0, f"{descripcion}: no se puede resolver solo"
    assert segunda.etiquetas == despues["labels"], f"{descripcion}: no se toca nada"
    assert segunda.estado_incidencia == despues["state"]
    assert len(segunda.comentarios) == 1, "y no se publica un segundo diagnóstico"


def test_si_el_perfil_cambia_entre_la_pasada_y_el_reintento_no_se_recupera(
    tmp_path: Path,
) -> None:
    """La orden ya no es de este carril: la recuperación no es suya."""
    primera = _puerta(
        "investigacion",
        tmp_path / "1",
        incidencia=incidencia_activa(),
        fallar="--add-label sirius:failed-safely",
    )
    despues = estado_tras(primera, cuerpo_de_orden("programador"))

    segunda = _puerta(
        "investigacion",
        tmp_path / "2",
        incidencia=despues,
        cuerpo_del_evento=cuerpo_de_orden("programador"),
    )

    assert segunda.codigo == 0
    assert segunda.valid != "true"
    assert segunda.etiquetas == despues["labels"], "no se toca nada"
    assert len(segunda.comentarios) == 1


def test_una_retirada_a_medias_no_se_completa_encima_de_trabajo_posterior(
    tmp_path: Path,
) -> None:
    """Completar no puede convertirse en pisar.

    Si además del estado a medias hay CUALQUIER otra etiqueta `sirius:`, el ciclo
    movió la incidencia después: la puerta no impone ningún desenlace, termina en
    rojo y pide que lo mire una persona. La comprobación no copia ninguna lista;
    es «todo `sirius:` que no sean las tres de esta transición», así que un
    estado que se invente mañana también la dispara.
    """
    primera = _puerta(
        "investigacion",
        tmp_path / "1",
        incidencia=incidencia_activa(),
        fallar="--remove-label sirius:implement-requested",
    )
    a_medias = estado_tras(primera, cuerpo_de_orden())
    a_medias["labels"] = [*a_medias["labels"], "sirius:implementing"]

    segunda = _puerta("investigacion", tmp_path / "2", incidencia=a_medias)

    assert segunda.codigo != 0, "una contradicción no se resuelve sola"
    assert sorted(segunda.etiquetas) == sorted(a_medias["labels"]), "no se toca nada"
    assert len(segunda.comentarios) == 1, "y no se publica un segundo diagnóstico"


# --------------------------------------------------------------------------
# Segunda ronda, hallazgo 2: no imponer un desenlace al trabajo en curso
# --------------------------------------------------------------------------


@pytest.mark.parametrize("estado", INCOMPATIBLES)
def test_una_activacion_improcedente_no_impone_failed_safely(tmp_path: Path, estado: str) -> None:
    """La puerta se había escrito su propia lista de estados terminales, de cuatro.

    Con `implementing`, `reviewing`, `repairing`, `ci-pending` o cualquiera de
    los `*-requested`, una activación nueva acababa poniendo `failed-safely`
    ENCIMA del trabajo en curso. Ahora quien decide si la activación es legítima
    es su dueño —`sirius_validate_activation.sh`, que tiene los diez estados—, y
    su política es explicar y retirar el evento **sin** imponer un desenlace.

    Los estados se leen del propio validador: si mañana añade uno, esta prueba lo
    cubre sola.
    """
    r = _puerta(
        "investigacion",
        tmp_path,
        incidencia=incidencia_activa(
            labels=["sirius:planned", "sirius:implement-requested", estado]
        ),
    )

    assert r.codigo == 0, r.stderr
    assert r.valid != "true"
    assert estado in r.etiquetas, f"{estado} es trabajo de otro: no se toca"
    assert "sirius:implement-requested" not in r.etiquetas, "el evento improcedente se retira"
    assert len(r.comentarios) == 1, "y se explica por qué"
    if estado != "sirius:failed-safely":
        assert "sirius:failed-safely" not in r.etiquetas, (
            "la retirada no puede imponer su desenlace a un trabajo en curso"
        )


def test_si_el_validador_ya_retiro_el_evento_la_puerta_no_toca_nada(tmp_path: Path) -> None:
    """El validador corre en su propio workflow y puede llegar primero.

    Cuando llega, deja la incidencia sin `sirius:implement-requested`. La puerta
    no puede suponer que ella va primero ni volver a actuar sobre una activación
    que ya no está viva.
    """
    r = _puerta(
        "investigacion",
        tmp_path,
        incidencia=incidencia_activa(labels=["sirius:planned"]),
    )

    assert r.codigo == 0
    assert r.valid != "true"
    assert r.etiquetas == ["sirius:planned"], r.etiquetas
    assert r.comentarios == []
    assert not any(ll.startswith("issue edit") for ll in r.llamadas_gh)


# --------------------------------------------------------------------------
# Segunda ronda, hallazgo 3: el reparto entre las dos puertas
# --------------------------------------------------------------------------

ORDENES = [
    pytest.param(("investigacion", "implementacion"), id="investigacion-primero"),
    pytest.param(("implementacion", "investigacion"), id="implementacion-primero"),
]


@pytest.mark.parametrize("orden", ORDENES)
@pytest.mark.parametrize(
    ("perfil", "duena"),
    [
        pytest.param("investigador", "investigacion", id="investigador"),
        pytest.param("programador", "implementacion", id="programador"),
    ],
)
def test_sin_cambio_de_perfil_hay_exactamente_una_duena(
    tmp_path: Path, orden: tuple[str, ...], perfil: str, duena: str
) -> None:
    """Ni ninguna ni las dos: una."""
    pasos, _ = _encadenar(tmp_path, orden, perfil_evento=perfil, perfil_actual=perfil)
    por_puerta = {p.cual: p.resultado for p in pasos}
    assert [p.cual for p in pasos if _atendio(p)] == [duena], (
        "exactamente una puerta se hace cargo del encargo"
    )

    if duena == "implementacion":
        assert por_puerta["implementacion"].valid == "true", "la atiende el implementador"
        assert por_puerta["investigacion"].valid == "false"
    else:
        # El carril de investigación está retirado en el registro controlado, así
        # que «atenderla» es retirarla: explicar y cerrar. Lo que importa es que
        # el implementador NO la toca.
        assert por_puerta["implementacion"].valid == "false"
        assert "sirius:failed-safely" in por_puerta["investigacion"].etiquetas


@pytest.mark.parametrize("orden", ORDENES)
@pytest.mark.parametrize(
    ("evento", "actual"),
    [
        pytest.param("investigador", "programador", id="de-investigador-a-programador"),
        pytest.param("programador", "investigador", id="de-programador-a-investigador"),
    ],
)
def test_un_perfil_cambiado_no_lo_ejecuta_nadie_y_no_retira_nada(
    tmp_path: Path, orden: tuple[str, ...], evento: str, actual: str
) -> None:
    """Los dos desenlaces peores, reproducidos sobre `398017a`:

    - evento `investigador` y cuerpo `programador`: las dos puertas declinaban y
      la incidencia se quedaba **sin que nadie la atendiera**;
    - evento `programador` y cuerpo `investigador`: **las dos** la atendían.

    Ninguna ejecuta ya. Y desde la cuarta ronda **tampoco se retira la etiqueta**:
    esa escritura solo sería legítima si la etiqueta fuese la que trajo este
    evento, y eso no se puede probar. Se explica y se para en rojo, conservando
    la activación para que la atienda el evento que sí le corresponde.
    """
    pasos, final = _encadenar(tmp_path, orden, perfil_evento=evento, perfil_actual=actual)

    for paso in pasos:
        assert not _atendio(paso), f"{paso.cual} no puede hacerse cargo de un evento rancio"
    assert [p.cual for p in pasos if p.resultado.codigo != 0], (
        "la puerta que sería la dueña según el cuerpo actual tiene que parar en rojo"
    )
    assert final["labels"] == ["sirius:planned", "sirius:implement-requested"], final["labels"]
    assert len(final["comments"]) == 1, "una sola explicación, corra quien corra primero"
    comentario = final["comments"][0]
    assert "perfil-cambiado" in comentario
    assert "No se ha ejecutado nada" in comentario
    assert "Tampoco se ha tocado ninguna etiqueta" in comentario, (
        "el diagnóstico no puede decir que retiró una etiqueta cuando la conservó"
    )
    # El aviso tiene que servir para los DOS casos, porque la etiqueta no los
    # distingue: puede haber una activación nueva ya en marcha, o puede que solo
    # se editara el perfil y esa etiqueta sea la de este mismo evento.
    assert "NO permite distinguir" in comentario, (
        "el aviso tiene que decir que la etiqueta, por sí sola, no distingue los dos casos"
    )
    assert "Si ya volviste a activar" in comentario and "dejala correr" in comentario, (
        "falta el caso en que ya existe una activación nueva: hay que dejarla continuar"
    )
    assert "Si solo editaste el perfil" in comentario, (
        "falta el caso en que solo se editó el perfil y nadie va a atender la etiqueta"
    )
    assert "no haya una ejecucion en curso" in comentario, (
        "antes de retirar la etiqueta hay que comprobar que no hay trabajo corriendo"
    )
    assert "retira la etiqueta y vuelve a aplicarla" in comentario, (
        "y decir cómo generar una activación nueva"
    )
    assert "la atendera el evento de esa activacion y aqui no hay nada mas" not in comentario, (
        "no puede afirmar que otro evento la atenderá: la etiqueta no lo demuestra"
    )


@pytest.mark.parametrize(
    ("perfil_a", "perfil_b"),
    [
        pytest.param("investigador", "programador", id="A-investigador-B-programador"),
        pytest.param("programador", "investigador", id="A-programador-B-investigador"),
    ],
)
@pytest.mark.parametrize(
    "rechazo_previo",
    [pytest.param(False, id="A-nunca-procesado"), pytest.param(True, id="A-ya-rechazado")],
)
def test_un_evento_viejo_no_borra_la_activacion_de_uno_nuevo(
    tmp_path: Path, perfil_a: str, perfil_b: str, rechazo_previo: bool
) -> None:
    """La secuencia entera, que es donde estaba el fallo.

    1. Se activa una orden con `Perfil: A`; su evento **A** queda en cola.
    2. El propietario cambia el perfil a **B**, retira la etiqueta y la vuelve a
       aplicar: nace el evento **B**.
    3. Arranca **A**. La etiqueta que ve es la de B.
    4. Arranca **B**.

    Sobre `08f45a5`, en el paso 3 el reparto retiraba la etiqueta —no había
    ningún marcador que lo frenara, porque A no se había procesado nunca— y en
    el paso 4 B encontraba solo `sirius:planned` y declinaba: **el encargo se
    perdía**. La protección de la tercera ronda solo cubría el caso con rechazo
    previo, y la AUSENCIA del marcador no demuestra que la etiqueta sea de este
    evento. Se prueban los dos, con marcador y sin él.
    """
    registro = _registro_controlado(tmp_path / "reg", "investigacion", "auditoria")
    cuerpo_b = cuerpo_de_orden(perfil_b)
    orden = ("investigacion", "implementacion")
    incidencia = incidencia_activa(body=cuerpo_b)

    if rechazo_previo:
        # A ya se procesó una vez: su diagnóstico está publicado.
        for i, cual in enumerate(orden):
            r = _puerta(
                cual,
                tmp_path / f"0-{i}",
                registro=registro,
                incidencia=incidencia,
                cuerpo_del_evento=cuerpo_de_orden(perfil_a),
            )
            incidencia = estado_tras(r, cuerpo_b)
        assert len(incidencia["comments"]) == 1

    # 3) Arranca A -sobre la etiqueta que aplicó B-.
    for i, cual in enumerate(orden):
        r = _puerta(
            cual,
            tmp_path / f"3-{i}",
            registro=registro,
            incidencia=incidencia,
            cuerpo_del_evento=cuerpo_de_orden(perfil_a),
        )
        assert r.valid != "true", f"A no puede ejecutar en {cual}"
        assert "sirius:implement-requested" in r.etiquetas, (
            f"A ha borrado en {cual} una activación que no es de su evento"
        )
        incidencia = estado_tras(r, cuerpo_b)
    assert incidencia["labels"] == ["sirius:planned", "sirius:implement-requested"]
    assert len(incidencia["comments"]) == 1, "un solo diagnóstico, no uno por pasada"

    # 4) Arranca B: su propio evento, con el cuerpo que coincide.
    atienden = []
    for i, cual in enumerate(orden):
        r = _puerta(
            cual,
            tmp_path / f"4-{i}",
            registro=registro,
            incidencia=incidencia,
            cuerpo_del_evento=cuerpo_b,
        )
        if _atendio(Paso(cual=cual, antes=list(incidencia["labels"]), resultado=r)):
            atienden.append(cual)
        incidencia = estado_tras(r, cuerpo_b)
    esperada = "investigacion" if perfil_b == "investigador" else "implementacion"
    assert atienden == [esperada], f"a B lo atiende {atienden}, no {esperada}"


def test_el_reparto_no_deja_que_las_dos_puertas_ejecuten_el_mismo_encargo(
    tmp_path: Path,
) -> None:
    """La propiedad, dicha entera y comprobada sobre las cuatro combinaciones."""
    # LOS DOS ÓRDENES, y no es cosmético: con investigación siempre primero, el
    # caso «evento programador, cuerpo investigador» salía como una sola dueña
    # incluso en el código defectuoso, porque la retirada dejaba `failed-safely`
    # y el validador frenaba después al implementador. Encadenando al revés se ve
    # lo que de verdad pasaba: las dos se hacían cargo del mismo encargo.
    for orden in (("investigacion", "implementacion"), ("implementacion", "investigacion")):
        for evento, actual in (
            ("investigador", "investigador"),
            ("programador", "programador"),
            ("investigador", "programador"),
            ("programador", "investigador"),
        ):
            pasos, _ = _encadenar(
                tmp_path / f"{orden[0]}-{evento}-{actual}",
                orden,
                perfil_evento=evento,
                perfil_actual=actual,
            )
            atienden = [p.cual for p in pasos if _atendio(p)]
            assert len(atienden) <= 1, (
                f"{orden[0]} primero, {evento}->{actual}: "
                f"se hacen cargo del mismo encargo {atienden}"
            )


def test_la_puerta_del_implementador_declina_el_perfil_investigador(tmp_path: Path) -> None:
    """Sin esto, una activación de investigación se implementaría como programación."""
    r = _puerta(
        "implementacion",
        tmp_path,
        incidencia=incidencia_activa(body=cuerpo_de_orden("investigador")),
        cuerpo_del_evento=cuerpo_de_orden("investigador"),
    )

    assert r.codigo == 0, r.stderr
    assert r.valid == "false"
    assert r.comentarios == [], "declinar no es rechazar: no comenta ni toca etiquetas"
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"]


def test_si_el_reparto_no_se_puede_decidir_las_dos_puertas_terminan_en_rojo(
    tmp_path: Path,
) -> None:
    """El mismo contrato de códigos que el lector: lo que no se sabe, para el paso.

    Hay que romper las DOS vías de lectura. `sirius_read_issue_body` cae a
    GraphQL cuando REST falla, y esa robustez es deliberada: con solo `gh api`
    roto el reparto todavía decide bien, y esta prueba lo comprobó al escribirla
    -falló por suponer que una vía bastaba-. «No se puede decidir» es que fallen
    todas.
    """
    for cual in ("investigacion", "implementacion"):
        r = _puerta(cual, tmp_path / cual, incidencia=incidencia_activa(), fallar="api,issue view")
        assert r.codigo != 0, f"{cual} no puede seguir sin saber si la orden es suya"
        assert r.valid != "true"
        assert not any(ll.startswith("issue edit") for ll in r.llamadas_gh)


def test_con_una_sola_via_de_lectura_rota_el_reparto_sigue_decidiendo(
    tmp_path: Path,
) -> None:
    """El respaldo GraphQL no es decorativo: con REST caído el reparto decide igual."""
    r = _puerta(
        "implementacion",
        tmp_path,
        incidencia=incidencia_activa(body=cuerpo_de_orden("investigador")),
        cuerpo_del_evento=cuerpo_de_orden("investigador"),
        fallar="api",
    )

    assert r.codigo == 0, r.stderr
    assert r.valid == "false", "decidió que no era suya, con REST caído"
    assert r.comentarios == []


# --------------------------------------------------------------------------
# El carril reactivado: la puerta se abre, y sin editar ninguna prueba
# --------------------------------------------------------------------------


def test_una_reactivacion_deja_la_puerta_de_investigacion_abierta(tmp_path: Path) -> None:
    """Reactivar tiene que SERVIR, no solo validar."""
    r = _puerta(
        "investigacion",
        tmp_path,
        incidencia=incidencia_activa(),
        registro=_registro_controlado(tmp_path / "reg", "auditoria"),
    )

    assert r.comentarios == [], "un carril vivo no explica que esté retirado"
    assert "sirius:failed-safely" not in r.etiquetas
    assert r.valid == "true", r.github_output + r.stderr
    assert r.etiquetas == ["sirius:planned", "sirius:implement-requested"]


def test_los_pasos_que_gastan_el_investigador_dependen_de_la_puerta() -> None:
    """`valid=false` es lo que apaga el gasto; esto comprueba que apaga TODO."""
    caros = [
        p
        for p in _pasos("investigar-orden.yml", "investigar")
        if p.get("id") in {"atender", "abrir_pr"} or "Atender" in str(p.get("name", ""))
    ]
    assert caros, "se esperaba encontrar los pasos que ejecutan al investigador"
    for paso in caros:
        assert "valid == 'true'" in str(paso.get("if", "")), (
            f"el paso {paso.get('name')!r} correría con el carril retirado"
        )


# --------------------------------------------------------------------------
# La puerta de auditoría
# --------------------------------------------------------------------------


def test_el_auditor_no_ejecuta_el_modelo_y_publica_la_explicacion(tmp_path: Path) -> None:
    r = _puerta("auditoria", tmp_path)

    assert r.codigo == 0, r.stderr
    assert r.retirado == "true"
    informe = (tmp_path / "sirius_audit_report.md").read_text(encoding="utf-8")
    assert "retirado" in informe
    assert "No se ha ejecutado ningun modelo" in informe

    claude = [
        p for p in _pasos("audit-sirius-repository.yml", "auditar") if p.get("id") == "claude"
    ]
    assert claude, "se esperaba el paso que ejecuta Claude"
    assert "retirada.outputs.retirado != 'true'" in str(claude[0].get("if", ""))


@pytest.mark.parametrize("codigo", [2, 3, 127])
def test_un_codigo_inesperado_del_lector_detiene_al_auditor(tmp_path: Path, codigo: int) -> None:
    r = _puerta("auditoria", tmp_path, codigo_del_lector=codigo)

    assert r.codigo != 0
    assert r.retirado != "false", r.github_output
    assert not (tmp_path / "sirius_audit_report.md").exists()


def test_con_el_carril_de_auditoria_reactivado_el_auditor_sigue_su_camino(
    tmp_path: Path,
) -> None:
    r = _puerta(
        "auditoria", tmp_path, registro=_registro_controlado(tmp_path / "reg", "investigacion")
    )

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
        assert "sirius_reparto_activacion" not in texto, f"{nombre} no debería haberse tocado"


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
