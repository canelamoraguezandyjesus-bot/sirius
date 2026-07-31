"""Esquema y validador de la ficha de candidato (ADR002-TOL-210, paquete 09).

Se congela en la preinscripcion. No mide, no lee ficheros y no ejecuta nada al
importarse.

Lo que COMPRUEBA, sin aceptar ningun valor declarado sin contrastarlo:

- el **contenido minimo** de TOL-210, campo a campo;
- que ningun campo quede vacio ni diga «pendiente»;
- que la ficha **cite** el presupuesto de TOL-207 y el perfil de TOL-209 ya
  aprobados, en vez de proponer los suyos;
- que el coste local por etapa **explique** el total declarado, y que el coste
  externo **no** se sume al local;
- que las seis puertas previas comunes esten declaradas;
- que ningun objetivo supere a su propio limite duro.

Todos los conjuntos de campos estan **cerrados**: cualquier clave no prevista
es un fallo. Una ficha contiene limites, no resultados; cerrar el conjunto es
lo que impide colar una medicion del propio candidato bajo un nombre nuevo.

Falla cerrado y es **total por contrato**: nunca lanza.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final, TypeGuard

from experiments.adr002.cards import card_protocol as cp

VERSION_ESQUEMA: Final = cp.VERSION_ESQUEMA

_HEXADECIMAL: Final = frozenset("0123456789abcdef")


def _es_sha(valor: Any) -> bool:
    return isinstance(valor, str) and len(valor) == 40 and set(valor) <= _HEXADECIMAL


def _es_lista(valor: Any) -> TypeGuard[Sequence[Any]]:
    return isinstance(valor, Sequence) and not isinstance(valor, str | bytes)


def _campos_ajenos(objeto: Mapping[str, Any], admitidos: Sequence[str], etiqueta: str) -> list[str]:
    """Cierra un conjunto de campos.

    Una lista de campos exigidos no impide publicar nada: basta anadir uno.
    Lo que impide colar una medicion en una ficha de limites es cerrar el
    conjunto, de modo que cualquier clave no prevista sea un fallo con
    independencia de como se llame.
    """
    ajenos = sorted(set(objeto) - set(admitidos))
    if not ajenos:
        return []
    return [f"{etiqueta} declara campos ajenos al esquema: {ajenos}"]


def _faltan(objeto: Mapping[str, Any], exigidos: Sequence[str], etiqueta: str) -> list[str]:
    ausentes = [c for c in exigidos if c not in objeto]
    if not ausentes:
        return []
    return [f"{etiqueta} sin campos {ausentes}"]


def _declaraciones(objeto: Mapping[str, Any], campos: Sequence[str], etiqueta: str) -> list[str]:
    """Cada campo debe contener una declaracion, no un hueco."""
    return [
        f"{etiqueta}.{campo} debe declararse: un campo vacio o «pendiente» invalida la ficha"
        for campo in campos
        if not cp.es_declaracion(objeto.get(campo))
    ]


def _seccion(doc: Mapping[str, Any], nombre: str) -> Mapping[str, Any] | None:
    valor = doc.get(nombre)
    return valor if isinstance(valor, Mapping) else None


# --------------------------------------------------------------------------
# Identidad y congelacion
# --------------------------------------------------------------------------


def _fallos_identidad(doc: Mapping[str, Any]) -> list[str]:
    identidad = _seccion(doc, "identidad")
    if identidad is None:
        return ["identidad ausente o con forma invalida"]
    fallos = _faltan(identidad, cp.CAMPOS_IDENTIDAD, "identidad")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(identidad, cp.CAMPOS_IDENTIDAD, "identidad"))

    candidato = identidad["candidato"]
    if candidato not in cp.CANDIDATOS:
        fallos.append(
            f"identidad.candidato debe ser uno de {list(cp.CANDIDATOS)}: el universo de fichas "
            f"lo fijo la Resolucion de la particion de candidatos v1.0, y NO es T1-T4"
        )
    elif not cp.papel_coherente(str(candidato), str(identidad["papel"])):
        fallos.append(
            f"identidad.papel invalido para {candidato}: solo {cp.CONTROL} puede fichar como "
            f"{cp.PAPEL_CONTROL}; las alternativas minimas son {cp.PAPEL_CANDIDATO} y se "
            f"juzgan con las mismas puertas"
        )
    version = identidad["version"]
    if not cp.entero_no_negativo(version) or version < 1:
        fallos.append("identidad.version debe ser un entero mayor o igual que 1")
        return fallos

    anterior = identidad["sustituye_a"]
    motivo = identidad["motivo_de_sustitucion"]
    if version == 1:
        if anterior is not None:
            fallos.append("la primera version de una ficha no sustituye a ninguna")
        if motivo is not None:
            fallos.append("la primera version de una ficha no tiene motivo de sustitucion")
    else:
        if not cp.entero_no_negativo(anterior) or not cp.version_sucesora_valida(
            int(anterior), int(version)
        ):
            fallos.append(
                f"identidad.sustituye_a debe ser {int(version) - 1}: las versiones de ficha "
                f"crecen de una en una y nunca retroceden"
            )
        if not cp.es_declaracion(motivo):
            fallos.append(
                "una version sucesora debe declarar por que sustituye a la anterior: "
                "cambiarla obliga ademas a repetir las ejecuciones ya realizadas"
            )
    return fallos


def _fallos_congelacion(doc: Mapping[str, Any]) -> list[str]:
    congelacion = _seccion(doc, "congelacion")
    if congelacion is None:
        return ["congelacion ausente o con forma invalida"]
    fallos = _faltan(congelacion, cp.CAMPOS_CONGELACION, "congelacion")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(congelacion, cp.CAMPOS_CONGELACION, "congelacion"))
    if not _es_sha(congelacion["commit"]):
        fallos.append("congelacion.commit no tiene forma de SHA de commit")
    if not _es_sha(congelacion["huella"]):
        fallos.append("congelacion.huella no tiene forma de blob Git")
    if not cp.es_declaracion(congelacion["ruta"]):
        fallos.append("congelacion.ruta debe declarar donde vive la ficha en el repositorio")
    return fallos


# --------------------------------------------------------------------------
# Arquitectura, componentes y corpus
# --------------------------------------------------------------------------


def _fallos_arquitectura(doc: Mapping[str, Any]) -> list[str]:
    arq = _seccion(doc, "arquitectura")
    if arq is None:
        return ["arquitectura ausente o con forma invalida"]
    fallos = _faltan(arq, cp.CAMPOS_ARQUITECTURA, "arquitectura")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(arq, cp.CAMPOS_ARQUITECTURA, "arquitectura"))
    fallos.extend(
        _declaraciones(
            arq,
            (
                "definicion_canonica_que_asume",
                "sustrato_lexico",
                "materializacion_de_relaciones",
                "puerto_de_acceso",
            ),
            "arquitectura",
        )
    )
    # El control de falsacion no es una alternativa minima: T0 incumple RF-14
    # y no compite. Se ficha igual, pero no declara alternativa.
    identidad = _seccion(doc, "identidad")
    es_control = identidad is not None and identidad.get("candidato") == cp.CONTROL
    alternativa = arq["alternativa_minima"]
    if es_control:
        if alternativa is not None:
            fallos.append(
                f"arquitectura.alternativa_minima debe ser null para {cp.CONTROL}: el control "
                f"de falsacion no representa ninguna alternativa minima"
            )
    elif alternativa not in cp.ALTERNATIVAS:
        fallos.append(
            f"arquitectura.alternativa_minima debe ser una de {list(cp.ALTERNATIVAS)} (ARQ-00 §23)"
        )

    etapas = arq.get("etapas_implementadas")
    if not isinstance(etapas, Mapping):
        fallos.append("arquitectura.etapas_implementadas debe ser un mapa etapa -> declaracion")
    else:
        fallos.extend(_campos_ajenos(etapas, cp.ETAPAS, "arquitectura.etapas_implementadas"))
        fallos.extend(_declaraciones(etapas, cp.ETAPAS, "arquitectura.etapas_implementadas"))

    # Las puertas previas comunes no son ventaja de ningun candidato y
    # ninguno puede omitirlas: se exigen las seis, declaradas una a una.
    previas = arq.get("puertas_previas_comunes")
    if not isinstance(previas, Mapping):
        fallos.append("arquitectura.puertas_previas_comunes debe ser un mapa puerta -> declaracion")
    else:
        fallos.extend(
            _campos_ajenos(
                previas, cp.PUERTAS_PREVIAS_COMUNES, "arquitectura.puertas_previas_comunes"
            )
        )
        fallos.extend(
            _declaraciones(
                previas, cp.PUERTAS_PREVIAS_COMUNES, "arquitectura.puertas_previas_comunes"
            )
        )
    return fallos


def _fallos_senal_tardia(doc: Mapping[str, Any]) -> list[str]:
    """§2.2 bis: la senal tardia habilitada distingue a cada alternativa.

    La etapa E3 es obligatoria para TODAS, incluida ADR002-A. Una senal
    semantica vectorial **no** lo es: convertir una obligacion de
    comportamiento en una realizacion predeterminada es justo lo que
    B04-RF-31 prohibe.
    """
    senal = _seccion(doc, "senal_tardia")
    if senal is None:
        return ["senal_tardia ausente o con forma invalida"]
    fallos = _faltan(senal, cp.CAMPOS_SENAL_TARDIA, "senal_tardia")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(senal, cp.CAMPOS_SENAL_TARDIA, "senal_tardia"))
    fallos.extend(
        _declaraciones(
            senal,
            (
                "como_satisface_e3",
                "validacion_en_e3",
                "orden_de_las_etapas_tardias",
                "condicion_de_insuficiencia_por_transicion",
            ),
            "senal_tardia",
        )
    )
    arq = _seccion(doc, "arquitectura")
    alternativa = arq.get("alternativa_minima") if arq is not None else None
    identidad = _seccion(doc, "identidad")
    es_control = identidad is not None and identidad.get("candidato") == cp.CONTROL
    if es_control:
        if senal["habilitada"] is not None:
            fallos.append(
                f"senal_tardia.habilitada debe ser null para {cp.CONTROL}: el control no "
                f"habilita ninguna senal tardia porque no es una alternativa"
            )
    elif (
        isinstance(alternativa, str)
        and alternativa in cp.ALTERNATIVAS
        and not cp.senal_coherente(alternativa, str(senal["habilitada"]))
    ):
        fallos.append(
            f"senal_tardia.habilitada ({senal['habilitada']!r}) no es la de "
            f"{alternativa} ({cp.SENAL_POR_ALTERNATIVA[alternativa]!r}): una discrepancia "
            f"con la alternativa declarada invalida la ficha"
        )
    if senal["coherente_con_la_alternativa"] is not True:
        fallos.append("senal_tardia.coherente_con_la_alternativa debe ser True")
    return fallos


def _fallos_restriccion_d(doc: Mapping[str, Any]) -> list[str]:
    """§2.2 ter: ADR002-D no es B mas C.

    Sus tres restricciones son acumulativas y su anclaje es B04-D15, que
    prohibe adelantar espacios posteriores. Un D que coordine ambas senales a
    la vez incumple la puerta 9 aunque sus resultados sean perfectos.
    """
    bloque = _seccion(doc, "restriccion_d")
    if bloque is None:
        return ["restriccion_d ausente o con forma invalida"]
    fallos = _faltan(bloque, cp.CAMPOS_RESTRICCION_D, "restriccion_d")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(bloque, cp.CAMPOS_RESTRICCION_D, "restriccion_d"))

    arq = _seccion(doc, "arquitectura")
    alternativa = arq.get("alternativa_minima") if arq is not None else None
    aplica = bloque["aplica"]
    if not isinstance(aplica, bool):
        fallos.append("restriccion_d.aplica debe ser booleano")
        return fallos
    esperado = (
        cp.restriccion_d_aplicable(str(alternativa)) if isinstance(alternativa, str) else False
    )
    if aplica is not esperado:
        fallos.append(f"restriccion_d.aplica debe ser {esperado} para {alternativa}")
    exigidos = (
        "senales_en_etapas_distintas",
        "orden_predefinido",
        "sin_coordinacion_simultanea",
        "como_se_demuestra_en_cada_ejecucion",
        "traza_a_b04_d15",
    )
    if aplica:
        fallos.extend(_declaraciones(bloque, exigidos, "restriccion_d"))
        if bloque["motivo_de_no_aplicacion"] is not None:
            fallos.append("restriccion_d: si aplica, no se declara motivo de no aplicacion")
    else:
        if not cp.es_declaracion(bloque["motivo_de_no_aplicacion"]):
            fallos.append(
                "restriccion_d.motivo_de_no_aplicacion debe declararse cuando la alternativa "
                "no habilita dos senales tardias"
            )
        for campo in exigidos:
            if bloque[campo] is not None:
                fallos.append(f"restriccion_d.{campo} debe ser null cuando el bloque no aplica")
    return fallos


def _fallos_componentes(doc: Mapping[str, Any]) -> list[str]:
    componentes = doc.get("componentes")
    if not _es_lista(componentes):
        return ["componentes debe ser una lista"]
    if not componentes:
        return ["componentes vacia: al menos el motor de base debe declararse"]
    fallos: list[str] = []
    for indice, componente in enumerate(componentes):
        etiqueta = f"componentes[{indice}]"
        if not isinstance(componente, Mapping):
            fallos.append(f"{etiqueta} debe ser un objeto")
            continue
        faltan = _faltan(componente, cp.CAMPOS_COMPONENTE, etiqueta)
        if faltan:
            fallos.extend(faltan)
            continue
        fallos.extend(_campos_ajenos(componente, cp.CAMPOS_COMPONENTE, etiqueta))
        fallos.extend(
            _declaraciones(componente, ("papel", "nombre", "version", "origen"), etiqueta)
        )
        acopla = componente["acopla_a_proveedor"]
        if not isinstance(acopla, bool):
            fallos.append(f"{etiqueta}.acopla_a_proveedor debe ser booleano")
        elif acopla and not cp.es_declaracion(componente["ruta_de_sustitucion"]):
            # Puerta 6 de ADR-002 (RF-31): el acoplamiento a un proveedor o
            # formato no portable descarta si no hay ruta de sustitucion.
            fallos.append(
                f"{etiqueta} acopla a proveedor y no declara ruta de sustitucion: "
                f"la puerta 6 de ADR-002 (RF-31) descarta"
            )
    return fallos


def _fallos_corpus(doc: Mapping[str, Any]) -> list[str]:
    corpus = _seccion(doc, "corpus")
    if corpus is None:
        return ["corpus ausente o con forma invalida"]
    fallos = _faltan(corpus, cp.CAMPOS_CORPUS, "corpus")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(corpus, cp.CAMPOS_CORPUS, "corpus"))
    fallos.extend(
        _declaraciones(
            corpus, ("version", "longitud_media_y_distribucion", "head_de_esquema"), "corpus"
        )
    )
    for campo in ("mensajes", "recuerdos", "decisiones", "proyectos"):
        if not cp.entero_no_negativo(corpus[campo]):
            fallos.append(f"corpus.{campo} debe ser un entero no negativo")
    if not _es_sha(corpus["commit"]):
        fallos.append("corpus.commit no tiene forma de SHA de commit")

    # TOL-208 paso 3: rederivar la linea base sobre el mismo corpus, antes de
    # T1-T4. Una ficha que declare que no se rederivo debe decir por que, y
    # una que declare que si, citar la ejecucion.
    rederivada = corpus["t0_rederivada_sobre_este_corpus"]
    if not isinstance(rederivada, bool):
        fallos.append("corpus.t0_rederivada_sobre_este_corpus debe ser booleano")
    elif not cp.es_declaracion(corpus["referencia_de_la_rederivacion"]):
        fallos.append(
            "corpus.referencia_de_la_rederivacion debe citar la ejecucion de T0 sobre este "
            "corpus, o declarar por que todavia no existe"
        )
    return fallos


def _fallos_protocolo_aplicado(doc: Mapping[str, Any]) -> list[str]:
    aplicado = _seccion(doc, "protocolo_aplicado")
    if aplicado is None:
        return ["protocolo_aplicado ausente o con forma invalida"]
    fallos = _faltan(aplicado, cp.CAMPOS_PROTOCOLO_APLICADO, "protocolo_aplicado")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(aplicado, cp.CAMPOS_PROTOCOLO_APLICADO, "protocolo_aplicado"))
    if aplicado["protocolo"] != cp.PROTOCOLO:
        fallos.append(f"protocolo_aplicado.protocolo debe ser el aprobado ({cp.PROTOCOLO})")
    fallos.extend(
        _declaraciones(aplicado, ("desviaciones", "entorno", "semilla"), "protocolo_aplicado")
    )
    repeticiones = aplicado["repeticiones_por_magnitud"]
    if not cp.entero_no_negativo(repeticiones) or int(repeticiones) < cp.REPETICIONES_MINIMAS:
        fallos.append(
            f"protocolo_aplicado.repeticiones_por_magnitud debe ser al menos "
            f"{cp.REPETICIONES_MINIMAS} (§3.1 del protocolo)"
        )
    return fallos


# --------------------------------------------------------------------------
# Limites por magnitud
# --------------------------------------------------------------------------


def _fallos_sustrato(doc: Mapping[str, Any]) -> list[str]:
    sustrato = _seccion(doc, "sustrato_lexico")
    if sustrato is None:
        return ["sustrato_lexico ausente o con forma invalida"]
    fallos = _faltan(sustrato, cp.CAMPOS_SUSTRATO, "sustrato_lexico")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(sustrato, cp.CAMPOS_SUSTRATO, "sustrato_lexico"))

    es_fts5 = sustrato["es_el_fts5_medido"]
    if not isinstance(es_fts5, bool):
        fallos.append("sustrato_lexico.es_el_fts5_medido debe ser booleano")
        return fallos
    if not cp.es_declaracion(sustrato["motivo"]):
        fallos.append("sustrato_lexico.motivo debe declararse en ambos casos")

    magnitudes = sustrato["magnitudes"]
    if not _es_lista(magnitudes):
        fallos.append("sustrato_lexico.magnitudes debe ser una lista")
        return fallos
    if es_fts5:
        # Con el FTS5 medido rigen TOL-101L, TOL-104L y los tiempos de
        # TOL-105: el candidato no congela limites propios de sustrato.
        if magnitudes:
            fallos.append(
                "sustrato_lexico.magnitudes debe estar vacia cuando el sustrato es el FTS5 "
                "medido: rigen TOL-101L, TOL-104L y los tiempos de TOL-105"
            )
        return fallos
    if not magnitudes:
        fallos.append(
            "un sustrato lexico alternativo debe congelar sus propias magnitudes (TOL-101A)"
        )
    fallos.extend(_fallos_magnitudes(magnitudes, "sustrato_lexico.magnitudes"))
    return fallos


def _fallos_magnitudes(magnitudes: Sequence[Any], etiqueta: str) -> list[str]:
    fallos: list[str] = []
    for indice, magnitud in enumerate(magnitudes):
        marca = f"{etiqueta}[{indice}]"
        if not isinstance(magnitud, Mapping):
            fallos.append(f"{marca} debe ser un objeto")
            continue
        faltan = _faltan(magnitud, cp.CAMPOS_MAGNITUD_SUSTRATO, marca)
        if faltan:
            fallos.extend(faltan)
            continue
        fallos.extend(_campos_ajenos(magnitud, cp.CAMPOS_MAGNITUD_SUSTRATO, marca))
        fallos.extend(_declaraciones(magnitud, ("magnitud", "fundamento"), marca))
        objetivo, limite = magnitud["objetivo"], magnitud["limite_duro"]
        if not cp.entero_no_negativo(objetivo) or not cp.entero_no_negativo(limite):
            fallos.append(f"{marca}: objetivo y limite_duro deben ser enteros no negativos")
        elif not cp.objetivo_no_supera_al_limite(int(objetivo), int(limite)):
            fallos.append(f"{marca}: un objetivo por encima de su limite duro no es un objetivo")
    return fallos


def _fallos_indices(doc: Mapping[str, Any]) -> list[str]:
    indices = doc.get("indices_no_lexicos")
    if not _es_lista(indices):
        return ["indices_no_lexicos debe ser una lista, vacia si no hay ninguno"]
    fallos: list[str] = []
    for indice, entrada in enumerate(indices):
        etiqueta = f"indices_no_lexicos[{indice}]"
        if not isinstance(entrada, Mapping):
            fallos.append(f"{etiqueta} debe ser un objeto")
            continue
        faltan = _faltan(entrada, cp.CAMPOS_INDICE, etiqueta)
        if faltan:
            fallos.extend(faltan)
            continue
        fallos.extend(_campos_ajenos(entrada, cp.CAMPOS_INDICE, etiqueta))
        fallos.extend(
            _declaraciones(
                entrada,
                (
                    "nombre",
                    "tipo",
                    "datos_canonicos_que_cubre",
                    "estructura",
                    "precision",
                    "construccion_y_reconstruccion",
                    "comportamiento_de_borrado",
                ),
                etiqueta,
            )
        )
        for campo in ("numero_de_elementos", "bytes_totales", "bytes_por_elemento"):
            if not cp.entero_no_negativo(entrada[campo]):
                fallos.append(f"{etiqueta}.{campo} debe ser un entero no negativo")
        for campo in ("ratio_sobre_el_canon", "porcentaje_del_fichero"):
            if not cp.entero_no_negativo(entrada[campo]):
                fallos.append(f"{etiqueta}.{campo} debe expresarse en milesimas, entero")
        for campo in ("crecimiento_por_escala", "escala_comun", "limites_por_magnitud"):
            if not isinstance(entrada[campo], Mapping) or not entrada[campo]:
                fallos.append(f"{etiqueta}.{campo} debe ser un mapa no vacio")
    return fallos


def _fallos_ciclo(doc: Mapping[str, Any]) -> list[str]:
    ciclo = _seccion(doc, "ciclo_de_indice")
    if ciclo is None:
        return ["ciclo_de_indice ausente o con forma invalida"]
    fallos = _faltan(ciclo, cp.CAMPOS_CICLO, "ciclo_de_indice")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(ciclo, cp.CAMPOS_CICLO, "ciclo_de_indice"))
    fallos.extend(
        _declaraciones(
            ciclo,
            (
                "reconstruccion_desde_el_canon",
                "desaparicion_completa",
                "tasa_de_exito_del_cien_por_cien",
                "purga_fisica_sin_fragmento",
            ),
            "ciclo_de_indice",
        )
    )

    operaciones = ciclo["operaciones"]
    if not isinstance(operaciones, Mapping):
        fallos.append("ciclo_de_indice.operaciones debe ser un mapa operacion -> limites")
        return fallos
    fallos.extend(_campos_ajenos(operaciones, cp.OPERACIONES_CICLO, "ciclo_de_indice.operaciones"))
    for nombre in cp.OPERACIONES_CICLO:
        etiqueta = f"ciclo_de_indice.operaciones.{nombre}"
        operacion = operaciones.get(nombre)
        if not isinstance(operacion, Mapping):
            fallos.append(f"{etiqueta} ausente o con forma invalida")
            continue
        faltan = _faltan(operacion, cp.CAMPOS_OPERACION_CICLO, etiqueta)
        if faltan:
            fallos.extend(faltan)
            continue
        fallos.extend(_campos_ajenos(operacion, cp.CAMPOS_OPERACION_CICLO, etiqueta))
        if not cp.entero_no_negativo(operacion["limite"]):
            fallos.append(f"{etiqueta}.limite debe ser un entero no negativo")
        if not cp.es_declaracion(operacion["fundamento"]):
            fallos.append(f"{etiqueta}.fundamento debe declararse")
        fallos.extend(_fallos_no_ejecutabilidad(operacion, etiqueta))
    return fallos


def _fallos_no_ejecutabilidad(operacion: Mapping[str, Any], etiqueta: str) -> list[str]:
    """La no ejecutabilidad se declara ANTES, con fundamento, o no vale.

    Invocarla despues de ejecutar equivale a no haber declarado el limite, y
    el §3.6 del protocolo lo prohibe expresamente.
    """
    ejecutable = operacion["ejecutable_treinta_veces"]
    motivo = operacion["motivo_de_no_ejecutabilidad"]
    alternativa = operacion["evidencia_alternativa"]
    if not isinstance(ejecutable, bool):
        return [f"{etiqueta}.ejecutable_treinta_veces debe ser booleano"]
    if ejecutable:
        fallos = []
        if motivo is not None:
            fallos.append(f"{etiqueta}: una operacion ejecutable no declara motivo de exencion")
        if alternativa is not None:
            fallos.append(f"{etiqueta}: una operacion ejecutable no propone evidencia alternativa")
        return fallos
    fallos = []
    if not cp.es_declaracion(motivo):
        fallos.append(
            f"{etiqueta}: la no ejecutabilidad se declara con fundamento tecnico, antes de "
            f"ejecutar (§3.6 del protocolo)"
        )
    if not cp.es_declaracion(alternativa):
        fallos.append(
            f"{etiqueta}: una operacion no ejecutable debe proponer evidencia alternativa"
        )
    return fallos


# --------------------------------------------------------------------------
# Coste, extremo a extremo y almacenamiento
# --------------------------------------------------------------------------


def _fallos_coste(doc: Mapping[str, Any]) -> list[str]:
    coste = _seccion(doc, "coste_por_etapa")
    if coste is None:
        return ["coste_por_etapa ausente o con forma invalida"]
    fallos = _faltan(coste, cp.CAMPOS_COSTE, "coste_por_etapa")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(coste, cp.CAMPOS_COSTE, "coste_por_etapa"))

    etapas = coste["etapas"]
    if not _es_lista(etapas):
        fallos.append("coste_por_etapa.etapas debe ser una lista")
        return fallos
    if [e.get("etapa") if isinstance(e, Mapping) else None for e in etapas] != list(cp.ETAPAS):
        fallos.append(f"coste_por_etapa.etapas debe cubrir E0-E5 en orden: {list(cp.ETAPAS)}")
        return fallos

    for indice, etapa in enumerate(etapas):
        etiqueta = f"coste_por_etapa.etapas[{indice}]"
        faltan = _faltan(etapa, cp.CAMPOS_ETAPA, etiqueta)
        if faltan:
            fallos.extend(faltan)
            continue
        fallos.extend(_campos_ajenos(etapa, cp.CAMPOS_ETAPA, etiqueta))
        fallos.extend(
            _declaraciones(etapa, ("operaciones_locales", "coste_externo_declarado"), etiqueta)
        )
        objetivo = etapa["coste_local_objetivo_ns"]
        limite = etapa["coste_local_limite_ns"]
        if not cp.entero_no_negativo(objetivo) or not cp.entero_no_negativo(limite):
            fallos.append(f"{etiqueta}: los costes locales deben ser enteros de nanosegundos")
        elif not cp.objetivo_no_supera_al_limite(int(objetivo), int(limite)):
            fallos.append(f"{etiqueta}: el objetivo local supera su propio limite duro")

    total = coste["coste_local_total_ns"]
    if not cp.entero_no_negativo(total):
        fallos.append("coste_por_etapa.coste_local_total_ns debe ser un entero de nanosegundos")
    elif not cp.coste_local_coherente(etapas, int(total)):
        # Regla de coherencia del §2.9: una discrepancia no explicada
        # invalida ambas declaraciones.
        fallos.append(
            "coste_por_etapa: la suma de los limites locales por etapa no explica el total "
            "declarado; una discrepancia no explicada invalida ambas declaraciones"
        )
    if not cp.es_declaracion(coste["coste_de_la_senal_de_consulta"]):
        fallos.append("coste_por_etapa.coste_de_la_senal_de_consulta debe declararse (TOL-202)")
    # El coste externo se declara aparte y NUNCA se suma al local: por eso es
    # texto y no un entero que pudiera entrar en la aritmetica.
    if not cp.es_declaracion(coste["coste_externo_total"]):
        fallos.append(
            "coste_por_etapa.coste_externo_total debe declararse aparte, en texto: TOL-202 "
            "prohibe sumarlo al coste local"
        )
    if not cp.entero_no_negativo(coste["coste_extremo_a_extremo_ns"]):
        fallos.append("coste_por_etapa.coste_extremo_a_extremo_ns debe ser un entero")
    return fallos


def _fallos_extremo(doc: Mapping[str, Any]) -> list[str]:
    extremo = _seccion(doc, "extremo_a_extremo")
    if extremo is None:
        return ["extremo_a_extremo ausente o con forma invalida"]
    fallos = _faltan(extremo, cp.CAMPOS_EXTREMO, "extremo_a_extremo")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(extremo, cp.CAMPOS_EXTREMO, "extremo_a_extremo"))
    fallos.extend(_declaraciones(extremo, ("percentil_y_n", "fundamento"), "extremo_a_extremo"))

    objetivo, limite = extremo["objetivo_p95_ns"], extremo["limite_duro_p99_ns"]
    if not cp.entero_no_negativo(objetivo) or not cp.entero_no_negativo(limite):
        fallos.append("extremo_a_extremo: objetivo y limite duro deben ser enteros")
    elif not cp.objetivo_no_supera_al_limite(int(objetivo), int(limite)):
        fallos.append("extremo_a_extremo: el objetivo P95 supera al limite duro P99")

    # Dos prohibiciones expresas del §2.10 de la plantilla, hechas campo.
    for campo, mensaje in (
        (
            "no_deriva_de_tol_102b",
            "estos valores no pueden derivarse de TOL-102B ni de un «techo razonable» "
            "inspirado en T0",
        ),
        (
            "no_invoca_el_barrido_de_t0",
            "ningun candidato puede invocar el barrido prohibido de T0 como justificacion "
            "de un coste alto propio",
        ),
    ):
        if extremo[campo] is not True:
            fallos.append(f"extremo_a_extremo.{campo} debe ser True: {mensaje}")

    coste = _seccion(doc, "coste_por_etapa")
    if (
        coste is not None
        and cp.entero_no_negativo(coste.get("coste_extremo_a_extremo_ns"))
        and coste["coste_extremo_a_extremo_ns"] != limite
    ):
        fallos.append(
            "el coste extremo a extremo del §2.9 no coincide con el limite duro del §2.10: "
            "la suma por etapas debe explicar el extremo a extremo declarado"
        )
    return fallos


def _fallos_almacenamiento(doc: Mapping[str, Any]) -> list[str]:
    almacenamiento = _seccion(doc, "almacenamiento")
    if almacenamiento is None:
        return ["almacenamiento ausente o con forma invalida"]
    fallos = _faltan(almacenamiento, cp.CAMPOS_ALMACENAMIENTO, "almacenamiento")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(almacenamiento, cp.CAMPOS_ALMACENAMIENTO, "almacenamiento"))

    # El presupuesto lo fijo el acta de TOL-207. La ficha lo CITA.
    if almacenamiento["presupuesto_absoluto_b"] != cp.PRESUPUESTO_TOL207_B:
        fallos.append(
            f"almacenamiento.presupuesto_absoluto_b debe citar el aprobado por TOL-207 "
            f"({cp.PRESUPUESTO_TOL207_B})"
        )
    consumo = almacenamiento["consumo_declarado_b"]
    proyeccion = almacenamiento["proyeccion_50000_b"]
    if not cp.entero_no_negativo(consumo) or not cp.entero_no_negativo(proyeccion):
        fallos.append("almacenamiento: consumo y proyeccion deben ser enteros de bytes")
        return fallos

    cabe = cp.cabe_en_el_presupuesto(int(consumo), cp.PRESUPUESTO_TOL207_B)
    if almacenamiento["cabe"] is not cabe:
        fallos.append(
            f"almacenamiento.cabe no recomputa: con {consumo} B sobre "
            f"{cp.PRESUPUESTO_TOL207_B} B deberia ser {cabe}"
        )
    esperado = cp.por_mil(int(consumo), cp.PRESUPUESTO_TOL207_B)
    if almacenamiento["porcentaje_por_mil"] != esperado:
        fallos.append(f"almacenamiento.porcentaje_por_mil no recomputa: deberia ser {esperado}")
    return fallos


# --------------------------------------------------------------------------
# Estabilidad, banda temporal, purga y huella
# --------------------------------------------------------------------------


def _fallos_estabilidad(doc: Mapping[str, Any]) -> list[str]:
    estabilidad = _seccion(doc, "estabilidad")
    if estabilidad is None:
        return ["estabilidad ausente o con forma invalida"]
    fallos = _faltan(estabilidad, cp.CAMPOS_ESTABILIDAD, "estabilidad")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(estabilidad, cp.CAMPOS_ESTABILIDAD, "estabilidad"))
    fallos.extend(list(cp.estabilidad_conforme_al_perfil(estabilidad)))
    fallos.extend(
        _declaraciones(
            estabilidad,
            ("regimen_p50", "regimen_p95", "consulta_de_banda", "repeticion_unica_y_no_evaluable"),
            "estabilidad",
        )
    )
    return fallos


def _fallos_banda_temporal(doc: Mapping[str, Any]) -> list[str]:
    banda = _seccion(doc, "banda_temporal")
    if banda is None:
        return ["banda_temporal ausente o con forma invalida"]
    fallos = _faltan(banda, cp.CAMPOS_BANDA_TEMPORAL, "banda_temporal")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(banda, cp.CAMPOS_BANDA_TEMPORAL, "banda_temporal"))
    fallos.extend(
        _declaraciones(
            banda,
            (
                "equivalencia_externa",
                "fraccion_de_signo_pareada",
                "ausencia_de_separacion_material",
                "repeticion_en_sesion_independiente",
                "modelo_de_amenaza",
            ),
            "banda_temporal",
        )
    )
    # La indistinguibilidad de la linea base es en buena medida accidental: la
    # enmascara un barrido que RF-14 prohibe. No se hereda, y la ficha tiene
    # que reconocerlo por escrito.
    if banda["no_hereda_la_indistinguibilidad_de_la_linea_base"] is not True:
        fallos.append(
            "banda_temporal.no_hereda_la_indistinguibilidad_de_la_linea_base debe ser True: "
            "el enmascaramiento del barrido de T0 no se hereda"
        )
    return fallos


def _fallos_purga(doc: Mapping[str, Any]) -> list[str]:
    purga = _seccion(doc, "purga")
    if purga is None:
        return ["purga ausente o con forma invalida"]
    fallos = _faltan(purga, cp.CAMPOS_PURGA, "purga")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(purga, cp.CAMPOS_PURGA, "purga"))
    fallos.extend(
        _declaraciones(
            purga,
            (
                "secuencia",
                "payload_reversible_en_el_derivado",
                "modelo_de_amenaza",
                "comprobacion_propuesta",
            ),
            "purga",
        )
    )
    cubiertos = purga["ficheros_cubiertos"]
    if not _es_lista(cubiertos) or sorted(cubiertos) != sorted(cp.FICHEROS_DE_PURGA):
        fallos.append(
            f"purga.ficheros_cubiertos debe cubrir exactamente {list(cp.FICHEROS_DE_PURGA)}"
        )
    return fallos


def _fallos_huella(doc: Mapping[str, Any]) -> list[str]:
    huella = _seccion(doc, "huella_candidato")
    if huella is None:
        return ["huella_candidato ausente o con forma invalida"]
    fallos = _faltan(huella, cp.CAMPOS_HUELLA, "huella_candidato")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(huella, cp.CAMPOS_HUELLA, "huella_candidato"))
    if not _es_sha(huella["commit_del_prototipo"]):
        fallos.append("huella_candidato.commit_del_prototipo no tiene forma de SHA de commit")
    fallos.extend(
        _declaraciones(
            huella,
            (
                "hash_del_arbol_de_fuentes",
                "migraciones_o_ddl",
                "artefactos_y_su_hash",
                "reproduccion",
            ),
            "huella_candidato",
        )
    )
    return fallos


def _fallos_declaracion(doc: Mapping[str, Any]) -> list[str]:
    declaracion = _seccion(doc, "declaracion_de_congelacion")
    if declaracion is None:
        return ["declaracion_de_congelacion ausente o con forma invalida"]
    fallos = _faltan(declaracion, cp.CAMPOS_DECLARACION, "declaracion_de_congelacion")
    if fallos:
        return fallos
    fallos.extend(_campos_ajenos(declaracion, cp.CAMPOS_DECLARACION, "declaracion_de_congelacion"))
    fallos.extend(
        _declaraciones(declaracion, ("texto", "responsable", "fecha"), "declaracion_de_congelacion")
    )
    if declaracion["valores_anteriores_a_la_primera_ejecucion"] is not True:
        fallos.append(
            "declaracion_de_congelacion.valores_anteriores_a_la_primera_ejecucion debe ser "
            "True: un valor congelado tarde no es tolerancia, es justificacion a posteriori"
        )
    return fallos


# --------------------------------------------------------------------------
# Entrada publica
# --------------------------------------------------------------------------


def fallos_ficha(doc: Mapping[str, Any]) -> list[str]:
    """Valida una ficha completa. Lista vacia significa conforme.

    **Total por contrato: nunca lanza.**
    """
    try:
        return _fallos_ficha(doc)
    except Exception as exc:
        return [f"validacion abortada por ficha malformada: {type(exc).__name__}: {exc}"]


def _fallos_ficha(doc: Mapping[str, Any]) -> list[str]:
    if not isinstance(doc, Mapping):
        return ["la ficha debe ser un objeto JSON"]

    fallos = [f"falta la seccion obligatoria: {s}" for s in cp.SECCIONES if s not in doc]
    fallos.extend(_campos_ajenos(doc, cp.SECCIONES, "la ficha"))

    if not cp.es_declaracion(doc.get("documento")):
        fallos.append("la ficha debe declarar su titulo")
    if doc.get("version_esquema") != VERSION_ESQUEMA:
        fallos.append(f"version_esquema debe ser {VERSION_ESQUEMA}")
    if doc.get("estado") not in cp.ESTADOS:
        fallos.append(f"estado debe ser uno de {list(cp.ESTADOS)}")
    if doc.get("plantilla") != cp.PLANTILLA:
        fallos.append(f"la ficha debe declarar la plantilla vigente ({cp.PLANTILLA})")
    if doc.get("registro") != cp.REGISTRO:
        fallos.append(f"la ficha debe declarar el Registro vigente ({cp.REGISTRO})")
    if doc.get("protocolo") != cp.PROTOCOLO:
        fallos.append(f"la ficha debe declarar el protocolo vigente ({cp.PROTOCOLO})")
    actas = doc.get("actas_de_puerta")
    if not _es_lista(actas) or sorted(actas) != sorted((cp.ACTA_TOL_207, cp.ACTA_TOL_209)):
        fallos.append(
            f"actas_de_puerta debe citar exactamente las actas de puerta vigentes: "
            f"{sorted((cp.ACTA_TOL_207, cp.ACTA_TOL_209))}"
        )
    # Una ficha contiene limites y declaraciones, jamas mediciones del propio
    # candidato. Los conjuntos cerrados lo hacen cumplir; este campo lo
    # declara para que el incumplimiento sea legible, no solo detectable.
    if doc.get("no_contiene_resultados") is not True:
        fallos.append("no_contiene_resultados debe ser True: la ficha declara limites, no medidas")

    fallos.extend(_fallos_identidad(doc))
    fallos.extend(_fallos_congelacion(doc))
    fallos.extend(_fallos_arquitectura(doc))
    fallos.extend(_fallos_senal_tardia(doc))
    fallos.extend(_fallos_restriccion_d(doc))
    fallos.extend(_fallos_componentes(doc))
    fallos.extend(_fallos_corpus(doc))
    fallos.extend(_fallos_protocolo_aplicado(doc))
    fallos.extend(_fallos_sustrato(doc))
    fallos.extend(_fallos_indices(doc))
    fallos.extend(_fallos_ciclo(doc))
    fallos.extend(_fallos_coste(doc))
    fallos.extend(_fallos_extremo(doc))
    fallos.extend(_fallos_almacenamiento(doc))
    fallos.extend(_fallos_estabilidad(doc))
    fallos.extend(_fallos_banda_temporal(doc))
    fallos.extend(_fallos_purga(doc))
    fallos.extend(_fallos_huella(doc))
    fallos.extend(_fallos_declaracion(doc))

    return fallos
