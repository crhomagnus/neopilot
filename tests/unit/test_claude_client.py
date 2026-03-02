"""Tests for the Claude client — mock Anthropic API calls."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from backend.app.services.claude_client import ClaudeClient, MODEL_PRICING


class MockUsage:
    def __init__(self, input_tokens=100, output_tokens=50):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class MockTextBlock:
    def __init__(self, text="Hello"):
        self.type = "text"
        self.text = text

    def model_dump(self):
        return {"type": "text", "text": self.text}


class MockToolUseBlock:
    def __init__(self, id="tool_1", name="click", input_data=None):
        self.type = "tool_use"
        self.id = id
        self.name = name
        self.input = input_data or {"x": 100, "y": 200}

    def model_dump(self):
        return {"type": "tool_use", "id": self.id, "name": self.name, "input": self.input}


class MockThinkingBlock:
    def __init__(self, thinking="Let me think..."):
        self.type = "thinking"
        self.thinking = thinking

    def model_dump(self):
        return {"type": "thinking", "thinking": self.thinking}


class MockResponse:
    def __init__(self, content=None, stop_reason="end_turn", usage=None):
        self.content = content or [MockTextBlock()]
        self.stop_reason = stop_reason
        self.usage = usage or MockUsage()


@pytest.fixture
def mock_anthropic():
    """Fixture that patches the Anthropic client."""
    with patch("backend.app.services.claude_client.anthropic.Anthropic") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def claude_client(mock_anthropic):
    """Create a ClaudeClient with mocked Anthropic."""
    with patch("backend.app.services.claude_client.settings") as mock_settings:
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.claude_model = MagicMock(value="claude-sonnet-4-20250514")
        mock_settings.claude_max_tokens = 4096
        mock_settings.claude_temperature = 0.1
        mock_settings.claude_enable_thinking = False
        mock_settings.claude_thinking_budget = 10000
        mock_settings.claude_enable_caching = False
        client = ClaudeClient()
    return client


class TestClaudeClient:

    def test_initialization(self, claude_client):
        """Client initializes with correct model and settings."""
        assert claude_client.model == "claude-sonnet-4-20250514"
        assert claude_client.max_tokens == 4096
        assert claude_client.total_requests == 0

    def test_chat_returns_text(self, claude_client, mock_anthropic):
        """Basic chat returns text response."""
        mock_anthropic.messages.create.return_value = MockResponse(
            content=[MockTextBlock("Olá, estudante!")],
            stop_reason="end_turn",
            usage=MockUsage(200, 100),
        )

        result = claude_client.chat(
            conversation_history=[],
            user_text="Olá!",
        )

        assert result["text"] == "Olá, estudante!"
        assert result["stop_reason"] == "end_turn"
        assert result["tool_calls"] == []
        assert len(result["conversation"]) > 0

    def test_chat_returns_tool_calls(self, claude_client, mock_anthropic):
        """Chat with tool calls returns parsed tool data."""
        mock_anthropic.messages.create.return_value = MockResponse(
            content=[
                MockTextBlock("Vou clicar no botão."),
                MockToolUseBlock("tool_123", "click", {"x": 500, "y": 300}),
            ],
            stop_reason="tool_use",
            usage=MockUsage(300, 150),
        )

        result = claude_client.chat(
            conversation_history=[],
            user_text="Onde está o botão?",
        )

        assert result["text"] == "Vou clicar no botão."
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "click"
        assert result["tool_calls"][0]["input"] == {"x": 500, "y": 300}
        assert result["stop_reason"] == "tool_use"

    def test_chat_with_thinking(self, claude_client, mock_anthropic):
        """Chat with thinking block returns thinking text."""
        mock_anthropic.messages.create.return_value = MockResponse(
            content=[
                MockThinkingBlock("Preciso analisar a tela..."),
                MockTextBlock("Vejo o menu aqui."),
            ],
            stop_reason="end_turn",
            usage=MockUsage(500, 200),
        )

        result = claude_client.chat(
            conversation_history=[],
            user_text="O que há na tela?",
        )

        assert result["thinking"] == "Preciso analisar a tela..."
        assert result["text"] == "Vejo o menu aqui."

    def test_token_tracking(self, claude_client, mock_anthropic):
        """Token usage is tracked across calls."""
        mock_anthropic.messages.create.return_value = MockResponse(
            usage=MockUsage(100, 50),
        )

        claude_client.chat(conversation_history=[], user_text="Test 1")
        claude_client.chat(conversation_history=[], user_text="Test 2")

        metrics = claude_client.get_metrics()
        assert metrics["total_requests"] == 2
        assert metrics["total_input_tokens"] == 200
        assert metrics["total_output_tokens"] == 100

    def test_cost_estimation(self, claude_client, mock_anthropic):
        """Cost is calculated based on model pricing."""
        mock_anthropic.messages.create.return_value = MockResponse(
            usage=MockUsage(1_000_000, 100_000),
        )

        claude_client.chat(conversation_history=[], user_text="Big request")

        metrics = claude_client.get_metrics()
        assert metrics["total_cost_usd"] > 0

    def test_submit_tool_results(self, claude_client, mock_anthropic):
        """Tool results can be submitted back to Claude."""
        mock_anthropic.messages.create.return_value = MockResponse(
            content=[MockTextBlock("Ação executada com sucesso!")],
            stop_reason="end_turn",
        )

        result = claude_client.submit_tool_results(
            conversation_history=[
                {"role": "user", "content": "Test"},
                {"role": "assistant", "content": [MockToolUseBlock().model_dump()]},
            ],
            tool_results=[{
                "tool_use_id": "tool_1",
                "content": "Clicked at (100, 200)",
            }],
        )

        assert result["text"] == "Ação executada com sucesso!"
        assert result["stop_reason"] == "end_turn"

    def test_build_messages_with_screenshot(self, claude_client):
        """Messages include image content block when screenshot provided."""
        messages = claude_client._build_messages(
            conversation_history=[],
            screenshot_b64="base64data",
            user_text="Analise a tela.",
        )

        assert len(messages) == 1
        content = messages[0]["content"]
        assert content[0]["type"] == "image"
        assert content[0]["source"]["data"] == "base64data"
        assert content[1]["type"] == "text"
        assert content[1]["text"] == "Analise a tela."


class TestModelPricing:

    def test_pricing_has_expected_models(self):
        assert "claude-opus-4-6" in MODEL_PRICING
        assert "claude-sonnet-4-20250514" in MODEL_PRICING

    def test_pricing_format(self):
        for model, prices in MODEL_PRICING.items():
            assert "input" in prices
            assert "output" in prices
            assert prices["input"] > 0
            assert prices["output"] > 0
