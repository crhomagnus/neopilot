"""
NeoPilot STT — Speech-to-Text
faster-whisper (local, offline) + Silero VAD para detecção de atividade de voz.
Suporte a português brasileiro por padrão.
"""

from __future__ import annotations

import io
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from neopilot.core.logger import get_logger

logger = get_logger("stt")


@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    duration_s: float
    timestamp: float = field(default_factory=time.time)


class VoiceActivityDetector:
    """Detecta segmentos de fala usando Silero VAD."""

    SAMPLE_RATE = 16000
    CHUNK_SIZE = 512  # ~32ms @ 16kHz

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self._model = None
        self._available = False
        self._load()

    def _load(self) -> None:
        try:
            import torch
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                trust_repo=True,
            )
            self._model = model
            self._get_speech_timestamps = utils[0]
            self._available = True
            logger.info("Silero VAD carregado")
        except Exception as e:
            logger.warning("Silero VAD não disponível", error=str(e))

    def is_speech(self, audio_chunk: bytes) -> bool:
        """Retorna True se chunk contém fala."""
        if not self._available or not self._model:
            return True  # assume fala se VAD não disponível

        try:
            import torch
            audio = torch.frombuffer(audio_chunk, dtype=torch.int16).float() / 32768.0
            confidence = self._model(audio.unsqueeze(0), self.SAMPLE_RATE).item()
            return confidence > self.threshold
        except Exception:
            return True

    def detect_speech_segments(self, audio_data: bytes) -> list[dict]:
        """Detecta segmentos de fala em arquivo de áudio completo."""
        if not self._available or not self._model:
            return [{"start": 0, "end": len(audio_data)}]

        try:
            import torch
            audio = torch.frombuffer(audio_data, dtype=torch.int16).float() / 32768.0
            segments = self._get_speech_timestamps(
                audio, self._model,
                sampling_rate=self.SAMPLE_RATE,
                threshold=self.threshold,
            )
            return [{"start": s["start"], "end": s["end"]} for s in segments]
        except Exception as e:
            logger.warning("VAD segment detection falhou", error=str(e))
            return [{"start": 0, "end": len(audio_data)}]


class WhisperSTT:
    """
    STT usando faster-whisper com suporte a português.
    Usa modelo local para privacidade e funcionamento offline.
    """

    DEFAULT_MODEL = "base"  # tiny|base|small|medium|large-v3
    SAMPLE_RATE = 16000

    def __init__(self, model_size: str = DEFAULT_MODEL, language: str = "pt"):
        self.model_size = model_size
        self.language = language
        self._model = None
        self._available = False
        self.vad = VoiceActivityDetector()
        self._load()

    def _load(self) -> None:
        try:
            from faster_whisper import WhisperModel
            cache_dir = Path.home() / ".neopilot" / "models" / "whisper"
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
                download_root=str(cache_dir),
            )
            self._available = True
            logger.info("Whisper STT carregado", model=self.model_size)
        except ImportError:
            logger.warning("faster-whisper não instalado")
        except Exception as e:
            logger.error("Falha ao carregar Whisper", error=str(e))

    def transcribe_file(self, audio_path: str) -> TranscriptionResult:
        """Transcreve arquivo de áudio."""
        if not self._available or not self._model:
            return TranscriptionResult(text="", language="pt", confidence=0.0, duration_s=0.0)

        start = time.time()
        try:
            segments, info = self._model.transcribe(
                audio_path,
                language=self.language,
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )
            text = " ".join(seg.text.strip() for seg in segments)
            duration = time.time() - start
            confidence = getattr(info, "language_probability", 1.0)

            logger.info("Transcrição concluída", text=text[:60], duration=round(duration, 2))
            return TranscriptionResult(
                text=text.strip(),
                language=info.language,
                confidence=confidence,
                duration_s=duration,
            )
        except Exception as e:
            logger.error("Transcrição falhou", error=str(e))
            return TranscriptionResult(text="", language="pt", confidence=0.0, duration_s=0.0)

    def transcribe_bytes(self, audio_bytes: bytes, sample_rate: int = 16000) -> TranscriptionResult:
        """Transcreve áudio a partir de bytes."""
        import tempfile, wave, os
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name

            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(audio_bytes)

            result = self.transcribe_file(tmp_path)
            os.unlink(tmp_path)
            return result
        except Exception as e:
            logger.error("transcribe_bytes falhou", error=str(e))
            return TranscriptionResult(text="", language="pt", confidence=0.0, duration_s=0.0)


class MicrophoneListener:
    """
    Captura áudio do microfone em tempo real com detecção de atividade de voz.
    Usa PyAudio ou sounddevice.
    """

    CHUNK = 1024
    SAMPLE_RATE = 16000
    CHANNELS = 1
    FORMAT = None  # pyaudio.paInt16

    def __init__(
        self,
        stt: WhisperSTT,
        on_transcription: Callable[[TranscriptionResult], None],
        silence_threshold_s: float = 1.5,
        min_speech_s: float = 0.3,
    ):
        self.stt = stt
        self.on_transcription = on_transcription
        self.silence_threshold_s = silence_threshold_s
        self.min_speech_s = min_speech_s
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue = queue.Queue()

    def start(self) -> bool:
        """Inicia captura de microfone em background thread."""
        try:
            import pyaudio
            self.FORMAT = pyaudio.paInt16
            self._running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
            logger.info("Microfone iniciado")
            return True
        except ImportError:
            logger.warning("pyaudio não disponível, tentando sounddevice")
            return self._start_sounddevice()
        except Exception as e:
            logger.error("Falha ao iniciar microfone", error=str(e))
            return False

    def _start_sounddevice(self) -> bool:
        try:
            import sounddevice as sd
            self._running = True
            self._thread = threading.Thread(target=self._listen_loop_sd, daemon=True)
            self._thread.start()
            logger.info("Microfone iniciado via sounddevice")
            return True
        except Exception as e:
            logger.error("sounddevice também falhou", error=str(e))
            return False

    def _listen_loop(self) -> None:
        """Loop de captura com PyAudio."""
        import pyaudio
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.SAMPLE_RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
        )

        frames: list[bytes] = []
        silent_chunks = 0
        silence_limit = int(self.silence_threshold_s * self.SAMPLE_RATE / self.CHUNK)
        min_speech_chunks = int(self.min_speech_s * self.SAMPLE_RATE / self.CHUNK)

        try:
            while self._running:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                is_speech = self.stt.vad.is_speech(data)

                if is_speech:
                    frames.append(data)
                    silent_chunks = 0
                elif frames:
                    silent_chunks += 1
                    frames.append(data)
                    if silent_chunks >= silence_limit:
                        if len(frames) >= min_speech_chunks:
                            audio_bytes = b"".join(frames)
                            result = self.stt.transcribe_bytes(audio_bytes)
                            if result.text:
                                self.on_transcription(result)
                        frames.clear()
                        silent_chunks = 0
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def _listen_loop_sd(self) -> None:
        """Loop de captura com sounddevice."""
        import sounddevice as sd
        import numpy as np

        frames: list[bytes] = []
        silent_chunks = 0
        silence_limit = int(self.silence_threshold_s * self.SAMPLE_RATE / self.CHUNK)
        min_speech_chunks = int(self.min_speech_s * self.SAMPLE_RATE / self.CHUNK)

        def callback(indata, _frames, _time, _status):
            audio_bytes = (indata * 32767).astype("int16").tobytes()
            is_speech = self.stt.vad.is_speech(audio_bytes)

            if is_speech:
                frames.append(audio_bytes)
            elif frames:
                frames.append(audio_bytes)
                nonlocal silent_chunks
                silent_chunks += 1
                if silent_chunks >= silence_limit:
                    if len(frames) >= min_speech_chunks:
                        audio_bytes_all = b"".join(frames)
                        result = self.stt.transcribe_bytes(audio_bytes_all)
                        if result.text:
                            self.on_transcription(result)
                    frames.clear()
                    silent_chunks = 0

        with sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="float32",
            blocksize=self.CHUNK,
            callback=callback,
        ):
            while self._running:
                time.sleep(0.1)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("Microfone parado")
