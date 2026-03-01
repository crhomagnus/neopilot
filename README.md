# NeoPilot

**Agente de IA Co-Pilot Universal para Linux**

NeoPilot é um agente autônomo que controla o desktop Linux em tempo real — abre aplicativos, navega na web, pesquisa, escreve documentos no LibreOffice, digita e salva arquivos, tudo via linguagem natural. Baseado em LangGraph ReAct loop com GPT-5.2 / Claude como backend.

```
╭──────────────────────────────────────────────────────────╮
│  NeoPilot v0.1.0 — Agente de IA Co-Pilot para Linux      │
│  LangGraph · Playwright · AT-SPI · Piper TTS · LO UNO    │
╰──────────────────────────────────────────────────────────╯
```

---

## Demo

```bash
# Pesquisa na web e cria documento no LibreOffice em tempo real
neopilot run "Pesquise sobre WebMCP em https://webmcp.link, leia o conteúdo \
  e escreva um documento completo no LibreOffice Writer. Salve como WebMCP.odt."

# Resultado: 9/9 passos | 0 erros | 114s | success=True
# Arquivo: ~/Desktop/WebMCP_Documento.odt (2 páginas, 475 palavras)
```

O agente executa em tempo real na tela: browser Playwright abre e navega, LibreOffice Writer abre e o texto é digitado dinamicamente, arquivo é salvo.

---

## Funcionalidades

| Capacidade | Tecnologia |
|---|---|
| Controle de desktop | AT-SPI (pyatspi) + xdotool/ydotool |
| Automação de browser | Playwright (headless=False) + WebMCP Bridge |
| Documentos LibreOffice | UNO API (python-ooo-dev-tools) |
| LLM orchestration | LangGraph ReAct + GPT-5.2 / Claude |
| Voz (STT) | faster-whisper + Silero VAD |
| Voz (TTS) | Piper TTS offline (pt_BR-faber-medium) |
| Memória | SQLite episódica + ChromaDB semântica |
| Interface | GTK4/Qt6 janela flutuante 300×400px |
| Segurança | Vault AES-256-GCM + Firejail sandbox |
| Enterprise | RBAC multi-role + audit trail SHA-256 |

---

## Arquitetura

```
neopilot run "tarefa"
        │
        ▼
  ┌─────────────┐
  │  Planner    │  GPT-5.2 decompõe tarefa em passos
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Observer   │  AT-SPI + OCR captura estado da tela
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Reasoner   │  GPT-5.2 decide próxima ação
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐     ┌──────────────────┐
  │  Executor   │────▶│  Ações:          │
  └──────┬──────┘     │  open_app        │
         │            │  focus_window    │
         ▼            │  navigate (URL)  │
  ┌─────────────┐     │  read_page       │
  │  Reflector  │     │  type (+ \n)     │
  └─────────────┘     │  save_file       │
                      │  hotkey          │
                      │  lo_writer       │
                      └──────────────────┘
```

---

## Instalação

**Requisitos:** Python 3.11+, Linux (X11 ou Wayland), xdotool

```bash
git clone https://github.com/crhomagnus/neopilot
cd neopilot

# Instala dependências
pip install -e ".[dev]"

# Instala browsers Playwright
playwright install chromium

# Configura LLM (OpenAI ou Anthropic)
neopilot config set llm.primary.provider openai
neopilot config set llm.primary.model gpt-5.2
```

**Dependências opcionais:**

```bash
# AT-SPI (acessibilidade semântica)
sudo apt install python3-pyatspi xdotool wmctrl

# Piper TTS offline (pt_BR)
pip install piper-tts
# Baixa modelo: ~/.neopilot/models/piper/pt_BR-faber-medium.onnx

# LibreOffice (para tarefas de documentos)
sudo apt install libreoffice
```

---

## Uso

```bash
# Tarefa única
neopilot run "Abre o LibreOffice Calc e cria uma planilha de orçamento mensal"

# Pesquisa + documento
neopilot run "Pesquise sobre Python 3.13 em python.org e escreva um resumo no Writer"

# Pergunta informacional (responde em ~5s)
neopilot run "O que é o protocolo WebMCP?"

# Modo Professor (corrige erros em tempo real)
neopilot run --professor "Ensina como usar fórmulas no LibreOffice Calc"

# Interface interativa com janela flutuante
neopilot chat

# Status e dependências
neopilot status
```

---

## Configuração

O arquivo de configuração principal fica em `~/.neopilot/config.yaml`:

```yaml
llm:
  primary:
    provider: openai       # openai | anthropic | ollama
    model: gpt-5.2
    temperature: 0.1
    max_tokens: 4096

agent:
  mode: assisted           # assisted | autonomous
  max_steps_per_task: 50

security:
  sandbox: firejail
  requires_confirmation:
    - delete_file
    - send_email
```

**API keys** são armazenadas em vault AES-256-GCM (`~/.neopilot/vault/`):

```bash
# Salva chave no vault (senha padrão: neopilot-local)
python -c "
from neopilot.security.vault import CredentialVault
v = CredentialVault('neopilot-local')
v.set('openai_api_key', 'sk-...')
"
```

---

## Estrutura do Projeto

```
neopilot/
├── src/neopilot/
│   ├── core/
│   │   ├── agent_graph.py      # LangGraph ReAct loop
│   │   ├── config.py           # Configuração (pydantic-settings)
│   │   └── logger.py           # structlog + AuditLogger SHA-256
│   ├── agents/
│   │   ├── desktop_agent.py    # AT-SPI + xdotool + Modo Professor
│   │   ├── web_agent.py        # Playwright + WebMCP Bridge
│   │   ├── input_controller.py # Mouse/teclado X11/Wayland
│   │   └── cad_agent.py        # CAD via Wine + SikuliX
│   ├── perception/
│   │   ├── accessibility.py    # Árvore AT-SPI
│   │   ├── context_builder.py  # Contexto unificado tela+apps
│   │   ├── screen_capture.py   # Screenshot (mss)
│   │   └── visual_grounder.py  # Grounding visual (OpenCV)
│   ├── integrations/
│   │   └── libreoffice/
│   │       └── lo_agent.py     # UNO API Writer/Calc/Impress
│   ├── memory/
│   │   └── manager.py          # SQLite episódica + ChromaDB
│   ├── voice/
│   │   ├── stt.py              # Whisper STT + VAD
│   │   └── tts.py              # Piper TTS offline
│   ├── security/
│   │   ├── vault.py            # AES-256-GCM vault
│   │   ├── sandbox.py          # Firejail/Bubblewrap/Docker
│   │   └── enterprise_policy.py # RBAC multi-role
│   ├── ui/
│   │   ├── floating_window.py  # GTK4/Qt6 mini-janela
│   │   └── professor_dashboard.py # FastAPI + WebSockets
│   └── cli.py                  # Typer CLI
├── tests/
│   ├── unit/                   # 49 testes unitários
│   └── integration/            # Testes de orquestração
├── config/default.yaml
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## Testes

```bash
# Roda todos os testes (49 testes)
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=neopilot --cov-report=html
```

```
49 passed in 8.00s
```

---

## Docker

```bash
# Build
docker build -t neopilot .

# Run (com acesso ao display X11)
docker-compose up
```

---

## WebMCP

O NeoPilot suporta o protocolo **WebMCP (Web Model Context Protocol)** — padrão emergente (Google + Microsoft + W3C, 2026) que permite sites exporem capacidades estruturadas para agentes via `navigator.modelContext`.

Quando um site suporta WebMCP, o agente usa a API diretamente em vez de scraping visual, reduzindo tokens e aumentando a confiabilidade:

```python
# Detecção automática ao navegar
await web_agent.navigate("https://site-com-webmcp.com")
# → WebMCP detectado: 3 tools disponíveis (search_flights, book_trip, ...)
```

---

## Licença

MIT — veja [LICENSE](LICENSE) para detalhes.

---

## Status

| Componente | Status |
|---|---|
| LangGraph ReAct loop | ✅ Produção |
| Executor (open_app, navigate, type, save_file) | ✅ Produção |
| WebAgent Playwright | ✅ Produção |
| read_page + web_content state | ✅ Produção |
| LibreOffice UNO | ✅ Produção |
| AT-SPI + xdotool | ✅ Produção |
| Vault AES-256-GCM | ✅ Produção |
| Memória SQLite + ChromaDB | ✅ Produção |
| Piper TTS offline | ✅ Produção |
| Whisper STT | ✅ Produção |
| GTK4/Qt6 UI | ✅ Implementado |
| Modo Professor | ✅ Implementado |
| Dashboard FastAPI | ✅ Implementado |
| Testes (49/49) | ✅ Passando |
