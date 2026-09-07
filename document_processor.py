import os
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader

def extract_text_from_file(file_path: Path) -> List[Tuple[int, str]]:
    """
    Extracts text per page/section from a file.
    Returns a list of tuples: (page_number, text_content).
    """
    ext = file_path.suffix.lower()
    pages_data = []

    if ext == ".pdf":
        try:
            reader = PdfReader(str(file_path))
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                cleaned = clean_text(text)
                if cleaned:
                    pages_data.append((i + 1, cleaned))
            if not pages_data:
                # If extraction was empty (scanned or protected), provide notice
                pages_data.append((1, "Document uploaded but text content could not be extracted directly."))
        except Exception as e:
            pages_data.append((1, f"Error reading PDF file: {str(e)}"))

    elif ext in [".txt", ".md", ".markdown", ".csv", ".json"]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            cleaned = clean_text(content)
            # Break large text files into virtual pages (~2500 characters per page)
            page_size = 2500
            if len(cleaned) <= page_size:
                pages_data.append((1, cleaned))
            else:
                for idx, start in enumerate(range(0, len(cleaned), page_size)):
                    pages_data.append((idx + 1, cleaned[start:start + page_size]))
        except Exception as e:
            pages_data.append((1, f"Error reading text file: {str(e)}"))
    else:
        pages_data.append((1, f"Unsupported file type {ext}."))

    return pages_data

def clean_text(text: str) -> str:
    """Normalizes whitespace and cleans up formatting artifacts."""
    if not text:
        return ""
    # Replace weird unicode spaces/chars
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Consolidate excessive spaces
    text = re.sub(r'[ \t]+', ' ', text)
    # Consolidate excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def chunk_document(
    pages_data: List[Tuple[int, str]], 
    chunk_size: int = 500, 
    chunk_overlap: int = 100
) -> List[Dict[str, Any]]:
    """
    Chunks document page-by-page preserving page numbers and detecting section headings.
    """
    chunks = []
    chunk_index = 0

    heading_pattern = re.compile(r'^(?:#+\s*|\d+[\.\)]\s*|[A-Z\s]{4,}:?\s*)([A-Za-z0-9\s\-_–—]+)$', re.MULTILINE)

    for page_num, page_text in pages_data:
        if not page_text:
            continue

        # Extract probable headings on this page
        headings = heading_pattern.findall(page_text)
        current_heading = headings[0].strip() if headings else f"Page {page_num}"

        # Split into sentences or paragraphs
        paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
        
        buffer = ""
        for para in paragraphs:
            # Check if this paragraph itself is a heading
            if len(para) < 80 and any(h in para for h in headings):
                current_heading = para.strip('# ').strip()

            if len(buffer) + len(para) + 1 <= chunk_size:
                buffer = f"{buffer} {para}".strip() if buffer else para
            else:
                if buffer:
                    token_approx = len(buffer.split())
                    chunks.append({
                        "chunk_index": chunk_index,
                        "page_number": page_num,
                        "heading": current_heading,
                        "content": buffer,
                        "token_count": token_approx
                    })
                    chunk_index += 1
                    # Retain overlap from end of buffer
                    overlap_chars = buffer[-chunk_overlap:] if len(buffer) > chunk_overlap else buffer
                    buffer = f"{overlap_chars} {para}".strip()
                else:
                    # If paragraph itself is longer than chunk_size, split by slicing
                    for sub_idx in range(0, len(para), chunk_size - chunk_overlap):
                        sub_text = para[sub_idx:sub_idx + chunk_size].strip()
                        if sub_text:
                            chunks.append({
                                "chunk_index": chunk_index,
                                "page_number": page_num,
                                "heading": current_heading,
                                "content": sub_text,
                                "token_count": len(sub_text.split())
                            })
                            chunk_index += 1
                    buffer = ""

        if buffer:
            chunks.append({
                "chunk_index": chunk_index,
                "page_number": page_num,
                "heading": current_heading,
                "content": buffer,
                "token_count": len(buffer.split())
            })
            chunk_index += 1

    return chunks
