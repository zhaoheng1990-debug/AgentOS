"""Thin composition root for pluggable AgentOS cognitive runtime modules."""

from __future__ import annotations

from typing import Any, Protocol


COGNITIVE_MODULE_REGISTRY_VERSION = "cognitive_module_registry_v0_1"


class CognitiveRuntimeModule(Protocol):
    module_id: str
    capabilities: tuple[str, ...]


class CognitiveModuleRegistry:
    """Install and discover modules without centralizing their behavior."""

    module_id = COGNITIVE_MODULE_REGISTRY_VERSION
    capabilities = ("cognitive_module_composition",)

    def __init__(self) -> None:
        self._modules: dict[str, CognitiveRuntimeModule] = {}

    def register(self, module: CognitiveRuntimeModule) -> None:
        module_id = getattr(module, "module_id", "")
        capabilities = getattr(module, "capabilities", ())
        if not module_id or not capabilities:
            raise ValueError("runtime_module_contract_incomplete")
        if module_id in self._modules:
            raise ValueError(f"duplicate_runtime_module_id:{module_id}")
        self._modules[module_id] = module

    def unregister(self, module_id: str) -> CognitiveRuntimeModule:
        try:
            return self._modules.pop(module_id)
        except KeyError as exc:
            raise KeyError(f"runtime_module_not_registered:{module_id}") from exc

    def resolve(self, capability: str) -> tuple[CognitiveRuntimeModule, ...]:
        return tuple(
            module
            for module in self._modules.values()
            if capability in module.capabilities
        )

    def require_one(self, capability: str) -> CognitiveRuntimeModule:
        matches = self.resolve(capability)
        if not matches:
            raise KeyError(f"runtime_capability_not_installed:{capability}")
        if len(matches) != 1:
            raise RuntimeError(f"runtime_capability_ambiguous:{capability}")
        return matches[0]

    def contract(self) -> dict[str, Any]:
        modules = [
            {
                "module_id": module.module_id,
                "capabilities": list(module.capabilities),
            }
            for module in self._modules.values()
        ]
        return {
            "registry_id": self.module_id,
            "module_count": len(modules),
            "modules": modules,
            "behavior_owner": "installed_modules",
            "centralized_cognition_owner": False,
        }
