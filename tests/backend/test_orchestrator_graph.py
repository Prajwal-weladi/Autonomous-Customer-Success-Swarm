
import pytest
from app.orchestrator.graph import should_continue_to_database, should_continue_to_policy, should_continue_to_resolution, should_end

class TestOrchestratorGraph:

    def test_route_triage_to_db(self):
        assert should_continue_to_database({"current_state": "DATA_FETCH"}) == "database"
        assert should_continue_to_database({"current_state": "HUMAN_HANDOFF"}) == "end"
        assert should_continue_to_database({"current_state": "UNKNOWN"}) == "end"

    def test_route_db_to_policy(self):
        assert should_continue_to_policy({"current_state": "POLICY_CHECK"}) == "policy"
        assert should_continue_to_policy({"current_state": "HUMAN_HANDOFF"}) == "end"

    def test_route_policy_to_resolution(self):
        assert should_continue_to_resolution({"current_state": "RESOLUTION"}) == "resolution"
        assert should_continue_to_resolution({"current_state": "HUMAN_HANDOFF"}) == "end"

    def test_route_resolution_to_end(self):
        assert should_end({"current_state": "COMPLETED"}) == "end"
        assert should_end({"current_state": "HUMAN_HANDOFF"}) == "end"
