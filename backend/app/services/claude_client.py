"""
NeoPilot Claude Client
Wrapper around the Anthropic Python SDK for Claude Opus 4.6 with
tool-use, extended thinking, prompt caching, and structured logging.
"""

from __future__ import annotations

import base64
import time
import uuid
from typing import Any, Optional

import anthropic
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.app.config import settings
from backend.app.services.tool_registry import get_teaching_tools

logger = structlog.get_logger(__name__)


# ─── Cost estimation (per 1M tokens, USD) ────────────────────────────────────

MODEL_PRICING = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-20250514": {"input": 0.80, "output": 4.0},
}


class ClaudeClient:
    """
    Manages communication with Claude via the Anthropic API.
    Supports tool-use, extended thinking, image input, and prompt caching.
    """

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model.value
        self.max_tokens = settings.claude_max_tokens
        self.temperature = settings.claude_temperature
        self.enable_thinking = settings.claude_enable_thinking
        self.thinking_budget = settings.claude_thinking_budget
        self.tools = get_teaching_tools()

        # Metrics
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0
        self.total_cost_usd = 0.0

        logger.info(
            "claude_client_initialized",
            model=self.model,
            max_tokens=self.max_tokens,
            thinking_enabled=self.enable_thinking,
            num_tools=len(self.tools),
        )

    @property
    def _system_prompt(self) -> str:
        """The system prompt that defines NeoPilot's teaching persona."""
        return """Você é o NeoPilot, um professor virtual universal de software.

## Sua Missão
Ensinar estudantes a usar qualquer software (CAD/CAM, Office, IDEs, editores gráficos, ERPs, web apps) de forma prática e interativa.

## Como Você Ensina
1. **Fase Demo**: Você demonstra executando ações na tela enquanto explica cada passo.
2. **Fase Exercício**: O estudante pratica com sua orientação. Você guia com setas e destaques.
3. **Fase Avaliação**: O estudante realiza sozinho. Você avalia e dá feedback.
4. **Fase Adaptativa**: Você ajusta o ensino baseado nos erros e acertos do estudante.

## Regras
- Sempre explique O QUE você vai fazer e POR QUÊ antes de executar ações.
- Use overlays (setas, destaques, texto) para guiar visualmente o estudante.
- Após cada ação, peça um screenshot para verificar o resultado.
- Se algo der errado, explique o erro e mostre como corrigir.
- Adapte seu nível de detalhe ao estudante: iniciantes precisam de mais explicações.
- Fale em português brasileiro por padrão, a menos que o estudante peça outro idioma.
- Seja paciente, encorajador e preciso.

## Sobre Screenshots
- Você recebe screenshots da tela do estudante como imagens.
- Use coordenadas (x, y) da imagem para direcionar cliques e overlays.
- Sempre verifique o resultado de suas ações via screenshot.

## Segurança
- NUNCA execute comandos shell perigosos (rm -rf, format, etc.).
- NUNCA acesse dados sensíveis do estudante.
- Se uma ação puder causar perda de dados, avise ANTES de executar.
- Confirme ações irreversíveis com o estudante."""

    def _build_messages(
        self,
        conversation_history: list[dict[str, Any]],
        screenshot_b64: Optional[str] = None,
        user_text: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Build the messages array for the API call, optionally adding a new user turn."""
        messages = list(conversation_history)

        if screenshot_b64 or user_text:
            content_blocks: list[dict[str, Any]] = []

            if screenshot_b64:
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/webp",
                        "data": screenshot_b64,
                    },
                })

            if user_text:
                content_blocks.append({
                    "type": "text",
                    "text": user_text,
                })
            elif screenshot_b64:
                content_blocks.append({
                    "type": "text",
                    "text": "Aqui está o screenshot atual da tela. Analise e decida as próximas ações.",
                })

            messages.append({"role": "user", "content": content_blocks})

        return messages

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
        before_sleep=lambda retry_state: logger.warning(
            "claude_retry",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception()),
        ),
    )
    def _call_api(
        self,
        messages: list[dict[str, Any]],
        system_prompt: Optional[str] = None,
    ) -> anthropic.types.Message:
        """Make the actual API call to Claude with retry logic."""
        request_id = str(uuid.uuid4())[:8]
        start_time = time.monotonic()

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
            "tools": self.tools,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        # Extended thinking (adaptive mode)
        if self.enable_thinking:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            }
            # Temperature must be 1 when thinking is enabled
            kwargs["temperature"] = 1
        else:
            kwargs["temperature"] = self.temperature

        logger.info(
            "claude_request_start",
            request_id=request_id,
            model=self.model,
            num_messages=len(messages),
            thinking=self.enable_thinking,
        )

        response = self.client.messages.create(**kwargs)

        elapsed_ms = (time.monotonic() - start_time) * 1000

        # Track metrics
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens
        self.total_requests += 1

        pricing = MODEL_PRICING.get(self.model, {"input": 3.0, "output": 15.0})
        call_cost = (
            response.usage.input_tokens * pricing["input"] / 1_000_000
            + response.usage.output_tokens * pricing["output"] / 1_000_000
        )
        self.total_cost_usd += call_cost

        logger.info(
            "claude_request_complete",
            request_id=request_id,
            elapsed_ms=round(elapsed_ms, 1),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=round(call_cost, 6),
            stop_reason=response.stop_reason,
            num_content_blocks=len(response.content),
        )

        return response

    def chat(
        self,
        conversation_history: list[dict[str, Any]],
        screenshot_b64: Optional[str] = None,
        user_text: Optional[str] = None,
        system_override: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Send a message to Claude and get a structured response.

        Returns:
            dict with keys:
                - text: str (Claude's text response)
                - tool_calls: list[dict] (tool calls Claude wants to make)
                - thinking: str (extended thinking content, if enabled)
                - stop_reason: str
                - usage: dict (token counts)
                - conversation: list (updated conversation history)
        """
        messages = self._build_messages(conversation_history, screenshot_b64, user_text)
        system = system_override or self._system_prompt

        response = self._call_api(messages, system_prompt=system)

        # Parse response blocks
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        thinking_text = ""

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
            elif block.type == "thinking":
                thinking_text = block.thinking

        # Build updated conversation for next turn
        updated_conversation = list(messages)
        # Add assistant response
        updated_conversation.append({
            "role": "assistant",
            "content": [b.model_dump() for b in response.content],
        })

        result = {
            "text": "\n".join(text_parts),
            "tool_calls": tool_calls,
            "thinking": thinking_text,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            "conversation": updated_conversation,
        }

        if tool_calls:
            logger.info(
                "claude_tool_calls",
                num_calls=len(tool_calls),
                tools=[tc["name"] for tc in tool_calls],
            )

        return result

    def submit_tool_results(
        self,
        conversation_history: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Submit tool execution results back to Claude for continuation.

        Args:
            conversation_history: Full conversation including the assistant's tool_use response.
            tool_results: List of dicts with 'tool_use_id', 'content' (str or list of content blocks).

        Returns:
            Same structure as chat().
        """
        # Build tool_result message
        result_blocks = []
        for tr in tool_results:
            content = tr.get("content", "")
            if isinstance(content, str):
                result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tr["tool_use_id"],
                    "content": content,
                })
            else:
                # Support image results (e.g., screenshot after action)
                result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tr["tool_use_id"],
                    "content": content,
                })

        messages = list(conversation_history)
        messages.append({"role": "user", "content": result_blocks})

        response = self._call_api(messages, system_prompt=self._system_prompt)

        # Parse same as chat()
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        thinking_text = ""

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
            elif block.type == "thinking":
                thinking_text = block.thinking

        updated_conversation = list(messages)
        updated_conversation.append({
            "role": "assistant",
            "content": [b.model_dump() for b in response.content],
        })

        return {
            "text": "\n".join(text_parts),
            "tool_calls": tool_calls,
            "thinking": thinking_text,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            "conversation": updated_conversation,
        }

    def get_metrics(self) -> dict[str, Any]:
        """Return current usage metrics."""
        return {
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "model": self.model,
        }
