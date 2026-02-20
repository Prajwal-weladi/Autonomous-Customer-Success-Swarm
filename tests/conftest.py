
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import logging
import sys
import os

# Add backend to path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), "../backend"))

from app.main import app
from app.storage.memory import _STORE, _HISTORY

# Add frontend to path so we can import frontend modules
sys.path.append(os.path.join(os.path.dirname(__file__), "../frontend"))

# --- FIXTURES ---

@pytest.fixture
def client():
    """FastAPI Test Client"""
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock external dependencies globally to prevent real API calls"""
    with patch("app.agents.triage.agent.ollama") as mock_ollama, \
         patch("app.agents.database.db_service.get_db_session") as mock_db, \
         patch("app.agents.resolution.crm.hubspot_client.requests.patch") as mock_hubspot:
        
        # Setup Ollama mock
        mock_ollama.chat.return_value = {"message": {"content": "{}"}}
        
        yield {
            "ollama": mock_ollama,
            "db": mock_db,
            "hubspot": mock_hubspot
        }

@pytest.fixture
def mock_order_details():
    """Standard mock order details for testing"""
    return {
        "order_id": "12345",
        "user_id": "user_123",
        "product": "Wireless Headphones",
        "size": "N/A",
        "order_date": "2023-10-01",
        "delivered_date": "2023-10-05",
        "status": "Delivered",
        "amount": 1500
    }

@pytest.fixture(autouse=True)
def clear_memory():
    """Clear in-memory storage before each test"""
    _STORE.clear()
    _HISTORY.clear()
    yield

@pytest.fixture
def mock_logger():
    """Mock logger to capture logs if needed"""
    return logging.getLogger("test_logger")
