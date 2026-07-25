"""Revisión dirigida de consistencia de los resultados de ADR-001.

    uv run python -m experiments.adr001.revision_dirigida

No reejecuta ningún spike. Coteja el informe v0.1, el paquete de evidencia,
las pruebas y el código, y comprueba de forma automática:

1. que los 14 resultados registrados corresponden con las pruebas y el JSON;
2. que ningún PASS se declara sin evidencia automática que lo sostenga;
3. que la regla RATIFICAR A / ESCALAR A B / ABRIR C está bien aplicada;
4. que el spike 19 mantiene explícitos su modelo de amenaza y sus límites;
5. que derivados, ``secure_delete`` y Windows siguen siendo condiciones
   pendientes y no garantías ya implementadas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiments.adr001.evidence import (
    ARTIFACTS_DIR,
    FAIL_ENGINE_SQLITE,
    FAIL_STRUCTURAL_MODEL,
    INCONCLUSIVE,
    PASS,
    SpikeEvidence,
)
from experiments.adr001.run_all import (
    DECISION_ABRIR_C,
    DECISION_BLOQUEADA,
    DECISION_ESCALAR_B,
    DECISION_RATIFICAR_A,
    decide,
)

EXPERIMENTS_DIR = Path(__file__).resolve().parent

SPIKES_ESPERADOS = (1, 2, 3, 4, 5, 6, 7, 8, 10, 15, 16, 17, 18, 19)

CAMPOS_MINIMOS_DEL_PAQUETE = (
    "objetivo",
    "incertidumbre",
    "dataset",
    "preparacion",
    "operacion",
    "resultado_esperado",
    "criterio_de_fallo",
    "evidencia",
    "resultado",
    "repeticion_limpia",
    "conclusion",
)

# Claves de la evidencia registrada que deben sostener cada PASS. Se han
# derivado leyendo la expresión ``ok`` de cada spike en el código: si el
# veredicto es PASS, estas medidas tienen que valer exactamente esto.
GATING: dict[int, dict[str, Any]] = {
    1: {"procedencias_registradas": 3, "0_1_intacto": True},
    2: {
        "apoyos": 2,
        "refutaciones": 2,
        "coexisten_ambas_posturas": True,
        "0_1_intacto": True,
    },
    3: {
        "misma_validez_distinto_registro": True,
        "mismo_registro_distinta_validez": True,
        "0_1_intacto": True,
    },
    4: {
        "valor_original_tras_corregir": "azul",
        "estado_anterior_preservado": True,
        "correccion_enlazada_al_original": True,
        "0_1_intacto": True,
    },
    5: {
        "valida_en_2021": [1],
        "esperado_2021": [1],
        "valida_en_2023": [3],
        "esperado_2023": [3],
        "0_1_intacto": True,
    },
    6: {
        "creencia_anterior_recuperable": True,
        "creencia_anterior_ya_no_vigente": True,
        "creencia_nueva_solo_despues": True,
        "0_1_intacto": True,
    },
    7: {
        "son_exactamente_siete": True,
        "siete_dimensiones_representadas_de_forma_independiente": True,
        "mutar_una_deja_intactas_las_otras_seis": True,
        "el_enum_monolitico_no_puede_expresarlas": True,
        "colapso_incluso_en_una_dimension_que_el_enum_roza": True,
        "ambito_y_autoridad_no_se_colapsan": True,
        "tablas_heredadas_no_alteradas": True,
        "0_1_intacto": True,
        "modelo_experimental": True,
        "ddl_productivo_fijado": False,
        "nombres_fisicos_productivos_fijados": False,
    },
    8: {
        "aislamiento_sin_fugas": True,
        "el_modelo_heredado_permite_dos_proyectos_activos": False,
        "0_1_intacto": True,
    },
    10: {
        "control_positivo_canario_localizable_antes": True,
        "procedimiento_completo_deja_el_fichero_limpio": True,
    },
    15: {
        "head_sin_cambios": True,
        "0_1_byte_a_byte_igual": True,
        "recuentos_heredados_iguales": True,
        "sin_perdidas": True,
        "sin_duplicaciones": True,
        "afirmaciones_huerfanas": 0,
        "afirmaciones_sin_procedencia": 0,
        "contenido_conservado_en_todas": True,
        "autoridad_unica": True,
    },
    16: {
        "esquema_completo_identico_al_inicial": True,
        "0_1_byte_a_byte_igual": True,
        "head_alembic_sin_cambios": True,
        "base_sigue_siendo_utilizable_por_sirius_0_1": True,
        "residuo_experimental": [],
    },
    17: {
        "excepcion_inyectada_y_capturada": True,
        "sin_estado_parcial": True,
        "0_1_intacto": True,
    },
    18: {
        "derivados_eliminados_por_completo": True,
        "la_consulta_canonica_no_depende_del_derivado": True,
        "reconstruccion_identica": True,
        "0_1_intacto": True,
    },
    19: {
        "traza_borrado_wal.etapa_4_canario_tras_vacuum": False,
        "intentos_de_reconstruccion.filas_canonicas_con_el_token": 0,
        "intentos_de_reconstruccion.coincidencias_fts": 0,
        "intentos_de_reconstruccion.sombras_que_aun_contienen_el_token": 0,
        "intentos_de_reconstruccion.copia_vacuum_into_contiene_el_canario": False,
    },
}

CONDICIONES_PENDIENTES = {
    "derivados": ("derivado",),
    "secure_delete": ("secure_delete",),
    "windows": ("Windows",),
}


def _ruta(evidencia: dict[str, Any], clave: str) -> Any:
    actual: Any = evidencia
    for parte in clave.split("."):
        if not isinstance(actual, dict) or parte not in actual:
            return "<ausente>"
        actual = actual[parte]
    return actual


def _cargar(nombre: str) -> list[dict[str, Any]]:
    return list(json.loads((ARTIFACTS_DIR / nombre).read_text(encoding="utf-8")))


def _como_evidencias(payload: list[dict[str, Any]]) -> list[SpikeEvidence]:
    return [SpikeEvidence(**entry) for entry in payload]


def _sintetico(numero: int, resultado: str) -> SpikeEvidence:
    return SpikeEvidence(
        numero=numero,
        nombre="sintetico",
        objetivo="",
        incertidumbre="",
        dataset="",
        preparacion="",
        operacion="",
        resultado_esperado="",
        criterio_de_fallo="",
        resultado=resultado,
    )


def main() -> int:
    lineas: list[str] = []
    add = lineas.append
    incidencias: list[str] = []

    bundle = _cargar("evidencia_spikes_v0.2.json")
    por_numero = {int(entry["numero"]): entry for entry in bundle}
    evidencias = _como_evidencias(bundle)
    fuente_pruebas = (EXPERIMENTS_DIR / "test_adr001_spikes.py").read_text(encoding="utf-8")
    informe_v01 = (
        ARTIFACTS_DIR / "SIRIUS_0.2_ADR_001_RESULTADOS_SPIKES_v0.1_PROPUESTO.md"
    ).read_text(encoding="utf-8")

    add("REVISIÓN DIRIGIDA DE CONSISTENCIA — ADR-001")
    add("=" * 68)
    add("")
    add("Alcance: cotejo del informe v0.1, el paquete de evidencia, las pruebas")
    add("y el código. NO se reejecuta ningún spike salvo el 7, ya corregido.")
    add("")

    # --- 1. Los 14 resultados corresponden con las pruebas y el JSON.
    add("1. CORRESPONDENCIA ENTRE RESULTADOS, PRUEBAS Y JSON")
    add("-" * 68)
    numeros = sorted(por_numero)
    if numeros != sorted(SPIKES_ESPERADOS):
        incidencias.append(f"el JSON no contiene los 14 spikes esperados: {numeros}")
    add(f"  spikes en el JSON            : {len(numeros)} -> {numeros}")
    add(f"  coinciden con los exigidos   : {numeros == sorted(SPIKES_ESPERADOS)}")

    sin_prueba = [n for n in SPIKES_ESPERADOS if f"spike_{n:02d}" not in fuente_pruebas]
    if sin_prueba:
        incidencias.append(f"spikes sin prueba pytest que los invoque: {sin_prueba}")
    add(f"  todos invocados por pytest   : {not sin_prueba}")

    incompletos = [
        n
        for n, entry in por_numero.items()
        if any(not str(entry.get(campo, "")).strip() for campo in CAMPOS_MINIMOS_DEL_PAQUETE)
    ]
    if incompletos:
        incidencias.append(f"spikes con campos vacíos del §6 del paquete: {incompletos}")
    add(f"  11 campos del §6 completos    : {not incompletos}")

    incoherentes = [
        n
        for n, entry in por_numero.items()
        if entry["resultado"] == PASS
        and (
            "NO REPRODUCIBLE" in entry["repeticion_limpia"]
            or not entry["conclusion"].strip()
            or "no se pudo" in entry["conclusion"].lower()
        )
    ]
    if incoherentes:
        incidencias.append(f"resultado/repetición/conclusión incoherentes: {incoherentes}")
    add(
        f"  resultado ↔ repetición ↔ concl.: {'coherentes' if not incoherentes else 'INCOHERENTES'}"
    )
    add("")

    # --- 2. Ningún PASS sin evidencia automática.
    add("2. NINGÚN PASS DECLARADO SIN EVIDENCIA AUTOMÁTICA")
    add("-" * 68)
    for numero in sorted(GATING):
        entry = por_numero[numero]
        fallos = [
            f"{clave}={_ruta(entry['evidencia'], clave)!r} (esperado {esperado!r})"
            for clave, esperado in GATING[numero].items()
            if _ruta(entry["evidencia"], clave) != esperado
        ]
        estado = "sostenido" if not fallos else "SIN SOSTÉN"
        medidas = len(GATING[numero])
        add(f"  spike {numero:>2}  {entry['resultado']:<6} {medidas:>2} medidas  {estado}")
        if fallos:
            incidencias.append(f"spike {numero}: PASS sin sostén -> {'; '.join(fallos)}")
    vacios = [n for n, entry in por_numero.items() if not entry["evidencia"]]
    if vacios:
        incidencias.append(f"spikes con evidencia vacía: {vacios}")
    add(f"  evidencia no vacía en los 14  : {not vacios}")
    add("")

    # --- 3. Regla de decisión.
    add("3. REGLA RATIFICAR A / ESCALAR A B / ABRIR C")
    add("-" * 68)
    decision = decide(evidencias)
    todos_pass = all(entry["resultado"] == PASS for entry in bundle)
    add(f"  los 14 en PASS                : {todos_pass}")
    add(f"  decisión sobre el conjunto    : {decision}")
    if todos_pass and decision != DECISION_RATIFICAR_A:
        incidencias.append("los 14 están en PASS pero la regla no devuelve RATIFICAR A")
    if not todos_pass and decision == DECISION_RATIFICAR_A:
        incidencias.append("se declara RATIFICAR A sin que los 14 estén en PASS")

    # Contraejemplos: la regla debe reaccionar, no solo devolver lo esperado.
    base = [_sintetico(n, PASS) for n in SPIKES_ESPERADOS]

    def _con(numero: int, resultado: str) -> list[SpikeEvidence]:
        return [_sintetico(n, resultado if n == numero else PASS) for n in SPIKES_ESPERADOS]

    contraejemplos = (
        ("14 en PASS", base, DECISION_RATIFICAR_A),
        ("FAIL_STRUCTURAL_MODEL en 7", _con(7, FAIL_STRUCTURAL_MODEL), DECISION_ESCALAR_B),
        ("FAIL_STRUCTURAL_MODEL en 15", _con(15, FAIL_STRUCTURAL_MODEL), DECISION_ESCALAR_B),
        ("FAIL_ENGINE_SQLITE en 10", _con(10, FAIL_ENGINE_SQLITE), DECISION_ABRIR_C),
        ("FAIL_ENGINE_SQLITE en 19", _con(19, FAIL_ENGINE_SQLITE), DECISION_ABRIR_C),
        ("INCONCLUSIVE en 3", _con(3, INCONCLUSIVE), DECISION_BLOQUEADA),
    )
    for etiqueta, conjunto, esperado in contraejemplos:
        obtenido = decide(conjunto)
        ok = obtenido == esperado
        add(f"  {etiqueta:<28} -> {obtenido:<22} {'ok' if ok else 'MAL APLICADA'}")
        if not ok:
            incidencias.append(f"regla mal aplicada en «{etiqueta}»: {obtenido} != {esperado}")
    add("")

    # --- 4. Spike 19: modelo de amenaza y límites.
    add("4. SPIKE 19 — MODELO DE AMENAZA Y LÍMITES")
    add("-" * 68)
    ev19 = por_numero[19]["evidencia"]
    modelo = str(ev19.get("modelo_de_amenaza", ""))
    declara_alcance = "-wal" in modelo and "copias" in modelo
    declara_exclusion = "excluye" in modelo and "forense" in modelo
    add(f"  modelo de amenaza explícito   : {bool(modelo)}")
    add(f"  declara el alcance            : {declara_alcance}")
    add(f"  declara lo que queda fuera    : {declara_exclusion}")
    contraste = ev19.get("contraste_demuestra_que_el_borrado_logico_no_purga")
    add(f"  contraste que valida la medida: {contraste}")
    add(f"  límite recogido en el informe : {'modelo de amenaza' in informe_v01}")
    if not (modelo and declara_alcance and declara_exclusion):
        incidencias.append("el spike 19 no mantiene explícitos su modelo de amenaza y sus límites")
    add("")

    # --- 5. Condiciones pendientes, no garantías.
    add("5. DERIVADOS, SECURE_DELETE Y WINDOWS SIGUEN SIENDO CONDICIONES")
    add("-" * 68)
    for etiqueta, agujas in CONDICIONES_PENDIENTES.items():
        presente = any(aguja in informe_v01 for aguja in agujas)
        add(f"  {etiqueta:<16} citado en el informe v0.1 : {presente}")
        if not presente:
            incidencias.append(f"la condición «{etiqueta}» no aparece en el informe v0.1")
    condiciones_como_condiciones = (
        "Condiciones que la ratificación arrastra" in informe_v01
        and "no son objeciones a A; son consecuencias medidas" in informe_v01
    )
    add(f"  declaradas como condiciones   : {condiciones_como_condiciones}")
    if not condiciones_como_condiciones:
        incidencias.append("las condiciones no están declaradas como tales en el informe v0.1")
    add("")

    # --- Cierre.
    add("RESULTADO DE LA REVISIÓN DIRIGIDA")
    add("=" * 68)
    if incidencias:
        add(f"  {len(incidencias)} incidencia(s) con defecto demostrable:")
        for incidencia in incidencias:
            add(f"    - {incidencia}")
    else:
        add("  Sin defectos demostrables. No se cambia ningún resultado.")
    add("")
    add("  Las observaciones que NO constituyen defecto (asimetrías de rigor,")
    add("  residuos de nomenclatura y desajustes de entorno) se detallan en el")
    add("  informe v0.2, §6.")

    destino = ARTIFACTS_DIR / "07_revision_dirigida.txt"
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    print(f"\ntraza: {destino}")
    return 1 if incidencias else 0


if __name__ == "__main__":
    raise SystemExit(main())
