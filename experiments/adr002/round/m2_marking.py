"""El marcado de `M2`, que el canon exige y ninguna métrica comprobaba.

`B04`, modo `M2 · Histórico explícito`:

    «Permite archivado, sustituido y finalizado con marcas temporales; separa
    tiempo válido de corte de registro **y nunca lo presenta como actual**.»

La readjudicación dejó esto escrito como `pendiente_de_medir` y así se quedó. Es
una **obligación canónica sin control**, y cerrar `ADR-002` sin ella sería cerrar
sobre una puerta que nunca se abrió. Este módulo la abre.

POR QUÉ MEDIRLO NO EXIGIÓ DESCONGELAR NADA
==========================================

Porque la marca **ya salía**: ``trace.py`` rellena ``Explicacion.estado`` y
``Explicacion.tiempo`` en cada resultado. Medir fue **leer** lo publicado y
contrastarlo con lo que el corpus declara, sin tocar candidatos ni fichas.

Eso importa por el orden en que ocurrieron las cosas: primero se midió sin tocar
nada —y `M2.1` y `M2.2` salieron verdes, `M2.3` roja—, y **solo después**, con el
defecto medido y publicado, se corrigió ``trace.py`` para que publicase cuál de
los tres estados es cada elemento. La medición no se diseñó sabiendo el arreglo:
el arreglo se hizo sabiendo la medición.

La lectura previa, con `M2.3` en rojo, sigue en ``SALIDA_PREVIA``. Sobrescribirla
habría borrado la prueba de que el defecto existía.

LAS TRES OBLIGACIONES, POR SEPARADO
===================================

La frase del canon dice tres cosas distintas, y mezclarlas en un solo booleano
las haría indistinguibles:

1. **Nunca como actual.** Lo que el canon no tiene por vigente no puede volver
   marcado «vigente». Es la parte prohibitiva, y es la más grave si falla.
2. **Separa tiempo válido de corte de registro.** Las dos marcas temporales
   tienen que venir, y venir distinguibles.
3. **Permite archivado, sustituido y finalizado.** Los tres estados **como tres**,
   no como «no vigente» a secas: `M3` y `M4` necesitan saber *cuál*.

POR QUÉ NO SE TOCA `metrics.py`
===============================

Porque produjo las cifras publicadas de `v0.1` y `v0.2`, y el §8.1 prohíbe
cambiar la medición después de observarla. Esta comprobación vive aparte y se
publica aparte, igual que la readjudicación.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]
#: La `v0.1` midio el marcado ANTES de corregirlo y dejo `M2.3` en rojo; esta
#: mide el mismo marcado DESPUES. Las dos conviven: sobrescribir la primera
#: habria borrado la prueba de que el defecto existia.
SALIDA: Final = "artifacts/adr002_round/marcado_de_m2_v0.2.json"
SALIDA_PREVIA: Final = "artifacts/adr002_round/marcado_de_m2_v0.1.json"

#: Lo que el canon **no** considera vigente, por cada eje del corpus. Sale del
#: corpus congelado, no de una lista escrita a mano aquí.
VALIDEZ_VIGENTE: Final = "VIGENTE"
DISPONIBILIDAD_DISPONIBLE: Final = "DISPONIBLE"

#: La marca que el motor publica cuando tiene el elemento por vigente.
MARCA_DE_VIGENTE: Final = "vigente"
MARCA_DE_NO_VIGENTE: Final = "no vigente"

#: Los tres estados que `M2` nombra, y que el canon distingue por dos ejes.
ESTADOS_QUE_M2_NOMBRA: Final[tuple[str, ...]] = ("archivado", "sustituido", "finalizado")

#: Disponibilidades que **no** son estados históricos: no es que el elemento sea
#: pasado, es que no debería poder recuperarse. Si aparecen, el defecto es de
#: contaminación —la puerta 1, que la ronda ya mide— y no del marcado de `M2`.
#: Nombrarlas aparte evita que un elemento purgado devuelto se cuente como un
#: fallo de marcado, que es un incumplimiento mucho más leve del que sería.
DISPONIBILIDAD_NO_RECUPERABLE: Final[frozenset[str]] = frozenset({"PURGADA", "NO_GUARDADA"})

CITA_DEL_CANON: Final = (
    "B04 M2 · Historico explicito: «Permite archivado, sustituido y finalizado con "
    "marcas temporales; separa tiempo valido de corte de registro y nunca lo presenta "
    "como actual»"
)


@dataclass(frozen=True, slots=True)
class EstadoCanonico:
    """Lo que el corpus declara de un elemento, por sus ejes."""

    identidad: str
    validez: str
    disponibilidad: str

    @property
    def es_vigente(self) -> bool:
        """Vigente es vigente **en los dos ejes**, no en uno.

        Un elemento `VIGENTE` pero `ARCHIVADA` no es actual: sigue siendo válido
        y ha dejado de estar disponible en los modos ordinarios. Colapsarlo en
        «vigente» sería presentarlo como actual, que es lo que `M2` prohíbe.
        """
        return self.validez == VALIDEZ_VIGENTE and self.disponibilidad == DISPONIBILIDAD_DISPONIBLE

    @property
    def es_recuperable(self) -> bool:
        """Lo purgado y lo no guardado no deberían volver **en ningún modo**."""
        return self.disponibilidad not in DISPONIBILIDAD_NO_RECUPERABLE

    @property
    def estado_que_m2_nombraria(self) -> str:
        """Cuál de los tres estados históricos es, si es alguno.

        Devuelve `no recuperable` para lo purgado y lo no guardado: llamarlos
        «vigente» —como hacía la primera versión— era falso por partida doble,
        porque ``es_vigente`` ya los daba por no vigentes y porque presentarlos
        como actuales es justo lo que se está comprobando que no pase.
        """
        if not self.es_recuperable:
            return "no recuperable"
        if self.disponibilidad == "ARCHIVADA":
            return "archivado"
        if self.validez == "SUSTITUIDA":
            return "sustituido"
        if self.validez == "SIN_SOPORTE":
            return "finalizado"
        return "vigente"


@dataclass(frozen=True, slots=True)
class Marca:
    """Lo que un participante publicó de un elemento que devolvió."""

    caso: str
    participante: str
    identidad: str
    estado_publicado: str
    tiempo_publicado: str


@dataclass(frozen=True, slots=True)
class Incumplimiento:
    """Un elemento no actual devuelto **como** actual. Lo grave."""

    caso: str
    participante: str
    identidad: str
    estado_canonico: str
    marca_recibida: str


def estados_canonicos(corpus: Mapping[str, Any]) -> dict[str, EstadoCanonico]:
    """Los ejes declarados por identidad canónica. Es el oráculo del marcado."""
    from experiments.adr002.projection import contracts as pc

    declarados: dict[str, EstadoCanonico] = {}
    for item in corpus["items"]:
        identidad = pc.referencia_canonica(str(item["id"]))
        if identidad is None:
            continue
        declarados[identidad] = EstadoCanonico(
            identidad=identidad,
            validez=str(item.get("validez") or VALIDEZ_VIGENTE),
            disponibilidad=str(item.get("disponibilidad") or DISPONIBILIDAD_DISPONIBLE),
        )
    return declarados


def presentado_como_actual(marca: Marca, canonico: EstadoCanonico) -> bool:
    """`M2.1`: lo que el canon no tiene por vigente vuelve **marcado**.

    Se comprueba en una sola dirección a propósito. Marcar «no vigente» algo que
    sí lo es sería otro defecto, pero **no es el que `M2` prohíbe**, y contarlos
    juntos haría que un candidato prudente de más pareciera incumplir la norma
    histórica.
    """
    return not canonico.es_vigente and marca.estado_publicado == MARCA_DE_VIGENTE


def separa_tiempo_valido_de_corte(marca: Marca) -> bool:
    """`M2.2`: las dos marcas temporales, y distinguibles."""
    tiempo = marca.tiempo_publicado
    return "aplicable a" in tiempo and "registrado" in tiempo


def distingue_los_tres_estados(marcas: Sequence[Marca]) -> tuple[bool, str]:
    """`M2.3`: archivado, sustituido y finalizado **como tres**.

    No se juzga por el diseño sino por lo publicado: si todas las marcas caen en
    dos valores, la salida no puede distinguir tres estados por muchos ejes que
    el motor lea por dentro. `M3` y `M4` necesitan saber **cuál**, y «no vigente»
    no se lo dice.
    """
    valores = {m.estado_publicado for m in marcas}
    distinguibles = valores - {MARCA_DE_VIGENTE}
    if len(distinguibles) >= len(ESTADOS_QUE_M2_NOMBRA):
        return True, f"la salida publica {len(distinguibles)} marcas de no vigencia"
    return False, (
        f"la salida publica {sorted(valores)}: {len(distinguibles)} marca(s) de no "
        f"vigencia para los {len(ESTADOS_QUE_M2_NOMBRA)} estados que M2 nombra "
        f"({', '.join(ESTADOS_QUE_M2_NOMBRA)}). Lo no vigente vuelve marcado, pero no "
        f"vuelve marcado CON QUE, y M3 y M4 necesitan saberlo"
    )


def incumplimientos(
    marcas: Sequence[Marca], canonicos: Mapping[str, EstadoCanonico]
) -> list[Incumplimiento]:
    """Los elementos no actuales devueltos como actuales."""
    fallos: list[Incumplimiento] = []
    for marca in marcas:
        canonico = canonicos.get(marca.identidad)
        if canonico is None or not presentado_como_actual(marca, canonico):
            continue
        fallos.append(
            Incumplimiento(
                caso=marca.caso,
                participante=marca.participante,
                identidad=marca.identidad,
                estado_canonico=canonico.estado_que_m2_nombraria,
                marca_recibida=marca.estado_publicado,
            )
        )
    return fallos


def documento(
    marcas_por_participante: Mapping[str, Sequence[Marca]],
    canonicos: Mapping[str, EstadoCanonico],
    sin_explicacion: Sequence[str],
) -> dict[str, Any]:
    """El artefacto. Publica las tres obligaciones por separado."""
    no_vigentes = {i: c for i, c in canonicos.items() if not c.es_vigente}
    por_participante: dict[str, Any] = {}
    for participante, marcas in marcas_por_participante.items():
        if participante in sin_explicacion:
            por_participante[participante] = {
                "medible": False,
                "razon": (
                    "no publica explicacion por resultado: sin marca que leer, M2 no "
                    "puede comprobarse. Es un incumplimiento declarado en su ficha, no "
                    "una carencia de esta medicion"
                ),
            }
            continue
        fallos = incumplimientos(marcas, canonicos)
        tres, razon_de_tres = distingue_los_tres_estados(marcas)
        sin_tiempo = [m.identidad for m in marcas if not separa_tiempo_valido_de_corte(m)]
        por_participante[participante] = {
            "medible": True,
            "resultados_observados": len(marcas),
            "no_vigentes_devueltos": sum(1 for m in marcas if m.identidad in no_vigentes),
            "estados_historicos_ejercitados": sorted(
                {
                    canonicos[m.identidad].estado_que_m2_nombraria
                    for m in marcas
                    if m.identidad in no_vigentes
                }
            ),
            "los_tres_estados_se_ejercitaron": {
                canonicos[m.identidad].estado_que_m2_nombraria
                for m in marcas
                if m.identidad in no_vigentes
            }
            >= set(ESTADOS_QUE_M2_NOMBRA),
            "por_que_importa_lo_anterior": (
                "sin ejercitar los tres estados, «nunca como actual» podria estar "
                "pasando por no haber devuelto ni un elemento no vigente, que es "
                "aprobar sin presentarse"
            ),
            "m2_1_nunca_como_actual": not fallos,
            "incumplimientos": [
                {
                    "caso": f.caso,
                    "identidad": f.identidad,
                    "estado_canonico": f.estado_canonico,
                    "marca_recibida": f.marca_recibida,
                }
                for f in fallos
            ],
            "m2_2_separa_tiempo_valido_de_corte": not sin_tiempo,
            "resultados_sin_las_dos_marcas": sorted(set(sin_tiempo)),
            "m2_3_distingue_los_tres_estados": tres,
            "razon_de_m2_3": razon_de_tres,
        }
    return {
        "documento": "Marcado de M2 en la ronda de ADR-002",
        "version_esquema": "marcado-m2-adr002-0.1",
        "estado": "EVIDENCIA",
        "mide_despues_de_la_correccion": (
            f"la lectura previa vive en {SALIDA_PREVIA} y dejo M2.3 en rojo para los "
            "cuatro; esta observa el mismo marcado despues de que trace.py publique "
            "cual de los tres estados historicos es cada elemento no vigente"
        ),
        "cita_del_canon": CITA_DEL_CANON,
        "por_que_faltaba": (
            "la readjudicacion lo dejo escrito como pendiente_de_medir: una obligacion "
            "canonica sin control. Cerrar ADR-002 sin ella seria cerrar sobre una "
            "puerta que nunca se abrio"
        ),
        "no_toca_nada_congelado": (
            "la marca ya la publica trace.Explicacion (estado y tiempo): esta medicion "
            "la LEE. No modifica candidatos ni capa comun, y no exige fichas sucesoras"
        ),
        "no_modifica_metrics": (
            "metrics.py produjo las cifras publicadas de v0.1 y v0.2 y no se toca: el "
            "§8.1 prohibe cambiar la medicion despues de observarla"
        ),
        "estados_no_vigentes_en_el_canon": {
            i: {
                "validez": c.validez,
                "disponibilidad": c.disponibilidad,
                "estado_que_m2_nombraria": c.estado_que_m2_nombraria,
            }
            for i, c in sorted(no_vigentes.items())
        },
        "por_participante": por_participante,
        "no_elige": (
            "esta medicion no elige alternativa: comprueba una obligacion del canon "
            "que ninguna metrica de la ronda comprobaba"
        ),
    }


__all__ = [
    "CITA_DEL_CANON",
    "ESTADOS_QUE_M2_NOMBRA",
    "MARCA_DE_NO_VIGENTE",
    "MARCA_DE_VIGENTE",
    "SALIDA",
    "EstadoCanonico",
    "Incumplimiento",
    "Marca",
    "distingue_los_tres_estados",
    "documento",
    "estados_canonicos",
    "incumplimientos",
    "presentado_como_actual",
    "separa_tiempo_valido_de_corte",
]
