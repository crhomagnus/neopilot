# NEO PILOT - AGENTE DE IA CO-PILOT UNIVERSAL PARA LINUX
## Descrição Técnica Detalhada para PRD

---

## 1. VISÃO GERAL DO PRODUTO

### 1.1 Nome e Versão
- **Nome:** NeoPilot
- **Versão Atual:** 0.1.0 (MVP)
- **Roadmap Planejado:** v1.0 (Q3 2026), v2.0 (Q4 2026), v3.0 (Q1 2027)
- **Status:** Desenvolvimento Ativo - Fase MVP

### 1.2 Conceito Central
NeoPilot é um **Agent-Computer Interface (ACI)** enterprise-grade que atua simultaneamente como:
1. **Co-pilot autônomo** para automação de tarefas complexas em desktop Linux
2. **Professor de software em tempo real** que observa, corrige erros e guia usuários

O agente opera através de uma **mini-janela flutuante conversacional (300×400px)** que permanece sempre visível, permitindo interação contínua via texto ou voz.

---

## 2. ARQUITETURA TÉCNICA

### 2.1 Padrão de Design Arquitetural
- **Paradigma:** Agentic AI com ReAct Loop (Reasoning + Acting)
- **Framework de Orquestração:** LangGraph (estado de grafo persistente)
- **Modelo de Planejamento:** Hierárquico com reflexão pós-ação
- **Grounding:** Percepção multimodal (visão + semântica + DOM)

### 2.2 Pilares Técnicos

#### 2.2.1 Percepção Universal (Input Layer)
| Fonte | Tecnologia | Propósito |
|-------|-----------|-----------|
| Captura de tela | OpenCV + MSS + PIL | Grounding visual via pixels |
| Acessibilidade semântica | AT-SPI (pyatspi) + D-Bus | Árvore de elementos UI acessível |
| Navegador | Playwright (headless=False) | DOM + estado de páginas web |
| OCR | EasyOCR + Tesseract | Extração de texto de imagens |

#### 2.2.2 Raciocínio (Processing Layer)
| Componente | Implementação | Função |
|------------|--------------|--------|
| LLM Core | GPT-5.2 / Claude via LangChain | Processamento de linguagem natural |
| Orquestração | LangGraph ReAct | Loop de raciocínio e ação |
| Planejamento | CrewAI + AutoGen | Decomposição hierárquica de tarefas |
| Memória Episódica | SQLite | Histórico de ações e contexto |
| Memória Semântica | ChromaDB + Sentence Transformers | Embeddings de conhecimento |

#### 2.2.3 Atuação (Output Layer)
| Domínio | Tecnologia | Capacidades |
|---------|-----------|-------------|
| Web | Playwright | Navegação, cliques, formulários, scraping |
| Desktop | pyatspi + dogtail | Interação com apps GTK/Qt nativos |
| Input Global | xdotool/ydotool | Teclado, mouse, atalhos sistema |
| LibreOffice | UNO API (ooo-dev-tools) | Automação completa de documentos |

---

## 3. FUNCIONALIDADES CORE

### 3.1 Modos de Operação
1. **Professor Assistido:** Observa ações do usuário, detecta erros, sugere correções em tempo real
2. **Autônomo Total:** Executa tarefas end-to-end com confirmação apenas para ações críticas
3. **Sala de Aula:** Multi-usuário com dashboard centralizado para educação
4. **Dev/Debug:** Logs detalhados, profiling, ferramentas de diagnóstico

### 3.2 Capacidades de Automação
- **Navegação Web:** Abrir sites, preencher formulários, extrair dados, navegar dinamicamente
- **LibreOffice:** Criar/editar documentos Writer, planilhas Calc, apresentações Impress
- **Desktop:** Abrir aplicativos, gerenciar janelas, manipular arquivos
- **Multimídia:** Captura de tela, gravação de áudio, reprodução TTS

### 3.3 Interface de Usuário
- **Mini-janela flutuante:** 300×400px, redimensionável, sempre no topo
- **Hotkey global:** Ctrl+Shift+P (ativa/oculta)
- **Indicadores visuais:** 🔴 Ouvindo | 🟡 Processando | 🟢 Executando | 👁 Observando
- **Transparência configurável:** 70-100%
- **System tray:** Ícone com menu de contexto

---

## 4. STACK TECNOLÓGICO COMPLETO

### 4.1 Linguagem e Runtime
- **Python:** 3.11+
- **Gerenciamento:** pip + setuptools + wheel
- **Tipagem:** Pydantic v2 + mypy

### 4.2 Dependências Principais

#### LLM e IA
```
langchain>=0.3.0
langchain-anthropic>=0.3.0
langchain-openai>=0.2.0
langchain-ollama>=0.2.0
langgraph>=0.2.0
crewai>=0.70.0
pyautogen>=0.4.0
```

#### Automação
```
playwright>=1.44.0
pyautogui>=0.9.54
python-xlib>=0.33
pyatspi>=2.46.0
dogtail>=1.0.0
ooo-dev-tools>=0.47.0
```

#### Visão Computacional
```
opencv-python>=4.9.0
pytesseract>=0.3.10
Pillow>=10.3.0
mss>=9.0.1
easyocr>=1.7.1
```

#### Voz (STT/TTS)
```
faster-whisper>=1.0.3 (STT offline)
piper-tts>=1.2.0 (TTS offline pt-BR)
silero-vad>=5.1.0 (detecção de voz)
pyaudio>=0.2.14
sounddevice>=0.4.7
elevenlabs>=1.3.0 (TTS cloud opcional)
```

#### Memória e Dados
```
chromadb>=0.5.0 (vector store)
sentence-transformers>=3.0.0
```

#### Segurança
```
cryptography>=42.0.0 (AES-256-GCM)
keyring>=25.2.0 (vault de segredos)
```

#### UI
```
PyQt6>=6.7.0 (interface gráfica)
rich>=13.7.0 (CLI bonito)
typer>=0.12.0
```

### 4.3 Infraestrutura
- **Sandbox:** Firejail (isolamento de processos)
- **Containerização:** Docker + docker-compose
- **CI/CD:** Pre-commit hooks, pytest, ruff, mypy
- **Testes:** Unitários (pytest), Integração, E2E

---

## 5. ESTRUTURA DE DIRETÓRIOS

```
neopilot/
├── src/neopilot/              # Código fonte principal
│   ├── core/                  # Config, logging, grafo principal
│   │   ├── agent_graph.py     # Definição do LangGraph
│   │   ├── config.py          # Configurações pydantic
│   │   └── logger.py          # Logging estruturado
│   ├── agents/                # Agentes especializados
│   │   ├── desktop_agent.py   # Automação desktop
│   │   ├── web_agent.py       # Automação web (Playwright)
│   │   ├── cad_agent.py       # Suporte a CAD/Software técnico
│   │   └── input_controller.py # Controle de input global
│   ├── perception/            # Percepção multimodal
│   ├── memory/                # Memória episódica e semântica
│   ├── integrations/          # Integrações específicas
│   │   └── libreoffice/       # UNO API para LibreOffice
│   ├── security/              # Vault, criptografia, sandbox
│   ├── ui/                    # Interface gráfica (Qt6)
│   ├── voice/                 # STT/TTS pipeline
│   └── cli.py                 # Interface de linha de comando
├── tests/
│   ├── unit/                  # Testes unitários
│   ├── integration/           # Testes de integração
│   └── e2e/                   # Testes end-to-end
├── config/                    # Arquivos de configuração
├── docs/                      # Documentação
├── scripts/                   # Scripts utilitários
├── pyproject.toml             # Metadados e dependências
├── docker-compose.yml         # Orquestração Docker
├── Dockerfile                 # Imagem de container
├── README.md                  # Documentação principal
├── PRD_NeoPilot_v1.0.md       # Requisitos v1.0
└── PRD_NeoPilot_v2.0.md       # Requisitos v2.0
```

---

## 6. REQUISITOS FUNCIONAIS DETALHADOS

### 6.1 RF001 - Controle de Desktop
- Capturar estado da tela em tempo real (5-10 FPS)
- Identificar janelas ativas e elementos focáveis
- Simular cliques, digitação, atalhos de teclado
- Suporte a múltiplos monitores
- Compatibilidade X11 e Wayland

### 6.2 RF002 - Automação Web
- Abrir navegador visível (não headless)
- Navegar para URLs específicas
- Interagir com elementos DOM (cliques, input, scroll)
- Extrair texto e dados estruturados
- Suporte a WebMCP para sites compatíveis (67% economia de tokens)

### 6.3 RF003 - Integração LibreOffice
- Abrir/criar documentos Writer, Calc, Impress
- Inserir e formatar texto
- Criar/editar tabelas
- Salvar em formatos nativos (.odt, .ods, .odp) e Microsoft Office
- Aplicar estilos e formatação

### 6.4 RF004 - Interface Conversacional
- Janela flutuante sempre visível
- Suporte a entrada de texto e comandos por voz
- Histórico de conversa persistente
- Renderização de rich content (links, imagens, código)
- Notificações visuais discretas

### 6.5 RF005 - Memória e Aprendizado
- Memória de curto prazo (sessão atual)
- Memória de longo prazo (SQLite + ChromaDB)
- Contexto de aplicativos (reconhece quando usuário muda de app)
- Aprendizado com feedback do usuário

### 6.6 RF006 - Modo Professor
- Detecção de erros em tempo real
- Sugestões proativas de correção
- Explicações passo a passo
- Feedback visual (highlights na tela)

---

## 7. REQUISITOS NÃO-FUNCIONAIS

### 7.1 Performance
- Latência de resposta LLM: < 3s para ações simples
- Captura de tela: 5-10 FPS contínuo
- Consumo de RAM: < 2GB em operação normal
- Startup: < 10s até pronto para uso

### 7.2 Segurança
- Criptografia AES-256-GCM para dados sensíveis
- Vault local para armazenamento de segredos
- Sandbox Firejail para isolamento de processos
- Confirmação humana para ações destrutivas
- Zero envio de dados à nuvem por padrão (modo offline)

### 7.3 Confiabilidade
- Retry automático com backoff exponencial
- Circuit breaker para falhas de serviços
- Logging estruturado completo
- Graceful degradation (funciona mesmo com LLM offline)

### 7.4 Usabilidade
- Interface intuitiva sem necessidade de treinamento
- Feedback claro de ações em execução
- Documentação contextual integrada
- Customização de atalhos e preferências

---

## 8. CASOS DE USO PRINCIPAIS

### 8.1 UC001 - Automação de Documentos
**Ator:** Usuário final
**Fluxo:**
1. Usuário solicita: "Crie um relatório mensal no LibreOffice com dados do site X"
2. NeoPilot abre navegador, navega para site, extrai dados
3. Abre LibreOffice Writer, cria documento estruturado
4. Insere tabelas, gráficos, formatação profissional
5. Salva arquivo em local especificado

### 8.2 UC002 - Correção em Tempo Real
**Ator:** Usuário iniciante
**Fluxo:**
1. Usuário trabalha em planilha no Calc
2. Erro detectado: fórmula incorreta em célula
3. NeoPilot destaca célula e sugere correção
4. Explica o erro e a solução passo a passo
5. Aplica correção com confirmação do usuário

### 8.3 UC003 - Pesquisa e Síntese
**Ator:** Pesquisador/Estudante
**Fluxo:**
1. Usuário pede: "Pesquise sobre X e crie resumo"
2. NeoPilot abre múltiplas fontes na web
3. Extrai informações relevantes
4. Compila documento com citações
5. Exporta em formato acadêmico

---

## 9. INTEGRAÇÕES EXTERNAS

### 9.1 Modelos de Linguagem Suportados
- OpenAI GPT-4o / GPT-5.2 (via API)
- Anthropic Claude 3.5 Sonnet/Opus (via API)
- Ollama (modelos locais: Llama 3, Mistral, etc.)

### 9.2 Navegadores
- Chromium (via Playwright)
- Firefox (via Playwright)

### 9.3 Sistemas de Arquivos
- Sistema de arquivos local (ext4, btrfs, etc.)
- Google Drive (via API opcional)
- Nextcloud/Owncloud (via WebDAV)

### 9.4 Comunicação
- WebSocket para comunicação em tempo real
- REST API para integrações externas
- D-Bus para comunicação com sistema Linux

---

## 10. ROADMAP E MILESTONES

### 10.1 MVP (v0.1.0) - Atual
- ✅ Automação web básica (Playwright)
- ✅ Integração LibreOffice (UNO)
- ✅ Captura de tela + OCR
- ✅ Interface flutuante Qt6
- ✅ STT/TTS básico (Piper TTS)
- ✅ Memória SQLite simples

### 10.2 v1.0 (Q3 2026)
- 🎯 Modo Professor completo
- 🎯 Memória semântica (ChromaDB)
- 🎯 Suporte multi-agente (CrewAI)
- 🎯 Sandbox Firejail
- 🎯 Enterprise RBAC

### 10.3 v2.0 (Q4 2026)
- 🎯 WebMCP nativo integrado
- 🎯 Suporte a aplicativos Windows (Wine)
- 🎯 Modo Sala de Aula multi-usuário
- 🎯 Audit trail imutável
- 🎯 Dashboard administrativo

### 10.4 v3.0 (Q1 2027)
- 🎯 Visão computacional avançada (YOLO, segmentation)
- 🎯 Raciocínio multi-modal (texto + imagem + áudio)
- 🎯 Marketplace de agentes especializados
- 🎯 Integração ERP/CRM enterprise

---

## 11. DIFERENCIAIS COMPETITIVOS

| Aspecto | NeoPilot | Competidores (Claude Computer Use, OpenAI Operator) |
|---------|----------|-----------------------------------------------------|
| Plataforma | Linux-first nativo | Web/cloud-based |
| Modo Professor | Correção em tempo real dentro do app | Não disponível |
| WebMCP | 67% menos tokens em sites compatíveis | Uso genérico de ferramentas |
| Offline | 100% funcional sem internet | Dependente de cloud |
| LibreOffice | Integração nativa UNO | Limitado ou indisponível |
| Educação | Multi-usuário, sala de aula | Foco individual |
| Código | Open Core (AGPLv3) | Proprietário/fechado |

---

## 12. MÉTRICAS DE SUCESSO (KPIs)

### 12.1 Técnicas
- Taxa de sucesso de tarefas end-to-end: > 85%
- Tempo médio de execução vs manual: -70%
- Precisão OCR: > 95%
- Latência de resposta LLM: < 3s

### 12.2 Usuário
- NPS (Net Promoter Score): > 50
- Tempo até primeira tarefa bem-sucedida: < 5 minutos
- Retenção semanal: > 60%
- Tarefas executadas por usuário/semana: > 20

### 12.3 Negócio
- TAM (Total Addressable Market): US$ 2.8B (2026)
- CAGR: 38%
- Segmentos principais: Educação Linux, Tutores IA, Enterprise Computer-Use

---

## 13. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Mudanças de UI quebram automação | Alta | Alto | WebMCP + grounding visual redundante |
| Latência LLM inaceitável | Média | Alto | Cache de respostas, modelos locais |
| Falsos positivos no modo Professor | Média | Médio | Confirmação humana, thresholds ajustáveis |
| Segurança (prompt injection) | Média | Alto | Sandboxing, validação de ações |
| Dependência de APIs proprietárias | Baixa | Alto | Suporte a múltiplos LLMs, fallback local |

---

## 14. COMANDOS E INTERFACE CLI

```bash
# Execução de tarefa
neopilot run "Crie um documento no LibreOffice sobre X"

# Modo interativo
neopilot chat

# Modo professor
neopilot teach --app=libreoffice-calc

# Configuração
neopilot config --llm=ollama --model=llama3

# Status e diagnóstico
neopilot status
neopilot doctor

# Modo debug
neopilot run "tarefa" --verbose --headless=false
```

---

## 15. NOTAS ADICIONAIS PARA PRD

### 15.1 Públicos-Alvo
1. **Educação Técnica:** Escolas e universidades com laboratórios Linux
2. **Profissionais Linux:** Usuários avançados de desktop Linux
3. **Enterprise:** Empresas com compliance LGPD/FERPA, necessidade de automação

### 15.2 Modelo de Negócio
- **Open Core:** AGPLv3 para código base
- **Enterprise:** Licença comercial com recursos avançados (RBAC, audit, suporte)
- **Educação:** Licença gratuita para instituições educacionais

### 15.3 Compliance
- LGPD (Brasil): Gestão de consentimento, direito ao esquecimento
- FERPA (EUA): Proteção de registros educacionais
- ISO 27001: Ready para certificação
- GDPR (UE): Se aplicável para usuários europeus

---

## 16. SUMÁRIO EXECUTIVO

**NeoPilot** representa uma nova categoria de software: o **Agent-Computer Interface (ACI)** para Linux. Ao combinar visão computacional, acessibilidade semântica e LLMs avançados em uma interface conversacional sempre disponível, ele elimina a lacuna entre intenção do usuário e execução técnica.

Diferente de assistentes de voz tradicionais ou ferramentas de automação rígidas, NeoPilot:
- **Vê** a tela como um humano (pixels + semântica)
- **Entende** o contexto e objetivo do usuário
- **Age** diretamente nos aplicativos (não apenas APIs)
- **Ensina** enquanto opera (modo Professor único)
- **Respeita** privacidade (offline-first por padrão)

Com um mercado endereçável de US$ 2.8B e crescimento de 38% ao ano, NeoPilot está posicionado para liderar a categoria de Computer-Use Agents em ambientes Linux, educação técnica e automação enterprise.

---

**Documento preparado para:** Criação de PRD profissional
**Base técnica:** MVP v0.1.0 + Roadmap v1.0/v2.0/v3.0
**Última atualização:** Março 2026
