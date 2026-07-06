import os
import io
from typing import List, Tuple
import pdfplumber
from docx import Document as DocxDocument
import markdown


class DocumentParser:
    SUPPORTED_TYPES = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".doc": "docx",
        ".md": "markdown",
        ".markdown": "markdown",
        ".txt": "text",
    }

    @classmethod
    def detect_type(cls, filename: str) -> str:
        ext = os.path.splitext(filename.lower())[1]
        return cls.SUPPORTED_TYPES.get(ext, "unknown")

    @classmethod
    def parse(cls, file_path: str, file_type: str) -> Tuple[str, List[dict]]:
        """Return (full_text, pages) where pages is list of {page_no, text}."""
        if file_type == "pdf":
            return cls._parse_pdf(file_path)
        elif file_type == "docx":
            return cls._parse_docx(file_path)
        elif file_type == "markdown":
            return cls._parse_markdown(file_path)
        elif file_type == "text":
            return cls._parse_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def _parse_pdf(file_path: str) -> Tuple[str, List[dict]]:
        pages = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append({"page_no": i, "text": text.strip()})
        full_text = "\n\n".join(p["text"] for p in pages)
        return full_text, pages

    @staticmethod
    def _parse_docx(file_path: str) -> Tuple[str, List[dict]]:
        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n".join(paragraphs)
        # Treat whole doc as single page for MVP
        pages = [{"page_no": 1, "text": full_text}]
        return full_text, pages

    @staticmethod
    def _parse_markdown(file_path: str) -> Tuple[str, List[dict]]:
        with open(file_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        html = markdown.markdown(md_text)
        # Simple strip tags for MVP
        import re
        text = re.sub(r"<[^>]+>", "", html)
        pages = [{"page_no": 1, "text": text.strip()}]
        return text, pages

    @staticmethod
    def _parse_text(file_path: str) -> Tuple[str, List[dict]]:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        pages = [{"page_no": 1, "text": text.strip()}]
        return text, pages
