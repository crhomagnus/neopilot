"""
NeoPilot TTS — Text-to-Speech
Piper TTS (local, offline, alta qualidade) + ElevenLabs (cloud, opcional).
Suporte a português brasileiro.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from neopilot.core.logger import get_logger

logger = get_logger("tts")


@dataclass
class TTSResult:
    success: bool
    method: str  # "piper" | "elevenlabs" | "espeak"
    audio_path: Optional[str] = None
    error: Optional[str] = None
    duration_s: float = 0.0


class PiperTTS:
    """
    TTS de alta qualidade usando Piper (offline).
    Modelo pt_BR disponível em github.com/rhasspy/piper.
    """

    # Modelos portugueses disponíveis no Piper
    MODELS = {
        "pt_BR": "pt_BR-faber-medium",
        "pt_PT": "pt_PT-tugão-medium",
    }

    def __init__(self, language: str = "pt_BR", models_dir: Optional[Path] = None):
        self.language = language
        self.models_dir = models_dir or Path.home() / ".neopilot" / "models" / "piper"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._model_path: Optional[Path] = None
        self._piper_bin: Optional[str] = None
        self._available = False
        self._check()

    def _check(self) -> None:
        """Verifica se Piper está disponível."""
        # Tenta piper no PATH
        try:
            result = subprocess.run(
                ["piper", "--version"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                self._piper_bin = "piper"
                self._find_model()
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Tenta piper instalado como Python package
        try:
            import piper
            self._piper_module = piper
            self._find_model()
            logger.info("Piper TTS disponível via Python package")
        except ImportError:
            logger.warning("Piper TTS não disponível, usando espeak fallback")

    def _find_model(self) -> None:
        """Localiza ou baixa modelo de voz."""
        model_name = self.MODELS.get(self.language, self.MODELS["pt_BR"])

        # Procura modelo local
        for ext in [".onnx", ""]:
            candidates = [
                self.models_dir / f"{model_name}{ext}",
                Path.home() / ".local/share/piper" / f"{model_name}.onnx",
            ]
            for path in candidates:
                if path.exists():
                    self._model_path = path
                    self._available = True
                    logger.info("Modelo Piper encontrado", path=str(path))
                    return

        logger.warning(
            "Modelo Piper não encontrado",
            model=model_name,
            hint=f"Baixe em: https://huggingface.co/rhasspy/piper-voices/tree/main/pt/{self.language}"
        )

    def synthesize(self, text: str, output_path: Optional[str] = None) -> TTSResult:
        """Sintetiza texto para áudio usando Piper."""
        if not self._available:
            return self._espeak_fallback(text, output_path)

        start = time.time()
        out_path = output_path or str(
            Path(tempfile.mktemp(suffix=".wav", dir="/tmp"))
        )

        try:
            if self._piper_bin:
                result = subprocess.run(
                    [
                        self._piper_bin,
                        "--model", str(self._model_path),
                        "--output_file", out_path,
                    ],
                    input=text,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Piper falhou: {result.stderr}")
            else:
                # Via Python package
                import piper
                voice = piper.PiperVoice.load(str(self._model_path))
                with open(out_path, "wb") as f:
                    voice.synthesize(text, f)

            duration = time.time() - start
            logger.debug("TTS sintetizado", chars=len(text), duration=round(duration, 2))
            return TTSResult(success=True, method="piper", audio_path=out_path, duration_s=duration)

        except Exception as e:
            logger.error("Piper TTS falhou", error=str(e))
            return self._espeak_fallback(text, output_path)

    def _espeak_fallback(self, text: str, output_path: Optional[str] = None) -> TTSResult:
        """Fallback usando espeak-ng (qualidade inferior mas sempre disponível)."""
        out_path = output_path or str(Path(tempfile.mktemp(suffix=".wav", dir="/tmp")))
        try:
            subprocess.run(
                [
                    "espeak-ng",
                    "-v", "pt-br",
                    "-w", out_path,
                    "--speed=150",
                    text,
                ],
                check=True,
                capture_output=True,
                timeout=15,
            )
            return TTSResult(success=True, method="espeak", audio_path=out_path)
        except Exception as e:
            logger.error("espeak fallback também falhou", error=str(e))
            return TTSResult(success=False, method="espeak", error=str(e))

    def play(self, text: str) -> TTSResult:
        """Sintetiza e reproduz imediatamente."""
        result = self.synthesize(text)
        if result.success and result.audio_path:
            self._play_audio(result.audio_path)
        return result

    @staticmethod
    def _play_audio(path: str) -> None:
        """Reproduz arquivo de áudio."""
        for player in ["aplay", "paplay", "ffplay -nodisp -autoexit"]:
            try:
                cmd = player.split() + [path]
                subprocess.run(cmd, capture_output=True, timeout=30)
                return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue


class ElevenLabsTTS:
    """
    TTS cloud de alta qualidade usando ElevenLabs API.
    Usado quando Piper não está disponível ou para vozes premium.
    """

    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel (inglês/multilíngue)
    PT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam (aceita pt-BR)

    def __init__(self, api_key: Optional[str] = None, voice_id: Optional[str] = None):
        self.api_key = api_key
        self.voice_id = voice_id or self.PT_VOICE_ID
        self._available = bool(api_key)

    def synthesize(self, text: str, output_path: Optional[str] = None) -> TTSResult:
        if not self._available:
            return TTSResult(success=False, method="elevenlabs", error="API key não configurada")

        out_path = output_path or str(Path(tempfile.mktemp(suffix=".mp3", dir="/tmp")))
        start = time.time()

        try:
            import requests
            resp = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                },
                timeout=30,
            )
            resp.raise_for_status()

            with open(out_path, "wb") as f:
                f.write(resp.content)

            duration = time.time() - start
            return TTSResult(success=True, method="elevenlabs", audio_path=out_path, duration_s=duration)

        except Exception as e:
            logger.error("ElevenLabs TTS falhou", error=str(e))
            return TTSResult(success=False, method="elevenlabs", error=str(e))


class TTSEngine:
    """
    Motor TTS unificado: Piper (local) → ElevenLabs (cloud) → espeak (fallback).
    """

    def __init__(
        self,
        language: str = "pt_BR",
        elevenlabs_key: Optional[str] = None,
    ):
        self.piper = PiperTTS(language=language)
        self.elevenlabs = ElevenLabsTTS(api_key=elevenlabs_key) if elevenlabs_key else None
        self._async_queue: list[str] = []

    def speak(self, text: str, async_mode: bool = False) -> TTSResult:
        """
        Sintetiza e reproduz texto.
        async_mode=True: não bloqueia (reproduz em background thread).
        """
        if not text or not text.strip():
            return TTSResult(success=True, method="none")

        if async_mode:
            import threading
            thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
            thread.start()
            return TTSResult(success=True, method="async")

        return self._speak_sync(text)

    def _speak_sync(self, text: str) -> TTSResult:
        """Fala sincronamente: Piper → ElevenLabs → espeak."""
        # Tenta Piper primeiro
        result = self.piper.play(text)
        if result.success:
            return result

        # Fallback para ElevenLabs
        if self.elevenlabs:
            result = self.elevenlabs.synthesize(text)
            if result.success and result.audio_path:
                PiperTTS._play_audio(result.audio_path)
                return result

        # Último fallback: espeak direto
        try:
            subprocess.run(
                ["espeak-ng", "-v", "pt-br", "--speed=150", text],
                timeout=15,
                capture_output=True,
            )
            return TTSResult(success=True, method="espeak")
        except Exception as e:
            return TTSResult(success=False, method="espeak", error=str(e))

    def speak_notification(self, message: str) -> None:
        """Fala notificação curta em background."""
        self.speak(message, async_mode=True)

    def speak_error(self, error: str) -> None:
        """Fala mensagem de erro em português."""
        self.speak(f"Atenção: {error}", async_mode=True)

    def speak_confirmation(self, action: str) -> None:
        """Fala pedido de confirmação."""
        self.speak(f"Posso executar: {action}? Diga sim para confirmar.", async_mode=True)
