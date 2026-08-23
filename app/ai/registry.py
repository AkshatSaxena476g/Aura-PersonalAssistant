"""Central registration and construction of swappable AI providers."""

from __future__ import annotations

from collections.abc import Callable

from .provider import AIProvider


ProviderFactory = Callable[[], AIProvider]


class ProviderRegistry:
    """Map stable provider names to provider factories.

    Concrete providers register themselves at the composition root. The core
    only needs the resulting ``AIProvider`` protocol and never imports a
    vendor SDK directly.
    """

    def __init__(self) -> None:
        self._factories: dict[str, ProviderFactory] = {}

    def register(self, name: str, factory: ProviderFactory) -> None:
        """Register a provider factory under a normalized name."""

        normalized_name = name.strip().lower()
        if not normalized_name:
            raise ValueError("Provider name must not be empty")
        if normalized_name in self._factories:
            raise ValueError(f"Provider already registered: {normalized_name}")
        self._factories[normalized_name] = factory

    def create(self, name: str) -> AIProvider:
        """Construct a registered provider or raise a clear configuration error."""

        normalized_name = name.strip().lower()
        try:
            factory = self._factories[normalized_name]
        except KeyError as error:
            available = ", ".join(sorted(self._factories)) or "none"
            raise LookupError(
                f"Unknown AI provider '{name}'. Available providers: {available}"
            ) from error
        return factory()

    @property
    def names(self) -> tuple[str, ...]:
        """Return registered provider names in deterministic order."""

        return tuple(sorted(self._factories))
