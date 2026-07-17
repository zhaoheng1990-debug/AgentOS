"""AgentOS CoreSlim kernel-facing primitives."""

from .codex_tool_bridge import (
    ALLOWED_CAPABILITIES,
    FORBIDDEN_CAPABILITIES,
    CodexToolBridge,
    ToolBridgeBlocked,
)
from .autonomous_icm_evolution import (
    AutonomousICMEvolutionPolicy,
    ProjectScopedDurableStore,
)
from .baseline_evolution_proposal import (
    BaselineEvolutionProposalProtocol,
    ProposalQueue,
)
from .provider_cognition_layer import (
    BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING,
    PASS_MECHANICAL_RUNTIME_OPERATION,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    PROVIDER_COGNITION_LAYER_ID,
    ProviderBackedRuntimeCognitionLayer,
)
from .provider_execution_plane import (
    ProviderAdapter,
    ProviderCapabilityProfile,
    ProviderCognitiveTask,
    ProviderFallbackDecision,
    ProviderInvocationReceipt,
    ProviderResultEnvelope,
    ProviderTaskRouter,
)
from .quality_decision_matrix import (
    BaselineEligibilityGate,
    EvidenceAdmissionGate,
    PublicationRetentionGate,
    QualityDecision,
    QualityDecisionMatrix,
    QualityFinding,
    ReaderIntegrityGate,
    ScopeCoverageGate,
)
from .artifact_versioning import (
    ArtifactIdentity,
    ArtifactPointer,
    ArtifactRelation,
    ArtifactRevision,
    ArtifactVersionStore,
    PublicationDecision,
    RetentionDecision,
)
from .task_lifecycle import (
    RuntimeTaskLifecycle,
    TASK_STATES,
    TaskRunState,
)
from .cognitive_asset_ledger import (
    ArtifactProjection,
    CognitiveAssetEntry,
    CognitiveAssetLedger,
)
from .evidence_dimensions import (
    EvidenceDimensionRegistry,
    EvidenceDimensionSpec,
    is_source_audit_excluded,
)
from .version import (
    AGENTOS_CORE_SLIM_CODENAME,
    AGENTOS_CORE_SLIM_PATCH_SEED,
    AGENTOS_CORE_SLIM_VERSION,
)

__all__ = [
    "ALLOWED_CAPABILITIES",
    "AGENTOS_CORE_SLIM_CODENAME",
    "AGENTOS_CORE_SLIM_PATCH_SEED",
    "AGENTOS_CORE_SLIM_VERSION",
    "ArtifactIdentity",
    "ArtifactPointer",
    "ArtifactProjection",
    "ArtifactRelation",
    "ArtifactRevision",
    "ArtifactVersionStore",
    "AutonomousICMEvolutionPolicy",
    "BaselineEvolutionProposalProtocol",
    "BaselineEligibilityGate",
    "BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING",
    "FORBIDDEN_CAPABILITIES",
    "CodexToolBridge",
    "CognitiveAssetEntry",
    "CognitiveAssetLedger",
    "EvidenceAdmissionGate",
    "EvidenceDimensionRegistry",
    "EvidenceDimensionSpec",
    "ProjectScopedDurableStore",
    "PASS_MECHANICAL_RUNTIME_OPERATION",
    "PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT",
    "ProviderAdapter",
    "PROVIDER_COGNITION_LAYER_ID",
    "ProviderBackedRuntimeCognitionLayer",
    "ProviderCapabilityProfile",
    "ProviderCognitiveTask",
    "ProviderFallbackDecision",
    "ProviderInvocationReceipt",
    "ProviderResultEnvelope",
    "ProviderTaskRouter",
    "PublicationDecision",
    "PublicationRetentionGate",
    "ProposalQueue",
    "QualityDecision",
    "QualityDecisionMatrix",
    "QualityFinding",
    "ReaderIntegrityGate",
    "RetentionDecision",
    "RuntimeTaskLifecycle",
    "ScopeCoverageGate",
    "TASK_STATES",
    "TaskRunState",
    "ToolBridgeBlocked",
    "is_source_audit_excluded",
]
