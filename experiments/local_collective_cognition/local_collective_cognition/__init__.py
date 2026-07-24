"""Optional workstation-local collective cognition experiment support."""

from .cognitive_work_execution_bridge import (
    COGNITIVE_WORK_EXECUTION_BRIDGE_VERSION,
    CognitiveWorkExecutionBridge,
    CognitiveWorkExecutionBridgeReceipt,
)
from .frozen_answer_harness import (
    FROZEN_ANSWER_BENCHMARK_VERSION,
    BenchmarkAnswerTruth,
    BenchmarkProviderInputAudit,
    BenchmarkQuestion,
    FrozenAnswerBenchmarkHarness,
    FrozenAnswerBenchmarkReceipt,
)
from .local_transformers_provider import (
    LOCAL_TRANSFORMERS_ADAPTER_VERSION,
    LocalStructuredGeneration,
    LocalTransformersJsonAdapter,
    LocalTransformersModelSpec,
    LocalTransformersResidentPool,
)
from .local_constrained_tool_provider import (
    CONSTRAINED_TOOL_TASK_KIND,
    ConstrainedTransformersResidentPool,
    LocalConstrainedToolAdapter,
)
from .local_hierarchical_tool_provider import (
    HIERARCHICAL_TOOL_TASK_KIND,
    HierarchicalTransformersResidentPool,
    LocalHierarchicalToolAdapter,
)
from .local_plan_intent_provider import (
    PLAN_INTENT_TASK_KIND,
    LocalPlanIntentAdapter,
    PlanIntentTransformersResidentPool,
)
from .local_problem_formulation_provider import (
    PROBLEM_FORMULATION_TASK_KIND,
    LocalProblemFormulationAdapter,
)
from .local_problem_dialogue_provider import (
    PROBLEM_CRITIQUE_TASK_KIND,
    PROBLEM_REVISION_TASK_KIND,
    LocalProblemDialogueAdapter,
)
from .ephemeral_structural_prior_contracts import STRUCTURAL_PRIOR_TASK_KIND
from .contrastive_quality_contracts import QUALITY_TASK_KIND
from .local_contrastive_quality_provider import LocalContrastiveQualityAdapter
from .local_structure_packet_provider import LocalQualityGatedStructureAdapter
from .ollama_provider import OLLAMA_JSON_ADAPTER_VERSION, OllamaJsonAdapter
from .provider_telemetry import (
    PROVIDER_TELEMETRY_VERSION,
    ProviderInvocationTelemetry,
    ProviderTelemetryLedger,
)
from .collective_protocol import PILOT_TASK_KINDS, LocalCollectiveCognitionProtocol
from .pilot_benchmark import PILOT_BENCHMARK_ID, build_pilot_harness

LOCAL_COLLECTIVE_COGNITION_EXPERIMENT_VERSION = "0.44.0"

__all__ = [
    "BenchmarkAnswerTruth",
    "BenchmarkProviderInputAudit",
    "BenchmarkQuestion",
    "COGNITIVE_WORK_EXECUTION_BRIDGE_VERSION",
    "CognitiveWorkExecutionBridge",
    "CognitiveWorkExecutionBridgeReceipt",
    "CONSTRAINED_TOOL_TASK_KIND",
    "ConstrainedTransformersResidentPool",
    "FROZEN_ANSWER_BENCHMARK_VERSION",
    "HIERARCHICAL_TOOL_TASK_KIND",
    "HierarchicalTransformersResidentPool",
    "FrozenAnswerBenchmarkHarness",
    "FrozenAnswerBenchmarkReceipt",
    "LOCAL_COLLECTIVE_COGNITION_EXPERIMENT_VERSION",
    "LOCAL_TRANSFORMERS_ADAPTER_VERSION",
    "LocalStructuredGeneration",
    "LocalConstrainedToolAdapter",
    "LocalHierarchicalToolAdapter",
    "LocalPlanIntentAdapter",
    "LocalProblemFormulationAdapter",
    "LocalProblemDialogueAdapter",
    "LocalContrastiveQualityAdapter",
    "LocalQualityGatedStructureAdapter",
    "LocalTransformersJsonAdapter",
    "LocalTransformersModelSpec",
    "LocalTransformersResidentPool",
    "OLLAMA_JSON_ADAPTER_VERSION",
    "PLAN_INTENT_TASK_KIND",
    "PROBLEM_FORMULATION_TASK_KIND",
    "PROBLEM_CRITIQUE_TASK_KIND",
    "PROBLEM_REVISION_TASK_KIND",
    "STRUCTURAL_PRIOR_TASK_KIND",
    "QUALITY_TASK_KIND",
    "PlanIntentTransformersResidentPool",
    "OllamaJsonAdapter",
    "PROVIDER_TELEMETRY_VERSION",
    "ProviderInvocationTelemetry",
    "ProviderTelemetryLedger",
    "PILOT_BENCHMARK_ID",
    "PILOT_TASK_KINDS",
    "LocalCollectiveCognitionProtocol",
    "build_pilot_harness",
]
