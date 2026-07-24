"""Durable runtime task lifecycle and recovery model."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from .cognitive_work_models import CognitiveWorkControlDecision


TASK_STATES = {
    "INTAKE",
    "PLANNED",
    "RUNNING",
    "PAUSED",
    "WAITING",
    "CANCELLED",
    "FAILED",
    "ROLLING_BACK",
    "ROLLED_BACK",
    "COMPLETED",
    "BLOCKED",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


@dataclass
class TaskRunState:
    run_id: str
    task_kind: str
    state: str = "INTAKE"
    stage_graph: list[str] = field(default_factory=list)
    current_stage: str = ""
    checkpoints: dict[str, dict[str, Any]] = field(default_factory=dict)
    receipts: list[dict[str, Any]] = field(default_factory=list)
    budget: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 0
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_kind": self.task_kind,
            "state": self.state,
            "stage_graph": self.stage_graph,
            "current_stage": self.current_stage,
            "checkpoints": self.checkpoints,
            "receipts": self.receipts,
            "budget": self.budget,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaskRunState":
        return cls(**payload)


class RuntimeTaskLifecycle:
    """Kernel-owned lifecycle; harnesses remain bounded action adapters."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.runs_dir = self.root / "runs"
        self.runs_dir.mkdir(exist_ok=True)

    def intake(self, run_id: str, task_kind: str, *, budget: dict[str, Any] | None = None, timeout_seconds: int = 0) -> TaskRunState:
        state = TaskRunState(run_id=run_id, task_kind=task_kind, budget=budget or {}, timeout_seconds=timeout_seconds)
        return self._save(state, "intake")

    def plan(self, run_id: str, stage_graph: list[str]) -> TaskRunState:
        state = self.load(run_id)
        state.stage_graph = list(stage_graph)
        state.current_stage = stage_graph[0] if stage_graph else ""
        state.state = "PLANNED"
        return self._save(state, "plan")

    def start(self, run_id: str) -> TaskRunState:
        state = self.load(run_id)
        state.state = "RUNNING"
        return self._save(state, "start")

    def checkpoint(self, run_id: str, stage: str, payload: dict[str, Any]) -> TaskRunState:
        state = self.load(run_id)
        state.checkpoints[stage] = {
            "payload": payload,
            "checkpoint_hash": _hash_payload(payload),
            "created_at": _utc_now(),
        }
        state.current_stage = stage
        receipt = self._receipt(run_id, "checkpoint", {"stage": stage, "checkpoint_hash": state.checkpoints[stage]["checkpoint_hash"]})
        state.receipts.append(receipt)
        return self._save(state, "checkpoint")

    def pause(self, run_id: str, reason: str = "") -> TaskRunState:
        return self._transition(run_id, "PAUSED", "pause", {"reason": reason})

    def resume(self, run_id: str) -> TaskRunState:
        return self._transition(run_id, "RUNNING", "resume", {})

    def wait(self, run_id: str, reason: str = "") -> TaskRunState:
        return self._transition(run_id, "WAITING", "wait", {"reason": reason})

    def cancel(self, run_id: str, reason: str = "") -> TaskRunState:
        return self._transition(run_id, "CANCELLED", "cancel", {"reason": reason})

    def fail(self, run_id: str, reason: str) -> TaskRunState:
        return self._transition(run_id, "FAILED", "fail", {"reason": reason})

    def block(self, run_id: str, reason: str) -> TaskRunState:
        return self._transition(run_id, "BLOCKED", "block", {"reason": reason})

    def complete(self, run_id: str) -> TaskRunState:
        return self._transition(run_id, "COMPLETED", "complete", {})

    def apply_cognitive_work_control(
        self,
        run_id: str,
        control: CognitiveWorkControlDecision,
    ) -> TaskRunState:
        """Bind Kernel cognitive-work control to the durable task schedule."""
        state = self.load(run_id)
        if state.run_id != control.trajectory_id:
            raise ValueError("cognitive_work_task_run_binding_invalid")
        target_state = {
            "CONTINUE": "RUNNING",
            "STOP_SUFFICIENT": "PAUSED",
            "STOP_LOW_MARGINAL": "PAUSED",
            "REORGANIZE": "PLANNED",
            "ESCALATE": "WAITING",
            "BLOCK_BUDGET": "BLOCKED",
        }[control.action]
        return self._transition(
            run_id,
            target_state,
            "cognitive_work_schedule",
            {
                "action": control.action,
                "reason": control.reason,
                "cognitive_work_control_hash": control.decision_hash,
                "allow_additional_round": control.allow_additional_round,
            },
        )

    def rollback(self, run_id: str, target_stage: str) -> dict[str, Any]:
        state = self.load(run_id)
        state.state = "ROLLING_BACK"
        self._save(state, "rolling_back")
        checkpoint = state.checkpoints.get(target_stage)
        receipt = self._receipt(run_id, "rollback", {"target_stage": target_stage, "checkpoint": checkpoint})
        state.receipts.append(receipt)
        state.state = "ROLLED_BACK"
        state.current_stage = target_stage
        self._save(state, "rolled_back")
        return receipt

    def active_runs(self) -> list[dict[str, Any]]:
        active = []
        for path in self.runs_dir.glob("*.json"):
            state = TaskRunState.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if state.state in {"INTAKE", "PLANNED", "RUNNING", "PAUSED", "WAITING", "ROLLING_BACK", "BLOCKED"}:
                active.append(state.as_dict())
        return sorted(active, key=lambda item: item["updated_at"])

    def load(self, run_id: str) -> TaskRunState:
        path = self.runs_dir / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"task_run_not_found:{run_id}")
        return TaskRunState.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _transition(self, run_id: str, state_name: str, event_type: str, payload: dict[str, Any]) -> TaskRunState:
        if state_name not in TASK_STATES:
            raise ValueError(f"unknown_task_state:{state_name}")
        state = self.load(run_id)
        state.state = state_name
        state.receipts.append(self._receipt(run_id, event_type, payload))
        return self._save(state, event_type)

    def _save(self, state: TaskRunState, event_type: str) -> TaskRunState:
        state.updated_at = _utc_now()
        path = self.runs_dir / f"{state.run_id}.json"
        path.write_text(json.dumps(state.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return state

    @staticmethod
    def _receipt(run_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        receipt = {
            "run_id": run_id,
            "event_type": event_type,
            "payload": payload,
            "created_at": _utc_now(),
        }
        receipt["receipt_hash"] = _hash_payload(receipt)
        return receipt
