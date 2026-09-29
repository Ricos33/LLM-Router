from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_ab_endpoint():
    # We don't want to actually run the router, we mock it.
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "Mocked Response"
    mock_resp.router_metadata.cost_actual_usd = 0.01
    mock_resp.router_metadata.actual_model = "test-model"
    
    with patch("app.main.router_engine.route_and_execute") as mock_execute:
        # We need async mock for route_and_execute
        import asyncio
        async def async_mock(*args, **kwargs):
            return mock_resp
        mock_execute.side_effect = async_mock
        
        response = client.post("/v1/ab-test", json={
            "system_prompt_a": "A",
            "system_prompt_b": "B",
            "user_prompt": "U",
            "model": "router-auto"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        
        # Check properties
        assert data["results"][0]["variant"] == "A"
        assert data["results"][1]["variant"] == "B"
        assert data["results"][0]["content"] == "Mocked Response"
