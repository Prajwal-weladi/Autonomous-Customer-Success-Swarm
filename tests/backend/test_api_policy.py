
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Create a mock RAG service since it's used in startup
# The conftest patch for dependencies might not cover the lifespan context manager fully
# if app is imported before patching. But let's try.

class TestApiPolicy:

    def test_root(self, client: TestClient):
        res = client.get("/")
        assert res.status_code == 200 # Main app root might be 404, but policy root is mounted or router included
        # Wait, policy router is included with prefix? No, check main.py
        # router is included without prefix but routes have /policy/... or /
        # Let's check policy.py: @router.get("/") -> {"message": "Policy RAG Agent API"}
        # But in main.py: app.include_router(policy_router)
        # So it should be at /
        assert "Policy RAG Agent API" in res.json().get("message", "")

    def test_policy_health(self, client: TestClient):
        # We need to ensure rag_service is mocked
        with patch("app.agents.policy.app.rag.service.rag_service.get_health") as mock_health:
            mock_health.return_value = {
                "status": "healthy", 
                "version": "1.0.0",
                "ollama_connected": True,
                "index_loaded": True,
                "documents_indexed": 10
            }
            res = client.get("/policy/health")
            assert res.status_code == 200
            assert res.json()["status"] == "healthy"

    def test_policy_query(self, client: TestClient):
        with patch("app.agents.policy.app.rag.service.rag_service.query") as mock_query:
            # Mock return must match QueryResponse schema (field 'answer')
            mock_query.return_value = {"answer": "Policy info"}
            # We also need to mock _initialized check
            with patch("app.agents.policy.app.rag.service.rag_service._initialized", True):
                res = client.post("/policy/query", json={"query": "refund policy"})
                assert res.status_code == 200
                assert "Policy info" in res.json()["answer"]
