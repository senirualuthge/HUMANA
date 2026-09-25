"""
humana/app/services/chunker.py
Text splitting and document parsing utilities.
Handles plain text, PDF (pypdf), DOCX (python-docx), Markdown.
"""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import List, Tuple

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
settings = get_settings()


# ── Simple recursive character splitter (no LangChain dep at runtime) ─────────
def _split_text(
    text: str,
    chunk_size: int,
    overlap: int,
) -> List[str]:
    """
    Split on double-newline, then single-newline, then sentences, then words.
    Returns list of chunks with `overlap` character overlap.
    """
    text = text.strip()
    if not text:
        return []

    separators = ["\n\n", "\n", ". ", " ", ""]
    for sep in separators:
        if sep and len(text.split(sep)) > 1:
            pieces = text.split(sep)
            break
    else:
        pieces = list(text)

    chunks: List[str] = []
    current = ""
    for piece in pieces:
        candidate = current + (sep if current else "") + piece
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            # carry overlap
            if overlap and current:
                current = current[-overlap:] + (sep if sep else "") + piece
            else:
                current = piece
    if current.strip():
        chunks.append(current.strip())

    # Filter empties and dedup
    seen = set()
    result = []
    for c in chunks:
        if c and c not in seen:
            seen.add(c)
            result.append(c)
    return result


def chunk_text(text: str) -> List[str]:
    return _split_text(text, settings.chunk_size, settings.chunk_overlap)


# ── File parsers ──────────────────────────────────────────────────────────────
def parse_pdf(content: bytes) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content))
        pages = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                pages.append(extracted)
        return "\n\n".join(pages)
    except Exception as exc:
        log.error("pdf_parse_failed", error=str(exc))
        raise ValueError(f"Could not parse PDF: {exc}") from exc


def parse_docx(content: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(content))
        paras = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paras)
    except Exception as exc:
        log.error("docx_parse_failed", error=str(exc))
        raise ValueError(f"Could not parse DOCX: {exc}") from exc


def parse_markdown(content: bytes) -> str:
    text = content.decode("utf-8", errors="ignore")
    # Strip markdown syntax for cleaner chunking
    text = re.sub(r"#+\s", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`{1,3}.*?`{1,3}", "", text, flags=re.DOTALL)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text


def parse_file(filename: str, content: bytes) -> Tuple[str, str]:
    """
    Returns (parsed_text, doc_type).
    Raises ValueError for unsupported formats.
    """
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return parse_pdf(content), "pdf"
    elif ext == ".docx":
        return parse_docx(content), "docx"
    elif ext in (".md", ".markdown"):
        return parse_markdown(content), "md"
    elif ext in (".txt", ".text", ""):
        return content.decode("utf-8", errors="ignore"), "text"
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use PDF, TXT, DOCX, or MD.")
