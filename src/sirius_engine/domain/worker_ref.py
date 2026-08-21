"""WorkerRef: con qué se ejecutó un Run (arquitectura §3.3, ADR-054).

§3.3 define el campo ``worker`` de un Run como «adapter + perfil + (si
aplica) modelo/runtime concretos usados». Este objeto de valor es esos tres
datos con su forma comprobable, en lugar de la cadena libre que hubo hasta
la incidencia #217 -y que dejaba al motor sin poder comparar dos Runs por
modelo ni sostener ninguna afirmación sobre qué modelo hizo qué.

Los dos primeros son obligatorios: quién ejecuta (``adapter``) y bajo qué
perfil versionado (``perfil_ref`` + ``perfil_version``, los mismos que
:class:`~sirius_engine.domain.profile.AgentProfile` y ``WorkerRequest`` ya
manejan). Los dos últimos son opcionales porque hoy no siempre se conocen:
un Worker remoto revela el modelo cuando acepta el encargo, no antes.
``None`` significa «no se sabe» y se conserva como tal; la cadena vacía es
inconstruible, para que un dato ausente no pueda disfrazarse de presente
(ADR-036).

Este módulo NO valida que un adapter, un perfil o un modelo existan: no hay
registro de Workers y este trabajo no lo crea. Comprueba forma, no verdad.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from sirius_engine.domain.errors import WorkerRuntimeConflictError


def _exigir_texto(nombre: str, valor: str) -> None:
    if not valor.strip():
        raise ValueError(f"WorkerRef.{nombre} must be a non-empty string")


def _exigir_texto_opcional(nombre: str, valor: str | None) -> None:
    if valor is None:
        return
    if not valor.strip():
        raise ValueError(
            f"WorkerRef.{nombre} must be None when unknown, never an empty string: "
            "an absent value must not be able to pass for a known one"
        )


@dataclass(frozen=True, slots=True)
class WorkerRef:
    """Adapter + perfil + (si aplica) modelo/runtime concretos usados (§3.3)."""

    #: Quién ejecuta el encargo (p. ej. ``"claude-code"``): el adapter, no el modelo.
    adapter: str
    #: ``AgentProfileRef`` del perfil bajo el que se ejecuta (§5.1).
    perfil_ref: str
    #: Versión de ese perfil. Obligatoria: la v1 y la v2 de un perfil no son
    #: el mismo perfil, y comparar dos Runs sin ella compara cosas distintas.
    perfil_version: int
    #: Modelo concreto usado, cuando se conoce. ``None`` = no se sabe.
    modelo: str | None = None
    #: Runtime concreto usado, cuando se conoce. ``None`` = no se sabe.
    runtime: str | None = None

    def __post_init__(self) -> None:
        _exigir_texto("adapter", self.adapter)
        _exigir_texto("perfil_ref", self.perfil_ref)
        if self.perfil_version < 1:
            raise ValueError(
                f"WorkerRef.perfil_version must be a positive version number, "
                f"got {self.perfil_version!r}"
            )
        _exigir_texto_opcional("modelo", self.modelo)
        _exigir_texto_opcional("runtime", self.runtime)

    def same_profile(self, other: WorkerRef) -> bool:
        """True si ambos son el mismo adapter bajo el mismo perfil versionado.

        Es la comparación que hace posible la pregunta de la incidencia
        #217: dos Runs que comparten adapter y perfil y difieren SOLO en el
        modelo son comparables entre sí; si difiere el perfil, no lo son.
        """
        return (
            self.adapter == other.adapter
            and self.perfil_ref == other.perfil_ref
            and self.perfil_version == other.perfil_version
        )

    def record_execution(
        self, *, modelo: str | None = None, runtime: str | None = None
    ) -> WorkerRef:
        """Anotar el modelo/runtime concretos observados, sin mutar nada.

        ``None`` no borra lo ya registrado: significa «esta observación no
        aporta ese dato». Un valor distinto del que ya consta NO sobrescribe:
        levanta :class:`~sirius_engine.domain.errors.WorkerRuntimeConflictError`,
        porque un Run que puede cambiar de modelo a posteriori no sostiene
        ninguna afirmación sobre qué modelo hizo qué.
        """
        _exigir_texto_opcional("modelo", modelo)
        _exigir_texto_opcional("runtime", runtime)
        return replace(
            self,
            modelo=_conciliar("modelo", registrado=self.modelo, recibido=modelo),
            runtime=_conciliar("runtime", registrado=self.runtime, recibido=runtime),
        )

    def without_execution(self) -> WorkerRef:
        """El mismo adapter y perfil, sin modelo ni runtime.

        Lo usa el reintento (§3.2): un Run recién PREPARADO todavía no se ha
        ejecutado, así que heredar el modelo del intento anterior sería
        afirmar más de lo que el dato sostiene. El adapter y el perfil sí se
        heredan: son la elección del llamador, no una observación.
        """
        return replace(self, modelo=None, runtime=None)


def _conciliar(campo: str, *, registrado: str | None, recibido: str | None) -> str | None:
    if recibido is None:
        return registrado
    if registrado is not None and registrado != recibido:
        raise WorkerRuntimeConflictError(campo, registrado=registrado, recibido=recibido)
    return recibido
