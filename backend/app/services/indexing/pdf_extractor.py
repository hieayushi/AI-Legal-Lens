"""
PDF text extraction + TOC detection + page splitting using PyMuPDF.
Runs OCR fallback via pytesseract if native text is sparse.
"""
import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    import pytesseract
    from pdf2image import convert_from_path
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

MIN_NATIVE_CHARS = 50

# Heading pattern matching Chapter, Section, Subsection structures
_HEADING_RE = re.compile(
    r"^(?:"
    r"(?:CHAPTER|SECTION|PART|ARTICLE|ORDER|RULE|SCHEDULE|SUB-SECTION)\s+[\dIVXLCivxlc]+[.:]?\s+.+"
    r"|(?:\d+\.){1,3}\s+[A-Z].{5,}"
    r"|[A-Z][A-Z\s]{4,}$"
    r")",
    re.MULTILINE,
)


def extract_document(file_path: str) -> Dict[str, Any]:
    """
    Extracts text per page, builds the TOC structural hierarchy, and detects scanned pages.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    pages_text, is_scanned = _extract_text(str(path))
    toc = _build_toc(pages_text, str(path))
    _assign_sections(pages_text, toc)
    detected_title = _detect_title(pages_text)

    return {
        "pages": pages_text,
        "toc": toc,
        "page_count": len(pages_text),
        "is_scanned": is_scanned,
        "detected_title": detected_title,
    }


def _extract_text(file_path: str) -> Tuple[List[Dict[str, Any]], bool]:
    pages = []
    is_scanned = False

    try:
        doc = fitz.open(file_path)
        for i, page in enumerate(doc, start=1):
            text = page.get_text() or ""
            pages.append({"page_number": i, "text": text.strip()})
        doc.close()
    except Exception as e:
        logger.error(f"PyMuPDF failed to extract text from {file_path}: {e}")
        pages = [{"page_number": 1, "text": ""}]

    # Check if scanned (mostly images / empty text)
    avg_chars = sum(len(p["text"]) for p in pages) / max(len(pages), 1)
    if avg_chars < MIN_NATIVE_CHARS and HAS_OCR:
        logger.info(f"Scanned document detected (avg chars {avg_chars:.1f}). Initiating OCR...")
        pages = _ocr_pages(file_path, len(pages))
        is_scanned = True

    return pages, is_scanned


def _ocr_pages(file_path: str, expected_pages: int) -> List[Dict[str, Any]]:
    pages = []
    try:
        images = convert_from_path(file_path, dpi=150)
        for i, img in enumerate(images, start=1):
            text = pytesseract.image_to_string(img, lang="eng")
            pages.append({"page_number": i, "text": text.strip()})
    except Exception as e:
        logger.error(f"OCR failed for {file_path}: {e}")
        pages = [{"page_number": i, "text": ""} for i in range(1, expected_pages + 1)]
    return pages


def _detect_title(pages: List[Dict[str, Any]]) -> str:
    if not pages:
        return "Untitled Document"
    first_page_text = pages[0].get("text", "")
    for line in first_page_text.splitlines():
        line = line.strip()
        if len(line) > 5 and not line.isdigit():
            return line[:200]
    return "Untitled Document"


def _build_toc(pages: List[Dict[str, Any]], file_path: str) -> List[Dict[str, Any]]:
    toc = []

    # Strategy 1: Attempt PyMuPDF native TOC extraction
    try:
        doc = fitz.open(file_path)
        native_toc = doc.get_toc()
        doc.close()
        if native_toc:
            for item in native_toc:
                # format: [level, title, page_number]
                level, title, page = item
                toc.append({
                    "title": title.strip()[:200],
                    "page": page,
                    "level": level
                })
            return toc
    except Exception as e:
        logger.warning(f"PyMuPDF get_toc failed, fallback to structural parsing: {e}")

    # Strategy 2: Structural parsing heuristic via regex match
    for page in pages:
        text = page.get("text", "")
        for match in _HEADING_RE.finditer(text):
            heading = match.group(0).strip()
            if len(heading) > 4:
                level = _heading_level(heading)
                toc.append({
                    "title": heading[:200],
                    "page": page["page_number"],
                    "level": level,
                })

    # Deduplicate consecutive/redundant headings
    seen = set()
    unique_toc = []
    for item in toc:
        key = (item["title"].lower(), item["page"])
        if key not in seen:
            seen.add(key)
            unique_toc.append(item)
    return unique_toc[:50]


def _heading_level(heading: str) -> int:
    h = heading.upper()
    if h.startswith("CHAPTER") or h.startswith("PART"):
        return 1
    if h.startswith("SECTION") or h.startswith("ARTICLE"):
        return 2
    if h.startswith("SUB-SECTION") or h.startswith("SUBSECTION"):
        return 3
    return 3


def _assign_sections(pages: List[Dict[str, Any]], toc: List[Dict[str, Any]]) -> None:
    toc_by_page = {}
    for item in toc:
        # Keep the highest level heading if multiple on same page
        page_num = item["page"]
        if page_num not in toc_by_page or item["level"] < toc_by_page[page_num]["level"]:
            toc_by_page[page_num] = item

    current_section = None
    current_level = 0
    for page in pages:
        pn = page["page_number"]
        if pn in toc_by_page:
            current_section = toc_by_page[pn]["title"]
            current_level = toc_by_page[pn]["level"]
        page["section_title"] = current_section
        page["section_level"] = current_level
