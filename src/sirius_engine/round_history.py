"""Analizadores puros del historial de rondas, compartidos por dos lados (H-13, incidencia #275).

``parse_round_records``, ``history_after_last_resume`` y ``ci_failure_streak``
-con las expresiones regulares y funciones auxiliares que necesitan- vivían
duplicadas en potencia: la política de convergencia real
(``scripts/automation/sirius_convergence.py``, que ``repair-sirius-work.yml``
ejecuta con el ``python3`` del sistema, **sin** el proyecto instalado) y el
espejo de solo lectura (:mod:`sirius_engine.mirror_projection`, incidencia
#193) necesitaban exactamente las mismas funciones para interpretar el mismo
texto de la misma forma. Antes de este bloque, el espejo las obtenía
insertando ``scripts/`` en ``sys.path`` e importando el script de
automatización -un truco que funcionaba en el checkout de desarrollo pero
rompía ``ModuleNotFoundError`` en cuanto alguien llamaba a la proyección
desde una instalación real del paquete, porque ``scripts/`` no viaja en el
wheel (incidencia #272).

Este módulo es la única definición de las tres funciones. Vive dentro de
``sirius_engine`` para que el paquete lo importe de forma normal, sin ningún
truco de ``sys.path`` (``from sirius_engine.round_history import ...``).
``scripts/automation/round_history.py`` es un enlace simbólico a este mismo
fichero -no una segunda copia-, así que ``sirius_convergence.py`` sigue
teniendo un módulo hermano que importar sin depender de ``sirius_engine`` ni
de que el proyecto esté instalado (comprobado construyendo el wheel real e
instalándolo en un venv limpio, y ejecutando el script bajo un intérprete
``python3`` distinto del de este proyecto).

Todas las funciones son puras -mismo texto de entrada, misma salida- y solo
usan la biblioteca estándar, para que ambos lados puedan cargarlas sin traer
ninguna dependencia del proyecto consigo.
"""

from __future__ import annotations

import json
import re
from typing import Any

# --- Registro de ronda -------------------------------------------------------
#
# Un registro de ronda solo cuenta si va precedido de su marcador oculto en el
# MISMO comentario: `<!-- sirius-round:N -->` seguido del bloque. Exigir el par
# completo evita que un bloque suelto —copiado, citado o publicado aparte— se
# cuele como ronda. La lectura previa ya filtra por autor de confianza
# (`sirius_dump_comments`), así que esto es la segunda barrera, no la única.
ROUND_RECORD_RE = re.compile(
    r"<!--\s*sirius-round:(\d+)\s*-->\s*"
    r"##\s*RONDA_HALLAZGOS\s*```json\s*(.*?)\s*```",
    re.DOTALL,
)

# Peso de cada severidad para medir la gravedad agregada de una ronda. Cubre la
# escala de Codex (P0..P4) y las etiquetas en español del revisor Claude. Un
# valor desconocido pesa como media: nunca cero, para que un hallazgo sin
# clasificar no pueda simular una mejora al perder su etiqueta.
SEVERITY_WEIGHTS: dict[str, int] = {
    "p0": 4,
    "critica": 4,
    "crítica": 4,
    "bloqueante": 4,
    "p1": 3,
    "alta": 3,
    "p2": 2,
    "media": 2,
    "p3": 1,
    "p4": 1,
    "baja": 1,
    "menor": 1,
}
DEFAULT_SEVERITY_WEIGHT = 2


# Sufijo de línea (o rango de líneas) que el recolector añade al archivo de una
# observación: `scripts/x.py:120`, `scripts/x.py:120-134`. Se recorta al calcular
# la huella porque la línea NO identifica al defecto: cualquier corrección en
# otra parte del mismo archivo desplaza la numeración, y con la línea dentro de
# la huella el mismo defecto sin tocar aparecería como uno resuelto más uno
# nuevo. Eso falsea las dos medidas a la vez —el detector de reaparición y el de
# progreso— justo en las rondas en las que más importa acertar.
LOCATION_LINE_RE = re.compile(r":\d+(?:-\d+)?$")


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _normalize_location(value: object) -> str:
    """Ubicación estable de una observación: archivo sin el sufijo de línea."""
    return LOCATION_LINE_RE.sub("", _normalize_text(value))


def severity_weight(value: object) -> int:
    return SEVERITY_WEIGHTS.get(_normalize_text(value), DEFAULT_SEVERITY_WEIGHT)


def parse_round_records(text: str) -> list[dict[str, Any]]:
    """Extrae, en orden cronológico, los registros de ronda de un texto.

    ``text`` es la concatenación de los comentarios de la incidencia del más
    antiguo al más reciente. Un bloque ilegible se ignora sin romper el
    análisis: la decisión se toma con los registros que sí son válidos.
    """
    records: list[dict[str, Any]] = []
    # Una ronda cuenta UNA vez por número, aunque su registro aparezca repetido.
    #
    # No es defensa contra un tercero —la lectura previa ya filtra por autor—
    # sino contra nosotros mismos: publicar un comentario contra la API de GitHub
    # no puede ser exactamente-una-vez, porque el POST no es idempotente y no hay
    # clave de idempotencia del lado del servidor. Un resultado ambiguo (GitHub
    # acepta y la respuesta se pierde) deja el comentario publicado, y ni la
    # ejecución que lo publicó ni la siguiente pueden demostrar que llegó si la
    # lectura todavía no lo refleja. Perseguir la unicidad en la escritura es
    # perseguir algo inalcanzable; lo que sí está en nuestra mano es que un
    # duplicado no signifique nada distinto de un original.
    #
    # Sin esto, dos copias del registro de la ronda N se leían como dos rondas
    # consecutivas sobre el mismo head, y la puerta bloqueaba por
    # `head-sin-avance` un trabajo que sí avanzaba. `ci_failure_streak` ya es
    # idempotente por el mismo motivo: cuenta heads distintos, no marcadores.
    seen_rounds: set[int] = set()
    for marker_round, raw in ROUND_RECORD_RE.findall(text):
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        findings = record.get("findings")
        if not isinstance(findings, list):
            continue
        normalized = [item for item in findings if isinstance(item, dict)]
        record["findings"] = normalized
        # El número de ronda autoritativo es el del MARCADOR, no el del cuerpo
        # del JSON: el marcador es lo que la automatización numera y lo que
        # `sirius_next_round_number` cuenta. Así un campo `round` ausente, no
        # numérico o manipulado no puede reordenar el historial ni provocar una
        # excepción al ordenar (que dejaría la decisión vacía y bloquearía toda
        # ronda posterior).
        record["round"] = int(marker_round)
        # La comprobación va aquí, después de validar el JSON: si la primera
        # copia estuviera corrupta y la segunda fuese legible, gana la legible.
        if record["round"] in seen_rounds:
            continue
        seen_rounds.add(record["round"])
        record["fingerprints"] = {
            str(item.get("fingerprint") or "") for item in normalized if item.get("fingerprint")
        }
        record["pending"] = len(normalized)
        records.append(record)
    records.sort(key=lambda item: int(item["round"]))
    _apply_sticky_severity(records)
    return records


def _apply_sticky_severity(records: list[dict[str, Any]]) -> None:
    """Fija la gravedad de cada huella a la peor jamás observada para ella.

    Sin esto, la gravedad agregada baja sola cuando un revisor omite la etiqueta
    de un hallazgo que sigue ahí: un P0 (peso 4) que reaparece sin insignia pasa
    a contar como `sin-clasificar` (peso 2) y el par (pendientes, gravedad)
    "mejora" sin que se haya corregido absolutamente nada. Esa mejora fantasma
    basta para superar la comprobación de progreso y mantener abierto un ciclo
    estancado. Una vez que una huella se ha visto como P0, cuenta como P0
    mientras siga pendiente: la gravedad de un defecto no la decide el formato
    del comentario que lo describe.

    Se aplica en orden de ronda y sobre TODAS las rondas —también las que sirven
    de mejor marca histórica—, así que el listón y la ronda medida usan la misma
    escala. La corrección solo puede subir el peso de una ronda respecto de sus
    propias etiquetas, nunca bajarlo, y el par sigue viviendo en ℕ²: la prueba
    de terminación no se ve afectada.
    """
    worst: dict[str, int] = {}
    for record in records:
        # Primero se consolida el peor peso de la RONDA por huella y solo
        # después se suma. Actualizar el máximo mientras se suma haría depender
        # el total del orden de llegada cuando una misma huella aparece dos
        # veces en la ronda con etiquetas distintas (P4 antes que P0 daría un
        # total y al revés otro), y la decisión debe ser función únicamente del
        # contenido del historial.
        for item in record["findings"]:
            fingerprint_value = str(item.get("fingerprint") or "")
            if fingerprint_value:
                worst[fingerprint_value] = max(
                    worst.get(fingerprint_value, 0), severity_weight(item.get("severity"))
                )
        total = 0
        for item in record["findings"]:
            fingerprint_value = str(item.get("fingerprint") or "")
            total += (
                worst[fingerprint_value]
                if fingerprint_value
                else severity_weight(item.get("severity"))
            )
        record["severity_total"] = total


# --- Historial vigente y racha de fallos de Quality -------------------------
#
# Marcador que publica `sirius_resume_on_command.sh` cuando el propietario
# levanta una parada escribiendo la orden en la incidencia.
#
# La política de convergencia es una salvaguarda, no un obstáculo: cuando
# bloquea, tiene razón. Lo que faltaba no era relajarla, sino una entrada por la
# que la decisión humana que reclama pueda LLEGAR. Sin ella, el historial la
# condena para siempre —`decide()` mide sobre todas las rondas publicadas, así
# que reponer la etiqueta disparadora vuelve a bloquear en el acto— y levantar
# la parada exige editar la incidencia a mano o hacer el trabajo fuera del
# ciclo. Ocurrió en la #186: el propietario autorizó una ronda más y no había
# forma de dársela a la máquina.
RESUME_MARKER_RE = re.compile(r"<!--\s*sirius-convergence-reset:[0-9a-fA-F]+\s*-->")


def history_after_last_resume(text: str) -> str:
    """El historial que cuenta: lo publicado DESPUÉS de la última orden de continuar.

    Corta el texto, no lo filtra, y por eso reinicia los DOS motores del ciclo a
    la vez —las rondas de revisión y la racha de fallos de Quality— con una sola
    regla. Reiniciar solo uno dejaría al otro condenando el trabajo que el
    propietario acaba de autorizar.

    Lo que NO hace, y es la mitad del diseño: **no borra nada**. Las rondas
    anteriores siguen publicadas en la incidencia y siguen siendo auditables;
    lo único que cambia es que dejan de servir de listón. Una parada por
    `sin-progreso` volverá a saltar en cuanto haya dos rondas planas
    *posteriores* al marcador, con el mismo criterio de siempre. La salvaguarda
    no se debilita: se le da una entrada.
    """
    corte = 0
    for match in RESUME_MARKER_RE.finditer(text):
        corte = match.end()
    return text[corte:]


# Marcadores que `advance-sirius-after-quality.yml` publica según el resultado
# de Quality sobre un head. Son la ÚNICA huella del otro motor del ciclo de
# corrección, y por eso hacen falta aquí.
#
# El ciclo tiene dos motores, no uno. Uno son las rondas de revisión, que
# publican `RONDA_HALLAZGOS` y que la política de progreso mide. El otro son los
# fallos de Quality: cuando la corrección rompe la construcción, el avance
# vuelve a aplicar `sirius:repair-requested` publicando `## CI_FAILURE`, que NO
# es un registro de ronda. Para ese camino el historial de rondas no cambia, la
# decisión de convergencia es siempre la misma y `CONTINUE` se repetiría sin fin.
CI_FAILURE_MARKER_RE = re.compile(
    r"<!--\s*sirius-quality:([0-9a-fA-F]+):(?:failure|timed_out)\s*-->"
)
CI_SUCCESS_MARKER_RE = re.compile(r"<!--\s*sirius-quality:[0-9a-fA-F]+:success\s*-->")


def ci_failure_streak(text: str) -> int:
    """Intentos de corrección consecutivos que Quality tumbó, desde el último verde.

    ``text`` es el historial de la incidencia en orden cronológico. Un Quality
    en verde reinicia la cuenta: significa que la construcción volvió a estar
    sana y que el ciclo avanza por el otro motor, el de las rondas de revisión.

    Se cuentan **heads distintos**, no marcadores. Lo que esta cota mide son
    intentos de corrección, y cada intento es forzosamente un commit nuevo: dos
    marcadores sobre el MISMO head siguen siendo un único intento. Contar
    marcadores gastaba presupuesto sin que el corrector hubiera vuelto a probar
    nada, y eso ocurre de verdad, no en teoría: basta con que Quality se
    reejecute sobre el mismo head y cambie de conclusión (``failure`` la primera
    vez, ``timed_out`` la siguiente) para que un solo intento consumiera dos
    tercios del margen. Una prueba intermitente —que este repositorio ya tiene—
    hace de esa reejecución la norma, no la excepción.
    """
    last_success = -1
    for match in CI_SUCCESS_MARKER_RE.finditer(text):
        last_success = match.end()
    heads = {
        match.group(1).casefold()
        for match in CI_FAILURE_MARKER_RE.finditer(text)
        if match.start() > last_success
    }
    return len(heads)
