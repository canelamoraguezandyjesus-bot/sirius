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

Por eso este arnes mide **cuatro corridas**:

1. la busqueda tal cual, que es la linea base publicada;
2. **mas la ampliacion**: las preguntas que el modelo escribe al guardar cada
   dato, indexadas junto a el. Esta es la mitad que **ensancha**;
3. **mas el filtro**: el modelo elige cuales de los candidatos responden de
   verdad. Esta es la mitad que **estrecha**;
4. **el filtro a solas**, sin la ampliacion.

La segunda sube la cobertura y **empeora** el ruido; la tercera tiene que
recuperar esa precision. Ninguna de las dos por separado cuenta la historia.

LA CUARTA CORRIDA, Y POR QUE SE ANADIO DESPUES
==============================================

La primera medicion —artefacto `resultado_modelo_local.json`, congelado— dejo
una pregunta sin responder que vale la mitad del coste del sistema: la corrida 2
salio en 23 aciertos exactos, **por debajo** de la linea base de 24, y la
ampliacion cuesta dos llamadas al modelo por dato guardado, ciento noventa y
cuatro para este canon. Con tres corridas no habia forma de saber si el filtro a
solas daria lo mismo, y por tanto si esa mitad cara sobra.

Anadir una corrida **no toca** la medida de las otras tres: el banco, las
metricas, el denominador y el listón preinscrito siguen siendo los mismos. El
§8.1 prohibe cambiar la medicion despues de ver los resultados; esto no la
cambia, la amplia, y las cifras de las corridas 1 a 3 se comparan con las
publicadas caso por caso.

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
) -> Corrida:
    corrida = Corrida(nombre)
    criticos = frozenset(contexto["criticos"])
    for caso in casos:
        recuperacion = engine.recuperar(caso.peticion, puerto, candidato, plano)
        ids = recuperacion.ids
        antes = ids
        filtrado: fl.Filtrado | None = None
        if filtrar_con is not None and ids:
            candidatos = [(i, textos.get(i, "")) for i in ids]
            comienzo = time.perf_counter()
            filtrado = fl.filtrar(caso.peticion.consulta, candidatos, filtrar_con)
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
    analizador.add_argument("--salida", type=Path, default=Path("resultado_modelo_local_v0.2.json"))
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

            print()
            print("=== 2. mas la ampliacion escrita al guardar (ENSANCHA) ===")
            ruta_ampliacion = Path(temporal) / "ampliacion.sqlite3"
            registro = construir_ampliacion(
                ruta_ampliacion,
                corpus["items"],
                criticos,
                proveedor,
                cota=argumentos.cota_ingesta,
            )
            candidato_ampliado = ConAmpliacion(ruta_ampliacion)
            ampliada = _correr(
                "2. mas ampliacion",
                casos,
                candidato_ampliado,
                puerto,
                plano,
                contexto,
                filtrar_con=None,
                textos=textos,
            )
            filas.append(_fila(ampliada, contexto))
            detalles["2. mas ampliacion"] = ampliada.detalles

            print()
            print("=== 3. mas el filtro que elige (ESTRECHA) ===")
            con_filtro = _correr(
                "3. mas filtro",
                casos,
                candidato_ampliado,
                puerto,
                plano,
                contexto,
                filtrar_con=proveedor,
                textos=textos,
            )
            filas.append(_fila(con_filtro, contexto))
            detalles["3. mas filtro"] = con_filtro.detalles

            # La corrida que faltaba. La ampliacion cuesta dos llamadas al
            # modelo por dato guardado —para este canon, ciento noventa y
            # cuatro— y la corrida 2 salio **por debajo** de la linea base en
            # aciertos exactos. Sin medir el filtro a solas no se sabe si esa
            # mitad cara aporta o si sobra, y esa pregunta vale la mitad del
            # coste del sistema entero.
            print()
            print("=== 4. el filtro SIN la ampliacion (¿se gana la mitad cara su sitio?) ===")
            solo_filtro = _correr(
                "4. solo filtro, sin ampliacion",
                casos,
                CandidatoA(),
                puerto,
                plano,
                contexto,
                filtrar_con=proveedor,
                textos=textos,
            )
            filas.append(_fila(solo_filtro, contexto))
            detalles["4. solo filtro, sin ampliacion"] = solo_filtro.detalles
        finally:
            puerto.close()
            plano.close()

    artefacto = {
        "que_es": (
            "medicion de las dos mitades del modelo local sobre el banco de ADR-002: "
            "la ampliacion que ensancha y el filtro que estrecha, en ese orden"
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
