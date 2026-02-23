"""
Tests for the memory storage module.
Covers load/save/clear state and conversation history (append + trim).
"""
import pytest
from app.storage import memory


@pytest.fixture(autouse=True)
def reset_memory():
    """Wipe in-memory store before each test to prevent cross-test pollution."""
    memory._STORE.clear()
    memory._HISTORY.clear()
    yield
    memory._STORE.clear()
    memory._HISTORY.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# State storage
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateStorage:

    def test_load_returns_none_for_unknown_id(self):
        assert memory.load_state("nonexistent") is None

    def test_save_and_load_roundtrip(self):
        state = {"intent": "refund", "order_id": "12345"}
        memory.save_state("conv-1", state)
        loaded = memory.load_state("conv-1")
        assert loaded == state

    def test_save_overwrites_existing_state(self):
        memory.save_state("conv-2", {"intent": "return"})
        memory.save_state("conv-2", {"intent": "refund"})
        assert memory.load_state("conv-2")["intent"] == "refund"

    def test_clear_removes_state(self):
        memory.save_state("conv-3", {"data": "x"})
        memory.clear_state("conv-3")
        assert memory.load_state("conv-3") is None

    def test_clear_nonexistent_does_not_raise(self):
        memory.clear_state("ghost")  # should not raise

    def test_get_all_conversations(self):
        memory.save_state("conv-a", {})
        memory.save_state("conv-b", {})
        all_ids = memory.get_all_conversations()
        assert "conv-a" in all_ids
        assert "conv-b" in all_ids

    def test_isolated_between_different_conversations(self):
        memory.save_state("conv-x", {"intent": "cancel"})
        memory.save_state("conv-y", {"intent": "exchange"})
        assert memory.load_state("conv-x")["intent"] == "cancel"
        assert memory.load_state("conv-y")["intent"] == "exchange"


# ═══════════════════════════════════════════════════════════════════════════════
# Conversation history
# ═══════════════════════════════════════════════════════════════════════════════

class TestConversationHistory:

    def test_empty_history_for_new_conversation(self):
        assert memory.get_history("new-conv") == []

    def test_append_user_message(self):
        memory.append_to_history("h-1", "user", "Hello")
        history = memory.get_history("h-1")
        assert len(history) == 1
        assert history[0] == {"role": "user", "content": "Hello"}

    def test_append_assistant_message(self):
        memory.append_to_history("h-2", "assistant", "How can I help?")
        history = memory.get_history("h-2")
        assert history[0]["role"] == "assistant"

    def test_multiple_turns_keep_order(self):
        memory.append_to_history("h-3", "user", "Hi")
        memory.append_to_history("h-3", "assistant", "Hello!")
        memory.append_to_history("h-3", "user", "I need a refund")
        history = memory.get_history("h-3")
        assert len(history) == 3
        assert history[0]["content"] == "Hi"
        assert history[2]["content"] == "I need a refund"

    def test_history_trimmed_to_max_turns(self):
        """append_to_history must cap at max_turns (default 20)."""
        for i in range(25):
            memory.append_to_history("h-trim", "user", f"msg {i}", max_turns=20)
        history = memory.get_history("h-trim")
        assert len(history) == 20
        # Oldest messages should have been dropped
        assert history[0]["content"] == "msg 5"
        assert history[-1]["content"] == "msg 24"

    def test_custom_max_turns_respected(self):
        for i in range(10):
            memory.append_to_history("h-small", "user", f"msg {i}", max_turns=5)
        assert len(memory.get_history("h-small")) == 5

    def test_histories_isolated_per_conversation(self):
        memory.append_to_history("ha", "user", "order refund")
        memory.append_to_history("hb", "user", "where is my order")
        assert len(memory.get_history("ha")) == 1
        assert len(memory.get_history("hb")) == 1
        assert memory.get_history("ha")[0]["content"] == "order refund"
