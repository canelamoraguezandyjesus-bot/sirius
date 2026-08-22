"""Los casos congelados, convertidos en peticiones ejecutables. **No mide.**

La familia de conformidad declara cada caso como datos: consulta, modo,
propósito, permiso, ámbito, tiempo, cardinalidad, etapa esperada, parada
esperada, orden esperado, elegibles y prohibidos. El motor común recibe una
``Peticion``. Este módulo hace **solo** esa traducción, y la hace igual para
los cinco participantes: si tradujera distinto según quién va a ejecutar,
mediría el traductor.

TRES TRADUCCIONES QUE NO SON OBVIAS, Y POR QUÉ SON ESAS
=======================================================

**El permiso.** ``Peticion`` no tiene campo de permiso: lo que el motor
comprueba en ``E0`` es que el propósito esté declarado, y un propósito no
declarado bloquea antes de recuperar. Un caso ``NO_AUTORIZADO`` es exactamente
eso —``B04-RF-02``: sin autorización no se recupera—, de modo que se traduce
como **propósito vacío**. No es un atajo: es el único punto del contrato donde
la falta de autorización tiene efecto, y traducirlo a cualquier otra cosa
inventaría un mecanismo que el motor no tiene.

**El límite.** Solo cuatro casos declaran límite en su dominio. Los demás no
declaran ninguno, y ``Peticion`` exige dos números. Poner ahí el número de
elegibles filtraría el oráculo al candidato; poner uno pequeño convertiría en
truncamiento lo que el caso no quiso truncar. Se usa un límite que **no ata**,
igual para los cinco: el tamaño del canon. Un límite que nunca corta es la
traducción fiel de «este caso no declara límite».

**El tiempo.** Un caso declara su instante objetivo, y uno declara un
intervalo (``SOLAPA_INTERVALO``). ``VentanaTemporal`` sostiene un instante y un
corte de registro, no un intervalo. Se toma **el extremo final** del intervalo
como instante objetivo, que es el instante en que el solapamiento declarado ya
ha terminado de ocurrir, y la desviación queda declarada en
``DESVIACIONES_DE_TRADUCCION`` para que viaje con la evidencia.

LO QUE NO SE TRADUCE, Y TAMPOCO EN SILENCIO
===========================================

``espacios_autorizados`` se deja en su valor por defecto —las cuatro etapas de
expansión— para **todos** los casos y **todos** los participantes. Los casos no
instancian qué espacios autoriza cada modo, y restringirlos aquí sería
inventarlo; además, una restricción mal puesta penalizaría al participante cuya
señal viva en la etapa cerrada, que es justo lo que el principio 3 del §3 de la
especificación prohíbe.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Cardinalidad,
    Modo,
    Peticion,
    VentanaTemporal,
)
from experiments.adr002.projection import contracts as pc

DIRECTORIO_DE_LA_FAMILIA: Final = Path(__file__).resolve().parents[1] / "benchmark"

#: Los tres artefactos de los que sale un caso ejecutable.
CASOS: Final = "cases_v0_5.json"
REFERENCIAS: Final = "references_v0_5.json"
CORPUS: Final = "conformance_corpus_v0_6.json"

#: Tipo de referencia que esta ronda ejecuta. Las de recuento de consumidores
#: no son casos de recuperación —la matriz v0.4 §7 las sacó de serlo— y no
#: entran: ejecutarlas exigiría un motor que no es este.
TIPO_EJECUTABLE: Final = "RECUPERACION_B04"

#: Ámbito declarado como global en la instanciación.
AMBITO_GLOBAL: Final = "GLOBAL"

#: Permiso que, por `B04-RF-02`, impide recuperar.
PERMISO_SIN_AUTORIZAR: Final = "NO_AUTORIZADO"

#: Modo cuyo contrato admite elementos no vigentes.
MODO_HISTORICO: Final = "M2"

#: Casos que el canon declara **no adjudicables**, con su razón literal. El §12
#: incertidumbre 1 de la especificación del benchmark los nombra: sin la clase
#: de equivalencia de orden (`RED-033`) ni las tolerancias de `RF-26`
#: (`RED-032`) congeladas, no hay referencia contra la que juzgarlos.
#:
#: Se ejecutan igual, porque su evidencia vale; lo que no se hace es **puntuar**
#: su veredicto. Excluirlos del recuento sin decirlo convertiría una carencia
#: declarada del canon en un dato que nadie ve.
NO_ADJUDICABLES: Final[Mapping[str, str]] = {
    "B04-CA-37": "RED-032 sin congelar: las tolerancias de texto, estado, conteo y tiempo "
    "de RF-26 no existen todavia (especificacion v0.3 §12 incertidumbre 1)",
    "B04-CA-39": "RED-033 sin congelar: la clase de equivalencia de orden no existe "
    "todavia (especificacion v0.3 §12 incertidumbre 1)",
    "B04-CA-48": "RED-032 sin congelar: las tolerancias de texto, estado, conteo y tiempo "
    "de RF-26 no existen todavia (especificacion v0.3 §12 incertidumbre 1)",
}

#: Cardinalidad con la que se ejecuta un caso que no declara ninguna. Solo
#: alcanza a los no adjudicables: un caso adjudicable sin cardinalidad seria un
#: defecto de la familia, y este modulo falla cerrado ante el.
CARDINALIDAD_SIN_DECLARAR: Final = "EXHAUSTIVA"

#: Desviaciones respecto de la especificación, declaradas por el §10.11.
DESVIACIONES_DE_TRADUCCION: Final[tuple[str, ...]] = (
    "el permiso NO_AUTORIZADO se traduce como proposito vacio, que es el unico "
    "punto del contrato comun donde la falta de autorizacion tiene efecto (E0)",
    "un caso declara su tiempo objetivo como intervalo; VentanaTemporal sostiene "
    "un instante, y se toma el extremo final del intervalo",
    "los casos que no declaran limite reciben un limite que no ata, igual para "
    "los cinco participantes: el tamano del canon",
    "espacios_autorizados queda en su valor por defecto para todos los casos y "
    "todos los participantes: los casos no instancian que espacios autoriza cada modo",
)


class CasoNoTraducibleError(RuntimeError):
    """Un caso congelado que este traductor no sabe convertir. Falla cerrado."""


@dataclass(frozen=True, slots=True)
class CasoEjecutable:
    """Un caso de la familia, listo para el motor, con su referencia al lado.

    La petición es lo que se ejecuta; el resto es lo que el veredicto compara.
    Van juntos a propósito: separarlos permitiría ejecutar con una petición y
    juzgar con la referencia de otra.
    """

    identificador: str
    canonico: str
    nivel: int
    peticion: Peticion
    cardinalidad_declarada: str
    etapa_esperada: str
    parada_esperada: str | None
    #: Conjunto esperado, **calculado** por la adjudicación del dominio. Es la
    #: autoridad: la matriz v0.4 §2 prohíbe escribirlo a mano.
    resultado_esperado: tuple[str, ...]
    #: Orden esperado cuando el caso declara uno. Catorce casos declaran
    #: `CONJUNTO` sin orden, y para ellos esto está vacío **con intención**:
    #: exigirles un orden sería inventar una referencia que el caso no fijó.
    orden_esperado: tuple[str, ...]
    tipo_de_orden: str
    elegibles: tuple[str, ...]
    prohibidos: tuple[str, ...]
    #: Elegibles que el límite deja fuera. No son fallo si no aparecen.
    pendientes_por_limite: tuple[str, ...]
    #: Señuelos fuera del ámbito declarado. Si aparecen, hay fuga de ámbito.
    decoys_fuera_de_ambito: tuple[str, ...]
    permiso: str
    proyecto_declarado: str
    #: Identidades que la referencia nombra y que **no son del canon**
    #: —documentos y mensajes—. No pueden ser resultados, de modo que no
    #: puntúan; se conservan porque apartarlas sin decirlo ocultaría que la
    #: referencia las nombró.
    referencias_fuera_del_canon: tuple[str, ...] = ()
    #: Si su veredicto cuenta. Los no adjudicables se ejecutan y se registran,
    #: pero no puntúan: no hay referencia congelada contra la que juzgarlos.
    adjudicable: bool = True
    motivo_no_adjudicable: str = ""

    @property
    def sin_autorizacion(self) -> bool:
        return self.permiso == PERMISO_SIN_AUTORIZAR

    @property
    def declara_orden(self) -> bool:
        return bool(self.orden_esperado) and self.tipo_de_orden == "ORDEN_TOTAL"

    @property
    def etapa_inconsistente(self) -> bool:
        """El caso declara zanjarse en `E0` **y** espera resultados.

        `E0` prepara y no expande: ninguna candidata puede originarse allí. Un
        caso que declare `E0` y a la vez espere elementos pide dos cosas que no
        pueden pasar a la vez, y el conflicto es de la instanciación, no del
        participante que lo ejecuta.

        No se corrige aquí —la referencia de nivel 1 no se reescribe— y no se
        calla: su métrica de etapa no puntúa, y el motivo viaja con la
        evidencia. Es el defecto que el §0.1 punto 5 de la especificación dejó
        anotado como abierto: «el campo 12 no está instanciado en su segunda
        mitad».
        """
        return self.etapa_esperada == "E0" and bool(self.resultado_esperado)


def _valor(campo: object) -> Any:
    """Un campo instanciado es ``{valor, fuente, seccion, estado}`` o el valor."""
    if isinstance(campo, Mapping) and "valor" in campo:
        return campo["valor"]
    return campo


def _identidades_canonicas(identificadores: Sequence[object]) -> tuple[str, ...]:
    """Del vocabulario del corpus al del canon, descartando lo que no es canon.

    ``MSG`` y ``DOC`` existen en el corpus pero no son elementos del canon: no
    pueden ser resultados, y por eso no pueden ser elegibles ni prohibidos.

    Acepta las **dos** formas que la familia usa: el identificador desnudo y el
    par ``{id, razon}`` de las listas motivadas. Aceptar solo la primera hacía
    que las listas de señuelos y de prohibidos llegasen vacías sin que nada
    fallara, que es la peor forma de perder un control.
    """
    return tuple(identidad for identidad, _ in _clasificar(identificadores)[0])


def _clasificar(
    identificadores: Sequence[object],
) -> tuple[list[tuple[str, str]], list[str]]:
    """Separa lo que es canon de lo que no. Devuelve ambas listas.

    Lo no canónico no se tira en silencio: una referencia que nombra un
    documento prohibido está diciendo algo, y perderlo dejaría la puerta de
    contaminación sin poder detectarlo **y sin que nadie lo supiera**.
    """
    del_canon: list[tuple[str, str]] = []
    fuera: list[str] = []
    for entrada in identificadores:
        crudo = entrada.get("id") if isinstance(entrada, Mapping) else entrada
        if crudo is None:
            continue
        identidad = pc.referencia_canonica(str(crudo))
        if identidad is None:
            continue
        if identidad.split(":")[0] in pc.CLASES_DEL_CANON:
            del_canon.append((identidad, str(crudo)))
        else:
            fuera.append(identidad)
    return del_canon, fuera


def _instante(declarado: str) -> str:
    """El instante objetivo. Un intervalo se resuelve por su extremo final."""
    return declarado.split("/")[-1] if "/" in declarado else declarado


def _ambito(declarado: str, numeros: Mapping[str, int]) -> Ambito:
    if declarado == AMBITO_GLOBAL:
        return Ambito(global_=True, proyectos=())
    numero = numeros.get(declarado)
    if numero is None:
        msg = f"ambito declarado que el corpus no numera: {declarado!r}"
        raise CasoNoTraducibleError(msg)
    return Ambito(global_=False, proyectos=(str(numero),))


def _limites(dominio: Mapping[str, Any], *, sin_atar: int) -> tuple[int, int]:
    """``(objetivo, duro)``. Sin límite declarado, uno que no ata."""
    limite = dominio.get("limite")
    if not isinstance(limite, Mapping):
        return sin_atar, sin_atar
    n = int(limite["n"])
    if limite.get("tipo") == "DURO":
        return n, n
    return n, sin_atar


def _modo(declarado: str) -> Modo:
    try:
        return Modo(declarado)
    except ValueError as error:
        msg = f"modo declarado fuera de M1-M5: {declarado!r}"
        raise CasoNoTraducibleError(msg) from error


def _cardinalidad(declarada: str) -> Cardinalidad:
    try:
        return Cardinalidad(declarada)
    except ValueError as error:
        msg = f"cardinalidad declarada fuera del vocabulario: {declarada!r}"
        raise CasoNoTraducibleError(msg) from error


def cargar_artefactos(directorio: Path | None = None) -> dict[str, Any]:
    """Lee los tres artefactos congelados. No valida blobs: eso es de la ronda."""
    origen = DIRECTORIO_DE_LA_FAMILIA if directorio is None else directorio
    return {
        nombre: json.loads((origen / nombre).read_text(encoding="utf-8"))
        for nombre in (CASOS, REFERENCIAS, CORPUS)
    }


def casos_ejecutables(artefactos: Mapping[str, Any]) -> tuple[CasoEjecutable, ...]:
    """Los casos de nivel 1 de recuperación, traducidos, en orden declarado.

    El orden es el del artefacto congelado, no un orden calculado aquí: la
    ronda ejecuta los casos en el orden en que la familia los declara, y así
    dos corridas recorren lo mismo en la misma secuencia.
    """
    casos = artefactos[CASOS]
    referencias = artefactos[REFERENCIAS]
    corpus = artefactos[CORPUS]

    numeros = {str(p["id"]): posicion for posicion, p in enumerate(corpus["proyectos"], start=1)}
    sin_atar = len(corpus["items"])
    por_caso = {str(r["caso"]): r for r in referencias["referencias_nivel_1"]}

    ejecutables: list[CasoEjecutable] = []
    for caso in casos["nivel_1"]:
        identificador = str(caso["id"])
        referencia = por_caso.get(identificador)
        if referencia is None or referencia["tipo_referencia"] != TIPO_EJECUTABLE:
            continue
        ejecutables.append(_traducir(caso, referencia, numeros=numeros, sin_atar=sin_atar))
    return tuple(ejecutables)


def _traducir(
    caso: Mapping[str, Any],
    referencia: Mapping[str, Any],
    *,
    numeros: Mapping[str, int],
    sin_atar: int,
) -> CasoEjecutable:
    """Un caso congelado y su referencia, en una petición y su veredicto."""
    instanciacion = caso["instanciacion"]
    identificador = str(caso["id"])
    canonico = str(caso["identificador_canonico"])
    motivo = NO_ADJUDICABLES.get(canonico, "")
    permiso = str(_valor(instanciacion["permiso"]))
    proyecto = str(_valor(instanciacion["ambito"]))
    modo = str(_valor(instanciacion["modo"]))
    proposito = "" if permiso == PERMISO_SIN_AUTORIZAR else str(_valor(instanciacion["proposito"]))
    corte = _valor(instanciacion["corte_registro"])
    adjudicacion = referencia.get("adjudicacion", {})
    dominio = adjudicacion.get("dominio", {})
    objetivo, duro = _limites(dominio, sin_atar=sin_atar)

    orden_declarado = _valor(instanciacion["orden"])
    tipo_de_orden = "CONJUNTO"
    if isinstance(orden_declarado, Mapping):
        tipo_de_orden = str(orden_declarado.get("tipo") or "CONJUNTO")
        orden_declarado = orden_declarado.get("valor")
    #: ``valor: null`` con ``tipo: CONJUNTO`` es una declaración, no un hueco:
    #: el caso fija **qué** se espera y deja **en qué orden** sin fijar.
    orden_declarado = list(orden_declarado or ())

    cardinalidad = _valor(instanciacion["cardinalidad"])
    if cardinalidad is None:
        if not motivo:
            msg = f"{identificador} ({canonico}) no declara cardinalidad y es adjudicable"
            raise CasoNoTraducibleError(msg)
        cardinalidad = CARDINALIDAD_SIN_DECLARAR

    peticion = Peticion(
        operation_id=f"ronda-primaria:{identificador}",
        consulta=str(_valor(instanciacion["consulta"])),
        proposito=proposito,
        modo=_modo(modo),
        ambito=_ambito(proyecto, numeros),
        ventana=VentanaTemporal(
            tiempo_objetivo=_instante(str(_valor(instanciacion["tiempo_objetivo"]))),
            corte_de_registro=None if corte is None else str(corte),
        ),
        cardinalidad=_cardinalidad(str(cardinalidad)),
        limite_objetivo=objetivo,
        limite_duro=duro,
        admite_no_vigentes=modo == MODO_HISTORICO,
    )
    parada = _valor(instanciacion["parada"])
    #: Los prohibidos vienen de dos sitios y los dos vinculan: la lista que el
    #: caso instancia y los que la adjudicación calculó como incumplidores de
    #: una puerta. Quedarse con una sola dejaría fuera prohibidos reales.
    listas = {
        "prohibidos_instanciados": list(_valor(instanciacion["prohibidos"]) or ()),
        "prohibidos_adjudicados": list(adjudicacion.get("prohibidos_entre_candidatos") or ()),
        "elegibles": list(_valor(instanciacion["elegibles"]) or ()),
        "resultado_esperado": list(adjudicacion.get("resultado_esperado") or ()),
    }
    clasificadas = {nombre: _clasificar(lista) for nombre, lista in listas.items()}
    fuera = sorted({identidad for _, apartadas in clasificadas.values() for identidad in apartadas})
    prohibidos = {
        identidad
        for nombre in ("prohibidos_instanciados", "prohibidos_adjudicados")
        for identidad, _ in clasificadas[nombre][0]
    }
    return CasoEjecutable(
        identificador=identificador,
        canonico=canonico,
        nivel=int(caso["nivel"]),
        peticion=peticion,
        cardinalidad_declarada=str(cardinalidad),
        etapa_esperada=str(_valor(instanciacion["etapa"])),
        parada_esperada=None if parada is None else str(parada),
        resultado_esperado=tuple(i for i, _ in clasificadas["resultado_esperado"][0]),
        orden_esperado=_identidades_canonicas(orden_declarado),
        tipo_de_orden=tipo_de_orden,
        elegibles=tuple(i for i, _ in clasificadas["elegibles"][0]),
        prohibidos=tuple(sorted(prohibidos)),
        pendientes_por_limite=_identidades_canonicas(
            list(adjudicacion.get("pendientes_por_limite") or ())
        ),
        decoys_fuera_de_ambito=_identidades_canonicas(
            list(adjudicacion.get("decoys_fuera_de_ambito") or ())
        ),
        permiso=permiso,
        proyecto_declarado=proyecto,
        referencias_fuera_del_canon=tuple(fuera),
        adjudicable=not motivo,
        motivo_no_adjudicable=motivo,
    )


__all__ = [
    "CASOS",
    "CORPUS",
    "DESVIACIONES_DE_TRADUCCION",
    "PERMISO_SIN_AUTORIZAR",
    "REFERENCIAS",
    "TIPO_EJECUTABLE",
    "CasoEjecutable",
    "CasoNoTraducibleError",
    "cargar_artefactos",
    "casos_ejecutables",
]
