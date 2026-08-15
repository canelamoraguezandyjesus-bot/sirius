"""Mide las dos mitades sobre el banco, y en el orden correcto.

    python -m experiments.adr002.modelo_local.medir

POR QUE PRIMERO ENSANCHAR Y DESPUES ESTRECHAR
=============================================

Medido sobre el banco antes de escribir esto: la busqueda entrega una **mediana
de dos** candidatos por pregunta, y en 12 de 47 casos no entrega ninguno. Solo 6
de 47 llegan a diez.

Un filtro sobre una lista de dos elementos **no tiene margen para mejorar la
precision**: su unico efecto posible es perder aciertos. De modo que medir el
filtro contra la busqueda de hoy no mediria el filtro; mediria el vacio, y el
resultado —«no cambia nada»— seria indistinguible de «el modulo no sirve».

Por eso este arnes mide **tres corridas**:

1. la busqueda tal cual, que es la linea base publicada;
2. **el filtro que elige** cuales de los candidatos responden de verdad;
3. **la compuerta**, que solo dice si hay algo aprovechable y no elige.

Y la ampliacion al guardar, con ``--con-ampliacion``, **apagada por defecto**.

LO QUE DOS CORRIDAS ENSENARON, Y POR QUE ESTAS SON ESTAS
========================================================

La ampliacion —las preguntas que el modelo escribe al guardar cada dato— se
midio en `resultado_modelo_local.json` y en `..._v0.2.json`. Las dos veces salio
**por debajo** de la linea base en aciertos exactos, 23 y 22 contra 24, y la
segunda ademas triplico la basura. Cuesta dos llamadas al modelo por dato, 194
para este canon. La corrida que la aislaba —el filtro sin ella— dio exactamente
lo mismo que con ella: 29 y 29 aciertos, 17 y 17 omisiones criticas. **No
aporta**, y por eso deja de medirse por defecto. Sigue disponible entera para
quien quiera reproducir aquello.

Lo que la sustituye es la pregunta que la v0.2 dejo planteada. Separando los 47
casos en los que esperan contenido y los que esperan que no salga nada:

===========================  ==================  =================
corrida                      aciertos contenido  aciertos ausencia
===========================  ==================  =================
busqueda sola                16/31               8/16
el filtro que elige          17/31               12/16
===========================  ==================  =================

De los cinco aciertos que el filtro gana, **cuatro estan en decir «no tengo
eso»**. Elegir cuales aporta uno, y cuesta dieciseis elementos correctos y seis
omisiones criticas, porque trunca las respuestas largas —cuatro de cinco
restricciones en `N1-44`, siete de diez en `N1-34`—.

La compuerta se queda con lo que funciona y **no puede** hacer lo que rompe: no
decide elemento a elemento, de modo que o entrega la lista entera o no entrega
nada. Sobre las decisiones reales de la v0.2 eso daria 27/47 con las **once**
omisiones criticas de la linea base, contra 29/47 con diecisiete.

Esto no cambia la medicion: el banco, las metricas, el denominador y el listón
preinscrito son los mismos, y la linea base se comprueba contra la publicada en
cada corrida. Cambia **que configuraciones se ponen a prueba**, que es lo que un
resultado debe cambiar.

QUE SE GUARDA DE CADA CASO, Y POR QUE HIZO FALTA
================================================

La version anterior solo publicaba totales, y con totales **no se puede
diagnosticar**. Cuando la corrida dijo que el filtro perdia trece elementos
correctos y una critica mas que la busqueda sin filtrar, hubo que averiguar
cuales leyendo el banco a mano. La causa resulto ser una regla mal escrita en la
instruccion del filtro —esta contada en `filtro.py`— y se encontro por lectura,
no por medida, que es exactamente lo que un arnes debe evitar.

Ahora cada corrida guarda, por caso, que entro al filtro, que se quito, y cuanto
de lo quitado era correcto o critico. Se calcula al terminar y **no vuelve al
modelo**: ninguna instruccion ve nada de esto.

QUE SE PUBLICA, Y POR QUE MAS DE LA CUENTA
==========================================

Tres cosas que un recuento ingenuo esconderia:

* **Cuantas veces el filtro actuo de verdad.** Falla abierto por diseno: si el
  servidor va lento, devuelve todo y la cifra sale igual que si hubiera sido
  prudente. Sin este contador, «filtro cuidadoso» y «filtro apagado» son
  indistinguibles.
* **Los casos de ausencia.** De los 47 adjudicables, **16 esperan que no salga
  nada**. Un arnes que solo mirase «lo esperado esta dentro» no puede puntuar un
  tercio del banco.
* **Cual de los dos 47.** El banco contiene dos recuentos distintos que valen
  47. Aqui el denominador es **el operativo**: 50 casos ejecutables menos 3 no
  adjudicables, que es lo que fija `round/cases.py`. Se declara para que nadie
  compare cifras de denominadores distintos.

Y la latencia, que `round/metrics.py` declara expresamente fuera de su alcance
—«la latencia es otro eje y vive en el ejecutor»—, se mide **aqui**, que es el
ejecutor, con mediana y percentil 95.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import subprocess
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.candidates.adr002_a.candidate import CandidatoA
from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.contracts import Candidata, ContextoDeEtapa, Etapa
from experiments.adr002.candidates.common.port import PuertoSqlite
from experiments.adr002.modelo_local import filtro as fl
from experiments.adr002.modelo_local import ingesta as ing
from experiments.adr002.modelo_local.puerto import ProveedorIA, ProveedorOllama
from experiments.adr002.projection import build
from experiments.adr002.projection import contracts as pc
from experiments.adr002.projection.contracts import Plano
from experiments.adr002.projection.plane import PlanoReservado
from experiments.adr002.round import cases as cs
from experiments.adr002.round import metrics as mt
from experiments.adr002.round import participants as pt
from experiments.adr002.round.execute_round import _criticos_del_canon

#: Las cifras publicadas de la linea base. Si la corrida no las reproduce, el
#: entorno cambio y la comparacion no vale: se comprueba, no se supone.
BASE_PUBLICADA: Final = {"exactos": 24, "omisiones": 11, "contaminacion": 3}

#: Palabras que nombran la categoria de un elemento critico. Vienen del **canon**
#: —quien sabe si un dato es critico es el canon, no el modelo— y por eso
#: sobreviven aunque el modelo no responda. Fijadas antes de medir.
VOCABULARIO_DE_CATEGORIA: Final[tuple[str, ...]] = (
    "esencial",
    "restriccion",
    "critica",
    "obligatoria",
    "imprescindible",
)

_DDL_AMPLIACION: Final = (
    "CREATE VIRTUAL TABLE ampliacion_fts USING fts5(identidad UNINDEXED, contenido)"
)


@dataclass(slots=True)
class Corrida:
    """Lo observado en una corrida entera. Descriptivo: no juzga."""

    nombre: str
    veredictos: list[Any] = field(default_factory=list)
    latencias: list[float] = field(default_factory=list)
    filtro_actuo: int = 0
    filtro_fallo_abierto: int = 0
    razones_de_fallo: list[str] = field(default_factory=list)
    #: Una entrada por caso. Sin esto, el artefacto solo trae totales y **no se
    #: puede saber que quito el filtro**: la corrida v0.1 dijo que perdia trece
    #: elementos correctos y hubo que deducir cuales leyendo el banco a mano.
    detalles: list[dict[str, Any]] = field(default_factory=list)


class ConAmpliacion(CandidatoA):
    """`ADR002-A` mas las preguntas escritas al guardar, buscadas en `E1`.

    Consulta un indice **aparte** y materializa por identidad a traves del
    puerto canonico: no enumera el canon, no lee texto de fuera del puerto y no
    toca el indice medido. La ampliacion es un derivado, y se comporta como tal.
    """

    def __init__(self, ruta_ampliacion: Path) -> None:
        super().__init__()
        self._ruta = ruta_ampliacion

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        base = list(super().candidatas(contexto))
        if contexto.etapa is not Etapa.E1:
            return base
        terminos = lexical.terminos_significativos(contexto.peticion.consulta)[:16]
        if not terminos:
            return base
        consulta = " OR ".join(f'"{t}"' for t in terminos)
        conexion = sqlite3.connect(f"file:{self._ruta}?mode=ro", uri=True)
        try:
            filas = conexion.execute(
                "SELECT identidad FROM ampliacion_fts WHERE ampliacion_fts MATCH ? LIMIT 64",
                (consulta,),
            ).fetchall()
        except sqlite3.OperationalError:
            filas = []
        finally:
            conexion.close()

        ya = set(contexto.ya_recuperados) | {c.item.id for c in base}
        nuevas = [str(f[0]) for f in filas if str(f[0]) not in ya]
        if not nuevas:
            return base
        extra: list[Candidata] = []
        for lote in [nuevas[i : i + 16] for i in range(0, len(nuevas), 16)]:
            for item in contexto.puerto.por_identificadores(tuple(lote)).items:
                extra.append(
                    Candidata(
                        item=item,
                        etapa=Etapa.E1,
                        lectura=self.leer(item, contexto.peticion.consulta),
                        razon="responde a una pregunta escrita al guardarlo",
                        senal="ampliacion generada en la ingesta",
                    )
                )
        return [*base, *extra]


def construir_ampliacion(
    ruta: Path, items: Sequence[Any], criticos: Any, proveedor: ProveedorIA, *, cota: int
) -> dict[str, Any]:
    """Genera las preguntas de cada elemento y las indexa. Devuelve el registro.

    El registro no es adorno: guarda **con que modelo y que pesos** se genero
    cada ampliacion, que es lo que `TOL-207` necesita para poder regenerarla.
    """
    conexion = sqlite3.connect(str(ruta))
    conexion.execute(_DDL_AMPLIACION)
    registro: dict[str, Any] = {"por_identidad": {}, "sin_generar": [], "procedencia": {}}
    for numero, item in enumerate(items[:cota], start=1):
        identidad = pc.referencia_canonica(str(item["id"]))
        if identidad is None:
            continue
        categoria = VOCABULARIO_DE_CATEGORIA if identidad in criticos else ()
        generado = ing.preguntas_que_responde(
            str(item["text"]), proveedor, vocabulario_de_categoria=categoria
        )
        contenido = generado.texto_para_indexar
        if contenido:
            conexion.execute(
                "INSERT INTO ampliacion_fts (identidad, contenido) VALUES (?, ?)",
                (identidad, contenido),
            )
        registro["por_identidad"][identidad] = {
            "preguntas": list(generado.preguntas),
            "categoria": list(generado.vocabulario_de_categoria),
            "descartadas": list(generado.aportes_descartados),
        }
        if generado.razon:
            registro["sin_generar"].append({"identidad": identidad, "razon": generado.razon})
        if generado.info_modelo is not None and not registro["procedencia"]:
            registro["procedencia"] = generado.procedencia
        if numero % 10 == 0:
            print(f"    ampliados {numero}/{min(len(items), cota)}...", flush=True)
    conexion.commit()
    conexion.close()
    return registro


def _fila(corrida: Corrida, contexto: dict[str, Any]) -> dict[str, Any]:
    resumen = mt.resumir(corrida.nombre, corrida.veredictos, borrado_y_regeneracion=True)
    adjudicables = [v for v in corrida.veredictos if v.adjudicable]
    con_contenido = [v for v in adjudicables if v.esperado]
    de_ausencia = [v for v in adjudicables if not v.esperado]
    cubiertos = sum(1 for v in con_contenido if set(v.esperado) <= set(v.obtenido))
    esperados = sum(len(v.esperado) for v in con_contenido)
    hallados = sum(len(set(v.esperado) & set(v.obtenido)) for v in con_contenido)
    sobrantes = sum(len(set(v.obtenido) - set(v.esperado)) for v in con_contenido)
    latencias = sorted(corrida.latencias)
    fila = {
        "corrida": corrida.nombre,
        "casos_adjudicables": len(adjudicables),
        "casos_con_contenido": len(con_contenido),
        "casos_de_ausencia": len(de_ausencia),
        "conjunto_exacto": resumen.casos_con_resultado_exacto,
        "lo_correcto_entra_entero": cubiertos,
        "elementos_hallados": f"{hallados}/{esperados}",
        "elementos_de_mas": sobrantes,
        "omisiones_criticas": resumen.criticos_pendientes_total,
        "contaminacion": resumen.contaminacion_total,
        "fuga_de_ambito": resumen.fuga_de_ambito_total,
        "ausencia_correcta": sum(1 for v in adjudicables if v.ausencia_correcta),
        "filtro_actuo": corrida.filtro_actuo,
        "filtro_fallo_abierto": corrida.filtro_fallo_abierto,
        # El dano del filtro, en la misma fila que su beneficio. Publicar «la
        # basura baja de 29 a 5» sin publicar «y de paso se lleva N correctos»
        # seria contar media medida.
        "correctos_quitados": sum(len(d.get("quitados_correctos", ())) for d in corrida.detalles),
        "criticos_quitados": sum(len(d.get("quitados_criticos", ())) for d in corrida.detalles),
        "latencia_mediana_s": round(statistics.median(latencias), 2) if latencias else None,
        "latencia_p95_s": (
            round(latencias[min(len(latencias) - 1, int(len(latencias) * 0.95))], 2)
            if latencias
            else None
        ),
    }
    print(
        f"  {corrida.nombre:34} exacto={fila['conjunto_exacto']}/{fila['casos_adjudicables']}  "
        f"entra-entero={cubiertos}/{len(con_contenido)}  hallados={fila['elementos_hallados']}  "
        f"de-mas={sobrantes}  omis={fila['omisiones_criticas']}  "
        f"ausencia={fila['ausencia_correcta']}/{fila['casos_adjudicables']}"
    )
    if corrida.latencias:
        print(
            f"  {'':34} filtro actuo {corrida.filtro_actuo}, fallo abierto "
            f"{corrida.filtro_fallo_abierto}; latencia mediana "
            f"{fila['latencia_mediana_s']}s p95 {fila['latencia_p95_s']}s"
        )
        print(
            f"  {'':34} el filtro se llevo {fila['correctos_quitados']} correctos, "
            f"de ellos {fila['criticos_quitados']} criticos"
        )
    del contexto
    return fila


def _detalle(
    caso: Any,
    antes: Sequence[str],
    despues: Sequence[str],
    filtrado: Any | None,
    criticos: frozenset[str],
) -> dict[str, Any]:
    """Que paso en un caso, con **lo quitado separado en bueno y malo**.

    Es el instrumento que faltaba. Un total de «elementos hallados 51/81» dice
    que se perdieron treinta, pero no **cuales**, y sin eso no se puede
    distinguir un filtro que tira ruido de uno que tira respuestas. Aqui lo
    quitado se parte contra `resultado_esperado` y contra la lista de criticos
    del canon, que es exactamente lo que `B04-RF-24` protege.

    Se calcula **despues** de que el modelo haya decidido y no vuelve a el:
    nada de esto entra en ninguna instruccion.
    """
    esperado = frozenset(caso.resultado_esperado)
    quitados = [i for i in antes if i not in frozenset(despues)]
    detalle: dict[str, Any] = {
        "caso": caso.identificador,
        "consulta": caso.peticion.consulta,
        "esperado": list(caso.resultado_esperado),
        "obtenido": list(despues),
    }
    if filtrado is None:
        return detalle
    detalle |= {
        "entraron_al_filtro": list(antes),
        "quitados": quitados,
        "quitados_correctos": [i for i in quitados if i in esperado],
        "quitados_criticos": [i for i in quitados if i in criticos and i in esperado],
        "filtro_actuo": filtrado.actuo,
    }
    if filtrado.rescatados:
        # Lo que decidio el **codigo**, separado de lo que decidio el modelo.
        # Con estas dos claves, quien lea el artefacto puede recomputar exacto
        # que habria salido sin la regla, sin volver a encender el modelo.
        detalle["rescatados_por_la_regla"] = list(filtrado.rescatados)
        detalle["obtenido_sin_proteccion"] = list(filtrado.sin_proteccion)
    if filtrado.razon:
        detalle["razon"] = filtrado.razon
    return detalle


def _correr(
    nombre: str,
    casos: Sequence[Any],
    candidato: Any,
    puerto: Any,
    plano: Any,
    contexto: dict[str, Any],
    *,
    filtrar_con: ProveedorIA | None,
    textos: dict[str, str],
    modo: str = "elige",
) -> Corrida:
    corrida = Corrida(nombre)
    criticos = frozenset(contexto["criticos"])
    # Solo el que elige puede truncar una respuesta, y por eso solo el lleva la
    # regla. La compuerta no la necesita: o entrega la lista entera o no entrega
    # nada, de modo que no hay nada de lo que protegerla.
    protegidos = frozenset() if modo == "compuerta" else criticos
    for caso in casos:
        recuperacion = engine.recuperar(caso.peticion, puerto, candidato, plano)
        ids = recuperacion.ids
        antes = ids
        filtrado: fl.Filtrado | None = None
        if filtrar_con is not None and ids:
            candidatos = [(i, textos.get(i, "")) for i in ids]
            comienzo = time.perf_counter()
            filtrado = (
                fl.compuerta(caso.peticion.consulta, candidatos, filtrar_con)
                if modo == "compuerta"
                else fl.filtrar(
                    caso.peticion.consulta, candidatos, filtrar_con, criticos=protegidos
                )
            )
            corrida.latencias.append(time.perf_counter() - comienzo)
            if filtrado.actuo:
                corrida.filtro_actuo += 1
            else:
                corrida.filtro_fallo_abierto += 1
                corrida.razones_de_fallo.append(filtrado.razon)
            ids = filtrado.identidades
        corrida.detalles.append(_detalle(caso, antes, ids, filtrado, criticos))
        conforme, razon = mt.etapa_conforme(
            caso,
            tuple(p.etapa.value for p in recuperacion.traza.pasos),
            pt._etapa_de_resolucion(recuperacion),
        )
        corrida.veredictos.append(
            mt.VeredictoDeCaso(
                caso=caso.identificador,
                canonico=caso.canonico,
                adjudicable=caso.adjudicable,
                obtenido=ids,
                esperado=caso.resultado_esperado,
                contaminacion=mt.contaminacion(ids, caso),
                fuga_de_ambito=mt.fuga_de_ambito(ids, caso, contexto["proyectos"]),
                confusion_de_polaridad=mt.confusion_de_polaridad(
                    ids,
                    {r.item.id: r.lectura.polaridad for r in recuperacion.resultados},
                    contexto["polaridades"],
                ),
                polaridad_mal_leida=(),
                etapa_conforme=conforme,
                razon_de_etapa=razon,
                etapa_puntua=not caso.etapa_inconsistente,
                resultado_exacto=tuple(sorted(ids)) == tuple(sorted(caso.resultado_esperado)),
                declara_orden=caso.declara_orden,
                orden_exacto=caso.declara_orden and ids == caso.orden_esperado,
                ausencia_correcta=mt.ausencia_correcta(caso, ids, recuperacion.estado_externo),
                criticos_pendientes=mt.criticos_pendientes(caso, ids, contexto["criticos"]),
                explicaciones_completas=0,
                resultados_totales=len(ids),
                suficiencia=recuperacion.suficiencia.value,
                estado_externo=recuperacion.estado_externo,
                parada=recuperacion.parada.identificador,
                etapas_recorridas=tuple(p.etapa.value for p in recuperacion.traza.pasos),
            )
        )
    return corrida


def main() -> int:
    analizador = argparse.ArgumentParser(description="Mide ampliacion y filtro sobre el banco")
    analizador.add_argument("--modelo", default=None, help="etiqueta del modelo en Ollama")
    analizador.add_argument("--servidor", default=None)
    analizador.add_argument("--cota-ingesta", type=int, default=1000)
    analizador.add_argument(
        "--con-ampliacion",
        action="store_true",
        help=(
            "mide tambien la ampliacion al guardar. Apagada por defecto: medida dos "
            "veces, cuesta 194 llamadas al modelo y no mejora nada"
        ),
    )
    analizador.add_argument("--salida", type=Path, default=Path("resultado_modelo_local_v0.3.json"))
    analizador.add_argument(
        "--sobrescribir",
        action="store_true",
        help="permite pisar un artefacto que ya existe (por defecto, no)",
    )
    argumentos = analizador.parse_args()

    # Antes de medir, no despues: una corrida entera dura minutos de grafica, y
    # negarse a escribir al final seria tirar ese trabajo. Y negarse a pisar es
    # la regla del proyecto: los artefactos medidos se conservan, no se pisan.
    if argumentos.salida.exists() and not argumentos.sobrescribir:
        print(f"ERROR: «{argumentos.salida}» ya existe y no se pisa.")
        print("Usa --salida con otro nombre, o --sobrescribir si de verdad quieres pisarlo.")
        return 2

    extra: dict[str, Any] = {}
    if argumentos.modelo:
        extra["modelo"] = argumentos.modelo
    if argumentos.servidor:
        extra["servidor"] = argumentos.servidor
    proveedor = ProveedorOllama(**extra)

    cabeza = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip()
    print(f"=== medido sobre HEAD {cabeza} ===")
    try:
        info = proveedor.info_modelo()
        print(f"modelo: {info.completo}")
    except Exception as fallo:
        print(f"AVISO: no se pudo hablar con el modelo: {fallo}")
        print("La ampliacion saldra vacia y el filtro fallara abierto. Las cifras lo diran.")
        info = None

    casos = cs.casos_ejecutables(cs.cargar_artefactos())
    familia = build.cargar_familia()
    corpus = familia[cs.CORPUS]
    contexto = {
        "proyectos": pt.proyectos_del_canon(corpus),
        "polaridades": pt.polaridades_del_canon(corpus),
        "criticos": _criticos_del_canon(familia["applied_criticality_v0_1.json"]["valores"]),
    }
    criticos = set(contexto["criticos"])
    textos: dict[str, str] = {}
    for item in corpus["items"]:
        identidad = pc.referencia_canonica(str(item["id"]))
        if identidad:
            textos[identidad] = str(item["text"])

    filas: list[dict[str, Any]] = []
    detalles: dict[str, list[dict[str, Any]]] = {}
    with tempfile.TemporaryDirectory() as temporal:
        proyeccion = build.construir_desde_la_familia(Path(temporal) / "planos")
        puerto = PuertoSqlite(proyeccion.ruta_de_entrada(), proyeccion.ruta(Plano.EJES_P2))
        plano = PlanoReservado(proyeccion)
        try:
            print()
            print("=== 1. la busqueda tal cual (linea base publicada) ===")
            base = _correr(
                "1. busqueda tal cual",
                casos,
                CandidatoA(),
                puerto,
                plano,
                contexto,
                filtrar_con=None,
                textos=textos,
            )
            fila_base = _fila(base, contexto)
            filas.append(fila_base)
            detalles["1. busqueda tal cual"] = base.detalles
            desviado = {
                c: (fila_base[k], v)
                for c, k, v in (
                    ("exactos", "conjunto_exacto", BASE_PUBLICADA["exactos"]),
                    ("omisiones", "omisiones_criticas", BASE_PUBLICADA["omisiones"]),
                    ("contaminacion", "contaminacion", BASE_PUBLICADA["contaminacion"]),
                )
                if fila_base[k] != v
            }
            if desviado:
                print()
                print("  AVISO: la linea base NO reproduce la publicada:", desviado)

            registro: dict[str, Any] = {}
            if argumentos.con_ampliacion:
                print()
                print("=== la ampliacion escrita al guardar (medida dos veces: no aporta) ===")
                ruta_ampliacion = Path(temporal) / "ampliacion.sqlite3"
                registro = construir_ampliacion(
                    ruta_ampliacion,
                    corpus["items"],
                    criticos,
                    proveedor,
                    cota=argumentos.cota_ingesta,
                )
                ampliada = _correr(
                    "ampliacion (opcional)",
                    casos,
                    ConAmpliacion(ruta_ampliacion),
                    puerto,
                    plano,
                    contexto,
                    filtrar_con=None,
                    textos=textos,
                )
                filas.append(_fila(ampliada, contexto))
                detalles["ampliacion (opcional)"] = ampliada.detalles

            print()
            print("=== 2. el filtro que ELIGE, sin poder tirar una critica ===")
            elige = _correr(
                "2. el filtro que elige, criticas protegidas",
                casos,
                CandidatoA(),
                puerto,
                plano,
                contexto,
                filtrar_con=proveedor,
                textos=textos,
            )
            filas.append(_fila(elige, contexto))
            detalles["2. el filtro que elige, criticas protegidas"] = elige.detalles
            rescatadas = sum(len(d.get("rescatados_por_la_regla", ())) for d in elige.detalles)
            print(f"  {'':34} la regla devolvio {rescatadas} criticas que el modelo tiraba")

            # La compuerta. Medido sobre las decisiones reales de la v0.2: de
            # los cinco aciertos que el que elige gana sobre la linea base,
            # cuatro salen de casos donde lo correcto era no devolver nada, y
            # elegir cuales cuesta dieciseis elementos correctos y seis
            # criticos. Esta se queda con la pregunta que funciona y no puede
            # hacer la que rompe: no decide elemento a elemento, asi que no
            # puede truncar una respuesta larga.
            print()
            print("=== 3. la COMPUERTA: solo dice si hay algo, no elige ===")
            gate = _correr(
                "3. la compuerta (todo o nada)",
                casos,
                CandidatoA(),
                puerto,
                plano,
                contexto,
                filtrar_con=proveedor,
                textos=textos,
                modo="compuerta",
            )
            filas.append(_fila(gate, contexto))
            detalles["3. la compuerta (todo o nada)"] = gate.detalles
        finally:
            puerto.close()
            plano.close()

    artefacto = {
        "que_es": (
            "medicion del modelo local sobre el banco de ADR-002: la busqueda sola, "
            "el filtro que elige cuales responden, y la compuerta que solo dice si hay "
            "algo. La ampliacion al guardar sale aparte y solo si se pide"
        ),
        "commit": cabeza,
        "denominador": (
            "47 adjudicables = 50 casos ejecutables menos 3 no adjudicables, segun "
            "round/cases.py. El banco contiene otro recuento distinto que tambien vale 47"
        ),
        "procedencia_del_modelo": (
            {"proveedor": info.proveedor, "modelo": info.modelo, "huella": info.huella}
            if info
            else {}
        ),
        "vocabulario_de_categoria": list(VOCABULARIO_DE_CATEGORIA),
        "linea_base_publicada": BASE_PUBLICADA,
        "filas": filas,
        "detalle_por_caso": detalles,
        "ampliacion_generada": registro,
    }
    argumentos.salida.write_text(
        json.dumps(artefacto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print()
    print(f"resultados escritos en {argumentos.salida.resolve()}")
    print("incluye las preguntas que genero el modelo, para poder juzgarlas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
