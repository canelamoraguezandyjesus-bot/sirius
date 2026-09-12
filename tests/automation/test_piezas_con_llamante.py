"""La enfermedad de esta casa: una pieza correcta a la que no llama nadie.

Este repositorio lleva **ocho** casos contados, y los ocho tenían pruebas en
verde vigilando código que no se ejecutaba nunca:

| pieza | cuánto estuvo muerta |
|---|---|
| el despachador (C2) | semanas |
| H-13 | días |
| el supervisor (`supervise_runs`, C1) | desde C1 hasta D2 |
| el contador de los siete días (`sirius-racha`) | desde el 23-08 |
| `authority_reversion` (D1c) | desde que se escribió, hasta D1c |
| el reflector y las clases que no miraba (ADR-173) | desde el 28-08 |
| **`MirroredWorkItem.cerrada` (ADR-173)** | desde que se escribió, hasta ADR-173 |
| el cierre a medias de ADR-176 | desde ADR-173 hasta ADR-176 |

El séptimo es el que tumbó a esta batería y por el que está reescrita. **Esta
guarda no lo vio, y no podía verlo:** vigilaba un diccionario escrito a mano con
**cuatro nombres de módulo** —el 5,3 % de los 75 módulos públicos del motor— y
`cerrada` no es un módulo, es un campo de un dataclass. Una guarda cuya
cobertura es un dato de entrada no descubre nada: solo confirma lo que alguien
se acordó de escribir en ella.

Así que el inventario ya no se escribe: **se deriva** del árbol de
`src/sirius_engine` con `ast`. Lo escrito a mano es ahora lo que se RESTA
—`SIN_LLAMANTE_CONOCIDO`—, y restar tiene la ventaja de que se nota: una
excepción que sobra pone la batería en rojo, mientras que una entrada que falta
en una lista de inclusión no la pone en rojo nunca. Es la decisión de ADR-177.

Esta batería no comprueba que las piezas estén bien hechas —eso lo hacen sus
propias pruebas—. Comprueba que **alguien las llame**, que es la mitad que
faltaba las ocho veces.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "src" / "sirius_engine"

#: Dónde vive el código que se considera PRODUCCIÓN y se lee como Python. Las
#: pruebas quedan fuera a propósito: una pieza llamada solo por sus pruebas es
#: exactamente el caso que esta batería existe para cazar.
PRODUCCION_PY = ("src", "scripts")

#: Dónde vive el código de producción que NO es Python y hay que leer como
#: texto: los workflows que invocan los guiones de consola y el `pyproject.toml`
#: que declara los puntos de entrada. Solo vale para los MÓDULOS —ver
#: `_nombrado_en_texto`—.
PRODUCCION_TEXTO = ("scripts", ".github/workflows")
SUFIJOS_TEXTO = (".yml", ".yaml", ".sh", ".ps1")


@dataclass(frozen=True)
class Pieza:
    """Una pieza pública del motor, derivada del código y no de una lista.

    `identidad` es lo que se escribe en `SIN_LLAMANTE_CONOCIDO`, y lleva delante
    la ruta punteada del módulo dentro del paquete para que dos piezas homónimas
    de módulos distintos no se confundan
    (`campo:domain.mirror.MirroredWorkItem.cerrada`).

    `clave` es el identificador que hay que ver USADO en producción. No es
    único: 84 identificadores del motor los comparten 274 piezas, así que la
    guarda puede dar por viva una pieza muerta homónima de una viva. Es un falso
    negativo, nunca un falso positivo, y está medido y declarado en ADR-177.
    """

    tipo: str
    identidad: str
    clave: str
    ruta: str


def _ficheros_py(base: Path) -> list[Path]:
    return sorted(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)


def _campos_anotados(clase: ast.ClassDef) -> list[str]:
    """Los campos públicos declarados con anotación en el cuerpo de la clase.

    Es la forma que tiene un dataclass de declarar sus campos, y es la forma que
    tenía `cerrada`: `cerrada: bool`, sin valor por defecto y sin aparecer en
    ningún `def`.
    """
    return [
        nodo.target.id
        for nodo in clase.body
        if isinstance(nodo, ast.AnnAssign)
        and isinstance(nodo.target, ast.Name)
        and not nodo.target.id.startswith("_")
    ]


@lru_cache(maxsize=1)
def piezas_del_motor() -> tuple[Pieza, ...]:
    """El inventario, DERIVADO del árbol del motor. Nadie lo escribe a mano.

    Entran tres formas de pieza, porque la que tumbó a esta batería no era un
    módulo:

    - `modulo:<ruta.punteada>` — cada `.py` público del paquete.
    - `definicion:<ruta.punteada>.<nombre>` — clases, funciones y constantes
      públicas de nivel superior.
    - `campo:<ruta.punteada>.<Clase>.<campo>` — cada campo anotado público de
      una clase. Aquí es donde entra `MirroredWorkItem.cerrada`.

    Lo privado (`_`) queda fuera, y también los métodos, los miembros de `Enum`
    y las claves de diccionario: la cobertura que esto gana está medida en
    ADR-177, no es total, y decirlo es parte del trato.
    """
    piezas: list[Pieza] = []
    for ruta in _ficheros_py(MOTOR):
        relativa = str(ruta.relative_to(RAIZ))
        modulo = ruta.stem
        # La ruta con puntos dentro del paquete, que es lo que distingue
        # `ports.store` de `adapters.durable.store`: tres stems del motor están
        # repetidos y con el stem a secas dos piezas distintas compartirían
        # identidad, que es justo el escondite que esta batería viene a cerrar.
        punteada = ".".join(ruta.relative_to(MOTOR).with_suffix("").parts)
        if modulo != "__init__" and not modulo.startswith("_"):
            piezas.append(Pieza("modulo", f"modulo:{punteada}", modulo, relativa))
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        for nodo in arbol.body:
            if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                if nodo.name.startswith("_"):
                    continue
                identidad = f"definicion:{punteada}.{nodo.name}"
                piezas.append(Pieza("definicion", identidad, nodo.name, relativa))
                if isinstance(nodo, ast.ClassDef):
                    for campo in _campos_anotados(nodo):
                        piezas.append(
                            Pieza(
                                "campo",
                                f"campo:{punteada}.{nodo.name}.{campo}",
                                campo,
                                relativa,
                            )
                        )
            elif isinstance(nodo, ast.Assign):
                for destino in nodo.targets:
                    if isinstance(destino, ast.Name) and not destino.id.startswith("_"):
                        identidad = f"definicion:{punteada}.{destino.id}"
                        piezas.append(Pieza("definicion", identidad, destino.id, relativa))
    return tuple(piezas)


@dataclass(frozen=True)
class _UsosDeUnFichero:
    nombres: frozenset[str]
    atributos_leidos: frozenset[str]


def _usos(arbol: ast.Module) -> _UsosDeUnFichero:
    """Lo que un fichero USA, leído del AST y no del texto.

    Leerlo del AST es lo que arregla de raíz el defecto que el docstring viejo
    de `_sin_comentarios` describía: un guardián que se conforma con que algo
    esté NOMBRADO no comprueba que esté LLAMADO. Un nombre que solo aparece en
    un comentario o en un docstring **no existe en el AST**, así que aquí no
    cuenta sin tener que recortar el texto a mano. Y distingue
    `annotate_observations` de `annotate_observations_with_verdicts`, que una
    búsqueda por subcadena confunde.

    Los atributos se recogen aparte y **solo en contexto de lectura**, porque el
    caso `cerrada` vive justo en esa distinción: `mirror_projection.py:926`
    ESCRIBE el campo (`cerrada=...`, un `keyword` del constructor) y eso no lo
    mantiene vivo. Lo que faltaba era quien lo LEYERA.
    """
    nombres: set[str] = set()
    atributos: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Load):
            nombres.add(nodo.id)
        elif isinstance(nodo, ast.Attribute):
            nombres.add(nodo.attr)
            if isinstance(nodo.ctx, ast.Load):
                atributos.add(nodo.attr)
        elif isinstance(nodo, ast.alias):
            nombres.update(nodo.name.split("."))
            if nodo.asname:
                nombres.add(nodo.asname)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.update(nodo.module.split("."))
    return _UsosDeUnFichero(frozenset(nombres), frozenset(atributos))


@lru_cache(maxsize=1)
def _usos_de_produccion() -> dict[str, _UsosDeUnFichero]:
    indice: dict[str, _UsosDeUnFichero] = {}
    for carpeta in PRODUCCION_PY:
        base = RAIZ / carpeta
        if not base.is_dir():
            continue
        for ruta in _ficheros_py(base):
            indice[str(ruta.relative_to(RAIZ))] = _usos(ast.parse(ruta.read_text(encoding="utf-8")))
    return indice


@lru_cache(maxsize=1)
def _textos_de_produccion() -> dict[str, str]:
    """Workflows, guiones de shell y `pyproject.toml`, sin sus comentarios."""
    textos: dict[str, str] = {}
    rutas: list[Path] = [RAIZ / "pyproject.toml"]
    for carpeta in PRODUCCION_TEXTO:
        base = RAIZ / carpeta
        if base.is_dir():
            rutas.extend(p for p in base.rglob("*") if p.suffix in SUFIJOS_TEXTO)
    for ruta in rutas:
        if not ruta.is_file():
            continue
        crudo = ruta.read_text(encoding="utf-8", errors="ignore")
        sin_comentarios = "\n".join(linea.split("#", 1)[0] for linea in crudo.splitlines())
        textos[str(ruta.relative_to(RAIZ))] = sin_comentarios
    return textos


def _nombrado_en_texto(pieza: Pieza) -> list[str]:
    """Ficheros no-Python de producción que nombran la pieza.

    **Solo vale para los módulos**, y a propósito. Un módulo puede tener su
    único llamante en un workflow o en un punto de entrada del `pyproject.toml`
    —`sirius-racha` es ese caso—, y ahí no hay AST que leer. Pero una búsqueda
    por texto sobre un campo llamado `estado` o `motivo` acierta en cualquier
    workflow por casualidad: aplicarla a definiciones y campos habría dado por
    vivas 9 piezas que están muertas, medido en ADR-177.
    """
    if pieza.tipo != "modulo":
        return []
    return sorted(
        fichero for fichero, texto in _textos_de_produccion().items() if pieza.clave in texto
    )


def llamantes(pieza: Pieza) -> list[str]:
    """Ficheros de PRODUCCIÓN cuyo CÓDIGO usa esta pieza.

    Para un módulo, el llamante tiene que estar en otro fichero: un módulo no se
    importa a sí mismo. Para una definición o un campo, vale su propio módulo,
    porque la pieza puede estar cableada ahí dentro y llegar viva a producción
    por el módulo que la contiene —lo que se persigue es la pieza a la que no
    llama NADIE, que es lo que decía la evidencia de ADR-173:
    `grep -rln "\\.cerrada\\b" src/ scripts/` sin coincidencias—.

    Su propia sentencia `def N`, `class N` o `N = ...` no cuenta como uso, y no
    hay que descontarla: `_usos` recoge `ast.Name` en contexto `Load` y los
    nombres de `FunctionDef`/`ClassDef` no son nodos `Name`.
    """
    encontrados: list[str] = []
    for fichero, usos in _usos_de_produccion().items():
        if pieza.tipo == "modulo" and Path(fichero).stem == pieza.clave:
            continue
        disponibles = usos.atributos_leidos if pieza.tipo == "campo" else usos.nombres
        if pieza.clave in disponibles:
            encontrados.append(fichero)
    return sorted(encontrados) + _nombrado_en_texto(pieza)


#: Pieza -> por qué no tiene llamante, en una frase que se lee en el fallo. Sin
#: el motivo, un rojo aquí parece burocracia y se silencia.
#:
#: **Esto es lo que se RESTA del inventario derivado, no lo que se suma.** Las 45
#: entradas son la deuda que la derivación destapó el 12-09-2026, el día que se
#: escribió esta guarda: la lista a mano vieja vigilaba 4 piezas y ninguna de
#: ellas estaba muerta, así que en tres meses no encontró nada. Cablear o retirar
#: cada una de estas 45 es trabajo de otras incidencias —queda fuera del alcance
#: de WI-20260912-154847—, y por eso entran aquí en vez de ponerse el rojo hoy.
#:
#: Tres cierres impiden que esta lista se convierta en el escondite que era la
#: otra: una entrada que ya no corresponde a ninguna pieza pone la batería en
#: rojo; una entrada cuya pieza YA tiene llamante también, para que se borre en
#: cuanto sobra; y una razón vacía, también. Lo que ningún mecanismo puede
#: impedir es que alguien escriba una razón falsa: eso lo sostiene la revisión.
SIN_LLAMANTE_CONOCIDO: dict[str, str] = {
    # --- Dobles de sustitución que viven en `src/` a propósito -------------
    # Estos tres no son la enfermedad: son adaptadores de sustitución puestos en
    # el paquete para que varias baterías los compartan, y que sus únicos
    # llamantes sean las pruebas es su diseño, no su muerte.
    "modulo:adapters.cli_notification": (
        "es el adaptador de notificación por consola, un doble que vive en `src/` "
        "para que lo compartan las baterías; su llamante son las pruebas a propósito"
    ),
    "definicion:adapters.cli_notification.NotificadorCLI": (
        "es la clase de ese mismo doble de notificación, compartida por las pruebas"
    ),
    "modulo:adapters.fixture_run_actions_probe": (
        "es la sonda de runs de mentira que usa la batería del observador de runs: "
        "un doble en `src/` para no duplicarlo en cada batería"
    ),
    "definicion:adapters.fixture_run_actions_probe.FixedRunActionsProbe": (
        "es la clase de esa sonda de mentira, compartida por las pruebas"
    ),
    "modulo:adapters.memory_supervisor_journal": (
        "es el diario de supervisión en memoria, el doble que usan "
        "`test_durable_supervisor_journal.py` y `test_supervisor.py`"
    ),
    "definicion:adapters.memory_supervisor_journal.InMemorySupervisorJournal": (
        "es la clase de ese diario en memoria, compartida por las pruebas"
    ),
    # --- Deuda destapada el 12-09-2026: módulos -----------------------------
    "modulo:adapters.github_worker_request": (
        "proyecta el encargo que se le manda al trabajador de GitHub, y en producción "
        "solo lo nombran docstrings; su única usuaria es `tests/engine/test_worker_request.py`"
    ),
    "modulo:governance": (
        "es el bloque de gasto y de fallo técnico del motor; en producción solo lo cita "
        "un comentario de `ports/store.py:98`, que es exactamente la forma de estar muerto"
    ),
    "modulo:profile_registry": (
        "es el registro de perfiles de agente, y en producción no lo nombra nadie, "
        "ni siquiera en un comentario"
    ),
    "modulo:worker_request": (
        "es la proyección determinista del encargo; en producción solo lo citan los "
        "docstrings de `issue_body_projection.py` y del propio módulo"
    ),
    # --- Deuda destapada el 12-09-2026: definiciones ------------------------
    "definicion:adapters.durable.entity_codec.entity_to_dict": (
        "es el codificador genérico de entidades del almacén durable, y no lo usa nadie: "
        "ni producción ni una sola prueba"
    ),
    "definicion:adapters.github_worker_request.read_procedure_text": (
        "lee el texto del procedimiento que se le entrega al trabajador; solo la usa "
        "`tests/engine/test_worker_request.py`"
    ),
    "definicion:adapters.github_worker_request.project_github_prompt": (
        "arma el prompt del trabajador de GitHub; solo la usa `tests/engine/test_worker_request.py`"
    ),
    "definicion:capability_registry.load_capability_registry": (
        "carga el registro de capacidades desde disco; solo la usan tres baterías de "
        "`tests/engine/`, y ningún camino de producción"
    ),
    "definicion:domain.budget.leer_limite_declarado": (
        "lee el límite de gasto que declara el encargo; solo la usa `tests/engine/test_budget.py`"
    ),
    "definicion:domain.permission_envelope.ENVELOPE_VACIO": (
        "es el sobre de permisos vacío del dominio; solo lo usa "
        "`tests/engine/test_permission_envelope.py`"
    ),
    "definicion:drip_guard.annotate_observations": (
        "es la variante sin veredictos de la anotación del goteo: producción llama "
        "siempre a `annotate_observations_with_verdicts`, y a esta solo su batería"
    ),
    "definicion:governance.registrar_gasto": (
        "es la ÚNICA función que actualiza el gasto del encargo, y no la llama nadie en "
        "producción: el presupuesto del §11 no se descuenta en ninguna pasada real"
    ),
    "definicion:governance.resolver_fallo_tecnico": (
        "decide qué hacer ante un fallo técnico del trabajador, y en producción no la "
        "invoca ningún camino"
    ),
    "definicion:memoria.problemas_de_la_leccion": (
        "es el detector de lecciones mal declaradas de ADR-174; lo ejecuta "
        "`tests/automation/test_mina_de_lecciones.py`, y ninguna pasada de producción"
    ),
    "definicion:mirror_projection.leer_y_proyectar_run": (
        "lee un run de GitHub y lo proyecta al dominio; solo la usa "
        "`tests/engine/test_mirror_projection.py`"
    ),
    "definicion:profile_registry.load_agent_profile": (
        "carga el perfil de un agente por su referencia; solo la usan cuatro baterías "
        "de `tests/engine/`, y ningún camino de producción"
    ),
    "definicion:projection_verifier.verificar_despacho": (
        "compara un despacho con lo que la incidencia proyecta; su módulo sí está vivo, "
        "pero a esta función solo la llama `tests/engine/test_projection_verifier.py`"
    ),
    "definicion:worker_request.project_worker_request": (
        "es la proyección del encargo hacia el trabajador; solo la usa "
        "`tests/engine/test_worker_request.py`"
    ),
    # --- Deuda destapada el 12-09-2026: campos escritos y nunca leídos ------
    # Esta es la forma exacta de `cerrada`: alguien los rellena en el
    # constructor y nadie los lee después.
    "campo:authority_reversion.ResultadoReversion.revierte": (
        "dice si la reversión de autoridad procede, y nadie lee el campo: el resultado "
        "se construye y se tira"
    ),
    "campo:authority_reversion.ResultadoReversion.aviso": (
        "es el aviso que acompaña a esa reversión, y tampoco lo lee nadie"
    ),
    "campo:context_recall.Referencia.fragmento": (
        "es el trozo de texto encontrado en una búsqueda de contexto, y no lo lee nadie: "
        "ni producción ni una prueba"
    ),
    "campo:domain.context_fragment.ContextFragment.contenido": (
        "es el contenido del fragmento de contexto, y no lo lee nadie: ni producción ni una prueba"
    ),
    "campo:domain.escalation.Escalada.ocurrida_en": (
        "es la fecha en que se escaló, y no la lee nadie: ni producción ni una prueba"
    ),
    "campo:domain.intent.IntentSignal.mensaje_original": (
        "guarda lo que el humano escribió antes de interpretarlo, y no lo lee nadie"
    ),
    "campo:domain.mirror.OrigenLectura.leido_en": (
        "es cuándo se leyó el espejo; solo lo leen dos baterías de `tests/engine/`"
    ),
    "campo:domain.mirror.VeredictoPublicado.rol": (
        "es el rol que publicó el veredicto; solo lo lee `tests/engine/test_mirror_projection.py`"
    ),
    "campo:domain.mirror.VeredictoPublicado.referencia": (
        "es el comentario donde vive ese veredicto, y no lo lee nadie"
    ),
    "campo:domain.mirror.PermisoDeReanudacion.forma": (
        "dice de qué forma se concedió el permiso de reanudación; solo lo leen dos "
        "baterías de `tests/engine/`"
    ),
    "campo:domain.mirror.PermisoDeReanudacion.referencia": (
        "es dónde consta ese permiso, y no lo lee nadie: el recibo de ADR-159 se arma sin él"
    ),
    "campo:domain.mirror.MirroredWorkItem.autoritativo": (
        "marca si el espejo del encargo manda sobre el motor, y solo lo lee "
        "`tests/engine/test_mirror_projection.py`"
    ),
    "campo:domain.mirror.MirroredRun.autoritativo": (
        "es el mismo marcador para el espejo de un run, y tampoco lo lee producción"
    ),
    "campo:domain.profile.AgentProfile.mision": (
        "es la misión del perfil de agente; solo la lee `tests/engine/test_agent_profile.py`"
    ),
    "campo:domain.profile.AgentProfile.contrato_entrada": (
        "es lo que el perfil promete recibir; solo lo lee `tests/engine/test_agent_profile.py`"
    ),
    "campo:domain.profile.AgentProfile.contrato_salida": (
        "es lo que el perfil promete entregar; solo lo leen dos baterías de `tests/engine/`"
    ),
    "campo:governance.ResultadoGasto.cortado": (
        "dice si el gasto cortó el encargo, y no lo lee producción; es el campo del "
        "módulo `governance`, que entero está sin cablear"
    ),
    "campo:memoria.Encargo.sucesos": (
        "es la lista de sucesos del encargo en la memoria; solo la lee "
        "`tests/engine/test_memoria.py`"
    ),
    "campo:session.RespuestaTurno.intake": (
        "es la admisión de trabajo que devuelve un turno de sesión, y no la lee producción"
    ),
    "campo:seven_day_streak.EvaluacionRacha.dias_consecutivos": (
        "es la cuenta de días verdes seguidos del §11.2: se calcula y nadie la lee, "
        "solo dos baterías de `tests/engine/`"
    ),
    "campo:worker_request.WorkerRequest.capacidades_resueltas": (
        "son las capacidades ya resueltas del encargo; solo las lee "
        "`tests/engine/test_worker_request.py`"
    ),
}

#: La pieza que tumbó a esta guarda. Se nombra aquí, y no en un comentario,
#: porque `test_la_pieza_que_tumbo_la_guarda_esta_vigilada` la usa: era un campo
#: de un dataclass, la lista a mano solo admitía módulos, y por eso la octava
#: aparición de la familia la encontró una persona leyendo código y no la
#: batería que existe para encontrarla.
PIEZA_QUE_TUMBO_LA_GUARDA = "campo:domain.mirror.MirroredWorkItem.cerrada"

#: Las cuatro que vigilaba la lista a mano, para que la derivación no pueda
#: perder en silencio la cobertura que ya había.
PIEZAS_DE_LA_LISTA_A_MANO = (
    "modulo:authority_reversion",
    "modulo:seven_day_streak",
    "modulo:projection_verifier",
    "modulo:supervisor",
)

#: Suelo del inventario. La lista a mano tenía 4 entradas y la derivación
#: encontró 826 el 12-09-2026; un inventario que cayera por debajo de 400 sería
#: una derivación rota, no un motor adelgazado, y esta batería lo diría en vez
#: de pasar en vacío sobre lo poco que quedara.
SUELO_DEL_INVENTARIO = 400


def _vigiladas() -> list[Pieza]:
    return [p for p in piezas_del_motor() if p.identidad not in SIN_LLAMANTE_CONOCIDO]


@pytest.mark.parametrize("pieza", _vigiladas(), ids=lambda p: p.identidad)
def test_cada_pieza_publica_tiene_quien_la_llame(pieza: Pieza) -> None:
    """Una pieza sin llamante está muerta aunque sus pruebas estén en verde."""
    assert llamantes(pieza), (
        f"`{pieza.identidad}` ({pieza.ruta}) no la llama nadie en producción.\n"
        "Está construida, probada y muerta: es la novena vez que pasa en esta casa. "
        "O se cablea, o se retira, o se declara en SIN_LLAMANTE_CONOCIDO con su razón."
    )


@pytest.mark.parametrize("identidad", sorted(SIN_LLAMANTE_CONOCIDO))
def test_cada_excepcion_sigue_correspondiendo_a_una_pieza(identidad: str) -> None:
    """Una excepción que ya no nombra nada es una excepción que hay que borrar.

    Sin esto, la lista se llena de fantasmas y deja de decir cuánta deuda hay,
    que es la única razón por la que se escribe.
    """
    conocidas = {pieza.identidad for pieza in piezas_del_motor()}
    assert identidad in conocidas, (
        f"`{identidad}` está declarada como excepción y ya no existe en el motor.\n"
        "Bórrala de SIN_LLAMANTE_CONOCIDO: una excepción a una pieza que no está "
        "no exime de nada y falsea la cuenta de la deuda."
    )


@pytest.mark.parametrize("identidad", sorted(SIN_LLAMANTE_CONOCIDO))
def test_ninguna_excepcion_sobra(identidad: str) -> None:
    """Si la pieza YA tiene llamante, la excepción sobra y se borra.

    Este es el cierre que la lista a mano no podía tener. Una lista de inclusión
    a la que le falta una entrada está callada; una de exclusión que ya no hace
    falta grita, y por eso restar es mejor que sumar.
    """
    por_identidad = {pieza.identidad: pieza for pieza in piezas_del_motor()}
    pieza = por_identidad.get(identidad)
    if pieza is None:
        pytest.skip("lo dice test_cada_excepcion_sigue_correspondiendo_a_una_pieza")
    quienes = llamantes(pieza)
    assert not quienes, (
        f"`{identidad}` ya tiene llamante en producción ({', '.join(quienes[:3])}).\n"
        "Se cableó: borra su entrada de SIN_LLAMANTE_CONOCIDO para que vuelva a estar "
        "vigilada. Una excepción que sobra es el escondite donde se pudre la siguiente."
    )


@pytest.mark.parametrize(("identidad", "razon"), sorted(SIN_LLAMANTE_CONOCIDO.items()))
def test_cada_excepcion_declara_su_razon(identidad: str, razon: str) -> None:
    """Una excepción sin razón escrita es una lista de nombres, no una decisión."""
    assert len(razon.strip()) >= 40, (
        f"la excepción `{identidad}` no explica por qué esa pieza puede estar sin "
        "llamante. Sin el motivo, un rojo aquí parece burocracia y se silencia."
    )


def test_el_inventario_se_deriva_y_no_esta_vacio() -> None:
    """Anti-vacua: un inventario vacío haría pasar esta batería sin medir nada.

    Es la cuarta forma de prueba vacua de `patrones.md`: una puerta parametrizada
    sobre una lista vacía siempre está verde.
    """
    piezas = piezas_del_motor()
    assert len(piezas) >= SUELO_DEL_INVENTARIO, (
        f"el inventario derivado trae {len(piezas)} piezas y el suelo son "
        f"{SUELO_DEL_INVENTARIO}: la derivación está rota, no el motor adelgazado"
    )
    tipos = {pieza.tipo for pieza in piezas}
    assert tipos == {"modulo", "definicion", "campo"}, (
        f"el inventario solo ve {sorted(tipos)}. Si pierde los campos vuelve a ser "
        "ciega para `cerrada`, que es el caso que la tumbó"
    )
    assert _vigiladas(), "todas las piezas están exceptuadas: esta batería no mediría nada"


def test_las_identidades_del_inventario_son_unicas() -> None:
    """Dos piezas con la misma identidad romperían el mapa de excepciones.

    Una excepción escrita para una eximiría a la otra sin que nadie lo viera, y
    volveríamos a tener un escondite.
    """
    identidades = [pieza.identidad for pieza in piezas_del_motor()]
    repetidas = sorted({i for i in identidades if identidades.count(i) > 1})
    assert not repetidas, (
        f"identidades repetidas en el inventario: {repetidas}. "
        "Hay que darles más contexto en `piezas_del_motor`"
    )


def test_la_pieza_que_tumbo_la_guarda_esta_vigilada() -> None:
    """`MirroredWorkItem.cerrada` entra en el inventario y tiene lector.

    Esta es la prueba que fija lo que pedía el encargo. Sobre la guarda vieja no
    podía ni escribirse: `PIEZAS` eran cuatro nombres de módulo y un campo de un
    dataclass no cabía en esa forma. Con la mutación que quita `espejo.cerrada`
    de `reflect.py`, la guarda vieja sigue en verde y esta se pone en rojo — las
    dos direcciones que ADR-001 §3 exige.
    """
    por_identidad = {pieza.identidad: pieza for pieza in piezas_del_motor()}
    pieza = por_identidad.get(PIEZA_QUE_TUMBO_LA_GUARDA)
    assert pieza is not None, (
        f"`{PIEZA_QUE_TUMBO_LA_GUARDA}` no está en el inventario derivado: la guarda "
        "ha vuelto a ser ciega para la forma de pieza que la tumbó"
    )
    assert PIEZA_QUE_TUMBO_LA_GUARDA not in SIN_LLAMANTE_CONOCIDO, (
        "la pieza que tumbó a esta guarda no puede estar exceptuada de ella"
    )
    quienes = llamantes(pieza)
    assert quienes, (
        "`MirroredWorkItem.cerrada` volvió a quedarse sin lector. Es el campo que "
        "`mirror_projection.py` escribe y que ADR-173 encontró muerto: sin él, un "
        "encargo cuya incidencia se cerró no termina nunca."
    )


@pytest.mark.parametrize("identidad", PIEZAS_DE_LA_LISTA_A_MANO)
def test_las_cuatro_de_la_lista_a_mano_siguen_vigiladas(identidad: str) -> None:
    """La derivación no puede perder en silencio lo que ya se vigilaba.

    Sin esto, una derivación que se estrechara por error dejaría de mirar las
    cuatro piezas que motivaron esta batería y nadie se enteraría: estaría verde.
    """
    por_identidad = {pieza.identidad: pieza for pieza in piezas_del_motor()}
    assert identidad in por_identidad, (
        f"`{identidad}` lo vigilaba la lista a mano y la derivación ya no lo ve"
    )
    assert identidad not in SIN_LLAMANTE_CONOCIDO, (
        f"`{identidad}` estaba vigilado y ahora está exceptuado, sin decir por qué"
    )
