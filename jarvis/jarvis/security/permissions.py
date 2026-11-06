# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ask-Before-Acting permission system with tiered risk classes."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class RiskClass(str, Enum):
    READ_ONLY = "read_only"
    APPROVAL_REQUIRED = "approval_required"
    HIGH_RISK = "high_risk"


# Tool name -> risk. Unknown tools default to APPROVAL_REQUIRED.
TOOL_RISK: dict[str, RiskClass] = {
    "answer": RiskClass.READ_ONLY,
    "memory_search": RiskClass.READ_ONLY,
    "memory_read": RiskClass.READ_ONLY,
    "web_search": RiskClass.READ_ONLY,
    "weather": RiskClass.READ_ONLY,
    "list_files": RiskClass.READ_ONLY,
    "read_file": RiskClass.READ_ONLY,
    "summarize_document": RiskClass.READ_ONLY,
    "system_info": RiskClass.READ_ONLY,
    "explain_code": RiskClass.READ_ONLY,
    "git_status": RiskClass.READ_ONLY,
    "git_diff": RiskClass.READ_ONLY,
    "write_file": RiskClass.APPROVAL_REQUIRED,
    "run_command": RiskClass.APPROVAL_REQUIRED,
    "open_url": RiskClass.APPROVAL_REQUIRED,
    "open_app": RiskClass.APPROVAL_REQUIRED,
    "send_message": RiskClass.APPROVAL_REQUIRED,
    "use_microphone": RiskClass.APPROVAL_REQUIRED,
    "use_camera": RiskClass.APPROVAL_REQUIRED,
    "organize_files": RiskClass.APPROVAL_REQUIRED,
    "git_commit": RiskClass.APPROVAL_REQUIRED,
    "memory_write": RiskClass.APPROVAL_REQUIRED,
    "delete_path": RiskClass.HIGH_RISK,
    "install_software": RiskClass.HIGH_RISK,
    "admin_command": RiskClass.HIGH_RISK,
    "modify_system_settings": RiskClass.HIGH_RISK,
    "transfer_private_data": RiskClass.HIGH_RISK,
    "execute_downloaded_script": RiskClass.HIGH_RISK,
    "make_purchase": RiskClass.HIGH_RISK,
    "git_push": RiskClass.HIGH_RISK,
    "deploy": RiskClass.HIGH_RISK,
}


@dataclass
class PendingAction:
    id: str
    tool: str
    risk: RiskClass
    preview: str
    arguments: dict
    created_at: float = field(default_factory=time.time)
    session_only: bool = False


ApprovalCallback = Callable[[PendingAction], bool]


class PermissionGate:
    """Default security mode: Ask Before Acting.

    High-risk actions always require fresh, action-specific approval.
    Session grants never cover HIGH_RISK. Blanket auto-approve cannot
    override HIGH_RISK protections.
    """

    def __init__(self, mode: str = "ask"):
        self.mode = mode if mode in ("ask", "bypass") else "ask"
        self._session_grants: set[str] = set()  # tool names for APPROVAL_REQUIRED only
        self._pending: dict[str, PendingAction] = {}
        self._stopped = threading.Event()
        self._lock = threading.Lock()
        self.approver: ApprovalCallback | None = None

    def stop_all(self) -> None:
        """Emergency stop — deny everything until cleared."""
        self._stopped.set()
        with self._lock:
            self._pending.clear()

    def clear_stop(self) -> None:
        self._stopped.clear()

    @property
    def is_stopped(self) -> bool:
        return self._stopped.is_set()

    def risk_for(self, tool: str) -> RiskClass:
        return TOOL_RISK.get(tool, RiskClass.APPROVAL_REQUIRED)

    def grant_session(self, tool: str) -> None:
        risk = self.risk_for(tool)
        if risk == RiskClass.HIGH_RISK:
            raise ValueError("High-risk tools cannot receive session auto-approval.")
        self._session_grants.add(tool)

    def revoke_session_grants(self) -> None:
        self._session_grants.clear()

    def list_pending(self) -> list[PendingAction]:
        with self._lock:
            return list(self._pending.values())

    def resolve(self, action_id: str, approved: bool) -> PendingAction | None:
        with self._lock:
            return self._pending.pop(action_id, None) if approved or True else None

    def decide(
        self,
        tool: str,
        arguments: dict,
        preview: str,
        *,
        session_only_request: bool = False,
    ) -> tuple[bool, PendingAction | None]:
        """Return (allowed, pending_or_none)."""
        if self._stopped.is_set():
            return False, None

        risk = self.risk_for(tool)
        if risk == RiskClass.READ_ONLY:
            return True, None

        # bypass may auto-allow APPROVAL_REQUIRED, never HIGH_RISK
        if self.mode == "bypass" and risk == RiskClass.APPROVAL_REQUIRED:
            return True, None
        if tool in self._session_grants and risk == RiskClass.APPROVAL_REQUIRED:
            return True, None

        action = PendingAction(
            id=str(uuid.uuid4()),
            tool=tool,
            risk=risk,
            preview=preview,
            arguments=dict(arguments),
            session_only=session_only_request,
        )
        with self._lock:
            self._pending[action.id] = action

        if self.approver is not None:
            ok = bool(self.approver(action))
            with self._lock:
                self._pending.pop(action.id, None)
            if ok and session_only_request and risk != RiskClass.HIGH_RISK:
                self._session_grants.add(tool)
            return ok, action

        # No interactive approver: leave pending for dashboard / deny by default
        return False, action
