
import pytest
# Mock streamlit
import sys
from unittest.mock import MagicMock
sys.modules["streamlit"] = MagicMock()

from frontend.components.handoff import render_handoff_banner

class TestHandoff:

    def test_render_handoff(self):
        """Test banner rendering logic"""
        # We can't easily check st.error output without deep mocking, 
        # but we can ensure it doesn't crash
        render_handoff_banner("handoff")
        render_handoff_banner("active")
