# NeoPilot – Agente de IA Co-Pilot Universal para Linux
## Product Requirements Document (PRD) — Versão 2.0
**Incorporando: WebMCP · Compute Use Enterprise · Modo Professor Avançado · Mini-Janela Flutuante**
**Data:** Março 2026 | **Status:** Ativo | **Licença:** Open Core (AGPLv3 + Enterprise)

---

# 1. Visão Geral e Resumo Executivo

O **NeoPilot** é um **Agent-Computer Interface (ACI) enterprise-grade para Linux** que funciona simultaneamente como **professor de software em tempo real** e **co-pilot autônomo**. Através de uma **mini-janela flutuante conversacional (300×400px)**, o agente observa a tela do usuário, compreende o contexto de aplicativos (LibreOffice, navegadores, CAD, ferramentas técnicas), **corrige erros em tempo real**, executa tarefas complexas e ensina passo a passo — seguindo o paradigma ReAct + planejamento hierárquico + grounding visual.

## 1.1 Mini-Janela Flutuante (Feature Central)

```
┌─────────────────────────────────────────────────────────────┐
│  NeoPilot  ●●●  [👁 Observando]  [⚙] [✕]           [≡]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🤖 Selecione a célula A2:B5 primeiro,                     │
│     depois clique em AutoSoma (Σ)                          │
│                                                             │
│  👤 como eu faço isso?                                     │
│                                                             │
│  🤖 Vou mostrar para você...                               │
│     [▶ Executando: selecionando A2:B5]                     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  📎  │  🎤 Falar  │  [Digite aqui...]          │  ➤        │
└─────────────────────────────────────────────────────────────┘
```

**Características da janela:**
- Tamanho padrão 300×400px, redimensionável, sempre no topo
- Transparência configurável (70-100%), tema claro/escuro
- Hotkey global: `Ctrl+Shift+P` (ativa/oculta instantaneamente)
- Ícone na system tray com menu de contexto rápido
- Detecção automática de mudança de contexto (LibreOffice → Firefox, etc.)
- Indicadores visuais: 🔴 Ouvindo | 🟡 Processando | 🟢 Executando | 👁 Observando

## 1.2 Modos de Operação

| Modo | Descrição | Público-Alvo |
|---|---|---|
| **Professor Assistido** | Observa, corrige erros, guia passo a passo | Alunos, iniciantes |
| **Autônomo Total** | Executa tarefas end-to-end com confirmação crítica | Power users, profissionais |
| **Sala de Aula** | Multi-usuário com dashboard centralizado | Professores, admins |
| **Dev/Debug** | Logs detalhados, profiling de agente | Desenvolvedores de IA |

## 1.3 Diferenciais Competitivos

- **WebMCP nativo:** 67% menos tokens, 80% menos falhas em sites compatíveis
- **Modo Professor:** Detecta e corrige erros do usuário em tempo real dentro do app
- **100% local/offline por padrão:** Zero envio de dados à nuvem sem consentimento
- **Linux-first:** Suporte nativo X11 + Wayland, AT-SPI, GTK4, LibreOffice UNO
- **Enterprise-ready:** Audit trail imutável, multi-tenant, compliance LGPD/FERPA

---

# 2. Problema que o Produto Resolve + Oportunidade de Mercado (2026)

## 2.1 Enterprise Computer-Use Gap

```
Linux Desktop + Educação Técnica = GAP CRÍTICO
┌─────────────────────┐    ┌──────────────────────────┐
│   Alunos Linux      │    │   Professores Linux      │
│  • Erros repetidos  │    │  • Não acompanham todos  │
│  • Menus esquecidos │    │  • Explicam 10x o mesmo  │
│  • Planilhas erradas│    │  • Falta feedback real   │
└──────────┬──────────┘    └──────────┬───────────────┘
           └──────────────┬───────────┘
                 ┌────────▼────────┐
                 │  NEOPILOT ACI   │ ← Resolve o gap
                 └─────────────────┘
```

**Requisitos Enterprise Computer-Use:**
- Zero Trust Security (sandbox multi-camada)
- Audit Trail completo e imutável de todas as ações
- Multi-tenant (escolas, laboratórios, empresas)
- Compliance (LGPD, FERPA equivalente, ISO 27001 ready)

## 2.2 O que é "Compute Use Enterprise"

"Compute Use Enterprise" descreve uma arquitetura de IA que executa tarefas concretas em ambientes de computação corporativa — usando o computador como um humano faria (navegador, desktop, arquivos, sistemas internos) — dentro de requisitos de:
- **Segurança:** Sandboxing, políticas granulares por usuário/perfil
- **Governança:** Log de ações, auditoria, compliance regulatório
- **Escalabilidade:** Dezenas/milhares de usuários em VMs/containers
- **Integrações Enterprise:** SSO/LDAP, SIEM, monitoramento centralizado

## 2.3 Oportunidade de Mercado TAM 2026: US$ 2.8B

| Segmento | TAM | CAGR |
|---|---|---|
| Linux Education Market | US$ 1.2B | 31% |
| AI Tutors (Office/CAD) | US$ 900M | 45% |
| Enterprise Computer-Use | US$ 700M | 67% |
| **Total Addressable** | **US$ 2.8B** | **38%** |

---

# 3. Objetivos de Negócio e Métricas de Sucesso (KPIs)

## 3.1 OKRs por Objetivo Estratégico

| Objetivo | KR1 | KR2 | KR3 |
|---|---|---|---|
| Liderar Computer-Use Linux | 35% OSWorld benchmark | 10K MAU | 85% task success |
| Transformar Educação Técnica | 40% redução tempo-aprendizagem | 70% taxa correção-erros | NPS ≥ 45 |
| Enterprise Scale | 500 instituições | 99.9% uptime | <1GB RAM médio |

## 3.2 KPIs Quantitativos Detalhados

| KPI | Definição | Meta MVP | Meta v1.0 | Meta v2.0 |
|---|---|---|---|---|
| **Task Success Rate** | % tarefas guiadas concluídas sem erro crítico | 65% | 78% | 85% |
| **Error Detection Rate** | % erros do usuário detectados pelo agente | 60% | 72% | 80% |
| **Error Correction Rate** | % erros detectados corrigidos com sucesso | 55% | 70% | 80% |
| **Tempo de Aprendizagem** | Redução vs. sem NeoPilot | -25% | -35% | -40% |
| **WebMCP Token Efficiency** | Redução de tokens em sites WebMCP | 50% | 65% | 67% |
| **OSWorld-Linux Score** | Benchmark tarefas 20-50 passos | 25% | 32% | 38% |
| **Latência (Modo Professor)** | p95 resposta a erro do usuário | < 800ms | < 600ms | < 500ms |
| **RAM Usage (idle)** | Consumo médio em standby | < 600MB | < 800MB | < 1GB |
| **NPS** | Net Promoter Score pós-treinamento | ≥ 38 | ≥ 42 | ≥ 48 |

## 3.3 MoSCoW Prioritization

```
MUST (MVP):
  ✓ Mini-janela flutuante + hotkey global
  ✓ WebMCP Bridge (navegador)
  ✓ LibreOffice Writer + Calc (UNO API)
  ✓ Modo Professor básico (observação + correção)
  ✓ STT Whisper offline
  ✓ Sandbox (Firejail + Docker)
  ✓ Audit log imutável

SHOULD (v1.0):
  ○ LibreOffice Impress + Draw
  ○ Multi-agente (Browser + Office)
  ○ Dashboard professor (sala de aula)
  ○ TTS emocional (Piper)
  ○ Memória episódica persistente

COULD (v1.5):
  ○ Wine/CAD (Fusion360, Rhino3D)
  ○ Suporte Kubernetes
  ○ SSO/LDAP integration
  ○ 8+ idiomas de voz

WON'T (2026):
  ✗ Mobile app
  ✗ Suporte macOS/Windows
  ✗ Training próprio de LLM
```

---

# 4. Personas de Usuário e User Journeys

## 4.1 Persona 1: João, Aluno de Informática (16 anos)

**Perfil:** Escola técnica, cursando Informática Básica. Usa Linux Mint.

**User Journey — LibreOffice Calc:**
```
1. João abre LibreOffice Calc com arquivo de orçamento
2. Ativa NeoPilot: Ctrl+Shift+P
3. Diz: "Professora, como coloco a SOMA desta coluna?"
4. NeoPilot OBSERVA: cursor de João está na célula errada (B1 ao invés de B6)
5. NeoPilot: "João, clique primeiro na célula B6, que fica abaixo dos números"
6. João tenta clicar em C6 (erro)
7. NeoPilot detecta erro → "Não é essa, é a coluna B. Quer que eu mostre?"
8. João: "sim"
9. NeoPilot EXECUTA: seleciona B6, insere =SOMA(B1:B5), pressiona Enter
10. NeoPilot: "Viu? Agora tente você na coluna C!"
11. João tenta e acerta ✓
12. NeoPilot gera resumo: "Você aprendeu: SOMA, seleção de células ✓"
```

## 4.2 Persona 2: Maria, Professora de Informática (35 anos)

**Perfil:** Leciona LibreOffice e Internet em escola técnica, turma de 30 alunos.

**User Journey — Sala de Aula:**
```
1. Maria abre dashboard NeoPilot Classroom no seu PC
2. Visualiza: 30 ícones, cada um com status de aluno
3. Dashboard mostra: 8/30 alunos com erro em "Fórmula SOMA"
4. Maria clica: "Broadcast mensagem": "Classe, cliquem em FX primeiro!"
5. Para João (erro persistente): Maria clica "Intervir" → assume controle remoto
6. NeoPilot do João: "Sua professora vai te ajudar agora"
7. Maria corrige remotamente via NeoPilot de João
8. Resultado: 95% da classe resolve tarefa em 15 min (vs 45 min antes)
```

## 4.3 Persona 3: Carlos, Admin de TI (42 anos)

**Perfil:** Responsável por 50 PCs em laboratório de informática.

**User Journey — Deploy Enterprise:**
```
1. carlos@server:~$ apt install neopilot-enterprise
2. Edita /etc/neopilot/policies.yaml:
   - allowed_apps: [libreoffice, firefox, thunderbird]
   - mode_default: professor
   - student_permissions: [no_autonomous, no_file_delete]
3. Distribui configuração via Ansible para 50 máquinas
4. Abre Grafana → dashboard NeoPilot:
   - 50 agentes online ✓
   - 3 erros de sandbox (alunos tentaram rodar script proibido)
   - Audit log: todas as ações registradas
5. Zero incidentes de segurança no mês
```

## 4.4 Persona 4: Dev IA / Pesquisador (28 anos)

**Perfil:** Pesquisador em Agent-Computer Interface, avaliando benchmarks OSWorld.

**User Journey — Extensão de Módulo:**
```
1. git clone github.com/neopilot/neopilot
2. pip install -e ".[dev]"
3. Roda: neopilot --mode=dev --log-level=debug --profile-agent
4. Examina LangGraph trace: cada nó com tokens, latência, estado
5. Adiciona novo agente: GitHubAgent(specialist)
6. Roda OSWorld-Linux benchmark: 37% success rate ✓
7. Submete PR com novo módulo
```

## 4.5 Persona 5: CTO de Escola Técnica (50 anos)

**Perfil:** Decisor de compra para 500 alunos, preocupado com LGPD e custo.

**Critérios de Decisão:**
- 100% local (zero dados na nuvem) ✓ NeoPilot
- Custo: Open Core gratuito + Enterprise €8/aluno/mês
- Compliance LGPD automático (audit log local) ✓
- ROI: redução de 2 professores auxiliares ≈ R$8.000/mês

---

# 5. Casos de Uso Principais e User Stories (42 total)

## 5.1 Módulo 1: Mini-Janela Flutuante (8 User Stories)

### US1.1 — Hotkey Global
```gherkin
Scenario: Ativação por hotkey
  Given NeoPilot está rodando em background
  When usuário pressiona Ctrl+Shift+P
  Then mini-janela aparece em < 200ms no canto superior direito
  And foco vai automaticamente para o campo de input
  When usuário pressiona Ctrl+Shift+P novamente
  Then janela é ocultada (não fechada) em < 100ms
```

### US1.2 — STT Whisper Offline em Tempo Real
```gherkin
Scenario: Comando por voz
  Given janela está aberta e microfone disponível
  When usuário clica em [🎤] ou pressiona Ctrl+M
  Then indicador 🔴 "Ouvindo" aparece
  And transcrição em tempo real aparece no input
  When usuário para de falar por 1.5s
  Then STT finaliza e comando é enviado automaticamente
  And latência total STT < 800ms para 5 segundos de áudio
```

### US1.3 — Anexar Arquivo para Análise
```gherkin
Scenario: Upload de arquivo para análise contextual
  Given usuário tem arquivo XLSX aberto no computador
  When usuário arrasta o arquivo para a mini-janela
  Then janela exibe "📎 planilha_vendas.xlsx carregado (45KB)"
  And agente analisa o arquivo e responde em contexto
  And arquivo é processado localmente (não enviado à nuvem)
```

### US1.4 — Detecção Automática de Contexto de App
```gherkin
Scenario: Mudança automática de contexto
  Given NeoPilot está em modo professor observando LibreOffice
  When usuário clica no Firefox e torna-o janela ativa
  Then NeoPilot detecta mudança em < 500ms
  And exibe: "Mudei para modo navegador. Como posso ajudar?"
  And muda conjunto de ferramentas ativas (LibreOffice → Playwright)
```

### US1.5 — Indicadores de Status Visual
- **US1.6** — Modo silencioso durante exames (TTS desativado mas observação ativa)
- **US1.7** — Tema escuro/claro, tipografia acessível, transparência ajustável
- **US1.8** — Suporte total a teclado (sem mouse obrigatório), alto contraste WCAG AA

## 5.2 Módulo 2: WebMCP + Navegador (12 User Stories)

### US2.1 — Detecção Automática WebMCP
```gherkin
Scenario: Site com WebMCP detectado
  Given agente navega para gmail.com
  When Playwright detecta navigator.modelContext disponível
  Then agente usa WebMCP tools como método primário
  And registra: "WebMCP: gmail.com — 8 tools disponíveis"
  And reduz em 67% os tokens usados vs. método visual
```

### US2.2 — Fallback para UI-TARS quando sem WebMCP
```gherkin
Scenario: Site sem WebMCP
  Given agente navega para site sem suporte WebMCP
  When navigator.modelContext não é detectado
  Then agente usa screenshot + UI-TARS como método primário
  And registra: "WebMCP não disponível — usando grounding visual"
```

### US2.3 — Navegação Multi-abas com Contexto Compartilhado
- **US2.4** — Preenchimento de formulários complexos (multi-step, validação)
- **US2.5** — Scroll inteligente e detecção de lazy-loading
- **US2.6** — Drag-and-drop em interfaces web (Trello, Jira, etc.)
- **US2.7** — Interceptação de respostas de API para enriquecer contexto do agente
- **US2.8** — Stealth mode (anti-fingerprint ético para dados próprios do usuário)
- **US2.9** — Upload/download de arquivos em formulários web
- **US2.10** — Execução de JavaScript no contexto da página
- **US2.11** — Operação em sites com autenticação 2FA (TOTP integrado)
- **US2.12** — Screenshot de elementos específicos do DOM

## 5.3 Módulo 3: LibreOffice Deep Integration (10 User Stories)

### US3.1 — UNO API como Canal Primário
```gherkin
Scenario: Criar planilha com dados e gráfico
  Given usuário solicita "crie planilha de orçamento Q1 2026"
  When agente conecta ao LibreOffice via UNO Bridge (porta 2002)
  Then agente cria nova planilha com python-ooo-dev-tools
  And insere cabeçalhos, dados e fórmulas de SOMA/MÉDIA
  And cria gráfico de barras na aba "Gráfico"
  And exporta como PDF em ~/Documents/orcamento_Q1.pdf
  And todo processo via UNO API sem cliques de mouse
```

### US3.2 — Modo Professor: Detecção de Erro de Fórmula
```gherkin
Scenario: Aluno digita fórmula errada
  Given agente está em modo professor observando LibreOffice Calc
  And o aluno deveria digitar =SOMA(B1:B5)
  When agente detecta via AT-SPI que usuário digitou =SOMA(B1-B5)
  Then agente reage em < 500ms
  And exibe: "Erro: use ':' para intervalo, não '-'. Ex: =SOMA(B1:B5)"
  And oferece: "[✓ Corrigir automaticamente] [📖 Mostrar como]"
```

- **US3.3** — Executar macros LibreOffice Basic existentes
- **US3.4** — Modo professor para LibreOffice Writer (formatação, estilos)
- **US3.5** — LibreOffice Impress: criar apresentações de outline de texto
- **US3.6** — Exportação multi-formato (ODF, DOCX, XLSX, PPTX, PDF)
- **US3.7** — Mala direta automatizada (Writer + Calc)
- **US3.8** — Detecção e correção de erros de referência circular
- **US3.9** — Aplicar templates e estilos corporativos
- **US3.10** — Modo "teaching playback": agente grava e replay de sequência de passos

## 5.4 Módulo 4: Modo Professor e Sala de Aula (6 User Stories)

### US4.1 — Dashboard de Sala de Aula
```gherkin
Scenario: Professor monitora 30 alunos
  Given professor tem dashboard aberto no seu PC
  And 30 PCs de alunos com NeoPilot ativo na rede local
  When agente do aluno João detecta erro crítico
  Then dashboard atualiza em < 2s: João - 🔴 Erro fórmula SOMA
  And professor pode clicar [Ver tela] [Intervir] [Broadcast]
```

- **US4.2** — Broadcast de mensagem para toda a turma
- **US4.3** — Intervenção remota (professor assume controle com permissão do aluno)
- **US4.4** — Relatório de aula: resumo de erros, progresso, tempo por tarefa
- **US4.5** — Modo "exame": agente só observa, não intervém, registra tudo
- **US4.6** — Configuração de "trilha de aprendizagem" (sequência de tarefas guiadas)

## 5.5 Módulo 5: Segurança Enterprise (6 User Stories)
(detalhadas na seção 11)

---

# 6. Requisitos Funcionais Detalhados

## 6.1 Módulo F1 — Mini-Janela Flutuante

### F1.1 Framework UI

| ID | Requisito | Prioridade |
|---|---|---|
| F1.1.1 | Janela GTK4 (X11 nativo) com fallback Qt6 (Wayland nativo) | MUST |
| F1.1.2 | Tamanho padrão 300×400px, redimensionável 250×300 a 600×800 | MUST |
| F1.1.3 | Always-on-top configurável (padrão: ativo) | MUST |
| F1.1.4 | Transparência de janela ajustável via slider (50-100%) | SHOULD |
| F1.1.5 | Snap para bordas do monitor | SHOULD |
| F1.1.6 | Drag para mover por qualquer parte da janela | MUST |
| F1.1.7 | System tray icon com menu: Abrir, Modos, Configurações, Sair | MUST |
| F1.1.8 | Tema escuro/claro automático (segue sistema) + manual | MUST |
| F1.1.9 | Suporte a HiDPI (scaling 1x-4x automático) | MUST |

### F1.2 Área de Conversa

| ID | Requisito | Prioridade |
|---|---|---|
| F1.2.1 | Bolhas de chat diferenciadas por remetente (usuário / agente) | MUST |
| F1.2.2 | Renderização de Markdown (negrito, código, listas) | MUST |
| F1.2.3 | Scroll automático para última mensagem | MUST |
| F1.2.4 | Indicador de digitação (agente processando) animado | MUST |
| F1.2.5 | Botão "Copiar" em blocos de código | SHOULD |
| F1.2.6 | Histórico de conversa persistente entre sessões | MUST |

### F1.3 Barra de Input

| ID | Requisito | Prioridade |
|---|---|---|
| F1.3.1 | Input multi-linha com Shift+Enter para nova linha | MUST |
| F1.3.2 | Botão 🎤 com ativação por click ou Ctrl+M | MUST |
| F1.3.3 | Botão 📎 para upload de arquivo (PDF, DOCX, XLSX, imagens) | MUST |
| F1.3.4 | Indicador de caracteres (limite de contexto) | COULD |
| F1.3.5 | Histórico de comandos navegável com setas ↑↓ | SHOULD |

### F1.4 Painel de Status (Modo Professor)

| ID | Requisito | Prioridade |
|---|---|---|
| F1.4.1 | Badge com app em foco atual (ex.: "LibreOffice Calc") | MUST |
| F1.4.2 | Indicador de modo: 👁 Observando / 🟡 Processando / 🟢 Executando | MUST |
| F1.4.3 | Contador de erros detectados na sessão | SHOULD |
| F1.4.4 | Botão pausa (interrompe agente mas mantém observação) | MUST |
| F1.4.5 | Botão confirmar/rejeitar antes de ação crítica | MUST |

---

## 6.2 Módulo F2 — WebMCP Bridge

### F2.1 Arquitetura WebMCP

```
┌──────────────────────────────────────────────────────────────┐
│                   WEBMCP BRIDGE ARCHITECTURE                  │
│                                                              │
│  Playwright Context                                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  page.evaluate() → navigator.modelContext detection  │   │
│  │  ┌──────────────────┐   ┌──────────────────────────┐ │   │
│  │  │  WebMCP Detector │──▶│  Tool Schema Extractor   │ │   │
│  │  └──────────────────┘   └──────────────────────────┘ │   │
│  └───────────────────────────────┬──────────────────────┘   │
│                                  │                           │
│  ┌───────────────────────────────▼──────────────────────┐   │
│  │              WebMCP → LangGraph Adapter               │   │
│  │  WebMCP Tool → LangChain Tool → Agent Tool Registry  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Resultado: agente usa login(), search(), purchase()         │
│  diretamente em vez de clicar pixel a pixel                 │
└──────────────────────────────────────────────────────────────┘
```

| ID | Requisito | Prioridade |
|---|---|---|
| F2.1.1 | Detectar `navigator.modelContext` via Playwright page.evaluate | MUST |
| F2.1.2 | Extrair schema de tools disponíveis no site | MUST |
| F2.1.3 | Converter WebMCP tools para LangChain Tool format | MUST |
| F2.1.4 | Fallback automático para grounding visual quando tool falha 2x | MUST |
| F2.1.5 | Registrar métricas: tokens WebMCP vs. visual por sessão | MUST |
| F2.1.6 | Suporte a autenticação WebMCP via token de sessão | SHOULD |
| F2.1.7 | Cache de schemas WebMCP por domínio (TTL 24h) | SHOULD |

### F2.2 Sites WebMCP Testados (MVP)

| Site | Tools Disponíveis | Status |
|---|---|---|
| Gmail | `send_email()`, `search_emails()`, `read_email()` | MVP |
| Google Docs | `create_doc()`, `edit_doc()`, `share_doc()` | MVP |
| GitHub | `create_issue()`, `open_pr()`, `search_repo()` | v1.0 |
| Notion | `create_page()`, `search()`, `update_block()` | v1.0 |
| Jira | `create_ticket()`, `update_status()`, `search()` | v1.5 |

---

## 6.3 Módulo F3 — Modo Professor

### F3.1 Sistema de Observação Contínua

| ID | Requisito | Prioridade |
|---|---|---|
| F3.1.1 | Captura de tela a 2fps durante modo professor (reduzível para 1fps) | MUST |
| F3.1.2 | Comparação de estado atual vs. estado esperado da tarefa | MUST |
| F3.1.3 | Detecção de desvio de passo em < 500ms | MUST |
| F3.1.4 | Classificação de erro: leve / moderado / crítico | MUST |
| F3.1.5 | Geração de explicação contextual do erro | MUST |
| F3.1.6 | Oferta de correção automática com confirmação do aluno | MUST |
| F3.1.7 | Modo "mostre o caminho certo" (highlight visual no elemento correto) | SHOULD |

### F3.2 Trilha de Aprendizagem

| ID | Requisito | Prioridade |
|---|---|---|
| F3.2.1 | Professor define sequência de passos esperados para uma tarefa | MUST |
| F3.2.2 | Agente compara ações do aluno vs. sequência esperada | MUST |
| F3.2.3 | Relatório pós-sessão: passos completados, erros, tempo por passo | MUST |
| F3.2.4 | Exportação de relatório em PDF para professor | SHOULD |
| F3.2.5 | Sugestão de repetição de exercícios com erros frequentes | COULD |

---

# 7. Requisitos Não Funcionais

| Categoria | Requisito | Métrica Target |
|---|---|---|
| **Performance** | Latência detecção de erro (modo professor) | p95 < 500ms |
| **Performance** | Startup da mini-janela | < 2s |
| **Performance** | STT latência (5s de áudio) | < 800ms local |
| **Performance** | WebMCP tool call vs. visual | 67% menos tokens |
| **Segurança** | Isolamento de processo | Docker + Firejail + Bubblewrap |
| **Segurança** | Credenciais em repouso | AES-256-GCM |
| **Privacidade** | Dados fora do dispositivo | Zero por padrão |
| **Privacidade** | Screenshots enviadas à nuvem | Só com opt-in explícito |
| **Escalabilidade** | Instâncias simultâneas por servidor | 1000+ (Kubernetes) |
| **Disponibilidade** | Uptime durante sessão do usuário | 99.9% |
| **Compatibilidade** | Distribuições Linux | Ubuntu 24.04+, Fedora 43+, Debian 13+, Arch |
| **Compatibilidade** | Display servers | X11 + Wayland (nativo, sem XWayland obrigatório) |
| **Compatibilidade** | Desktop environments | GNOME 46+, KDE Plasma 6+, XFCE 4.18+ |
| **Acessibilidade** | Standard | WCAG 2.2 AA |
| **Recursos** | CPU (modo professor ativo) | ≤ 30% em hardware médio |
| **Recursos** | RAM (uso médio) | ≤ 1GB |

---

# 8. Arquitetura Técnica e Stack (Enterprise Computer-Use)

## 8.1 Diagrama de Arquitetura Completa

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEOPILOT v2.0 — ENTERPRISE ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                  CAMADA UI (Mini-Janela Flutuante)                    │  │
│  │    GTK4 / Qt6  ←→  System Tray  ←→  Hotkey (sxhkd/ydotool)         │  │
│  │    Chat UI  │  STT Whisper.cpp  │  TTS Piper  │  File Upload         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    ↕                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    CAMADA COGNITIVA (ReAct Loop)                      │  │
│  │                                                                        │  │
│  │  LangGraph StatefulGraph                                              │  │
│  │  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │  │
│  │  │ Planner  │ │ Observer  │ │ Reasoner │ │ Executor │ │Reflector │ │  │
│  │  │ (HTP)    │ │ (2fps)    │ │ (LLM)    │ │          │ │          │ │  │
│  │  └──────────┘ └───────────┘ └──────────┘ └──────────┘ └──────────┘ │  │
│  │                                                                        │  │
│  │  Agent S2 (EAHP)  ←→  CrewAI  ←→  AutoGen  ←→  OpenInterpreter     │  │
│  │  Memory: ChromaDB (vetorial) + SQLite (episódico) + JSON (semântico) │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    ↕                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                   CAMADA DE PERCEPÇÃO (Multimodal)                    │  │
│  │                                                                        │  │
│  │  Screenshot (mss/grim) ──▶ UI-TARS 1.5 Grounder                     │  │
│  │  AT-SPI pyatspi/dogtail ──▶ Semantic Tree Builder                    │  │
│  │  Playwright DOM ──▶ WebMCP Bridge ──▶ Tool Registry                  │  │
│  │  OCR Tesseract ──▶ Text Extractor                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    ↕                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     CAMADA DE AÇÃO (Multi-Channel)                    │  │
│  │                                                                        │  │
│  │  Web: Playwright + WebMCP Bridge                                      │  │
│  │  Desktop: xdotool (X11) / ydotool (Wayland) / dogtail (AT-SPI)       │  │
│  │  LibreOffice: python-ooo-dev-tools (UNO API) + GUI fallback           │  │
│  │  Wine/CAD: PyAutoGUI + SikuliX + OpenCV                              │  │
│  │  Code: OpenInterpreter (sandbox Python/Bash)                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    ↕                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              CAMADA DE SEGURANÇA (Zero Trust / Enterprise)            │  │
│  │   Docker ← Firejail ← Bubblewrap ← AppArmor ← SELinux               │  │
│  │   Credential Vault (AES-256) │ Audit Log (imutável) │ RBAC           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              ENTERPRISE LAYER (Sala de Aula / Multi-tenant)           │  │
│  │   Dashboard Web (FastAPI + React)  │  WebSocket Server               │  │
│  │   Policy Engine (YAML)  │  LDAP/SSO  │  Grafana + Loki monitoring   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 8.2 Stack Técnica Completa

### 8.2.1 UI e Interface

| Componente | Tecnologia | Justificativa |
|---|---|---|
| Mini-janela (X11) | GTK4 + PyGObject | Nativo Linux, integração perfeita com temas GNOME |
| Mini-janela (Wayland) | Qt6 + PySide6 | Suporte Wayland de primeira classe |
| System Tray | pystray + Pillow | Cross-DE, compatível com GNOME Extension e KDE |
| Hotkeys globais | keyboard + sxhkd | Funciona em X11 e Wayland |
| Markdown render | mistune + Pango | Renderização rica dentro do GTK |

### 8.2.2 Agente e Orquestração

| Componente | Tecnologia | Justificativa |
|---|---|---|
| Orquestrador principal | **LangGraph 0.2+** | Grafo de estado com loops ReAct, checkpointing, human-in-the-loop nativo |
| Framework base | **LangChain 0.3+** | Abstração de LLMs, tool calling, prompts |
| Computer-Use SOTA | **Agent S2 (Simular AI)** | 83.9% OSWorld, EAHP para memória de experiências |
| Multi-agente paralelo | **CrewAI 0.70+** | Agentes especialistas com papéis definidos |
| Multi-agente conversacional | **AutoGen 0.4+** | Debate entre agentes para decisões críticas |
| Execução de código segura | **OpenInterpreter** | Python/Bash em sandbox com filesystem limitado |

### 8.2.3 WebMCP Bridge

| Componente | Tecnologia | Descrição |
|---|---|---|
| Bridge principal | Python asyncio + WebSockets | Conecta Playwright ao LangGraph |
| Detecção de WebMCP | Playwright page.evaluate | Verifica `navigator.modelContext` |
| Tool converter | Pydantic + LangChain | WebMCP schema → LangChain Tool |
| Fallback handler | UI-TARS + Playwright | Ativa quando WebMCP não disponível |

### 8.2.4 Navegador (Web ACI)

| Componente | Tecnologia | Prioridade |
|---|---|---|
| Automação web | **Playwright for Python** | MUST — controle completo Chromium/Firefox |
| Grounding visual web | **UI-TARS 1.5** | MUST — identificação de elementos |
| Stealth mode | playwright-stealth | SHOULD — anti-fingerprint ético |
| Fallback legacy | Selenium 4 | COULD — compatibilidade com sites antigos |

### 8.2.5 Desktop GUI (ACI Nativo)

| Componente | Tecnologia | Uso |
|---|---|---|
| Input X11 | **xdotool** | Mouse/teclado/janelas em X11 |
| Input Wayland | **ydotool** | Input via /dev/uinput, independente do display server |
| Acessibilidade GNOME | **dogtail + pyatspi** | Árvore semântica AT-SPI |
| Controle visual | **PyAutoGUI + OpenCV** | Apps sem AT-SPI (Wine, legado) |
| Template matching | **SikuliX** | Reconhecimento de imagem de alta precisão |

### 8.2.6 LibreOffice ACI

| Componente | Tecnologia | Capacidade |
|---|---|---|
| API primária | **python-ooo-dev-tools** | 95% das tarefas de escritório |
| UNO Bridge | **LibreOffice UNO** | Criação, edição, exportação completa |
| Fallback GUI | dogtail + pyatspi | Dialogs complexos, preferências |
| Macros | LibreOffice Basic + Python | Execução de automações legadas |

### 8.2.7 Voz (STT + TTS)

| Componente | Tecnologia | Modo |
|---|---|---|
| STT offline (foco) | **Whisper.cpp** (faster-whisper) | Sempre disponível, PT-BR otimizado |
| STT online (fallback) | Google Speech API | Opcional, requer consent |
| VAD | Silero VAD | Detecção de início/fim de fala |
| TTS offline | **Piper TTS** (8 idiomas) | Qualidade superior ao pyttsx3 |
| TTS premium | **ElevenLabs** | Cloud, emoção detectada, opt-in |

### 8.2.8 Segurança e Sandboxing

| Camada | Tecnologia | Função |
|---|---|---|
| Isolamento de processo | **Docker** | Namespace de rede, filesystem, PID |
| Filtro de syscalls | **Firejail** | Perfis por aplicativo, seccomp |
| Filesystem jail | **Bubblewrap** | Namespace de montagem sem root |
| Path confinement | **AppArmor** | Restrição de acesso a paths do sistema |
| SELinux (enterprise) | **SELinux policies** | Para RHEL/Fedora enterprise |
| Credential storage | AES-256-GCM + PBKDF2 | Vault local criptografado |
| Audit trail | Append-only + SHA-256 chain | Log imutável de ações |

### 8.2.9 Modelos de IA Recomendados (2026)

| Rank | Modelo | Provider | Uso ideal | Offline |
|---|---|---|---|---|
| 1º | **Grok-4** | xAI | Computer-use, planejamento complexo | Não |
| 2º | **Claude Sonnet 4.6** | Anthropic | Raciocínio, documentos, código | Não |
| 3º | **Gemini 2.5 Pro** | Google | Contexto longo, multimodal | Não |
| 4º | **GPT-5** | OpenAI | Fallback premium | Não |
| 5º | **Llama 4 70B** | Meta (local) | Privacidade total, offline | **Sim** |
| 6º | **Qwen2.5-VL-7B** | Alibaba (local) | Visão + texto, baixo custo GPU | **Sim** |

---

# 9. Estratégia de Implantação e Roadmap

## 9.1 Roadmap Visual

```
Q1 2026           Q2 2026           Q4 2026           Q2 2027
   │                  │                  │                  │
 MVP (v0.1)        v1.0 GA           v2.0              v3.0 Enterprise
   │                  │                  │                  │
 Mini-janela      +Suite LO         +Wine/CAD         +1000 instâncias
 WebMCP+Firefox   +Multi-agente     +Kubernetes       +100 apps
 LO Writer/Calc   +Dashboard        +OSWorld 35%+     +Compliance full
 Whisper STT      +Piper TTS        +SSO/LDAP
```

## 9.2 Fase 1 — MVP (v0.1): Fundação

**Duração:** 12 semanas | **Equipe:** 5 devs + 1 UX + 1 QA

| # | Deliverable | Critério de Aceitação |
|---|---|---|
| D1 | Mini-janela GTK4 (300×400px, always-on-top) | Aparece em < 200ms via hotkey |
| D2 | STT Whisper.cpp (PT-BR offline) | WER < 8% em ambiente quieto |
| D3 | WebMCP Bridge (Gmail, Google Docs) | 67% menos tokens vs. modo visual |
| D4 | LibreOffice Writer + Calc via UNO | 80% de tarefas básicas via API |
| D5 | Modo Professor básico (detecção de erro) | Detecção de erro em < 500ms |
| D6 | Sandbox (Firejail + Docker) | Zero escape em pentest |
| D7 | Audit log imutável | 100% das ações registradas |
| D8 | LangGraph ReAct loop | TCR ≥ 55% no NLB benchmark |

## 9.3 Fase 2 — v1.0 GA: Suite Completa

**Duração:** 12 semanas

| # | Deliverable |
|---|---|
| D9 | LibreOffice Impress + Draw + Base |
| D10 | Multi-agente (Web Agent + Office Agent simultâneos) |
| D11 | Dashboard professor (sala de aula, 30 alunos) |
| D12 | Piper TTS (8 idiomas, PT-BR nativo) |
| D13 | Memória episódica persistente (ChromaDB) |
| D14 | Suporte nativo Wayland (ydotool + Qt6) |
| D15 | AppArmor profiles para apps suportados |

## 9.4 Fase 3 — v2.0: Enterprise + CAD

**Duração:** 16 semanas

| # | Deliverable |
|---|---|
| D16 | Wine/CAD: Fusion 360, Rhinoceros 3D, CorelDRAW |
| D17 | Kubernetes Helm chart (multi-tenant) |
| D18 | SSO/LDAP integração |
| D19 | Grafana + Loki monitoring centralizado |
| D20 | OSWorld-Linux benchmark ≥ 35% |
| D21 | API REST pública (FastAPI) |

## 9.5 Fase 4 — v3.0: Escala Global

**Duração:** 14 semanas

| # | Deliverable |
|---|---|
| D22 | 100+ integrações de apps |
| D23 | Marketplace de trilhas de aprendizagem |
| D24 | Modo classroom remoto (internet) |
| D25 | Full LGPD/FERPA compliance report |
| D26 | OSWorld benchmark ≥ 50% |

---

# 10. Integrações Específicas por Aplicativo

## 10.1 Matriz de Integrações

| Aplicativo | Método Primário | Método Fallback | Fase |
|---|---|---|---|
| Firefox / Chromium | WebMCP + Playwright | xdotool + UI-TARS | MVP |
| LibreOffice Writer | UNO API | dogtail + AT-SPI | MVP |
| LibreOffice Calc | UNO API | dogtail + AT-SPI | MVP |
| LibreOffice Impress | UNO API | dogtail + AT-SPI | v1.0 |
| Gmail | WebMCP (send, search) | Playwright + UI-TARS | MVP |
| Google Docs | WebMCP (create, edit) | Playwright + DOM | MVP |
| GitHub | WebMCP (PR, issues) | Playwright + UI-TARS | v1.0 |
| Thunderbird | dogtail + AT-SPI | PyAutoGUI | v1.0 |
| GIMP | Script-Fu + dogtail | PyAutoGUI + OpenCV | v1.5 |
| Inkscape | dogtail + AT-SPI | PyAutoGUI | v1.5 |
| Fusion 360 (Wine) | PyAutoGUI + SikuliX | API REST F360 | v2.0 |
| Rhinoceros 3D (Wine) | SikuliX + RhinoScript | PyAutoGUI | v2.0 |
| CorelDRAW (Wine) | PyAutoGUI + SikuliX | VBA automation | v2.0 |

## 10.2 WebMCP — Especificação Técnica

### 10.2.1 O que é WebMCP

WebMCP (Web Model Context Protocol) é um padrão emergente (2026) que permite que sites exponham ferramentas estruturadas diretamente para agentes de IA via `navigator.modelContext`. Em vez de o agente "adivinhar" onde clicar usando screenshots, o site publica funções como `login(username, password)` ou `search(query)` que o agente invoca diretamente.

**Benefícios mensurados:**
- **67% redução de tokens** vs. automação por screenshot
- **80% menos falhas** de navegação
- **3x mais rápido** em tarefas de formulário

### 10.2.2 Implementação no NeoPilot

```python
# webmcp_bridge.py — Fluxo de detecção e uso
class WebMCPBridge:
    async def detect_and_activate(self, page: Page) -> bool:
        # 1. Detecta suporte WebMCP
        has_webmcp = await page.evaluate(
            "() => typeof navigator.modelContext !== 'undefined'"
        )
        if not has_webmcp:
            return False  # Usa fallback visual

        # 2. Extrai tools disponíveis
        tools_schema = await page.evaluate(
            "() => navigator.modelContext.getTools()"
        )

        # 3. Converte para LangChain Tools
        self.tools = self._convert_to_langchain_tools(tools_schema)
        return True

    async def call_tool(self, tool_name: str, args: dict) -> Any:
        return await self.page.evaluate(
            f"(args) => navigator.modelContext.callTool('{tool_name}', args)",
            args
        )
```

---

# 11. Fluxos de Dados, Segurança e Sandboxing

## 11.1 Fluxo de Dados Zero Trust

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUXO ZERO TRUST NEOPILOT                    │
│                                                                  │
│  Input do Usuário (Texto/Voz)                                   │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐    Somente texto transcrito                    │
│  │ STT Local   │──────────────────────────────▶                 │
│  │ (Whisper.cpp│    (áudio NUNCA sai do device)                 │
│  └─────────────┘                                                 │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              SANDBOX GATEWAY (verificação de policy)      │   │
│  │   • Bloqueia ações fora da whitelist de apps             │   │
│  │   • Valida path de filesystem                            │   │
│  │   • Detecta tentativa de escalada de privilégio          │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              LangGraph Orchestrator                       │   │
│  │                      │                                   │   │
│  │         ┌────────────┴──────────────┐                   │   │
│  │         ▼                           ▼                   │   │
│  │   WebMCP Tool                 Percepção Visual           │   │
│  │   (direto, seguro)            (screenshot + AT-SPI)      │   │
│  │         │                           │                   │   │
│  │         └────────────┬──────────────┘                   │   │
│  │                      ▼                                   │   │
│  │              Action Executor                             │   │
│  │              (dentro do sandbox)                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              AUDIT LOG (imutável, local)                  │   │
│  │   Ação + Timestamp + SHA-256(prev_hash) + Aprovado?      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 11.2 Modelo de Ameaças e Mitigações

| Ameaça | Vetor | Mitigação |
|---|---|---|
| Prompt Injection via Web | Site malicioso com instruções em HTML | Content analysis + separação dados/instrução |
| Exfiltração via clipboard | App lê clipboard com dados sensíveis | Clipboard sanitization + acesso controlado |
| Escalada de privilégio | Script executado fora do sandbox | Firejail seccomp + Bubblewrap namespaces |
| Credential theft | Screenshot captura senha exibida | Blur automático em campos de senha detectados |
| Sandbox escape | Exploit de isolamento | AppArmor + SELinux como defesa em profundidade |
| Abuse de WebMCP | Site enganoso expõe tools destrutivas | Confirmação humana para tools com side effects |

---

# 12. Testes, Qualidade e Métricas de Avaliação

## 12.1 OSWorld-Linux Benchmark Suite

| Categoria | Tarefas | Meta MVP | Meta v2.0 |
|---|---|---|---|
| LibreOffice (básico-avançado) | 15 tasks | 55% | 78% |
| Browser (WebMCP + fallback) | 20 tasks | 45% | 72% |
| Sistema (terminal seguro) | 10 tasks | 35% | 60% |
| CAD/Wine apps | 5 tasks | — | 40% |
| **Total** | **50 tasks** | **~45%** | **~68%** |

## 12.2 Pirâmide de Testes

```
              [E2E Agent — 50 cenários OSWorld-Linux]
           [Integration — 200 cenários por módulo]
        [Unit Tests — 800+ funções core]
```

## 12.3 Métricas de Qualidade do Agente

| Métrica | Definição | Meta MVP | Meta v1.0 |
|---|---|---|---|
| Task Completion Rate | % tarefas concluídas sem intervenção | 55% | 72% |
| Error Detection Rate | % erros detectados em modo professor | 60% | 75% |
| Grounding Precision@0.85 | IoU > 0.5 com ground truth | 78% | 88% |
| Recovery Rate | % erros que o agente auto-corrige | 40% | 62% |
| Token Efficiency (WebMCP) | Redução vs. modo visual | 50% | 67% |

---

# 13. Riscos, Dependências e Mitigações

| ID | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|
| R01 | WebMCP adoption lenta (poucos sites) | Alta | Alto | Fallback UI-TARS robusto + modo híbrido |
| R02 | Wayland incompatibilidade com apps legados | Média | Médio | XWayland como fallback transparente |
| R03 | LLMs locais lentos (Llama 4 7B) | Alta | Alto | Async execution + cache de respostas |
| R04 | Sandbox escape (vulnerabilidade 0-day) | Baixa | Crítico | 5 camadas defesa + bug bounty |
| R05 | AT-SPI desabilitado por admin | Média | Médio | Grounding visual como fallback total |
| R06 | Modelos multimodais aumentam preços API | Alta | Médio | Modelos locais como alternativa |
| R07 | Regulação EU AI Act restringe Computer Use | Baixa | Alto | Modo suggest-only como fallback legal |
| R08 | Concorrente lança produto Linux similar | Média | Médio | Acelerar WebMCP + modo professor |

---

# 14. Apêndice

## A1: System Prompts de Referência

### Modo Professor
```
Você é NeoPilot, professor paciente de software para Linux.
Modo: PROFESSOR ASSISTIDO

MISSÃO: Acompanhar o usuário dentro de [APP_ATUAL] e guiar sua aprendizagem.

COMPORTAMENTO:
- OBSERVE constantemente a tela via screenshots e AT-SPI
- Se o usuário executa ação INCORRETA vs. nosso plano:
  1. Explique o erro gentilmente (máx 2 frases)
  2. Mostre o passo correto
  3. Pergunte: "Quer que eu execute por você?"
- Se o usuário está no caminho certo: incentive com 1 frase curta
- Se errar 3x seguidos: ofereça demonstração completa

LINGUAGEM: Português claro, sem jargão técnico, tom de tutor próximo.
NUNCA: Execute ações destrutivas sem confirmação. Nunca seja condescendente.
```

### Modo WebMCP
```
Você tem acesso a WebMCP tools para [SITE].
PRIORIZE WebMCP tools sobre grounding visual.
Use grounding visual APENAS se:
  - Tool falhou 2x consecutivas
  - Elemento não exposto via WebMCP
  - Ação requer precisão de pixel específica

Tools disponíveis: {webmcp_tools}
Sempre prefira a tool mais específica para a tarefa.
```

## A2: Configuração Enterprise (policies.yaml)

```yaml
neopilot_enterprise:
  version: "2.0"

  security:
    sandbox: "firejail+docker"
    apparmor_enabled: true
    selinux_enabled: false  # true para RHEL/Fedora

  allowed_applications:
    - name: "libreoffice"
      modes: [professor, autonomous]
    - name: "firefox"
      modes: [professor, autonomous]
      webmcp_enabled: true
    - name: "thunderbird"
      modes: [professor]

  student_permissions:
    autonomous_mode: false      # alunos só em modo professor
    file_delete: false
    system_commands: false
    external_network: false     # só whitelist abaixo

  network_whitelist:
    - "*.escola.edu.br"
    - "*.libreoffice.org"
    - "fonts.google.com"

  classroom:
    dashboard_enabled: true
    dashboard_port: 8765
    remote_intervention: true   # professor pode assumir controle
    exam_mode_available: true

  audit:
    log_path: "/var/log/neopilot/audit.jsonl"
    retention_days: 365
    hash_chain: true
    forward_to_siem: false
```

## A3: Glossário Técnico

| Termo | Definição |
|---|---|
| **ACI (Agent-Computer Interface)** | Interface padronizada para agentes de IA interagirem com sistemas de computador |
| **WebMCP** | Web Model Context Protocol — sites expõem tools estruturadas para agentes via `navigator.modelContext` |
| **Grounding Visual** | Mapeamento de descrições textuais de elementos para localizações precisas na tela |
| **AT-SPI** | Assistive Technology Service Provider Interface — protocolo de acessibilidade Linux |
| **ReAct** | Reasoning + Acting — padrão de agente que intercala raciocínio e ação |
| **HTP** | Hierarchical Task Planning — planejamento de tarefas em múltiplos níveis |
| **EAHP** | Experience-Augmented Hierarchical Planning (Agent S2) |
| **OSWorld** | Benchmark padrão de Computer Use agents |
| **Human-in-the-loop** | Humano mantém aprovação para ações críticas |
| **Compute Use Enterprise** | Copiloto de IA que usa o computador em ambientes corporativos com segurança e governança |

---

*NeoPilot PRD v2.0 — Open Core (AGPLv3 + Enterprise License)*
*Prepared by NeoPilot Product Team — Março 2026*
