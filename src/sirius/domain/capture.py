"""Escenas autorizadas de Model Studio.

#127 exige un ``SceneRegistry`` con identificadores estables, nombres visibles,
alias de voz, escena de reserva y **lista blanca**. La lista blanca es lo
importante: una escena que no esté aquí no se puede activar, venga la orden de
donde venga. Sin ella, decir en voz alta el nombre de cualquier cosa sería una
forma de mandar texto libre al sistema de captura.

Los identificadores son estables a propósito: el nombre visible de una escena
puede cambiar en OBS sin que se rompa nada de lo que Sirius recuerde o registre.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field


def normalize_alias(text: str) -> str:
    """Forma canónica de un alias hablado.

    Quita acentos y mayúsculas porque una transcripción de voz escribe «cámara»
    o «camara» según le parezca, y ninguna de las dos puede fallar por eso.
    """
    lowered = text.strip().casefold()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


@dataclass(frozen=True, slots=True)
class Scene:
    """Una escena autorizada.

    ``scene_id`` es el identificador estable con el que Sirius la conoce.
    ``backend_name`` es cómo se llama en el sistema de captura, que puede
    cambiar. ``aliases`` son las formas de nombrarla en voz alta.
    """

    scene_id: str
    display_name: str
    backend_name: str
    aliases: tuple[str, ...] = ()
    is_fallback: bool = False

    def matches(self, spoken: str) -> bool:
        """Si esta escena responde a lo que se ha dicho."""
        wanted = normalize_alias(spoken)
        if not wanted:
            return False
        candidates = (self.scene_id, self.display_name, *self.aliases)
        return any(normalize_alias(candidate) == wanted for candidate in candidates)


@dataclass(frozen=True, slots=True)
class SceneRegistry:
    """Lista blanca de escenas. Lo que no está aquí, no se activa."""

    scenes: tuple[Scene, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        identifiers = [scene.scene_id for scene in self.scenes]
        if len(identifiers) != len(set(identifiers)):
            msg = "Hay escenas con el mismo identificador."
            raise ValueError(msg)

    @property
    def is_empty(self) -> bool:
        return not self.scenes

    @property
    def fallback(self) -> Scene | None:
        """Escena de reserva a la que volver si una fuente se pierde.

        Si nadie la marcó, se usa la primera: tener una reserva imperfecta es
        mejor que quedarse con un plano roto en pantalla mientras se graba.
        """
        for scene in self.scenes:
            if scene.is_fallback:
                return scene
        return self.scenes[0] if self.scenes else None

    def by_id(self, scene_id: str) -> Scene | None:
        """Escena con ese identificador, o ``None`` si no está autorizada."""
        for scene in self.scenes:
            if scene.scene_id == scene_id:
                return scene
        return None

    def resolve(self, spoken_or_id: str) -> Scene | None:
        """Escena que corresponde a un identificador o a algo dicho en voz alta.

        Devuelve ``None`` cuando no hay coincidencia exacta. **No adivina**: una
        escena parecida no es la escena pedida, y cambiar de plano por error en
        mitad de una grabación es peor que no cambiar.
        """
        exact = self.by_id(spoken_or_id)
        if exact is not None:
            return exact
        matches = [scene for scene in self.scenes if scene.matches(spoken_or_id)]
        # Dos escenas que responden al mismo alias son una ambigüedad de
        # configuración: no se elige ninguna.
        return matches[0] if len(matches) == 1 else None

    def contains_backend_name(self, backend_name: str) -> bool:
        """Si el sistema de captura reporta una escena que sí está autorizada."""
        return any(scene.backend_name == backend_name for scene in self.scenes)


def build_scene_registry(configured: object) -> SceneRegistry:
    """Construye la lista blanca a partir de la configuración del usuario.

    Es deliberadamente estricta: una entrada mal escrita **se descarta**, no se
    intenta arreglar. Una escena a medias en la lista blanca sería una escena
    que se puede activar sin que nadie la haya autorizado del todo.

    Sin configuración válida devuelve una lista vacía, y con una lista vacía el
    Módulo Captura no se puede encender. Es el estado correcto de partida.
    """
    if not isinstance(configured, list):
        return SceneRegistry()

    scenes: list[Scene] = []
    seen: set[str] = set()
    for entry in configured:
        if not isinstance(entry, dict):
            continue
        scene_id = str(entry.get("id", "")).strip()
        backend_name = str(entry.get("backend_name", "")).strip()
        if not scene_id or not backend_name or scene_id in seen:
            continue
        raw_aliases = entry.get("aliases", [])
        aliases = (
            tuple(str(alias) for alias in raw_aliases if str(alias).strip())
            if isinstance(raw_aliases, list)
            else ()
        )
        scenes.append(
            Scene(
                scene_id=scene_id,
                display_name=str(entry.get("name", "")).strip() or backend_name,
                backend_name=backend_name,
                aliases=aliases,
                is_fallback=bool(entry.get("fallback", False)),
            )
        )
        seen.add(scene_id)
    return SceneRegistry(tuple(scenes))
