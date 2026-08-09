"""Las métricas del §9 de la especificación, calculadas sobre lo recuperado.

**No mide tiempo.** Aquí se juzga *qué* devolvió cada participante, no *cuánto
tardó*: la latencia es otro eje y vive en el ejecutor.

CINCO PUERTAS BOOLEANAS Y NINGUNA CIFRA
=======================================

El §9 fija que cinco métricas **no dependen de ninguna tolerancia**:
contaminación cero, fuga de ámbito cero, confusión de polaridad cero,
conformidad de etapa verdadera y borrado/regeneración completos. Son recuentos
absolutos y booleanos, y por eso pueden **descartar** a un candidato aunque no
hubiera cifras de entorno congeladas.

Las tres primeras son de fallo duro (§6.1): **un solo** resultado prohibido, una
sola fuga o una sola fusión descartan al candidato, por perfecto que sea el
resto. No se promedian ni se ponderan; se cuentan.

POR QUÉ LA CONFORMIDAD DE ETAPA NO SE LEE DEL RESULTADO
=======================================================

El §6.1 dice que `C-17` es el único fallo duro que puede darse **con resultados
perfectos**: devolver exactamente lo correcto saltándose `E0-E5` incumple `B04`
igual que devolver basura. De modo que esta métrica no mira los resultados:
mira la **traza**, que es donde consta qué etapas se recorrieron y por qué se
pasó de una a la siguiente.

LO QUE NO SE CALCULA, Y NO EN SILENCIO
======================================

`B04-M14` —explicabilidad— tiene su **regla de muestreo sin fuente conocida**
(§12 incertidumbre 2). Aquí se calcula la fracción de resultados con los siete
elementos de `RF-28` registrados, que es la forma que el §9 fija, y se declara
que la regla de muestreo no está congelada: la cifra es descriptiva, no una
puerta.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from experiments.adr002.candidates.common.contracts import Etapa, Polaridad
from experiments.adr002.round.cases import CasoEjecutable

#: Etapas que **no originan** candidatas: `E0` prepara y `E5` adjudica. Ningún
#: resultado puede tener su origen ahí, de modo que un caso que declare `E0` o
#: `E5` como etapa de resolución no está fijando un origen; está diciendo otra
#: cosa, y ``etapa_conforme`` la comprueba aparte.
ETAPAS_QUE_NO_ORIGINAN: Final[frozenset[str]] = frozenset({"E0", "E5"})

#: Los siete elementos que `B04-RF-28` exige por resultado.
ELEMENTOS_DE_RF_28: Final[tuple[str, ...]] = (
    "coincidencia",
    "ambito",
    "tiempo",
    "estado",
    "procedencias",
    "criticidad",
    "razon_de_orden",
)

#: Las cinco puertas que no dependen de ninguna cifra (§9).
PUERTAS_BOOLEANAS: Final[tuple[str, ...]] = (
    "contaminacion_cero",
    "fuga_de_ambito_cero",
    "confusion_de_polaridad_cero",
    "conformidad_de_etapa",
    "borrado_y_regeneracion",
)

#: Las tres de fallo duro: una sola ocurrencia descarta (§6.1).
PUERTAS_DE_FALLO_DURO: Final[tuple[str, ...]] = (
    "contaminacion_cero",
    "fuga_de_ambito_cero",
    "confusion_de_polaridad_cero",
)


@dataclass(frozen=True, slots=True)
class VeredictoDeCaso:
    """Lo observado en un caso, por participante. Sin promediar nada."""

    caso: str
    canonico: str
    adjudicable: bool
    obtenido: tuple[str, ...]
    esperado: tuple[str, ...]
    contaminacion: tuple[str, ...]
    fuga_de_ambito: tuple[str, ...]
    confusion_de_polaridad: tuple[str, ...]
    #: Lecturas de polaridad contrarias al canon. Se publica; no es puerta.
    polaridad_mal_leida: tuple[str, ...]
    etapa_conforme: bool
    razon_de_etapa: str
    #: Si la métrica de etapa de este caso puntúa. No lo hace cuando la propia
    #: instanciación se contradice: el conflicto es suyo, no del participante.
    etapa_puntua: bool
    resultado_exacto: bool
    #: Si el caso declara un orden total. Catorce casos declaran `CONJUNTO` sin
    #: orden, y para ellos ``orden_exacto`` no significa nada: contarlos como
    #: aciertos o como fallos falsearía la fracción en direcciones opuestas.
    declara_orden: bool
    orden_exacto: bool
    ausencia_correcta: bool
    criticos_pendientes: tuple[str, ...]
    explicaciones_completas: int
    resultados_totales: int
    suficiencia: str
    estado_externo: str
    parada: str
    etapas_recorridas: tuple[str, ...]

    @property
    def sin_fallo_duro(self) -> bool:
        return not (self.contaminacion or self.fuga_de_ambito or self.confusion_de_polaridad)


def contaminacion(obtenido: Sequence[str], caso: CasoEjecutable) -> tuple[str, ...]:
    """Resultados prohibidos que aparecieron. Recuento absoluto, puerta 2."""
    prohibidos = frozenset(caso.prohibidos)
    return tuple(identidad for identidad in obtenido if identidad in prohibidos)


def fuga_de_ambito(
    obtenido: Sequence[str], caso: CasoEjecutable, proyecto_por_identidad: Mapping[str, str | None]
) -> tuple[str, ...]:
    """Resultados fuera del ámbito declarado. Recuento absoluto, puerta 8.

    Se comprueba contra el **proyecto real** de cada resultado, no contra la
    lista de señuelos: los señuelos son los casos que la referencia previó, y
    una fuga que nadie previó sigue siendo una fuga.

    UN ELEMENTO GLOBAL NO ES UNA FUGA
    =================================

    Un elemento de ámbito global —proyecto nulo, que es como la proyección
    codifica «no pertenece a ningún proyecto»— es visible desde cualquier
    ámbito, y por eso `G4` lo admite sin condición. Contarlo aquí como fuga
    hacía que **la puerta y el corrector discreparan sobre el mismo elemento**:
    el candidato hacía lo correcto y la medición lo marcaba con un fallo duro
    del §6.1.

    No es teoría. En el canon hay exactamente un elemento así, `MEMORIA:1`, y
    ninguna de las corridas publicadas llegó a entregarlo en un caso acotado a
    proyecto, de modo que el desacuerdo nunca afloró. Al medir la señal
    semántica real sí aflora: es una memoria de tono, próxima a casi cualquier
    consulta, y apareció en tres puntos del barrido marcando fuga donde no la
    había.

    IDENTIDAD DESCONOCIDA SIGUE SIENDO FUGA
    =======================================

    Ausente del mapa **no** es lo mismo que sin proyecto. De una identidad que
    el canon no reconoce no se puede afirmar que esté dentro de ámbito, así que
    se cuenta. Distinguir los dos casos evita que la corrección de arriba
    abriera un agujero por el que pasaría cualquier identidad inventada.
    """
    ambito = caso.peticion.ambito
    fugas: list[str] = []
    for identidad in obtenido:
        if identidad not in proyecto_por_identidad:
            fugas.append(identidad)
            continue
        proyecto = proyecto_por_identidad[identidad]
        if proyecto is None:
            continue
        if not ambito.autoriza(proyecto):
            fugas.append(identidad)
    return tuple(fugas)


def confusion_de_polaridad(
    obtenido: Sequence[str],
    polaridad_leida: Mapping[str, Polaridad],
    polaridad_del_canon: Mapping[str, Polaridad],
) -> tuple[str, ...]:
    """Pares de la misma respuesta que el participante **no distingue**. `RF-19`.

    La puerta del §9 cuenta «fusiones afirmación/negación», y el §6.1 dice qué
    es fundir y qué no: «Fundir ambas es fallo; recuperarlas **marcadas y
    distinguidas** es correcto». De modo que lo que se cuenta es un **par**: dos
    resultados que el canon declara con polaridad opuesta y que el participante
    entrega con la misma marca —o sin marca—, y que por tanto ya no pueden
    distinguirse.

    Leer una polaridad **al revés** es otro defecto y se cuenta aparte, en
    ``polaridad_mal_leida``: es una lectura errónea de `RF-17`, no una fusión, y
    meterla aquí haría fallar la puerta por algo que la puerta no nombra.

    Un participante que **no lee polaridad** no distingue nada: cualquier par
    opuesto que devuelva queda fundido. No es una penalización inventada; es lo
    que «recuperarlas marcadas y distinguidas» exige, y quien no marca no
    distingue.
    """
    conocidos = [i for i in obtenido if i in polaridad_del_canon]
    fundidos: list[str] = []
    for posicion, primero in enumerate(conocidos):
        for segundo in conocidos[posicion + 1 :]:
            if polaridad_del_canon[primero] == polaridad_del_canon[segundo]:
                continue
            marca_a = polaridad_leida.get(primero)
            marca_b = polaridad_leida.get(segundo)
            if marca_a is None or marca_b is None or marca_a == marca_b:
                fundidos.append(f"{primero}|{segundo}")
    return tuple(fundidos)


def polaridad_mal_leida(
    obtenido: Sequence[str],
    polaridad_leida: Mapping[str, Polaridad],
    polaridad_del_canon: Mapping[str, Polaridad],
) -> tuple[str, ...]:
    """Resultados cuya polaridad leída contradice la del canon. **No es puerta.**

    `RF-17` obliga a validar polaridad; leerla al revés es incumplirlo. Pero el
    §9 no lo pone entre las cinco puertas booleanas, y ascenderlo a puerta por
    mi cuenta descartaría candidatos por un criterio que nadie aprobó. Se mide,
    se publica y se deja a la vista.
    """
    return tuple(
        identidad
        for identidad in obtenido
        if identidad in polaridad_del_canon
        and identidad in polaridad_leida
        and polaridad_leida[identidad] != polaridad_del_canon[identidad]
    )


def etapa_conforme(
    caso: CasoEjecutable, etapas_recorridas: Sequence[str], etapa_de_resolucion: str | None
) -> tuple[bool, str]:
    """`RF-14`: sin saltos, y resuelto donde el caso dijo. Devuelve razón.

    Dos cosas distintas, y las dos obligatorias:

    1. **Sin saltos en la expansión.** Las etapas **de expansión** recorridas
       —de `E1` a `E4`— deben ser consecutivas desde `E1`: pasar de `E1` a `E3` sin
       `E2` es el salto que `RF-14` prohíbe. **Parar antes no es saltar**: la
       política escalonada manda expandir solo por insuficiencia, de modo que
       `E1` sola es lo correcto cuando `E1` basta.
    2. **Resuelto donde tocaba.** La etapa que aportó el resultado debe ser la
       que el caso declaró. Resolver antes no es mejor: significa que la
       referencia esperaba una expansión que no ocurrió.

    `E0` y `E5` quedan fuera de la comprobación de contigüidad **porque no
    expanden**: `E0` prepara y `E5` adjudica, y las dos corren siempre. Meterlas
    en la cadena hacía que `E0 → E1 → E5` —la traza de un caso que se resuelve
    en `E1`, es decir, el caso perfecto— se leyera como un salto.

    Un caso sin resultados no tiene etapa de resolución, y entonces solo se
    exige lo primero: no hay dónde comprobar lo segundo, e inventar una etapa
    de resolución para un conjunto vacío sería inventar el veredicto.
    """
    expansion = [e.value for e in Etapa if e.value not in ETAPAS_QUE_NO_ORIGINAN]
    recorridas = [e for e in etapas_recorridas if e in expansion]
    posiciones = [expansion.index(e) for e in recorridas]
    if posiciones != sorted(posiciones) or len(set(posiciones)) != len(posiciones):
        return False, f"etapas de expansion fuera de orden: {recorridas}"
    if posiciones and posiciones != list(range(len(posiciones))):
        return False, f"salto de etapa: {recorridas} no arranca en E1 y sigue"

    esperada = caso.etapa_esperada
    if esperada == "E0":
        # El caso se zanja ANTES de expandir. Lo comprobable es que ninguna
        # etapa de expansion aportase, no que `E0` originase: `E0` prepara.
        if etapa_de_resolucion is None:
            return True, "zanjado antes de expandir, como el caso declara (E0)"
        return False, f"el caso declara E0 y la expansion aporto en {etapa_de_resolucion}"
    if esperada == "E5":
        # `E5` adjudica; ningun resultado se origina alli. Lo que el caso fija
        # con `E5` es que la respuesta se cierra en la adjudicacion, y eso ya
        # lo comprueban la parada y el conjunto esperado. Exigir origen en `E5`
        # seria exigir lo imposible para todos por igual.
        return True, "adjudicado en E5; el origen no se fija (E5 no origina)"
    if etapa_de_resolucion is None:
        return True, "sin resultados: no hay etapa de resolucion que comprobar"
    if etapa_de_resolucion != esperada:
        return False, f"resuelto en {etapa_de_resolucion} y el caso declara {esperada}"
    return True, f"resuelto en {esperada}, como el caso declara"


def ausencia_correcta(caso: CasoEjecutable, obtenido: Sequence[str], estado_externo: str) -> bool:
    """`RF-25`/`RF-26`: declarar ausencia solo cuando la ausencia es real.

    El fallo duro `C-14` es el «no existe» **falso**: decir que no hay nada
    cuando el contenido existía pero no era reportable. Aquí se comprueba lo
    simétrico y comprobable: que el estado externo de ausencia acompañe a un
    conjunto esperado vacío, y solo a él.
    """
    esperaba_nada = not caso.resultado_esperado
    declaro_nada = not obtenido
    if esperaba_nada:
        return declaro_nada
    return not declaro_nada and bool(estado_externo)


def criticos_pendientes(
    caso: CasoEjecutable, obtenido: Sequence[str], criticos: Sequence[str]
) -> tuple[str, ...]:
    """`B04-M01` y `TOL-204`: críticos elegibles que no se cubrieron.

    Un crítico que el límite dejó pendiente **no cuenta**: la referencia lo
    declaró pendiente, y exigirlo sería exigir que el límite no se respetase.
    """
    entregados = frozenset(obtenido)
    excusados = frozenset(caso.pendientes_por_limite)
    return tuple(
        identidad
        for identidad in criticos
        if identidad in frozenset(caso.resultado_esperado)
        and identidad not in entregados
        and identidad not in excusados
    )


@dataclass(frozen=True, slots=True)
class Resumen:
    """Lo que un participante consiguió sobre todos los casos adjudicables."""

    participante: str
    casos_adjudicados: int
    casos_no_adjudicables: int
    contaminacion_total: int
    fuga_de_ambito_total: int
    confusion_de_polaridad_total: int
    polaridad_mal_leida_total: int
    casos_con_etapa_conforme: int
    casos_con_etapa_puntuable: int
    casos_con_resultado_exacto: int
    casos_con_orden_exacto: int
    casos_con_orden_declarado: int
    casos_con_ausencia_correcta: int
    criticos_pendientes_total: int
    explicaciones_completas: int
    resultados_totales: int
    borrado_y_regeneracion: bool

    @property
    def puertas(self) -> dict[str, bool]:
        """Las cinco puertas booleanas del §9, sin ponderar ninguna."""
        return {
            "contaminacion_cero": self.contaminacion_total == 0,
            "fuga_de_ambito_cero": self.fuga_de_ambito_total == 0,
            "confusion_de_polaridad_cero": self.confusion_de_polaridad_total == 0,
            "conformidad_de_etapa": self.casos_con_etapa_conforme == self.casos_con_etapa_puntuable,
            "borrado_y_regeneracion": self.borrado_y_regeneracion,
        }

    @property
    def pasa_las_puertas(self) -> bool:
        return all(self.puertas.values())

    @property
    def descartado_por_fallo_duro(self) -> bool:
        """Una sola ocurrencia basta (§6.1). No se promedia."""
        return any(not self.puertas[puerta] for puerta in PUERTAS_DE_FALLO_DURO)


def resumir(
    participante: str,
    veredictos: Sequence[VeredictoDeCaso],
    *,
    borrado_y_regeneracion: bool,
) -> Resumen:
    """Agrega **solo** los casos adjudicables. Los demás se cuentan aparte."""
    adjudicados = [v for v in veredictos if v.adjudicable]
    con_orden = [v for v in adjudicados if v.declara_orden]
    return Resumen(
        participante=participante,
        casos_adjudicados=len(adjudicados),
        casos_no_adjudicables=len(veredictos) - len(adjudicados),
        contaminacion_total=sum(len(v.contaminacion) for v in adjudicados),
        fuga_de_ambito_total=sum(len(v.fuga_de_ambito) for v in adjudicados),
        confusion_de_polaridad_total=sum(len(v.confusion_de_polaridad) for v in adjudicados),
        polaridad_mal_leida_total=sum(len(v.polaridad_mal_leida) for v in adjudicados),
        casos_con_etapa_conforme=sum(1 for v in adjudicados if v.etapa_puntua and v.etapa_conforme),
        casos_con_etapa_puntuable=sum(1 for v in adjudicados if v.etapa_puntua),
        casos_con_resultado_exacto=sum(1 for v in adjudicados if v.resultado_exacto),
        casos_con_orden_exacto=sum(1 for v in con_orden if v.orden_exacto),
        casos_con_orden_declarado=len(con_orden),
        casos_con_ausencia_correcta=sum(1 for v in adjudicados if v.ausencia_correcta),
        criticos_pendientes_total=sum(len(v.criticos_pendientes) for v in adjudicados),
        explicaciones_completas=sum(v.explicaciones_completas for v in adjudicados),
        resultados_totales=sum(v.resultados_totales for v in adjudicados),
        borrado_y_regeneracion=borrado_y_regeneracion,
    )


__all__ = [
    "ELEMENTOS_DE_RF_28",
    "PUERTAS_BOOLEANAS",
    "PUERTAS_DE_FALLO_DURO",
    "Resumen",
    "VeredictoDeCaso",
    "ausencia_correcta",
    "confusion_de_polaridad",
    "contaminacion",
    "criticos_pendientes",
    "etapa_conforme",
    "fuga_de_ambito",
    "polaridad_mal_leida",
    "resumir",
]
