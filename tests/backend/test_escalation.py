
import pytest
from app.orchestrator.escalation import should_escalate

class TestEscalation:

    def test_escalation_handoff_state(self):
        """Already in handoff state -> escalate"""
        state = {"current_state": "HUMAN_HANDOFF"}
        assert should_escalate(state) is True

    def test_escalation_error(self):
        """Error present -> escalate"""
        state = {"last_error": "Some error"}
        assert should_escalate(state) is True

    def test_escalation_too_many_steps(self):
        """Too many total agent steps -> escalate"""
        state = {"attempts": {"a": 3, "b": 3}} # Total 6 > 5
        assert should_escalate(state) is True

    def test_no_escalation(self):
        """Normal state -> no escalation"""
        state = {
            "current_state": "COMPLETED",
            "last_error": None,
            "attempts": {"a": 1}
        }
        assert should_escalate(state) is False
