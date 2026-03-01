FROM python:3.11-slim

LABEL maintainer="NeoPilot Project"
LABEL description="NeoPilot — Agente de IA Co-Pilot Universal para Linux"

# Sistema base
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Ferramentas de UI
    xdotool \
    ydotool \
    xvfb \
    # AT-SPI / Acessibilidade
    libatk1.0-dev \
    python3-pyatspi \
    # LibreOffice (headless)
    libreoffice-calc \
    libreoffice-writer \
    # TTS
    espeak-ng \
    # Áudio (para captura de microfone)
    portaudio19-dev \
    # OCR
    tesseract-ocr \
    tesseract-ocr-por \
    tesseract-ocr-eng \
    # Utilitários
    curl \
    git \
    wget \
    xclip \
    xdg-utils \
    # Firejail / Bubblewrap
    firejail \
    bubblewrap \
    && rm -rf /var/lib/apt/lists/*

# GTK4 / GObject Introspection (para UI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-gi \
    gir1.2-gtk-4.0 \
    libgtk-4-dev \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root
RUN useradd -m -u 1000 neopilot && mkdir -p /home/neopilot/.neopilot
WORKDIR /app

# Instala dependências Python
COPY pyproject.toml /app/
RUN pip install --no-cache-dir pip setuptools wheel && \
    pip install --no-cache-dir \
    langchain-core \
    langchain-anthropic \
    langchain-openai \
    langgraph \
    playwright \
    faster-whisper \
    chromadb \
    structlog \
    pydantic-settings \
    typer[all] \
    rich \
    cryptography \
    PyYAML \
    httpx \
    requests \
    Pillow \
    opencv-python-headless \
    pytesseract \
    pyautogui \
    pyaudio \
    sounddevice \
    numpy \
    fastapi \
    uvicorn[standard] \
    websockets \
    && playwright install chromium --with-deps

# Copia código fonte
COPY src/ /app/src/
COPY config/ /app/config/

# Instala pacote
RUN pip install --no-cache-dir -e /app

# Configura display virtual
ENV DISPLAY=:99
ENV NEOPILOT_AGENT__MODE=copilot
ENV NEOPILOT_LLM__PROVIDER=anthropic

# Script de inicialização
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

USER neopilot

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD neopilot status || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["neopilot", "chat", "--no-gui"]
