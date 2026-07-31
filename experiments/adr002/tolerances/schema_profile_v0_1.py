"""Esquema y validador del perfil ``perfil_tolerancias_v0.1.json``.

Se congela en la preinscripcion. No mide, no lee ficheros y no ejecuta nada
al importarse.

Lo que RECOMPUTA, sin aceptar ningun valor declarado:

- ``D50(s)`` y ``D95(s)`` por separado, familia a familia;
- ``E50(s)`` y ``E95(s)``, y su monotonia y cobertura;
- el cruce ``U50 = 5 E50(s_k)``, su intervalo y la continuidad exacta;
- ``B50(M)`` y ``B95(M)`` en cada escalon;
- ``SM``;
- que ``P95`` **no** tenga umbral relativo;
- que toda magnitud del contraste con distinto numero de sesiones salga
  ``NO_COMPARABLE`` y **sin veredicto**, y que la que declare exactamente
  once **si** lo reciba y ese veredicto **recompute** desde `SM` y las curvas
  que el propio documento publica.

Todos los conjuntos de campos estan **cerrados**: cualquier clave no prevista
es un fallo. Una lista de nombres prohibidos se esquiva rebautizando; un
conjunto cerrado, no.

**Importante:** el validador NO recibe la fuente v0.3. Recomputa a partir de
las curvas que el propio perfil publica y comprueba su coherencia interna,
sus invariantes y sus reglas. La correspondencia con la fuente la garantiza
la custodia por blob, no este modulo.

Falla cerrado y es **total por contrato**: nunca lanza.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import Any, Final

from experiments.adr002.tolerances import envelope_protocol as ep
from experiments.adr002.tolerances import profile_protocol as pp

VERSION_ESQUEMA: Final = pp.VERSION_ESQUEMA

SECCIONES_OBLIGATORIAS: Final[tuple[str, ...]] = (
    "documento",
    "version_esquema",
    "estado",
    "acta",
    "protocolo",
    "registro",
    "paquete",
    "derivado_no_medido",
    "fuente",
    "metodo",
    "sesiones_exigidas",
    "sm_ns",
    "p50",
    "p95",
    "preinscripcion",
    "controles_internos",
    "contraste_no_comparable",
    "custodia",
    "no_autoriza",
)

CAMPOS_FUENTE: Final[tuple[str, ...]] = (
    "ruta",
    "blob",
    "commit",
    "sesiones",
    "escalera_ns",
    "familias",
    "nota",
)

CAMPOS_P50: Final[tuple[str, ...]] = (
    "objetivo_relativo",
    "factor_u",
    "m",
    "u50_ns",
    "b50_en_u50_ns",
    "indice_escalon_del_cruce",
    "escalon_del_cruce_ns",
    "intervalo_del_cruce_ns",
    "motivo_no_evaluable",
    "curva",
)

CAMPOS_P95: Final[tuple[str, ...]] = (
    "sin_umbral_relativo",
    "objetivo_relativo_aplicable",
    "rango_cubierto_ns",
    "curva",
)

CAMPOS_CURVA: Final[tuple[str, ...]] = (
    "escala_ns",
    "dispersion_ns",
    "envolvente_ns",
    "banda_ns",
    "razon_dispersion_por_mil",
    "razon_envolvente_por_mil",
)

CAMPOS_PREINSCRIPCION: Final[tuple[str, ...]] = (
    "commit_a",
    "head_en_derivacion",
    "blobs_preinscritos",
    "blobs_heredados",
    "blob_fuente",
    "blob_linea_base",
    "blobs_evidencias_anteriores",
    "blob_protocolo_anterior",
    "blob_registro_anterior",
)

CAMPOS_METODO_TEXTO: Final[tuple[str, ...]] = (
    "nombre",
    "p50",
    "p95",
    "envolvente",
    "consulta_de_banda",
    "sesiones",
    "continuidad",
    # La regla de agregacion decide el veredicto de la magnitud y no estaba
    # declarada: un consumidor del JSON no podia reconstruirla.
    "agregacion",
)

CAMPOS_METODO: Final[tuple[str, ...]] = (
    *CAMPOS_METODO_TEXTO,
    "hereda_de",
    "no_sustituye_evidencia",
)

CAMPOS_CUSTODIA: Final[tuple[str, ...]] = (
    "sha_a_es_ancestro",
    "diff_preinscritos_vacio",
    "evidencias_anteriores_intactas",
    "documentos_de_gobierno_intactos",
    "head",
)

CAMPOS_CONTRASTE_CABECERA: Final[tuple[str, ...]] = (
    "fuente",
    "sesiones",
    "sesiones_exigidas",
    "nota",
    "magnitudes",
)

NEGACIONES_OBLIGATORIAS: Final[tuple[str, ...]] = (
    "aprobacion_tol_209",
    "limite_duro_tol_107",
    "sustitucion_evidencias_anteriores",
    "medicion_nueva",
    "t0",
    "candidatos",
    "benchmark",
    "merge_pr_117",
)

CAMPOS_CONTRASTE: Final[tuple[str, ...]] = (
    "magnitud",
    "fuente",
    "sesiones",
    "sesiones_exigidas",
    "min_p50_ns",
    "max_p50_ns",
    "dispersion_p50_ns",
    "min_p95_ns",
    "max_p95_ns",
    "dispersion_p95_ns",
    "resultado",
    "motivo",
    "registro",
)

CAMPOS_CONTRASTE_BANDA: Final[tuple[str, ...]] = (
    "banda_p50_que_le_corresponderia_ns",
    "banda_p95_que_le_corresponderia_ns",
)

_HEXADECIMAL: Final = frozenset("0123456789abcdef")


def _fallos_campos_ajenos(
    objeto: Mapping[str, Any], admitidos: Sequence[str], etiqueta: str
) -> list[str]:
    """Cierra un conjunto de campos.

    Una lista de campos EXIGIDOS no impide publicar nada: basta rebautizar lo
    prohibido. Lo que hace cumplir una prohibicion es cerrar el conjunto, de
    modo que cualquier campo no previsto sea un fallo con independencia de
    como se llame.
    """
    ajenos = sorted(set(objeto) - set(admitidos))
    if not ajenos:
        return []
    return [f"{etiqueta} publica campos ajenos al esquema: {ajenos}"]


def _es_entero(valor: Any) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _entero_o_none(valor: Any) -> int | None:
    return valor if _es_entero(valor) else None


def _es_sha(valor: Any) -> bool:
    return isinstance(valor, str) and len(valor) == 40 and set(valor) <= _HEXADECIMAL


def _texto_no_vacio(valor: Any) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _fallos_secciones(doc: Mapping[str, Any]) -> list[str]:
    return [f"falta la seccion obligatoria: {s}" for s in SECCIONES_OBLIGATORIAS if s not in doc]


# --------------------------------------------------------------------------
# Curvas
# --------------------------------------------------------------------------


def _curva_valida(curva: Any, etiqueta: str, *, con_sostenibilidad: bool) -> list[str]:
    """Forma, cobertura de la escalera y coherencia interna de una curva."""
    if not isinstance(curva, Sequence) or isinstance(curva, str | bytes):
        return [f"{etiqueta}.curva ausente o con forma invalida"]
    if len(curva) != len(pp.ESCALERA_NS):
        return [
            f"{etiqueta}.curva tiene {len(curva)} escalones; la escalera tiene "
            f"{len(pp.ESCALERA_NS)}"
        ]
    fallos: list[str] = []
    for indice, fila in enumerate(curva):
        if not isinstance(fila, Mapping):
            fallos.append(f"{etiqueta}.curva[{indice}] debe ser un objeto")
            continue
        ausentes = [c for c in CAMPOS_CURVA if c not in fila]
        if ausentes:
            fallos.append(f"{etiqueta}.curva[{indice}] sin campos {ausentes}")
            continue
        fallos.extend(
            _fallos_campos_ajenos(
                fila, (*CAMPOS_CURVA, "sostenible"), f"{etiqueta}.curva[{indice}]"
            )
        )
        if con_sostenibilidad and "sostenible" not in fila:
            fallos.append(f"{etiqueta}.curva[{indice}] sin campo sostenible")
        if not con_sostenibilidad and "sostenible" in fila:
            fallos.append(
                f"{etiqueta}.curva[{indice}] publica sostenible: P95 no tiene umbral relativo"
            )
        if fila["escala_ns"] != pp.ESCALERA_NS[indice]:
            fallos.append(f"{etiqueta}.curva[{indice}] no corresponde a la escalera preinscrita")
            continue
        # Los tipos se validan ANTES de usarlos, y con su propia lista, para
        # que un fallo de otra fila no decida si esta se sigue examinando.
        problemas = [
            f"{etiqueta}.curva[{indice}].{campo} debe ser un entero no negativo"
            for campo in ("dispersion_ns", "envolvente_ns", "banda_ns")
            if not _es_entero(fila[campo]) or int(fila[campo]) < 0
        ]
        if problemas:
            fallos.extend(problemas)
            continue
        escala = int(fila["escala_ns"])
        dispersion, envuelta = int(fila["dispersion_ns"]), int(fila["envolvente_ns"])
        if fila["banda_ns"] != envuelta:
            fallos.append(f"{etiqueta}.curva[{indice}]: la banda debe ser la envolvente")
        if envuelta < dispersion:
            fallos.append(
                f"{etiqueta}.curva[{indice}]: la envolvente no cubre la dispersion medida"
            )
        if fila["razon_dispersion_por_mil"] != pp.razon_por_mil(dispersion, escala):
            fallos.append(f"{etiqueta}.curva[{indice}]: razon_dispersion_por_mil no recomputa")
        if fila["razon_envolvente_por_mil"] != pp.razon_por_mil(envuelta, escala):
            fallos.append(f"{etiqueta}.curva[{indice}]: razon_envolvente_por_mil no recomputa")
        if con_sostenibilidad and fila.get("sostenible") is not ep.sostenible_en_escalon(
            envuelta, escala
        ):
            fallos.append(f"{etiqueta}.curva[{indice}]: sostenible no recomputa")
    return fallos


def _envolvente_desde_curva(curva: Any) -> ep.Envolvente | None:
    """Reconstruye la envolvente tipada desde la curva publicada."""
    if not isinstance(curva, Sequence) or isinstance(curva, str | bytes):
        return None
    if len(curva) != len(pp.ESCALERA_NS):
        return None
    dispersiones: list[int] = []
    envolvente: list[int] = []
    for indice, fila in enumerate(curva):
        if not isinstance(fila, Mapping):
            return None
        if fila.get("escala_ns") != pp.ESCALERA_NS[indice]:
            return None
        d, e = _entero_o_none(fila.get("dispersion_ns")), _entero_o_none(fila.get("envolvente_ns"))
        if d is None or e is None:
            return None
        dispersiones.append(d)
        envolvente.append(e)
    return ep.Envolvente(dispersiones=tuple(dispersiones), envolvente=tuple(envolvente))


def _fallos_envolvente(envolvente: ep.Envolvente, etiqueta: str) -> list[str]:
    """Las tres propiedades vinculantes de una envolvente."""
    fallos: list[str] = []
    # La envolvente publicada tiene que ser el maximo acumulado de su propia
    # curva de dispersiones: no basta con que sea monotona.
    acumulado: list[int] = []
    peor = 0
    for valor in envolvente.dispersiones:
        peor = max(peor, valor)
        acumulado.append(peor)
    if tuple(acumulado) != envolvente.envolvente:
        fallos.append(f"{etiqueta}: la envolvente no es el maximo acumulado de su dispersion")
    if not envolvente.es_monotona():
        fallos.append(f"{etiqueta}: la envolvente no es monotona no decreciente")
    if not envolvente.cubre_el_suelo():
        fallos.append(f"{etiqueta}: la envolvente no cubre la dispersion en algun escalon")
    if not ep.banda_no_decreciente(envolvente):
        fallos.append(f"{etiqueta}: la banda se estrecha al crecer la magnitud (reabre M-03)")
    return fallos


# --------------------------------------------------------------------------
# P50: cruce y continuidad
# --------------------------------------------------------------------------


def _fallos_p50(doc: Mapping[str, Any]) -> list[str]:
    p50 = doc.get("p50")
    if not isinstance(p50, Mapping):
        return ["p50 ausente o con forma invalida"]

    fallos = [f"p50 sin campo {c}" for c in CAMPOS_P50 if c not in p50]
    if fallos:
        return fallos
    fallos.extend(_fallos_campos_ajenos(p50, CAMPOS_P50, "p50"))

    objetivo = f"{pp.OBJETIVO_RELATIVO_NUM}/{pp.OBJETIVO_RELATIVO_DEN}"
    if p50["objetivo_relativo"] != objetivo:
        fallos.append(f"p50.objetivo_relativo debe ser {objetivo}: no se elige en este paquete")
    if p50["factor_u"] != pp.FACTOR_U:
        fallos.append(f"p50.factor_u debe ser {pp.FACTOR_U}")
    if p50["m"] != pp.MARGEN_M:
        fallos.append(f"p50.m debe ser {pp.MARGEN_M}")

    fallos.extend(_curva_valida(p50["curva"], "p50", con_sostenibilidad=True))
    envolvente = _envolvente_desde_curva(p50["curva"])
    if envolvente is None:
        return [*fallos, "p50: la curva publicada no permite recomputar la envolvente"]
    fallos.extend(_fallos_envolvente(envolvente, "p50"))

    cruce = ep.resolver_cruce(envolvente)
    if p50["u50_ns"] != cruce.u:
        fallos.append(
            f"p50.u50_ns publicado {p50['u50_ns']!r} no coincide con el cruce recomputado "
            f"({cruce.u!r})"
        )
    if p50["b50_en_u50_ns"] != cruce.b_en_u:
        fallos.append("p50.b50_en_u50_ns no coincide con el recomputado")
    if p50["indice_escalon_del_cruce"] != cruce.indice_escalon:
        fallos.append("p50.indice_escalon_del_cruce no coincide con el recomputado")

    escalon = cruce.indice_escalon
    esperado_escalon = None if escalon is None else pp.ESCALERA_NS[escalon]
    if p50["escalon_del_cruce_ns"] != esperado_escalon:
        fallos.append("p50.escalon_del_cruce_ns no coincide con el recomputado")
    esperado_intervalo = (
        None
        if escalon is None
        else [0 if escalon == 0 else pp.ESCALERA_NS[escalon - 1], pp.ESCALERA_NS[escalon]]
    )
    if p50["intervalo_del_cruce_ns"] != esperado_intervalo:
        fallos.append("p50.intervalo_del_cruce_ns no coincide con el recomputado")

    if cruce.evaluable:
        u, banda = cruce.u, cruce.b_en_u
        assert u is not None and banda is not None
        if p50["motivo_no_evaluable"] is not None:
            fallos.append("p50.motivo_no_evaluable debe ser null con cruce resuelto")
        if not ep.continuidad_exacta(cruce):
            fallos.append("p50: la continuidad m*B50(U50) = 0,20 U50 no es exacta")
        if pp.FACTOR_U * banda != u:
            fallos.append(f"p50: U50 debe ser {pp.FACTOR_U} * B50(U50)")
        if esperado_intervalo is not None and not (
            esperado_intervalo[0] < u <= esperado_intervalo[1]
        ):
            fallos.append("p50: U50 fuera del intervalo de su escalon")
    else:
        if p50["u50_ns"] is not None or p50["b50_en_u50_ns"] is not None:
            fallos.append("p50: sin cruce no se pueden publicar U50 ni B50(U50)")
        if not _texto_no_vacio(p50["motivo_no_evaluable"]):
            fallos.append("p50: sin cruce se exige motivo explicito y no vacio")

    return fallos


# --------------------------------------------------------------------------
# P95: sin umbral relativo
# --------------------------------------------------------------------------


def _fallos_p95(doc: Mapping[str, Any]) -> list[str]:
    p95 = doc.get("p95")
    if not isinstance(p95, Mapping):
        return ["p95 ausente o con forma invalida"]

    fallos = [f"p95 sin campo {c}" for c in CAMPOS_P95 if c not in p95]
    if fallos:
        return fallos

    # La decision de gobierno es explicita: no se crea umbral relativo para
    # P95. Publicar uno seria reintroducir por la puerta de atras lo que la
    # separacion eliminó. Por eso el conjunto de campos se CIERRA: una lista
    # de nombres prohibidos se esquiva rebautizando el umbral.
    if p95["sin_umbral_relativo"] is not True:
        fallos.append("p95.sin_umbral_relativo debe ser True")
    if p95["objetivo_relativo_aplicable"] is not False:
        fallos.append("p95.objetivo_relativo_aplicable debe ser False")
    ajenos = sorted(set(p95) - set(CAMPOS_P95))
    if ajenos:
        fallos.append(
            f"p95 publica campos ajenos al esquema y por tanto no auditables: {ajenos}. "
            f"P95 no tiene umbral relativo bajo ningun nombre"
        )

    fallos.extend(_curva_valida(p95["curva"], "p95", con_sostenibilidad=False))
    envolvente = _envolvente_desde_curva(p95["curva"])
    if envolvente is None:
        return [*fallos, "p95: la curva publicada no permite recomputar la envolvente"]
    fallos.extend(_fallos_envolvente(envolvente, "p95"))

    rango = p95["rango_cubierto_ns"]
    sm = _entero_o_none(doc.get("sm_ns"))
    if (
        not isinstance(rango, Sequence)
        or isinstance(rango, str | bytes)
        or len(rango) != 2
        or not all(_es_entero(v) for v in rango)
    ):
        fallos.append("p95.rango_cubierto_ns debe ser un par de enteros")
    elif sm is not None and list(rango) != [sm, pp.ESCALERA_NS[-1]]:
        fallos.append(
            f"p95.rango_cubierto_ns debe ser [SM, {pp.ESCALERA_NS[-1]}] = "
            f"[{sm}, {pp.ESCALERA_NS[-1]}]"
        )

    return fallos


def _fallos_relacion_entre_percentiles(doc: Mapping[str, Any]) -> list[str]:
    """``E95(s) >= E50(s)`` en todo escalon: la cola no puede ser mas estable."""
    p50, p95 = doc.get("p50"), doc.get("p95")
    if not isinstance(p50, Mapping) or not isinstance(p95, Mapping):
        return []
    e50 = _envolvente_desde_curva(p50.get("curva"))
    e95 = _envolvente_desde_curva(p95.get("curva"))
    if e50 is None or e95 is None:
        return []
    if any(a > b for a, b in zip(e50.envolvente, e95.envolvente, strict=True)):
        return [
            "E95 queda por debajo de E50 en algun escalon: la cola no puede ser mas estable "
            "que el centro, y el perfil seria ilegible"
        ]
    return []


# --------------------------------------------------------------------------
# Contraste: la guarda de sesiones
# --------------------------------------------------------------------------


def _perfil_desde_documento(doc: Mapping[str, Any]) -> pp.Perfil | None:
    """Reconstruye el perfil tipado desde lo que el propio documento publica.

    Con ``SM`` y las dos curvas, el veredicto de cualquier magnitud del
    contraste es **recomputable** sin salir del documento. Devuelve ``None``
    solo si el documento no da para reconstruirlo; los fallos de forma los
    denuncian los validadores especificos.
    """
    sm = _entero_o_none(doc.get("sm_ns"))
    p50, p95 = doc.get("p50"), doc.get("p95")
    if sm is None or sm <= 0 or not isinstance(p50, Mapping) or not isinstance(p95, Mapping):
        return None
    e50 = _envolvente_desde_curva(p50.get("curva"))
    e95 = _envolvente_desde_curva(p95.get("curva"))
    if e50 is None or e95 is None:
        return None
    try:
        return pp.Perfil(
            sm_ns=sm,
            cruce_p50=ep.resolver_cruce(e50),
            envolvente_p95=e95,
            sesiones=pp.SESIONES_EXIGIDAS,
        )
    except ValueError, ArithmeticError:
        return None


def _fallos_entrada_comparable(
    entrada: Mapping[str, Any], etiqueta: str, perfil: pp.Perfil | None
) -> list[str]:
    """Una entrada con exactamente once sesiones SI recibe veredicto: se recomputa."""
    if perfil is None:
        return [
            f"{etiqueta}: declara {pp.SESIONES_EXIGIDAS} sesiones y el veredicto no es "
            f"recomputable desde el documento"
        ]
    minimos = [_entero_o_none(entrada[c]) for c in ("min_p50_ns", "max_p50_ns")]
    minimos += [_entero_o_none(entrada[c]) for c in ("min_p95_ns", "max_p95_ns")]
    if any(v is None for v in minimos):
        return []
    min50, max50, min95, max95 = (int(v) for v in minimos if v is not None)
    if min95 < min50:
        return []
    try:
        veredicto = pp.evaluar_magnitud(
            [min50, max50] + [min50] * (pp.SESIONES_EXIGIDAS - 2),
            [min95, max95] + [min95] * (pp.SESIONES_EXIGIDAS - 2),
            perfil=perfil,
        )
    except (ValueError, ArithmeticError) as exc:
        return [f"{etiqueta}: el veredicto no se pudo recomputar ({exc})"]
    fallos: list[str] = []
    if entrada["resultado"] != veredicto.resultado:
        fallos.append(
            f"{etiqueta}: veredicto publicado {entrada['resultado']!r} distinto del "
            f"recomputado {veredicto.resultado!r}"
        )
    if entrada["motivo"] is not None:
        fallos.append(f"{etiqueta}: con {pp.SESIONES_EXIGIDAS} sesiones no hay motivo de exclusion")
    if entrada["registro"] != pp.registro_por_percentil(veredicto):
        fallos.append(f"{etiqueta}: el registro por percentil no recomputa")
    return fallos


def _fallos_contraste(doc: Mapping[str, Any]) -> list[str]:
    contraste = doc.get("contraste_no_comparable")
    if not isinstance(contraste, Mapping):
        return ["contraste_no_comparable ausente o con forma invalida"]

    fallos: list[str] = _fallos_campos_ajenos(
        contraste, CAMPOS_CONTRASTE_CABECERA, "contraste_no_comparable"
    )
    if contraste.get("sesiones_exigidas") != pp.SESIONES_EXIGIDAS:
        fallos.append(f"el contraste debe declarar {pp.SESIONES_EXIGIDAS} sesiones exigidas")
    if not _texto_no_vacio(contraste.get("nota")):
        fallos.append("el contraste debe explicar por escrito por que no es comparable")
    cabecera_sesiones = _entero_o_none(contraste.get("sesiones"))
    if cabecera_sesiones is None:
        fallos.append("contraste_no_comparable.sesiones debe ser un entero")
    perfil = _perfil_desde_documento(doc)

    magnitudes = contraste.get("magnitudes")
    if not isinstance(magnitudes, Sequence) or isinstance(magnitudes, str | bytes):
        return [*fallos, "contraste_no_comparable.magnitudes debe ser una lista"]
    if not magnitudes:
        return [*fallos, "contraste_no_comparable.magnitudes vacia: la divulgacion es obligatoria"]

    for indice, entrada in enumerate(magnitudes):
        etiqueta = f"contraste_no_comparable.magnitudes[{indice}]"
        if not isinstance(entrada, Mapping):
            fallos.append(f"{etiqueta} debe ser un objeto")
            continue
        ausentes = [c for c in CAMPOS_CONTRASTE if c not in entrada]
        if ausentes:
            fallos.append(f"{etiqueta} sin campos {ausentes}")
            continue
        fallos.extend(
            _fallos_campos_ajenos(entrada, (*CAMPOS_CONTRASTE, *CAMPOS_CONTRASTE_BANDA), etiqueta)
        )
        if entrada["sesiones_exigidas"] != pp.SESIONES_EXIGIDAS:
            fallos.append(f"{etiqueta}: sesiones_exigidas debe ser {pp.SESIONES_EXIGIDAS}")
        sesiones = _entero_o_none(entrada["sesiones"])
        if sesiones is None:
            fallos.append(f"{etiqueta}: sesiones debe ser un entero")
            continue
        # El documento declara DOS veces el numero de sesiones de esta fuente:
        # en la cabecera de la seccion y en cada entrada. Se cruzan, porque la
        # coherencia interna es justo lo que este validador dice comprobar.
        if (
            cabecera_sesiones is not None
            and entrada["fuente"] == contraste.get("fuente")
            and sesiones != cabecera_sesiones
        ):
            fallos.append(
                f"{etiqueta}: declara {sesiones} sesiones y la cabecera de su misma fuente "
                f"declara {cabecera_sesiones}"
            )
        # ESTA es la regla 5 hecha ejecutable, en sus DOS direcciones: con un
        # numero distinto de once no hay veredicto, y con once el veredicto se
        # recomputa desde las bandas que el propio documento publica.
        if sesiones == pp.SESIONES_EXIGIDAS:
            fallos.extend(_fallos_entrada_comparable(entrada, etiqueta, perfil))
        else:
            if entrada["resultado"] != pp.NO_COMPARABLE:
                fallos.append(
                    f"{etiqueta}: {sesiones} sesiones frente a {pp.SESIONES_EXIGIDAS} exigidas, "
                    f"y aun asi se emitio el veredicto {entrada['resultado']!r}"
                )
            if entrada["motivo"] != pp.MOTIVO_SESIONES:
                fallos.append(f"{etiqueta}: el motivo debe ser {pp.MOTIVO_SESIONES}")
            if entrada["registro"] != pp.NO_COMPARABLE:
                fallos.append(f"{etiqueta}: el registro debe ser {pp.NO_COMPARABLE}")
            for campo in (
                "banda_p50_que_le_corresponderia_ns",
                "banda_p95_que_le_corresponderia_ns",
            ):
                if entrada.get(campo) is not None:
                    fallos.append(
                        f"{etiqueta}: no se publica banda para una magnitud no comparable"
                    )
        for campo, minimo, maximo in (
            ("p50", "min_p50_ns", "max_p50_ns"),
            ("p95", "min_p95_ns", "max_p95_ns"),
        ):
            mn, mx = _entero_o_none(entrada[minimo]), _entero_o_none(entrada[maximo])
            if mn is None or mx is None:
                fallos.append(f"{etiqueta}: los minimos y maximos de {campo} deben ser enteros")
                continue
            if mx < mn:
                fallos.append(f"{etiqueta}: maximo de {campo} por debajo del minimo")
            declarada = _entero_o_none(entrada[f"dispersion_{campo}_ns"])
            if declarada != mx - mn:
                fallos.append(f"{etiqueta}: dispersion de {campo} no recomputa")
        min50, min95 = _entero_o_none(entrada["min_p50_ns"]), _entero_o_none(entrada["min_p95_ns"])
        if min50 is not None and min95 is not None and min95 < min50:
            fallos.append(f"{etiqueta}: invariante violado min_s P95 < min_s P50")

    return fallos


# --------------------------------------------------------------------------
# Identidad, fuente, controles, negaciones y custodia
# --------------------------------------------------------------------------


def _fallos_fuente(doc: Mapping[str, Any]) -> list[str]:
    fuente = doc.get("fuente")
    if not isinstance(fuente, Mapping):
        return ["fuente ausente o con forma invalida"]
    fallos = [f"fuente sin campo {c}" for c in CAMPOS_FUENTE if c not in fuente]
    if fallos:
        return fallos
    fallos.extend(_fallos_campos_ajenos(fuente, CAMPOS_FUENTE, "fuente"))
    if not _texto_no_vacio(fuente["nota"]):
        fallos.append("fuente.nota debe declarar por escrito que no hubo medicion nueva")
    if fuente["ruta"] != pp.FUENTE:
        fallos.append("la fuente declarada no es la evidencia congelada v0.3")
    if fuente["blob"] != pp.BLOB_FUENTE:
        fallos.append("el blob de la fuente no coincide con el congelado")
    if not _es_sha(fuente["commit"]):
        fallos.append("fuente.commit no tiene forma de SHA de commit")
    if fuente["sesiones"] != pp.SESIONES_EXIGIDAS:
        fallos.append(f"la fuente debe declarar {pp.SESIONES_EXIGIDAS} sesiones")
    if fuente["escalera_ns"] != list(pp.ESCALERA_NS):
        fallos.append("fuente.escalera_ns no es la escalera preinscrita")
    if fuente["familias"] != list(pp.FAMILIAS):
        fallos.append("fuente.familias no son las familias preinscritas")
    return fallos


def _fallos_metodo(doc: Mapping[str, Any]) -> list[str]:
    metodo = doc.get("metodo")
    if not isinstance(metodo, Mapping):
        return ["metodo ausente o con forma invalida"]
    fallos = [
        f"metodo.{campo} debe declararse por escrito"
        for campo in CAMPOS_METODO_TEXTO
        if not _texto_no_vacio(metodo.get(campo))
    ]
    fallos.extend(_fallos_campos_ajenos(metodo, CAMPOS_METODO, "metodo"))
    if metodo.get("hereda_de") != list(pp.ARCHIVOS_HEREDADOS):
        fallos.append("metodo.hereda_de no cita la maquinaria heredada")
    if metodo.get("no_sustituye_evidencia") is not True:
        fallos.append("metodo.no_sustituye_evidencia debe ser True")
    return fallos


def _fallos_preinscripcion(doc: Mapping[str, Any]) -> list[str]:
    pre = doc.get("preinscripcion")
    if not isinstance(pre, Mapping):
        return ["preinscripcion ausente o con forma invalida"]
    fallos = [f"preinscripcion sin campo {c}" for c in CAMPOS_PREINSCRIPCION if c not in pre]
    fallos.extend(_fallos_campos_ajenos(pre, CAMPOS_PREINSCRIPCION, "preinscripcion"))
    for campo in ("commit_a", "head_en_derivacion"):
        if campo in pre and not _es_sha(pre[campo]):
            fallos.append(f"preinscripcion.{campo} no tiene forma de SHA de commit")
    blobs = pre.get("blobs_preinscritos")
    if isinstance(blobs, Mapping):
        for ruta in pp.ARCHIVOS_PREINSCRITOS:
            if ruta not in blobs:
                fallos.append(f"blob preinscrito ausente: {ruta}")
            elif not _es_sha(blobs[ruta]):
                fallos.append(f"blob preinscrito sin forma de blob Git: {ruta}")
    elif "blobs_preinscritos" in pre:
        fallos.append("blobs_preinscritos debe ser un mapa ruta -> blob")
    heredados = pre.get("blobs_heredados")
    if isinstance(heredados, Mapping):
        for ruta, esperado in pp.ARCHIVOS_HEREDADOS.items():
            if heredados.get(ruta) != esperado:
                fallos.append(f"blob heredado alterado o ausente: {ruta}")
    elif "blobs_heredados" in pre:
        fallos.append("blobs_heredados debe ser un mapa ruta -> blob")
    if pre.get("blob_fuente") != pp.BLOB_FUENTE:
        fallos.append("el blob de la fuente no coincide")
    if pre.get("blobs_evidencias_anteriores") != dict(pp.EVIDENCIAS_ANTERIORES):
        fallos.append(
            "blobs_evidencias_anteriores no cita intactas las evidencias v0.1, v0.2 y v0.3"
        )
    if pre.get("blob_protocolo_anterior") != ep.BLOB_PROTOCOLO_APROBADO:
        fallos.append("el blob del protocolo anterior no coincide: no debe tocarse")
    if pre.get("blob_registro_anterior") != ep.BLOB_REGISTRO_ACTUALIZADO:
        fallos.append("el blob del Registro anterior no coincide: no debe tocarse")
    return fallos


def _fallos_controles(doc: Mapping[str, Any]) -> list[str]:
    controles = doc.get("controles_internos")
    if not isinstance(controles, Mapping):
        return ["controles_internos ausente o con forma invalida"]
    fallos = [
        f"control bloqueante ausente: {c}" for c in pp.CONTROLES_BLOQUEANTES if c not in controles
    ]
    fallos.extend(_fallos_campos_ajenos(controles, pp.CONTROLES_BLOQUEANTES, "controles_internos"))
    fallidos = [
        c for c in pp.CONTROLES_BLOQUEANTES if c in controles and controles.get(c) is not True
    ]
    p50 = doc.get("p50")
    publica_u50 = isinstance(p50, Mapping) and p50.get("u50_ns") is not None
    if publica_u50 and fallidos:
        fallos.append(f"se publico U50 con controles bloqueantes fallidos: {sorted(fallidos)}")
    if not publica_u50:
        indebidos = sorted(c for c in fallidos if c not in pp.CONTROLES_QUE_EXIGEN_U50)
        if indebidos:
            fallos.append(f"sin U50 no se absuelven los controles fallidos: {indebidos}")
    return fallos


def _fallos_negaciones(doc: Mapping[str, Any]) -> list[str]:
    no_autoriza = doc.get("no_autoriza")
    if not isinstance(no_autoriza, Mapping):
        return ["no_autoriza ausente o con forma invalida"]
    fallos: list[str] = _fallos_campos_ajenos(no_autoriza, NEGACIONES_OBLIGATORIAS, "no_autoriza")
    for clave in NEGACIONES_OBLIGATORIAS:
        if clave not in no_autoriza:
            fallos.append(f"no_autoriza sin la negacion explicita: {clave}")
        elif no_autoriza[clave] is not False:
            fallos.append(f"no_autoriza.{clave} debe ser False")
    return fallos


# --------------------------------------------------------------------------
# Entrada publica
# --------------------------------------------------------------------------


def fallos_perfil_tolerancias(doc: Mapping[str, Any]) -> list[str]:
    """Valida el perfil completo. Lista vacia significa conforme.

    **Total por contrato: nunca lanza.**
    """
    try:
        return _fallos_perfil_tolerancias(doc)
    except Exception as exc:
        return [f"validacion abortada por documento malformado: {type(exc).__name__}: {exc}"]


def _fallos_perfil_tolerancias(doc: Mapping[str, Any]) -> list[str]:
    if not isinstance(doc, Mapping):
        return ["el documento debe ser un objeto JSON"]
    fallos = _fallos_secciones(doc)

    if not _texto_no_vacio(doc.get("documento")):
        fallos.append("documento sin titulo")
    if doc.get("version_esquema") != VERSION_ESQUEMA:
        fallos.append(f"version_esquema debe ser {VERSION_ESQUEMA}")
    if doc.get("estado") != pp.ESTADO:
        fallos.append("el estado declarado no es el preinscrito")
    if doc.get("acta") != pp.ACTA:
        fallos.append("el acta declarada no es la del paquete 08")
    if doc.get("protocolo") != pp.PROTOCOLO:
        fallos.append("el protocolo declarado no es el actualizado (v0.2)")
    if doc.get("registro") != pp.REGISTRO:
        fallos.append("el Registro declarado no es el actualizado (v0.5)")
    if doc.get("paquete") != pp.PAQUETE:
        fallos.append("el paquete declarado no es el 08")
    if doc.get("derivado_no_medido") is not True:
        fallos.append("derivado_no_medido debe ser True: este artefacto no mide")
    if doc.get("sesiones_exigidas") != pp.SESIONES_EXIGIDAS:
        fallos.append(f"sesiones_exigidas debe ser {pp.SESIONES_EXIGIDAS}")
    if not _es_entero(doc.get("sm_ns")) or int(doc.get("sm_ns", 0)) <= 0:
        fallos.append("sm_ns debe ser un entero positivo")
    # El perfil no republica la medicion. La prohibicion se hace cumplir
    # CERRANDO el conjunto de secciones, no enumerando nombres: una lista
    # negra se esquiva renombrando la seccion.
    ajenas = sorted(set(doc) - set(SECCIONES_OBLIGATORIAS))
    if ajenas:
        fallos.append(
            f"el perfil publica secciones ajenas al esquema: {ajenas}. No es una medicion, y "
            f"duplicar la fuente permitiria que divergiesen"
        )

    fallos.extend(_fallos_fuente(doc))
    fallos.extend(_fallos_metodo(doc))
    fallos.extend(_fallos_preinscripcion(doc))
    fallos.extend(_fallos_p50(doc))
    fallos.extend(_fallos_p95(doc))
    fallos.extend(_fallos_relacion_entre_percentiles(doc))
    fallos.extend(_fallos_contraste(doc))
    fallos.extend(_fallos_controles(doc))
    fallos.extend(_fallos_negaciones(doc))

    custodia = doc.get("custodia")
    if not isinstance(custodia, Mapping):
        fallos.append("custodia ausente o con forma invalida")
    else:
        fallos.extend(_fallos_campos_ajenos(custodia, CAMPOS_CUSTODIA, "custodia"))
        for clave, mensaje in (
            ("sha_a_es_ancestro", "el commit de preinscripcion no es ancestro de HEAD"),
            ("diff_preinscritos_vacio", "el diff en los ficheros preinscritos no esta vacio"),
            (
                "evidencias_anteriores_intactas",
                "no se acredita que las evidencias v0.1, v0.2 y v0.3 sigan intactas",
            ),
            (
                "documentos_de_gobierno_intactos",
                "no se acredita que el protocolo y el Registro anteriores sigan intactos",
            ),
        ):
            if custodia.get(clave) is not True:
                fallos.append(f"custodia: {mensaje}")
        if not _es_sha(custodia.get("head")):
            fallos.append("custodia.head no tiene forma de SHA de commit")

    return fallos


def escalera_estrictamente_creciente() -> bool:
    """Comprobacion de forma de la escalera heredada."""
    return all(a < b for a, b in pairwise(pp.ESCALERA_NS))
