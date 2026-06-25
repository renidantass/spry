from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, get_type_hints

Factory = Callable[["Resolver"], Any]


class Resolver:
    def resolve(self, service_type: type[Any]) -> Any:
        raise NotImplementedError

    def construct(self, implementation_type: type[Any]) -> Any:
        raise NotImplementedError


class ServiceLifetime(str, Enum):
    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"


@dataclass(slots=True)
class ServiceDescriptor:
    service_type: type[Any]
    factory: Factory
    lifetime: ServiceLifetime


class ServiceCollection:
    def __init__(self) -> None:
        self._descriptors: dict[type[Any], ServiceDescriptor] = {}

    def add_singleton(
        self,
        service_type: type[Any],
        implementation: type[Any] | None = None,
        *,
        instance: Any | None = None,
        factory: Factory | None = None,
    ) -> None:
        descriptor = self._build_descriptor(service_type, implementation, instance, factory, ServiceLifetime.SINGLETON)
        self._descriptors[service_type] = descriptor

    def add_scoped(
        self,
        service_type: type[Any],
        implementation: type[Any] | None = None,
        *,
        factory: Factory | None = None,
    ) -> None:
        descriptor = self._build_descriptor(service_type, implementation, None, factory, ServiceLifetime.SCOPED)
        self._descriptors[service_type] = descriptor

    def add_transient(
        self,
        service_type: type[Any],
        implementation: type[Any] | None = None,
        *,
        factory: Factory | None = None,
    ) -> None:
        descriptor = self._build_descriptor(service_type, implementation, None, factory, ServiceLifetime.TRANSIENT)
        self._descriptors[service_type] = descriptor

    def build_provider(self) -> ServiceProvider:
        return ServiceProvider(self._descriptors)

    @staticmethod
    def _build_descriptor(
        service_type: type[Any],
        implementation: type[Any] | None,
        instance: Any | None,
        factory: Factory | None,
        lifetime: ServiceLifetime,
    ) -> ServiceDescriptor:
        if instance is not None:
            return ServiceDescriptor(service_type=service_type, factory=lambda _: instance, lifetime=lifetime)
        if factory is not None:
            return ServiceDescriptor(service_type=service_type, factory=factory, lifetime=lifetime)

        implementation_type = implementation or service_type
        return ServiceDescriptor(
            service_type=service_type,
            factory=lambda resolver: resolver.construct(implementation_type),
            lifetime=lifetime,
        )


class ServiceProvider(Resolver):
    def __init__(self, descriptors: dict[type[Any], ServiceDescriptor]) -> None:
        self._descriptors = descriptors
        self._singletons: dict[type[Any], Any] = {}

    def create_scope(self) -> ServiceScope:
        return ServiceScope(self)

    def registered(self, service_type: type[Any]) -> bool:
        return service_type in self._descriptors

    def resolve(self, service_type: type[Any]) -> Any:
        descriptor = self._get_descriptor(service_type)
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if service_type not in self._singletons:
                self._singletons[service_type] = descriptor.factory(self)
            return self._singletons[service_type]
        if descriptor.lifetime == ServiceLifetime.SCOPED:
            raise RuntimeError(f"Scoped service {service_type.__name__} requires a scope")
        return descriptor.factory(self)

    def construct(self, implementation_type: type[Any]) -> Any:
        return _construct_instance(self, implementation_type)

    def _get_descriptor(self, service_type: type[Any]) -> ServiceDescriptor:
        descriptor = self._descriptors.get(service_type)
        if descriptor is None:
            raise KeyError(f"Service {service_type.__name__} is not registered")
        return descriptor


class ServiceScope(Resolver):
    def __init__(self, provider: ServiceProvider) -> None:
        self._provider = provider
        self._instances: dict[type[Any], Any] = {}

    def resolve(self, service_type: type[Any]) -> Any:
        descriptor = self._provider._get_descriptor(service_type)
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self._provider.resolve(service_type)
        if descriptor.lifetime == ServiceLifetime.SCOPED:
            if service_type not in self._instances:
                self._instances[service_type] = descriptor.factory(self)
            return self._instances[service_type]
        return descriptor.factory(self)

    def construct(self, implementation_type: type[Any]) -> Any:
        return _construct_instance(self, implementation_type)

    def registered(self, service_type: type[Any]) -> bool:
        return self._provider.registered(service_type)

    def dispose(self) -> None:
        for instance in self._instances.values():
            close = getattr(instance, "close", None)
            if callable(close):
                close()
        self._instances.clear()


def _construct_instance(resolver: Resolver, implementation_type: type[Any]) -> Any:
    signature = inspect.signature(implementation_type.__init__)
    type_hints = get_type_hints(implementation_type.__init__)
    kwargs: dict[str, Any] = {}

    for name, parameter in signature.parameters.items():
        if name == "self":
            continue
        if parameter.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
            continue
        annotation = type_hints.get(name, parameter.annotation)
        if annotation is inspect._empty:
            if parameter.default is inspect._empty:
                raise TypeError(f"Cannot resolve parameter '{name}' for {implementation_type.__name__}")
            continue
        try:
            kwargs[name] = resolver.resolve(annotation)
        except KeyError:
            if parameter.default is inspect._empty:
                raise
    return implementation_type(**kwargs)
