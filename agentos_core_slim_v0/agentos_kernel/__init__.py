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
from .constraint_aligned_retention import (
    ConstraintAlignedRetentionDecision,
    ConstraintAlignedRetentionGate,
)
from .group_cognition_eval import (
    CognitionRunObservation,
    GroupCognitionEvaluation,
    GroupCognitionEvalHarness,
)
from .epistemic_review import (
    ClaimCandidate,
    EpistemicReviewDecision,
    EpistemicReviewProtocol,
    ObjectionReceipt,
    ReplicationReceipt,
)
from .credit_ledger import (
    CreditEvent,
    CreditEventStore,
    CreditLedger,
    CreditProfile,
    JsonlCreditEventStore,
)
from .agent_registry import (
    AgentDescriptor,
    AgentRegistry,
    AgentRoleRequirement,
    AgentRuntimeAdapter,
    AgentWorkOrder,
    EnsembleAssignment,
)
from .endogenous_agenda import (
    AgendaCandidate,
    AgendaFeedback,
    AgendaSelection,
    EndogenousAgendaLoop,
    OpenProblem,
)
from .cascading_invalidation import (
    CascadingInvalidationGraph,
    DependencyEdge,
    InvalidationReceipt,
    InvalidationTransition,
    KnowledgeNode,
)
from .cognitive_module_registry import (
    CognitiveModuleRegistry,
    CognitiveRuntimeModule,
)
from .provider_cognition_layer import (
    BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT,
    BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING,
    PASS_MECHANICAL_RUNTIME_OPERATION,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
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
    AGENTOS_CORE_SLIM_FEATURE_SET,
    AGENTOS_CORE_SLIM_PATCH_SEED,
    AGENTOS_CORE_SLIM_VERSION,
)

__all__ = [
    "ALLOWED_CAPABILITIES",
    "AGENTOS_CORE_SLIM_CODENAME",
    "AGENTOS_CORE_SLIM_FEATURE_SET",
    "AGENTOS_CORE_SLIM_PATCH_SEED",
    "AGENTOS_CORE_SLIM_VERSION",
    "AgentDescriptor",
    "AgentRegistry",
    "AgentRoleRequirement",
    "AgentRuntimeAdapter",
    "AgentWorkOrder",
    "AgendaCandidate",
    "AgendaFeedback",
    "AgendaSelection",
    "ArtifactIdentity",
    "ArtifactPointer",
    "ArtifactProjection",
    "ArtifactRelation",
    "ArtifactRevision",
    "ArtifactVersionStore",
    "AutonomousICMEvolutionPolicy",
    "BaselineEvolutionProposalProtocol",
    "BaselineEligibilityGate",
    "CascadingInvalidationGraph",
    "BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT",
    "BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING",
    "FORBIDDEN_CAPABILITIES",
    "CodexToolBridge",
    "ClaimCandidate",
    "CognitiveAssetEntry",
    "CognitiveAssetLedger",
    "ConstraintAlignedRetentionDecision",
    "ConstraintAlignedRetentionGate",
    "CognitionRunObservation",
    "CognitiveModuleRegistry",
    "CognitiveRuntimeModule",
    "CreditEvent",
    "CreditEventStore",
    "CreditLedger",
    "CreditProfile",
    "DependencyEdge",
    "EvidenceAdmissionGate",
    "EvidenceDimensionRegistry",
    "EvidenceDimensionSpec",
    "EpistemicReviewDecision",
    "EpistemicReviewProtocol",
    "EnsembleAssignment",
    "EndogenousAgendaLoop",
    "GroupCognitionEvaluation",
    "GroupCognitionEvalHarness",
    "InvalidationReceipt",
    "InvalidationTransition",
    "JsonlCreditEventStore",
    "KnowledgeNode",
    "ObjectionReceipt",
    "OpenProblem",
    "ProjectScopedDurableStore",
    "PASS_MECHANICAL_RUNTIME_OPERATION",
    "PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT",
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
    "ReplicationReceipt",
    "RetentionDecision",
    "RuntimeTaskLifecycle",
    "ScopeCoverageGate",
    "TASK_STATES",
    "TaskRunState",
    "ToolBridgeBlocked",
    "is_source_audit_excluded",
]
