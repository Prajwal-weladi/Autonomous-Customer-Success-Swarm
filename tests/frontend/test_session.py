
import pytest
from unittest.mock import MagicMock
# Need to mock streamlit before importing session
import sys
from unittest.mock import MagicMock

sys.modules["streamlit"] = MagicMock()
import streamlit as st
from frontend.state.session import new_conversation, init_session

class MockSessionState(dict):
    """Mock Streamlit session state allowing dot access"""
    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        self[key] = value

class TestFrontendSession:

    def setup_method(self):
        st.session_state = MockSessionState()

    def test_new_conversation(self):
        conv = new_conversation()
        assert "conversation_id" in conv
        assert conv["messages"] == []
        assert conv["status"] == "in_progress"

    def test_init_session(self):
        # Reset session state mock
        st.session_state = MockSessionState()
        init_session()
        
        assert "conversations" in st.session_state
        assert len(st.session_state.conversations) == 1
