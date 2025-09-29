# core/pdf_service.py
# shim de compatibilidade: re-exporta PDFService do novo pacote core.pdf
from core.pdf.pdf_service import PDFService

__all__ = ["PDFService"]
