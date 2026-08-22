"""Constructor determinista de la proyeccion experimental.

Recibe **por firma** el corpus y los tres canales laterales. No abre ficheros
por su cuenta ni conoce los nombres de los artefactos de oraculo: la
independencia respecto del oraculo no es una promesa, es que no tiene por donde
leerlo.

Determinismo: ningun identificador depende del orden de recorrido, ningun valor
depende del reloj, y toda la escritura ordena por identidad canonica. Dos
construcciones sobre las mismas entradas producen el mismo contenido logico y
la misma huella.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from experiments.adr002.benchmark import schema_v0_5 as S5
from experiments.adr002.candidates.common import derived
from experiments.adr002.projection.contracts import (
    ARTEFACTOS_FUENTE,
    CAMPOS_DE_CRITICIDAD_APLICADA,
    CAMPOS_QUE_NO_CRUZAN_A_ITEM_CANONICO,
    CAPACIDAD_DEL_PLANO,
    CONSUMIDORES_DEL_PLANO,
    FAMILIA_FUENTE,
    PERDIDA_POR_COLAPSO_DE_ESTADO,
    VERSION_PROYECCION,
    Plano,
    ProyeccionError,
    ProyeccionExperimental,
    clases_candidatas_de_equivalencia,
    estado_de_decision,
    estado_de_memoria,
    identidad_canonica,
    numero_canonico,
    referencia_canonica,
)

from sirius.adapters.persistence.migrations import upgrade_to_head

#: Conversacion unica que aloja el historial. El canon exige una; el corpus no
#: modela conversaciones, de modo que se declara una sola y se dice aqui.
_CONVERSACION: Final = 1

#: El corpus no declara proyecto activo. Marcar uno seria elegir a que items
#: favorece el desempate por proyecto activo de Sirius 0.1, de modo que
#: **ninguno** lo es y el desempate queda uniformemente falso.
_NINGUN_PROYECTO_ACTIVO: Final = 0

#: Unica relacion que el canon de Sirius 0.1 materializa como columna.
_RELACION_MATERIALIZADA: Final = "SUSTITUYE_A"

_DDL_EJES_P2: Final = """
CREATE TABLE ejes_del_item (
    identidad TEXT PRIMARY KEY,
    corpus_id TEXT NOT NULL UNIQUE,
    clase TEXT NOT NULL,
    confirmacion TEXT NOT NULL,
    validez TEXT NOT NULL,
    disponibilidad TEXT NOT NULL,
    sensibilidad TEXT NOT NULL,
    ambito TEXT NOT NULL,
    autoridad TEXT NOT NULL,
    no_usar_como_memoria INTEGER NOT NULL,
    no_consolidable INTEGER NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    occurred_at TEXT,
    recorded_at TEXT NOT NULL,
    ambito_declarado TEXT NOT NULL
);
CREATE TABLE ejes_reservados_al_arnes (
    identidad TEXT PRIMARY KEY,
    polaridad TEXT NOT NULL,
    condicion TEXT,
    motivo_de_no_cruce TEXT NOT NULL
);
CREATE TABLE procedencias (
    identidad TEXT NOT NULL,
    orden INTEGER NOT NULL,
    referencia TEXT NOT NULL,
    referencia_canonica TEXT,
    PRIMARY KEY (identidad, orden)
);
CREATE TABLE entidades (
    id TEXT PRIMARY KEY,
    nombre_canonico TEXT NOT NULL
);
CREATE TABLE alias_de_entidad (
    entidad TEXT NOT NULL,
    alias TEXT NOT NULL,
    PRIMARY KEY (entidad, alias)
);
CREATE TABLE entidades_del_item (
    identidad TEXT NOT NULL,
    entidad TEXT NOT NULL,
    PRIMARY KEY (identidad, entidad)
);
CREATE TABLE relaciones (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    origen TEXT NOT NULL,
    destino TEXT NOT NULL,
    origen_canonico TEXT,
    destino_canonico TEXT,
    materializada_en_el_canon INTEGER NOT NULL
);
CREATE TABLE documentos (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    accesible INTEGER NOT NULL,
    texto TEXT,
    afirmacion_atribuida TEXT
);
CREATE TABLE ejes_del_mensaje (
    identidad TEXT PRIMARY KEY,
    corpus_id TEXT NOT NULL UNIQUE,
    project_id TEXT NOT NULL,
    no_guardar INTEGER NOT NULL,
    redactado INTEGER NOT NULL
);
CREATE TABLE proyectos (
    id TEXT PRIMARY KEY,
    numero INTEGER NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL
);
CREATE TABLE alias_de_proyecto (
    proyecto TEXT NOT NULL,
    alias TEXT NOT NULL,
    PRIMARY KEY (proyecto, alias)
);
CREATE TABLE miembros_de_lista_cerrada (
    lista TEXT NOT NULL,
    miembro TEXT NOT NULL,
    PRIMARY KEY (lista, miembro)
);
"""

_DDL_RESERVADO: Final = """
CREATE TABLE property_key (
    identidad TEXT PRIMARY KEY,
    valor TEXT
);
CREATE TABLE criticidad_aplicada (
    identidad TEXT PRIMARY KEY,
    nivel TEXT,
    razon_segura TEXT,
    fuente_de_politica TEXT,
    regla_de_politica TEXT
);
"""


def _huella(contenido: object) -> str:
    """SHA-256 de la forma canonica. No se hashea el fichero SQLite.

    Un fichero SQLite no es reproducible byte a byte —lleva paginas libres y
    contadores de cambio—, de modo que hashearlo daria un falso negativo de
    determinismo. Lo que se congela es el **contenido logico**.
    """
    serializado = json.dumps(contenido, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _texto(valor: object) -> str:
    if not isinstance(valor, str):
        msg = f"se esperaba texto y llego {type(valor).__name__}: {valor!r}"
        raise ProyeccionError(msg)
    return valor


def _comprobar_vocabulario(campo: str, valor: str, admitidos: Sequence[str]) -> None:
    """Falla cerrado: un valor fuera del vocabulario P2 aborta la proyeccion."""
    if valor not in admitidos:
        msg = (
            f"{campo} = {valor!r} fuera del vocabulario P2 congelado "
            f"{sorted(admitidos)}; la proyeccion no admite valores nuevos"
        )
        raise ProyeccionError(msg)


def _validar_vocabularios(items: Sequence[Mapping[str, Any]]) -> None:
    """Los ocho vocabularios P2 que la familia sucesora cerro.

    Se invocan del esquema congelado, no se reescriben aqui: una copia seria
    una segunda fuente de verdad que podria divergir en silencio.
    """
    for item in items:
        _comprobar_vocabulario("kind", _texto(item["kind"]), ("MEMORIA", "DECISION"))
        _comprobar_vocabulario("polaridad", _texto(item["polaridad"]), S5.POLARIDAD)
        _comprobar_vocabulario("confirmacion", _texto(item["confirmacion"]), S5.CONFIRMACION)
        _comprobar_vocabulario("validez", _texto(item["validez"]), S5.VALIDEZ)
        _comprobar_vocabulario("disponibilidad", _texto(item["disponibilidad"]), S5.DISPONIBILIDAD)
        _comprobar_vocabulario("sensibilidad", _texto(item["sensibilidad"]), S5.SENSIBILIDAD)
        _comprobar_vocabulario("ambito", _texto(item["ambito"]), S5.AMBITO)
        _comprobar_vocabulario("autoridad", _texto(item["autoridad"]), S5.AUTORIDAD)
        criticidad = item.get("criticidad")
        if criticidad is not None:
            _comprobar_vocabulario(
                "criticidad.nivel", _texto(criticidad["nivel"]), S5.NIVEL_CRITICIDAD
            )


def _numeros_de_proyecto(proyectos: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Numeracion estable por posicion declarada en el corpus congelado."""
    numeros: dict[str, int] = {}
    for posicion, proyecto in enumerate(proyectos, start=1):
        identificador = _texto(proyecto["id"])
        if identificador in numeros:
            msg = f"proyecto duplicado en el corpus: {identificador!r}"
            raise ProyeccionError(msg)
        numeros[identificador] = posicion
    return numeros


def _construir_entrada(
    destino: Path,
    corpus: Mapping[str, Any],
    sujetos: Mapping[str, str | None],
    numeros_de_proyecto: Mapping[str, int],
) -> None:
    """La base del esquema canonico de Sirius 0.1. **Sin DDL adicional.**"""
    upgrade_to_head(destino)
    conexion = sqlite3.connect(str(destino))
    conexion.execute("PRAGMA foreign_keys=ON")
    try:
        cursor = conexion.cursor()
        instante = _texto(corpus["ahora_declarado"])
        cursor.execute(
            "INSERT INTO conversations (id, created_at, is_main) VALUES (?, ?, 1)",
            (_CONVERSACION, instante),
        )
        for proyecto in corpus["proyectos"]:
            cursor.execute(
                "INSERT INTO projects (id, name, objective, current_state, next_step, "
                "is_active, created_at, updated_at, blockers, status) "
                "VALUES (?, ?, '', '', '', ?, ?, ?, '', 'active')",
                (
                    numeros_de_proyecto[_texto(proyecto["id"])],
                    _texto(proyecto["nombre"]),
                    _NINGUN_PROYECTO_ACTIVO,
                    instante,
                    instante,
                ),
            )

        sustituciones: list[tuple[int, int]] = []
        for relacion in corpus["relaciones"]:
            if _texto(relacion["tipo"]) != _RELACION_MATERIALIZADA:
                continue
            origen, destino_id = _texto(relacion["origen"]), _texto(relacion["destino"])
            if origen.startswith("DEC-") and destino_id.startswith("DEC-"):
                sustituciones.append((numero_canonico(origen), numero_canonico(destino_id)))

        for item in corpus["items"]:
            corpus_id = _texto(item["id"])
            numero = numero_canonico(corpus_id)
            proyecto = numeros_de_proyecto[_texto(item["project_id"])]
            registrado = _texto(item["temporalidad"]["recorded_at"])
            # Ausencia real de sujeto: el canon exige texto en decisions.subject,
            # y la cadena vacia es la unica forma de "sin sujeto" que admite.
            # Fabricar uno seria P-SUJETO-01, la proyeccion expresamente
            # descartada.
            sujeto = sujetos.get(corpus_id) or ""
            if _texto(item["kind"]) == "MEMORIA":
                cursor.execute(
                    "INSERT INTO memories (id, status, created_at, updated_at, subject_key, "
                    "project_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        numero,
                        estado_de_memoria(
                            _texto(item["confirmacion"]),
                            _texto(item["validez"]),
                            _texto(item["disponibilidad"]),
                        ),
                        registrado,
                        registrado,
                        sujeto or None,
                        None if _texto(item["ambito"]) == "GLOBAL" else proyecto,
                    ),
                )
                cursor.execute(
                    "INSERT INTO memory_revisions (memory_id, version, content, origin, "
                    "is_current, created_at) VALUES (?, 1, ?, 'proyeccion', 1, ?)",
                    (numero, _texto(item["text"]), registrado),
                )
            else:
                cursor.execute(
                    "INSERT INTO decisions (id, subject, project_id, status, created_at, "
                    "updated_at, supersedes_decision_id) VALUES (?, ?, ?, ?, ?, ?, NULL)",
                    (
                        numero,
                        sujeto,
                        proyecto,
                        estado_de_decision(
                            _texto(item["confirmacion"]),
                            _texto(item["validez"]),
                            _texto(item["disponibilidad"]),
                        ),
                        registrado,
                        registrado,
                    ),
                )
                cursor.execute(
                    "INSERT INTO decision_revisions (decision_id, version, content, "
                    "source_event_id, is_current, created_at) VALUES (?, 1, ?, NULL, 1, ?)",
                    (numero, _texto(item["text"]), registrado),
                )

        for origen, destino_id in sorted(sustituciones):
            cursor.execute(
                "UPDATE decisions SET supersedes_decision_id = ? WHERE id = ?",
                (destino_id, origen),
            )

        for secuencia, mensaje in enumerate(corpus["mensajes"]):
            corpus_id = _texto(mensaje["id"])
            redactado = bool(mensaje["redactado"])
            cursor.execute(
                "INSERT INTO messages (id, conversation_id, sequence, role, content, "
                "created_at, operation_id, identity_version, status, redacted_at) "
                "VALUES (?, ?, ?, 'user', ?, ?, ?, 1, 'completed', ?)",
                (
                    numero_canonico(corpus_id),
                    _CONVERSACION,
                    secuencia,
                    None if redactado else _texto(mensaje["texto"]),
                    _texto(mensaje["recorded_at"]),
                    f"proyeccion-{corpus_id}",
                    _texto(mensaje["recorded_at"]) if redactado else None,
                ),
            )
        conexion.commit()
    finally:
        conexion.close()


def _construir_ejes_p2(
    destino: Path,
    corpus: Mapping[str, Any],
    numeros_de_proyecto: Mapping[str, int],
) -> None:
    """Los ejes que el esquema canonico no puede sostener. Sin oraculo."""
    conexion = sqlite3.connect(str(destino))
    try:
        conexion.executescript(_DDL_EJES_P2)
        cursor = conexion.cursor()
        for item in sorted(corpus["items"], key=lambda i: identidad_canonica(_texto(i["id"]))):
            corpus_id = _texto(item["id"])
            identidad = identidad_canonica(corpus_id)
            temporalidad = item["temporalidad"]
            cursor.execute(
                "INSERT INTO ejes_del_item (identidad, corpus_id, clase, confirmacion, validez, "
                "disponibilidad, sensibilidad, ambito, autoridad, no_usar_como_memoria, "
                "no_consolidable, valid_from, valid_to, occurred_at, recorded_at, "
                "ambito_declarado) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    identidad,
                    corpus_id,
                    _texto(item["kind"]),
                    _texto(item["confirmacion"]),
                    _texto(item["validez"]),
                    _texto(item["disponibilidad"]),
                    _texto(item["sensibilidad"]),
                    _texto(item["ambito"]),
                    _texto(item["autoridad"]),
                    int(bool(item["no_usar_como_memoria"])),
                    int(bool(item["no_consolidable"])),
                    temporalidad["valid_from"],
                    temporalidad["valid_to"],
                    temporalidad["occurred_at"],
                    _texto(temporalidad["recorded_at"]),
                    _texto(item["project_id"]),
                ),
            )
            cursor.execute(
                "INSERT INTO ejes_reservados_al_arnes (identidad, polaridad, condicion, "
                "motivo_de_no_cruce) VALUES (?, ?, ?, ?)",
                (
                    identidad,
                    _texto(item["polaridad"]),
                    item["condicion"],
                    CAMPOS_QUE_NO_CRUZAN_A_ITEM_CANONICO["polaridad"],
                ),
            )
            for orden, referencia in enumerate(item["procedencia"]):
                cursor.execute(
                    "INSERT INTO procedencias (identidad, orden, referencia, "
                    "referencia_canonica) VALUES (?, ?, ?, ?)",
                    (identidad, orden, _texto(referencia), referencia_canonica(_texto(referencia))),
                )
            for entidad in sorted(item["entity_ids"]):
                cursor.execute(
                    "INSERT INTO entidades_del_item (identidad, entidad) VALUES (?, ?)",
                    (identidad, _texto(entidad)),
                )

        for entidad in corpus["entidades"]:
            # Ni nota ni grupo_homonimo: la clasificacion los declara oraculo.
            # grupo_homonimo es precisamente la respuesta de G5 —que dos
            # homonimos no se fusionan—, y entregarla seria dar el resultado.
            cursor.execute(
                "INSERT INTO entidades (id, nombre_canonico) VALUES (?, ?)",
                (_texto(entidad["id"]), _texto(entidad["nombre_canonico"])),
            )
            for alias in sorted(entidad["alias"]):
                cursor.execute(
                    "INSERT INTO alias_de_entidad (entidad, alias) VALUES (?, ?)",
                    (_texto(entidad["id"]), _texto(alias)),
                )

        for relacion in corpus["relaciones"]:
            origen, destino_id = _texto(relacion["origen"]), _texto(relacion["destino"])
            # Sin nota: la clasificacion la declara oraculo prohibido.
            cursor.execute(
                "INSERT INTO relaciones (id, tipo, origen, destino, origen_canonico, "
                "destino_canonico, materializada_en_el_canon) VALUES (?,?,?,?,?,?,?)",
                (
                    _texto(relacion["id"]),
                    _texto(relacion["tipo"]),
                    origen,
                    destino_id,
                    referencia_canonica(origen),
                    referencia_canonica(destino_id),
                    int(
                        _texto(relacion["tipo"]) == _RELACION_MATERIALIZADA
                        and origen.startswith("DEC-")
                        and destino_id.startswith("DEC-")
                    ),
                ),
            )

        for documento in corpus["documentos"]:
            cursor.execute(
                "INSERT INTO documentos (id, titulo, accesible, texto, afirmacion_atribuida) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    _texto(documento["id"]),
                    _texto(documento["titulo"]),
                    int(bool(documento["accesible"])),
                    documento["texto"],
                    documento["afirmacion_atribuida"],
                ),
            )

        for mensaje in corpus["mensajes"]:
            corpus_id = _texto(mensaje["id"])
            cursor.execute(
                "INSERT INTO ejes_del_mensaje (identidad, corpus_id, project_id, no_guardar, "
                "redactado) VALUES (?, ?, ?, ?, ?)",
                (
                    identidad_canonica(corpus_id),
                    corpus_id,
                    _texto(mensaje["project_id"]),
                    int(bool(mensaje["no_guardar"])),
                    int(bool(mensaje["redactado"])),
                ),
            )

        for proyecto in corpus["proyectos"]:
            identificador = _texto(proyecto["id"])
            cursor.execute(
                "INSERT INTO proyectos (id, numero, nombre, tipo) VALUES (?, ?, ?, ?)",
                (
                    identificador,
                    numeros_de_proyecto[identificador],
                    _texto(proyecto["nombre"]),
                    _texto(proyecto["tipo"]),
                ),
            )
            for alias in sorted(proyecto["alias"]):
                cursor.execute(
                    "INSERT INTO alias_de_proyecto (proyecto, alias) VALUES (?, ?)",
                    (identificador, _texto(alias)),
                )
            for miembro in sorted(proyecto["miembros_lista_cerrada"]):
                cursor.execute(
                    "INSERT INTO miembros_de_lista_cerrada (lista, miembro) VALUES (?, ?)",
                    (identificador, _texto(miembro)),
                )
        conexion.commit()
    finally:
        conexion.close()


def _construir_reservado(
    destino: Path,
    corpus: Mapping[str, Any],
    propiedades: Mapping[str, str | None],
    criticidad: Mapping[str, Mapping[str, str] | None],
) -> None:
    """``property_key`` y criticidad aplicada. Ningun candidato lo abre."""
    conexion = sqlite3.connect(str(destino))
    try:
        conexion.executescript(_DDL_RESERVADO)
        cursor = conexion.cursor()
        for item in corpus["items"]:
            corpus_id = _texto(item["id"])
            identidad = identidad_canonica(corpus_id)
            # Presente en TODOS los items, null incluido: la ausencia se
            # declara, y una fila que faltase seria indistinguible de un item
            # que la proyeccion olvido.
            if corpus_id not in propiedades:
                msg = f"property_key ausente para {corpus_id!r}; el canal lateral debe ser total"
                raise ProyeccionError(msg)
            cursor.execute(
                "INSERT INTO property_key (identidad, valor) VALUES (?, ?)",
                (identidad, propiedades[corpus_id]),
            )
            if corpus_id not in criticidad:
                msg = f"criticidad aplicada ausente para {corpus_id!r}; el plano debe ser total"
                raise ProyeccionError(msg)
            aplicada = criticidad[corpus_id]
            cursor.execute(
                "INSERT INTO criticidad_aplicada (identidad, nivel, razon_segura, "
                "fuente_de_politica, regla_de_politica) VALUES (?, ?, ?, ?, ?)",
                (
                    identidad,
                    *(
                        None if aplicada is None else aplicada[c]
                        for c in CAMPOS_DE_CRITICIDAD_APLICADA
                    ),
                ),
            )
        conexion.commit()
    finally:
        conexion.close()


#: Directorio de los artefactos congelados. La lectura se limita a los cuatro
#: nombres de ``ARTEFACTOS_FUENTE``: no hay ruta por la que un fichero de
#: oraculo pueda entrar.
DIRECTORIO_DE_LA_FAMILIA: Final = Path(__file__).resolve().parents[1] / "benchmark"


def cargar_familia() -> dict[str, Any]:
    """Lee **solo** los cuatro artefactos autorizados de la familia v0.6."""
    cargados: dict[str, Any] = {}
    for nombre in ARTEFACTOS_FUENTE:
        ruta = DIRECTORIO_DE_LA_FAMILIA / nombre
        if not ruta.exists():
            msg = f"artefacto congelado ausente: {ruta}"
            raise ProyeccionError(msg)
        cargados[nombre] = json.loads(ruta.read_text(encoding="utf-8"))
    return cargados


def construir_desde_la_familia(raiz: Path) -> ProyeccionExperimental:
    """Atajo de uso: carga los cuatro artefactos y materializa los tres planos."""
    cargados = cargar_familia()
    return construir(
        raiz,
        corpus=cargados["conformance_corpus_v0_6.json"],
        sujetos=cargados["subject_keys_v0_2.json"]["valores"],
        propiedades=cargados["property_keys_v0_2.json"]["valores"],
        criticidad=cargados["applied_criticality_v0_1.json"]["valores"],
    )


def construir(
    raiz: Path,
    *,
    corpus: Mapping[str, Any],
    sujetos: Mapping[str, str | None],
    propiedades: Mapping[str, str | None],
    criticidad: Mapping[str, Mapping[str, str] | None],
) -> ProyeccionExperimental:
    """Materializa los tres planos. Firma cerrada: el oraculo no cabe aqui."""
    items = corpus["items"]
    _validar_vocabularios(items)
    identidades = [identidad_canonica(_texto(i["id"])) for i in items]
    if len(set(identidades)) != len(identidades):
        msg = "colision de identidad canonica entre items del corpus"
        raise ProyeccionError(msg)
    for canal, nombre in ((sujetos, "sujetos"), (propiedades, "propiedades")):
        faltantes = {_texto(i["id"]) for i in items} - set(canal)
        if faltantes:
            msg = f"canal {nombre} incompleto: faltan {sorted(faltantes)[:5]}"
            raise ProyeccionError(msg)

    numeros_de_proyecto = _numeros_de_proyecto(corpus["proyectos"])
    raiz.mkdir(parents=True, exist_ok=True)
    _construir_entrada(raiz / "entrada.sqlite3", corpus, sujetos, numeros_de_proyecto)
    _construir_ejes_p2(raiz / "ejes_p2.sqlite3", corpus, numeros_de_proyecto)
    _construir_reservado(raiz / "reservado.sqlite3", corpus, propiedades, criticidad)
    return ProyeccionExperimental(raiz=raiz)


def _tablas_del_canon(conexion: sqlite3.Connection) -> list[str]:
    """Tablas propias, excluyendo el derivado FTS5 y sus sombras.

    El indice y sus tablas sombra son **derivado**: se reconstruyen del canon
    y sus paginas internas no son estables byte a byte. Incluirlos en la huella
    daria un falso negativo de determinismo sobre un contenido que ya esta
    determinado por las tablas base.
    """
    inventario = derived.inventariar(conexion)
    derivado = {*inventario.tablas, *inventario.sombras}
    return [
        str(fila[0])
        for fila in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        if str(fila[0]) not in derivado
    ]


def contenido_logico(proyeccion: ProyeccionExperimental) -> dict[str, Any]:
    """Volcado ordenado de los tres planos. Es lo que se congela y se compara."""
    volcado: dict[str, Any] = {}
    for plano in Plano:
        conexion = proyeccion.abrir(plano, "common")
        try:
            por_tabla: dict[str, Any] = {}
            for tabla in _tablas_del_canon(conexion):
                filas = [dict(fila) for fila in conexion.execute(f"SELECT * FROM {tabla}")]
                por_tabla[tabla] = sorted(
                    filas, key=lambda f: json.dumps(f, ensure_ascii=False, sort_keys=True)
                )
            volcado[plano.value] = por_tabla
        finally:
            conexion.close()
    return volcado


def manifiesto(
    proyeccion: ProyeccionExperimental,
    *,
    blobs_de_origen: Mapping[str, str],
    sujetos: Mapping[str, str | None],
    propiedades: Mapping[str, str | None],
) -> dict[str, Any]:
    """Custodia de la proyeccion: origen, reglas, perdidas y huellas."""
    volcado = contenido_logico(proyeccion)
    candidatas = clases_candidatas_de_equivalencia(
        {identidad_canonica(k): v for k, v in sujetos.items()},
        {identidad_canonica(k): v for k, v in propiedades.items()},
    )
    return {
        "documento": "Manifiesto de la proyeccion experimental de ADR-002",
        "version": VERSION_PROYECCION,
        "familia_fuente": FAMILIA_FUENTE,
        "estado": "PROPUESTO_NO_CONGELADO",
        "generador": "experiments/adr002/projection/build.py",
        "artefactos_fuente": list(ARTEFACTOS_FUENTE),
        "blobs_de_origen": dict(sorted(blobs_de_origen.items())),
        "independencia_del_oraculo": (
            "construir() recibe por firma el corpus y los tres canales laterales. "
            "No abre ficheros ni conoce los nombres de casos, referencias, "
            "adjudicaciones o resultados esperados: no puede leerlos."
        ),
        "regla_de_identidad": (
            "MEM-<n> -> MEMORIA:<n>, DEC-<n> -> DECISION:<n>, MSG-<n> -> MENSAJE:<n>, "
            "DOC-<n> -> DOCUMENTO:<n>. El numero sale del identificador, nunca de un "
            "contador de insercion, de modo que no depende del orden de recorrido."
        ),
        "referencias_sin_identidad_canonica": (
            "entidades y proyectos no son elementos del canon de Sirius 0.1 y su "
            "referencia canonica es null; inventarles una haria indistinguible "
            "«no existe en el canon» de «existe»."
        ),
        "planos": {
            plano.value: {
                "fichero": f"{plano.value}.sqlite3",
                "capacidades": list(CAPACIDAD_DEL_PLANO[plano]),
                "consumidores": list(CONSUMIDORES_DEL_PLANO[plano]),
                "tablas": sorted(volcado[plano.value]),
                "filas": {t: len(f) for t, f in sorted(volcado[plano.value].items())},
                "huella_logica": _huella(volcado[plano.value]),
            }
            for plano in Plano
        },
        "huella_logica_total": _huella(volcado),
        "perdidas_declaradas": {
            "colapso_de_estado": PERDIDA_POR_COLAPSO_DE_ESTADO,
            "ambito_multiproyecto": (
                "memories.project_id y decisions.project_id son una sola clave "
                "foranea y no pueden expresar una lista cerrada. El plano entrada "
                "guarda el numero del pseudo-proyecto; el ambito verdadero y sus "
                "miembros viajan en ejes_p2, y G4 debe leerlos de alli."
            ),
            "sujeto_ausente": (
                "decisions.subject es NOT NULL: la ausencia real de sujeto se "
                "proyecta como cadena vacia, que el puerto y las consultas por "
                "clave y por prefijo ya tratan como ausencia. Fabricar un sujeto "
                "seria P-SUJETO-01, la proyeccion expresamente descartada."
            ),
            "sin_proyecto_activo": (
                "el corpus no declara proyecto activo; marcar uno decidiria a "
                "quien favorece el desempate por proyecto activo. Ninguno lo es."
            ),
        },
        "campos_que_no_cruzan_a_item_canonico": dict(CAMPOS_QUE_NO_CRUZAN_A_ITEM_CANONICO),
        "deduplicacion_y_agrupacion": {
            "mecanismo_a_identidad_exacta": (
                "clave primaria de los tres planos; una identidad repetida aborta "
                "la construccion. No consulta sujeto ni propiedad."
            ),
            "mecanismo_b_equivalencia": (
                "clases CANDIDATAS por (subject_key_experimental, property_key), "
                "ambas no nulas. Son dos de los siete ejes de B04-Q13: los otros "
                "cinco los adjudica la capa comun, y esta proyeccion no fusiona nada."
            ),
            "clases_candidatas": {
                f"{sujeto}|{propiedad}": list(miembros)
                for (sujeto, propiedad), miembros in candidatas.items()
            },
        },
        "advertencia": (
            "Ninguna puerta de arranque queda satisfecha por esta proyeccion. El "
            "benchmark permanece BLOQUEADO, NO AUTORIZADO y NO EJECUTADO."
        ),
    }


__all__ = [
    "DIRECTORIO_DE_LA_FAMILIA",
    "cargar_familia",
    "construir",
    "construir_desde_la_familia",
    "contenido_logico",
    "manifiesto",
]
