"""
NeoPilot Web Agent
Controle de navegador via Playwright + WebMCP Bridge.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

from neopilot.core.logger import get_logger

logger = get_logger("web_agent")


@dataclass
class WebMCPTool:
    name: str
    description: str
    parameters: dict[str, Any]
    domain: str


@dataclass
class WebAction:
    action_type: str  # navigate|click|type|scroll|submit|webmcp
    url: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    scroll_direction: str = "down"
    scroll_amount: int = 3


@dataclass
class WebResult:
    success: bool
    method: str  # "webmcp" | "playwright" | "visual"
    data: Any = None
    screenshot_b64: Optional[str] = None
    error: Optional[str] = None
    tokens_saved: int = 0


class WebMCPBridge:
    """Ponte entre navigator.modelContext do site e o agente LangGraph."""

    def __init__(self):
        self._tools: dict[str, WebMCPTool] = {}
        self._active_domain: Optional[str] = None

    async def detect(self, page: Any) -> bool:
        """Detecta suporte WebMCP na página atual."""
        try:
            has_mcp = await page.evaluate(
                "() => typeof navigator !== 'undefined' && "
                "typeof navigator.modelContext !== 'undefined'"
            )
            if has_mcp:
                domain = urlparse(page.url).netloc
                logger.info("WebMCP detectado", domain=domain)
                await self._load_tools(page, domain)
                return True
        except Exception as e:
            logger.debug("WebMCP não disponível", error=str(e))
        return False

    async def _load_tools(self, page: Any, domain: str) -> None:
        """Carrega tools disponíveis no site via WebMCP."""
        try:
            tools_schema = await page.evaluate(
                "() => { try { return navigator.modelContext.getTools(); } "
                "catch(e) { return []; } }"
            )
            self._tools = {}
            for tool in (tools_schema or []):
                t = WebMCPTool(
                    name=tool.get("name", ""),
                    description=tool.get("description", ""),
                    parameters=tool.get("parameters", {}),
                    domain=domain,
                )
                self._tools[t.name] = t
            self._active_domain = domain
            logger.info("WebMCP tools carregadas", count=len(self._tools), domain=domain)
        except Exception as e:
            logger.error("Falha ao carregar WebMCP tools", error=str(e))

    async def call_tool(self, page: Any, tool_name: str, args: dict) -> Any:
        """Invoca uma WebMCP tool diretamente."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' não disponível via WebMCP")
        try:
            result = await page.evaluate(
                f"""(args) => navigator.modelContext.callTool(
                    '{tool_name}', args
                )""",
                args,
            )
            logger.info("WebMCP tool executada", tool=tool_name, args=args)
            return result
        except Exception as e:
            logger.error("WebMCP tool falhou", tool=tool_name, error=str(e))
            raise

    def get_available_tools(self) -> list[WebMCPTool]:
        return list(self._tools.values())

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def clear(self) -> None:
        self._tools = {}
        self._active_domain = None


class WebAgent:
    """
    Agente especialista em controle de navegador.
    Usa WebMCP quando disponível, Playwright como método principal,
    e UI-TARS + grounding visual como fallback.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.webmcp = WebMCPBridge()
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._playwright: Any = None
        self._webmcp_failures: dict[str, int] = {}

    async def start(self) -> None:
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()

        # Intercepta respostas de API para enriquecer contexto
        self._page.on("response", self._on_response)
        logger.info("WebAgent iniciado", headless=self.headless)

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("WebAgent encerrado")

    async def _on_response(self, response: Any) -> None:
        """Captura respostas JSON de APIs para enriquecer contexto."""
        try:
            ct = response.headers.get("content-type", "")
            if "application/json" in ct and response.status == 200:
                pass  # Processado pelo orquestrador quando necessário
        except Exception:
            pass

    # ─── Ações Principais ──────────────────────────────────────────────────────

    async def navigate(self, url: str, wait_until: str = "networkidle") -> WebResult:
        """Navega para URL e detecta WebMCP."""
        try:
            await self._page.goto(url, wait_until=wait_until, timeout=30000)
            await self.webmcp.detect(self._page)
            screenshot = await self._take_screenshot()
            logger.info("Navegou para URL", url=url)
            return WebResult(success=True, method="playwright", screenshot_b64=screenshot)
        except Exception as e:
            logger.error("Falha ao navegar", url=url, error=str(e))
            return WebResult(success=False, method="playwright", error=str(e))

    async def execute_action(self, action: WebAction) -> WebResult:
        """Executa ação web com fallback automático."""
        if action.action_type == "webmcp" and action.tool_name:
            return await self._execute_webmcp(action)
        elif action.action_type == "navigate":
            return await self.navigate(action.url or "")
        elif action.action_type == "click":
            return await self._click(action)
        elif action.action_type == "type":
            return await self._type(action)
        elif action.action_type == "scroll":
            return await self._scroll(action)
        elif action.action_type == "submit":
            return await self._submit(action)
        else:
            return WebResult(success=False, method="none", error=f"Ação desconhecida: {action.action_type}")

    async def _execute_webmcp(self, action: WebAction) -> WebResult:
        """Tenta executar via WebMCP, com fallback para Playwright."""
        tool_name = action.tool_name or ""
        failures = self._webmcp_failures.get(tool_name, 0)

        # Após 2 falhas, usa fallback visual
        if failures >= 2:
            logger.warning("WebMCP desativado por falhas repetidas", tool=tool_name)
            return WebResult(
                success=False, method="webmcp",
                error="Fallback para modo visual após 2 falhas"
            )

        try:
            result = await self.webmcp.call_tool(
                self._page, tool_name, action.tool_args or {}
            )
            self._webmcp_failures.pop(tool_name, None)
            screenshot = await self._take_screenshot()
            return WebResult(
                success=True, method="webmcp",
                data=result, screenshot_b64=screenshot,
                tokens_saved=250,  # Estimativa de tokens economizados
            )
        except Exception as e:
            self._webmcp_failures[tool_name] = failures + 1
            logger.warning("WebMCP falhou, contando tentativa", tool=tool_name, attempt=failures + 1)
            return WebResult(success=False, method="webmcp", error=str(e))

    async def _click(self, action: WebAction) -> WebResult:
        """Clica em elemento via selector ou coordenadas."""
        try:
            if action.selector:
                await self._page.click(action.selector, timeout=5000)
            elif action.x is not None and action.y is not None:
                await self._page.mouse.click(action.x, action.y)
            screenshot = await self._take_screenshot()
            return WebResult(success=True, method="playwright", screenshot_b64=screenshot)
        except Exception as e:
            logger.error("Click falhou", selector=action.selector, error=str(e))
            return WebResult(success=False, method="playwright", error=str(e))

    async def _type(self, action: WebAction) -> WebResult:
        """Digita texto em elemento focado ou pelo selector."""
        try:
            if action.selector:
                await self._page.fill(action.selector, action.text or "")
            else:
                await self._page.keyboard.type(action.text or "", delay=30)
            screenshot = await self._take_screenshot()
            return WebResult(success=True, method="playwright", screenshot_b64=screenshot)
        except Exception as e:
            return WebResult(success=False, method="playwright", error=str(e))

    async def _scroll(self, action: WebAction) -> WebResult:
        """Faz scroll na página."""
        try:
            delta = -action.scroll_amount * 100 if action.scroll_direction == "up" else action.scroll_amount * 100
            await self._page.mouse.wheel(0, delta)
            screenshot = await self._take_screenshot()
            return WebResult(success=True, method="playwright", screenshot_b64=screenshot)
        except Exception as e:
            return WebResult(success=False, method="playwright", error=str(e))

    async def _submit(self, action: WebAction) -> WebResult:
        """Submete formulário."""
        try:
            if action.selector:
                await self._page.click(action.selector)
            else:
                await self._page.keyboard.press("Enter")
            await self._page.wait_for_load_state("networkidle", timeout=15000)
            screenshot = await self._take_screenshot()
            return WebResult(success=True, method="playwright", screenshot_b64=screenshot)
        except Exception as e:
            return WebResult(success=False, method="playwright", error=str(e))

    async def _take_screenshot(self) -> str:
        """Captura screenshot em base64."""
        import base64
        try:
            data = await self._page.screenshot(type="jpeg", quality=85)
            return base64.b64encode(data).decode()
        except Exception:
            return ""

    async def get_page_context(self) -> dict[str, Any]:
        """Retorna contexto completo da página atual."""
        try:
            return {
                "url": self._page.url,
                "title": await self._page.title(),
                "webmcp_available": len(self.webmcp.get_available_tools()) > 0,
                "webmcp_tools": [t.name for t in self.webmcp.get_available_tools()],
                "screenshot_b64": await self._take_screenshot(),
            }
        except Exception as e:
            return {"error": str(e)}

    async def find_element_by_text(self, text: str) -> Optional[dict]:
        """Localiza elemento pelo texto visível."""
        try:
            locator = self._page.get_by_text(text)
            count = await locator.count()
            if count > 0:
                first = locator.first
                bbox = await first.bounding_box()
                return {"found": True, "bbox": bbox, "selector": f"text={text}"}
        except Exception:
            pass
        return {"found": False}

    async def new_tab(self, url: Optional[str] = None) -> Any:
        """Abre nova aba."""
        page = await self._context.new_page()
        if url:
            await page.goto(url)
        return page

    async def get_page_text(self, max_chars: int = 4000) -> str:
        """Extrai texto principal da página atual via inner_text('body')."""
        try:
            text = await self._page.inner_text("body")
            if text:
                return text[:max_chars]
            return ""
        except Exception as e:
            logger.error("Falha ao extrair texto da página", error=str(e))
            return ""
