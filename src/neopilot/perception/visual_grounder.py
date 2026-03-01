"""
NeoPilot Visual Grounder
Identificação de elementos de UI em screenshots via OpenCV + OCR + UI-TARS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image

from neopilot.core.logger import get_logger
from neopilot.perception.screen_capture import Screenshot

logger = get_logger("visual_grounder")


@dataclass
class GroundingResult:
    found: bool
    x: int
    y: int
    width: int
    height: int
    confidence: float
    method: str           # "template" | "ocr" | "ui_tars" | "llm"
    element_text: str = ""

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height


class VisualGrounder:
    """
    Grounding visual de elementos de UI em screenshots.
    Ordem de preferência: UI-TARS → OCR → Template Matching → LLM Vision.
    """

    CONFIDENCE_THRESHOLD = 0.80

    def __init__(self, use_ui_tars: bool = False):
        self.use_ui_tars = use_ui_tars
        self._ui_tars_model = None
        if use_ui_tars:
            self._load_ui_tars()

    def _load_ui_tars(self) -> None:
        try:
            from transformers import AutoProcessor, AutoModelForCausalLM
            import torch
            logger.info("Carregando modelo UI-TARS...")
            self._ui_tars_processor = AutoProcessor.from_pretrained(
                "bytedance-research/UI-TARS-7B-SFT",
                trust_remote_code=True,
            )
            self._ui_tars_model = AutoModelForCausalLM.from_pretrained(
                "bytedance-research/UI-TARS-7B-SFT",
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
            )
            logger.info("UI-TARS carregado com sucesso")
        except Exception as e:
            logger.warning("UI-TARS não disponível, usando OCR+Template", error=str(e))
            self.use_ui_tars = False

    def find_by_text(
        self, screenshot: Screenshot, text: str, lang: str = "por+eng"
    ) -> GroundingResult:
        """Localiza elemento pelo texto visível via OCR (Tesseract)."""
        gray = cv2.cvtColor(screenshot.image, cv2.COLOR_BGR2GRAY)
        # Aumenta contraste para melhorar OCR
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        data = pytesseract.image_to_data(
            gray,
            lang=lang,
            output_type=pytesseract.Output.DICT,
        )

        target_lower = text.lower()
        for i, word in enumerate(data["text"]):
            conf = int(data["conf"][i])
            if conf < 0:
                continue
            if target_lower in word.lower() and conf > 50:
                x, y = data["left"][i], data["top"][i]
                w, h = data["width"][i], data["height"][i]
                logger.debug("Elemento encontrado via OCR", text=word, conf=conf)
                return GroundingResult(
                    found=True, x=x, y=y, width=w, height=h,
                    confidence=conf / 100, method="ocr",
                    element_text=word,
                )

        return GroundingResult(
            found=False, x=0, y=0, width=0, height=0,
            confidence=0.0, method="ocr",
        )

    def find_by_template(
        self,
        screenshot: Screenshot,
        template: np.ndarray,
        threshold: float = 0.85,
    ) -> GroundingResult:
        """Localiza elemento por template matching (OpenCV)."""
        result = cv2.matchTemplate(
            screenshot.image, template, cv2.TM_CCOEFF_NORMED
        )
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            x, y = max_loc
            h, w = template.shape[:2]
            logger.debug("Template match encontrado", confidence=max_val)
            return GroundingResult(
                found=True, x=x, y=y, width=w, height=h,
                confidence=max_val, method="template",
            )

        return GroundingResult(
            found=False, x=0, y=0, width=0, height=0,
            confidence=max_val, method="template",
        )

    def find_by_template_file(
        self,
        screenshot: Screenshot,
        template_path: str,
        threshold: float = 0.85,
    ) -> GroundingResult:
        """Localiza elemento por template salvo em arquivo."""
        template = cv2.imread(template_path)
        if template is None:
            logger.error("Template não encontrado", path=template_path)
            return GroundingResult(
                found=False, x=0, y=0, width=0, height=0,
                confidence=0.0, method="template",
            )
        return self.find_by_template(screenshot, template, threshold)

    def find_by_ui_tars(
        self, screenshot: Screenshot, description: str
    ) -> GroundingResult:
        """Localiza elemento via modelo UI-TARS (grounding visual neural)."""
        if not self.use_ui_tars or self._ui_tars_model is None:
            return GroundingResult(
                found=False, x=0, y=0, width=0, height=0,
                confidence=0.0, method="ui_tars",
            )

        try:
            import torch

            inputs = self._ui_tars_processor(
                text=f"Find the UI element: {description}",
                images=screenshot.pil_image,
                return_tensors="pt",
            )
            inputs = {k: v.to(self._ui_tars_model.device) for k, v in inputs.items()}

            with torch.inference_mode():
                outputs = self._ui_tars_model.generate(
                    **inputs, max_new_tokens=128
                )

            result_text = self._ui_tars_processor.decode(
                outputs[0], skip_special_tokens=True
            )

            # Parse bbox from output (formato: "x=0.1,y=0.2,w=0.05,h=0.03")
            bbox = self._parse_bbox_output(result_text, screenshot)
            if bbox:
                x, y, w, h = bbox
                return GroundingResult(
                    found=True, x=x, y=y, width=w, height=h,
                    confidence=0.92, method="ui_tars",
                    element_text=description,
                )
        except Exception as e:
            logger.error("Erro no UI-TARS grounding", error=str(e))

        return GroundingResult(
            found=False, x=0, y=0, width=0, height=0,
            confidence=0.0, method="ui_tars",
        )

    def _parse_bbox_output(
        self, text: str, screenshot: Screenshot
    ) -> Optional[tuple[int, int, int, int]]:
        """Extrai coordenadas normalizadas do output do modelo."""
        import re
        pattern = r"(\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*)"
        match = re.search(pattern, text)
        if not match:
            return None

        vals = [float(v) for v in match.groups()]

        # Se os valores são normalizados (0-1), converte para pixels
        if all(v <= 1.0 for v in vals):
            x = int(vals[0] * screenshot.width)
            y = int(vals[1] * screenshot.height)
            w = int(vals[2] * screenshot.width)
            h = int(vals[3] * screenshot.height)
        else:
            x, y, w, h = (int(v) for v in vals)

        return x, y, w, h

    def find(
        self,
        screenshot: Screenshot,
        description: str,
        template: Optional[np.ndarray] = None,
    ) -> GroundingResult:
        """
        Método principal: tenta múltiplos métodos em ordem de confiança.
        1. UI-TARS (se disponível)
        2. OCR (busca por texto)
        3. Template matching (se template fornecido)
        """
        # 1. UI-TARS
        if self.use_ui_tars:
            result = self.find_by_ui_tars(screenshot, description)
            if result.found and result.confidence >= self.CONFIDENCE_THRESHOLD:
                logger.info("Elemento encontrado via UI-TARS", description=description)
                return result

        # 2. OCR
        result = self.find_by_text(screenshot, description)
        if result.found and result.confidence >= self.CONFIDENCE_THRESHOLD:
            logger.info("Elemento encontrado via OCR", description=description)
            return result

        # 3. Template matching
        if template is not None:
            result = self.find_by_template(screenshot, template)
            if result.found:
                logger.info("Elemento encontrado via template matching")
                return result

        logger.warning("Elemento não encontrado", description=description)
        return GroundingResult(
            found=False, x=0, y=0, width=0, height=0,
            confidence=0.0, method="none",
        )

    def extract_all_text(self, screenshot: Screenshot, lang: str = "por+eng") -> str:
        """Extrai todo o texto da screenshot via OCR."""
        gray = cv2.cvtColor(screenshot.image, cv2.COLOR_BGR2GRAY)
        return pytesseract.image_to_string(gray, lang=lang)

    def detect_ui_regions(self, screenshot: Screenshot) -> list[dict]:
        """Detecta regiões de UI (botões, caixas de texto) via morfologia."""
        gray = cv2.cvtColor(screenshot.image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
        dilated = cv2.dilate(binary, kernel, iterations=2)

        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 30 and h > 10:  # Filtra ruído
                regions.append({"x": x, "y": y, "width": w, "height": h})

        return regions
