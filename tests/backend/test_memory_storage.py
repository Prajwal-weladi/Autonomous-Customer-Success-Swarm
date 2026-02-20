
import pytest
from app.storage.memory import _STORE, _HISTORY, load_state, save_state, clear_state, get_all_conversations, append_to_history, get_history

class TestMemoryStorage:

    def test_save_and_load_state(self):
        """Test saving and retrieving conversation state"""
        cid = "test-123"
        data = {"status": "active", "intent": "refund"}
        
        save_state(cid, data)
        loaded = load_state(cid)
        
        assert loaded == data
        assert loaded["status"] == "active"

    def test_load_non_existent_state(self):
        """Loading unknown state should return None"""
        assert load_state("unknown-id") is None

    def test_clear_state(self):
        """Test clearing state from memory"""
        cid = "test-clear"
        save_state(cid, {"foo": "bar"})
        
        clear_state(cid)
        assert load_state(cid) is None
        
    def test_clear_non_existent_state(self):
        """Clearing unknown state should not crash"""
        try:
            clear_state("unknown-clear")
        except Exception as e:
            pytest.fail(f"clear_state raised exception: {e}")

    def test_get_all_conversations(self):
        """Test listing all conversation IDs"""
        _STORE.clear()
        save_state("c1", {})
        save_state("c2", {})
        
        # Order not guaranteed in dict keys
        ids = get_all_conversations()
        assert len(ids) == 2
        assert "c1" in ids
        assert "c2" in ids

    def test_history_management(self):
        """Test appending and retrieving conversation history"""
        cid = "hist-1"
        append_to_history(cid, "user", "Hello")
        append_to_history(cid, "assistant", "Hi there")
        
        hist = get_history(cid)
        assert len(hist) == 2
        assert hist[0] == {"role": "user", "content": "Hello"}
        assert hist[1] == {"role": "assistant", "content": "Hi there"}
        
    def test_history_trimming(self):
        """Test history trimming to max_turns"""
        cid = "hist-trim"
        # Append 25 messages, max is 20 default
        for i in range(25):
            append_to_history(cid, "user", f"msg-{i}")
            
        hist = get_history(cid)
        assert len(hist) == 20
        # Should keep newest, so last message should be msg-24
        assert hist[-1]["content"] == "msg-24"
        # Oldest kept should be msg-5 (since 0-4 dropped)
        assert hist[0]["content"] == "msg-5"
