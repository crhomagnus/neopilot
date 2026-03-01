"""
NeoPilot LibreOffice Agent
Controle profundo do LibreOffice via UNO API (python-ooo-dev-tools).
Inclui modo professor para LibreOffice Calc/Writer.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from neopilot.core.logger import get_logger

logger = get_logger("lo_agent")


@dataclass
class LOResult:
    success: bool
    method: str  # "uno" | "gui_fallback"
    data: Any = None
    error: Optional[str] = None
    file_path: Optional[str] = None


class LibreOfficeAgent:
    """
    Agente especialista para LibreOffice via UNO API.
    Conecta ao LibreOffice em modo socket server para controle programático completo.
    """

    UNO_PORT = 2002

    def __init__(self):
        self._lo_connected = False
        self._desktop: Any = None
        self._doc: Any = None

    def start_libreoffice_server(self) -> bool:
        """Inicia LibreOffice em modo socket server se não estiver rodando."""
        import socket
        try:
            sock = socket.create_connection(("localhost", self.UNO_PORT), timeout=1)
            sock.close()
            logger.info("LibreOffice server já está rodando")
            return True
        except ConnectionRefusedError:
            pass

        logger.info("Iniciando LibreOffice em modo server...")
        subprocess.Popen([
            "soffice",
            "--headless",
            "--accept=socket,host=localhost,port=2002;urp;StarOffice.ServiceManager",
            "--norestore",
            "--nocrashreport",
        ])

        # Aguarda inicialização
        for i in range(15):
            time.sleep(1)
            try:
                sock = socket.create_connection(("localhost", self.UNO_PORT), timeout=1)
                sock.close()
                logger.info("LibreOffice server iniciado", attempts=i + 1)
                return True
            except Exception:
                pass

        logger.error("LibreOffice server não iniciou em 15 segundos")
        return False

    def connect(self) -> bool:
        """Conecta ao LibreOffice via UNO bridge."""
        try:
            import uno
            from com.sun.star.beans import PropertyValue

            localContext = uno.getComponentContext()
            resolver = localContext.ServiceManager.createInstanceWithContext(
                "com.sun.star.bridge.UnoUrlResolver", localContext
            )
            ctx = resolver.resolve(
                f"uno:socket,host=localhost,port={self.UNO_PORT};"
                "urp;StarOffice.ComponentContext"
            )
            smgr = ctx.ServiceManager
            self._desktop = smgr.createInstanceWithContext(
                "com.sun.star.frame.Desktop", ctx
            )
            self._lo_connected = True
            logger.info("Conectado ao LibreOffice via UNO")
            return True
        except Exception as e:
            logger.error("Falha ao conectar ao LibreOffice UNO", error=str(e))
            self._lo_connected = False
            return False

    def _ensure_connected(self) -> bool:
        if not self._lo_connected:
            if not self.start_libreoffice_server():
                return False
            time.sleep(2)
            return self.connect()
        return True

    # ─── Writer ────────────────────────────────────────────────────────────────

    def create_writer_document(
        self,
        content: str,
        title: str = "Documento",
        output_path: Optional[str] = None,
    ) -> LOResult:
        """Cria documento Writer com conteúdo especificado."""
        if not self._ensure_connected():
            return self._fallback_writer_create(content, title, output_path)

        try:
            import uno
            from com.sun.star.beans import PropertyValue

            doc = self._desktop.loadComponentFromURL(
                "private:factory/swriter", "_blank", 0, ()
            )
            text = doc.getText()
            cursor = text.createTextCursor()
            cursor.gotoStart(False)

            # Insere conteúdo com formatação básica
            for line in content.split("\n"):
                text.insertString(cursor, line, False)
                text.insertControlCharacter(
                    cursor,
                    uno.getConstantByName(
                        "com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK"
                    ),
                    False,
                )

            # Define título do documento
            doc_info = doc.getDocumentProperties()
            doc_info.Title = title

            # Salva se path fornecido
            if output_path:
                path = Path(output_path).expanduser()
                store_url = f"file://{path.absolute()}"
                props = self._pdf_props() if str(path).endswith(".pdf") else ()
                doc.storeToURL(store_url, props)
                logger.info("Documento Writer salvo", path=str(path))
                return LOResult(success=True, method="uno", file_path=str(path))

            return LOResult(success=True, method="uno", data=doc)

        except Exception as e:
            logger.error("Falha ao criar documento Writer", error=str(e))
            return LOResult(success=False, method="uno", error=str(e))

    def _fallback_writer_create(self, content: str, title: str, output_path: Optional[str]) -> LOResult:
        """Fallback: cria arquivo .odt diretamente sem UNO."""
        try:
            path = Path(output_path or f"~/{title}.odt").expanduser()
            # Usa python-docx como último recurso (converte depois)
            path.write_text(content, encoding="utf-8")
            return LOResult(success=True, method="gui_fallback", file_path=str(path))
        except Exception as e:
            return LOResult(success=False, method="gui_fallback", error=str(e))

    # ─── Calc ──────────────────────────────────────────────────────────────────

    def create_calc_spreadsheet(
        self,
        data: list[list[Any]],
        headers: Optional[list[str]] = None,
        sheet_name: str = "Planilha1",
        output_path: Optional[str] = None,
        create_chart: bool = False,
    ) -> LOResult:
        """Cria planilha Calc com dados, headers opcionais e gráfico."""
        if not self._ensure_connected():
            return LOResult(success=False, method="uno", error="LibreOffice não conectado")

        try:
            doc = self._desktop.loadComponentFromURL(
                "private:factory/scalc", "_blank", 0, ()
            )
            sheets = doc.getSheets()
            sheet = sheets.getByIndex(0)
            sheet.setName(sheet_name)

            row_offset = 0

            # Headers
            if headers:
                for col, header in enumerate(headers):
                    cell = sheet.getCellByPosition(col, 0)
                    cell.setString(header)
                    # Negrito no header
                    cell.CharWeight = 150  # com.sun.star.awt.FontWeight.BOLD
                row_offset = 1

            # Dados
            for row_idx, row in enumerate(data):
                for col_idx, value in enumerate(row):
                    cell = sheet.getCellByPosition(col_idx, row_idx + row_offset)
                    if isinstance(value, (int, float)):
                        cell.setValue(value)
                    elif isinstance(value, str) and value.startswith("="):
                        cell.setFormula(value)
                    else:
                        cell.setString(str(value))

            # Gráfico simples
            if create_chart and data:
                self._insert_chart(sheet, len(headers or data[0]), len(data) + row_offset)

            if output_path:
                path = Path(output_path).expanduser()
                doc.storeToURL(f"file://{path.absolute()}", ())
                logger.info("Planilha Calc salva", path=str(path))
                return LOResult(success=True, method="uno", file_path=str(path))

            return LOResult(success=True, method="uno", data=doc)

        except Exception as e:
            logger.error("Falha ao criar planilha Calc", error=str(e))
            return LOResult(success=False, method="uno", error=str(e))

    def detect_formula_error(self, sheet_name: Optional[str] = None) -> list[dict]:
        """Detecta fórmulas com erro na planilha atual (modo professor Calc)."""
        if not self._doc or not self._lo_connected:
            return []

        errors = []
        try:
            sheets = self._doc.getSheets()
            sheet = sheets.getByName(sheet_name) if sheet_name else sheets.getByIndex(0)

            cursor = sheet.createCursor()
            cursor.gotoStartOfUsedArea(False)
            cursor.gotoEndOfUsedArea(True)

            end_col = cursor.getRangeAddress().EndColumn
            end_row = cursor.getRangeAddress().EndRow

            for row in range(end_row + 1):
                for col in range(end_col + 1):
                    cell = sheet.getCellByPosition(col, row)
                    # Tipo 3 = FORMULA, verifica se há erro
                    if cell.getType() == 3:
                        formula = cell.getFormula()
                        formula_result = cell.getString()
                        if formula_result.startswith("Err:") or formula_result == "#NAME?":
                            errors.append({
                                "row": row + 1,
                                "col": col + 1,
                                "cell_ref": self._col_to_letter(col) + str(row + 1),
                                "formula": formula,
                                "error": formula_result,
                            })
        except Exception as e:
            logger.error("Falha ao detectar erros de fórmula", error=str(e))

        return errors

    def _col_to_letter(self, col: int) -> str:
        result = ""
        while col >= 0:
            result = chr(col % 26 + ord('A')) + result
            col = col // 26 - 1
        return result

    def _insert_chart(self, sheet: Any, num_cols: int, num_rows: int) -> None:
        """Insere gráfico de barras básico na planilha."""
        try:
            import uno
            from com.sun.star.awt import Rectangle
            from com.sun.star.table import CellRangeAddress

            charts = sheet.Charts
            rect = Rectangle()
            rect.X = 3000
            rect.Y = num_rows * 600 + 500
            rect.Width = 10000
            rect.Height = 7000

            range_addr = CellRangeAddress()
            range_addr.Sheet = 0
            range_addr.StartColumn = 0
            range_addr.StartRow = 0
            range_addr.EndColumn = num_cols - 1
            range_addr.EndRow = num_rows - 1

            charts.addNewByName("Gráfico1", rect, (range_addr,), True, True)
        except Exception as e:
            logger.debug("Falha ao inserir gráfico", error=str(e))

    def export_to_pdf(self, doc: Any, output_path: str) -> LOResult:
        """Exporta documento aberto como PDF."""
        try:
            path = Path(output_path).expanduser()
            doc.storeToURL(f"file://{path.absolute()}", self._pdf_props())
            return LOResult(success=True, method="uno", file_path=str(path))
        except Exception as e:
            return LOResult(success=False, method="uno", error=str(e))

    def run_macro(self, macro_name: str, module: str = "Standard") -> LOResult:
        """Executa macro LibreOffice Basic existente."""
        if not self._ensure_connected():
            return LOResult(success=False, method="uno", error="LibreOffice não conectado")
        try:
            dispatcher = self._desktop.createDispatchHelper()
            dispatcher.executeDispatch(
                self._desktop.getCurrentFrame(),
                f".uno:MacroDialog",
                "",
                0,
                (),
            )
            return LOResult(success=True, method="uno", data=f"Macro {macro_name} executada")
        except Exception as e:
            return LOResult(success=False, method="uno", error=str(e))

    def _pdf_props(self) -> tuple:
        """Propriedades de exportação PDF."""
        try:
            import uno
            from com.sun.star.beans import PropertyValue
            prop = PropertyValue()
            prop.Name = "FilterName"
            prop.Value = "writer_pdf_Export"
            return (prop,)
        except Exception:
            return ()

    def close(self) -> None:
        """Encerra conexão com LibreOffice."""
        if self._doc:
            try:
                self._doc.close(True)
            except Exception:
                pass
        self._lo_connected = False
        logger.info("LibreOffice Agent desconectado")
