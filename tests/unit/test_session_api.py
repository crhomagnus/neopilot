"""Tests for the Session REST API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager."""
    manager = AsyncMock()
    return manager


@pytest.fixture
def app(mock_session_manager):
    """Create a test FastAPI app with mocked services."""
    from backend.app.main import app as fastapi_app
    from backend.app import api

    # Override the service dependency
    with patch("backend.app.api.session._session_manager", mock_session_manager):
        yield fastapi_app


@pytest.fixture
def client(app):
    """Create a test HTTP client."""
    return TestClient(app)


class TestHealthEndpoint:

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.0.0-alpha"

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NeoPilot Backend"
        assert "docs" in data


class TestSessionStartEndpoint:

    def test_start_session_success(self, client, mock_session_manager):
        """POST /session/start creates a session and returns teaching response."""
        from backend.app.models.schemas import TeachingResponse, SessionPhase

        mock_response = TeachingResponse(
            session_id="test-123",
            message="Olá! Vamos aprender FreeCAD.",
            actions=[],
            overlays=[],
            phase=SessionPhase.DEMO,
            progress_pct=0.0,
        )
        mock_session_manager.create_session.return_value = (MagicMock(), mock_response)

        response = client.post("/session/start", json={
            "app_id": "freecad",
            "task_description": "Basic extrusion in FreeCAD",
            "user_context": {"level": "beginner"},
        })

        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == "test-123"
        assert "Olá" in data["message"]

    def test_start_session_missing_fields(self, client):
        """POST /session/start rejects requests with missing required fields."""
        response = client.post("/session/start", json={
            "app_id": "freecad",
            # Missing task_description
        })
        assert response.status_code == 422

    def test_start_session_short_description(self, client):
        """POST /session/start rejects descriptions shorter than 5 chars."""
        response = client.post("/session/start", json={
            "app_id": "freecad",
            "task_description": "hi",
        })
        assert response.status_code == 422


class TestObserveEndpoint:

    def test_observe_success(self, client, mock_session_manager):
        """POST /session/observe processes screenshot and returns teaching."""
        from backend.app.models.schemas import TeachingResponse, SessionPhase

        mock_response = TeachingResponse(
            session_id="test-123",
            message="Vejo a tela do FreeCAD. Vamos começar.",
            actions=[],
            overlays=[],
            phase=SessionPhase.DEMO,
        )
        mock_session_manager.process_observation.return_value = mock_response

        response = client.post("/session/observe", json={
            "session_id": "test-123",
            "screenshot_b64": "base64encodedimage",
            "text": "What should I do?",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-123"

    def test_observe_session_not_found(self, client, mock_session_manager):
        """POST /session/observe returns 404 for unknown session."""
        mock_session_manager.process_observation.side_effect = ValueError("Session not found")

        response = client.post("/session/observe", json={
            "session_id": "nonexistent",
            "screenshot_b64": "data",
        })

        assert response.status_code == 404


class TestActionResultEndpoint:

    def test_action_result_success(self, client, mock_session_manager):
        """POST /session/action-result reports successful action."""
        from backend.app.models.schemas import TeachingResponse, SessionPhase

        mock_response = TeachingResponse(
            session_id="test-123",
            message="Muito bem! Ação executada corretamente.",
            phase=SessionPhase.EXERCISE,
        )
        mock_session_manager.process_action_result.return_value = mock_response

        response = client.post("/session/action-result", json={
            "session_id": "test-123",
            "action_id": "action-456",
            "success": True,
            "screenshot_after_b64": "afterimage",
        })

        assert response.status_code == 200
        data = response.json()
        assert "Muito bem" in data["message"]

    def test_action_result_failure(self, client, mock_session_manager):
        """POST /session/action-result reports failed action."""
        from backend.app.models.schemas import TeachingResponse

        mock_response = TeachingResponse(
            session_id="test-123",
            message="Parece que o clique não funcionou. Vamos tentar novamente.",
        )
        mock_session_manager.process_action_result.return_value = mock_response

        response = client.post("/session/action-result", json={
            "session_id": "test-123",
            "action_id": "action-789",
            "success": False,
            "error_message": "Element not found",
        })

        assert response.status_code == 200
