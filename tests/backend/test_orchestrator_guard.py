
import pytest
from app.orchestrator.guard import agent_guard, MAX_AGENT_CALLS

class TestAgentGuard:

    @pytest.mark.asyncio
    async def test_guard_execution_success(self):
        """Guard allows execution within limits"""
        state = {"attempts": {}}
        
        @agent_guard("test_agent")
        async def mock_agent(s):
            s["executed"] = True
            return s
            
        new_state = await mock_agent(state)
        
        assert new_state["executed"] is True
        assert new_state["attempts"]["test_agent"] == 1
        assert "test_agent" in new_state["agents_called"]

    @pytest.mark.asyncio
    async def test_guard_limit_exceeded(self):
        """Guard blocks execution if limit exceeded"""
        state = {"attempts": {"test_agent": MAX_AGENT_CALLS}}
        
        @agent_guard("test_agent")
        async def mock_agent(s):
            s["executed"] = True
            return s
            
        new_state = await mock_agent(state)
        
        assert "executed" not in new_state
        assert new_state["current_state"] == "HUMAN_HANDOFF"
        assert "exceeded retry limit" in new_state["last_error"]

    @pytest.mark.asyncio
    async def test_guard_error_handling(self):
        """Guard catches and escalates errors"""
        state = {"attempts": {}}
        
        @agent_guard("test_agent")
        async def mock_agent(s):
            raise ValueError("Test error")
            
        new_state = await mock_agent(state)
        
        assert new_state["current_state"] == "HUMAN_HANDOFF"
        assert "Test error" in new_state["last_error"]
