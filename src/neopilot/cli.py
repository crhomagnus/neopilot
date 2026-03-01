"""
NeoPilot CLI — Ponto de entrada principal
Comandos: run, chat, professor, status, config
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="neopilot",
    help="NeoPilot — Agente de IA Co-Pilot Universal para Linux",
    add_completion=False,
    pretty_exceptions_enable=False,
)
console = Console()


def _banner() -> None:
    console.print(Panel(
        Text.from_markup(
            "[bold cyan]NeoPilot[/] v0.1.0 — Agente de IA Co-Pilot para Linux\n"
            "[dim]LangGraph · Playwright · AT-SPI · Piper TTS · LibreOffice UNO[/]"
        ),
        border_style="cyan",
        padding=(0, 2),
    ))


@app.command()
def run(
    task: str = typer.Argument(..., help="Tarefa a executar (ex: 'Abra o LibreOffice e crie uma planilha')"),
    professor: bool = typer.Option(False, "--professor", "-p", help="Ativar Modo Professor"),
    voice: bool = typer.Option(False, "--voice", "-v", help="Ativar interface de voz"),
    provider: str = typer.Option("anthropic", "--provider", help="Provedor LLM: anthropic|openai"),
    session_id: Optional[str] = typer.Option(None, "--session", help="ID de sessão para continuar"),
) -> None:
    """Executa uma tarefa única e encerra."""
    _banner()

    async def _run():
        from neopilot.core.agent_graph import NeoPilotOrchestrator
        orch = NeoPilotOrchestrator(llm_provider=provider)

        with console.status("[cyan]Inicializando NeoPilot...[/]"):
            await orch.initialize()

        console.print(f"[bold]Tarefa:[/] {task}")
        if professor:
            console.print("[magenta]🎓 Modo Professor ativado[/]")

        with console.status("[yellow]Executando...[/]"):
            result = await orch.run_task(task, professor_mode=professor, session_id=session_id)

        await orch.shutdown()
        _print_result(result)

    asyncio.run(_run())


@app.command()
def chat(
    professor: bool = typer.Option(False, "--professor", "-p", help="Modo Professor"),
    voice: bool = typer.Option(False, "--voice", "-v", help="Interface de voz"),
    gui: bool = typer.Option(True, "--gui/--no-gui", help="Janela flutuante GTK4/Qt6"),
    provider: str = typer.Option("anthropic", "--provider"),
) -> None:
    """Inicia sessão interativa com o NeoPilot."""
    _banner()

    if gui:
        _start_gui(professor=professor, voice=voice, provider=provider)
    else:
        _start_console_chat(professor=professor, voice=voice, provider=provider)


def _start_gui(professor: bool, voice: bool, provider: str) -> None:
    """Inicia interface GUI (GTK4/Qt6)."""
    from neopilot.ui.floating_window import create_floating_window, AgentStatus, ChatMessage
    from neopilot.core.agent_graph import NeoPilotOrchestrator
    from neopilot.voice.stt import WhisperSTT, MicrophoneListener
    from neopilot.voice.tts import TTSEngine

    window = create_floating_window()
    orchestrator = NeoPilotOrchestrator(llm_provider=provider)
    loop = asyncio.new_event_loop()

    # STT/TTS
    tts = TTSEngine()
    stt = None
    mic_listener = None

    if voice:
        stt = WhisperSTT()

        def on_transcription(result):
            if result.text:
                window.add_message(ChatMessage(role="user", content=f"🎤 {result.text}"))
                _run_task(result.text)

        mic_listener = MicrophoneListener(stt, on_transcription=on_transcription)
        mic_listener.start()
        window.set_status(AgentStatus.LISTENING)

    def _run_task(task: str) -> None:
        window.set_status(AgentStatus.THINKING)

        async def _exec():
            if not orchestrator._initialized:
                await orchestrator.initialize()
            result = await orchestrator.run_task(task, professor_mode=professor)
            return result

        def _done(future):
            result = future.result()
            success = result.get("success", False)
            msg = result.get("result", "Concluído")
            window.add_message(ChatMessage(
                role="agent" if success else "error",
                content=msg,
            ))
            tts.speak_notification(msg[:100])
            window.set_status(AgentStatus.IDLE)

        future = asyncio.run_coroutine_threadsafe(_exec(), loop)
        future.add_done_callback(_done)

    def on_voice_toggle():
        if mic_listener:
            if mic_listener._running:
                mic_listener.stop()
                window.set_status(AgentStatus.IDLE)
            else:
                mic_listener.start()
                window.set_status(AgentStatus.LISTENING)

    window.on_user_input(_run_task)
    window.on_voice_toggle(on_voice_toggle)

    if professor:
        window.set_professor_mode(True)
        window.set_status(AgentStatus.PROFESSOR)

    # Inicia event loop em thread separada
    import threading
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()

    console.print("[green]✓ NeoPilot iniciado[/] — Janela flutuante ativa")
    window.run()

    # Cleanup
    loop.call_soon_threadsafe(loop.stop)
    asyncio.run(orchestrator.shutdown())


def _start_console_chat(professor: bool, voice: bool, provider: str) -> None:
    """Chat interativo no terminal."""
    from neopilot.core.agent_graph import NeoPilotOrchestrator

    async def _chat_loop():
        orch = NeoPilotOrchestrator(llm_provider=provider)

        with console.status("[cyan]Inicializando...[/]"):
            await orch.initialize()

        console.print("[green]✓ Pronto![/] Digite tarefas (Ctrl+C para sair)\n")
        if professor:
            console.print("[magenta]🎓 Modo Professor ativo[/]\n")

        while True:
            try:
                task = console.input("[bold cyan]Você:[/] ").strip()
                if not task:
                    continue
                if task.lower() in ("sair", "exit", "quit"):
                    break

                with console.status("[yellow]Executando...[/]"):
                    result = await orch.run_task(task, professor_mode=professor)

                _print_result(result)

            except KeyboardInterrupt:
                break

        await orch.shutdown()
        console.print("\n[dim]NeoPilot encerrado.[/]")

    asyncio.run(_chat_loop())


@app.command()
def professor(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8765, "--port"),
) -> None:
    """Inicia o dashboard do professor (FastAPI + WebSockets)."""
    _banner()
    from neopilot.ui.professor_dashboard import ProfessorDashboard
    dashboard = ProfessorDashboard(host=host, port=port)

    if not dashboard._available:
        console.print("[red]Erro:[/] FastAPI ou websockets não estão instalados.")
        console.print("Execute: [bold]pip install fastapi uvicorn websockets[/]")
        raise typer.Exit(1)

    console.print(f"[green]✓ Professor Dashboard:[/] http://{host}:{port}")
    asyncio.run(dashboard.start())


@app.command()
def status() -> None:
    """Mostra status e configuração do NeoPilot."""
    _banner()

    from neopilot.core.config import get_settings
    settings = get_settings()

    table = Table(title="Configuração", border_style="cyan", show_header=False)
    table.add_column("Chave", style="dim")
    table.add_column("Valor", style="bold")

    table.add_row("Modo", settings.agent.mode.value)
    table.add_row("LLM Provider", settings.llm.primary.provider.value)
    table.add_row("LLM Model", settings.llm.primary.model)
    table.add_row("STT Engine", settings.voice.stt.engine.value)
    table.add_row("TTS Engine", settings.voice.tts.engine.value)
    table.add_row("STT Language", settings.voice.stt.language)
    table.add_row("Sandbox", settings.security.sandbox.value)
    table.add_row("Max Steps", str(settings.agent.max_steps_per_task))

    console.print(table)

    # Verifica disponibilidade de dependências
    checks = Table(title="Dependências", border_style="green", show_header=False)
    checks.add_column("Componente", style="dim")
    checks.add_column("Status")

    def check_import(module: str, label: str) -> None:
        try:
            __import__(module)
            checks.add_row(label, "[green]✓ Disponível[/]")
        except ImportError:
            checks.add_row(label, "[red]✗ Não instalado[/]")

    check_import("langgraph", "LangGraph")
    check_import("playwright", "Playwright")
    check_import("faster_whisper", "Faster-Whisper")
    check_import("chromadb", "ChromaDB")
    check_import("gi", "GTK4 (PyGObject)")
    check_import("PyQt6", "PyQt6")
    check_import("pyatspi", "AT-SPI (pyatspi)")

    console.print(checks)


@app.command("config")
def config_cmd(
    key: Optional[str] = typer.Argument(None, help="Chave de configuração"),
    value: Optional[str] = typer.Argument(None, help="Novo valor"),
    show: bool = typer.Option(False, "--show", "-s", help="Mostrar configuração atual"),
) -> None:
    """Gerencia configuração do NeoPilot."""
    config_path = Path.home() / ".neopilot" / "config.yaml"

    if show or not key:
        if config_path.exists():
            console.print(config_path.read_text())
        else:
            console.print("[dim]Configuração padrão em uso (arquivo não encontrado)[/]")
        return

    if not value:
        console.print(f"[red]Erro:[/] Forneça um valor para '{key}'")
        raise typer.Exit(1)

    # Leitura e escrita simples do YAML
    import yaml
    config = {}
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text()) or {}

    # Suporte a nested keys: llm.model → {"llm": {"model": value}}
    keys = key.split(".")
    d = config
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False))
    console.print(f"[green]✓[/] {key} = {value}")


@app.command()
def vault(
    action: str = typer.Argument(..., help="set | get | list | delete"),
    key: Optional[str] = typer.Argument(None, help="Nome da credencial"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Valor (ou usa stdin)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", envvar="NEOPILOT_VAULT_PASSWORD",
                                            help="Senha mestre do vault"),
) -> None:
    """Gerencia credenciais no vault criptografado (AES-256-GCM)."""
    import getpass
    from neopilot.security.vault import CredentialVault

    if not password:
        password = getpass.getpass("Senha mestre do vault: ")

    v = CredentialVault(master_password=password)

    if action == "set":
        if not key:
            console.print("[red]Erro:[/] Informe a chave. Ex: neopilot vault set anthropic_api_key --value sk-ant-...")
            raise typer.Exit(1)
        if not value:
            import sys
            if not sys.stdin.isatty():
                value = sys.stdin.read().strip()
            else:
                value = getpass.getpass(f"Valor para '{key}': ")
        v.set(key, value)
        console.print(f"[green]✓[/] '{key}' salvo no vault")

    elif action == "get":
        if not key:
            console.print("[red]Erro:[/] Informe a chave")
            raise typer.Exit(1)
        result = v.get(key)
        if result:
            console.print(result)
        else:
            console.print(f"[yellow]Chave '{key}' não encontrada[/]")

    elif action == "list":
        keys = v.list_keys()
        if keys:
            for k in keys:
                console.print(f"  • {k}")
        else:
            console.print("[dim]Vault vazio[/]")

    elif action == "delete":
        if not key:
            console.print("[red]Erro:[/] Informe a chave")
            raise typer.Exit(1)
        if v.delete(key):
            console.print(f"[green]✓[/] '{key}' removido")
        else:
            console.print(f"[yellow]Chave '{key}' não encontrada[/]")
    else:
        console.print(f"[red]Ação inválida:[/] {action}. Use: set | get | list | delete")


def _print_result(result: dict) -> None:
    """Exibe resultado formatado no terminal."""
    success = result.get("success", False)
    task = result.get("task", "")
    res = result.get("result", "")
    steps = result.get("steps_executed", 0)
    total = result.get("total_steps", 0)
    errors = result.get("error_count", 0)
    duration = result.get("duration_s", 0)

    status_color = "green" if success else "red"
    status_icon = "✓" if success else "✗"

    console.print(Panel(
        f"[{status_color}]{status_icon} {res}[/]\n\n"
        f"[dim]Passos: {steps}/{total} | Erros: {errors} | Tempo: {duration}s[/]",
        title=f"[bold]Tarefa:[/] {task[:60]}",
        border_style=status_color,
    ))


def main():
    app()


if __name__ == "__main__":
    main()
