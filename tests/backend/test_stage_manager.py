
import pytest
from app.agents.resolution.crm.stage_manager import get_stage_transition

class TestStageManager:

    def test_stage_transitions(self):
        assert "EXCHANGED" in get_stage_transition("exchange")
        assert "CANCELLED" in get_stage_transition("cancel")
        assert "REFUND_DONE" in get_stage_transition("refund")
        assert "RETURNED" in get_stage_transition("return")
        assert get_stage_transition("unknown") == []
